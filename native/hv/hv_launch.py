#!/usr/bin/env python3
"""Run the verified boot033/boot034 diagnostic kernel at EL1 under a private m1n1 HV.

Private iLinux tooling (never for upstream). Default execution is offline:
it verifies both packages and opens no USB port. A live run:

1. checks the installed boot021 m1n1 exactly like native/boot/launch.py, then
   repeats the guarded register census (hv_regs.py) in the same boot;
2. chainloads the private hv m1n1 into RAM (no RVBAR writes, no disk). The
   default in-tree mode does what src/chainload.c does: only SEPFW moves and
   its ADT property is patched in place in the raw ADT, as the very last
   write before the handoff (slot 2 and every host-only line come just before
   it; afterwards only cache maintenance, one short print and the handoff
   follow, all under one guard: a failed or interrupted patch is reverted and
   the outcome reported, up to the moment reload() is entered). All layout
   gates run before the first write (hv_chainload.py); the new instance's
   top_of_kernel_data is max(current, destination end), so its heap starts
   where the old one did. The copy stub marks its entry in slot 3, clears the
   screen strip and paints a bar over slots 0-4, and the new m1n1 lights
   slots 5-20 (where its own guard lets it paint), so the screen names how
   far the handoff got. --chainload-mode python is the old six-blob flow that
   rebuilds and rewrites the whole ADT (size-checked, read back, restored on
   failure);
3. proves a NEW m1n1 instance answers (its boot_args pointer is the copy this
   launcher staged, which the original instance cannot report), re-verifies
   the target, gates on the hv single-CPU/ECV flags (only on this full path,
   after hv.init()), and prepares the effective DT with the same checks as the
   native launcher;
4. starts Linux as a single-CPU EL1 guest. The kernel log is mirrored to the
   HV virtual UART (USB interface 3); Ctrl-C enters the HV shell.

Two live diagnostic modes stop earlier. --layout-only reads the target and
prints the layout gates, the framebuffer facts and the destination end against
top_of_kernel_data; it makes no memory writes (ProxyUtils itself issues two
m1n1 heap-bookkeeping requests, heapblock_alloc(0) and heapblock_set_limit).
It exits 0 on LAYOUT PASS and 3 on LAYOUT FAIL (2 is an argument error, 1 a
STOP line, 130 Ctrl-C). --chainload-only chainloads, proves the new instance,
re-verifies the marker and stops without starting the HV; with --control stock
it chainloads the guest package's stock boot021 m1n1.bin instead (a control for
the chainload mechanism itself). Only ONE chainload can happen per boot of the
original instance: power-cycle between runs.

The target's console text is never echoed (tty_enable is off on every open),
because it can carry the device serial number; error text never contains a
USB callout path.

Nothing is installed; power off returns the machine to Macintosh HD.
"""
import argparse
import collections
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
BOOT = HERE.parent / "boot"
sys.path.insert(0, str(BOOT))
import launch  # noqa: E402  (boot033 package gates and fixed constants)
import dapf_guard  # noqa: E402
import entry_guard  # noqa: E402
import gpio_guard  # noqa: E402
from fdt import check_stage_b  # noqa: E402
sys.path.insert(0, str(HERE))
import adt_patch  # noqa: E402
import hv_chainload  # noqa: E402
import hv_regs  # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / "tools/m1n1-client"))
import usb_identity  # noqa: E402

CONFIRM = "HV-J716C-RAM-DIAGNOSTIC"
CONTROL_NOTE = ("Control session: only ONE chainload can happen per boot of the original "
                "instance (the stock m1n1 you chainload looks exactly like the one that is "
                "running, so a second run in the same power cycle is refused by the layout "
                "gate or proves nothing). POWER-CYCLE between chainload runs.")
# What success means for the stock control build (it carries no breadcrumb patch).
CONTROL_SUCCESS = ("stock build paints no c-blocks: success is the bar only plus the USB port "
                   "returning and the new-instance proof")
# Exit codes of --layout-only (argparse errors exit 2, a STOP line 1, Ctrl-C 130).
EXIT_LAYOUT_PASS = 0
EXIT_LAYOUT_FAIL = 3
# What the layout gates have established once they pass (hv_chainload.check_layout).
LAYOUT_GATE_PASS = ("Layout gate PASS: the destination clears the ADT and framebuffer; any "
                    "staging overlap is below the stub and the copy is ascending; the staging "
                    "block starts at or above top_of_kernel_data and clears the source blobs "
                    "being moved; no earlier chainload detected.")
LAYOUT_ONLY_NOTE = ("no memory writes; ProxyUtils issues two m1n1 heap-bookkeeping requests "
                    "(heapblock_alloc(0), heapblock_set_limit)")
# Outcomes of a failed live ADT write; the wording is what the operator acts on.
ADT_NOT_RESTORED = ("live ADT SEPFW patched and NOT restored: POWER OFF completely before any "
                    "further run")
ADT_RESTORED = "live ADT patch failed and was restored and verified"
RELOAD_NO_PORT = ("reload() did not reopen the port (%s); handoff issued, live ADT patched: "
                  "trying the descriptor-checked reconnect; if that fails POWER OFF and read the "
                  "strip per hv-instructions.md")
# A callout path embeds the device serial number: it ends at whitespace or a delimiter.
DEVICE_PATH = re.compile(r"/dev/(?:cu|tty)\.[^\s'\"`:;,)\]}>]*")
CHIP_T6050 = 0x6050
P_ILINUX_KBOOT_PREPARE_HV_GUEST = 0x7F0
UART0 = 0x505200000
CPU_START_T6050 = 0x88000  # smp.c uses the T6031 offset for T6050
MIB = 1024 * 1024

# boot033's fixed arguments with an extra console on the HV virtual UART.
# console=tty0 stays last, so /dev/console (diag init's direct writes) is the
# framebuffer exactly as in native boots. Kernel printk, including diag
# init's /dev/kmsg copies, goes to both consoles; serial console writes are
# polled, so they do not depend on vUART interrupts. Only one earlycon is
# possible: the serial one replaces earlycon=ilinuxfb.
HV_BOOTARGS = launch.BOOTARGS.replace(
    "console=tty0", "console=ttySAC0,115200 console=tty0").replace(
    "earlycon=ilinuxfb", "earlycon=s5l,0x%x" % UART0)

# Symbols of the private patch that the launcher reads or calls; their
# offsets are recorded in hv-manifest.json and checked against the build.
HV_SYMBOLS = {"dt": "hv_dt_pointer_offset",
              "hv_ilinux_single_cpu": "hv_single_cpu_offset",
              "hv_ilinux_init_failed": "hv_init_failed_offset"}


def manifest():
    return json.loads((HERE / "hv-manifest.json").read_text())


def guest_manifest_for(directory):
    """The repository manifest that matches this guest package, by name and content.

    native/boot/package-manifest.json always describes the *newest* package, so a
    guest from an earlier release (boot033) is checked against its retained
    bootNNN-package-manifest.json instead. launch.py itself stays unchanged.
    """
    own = json.loads((directory / "package-manifest.json").read_text())
    candidates = [BOOT / "package-manifest.json"] + sorted(BOOT.glob("boot*-package-manifest.json"))
    for path in candidates:
        repo = json.loads(path.read_text())
        if repo.get("package") == own.get("package"):
            if repo != own:
                raise ValueError("package manifest differs from the repository's " + path.name)
            return repo
    raise ValueError("no repository manifest for package " + str(own.get("package")))


def verify_guest_package(directory):
    """launch.verify_package() with the matching manifest; same file and DT gates."""
    manifest = guest_manifest_for(directory)
    if manifest["m1n1_commit"] != launch.M1N1_COMMIT:
        raise ValueError("unexpected m1n1 pin")
    loaded = {}
    for name, info in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("invalid package filename")
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != info["size"]:
            raise ValueError("missing file or size mismatch: " + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != info["sha256"]:
            raise ValueError("checksum mismatch: " + name)
        loaded[name] = data
    image = loaded["Image"]
    if image[56:60] != b"ARM\x64" or len(image) < 64:
        raise ValueError("not an uncompressed ARM64 Image")
    check_stage_b(loaded["t6050-j716c-stage-b.dtb"])
    dapf_guard.verify_image(loaded["m1n1.bin"])
    entry_guard.descriptor_offset(image)
    return manifest, loaded


def say(text):
    print(text, flush=True)


def stub(entry, paint=None):
    """Copy stub with an 8-byte aligned literal pool; see hv_chainload.stub()."""
    return hv_chainload.stub(entry, paint)


def parse_nm(text):
    """`nm -an` output: offset, type, name. m1n1 links at 0 = its RAM base."""
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3:
            out.setdefault(parts[2], int(parts[0], 16))
    return out


def system_map_name(m, image):
    """(System.map file name, guest package name or None) for this guest Image.

    Schema 2 lists "guests": {image_sha256: {"package", "system_map"}}. The
    schema-1 keys (guest_image_sha256 + System.map) are still accepted.
    """
    digest = hashlib.sha256(image).hexdigest()
    entry = (m.get("guests") or {}).get(digest)
    if entry is not None:
        name = entry.get("system_map") if isinstance(entry, dict) else None
        if not isinstance(name, str) or Path(name).name != name or not name:
            raise ValueError("invalid guests entry in the hv manifest")
        return name, entry.get("package")
    if m.get("guest_image_sha256") == digest:
        return "System.map", m.get("guest_package")
    raise ValueError("guest Image is not one this hv package was built for")


# Schema 1 recorded one patch and no symbol list; these were checked then.
SCHEMA1_REQUIRED_SYMBOLS = ("kboot_prepare_hv_guest", "hv_ilinux_timers_reset")
HEX_DIGEST = re.compile(r"[0-9a-f]{64}")


def manifest_patches(m):
    """([(patch file name, sha256)], required symbol names) of a schema 1 or 2 hv manifest.

    Schema 1: "m1n1_patch" (a repository path; only its file name is used) with
    "m1n1_patch_sha256". Schema 2 (make_hv_package.py): "m1n1_patches" as a list
    of {"file", "sha256"} and "required_symbols". Names are plain file names
    that sit next to this launcher; nothing is read here.
    """
    schema = m.get("schema")
    if schema == 1:
        name = m.get("m1n1_patch")
        if not isinstance(name, str) or not name:
            raise ValueError("hv manifest names no m1n1 patch")
        entries = [{"file": Path(name).name, "sha256": m.get("m1n1_patch_sha256")}]
        required = list(SCHEMA1_REQUIRED_SYMBOLS)
    elif schema == 2:
        entries, required = m.get("m1n1_patches"), m.get("required_symbols")
        if not isinstance(entries, list) or not entries:
            raise ValueError("hv manifest lists no m1n1 patches")
        if (not isinstance(required, list) or not required or
                not all(isinstance(s, str) and s for s in required)):
            raise ValueError("hv manifest lists no required symbols")
    else:
        raise ValueError("unsupported hv manifest schema")
    out = []
    for entry in entries:
        name = entry.get("file") if isinstance(entry, dict) else None
        digest = entry.get("sha256") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name or Path(name).name != name or name[0] == ".":
            raise ValueError("invalid patch file name in the hv manifest")
        if not isinstance(digest, str) or not HEX_DIGEST.fullmatch(digest):
            raise ValueError("invalid patch digest in the hv manifest: " + name)
        if name in [n for n, _ in out]:
            raise ValueError("patch listed twice in the hv manifest: " + name)
        out.append((name, digest))
    return out, required


def check_toolchain_record(m, patches, loaded):
    """Tie the manifest's commit and patch digests to the build record that came with the binary.

    The job's toolchain.txt names the m1n1 commit and the digest of every patch
    it applied ("m1n1 <commit> + <sha> + <sha>"). Without this a patch file
    edited after the build, with its manifest digest edited to match, would
    still verify. Schema 2 only.
    """
    if "toolchain.txt" not in loaded:
        raise ValueError("hv manifest does not list the build record (toolchain.txt)")
    record = loaded["toolchain.txt"].decode("utf-8", "replace").lower()
    if m["m1n1_commit"].lower() not in record:
        raise ValueError("hv build record does not name the manifest's m1n1 commit")
    for patch_name, patch_digest in patches:
        if patch_digest.lower() not in record:
            raise ValueError("hv build record does not name the digest of patch " + patch_name)


def verify_hv_package(directory, image, guest_package=None):
    m = manifest()
    if m["m1n1_commit"] != launch.M1N1_COMMIT:
        raise ValueError("hv build is not based on the pinned m1n1")
    patches, required_symbols = manifest_patches(m)
    for patch_name, patch_digest in patches:
        patch_path = HERE / patch_name
        if patch_path.is_symlink() or not patch_path.is_file():
            raise ValueError("hv patch file is missing next to the launcher: " + patch_name)
        if hashlib.sha256(patch_path.read_bytes()).hexdigest() != patch_digest:
            raise ValueError("hv patch differs from the manifest: " + patch_name)
    map_name, want_package = system_map_name(m, image)
    if guest_package is not None and want_package is not None and want_package != guest_package:
        raise ValueError("hv package was built for a different guest package")
    if map_name not in m["files"]:
        raise ValueError("System.map file is not listed in the hv manifest: " + map_name)
    loaded = {}
    for name, info in m["files"].items():
        if Path(name).name != name:
            raise ValueError("invalid package filename")
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != info["size"]:
            raise ValueError("missing file or size mismatch: " + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != info["sha256"]:
            raise ValueError("checksum mismatch: " + name)
        loaded[name] = data
    if m["schema"] == 2:
        check_toolchain_record(m, patches, loaded)
    hv = loaded["m1n1-hv.bin"]
    marker = m["hv_version_marker"].encode() + b"\0"
    off = m["hv_version_offset"]
    if hv[off:off + len(marker)] != marker:
        raise ValueError("hv version marker not at the recorded offset")
    syms = parse_nm(loaded["m1n1-hv-symbols.txt"].decode("ascii"))
    for symbol, key in HV_SYMBOLS.items():
        if syms.get(symbol) != m[key]:
            raise ValueError("hv symbol offset differs from the build: " + symbol)
    for required in required_symbols:
        if required not in syms:
            raise ValueError("hv build lacks " + required + " (not an hv m1n1 build with the "
                             "patches this manifest lists)")
    if not all(m[key] < len(hv) for key in HV_SYMBOLS.values()):
        raise ValueError("hv symbol outside the loaded image")
    with hv_dapf_pin(hv):
        dapf_guard.verify_image(hv)
    check_system_map(loaded[map_name].decode("ascii"), image)
    return m, loaded


def check_system_map(text, image):
    """The map must describe this exact Image (Image starts at _text)."""
    syms = parse_nm(text)
    for name in ("_text", "_end", "ilinux_fb_descriptor", "deferred_probe_initcall"):
        if name not in syms:
            raise ValueError("System.map lacks " + name)
    if syms["ilinux_fb_descriptor"] - syms["_text"] != entry_guard.descriptor_offset(image):
        raise ValueError("System.map does not match the guest Image")
    image_size = struct.unpack_from("<Q", image, 16)[0]
    if syms["_end"] - syms["_text"] != image_size:
        raise ValueError("System.map image size differs from the Image header")
    return syms


@contextlib.contextmanager
def hv_dapf_pin(hv_image):
    """Reuse the reviewed DAPF guard for the hv build.

    Only the whole-image pin differs: job 034 confirmed identical table,
    path and function offsets; prepare() still compares live code bytes.
    """
    old = dapf_guard.IMAGE_SHA256
    dapf_guard.IMAGE_SHA256 = hashlib.sha256(hv_image).hexdigest()
    try:
        yield
    finally:
        dapf_guard.IMAGE_SHA256 = old


def align_up(value, alignment):
    return (value + alignment - 1) & ~(alignment - 1)


def guest_layout(heap_top, mem_top, image, initrd_len, dt_len):
    """Place Linux, initramfs and DT above the HV heap, inside guest RAM."""
    text_offset, image_size = struct.unpack_from("<QQ", image, 8)
    if text_offset > 2 * MIB or image_size < len(image) or image_size > 512 * MIB:
        raise ValueError("unsupported Image memory layout")
    base = align_up(heap_top + 16 * MIB, 2 * MIB)
    kernel = base + text_offset
    initrd = align_up(kernel + image_size, 64 * 1024)
    dt = align_up(initrd + initrd_len, 64 * 1024)
    end = align_up(dt + max(dt_len, 2 * MIB), 2 * MIB)
    if end > mem_top:
        raise ValueError("guest payloads do not fit below the top of RAM")
    return {"base": base, "kernel": kernel, "initrd": initrd, "dt": dt, "end": end}


def _fdt_props(blob):
    """Yield (node_path, prop_name, value_offset, length) from a flat DT."""
    magic, total, off_struct, off_strings = struct.unpack_from(">IIII", blob, 0)
    if magic != 0xD00DFEED or total > len(blob):
        raise ValueError("invalid FDT")
    pos, path = off_struct, []
    while True:
        tag = struct.unpack_from(">I", blob, pos)[0]
        pos += 4
        if tag == 1:
            end = blob.index(b"\0", pos)
            path.append(blob[pos:end].decode())
            pos = align_up(end + 1, 4)
        elif tag == 2:
            path.pop()
        elif tag == 3:
            length, nameoff = struct.unpack_from(">II", blob, pos)
            pos += 8
            name_end = blob.index(b"\0", off_strings + nameoff)
            name = blob[off_strings + nameoff:name_end].decode()
            yield "/".join(path) or "/", name, pos, length
            pos = align_up(pos + length, 4)
        elif tag == 4:
            continue
        elif tag == 9:
            return
        else:
            raise ValueError("invalid FDT token")


def restrict_memory(blob, guest_base):
    """Start Linux's first RAM range at guest_base, excluding the HV.

    m1n1's kboot declares the boot-args range as region 0; later regions are
    reserved-memory outside it. Patch region 0 in place (same length).
    """
    out = bytearray(blob)
    regs = [(p, o, n) for p, name, o, n in _fdt_props(blob)
            if name == "reg" and p.rsplit("/", 1)[-1].startswith("memory")]
    if len(regs) != 1 or regs[0][2] < 16 or regs[0][2] % 16:
        raise ValueError("expected one /memory node with 64-bit ranges")
    _, off, _ = regs[0]
    start, size = struct.unpack_from(">QQ", blob, off)
    if not start < guest_base < start + size:
        raise ValueError("guest base outside the declared RAM range")
    struct.pack_into(">QQ", out, off, guest_base, start + size - guest_base)
    return bytes(out)


def check_payload_overlap(tree, layout):
    """Kernel/initramfs/DT must not land on reserved memory or the framebuffer."""
    for path, node in tree.items():
        if not (path.startswith("/reserved-memory/") or path.startswith("/chosen/framebuffer")):
            continue
        reg = node.get("reg", b"")
        for i in range(0, len(reg) - len(reg) % 16, 16):
            start, size = struct.unpack_from(">QQ", reg, i)
            if start < layout["end"] and layout["base"] < start + size:
                raise ValueError("guest payloads overlap " + path)


def check_target(iface, proxy, base, marker, offset):
    proxy.nop()
    if proxy.get_chipid() != CHIP_T6050:
        raise ValueError("target chip is not t6050")
    want = marker.encode("ascii") + b"\0"
    if iface.readmem(base + offset, len(want)) != want:
        raise ValueError("target m1n1 does not match " + marker)
    launch.ensure_no_secondaries(proxy)


def register_preflight(utils, errors):
    """Guarded register census in this boot, before anything is chainloaded."""
    rows = hv_regs.census(utils, errors)
    blockers = hv_regs.verdict(rows)
    if blockers:
        raise ValueError("register preflight BLOCKED: " + "; ".join(blockers))
    return rows


def check_hv_flags(proxy, base, m):
    """The HV must have taken its single-CPU path and found the ECV timer traps."""
    single = proxy.read8(base + m["hv_single_cpu_offset"])
    failed = proxy.read8(base + m["hv_init_failed_offset"])
    if single != 1:
        raise ValueError("hv m1n1 did not enter single-CPU mode")
    if failed != 0:
        raise ValueError("hv m1n1 refused to start: no ECV timer traps; power off")


TargetState = collections.namedtuple(
    "TargetState", "ba_addr raw_ba ba adt_addr raw_adt memory_map problems")
Prepared = collections.namedtuple("Prepared", "state plan facts problems notes moved")

MAX_ADT = 64 * MIB
BA_FIELDS = ("virt_base", "phys_base", "mem_size", "top_of_kernel_data", "devtree",
             "devtree_size")
# The strip decisions (video_ok, stub_paint) and the table use depth as well.
VIDEO_FIELDS = ("base", "stride", "width", "height", "depth")


def printable(text):
    """Text from the target (ADT names in parse errors) reduced to plain ASCII."""
    return "".join(c if " " <= c <= "~" else "?" for c in str(text))[:200]


def read_target_state(iface, proxy, utils):
    """Fresh raw boot_args and ADT bytes from the target. Reads only.

    The raw bytes are what the in-tree chainload copies and patches. They are
    cross-checked against what the controller parsed at startup; any
    difference is a problem, never silently accepted.
    """
    problems = []
    ba_addr = proxy.get_bootargs()
    raw_ba = iface.readmem(ba_addr, hv_chainload.BOOT_ARGS_LEN)
    ba = hv_chainload.parse_boot_args(raw_ba)
    if ba.revision > 3:
        problems.append("unsupported boot_args revision %d" % ba.revision)
    ctrl = utils.ba
    for name in BA_FIELDS:
        if getattr(ctrl, name, None) != getattr(ba, name):
            problems.append("boot_args %s differs from the controller's copy" % name)
    for name in VIDEO_FIELDS:
        if getattr(getattr(ctrl, "video", None), name, None) != getattr(ba.video, name):
            problems.append("boot_args video %s differs from the controller's copy" % name)
    raw_adt, memory_map = b"", {}
    if not 0 < ba.devtree_size <= MAX_ADT:
        problems.append("ADT size 0x%x is implausible" % ba.devtree_size)
    else:
        raw_adt = iface.readmem(ba.adt_address, ba.devtree_size)
        if raw_adt != utils.get_adt():
            problems.append("ADT read from the target differs from the controller's copy")
        try:
            memory_map = adt_patch.memory_map(raw_adt)
        except adt_patch.ADTError as exc:
            problems.append("ADT walk failed: %s" % printable(exc))
    return TargetState(ba_addr, raw_ba, ba, ba.adt_address, raw_adt, memory_map, problems)


def build_facts(state, staging):
    ba = state.ba
    framebuffer = None
    if ba.video.base:
        framebuffer = (ba.video.base, ba.video.stride * ba.video.height)
    return hv_chainload.Facts(
        adt=(state.adt_addr, ba.devtree_size),
        boot_args=(state.ba_addr, hv_chainload.BOOT_ARGS_LEN),
        framebuffer=framebuffer, staging=staging, ram=(ba.phys_base, ba.mem_size),
        memory_map=dict(state.memory_map), top=ba.top_of_kernel_data)


def gate_layout(utils, state, plan, moved, staging_size):
    """Allocate the staging block (host-side bookkeeping only) and run the gates.

    The staging address is a gate input, so it is allocated first; nothing
    reaches the target until the caller has seen an empty problem list.
    """
    staging = None
    if not plan.overflow:
        try:
            staging = (utils.malloc(staging_size), staging_size)
        except Exception:  # the proxy heap raises a plain Exception when full
            staging = None
    facts = build_facts(state, staging)
    problems, notes = hv_chainload.check_layout(plan, facts, moved)
    return Prepared(state, plan, facts, list(state.problems) + problems, notes, tuple(moved))


def release_staging(utils, prepared):
    if prepared.facts.staging is not None:
        with contextlib.suppress(Exception):
            utils.free(prepared.facts.staging[0])


def show_layout(prepared, out=say):
    """The layout table, the framebuffer facts and strip decisions, the current top,
    the destination end and the chosen new top_of_kernel_data, then notes and
    problems. Hex and names only."""
    out("Chainload layout from the live target (hex addresses and sizes only):")
    for line in hv_chainload.layout_table(prepared.plan, prepared.facts,
                                          prepared.moved).splitlines():
        out(line)
    ba = prepared.state.ba
    for line in hv_chainload.video_report(ba.video):
        out(line)
    top_lines, top_notes = hv_chainload.top_report(prepared.plan, ba.top_of_kernel_data,
                                                   prepared.facts)
    for line in top_lines:
        out(line)
    for note in prepared.notes + top_notes:
        out("NOTE: " + note)
    for problem in prepared.problems:
        out("PROBLEM: " + problem)


def breadcrumb(iface, video, slot):
    """Paint one strip block (silently nothing when the framebuffer is ineligible)."""
    for address, row in hv_chainload.paint_rows(video, slot):
        iface.writemem(address, row)


def breadcrumb_status(video, control=False):
    """The "Breadcrumbs:" line. Uses the stub's own predicate (stub_paint), not video_ok().

    control: the stock boot021 build is being chainloaded; it paints no c-blocks.
    """
    mode = hv_chainload.strip_mode(video)
    if mode == "bar":
        if control:
            return ("Breadcrumbs: stub bar enabled. Host slots 0-2 show host progress but "
                    "boot021's own redraw may erase them before the handoff; the stub marks its "
                    "entry in slot 3, clears the strip and paints one bar over slots 0-4. "
                    "Control: " + CONTROL_SUCCESS + ".")
        steps = hv_chainload.m1n1_painted_steps(video)
        if steps == 0:
            return ("Breadcrumbs: stub bar enabled. Host slots 0-2 show host progress but "
                    "boot021's own redraw may erase them before the handoff; the stub marks its "
                    "entry in slot 3, clears the strip and paints one bar over slots 0-4; the new "
                    "m1n1 will NOT paint slots 5-20 (its stride/height ceilings reject this "
                    "geometry).")
        if steps < hv_chainload.M1N1_STEPS:
            return ("Breadcrumbs: stub bar enabled. Host slots 0-2 show host progress but "
                    "boot021's own redraw may erase them before the handoff; the stub marks its "
                    "entry in slot 3, clears the strip and paints one bar over slots 0-4; the new "
                    "m1n1 paints only c0-c8 (slots 5-13): the framebuffer base is not 16K "
                    "aligned, so it cannot map it once the MMU is on and c9-c15 (slots 14-20) "
                    "will not paint.")
        return ("Breadcrumbs: stub bar enabled. Host slots 0-2 show host progress but "
                "boot021's own redraw may erase them before the handoff; the stub marks its "
                "entry in slot 3, clears the strip and paints one bar over slots 0-4; the new "
                "m1n1 paints slots 5-20.")
    if mode == "host":
        if control:
            return ("Breadcrumbs: the copy stub will NOT paint (row stride is not 4-byte aligned): "
                    "no bar. Host slots 0-2 may be erased by boot021's own redraw. Control: the "
                    "stock build paints no c-blocks, so nothing on the screen can show success; "
                    "only the USB port returning and the new-instance proof can.")
        return ("Breadcrumbs: the copy stub will NOT paint (row stride is not 4-byte aligned): no "
                "bar, and the new m1n1 will not paint either (its guard rejects the same stride). "
                "Host slots 0-2 may be erased by boot021's own redraw; the screen may show no "
                "progress at all.")
    return ("Breadcrumbs: framebuffer geometry not eligible; the copy stub will NOT paint, the new "
            "m1n1 will not paint either (same limits) and the strip is disabled.")


def announce_handoff(video, out=say, control=False):
    """What the human should see on the screen; same predicate as the stub itself."""
    if hv_chainload.stub_paint(video) is not None:
        stub_part = ("Handoff. Screen strip: the copy stub marks its entry in slot 3, then clears "
                     "the strip and paints ONE bar over slots 0-4 (host slots 0-2 may already have "
                     "been erased by boot021's redraw; slot 3 alone means the stub was entered but "
                     "its copy or paint did not finish; the bar proves host steps 0-2 and the copy "
                     "finished)")
        if control:
            out(stub_part + ". Control: " + CONTROL_SUCCESS + ".")
        elif hv_chainload.m1n1_painted_steps(video) == 0:
            out(stub_part + "; the new m1n1 will NOT paint (its stride/height ceilings reject "
                "this geometry), so success on the screen is the bar only, plus the USB port "
                "returning and the new-instance proof.")
        elif hv_chainload.m1n1_painted_steps(video) < hv_chainload.M1N1_STEPS:
            out(stub_part + ", then the new m1n1 lights slots 5-13 (steps c0-c8 only: the "
                "framebuffer base is not 16K aligned, so c9-c15, slots 14-20, cannot paint). "
                "Success = bar (slots 0-4) + all of 5-13 lit; the lit prefix after the bar names "
                "the last completed step among c0-c8.")
        else:
            out(stub_part + ", then the new m1n1 lights slots 5-20 (steps c0-c15). Success = bar "
                "(slots 0-4) + all of 5-20 lit; the lit prefix after the bar names the last "
                "completed step.")
    elif control:
        out("Handoff. The copy stub will NOT paint (framebuffer not eligible for the stub): no "
            "bar. Do not read slots 0-4; the stock build paints no c-blocks, so the screen cannot "
            "show success: only the USB port returning and the new-instance proof can.")
    else:
        out("Handoff. The copy stub will NOT paint (framebuffer not eligible for the stub): no "
            "bar, and the new m1n1 will not paint either (same geometry limits). Do not read "
            "slots 0-20; the screen cannot show progress: only the USB port returning and the "
            "new-instance proof can show success.")


def python_plan(utils, image_len, new_base, blob_api):
    """Layout of the six-blob Python flow, decided by m1n1.bootmem."""
    names, find_boot_blobs, _, _ = blob_api
    props = utils.adt["chosen"]["memory-map"]._properties
    blobs, end = find_boot_blobs(props, names, align_up(image_len + 4, 0x4000))
    sepfw_off = next((off for name, _, _, off in blobs if name == "SEPFW"), 0)
    plan = hv_chainload.plan_with_blobs(image_len, new_base, props.get("SEPFW"), sepfw_off,
                                        end, end + 0x4000)
    return plan, blobs


def layout_report(iface, proxy, utils, image_len, mode="intree", blob_api=None, out=say):
    """--layout-only: facts, plan, gates and a table. No memory writes; True on PASS.

    ProxyUtils (built by the caller) issues two m1n1 heap-bookkeeping requests,
    heapblock_alloc(0) and heapblock_set_limit; nothing here writes memory, and
    the staging block is host-side bookkeeping that is released again.
    """
    state = read_target_state(iface, proxy, utils)
    if mode == "python":
        plan, blobs = python_plan(utils, image_len, utils.base, blob_api)
        moved = tuple(name for name, _, _, _ in blobs)
    else:
        plan = hv_chainload.plan_layout(image_len, utils.base, state.memory_map.get("SEPFW"))
        moved = ("SEPFW",)
    prepared = gate_layout(utils, state, plan, moved, plan.image_size + hv_chainload.STUB_MAX)
    release_staging(utils, prepared)
    show_layout(prepared, out)
    return not prepared.problems


def require_gates(utils, prepared):
    if prepared.problems:
        release_staging(utils, prepared)
        hint = ""
        # Only the planned-address signature is a problem (hv_chainload.check_layout):
        # a live boot_args that merely lies inside the destination is a NOTE.
        if any(p.startswith("destination overlaps the boot_args at the planned")
               for p in prepared.problems):
            hint = (" (a second chainload in the same power cycle looks like this: power off "
                    "completely and start again from the original instance)")
        raise ValueError("layout gate FAILED, nothing was written: " +
                         "; ".join(prepared.problems) + hint)


def verify_readback(iface, address, want, what):
    if iface.readmem(address, len(want)) != want:
        raise ValueError("%s read back differently from what was written" % what)


def plan_adt_patch(state, plan):
    """(value, offset, old, patched): the 16-byte SEPFW value patch, validated, nothing written.

    Pure computation on the raw ADT already read from the target; every check
    that can refuse runs here, before the first write to the target.
    """
    sepfw_addr, sepfw_size = plan.sepfw
    value = struct.pack("<QQ", plan.sepfw_address, sepfw_size)
    patched, offset, old = adt_patch.patch_value(state.raw_adt, "/chosen/memory-map",
                                                 "SEPFW", value)
    if old != struct.pack("<QQ", sepfw_addr, sepfw_size):
        raise ValueError("ADT SEPFW value differs from the memory map entry")
    if (patched[:offset] != state.raw_adt[:offset] or
            patched[offset + 16:] != state.raw_adt[offset + 16:]):
        raise ValueError("ADT patch touched bytes outside the SEPFW value")
    return value, offset, old, patched


class LiveAdtMismatch(ValueError):
    """The live ADT did not read back as written."""


def restore_live_adt(iface, proxy, state, restore):
    """Best effort: write the original bytes back and verify the WHOLE ADT against the original.

    restore is (address, bytes). True only when the write, the full readback
    and the cache clean all succeeded; any ordinary failure (including a dead
    port) returns False so the caller can state the outcome. An interruption
    (BaseException that is not an Exception) propagates; commit_live_adt()
    reports it.
    """
    address, data = restore
    try:
        iface.writemem(address, data)
        if iface.readmem(state.adt_addr, len(state.raw_adt)) != state.raw_adt:
            return False
        proxy.dc_cvau(address, len(data))
    except Exception:
        return False
    return True


def issue_reload(proxy, args, out=say, entered=None):
    """proxy.reload(*args) with a policy for a port that does not come back by itself.

    reload() blocks in wait_boot() (15 s read timeout plus 200 reopen attempts
    of the SAME device path) and raises UartTimeout when the port does not
    return; the descriptor-checked reconnect (which also accepts another
    callout path) is the caller's next step, so any ordinary failure only
    prints one sanitized line. The global alarm's TimeoutError passes through.
    entered, when given, receives a True immediately before reload() is
    called: from then on the handoff may have happened (see commit_live_adt()).
    """
    if entered is not None:
        entered.append(True)
    try:
        proxy.reload(*args)
    except TimeoutError:
        raise
    except Exception as exc:
        out(RELOAD_NO_PORT % type(exc).__name__)


def commit_live_adt(iface, proxy, state, write, want, clean, restore, reload_args=None,
                    out=say, what="", message=""):
    """The one change to live state AND everything up to proxy.reload, as ONE guarded region.

    write() is the live write; the ADT is read back against want and cleaned
    from the cache (clean is (address, size)); message is the single short
    print that follows; then issue_reload(reload_args) is called. reload_args
    None stops after the cache clean (the write alone).

    On ANY BaseException before reload() is entered (a mismatch, UartTimeout,
    the global alarm's TimeoutError, Ctrl-C, an interrupted print) the original
    bytes (restore is (address, bytes)) are written back and the WHOLE ADT is
    read back, and the outcome is stated: ADT_RESTORED or ADT_NOT_RESTORED,
    after the optional prefix what. An ordinary failure then becomes a
    ValueError carrying that outcome (and only the exception class name, never
    its text, which may embed a device path); TimeoutError and
    KeyboardInterrupt print the outcome and propagate unchanged. If the
    restore is itself interrupted, ADT_NOT_RESTORED is printed and that
    interruption propagates. Once reload() has been entered there is NO
    restore: the handoff may already have happened, and the old instance would
    be gone either way. Because write, verification, print and the call into
    reload share one try, no interruption can fall between them.
    """
    entered = []
    try:
        write()
        if iface.readmem(state.adt_addr, len(want)) != want:
            raise LiveAdtMismatch("live ADT read back differently from what was written")
        proxy.dc_cvau(*clean)
        if reload_args is not None:
            if message:
                out(message)
            issue_reload(proxy, reload_args, out, entered)
    except BaseException as exc:
        if entered:
            raise
        prefix = what + "; " if what else ""
        try:
            restored = restore_live_adt(iface, proxy, state, restore)
        except BaseException:
            out(prefix + ADT_NOT_RESTORED)
            raise
        outcome = ADT_RESTORED if restored else ADT_NOT_RESTORED
        if isinstance(exc, Exception) and not isinstance(exc, TimeoutError):
            reason = str(exc) if isinstance(exc, LiveAdtMismatch) else type(exc).__name__
            raise ValueError("%s%s (%s)" % (prefix, outcome, reason)) from None
        out(prefix + outcome)
        raise


def chainload_intree(iface, proxy, utils, hv_image, out=say, control=False):
    """What src/chainload.c does, driven from the host. Returns the Plan.

    Only SEPFW moves; its ADT property is patched in the raw ADT in place (16
    bytes); boot_args is the raw target copy with top_of_kernel_data changed
    to max(current, destination end), 16K aligned (hv_chainload module
    docstring). RVBARs are never written and push_adt() is never called.
    control: the image is the stock control build (handoff text only).

    Order: every gate and every pure check (including the stub's size and the
    copy length) runs before the first write. Then the image, SEPFW and
    boot_args copy are staged, read back and cache-cleaned, then the copy stub
    is written, read back and cache-maintained, then slot 2 is painted
    ("everything staged and verified"), the handoff text is printed, and ONLY
    THEN is the live ADT patched, read back and cleaned, then one short print
    and the call into proxy.reload follow, all under ONE try
    (commit_live_adt) that restores the original bytes and states the outcome
    on any failure, an interrupted print included. Once reload() is entered
    there is no restore. A failure anywhere earlier leaves the live ADT
    untouched. Breadcrumbs follow hv_chainload.py.
    """
    state = read_target_state(iface, proxy, utils)
    plan = hv_chainload.plan_layout(len(hv_image), utils.base, state.memory_map.get("SEPFW"))
    prepared = gate_layout(utils, state, plan, ("SEPFW",),
                           plan.image_size + hv_chainload.STUB_MAX)
    show_layout(prepared, out)
    require_gates(utils, prepared)
    out(LAYOUT_GATE_PASS)
    video = state.ba.video
    paint = hv_chainload.stub_paint(video)
    out(breadcrumb_status(video, control))
    staging = prepared.facts.staging[0]
    new_base, entry = plan.new_base, plan.entry
    sepfw_addr, sepfw_size = plan.sepfw
    adt_value, adt_offset, adt_old, adt_patched = plan_adt_patch(state, plan)
    new_top = hv_chainload.new_top_of_kernel_data(plan, state.ba.top_of_kernel_data)
    new_args = hv_chainload.with_top_of_kernel_data(state.raw_ba, new_top)
    code = hv_chainload.check_stub_size(stub(entry, paint))
    hv_chainload.check_copy_length(plan.image_size)
    breadcrumb(iface, video, hv_chainload.SLOT_HOST_GATE)

    # Stage everything in the proxy heap; the live system is still untouched.
    image = hv_image + b"\0\0\0\0"
    utils.compressed_writemem(staging, image, True)
    proxy.memcpy8(staging + plan.sepfw_off, sepfw_addr, sepfw_size)
    iface.writemem(staging + plan.bootargs_off, new_args)
    verify_readback(iface, staging, image, "staged image")
    if iface.readmem(staging + plan.sepfw_off, sepfw_size) != iface.readmem(sepfw_addr, sepfw_size):
        raise ValueError("staged SEPFW read back differently from its source")
    verify_readback(iface, staging + plan.bootargs_off, new_args, "staged boot_args")
    for address, size in ((staging, len(image)), (staging + plan.sepfw_off, sepfw_size),
                          (staging + plan.bootargs_off, hv_chainload.BOOT_ARGS_LEN)):
        proxy.dc_cvau(address, size)
    out("Staged and verified: image, SEPFW and boot_args copy.")

    stub_addr = staging + plan.image_size
    iface.writemem(stub_addr, code)
    verify_readback(iface, stub_addr, code, "copy stub")
    proxy.dc_cvau(stub_addr, len(code))
    proxy.ic_ivau(stub_addr, len(code))
    out("Copy stub written and verified (%d bytes, 8-byte aligned literal pool)." % len(code))
    breadcrumb(iface, video, hv_chainload.SLOT_HOST_STAGED)

    # Slot 2 and ALL host-only text BEFORE the live write, so that the window
    # between the verified patch and the reload request holds as little as possible.
    breadcrumb(iface, video, hv_chainload.SLOT_HOST_HANDOFF)
    out("Everything staged and verified; patching the live ADT (SEPFW, 16 bytes) and handing off.")
    announce_handoff(video, out, control)
    reload_args = (stub_addr, plan.bootargs_address, staging, new_base, plan.image_size)
    live = state.adt_addr + adt_offset
    # The one change to live state (the 16 SEPFW value bytes of the raw ADT) and, in the same
    # guarded region, the one short print and the call into reload(). reload() waits for the
    # new m1n1 and reopens the port if USB re-enumerates.
    commit_live_adt(iface, proxy, state, lambda: iface.writemem(live, adt_value), adt_patched,
                    (live, 16), (live, adt_old), reload_args, out,
                    message="Live ADT patched (SEPFW, 16 bytes) and verified; handing off.")
    return plan


def chainload_python(iface, proxy, utils, hv_image, blob_api, bootargs_types, out=say,
                     control=False):
    """upstream chainload.py -r: six blobs moved, whole ADT rebuilt and pushed. Returns the Plan.

    RVBARs are never written; upstream also skips them here, because a raw
    image entering at base + 0x800 keeps the current page-aligned base. The
    layout gate, the aligned (optionally painting) stub and top_of_kernel_data
    = max(current, destination end) are shared with the in-tree mode, and so
    is the order: every pure check (stub size, copy length, the rebuilt ADT
    fitting the live ADT's size) runs before the first write, the rebuilt ADT
    is pushed LAST under commit_live_adt (read back, restored and the outcome
    stated on failure), after the stub is written and cache-maintained, slot 2
    painted and the handoff text printed, immediately before proxy.reload (the
    write, one short print and the call into reload() share one guarded
    region, commit_live_adt). The host paints slots 0 and 2 only, since this
    flow does not read its staged data back.
    """
    image = hv_image + b"\0\0\0\0"
    new_base = utils.base
    entry = new_base + hv_chainload.ENTRY_OFFSET
    _, _, copy_boot_blobs, blob_type = blob_api
    state = read_target_state(iface, proxy, utils)
    plan, blobs = python_plan(utils, len(hv_image), new_base, blob_api)
    prepared = gate_layout(utils, state, plan, tuple(name for name, _, _, _ in blobs),
                           plan.image_size + hv_chainload.STUB_MAX)
    show_layout(prepared, out)
    require_gates(utils, prepared)
    out(LAYOUT_GATE_PASS)
    video = state.ba.video
    out(breadcrumb_status(video, control))
    bootargs_off, image_size = plan.bootargs_off, plan.image_size
    image_addr = prepared.facts.staging[0]
    code = hv_chainload.check_stub_size(stub(entry, hv_chainload.stub_paint(video)))
    hv_chainload.check_copy_length(image_size)
    # Host-side only until the first write: edit the ADT model, rebuild it and
    # refuse a rebuilt ADT that does not fit where the live one is.
    mm = utils.adt["chosen"]["memory-map"]
    for name, _, size, off in blobs:
        mm._properties[name] = (new_base + off, size)
        mm._types[name] = blob_type
    mm.BootArgs = (new_base + bootargs_off, 0x4000)
    built = utils.adt.build()
    if len(built) > state.ba.devtree_size:
        raise ValueError("rebuilt ADT (0x%x bytes) is larger than the live ADT (0x%x bytes); "
                         "nothing was written" % (len(built), state.ba.devtree_size))
    tba = utils.ba.copy()
    tba.top_of_kernel_data = hv_chainload.new_top_of_kernel_data(plan, state.ba.top_of_kernel_data)
    breadcrumb(iface, video, hv_chainload.SLOT_HOST_GATE)
    copy_boot_blobs(proxy, [(n, s, z, image_addr + o) for n, s, z, o in blobs])
    utils.compressed_writemem(image_addr, image, True)
    proxy.dc_cvau(image_addr, len(image))
    iface.writemem(image_addr + bootargs_off, bootargs_types[tba.revision].build(tba))
    stub_addr = image_addr + image_size
    iface.writemem(stub_addr, code)
    proxy.dc_cvau(stub_addr, len(code))
    proxy.ic_ivau(stub_addr, len(code))
    # Slot 2 and ALL host-only text BEFORE the live write (see chainload_intree).
    breadcrumb(iface, video, hv_chainload.SLOT_HOST_HANDOFF)
    out("Everything staged; pushing the rebuilt ADT (0x%x bytes) and handing off." % len(built))
    announce_handoff(video, out, control)
    reload_args = (stub_addr, plan.bootargs_address, image_addr, new_base, image_size)
    # The live ADT write, last before the handoff, with the short print and the call into
    # reload() (which waits for the new m1n1 and reopens the port) in the same guarded region.
    commit_live_adt(iface, proxy, state, utils.push_adt, built, (state.adt_addr, len(built)),
                    (state.adt_addr, state.raw_adt), reload_args, out,
                    what="python mode rewrote the whole ADT",
                    message="Live ADT rewritten and verified; handing off.")
    return plan


def prepare_guest(iface, proxy, utils, files, hv_files, m):
    """Gates and DT preparation on the running hv m1n1; returns the layout."""
    try:
        compatible = utils.adt.compatible
    except (KeyError, AttributeError):
        raise ValueError("target ADT root compatibility unavailable") from None
    if not isinstance(compatible, (list, tuple)) or "J716cAP" not in compatible:
        raise ValueError("target board is not J716c")
    if not utils.ba.video.base or not utils.ba.video.width or not utils.ba.video.height:
        raise ValueError("m1n1 has no boot framebuffer")
    gpio_guard.check_adt(utils.adt)
    print("GPIO ADT PASS: 221 pins/7 groups; exclusions 5,6,7,112,141.", flush=True)
    base = utils.base
    with hv_dapf_pin(hv_files["m1n1-hv.bin"]):
        dapf_plan = dapf_guard.prepare(iface, base, hv_files["m1n1-hv.bin"], utils.adt)
    image, dtb = files["Image"], files["t6050-j716c-stage-b.dtb"]
    initrd = files["initramfs-stage-b.cpio.gz"]
    mem_top = utils.ba.phys_base + utils.ba.mem_size
    layout = guest_layout(utils.heap_top, mem_top, image, len(initrd), 256 * 1024)
    dt_src = utils.memalign(65536, len(dtb))
    print("Uploading DT, initramfs and kernel to guest RAM.", flush=True)
    iface.writemem(dt_src, dtb)
    iface.writemem(layout["initrd"], initrd)
    iface.writemem(layout["kernel"], image)
    proxy.kboot_set_chosen("bootargs", HV_BOOTARGS)
    proxy.kboot_set_initrd(layout["initrd"], len(initrd))
    if proxy.kboot_prepare_dt(dt_src) != 0:
        raise ValueError("m1n1 DT preparation failed")
    prepared = proxy.read64(base + m["hv_dt_pointer_offset"])
    if not prepared:
        raise ValueError("m1n1 returned no prepared DT")
    magic, total = struct.unpack(">II", iface.readmem(prepared, 8))
    if magic != 0xD00DFEED or not 40 <= total <= 256 * 1024:
        raise ValueError("invalid prepared DT size")
    blob = restrict_memory(iface.readmem(prepared, total), layout["base"])
    tree = check_stage_b(blob, prepared=True)
    args = tree.get("/chosen", {}).get("bootargs", b"").rstrip(b"\0").decode("ascii").split()
    if args[:len(HV_BOOTARGS.split())] != HV_BOOTARGS.split():
        raise ValueError("prepared DT bootargs differ from fixed hv arguments")
    if any(a not in ("idle=nop", "arm64.nowfxt") for a in args[len(HV_BOOTARGS.split()):]):
        raise ValueError("unexpected appended bootargs")
    check_payload_overlap(tree, layout)
    print("Hardware DT PASS; Linux RAM starts above the hypervisor.", flush=True)
    descriptor = entry_guard.plan(image, tree)
    iface.writemem(layout["dt"], blob)
    launch.ensure_no_secondaries(proxy)
    dapf_guard.apply(iface, dapf_plan)
    print("DAPF RAM table corrected (absent AOP DAPF omitted).", flush=True)
    if proxy.request(P_ILINUX_KBOOT_PREPARE_HV_GUEST) != 0:
        raise ValueError("hv guest hardware preparation failed")
    print("Clocks, tunables, cache and DAPF prepared (no USB/PCIe init).", flush=True)
    entry_guard.apply(iface, layout["kernel"], descriptor)
    for addr, data in ((layout["kernel"], image), (layout["dt"], blob), (layout["initrd"], initrd)):
        proxy.dc_cvau(addr, len(data))
    proxy.ic_ivau(layout["kernel"], len(image))
    return layout


def map_guest(hv, utils, layout, irange, trace_off):
    """Identity-map RAM outside m1n1 and its heap, as HV.load_raw() does."""
    phys_base = utils.heap_top
    ram_base = phys_base & ~0xFFFFFFFF
    hv.phys_base, hv.ram_base, hv.ram_size = phys_base, ram_base, utils.ba.mem_size_actual
    hv.add_tracer(irange(ram_base, utils.ba.phys_base - ram_base), "RAM-LOW", trace_off)
    hv.add_tracer(irange(phys_base, utils.ba.mem_size_actual - phys_base + ram_base),
                  "RAM-HIGH", trace_off)
    hv.unmap_carveouts()
    if not phys_base < layout["base"]:
        raise ValueError("guest base overlaps the hypervisor")


def hook_cpu_start(hv, irange, reserved):
    """Drop guest CPU_START writes: t6050 secondaries must not start.

    The RESERVED tracer (as upstream) keeps pt_update() from replacing the
    hook with plain passthrough of the surrounding PMGR range.
    """
    addr = hv.adt["/arm-io/pmgr"].get_reg(0)[0] + CPU_START_T6050

    def write(base, off, data, width):
        hv.log(f"CPU_START write dropped: +{off:#x} = {data:#x}")

    hv.map_hook(addr, 0x20, write=write)
    hv.add_tracer(irange(addr, 0x20), "CPU_START", reserved)


def start_guest(hv, proxy, iface, entry, dt, iodev_cls):
    """HV.start() for a Linux Image: no ADT upload, no SPRR, x0 = DT."""
    for iodev in iodev_cls:
        if iodev != hv.iodev:
            proxy.iodev_set_usage(iodev, 0)
    hv.map_essential()
    hv.pt_update()
    proxy.fb_shutdown(False)
    hv.entry = entry
    iface.dev.timeout = None
    hv.default_sigint = signal.signal(signal.SIGINT, hv._handle_sigint)
    hv.started = True
    for cpu_node in list(hv.adt["cpus"]):
        if cpu_node.state == "running":
            break
    hv.started_cpus[cpu_node.cpu_id] = (getattr(cpu_node, "die_id", 0),
                                        cpu_node.cluster_id, cpu_node.cpu_id)
    hv.sysreg[cpu_node.cpu_id] = {}
    print("Starting EL1 guest; Ctrl-C enters the HV shell.", flush=True)
    proxy.hv_start(entry, dt)
    # hv_start returns only if the HV refused to start or the guest exited.


def open_primary(device):
    """Open the descriptor-verified primary callout: (transport, interface).

    The target's console text is discarded (tty_enable off, as launch.py and
    census.py do): it carries the device serial number (kboot's 'reporting
    device serial number' line) and the new m1n1's banner, and would otherwise
    be echoed to the terminal and into --log. This is the only opener, so the
    first open and every reconnect are covered. Errors name only the exception
    class: a callout path embeds the serial number. TimeoutError (the global
    alarm) passes through untouched.
    """
    from m1n1.proxy import UartInterface, Serial
    try:
        selected = usb_identity.select_primary(usb_identity.discover(), device)
    except TimeoutError:
        raise
    except Exception as exc:
        raise ValueError("USB identity check failed (%s); no port opened"
                         % type(exc).__name__) from None
    transport = None
    try:
        transport = Serial(selected, UartInterface.DEFAULT_BAUD_RATE)
        iface = UartInterface(device=transport)
        iface.tty_enable = False
        iface.dev.timeout = 15
    except BaseException as exc:
        if transport is not None:
            with contextlib.suppress(Exception):
                transport.close()
        if isinstance(exc, Exception) and not isinstance(exc, TimeoutError):
            raise RuntimeError("USB transport failed (%s); do not automatically retry"
                               % type(exc).__name__) from None
        raise
    return transport, iface


def close_quietly(transport):
    """Close a port that may already be closed; only the global alarm propagates."""
    try:
        transport.close()
    except TimeoutError:
        raise
    except Exception:
        pass


def reconnect(device, make_proxy, wait=30.0, opener=None, sleep=time.sleep, clock=time.monotonic):
    """Reopen the descriptor-checked primary port and prove it with a NOP."""
    opener = opener or open_primary
    deadline = clock() + wait
    while True:
        transport = None
        try:
            transport, iface = opener(device)
            proxy = make_proxy(iface)
            proxy.nop()
            return transport, iface, proxy
        except TimeoutError:
            raise
        except Exception:
            if transport is not None:
                with contextlib.suppress(Exception):
                    transport.close()
            if clock() > deadline:
                raise ValueError("m1n1 did not answer after chainload; POWER OFF completely and "
                                 "read the strip per hv-instructions.md") from None
            sleep(0.5)


def prove_new_instance(proxy, plan, old_bootargs, out=say):
    """Require that the answering m1n1 is the NEW instance, not the original one.

    The stub hands the new m1n1 the boot_args copy this launcher staged at
    new_base + bootargs_off, and m1n1 reports that pointer as P_GET_BOOTARGS.
    The original instance reports iBoot's pointer. The version marker cannot
    tell them apart for --control stock (same object), and a chainload that
    silently did not happen would leave the old instance answering.
    """
    want = plan.new_base + plan.bootargs_off
    if want == old_bootargs:
        raise ValueError("new-instance proof impossible: the staged boot_args copy (0x%x) is at "
                         "the original boot_args address; power off" % want)
    got = proxy.get_bootargs()
    if got == want:
        out("New-instance proof PASS: boot_args pointer 0x%x is the copy staged by this chainload."
            % got)
        return
    if got == old_bootargs:
        raise ValueError(
            "new-instance proof FAILED: boot_args pointer 0x%x is still the original instance's "
            "(expected 0x%x); the chainload did not take effect or the old m1n1 still answers; "
            "power off" % (got, want))
    raise ValueError("new-instance proof FAILED: boot_args pointer 0x%x, expected the staged copy "
                     "at 0x%x; power off" % (got, want))


def check_control(guest_manifest, boot_manifest, m1n1_bin):
    """The stock control image must be the installed boot021 object.

    Marker and offset must equal the repository's current package manifest
    (the installed object is the same in every package), and so must the
    SHA-256 of the m1n1.bin bytes that would be chainloaded. Fails closed when
    that digest is not recorded.
    """
    for key in ("m1n1_version_marker", "m1n1_version_offset"):
        if guest_manifest.get(key) != boot_manifest.get(key):
            raise ValueError("guest package m1n1.bin is not the installed boot021 object")
    recorded = ((boot_manifest.get("files") or {}).get("m1n1.bin") or {}).get("sha256")
    if not isinstance(recorded, str) or not HEX_DIGEST.fullmatch(recorded):
        raise ValueError("installed boot021 m1n1.bin digest is not recorded in the package "
                         "manifest; refusing the control")
    if hashlib.sha256(bytes(m1n1_bin)).hexdigest() != recorded:
        raise ValueError("guest package m1n1.bin digest differs from the installed boot021 object")


def run_live(device, files, hv_files, m, logfile, symbols, api, guest_manifest=None,
             mode="intree", layout_only=False, chainload_only=False, control=None):
    """Live session; api carries the m1n1 client classes (injected by tests)."""
    def timeout(*_):
        raise TimeoutError("preflight exceeded 300 seconds; do not automatically retry")

    old = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    transport = None
    log_handle = None
    try:
        transport, iface = api.opener(device)
        proxy = api.M1N1Proxy(iface)
        boot_m = json.loads((BOOT / "package-manifest.json").read_text())
        check_target(iface, proxy, proxy.get_base(), boot_m["m1n1_version_marker"],
                     boot_m["m1n1_version_offset"])
        print("Target PASS: t6050, installed boot021, no started secondaries.", flush=True)
        utils = api.ProxyUtils(proxy)
        image = files["m1n1.bin"] if control else hv_files["m1n1-hv.bin"]
        if layout_only:
            print("Layout check only: " + LAYOUT_ONLY_NOTE + ".", flush=True)
            ok = layout_report(iface, proxy, utils, len(image), mode, api.blob_api)
            if ok:
                print("LAYOUT PASS: the planned chainload region clears the ADT and framebuffer "
                      "(any staging overlap is below the stub and the copy is ascending), the "
                      "staging block starts at or above top_of_kernel_data and clears the source "
                      "blobs being moved, and no earlier chainload is detected; read the NOTES "
                      "for blobs and the live boot_args it would overwrite.", flush=True)
                return EXIT_LAYOUT_PASS
            print("LAYOUT FAIL: no memory was written to the target.", flush=True)
            return EXIT_LAYOUT_FAIL
        register_preflight(utils, (api.ProxyError,))
        print("Register preflight PASS: ECV present; HV start/exception/FIQ registers readable.",
              flush=True)
        if logfile and not chainload_only:
            # Created BEFORE the first target write, so that a failure here (the path appeared,
            # the disk is full, the permissions changed after main() checked them) stops the
            # session while nothing has happened to the target. 'x': never truncate evidence.
            log_handle = logfile.open("x")
        if control:
            label = "stock boot021"
            want_marker = guest_manifest["m1n1_version_marker"]
            want_offset = guest_manifest["m1n1_version_offset"]
            print("Control: chainloading the guest package's stock boot021 m1n1.bin "
                  "(still painting the strip).", flush=True)
            print(CONTROL_NOTE, flush=True)
        else:
            label = m["hv_version_marker"].rsplit("-", 1)[-1]
            want_marker, want_offset = m["hv_version_marker"], m["hv_version_offset"]
        print("Chainload mode: %s." % ("in-tree (SEPFW only, ADT patched in place)"
                                       if mode == "intree" else "python (six blobs, ADT rebuilt)"),
              flush=True)
        old_bootargs = proxy.get_bootargs()   # the original instance's boot_args pointer
        if mode == "intree":
            plan = chainload_intree(iface, proxy, utils, image, control=bool(control))
        else:
            plan = chainload_python(iface, proxy, utils, image, api.blob_api, api.bootargs_types,
                                    control=bool(control))
        print("Chainloaded %s into RAM; re-verifying the port." % label, flush=True)
        close_quietly(transport)
        transport, iface, proxy = reconnect(device, api.M1N1Proxy, opener=api.opener)
        prove_new_instance(proxy, plan, old_bootargs)
        check_target(iface, proxy, proxy.get_base(), want_marker, want_offset)
        print("Target PASS: %s running, no started secondaries." % label, flush=True)
        if chainload_only:
            if control:
                detail = ("stock marker verified; the hypervisor flags are only checked on the "
                          "full path after hv.init() (the stock build has none); power-cycle "
                          "before the next chainload run")
            else:
                detail = ("marker verified; the hypervisor flags (single-CPU, ECV timer traps) are "
                          "NOT checked here, only on the full path after hv.init()")
            print("CHAINLOAD PASS: %s answered after the chainload, new instance proven; %s; "
                  "the HV was not started." % (label, detail), flush=True)
            return 0
        utils = api.ProxyUtils(proxy, heap_size=128 * MIB, m1n1_heap=128 * MIB)
        hv = api.HV(iface, proxy, utils)
        hv.emulate_sprr = False
        hv.init()
        check_hv_flags(proxy, utils.base, m)
        print("HV PASS: single-CPU mode, ECV timer traps on; guest timers masked at source.",
              flush=True)
        if log_handle is not None:
            hv.set_logfile(log_handle)
        hv.load_system_map(str(symbols))
        layout = prepare_guest(iface, proxy, utils, files, hv_files, m)
        map_guest(hv, utils, layout, api.irange, api.TraceMode.OFF)
        hook_cpu_start(hv, api.irange, api.TraceMode.RESERVED)
        signal.alarm(0)
        start_guest(hv, proxy, iface, layout["kernel"], layout["dt"], api.IODEV)
        print("STOP: hv_start returned (HV refused start or guest exited).", flush=True)
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
        if transport is not None:
            with contextlib.suppress(OSError):
                transport.close()
        if log_handle is not None:
            with contextlib.suppress(Exception):
                log_handle.close()


def connect_and_run(device, m1n1, files, hv_files, m, logfile, symbols, **options):
    pin = subprocess.check_output(["git", "-C", str(m1n1), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(m1n1), "status", "--porcelain",
                                     "--untracked-files=no"], text=True)
    if pin != launch.M1N1_COMMIT or dirty:
        raise ValueError("client must be the clean pinned m1n1 checkout")
    sys.path.insert(0, str(m1n1 / "proxyclient"))
    from m1n1.proxy import M1N1Proxy, IODEV, ProxyError
    from m1n1.proxyutils import ProxyUtils
    from m1n1.bootmem import BOOT_BLOBS, find_boot_blobs, copy_boot_blobs
    from m1n1.tgtypes import BootArgs_r1, BootArgs_r2, BootArgs_r3
    from m1n1.hv import HV
    from m1n1.hv.types import TraceMode
    from m1n1.utils import irange
    from construct import Array, Int64ul

    api = SimpleNamespace(
        opener=open_primary, M1N1Proxy=M1N1Proxy, ProxyUtils=ProxyUtils, ProxyError=ProxyError,
        HV=HV, TraceMode=TraceMode, IODEV=IODEV, irange=irange,
        blob_api=(BOOT_BLOBS, find_boot_blobs, copy_boot_blobs, (Array(2, Int64ul), False)),
        bootargs_types={0: BootArgs_r1, 1: BootArgs_r1, 2: BootArgs_r2, 3: BootArgs_r3})
    return run_live(device, files, hv_files, m, logfile, symbols, api, **options)


def log_path_problem(path):
    """Why a --log path cannot work, or None. Runs at argument time.

    The log is created with mode 'x' only after the handoff and hv.init(), when
    nothing can be undone, so every deterministic reason it would fail has to be
    refused up front: the path exists (any kind of entry, a dangling symlink
    included), or its parent directory is missing, is not a directory or cannot
    be written to, or the file name is longer than the filesystem allows.
    """
    if os.path.lexists(path):
        return "log file exists; choose a new name"
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.exists(parent):
        return "log directory does not exist; choose a path in an existing directory"
    if not os.path.isdir(parent):
        return "log path's parent is not a directory; choose a path in an existing directory"
    if not os.access(parent, os.W_OK | os.X_OK):
        return "log directory is not writable; choose a path in a writable directory"
    try:
        name_max = os.pathconf(parent, "PC_NAME_MAX")
    except (AttributeError, OSError, ValueError):
        name_max = 0
    name = os.fsencode(os.path.basename(os.path.abspath(path)))
    if len(name) > (name_max if name_max > 0 else 255):
        return "log file name is too long; choose a shorter name"
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True, help="boot033/boot034 guest package")
    parser.add_argument("--hv-package", type=Path, required=True, help="hv m1n1 package")
    parser.add_argument("--launch", action="store_true",
                        help="LIVE RAM boot under the HV; requires separate user authorization")
    parser.add_argument("--device", help="auto, or the exact descriptor-verified primary callout")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--log", type=Path,
                        help="HV event log (keep local; ignored path). Applies to the FULL run "
                             "only (--layout-only and --chainload-only write no log). Created "
                             "exclusively: an existing file is refused, choose a new name; a "
                             "missing or unwritable directory is refused at once, because the "
                             "log is only opened after the handoff")
    parser.add_argument("--m1n1", type=Path, default=HERE.parents[1] / "third_party/m1n1")
    parser.add_argument("--chainload-mode", choices=("intree", "python"), default=None,
                        help="intree (default): SEPFW only, ADT patched in place; "
                             "python: six blobs, ADT rebuilt and pushed (the original hv flow)")
    parser.add_argument("--layout-only", action="store_true",
                        help="LIVE: print the layout gates and exit 0 (PASS) or 3 (FAIL; 2 is "
                             "an argument error); "
                             + LAYOUT_ONLY_NOTE)
    parser.add_argument("--chainload-only", action="store_true",
                        help="LIVE: chainload, verify the marker, stop; the HV is not started")
    parser.add_argument("--control", choices=("stock",), default=None,
                        help="with --chainload-only: chainload the guest package's stock "
                             "boot021 m1n1.bin (digest-checked against the installed object) "
                             "instead of the hv build (the stub still paints its bar; the stock "
                             "build paints no c-blocks; power-cycle between control runs)")
    args = parser.parse_args(argv)
    if args.launch and (args.confirm != CONFIRM or args.device is None):
        parser.error("live launch requires --device and --confirm " + CONFIRM)
    if not args.launch and (args.device is not None or args.confirm):
        parser.error("offline mode does not accept device/confirmation arguments")
    if args.layout_only and args.chainload_only:
        parser.error("--layout-only and --chainload-only are mutually exclusive")
    if args.control and not args.chainload_only:
        parser.error("--control is only valid with --chainload-only")
    if not args.launch and (args.layout_only or args.chainload_only or args.chainload_mode):
        parser.error("--layout-only, --chainload-only and --chainload-mode are live options; "
                     "they need --launch")
    if args.log is not None:
        problem = log_path_problem(args.log)
        if problem:
            parser.error(problem)
    mode = args.chainload_mode or "intree"
    guest_manifest, files = verify_guest_package(args.package)
    m, hv_files = verify_hv_package(args.hv_package, files["Image"],
                                    guest_package=guest_manifest.get("package"))
    map_name, _ = system_map_name(m, files["Image"])
    if args.control:
        check_control(guest_manifest, json.loads((BOOT / "package-manifest.json").read_text()),
                      files["m1n1.bin"])
    guest_label = str(guest_manifest.get("package", "guest")).rsplit("-", 1)[-1]
    print("Package PASS: %s guest and %s m1n1 match their manifests."
          % (guest_label, m["hv_version_marker"].rsplit("-", 1)[-1]))
    if not args.launch:
        print("Mode: OFFLINE ONLY; USB not opened")
    elif args.layout_only:
        print("Mode: LIVE LAYOUT CHECK; " + LAYOUT_ONLY_NOTE)
    elif args.chainload_only:
        print("Mode: LIVE CHAINLOAD ONLY (%s); the HV is not started"
              % ("stock boot021 control" if args.control else "hv m1n1"))
        if args.control:
            print(CONTROL_NOTE)
    else:
        print("Mode: LIVE HV RAM LAUNCH")
    print("Boot arguments:", HV_BOOTARGS)
    if args.log is not None and (args.layout_only or args.chainload_only):
        print("Note: --log applies to the full run only; nothing is logged in this mode.")
    if args.launch:
        return connect_and_run(args.device, args.m1n1, files, hv_files, m, args.log,
                               args.hv_package / map_name, guest_manifest=guest_manifest,
                               mode=mode, layout_only=args.layout_only,
                               chainload_only=args.chainload_only, control=args.control)
    return 0


def scrub(text):
    """text with any /dev/cu.* or /dev/tty.* callout path (it embeds the serial) removed."""
    return DEVICE_PATH.sub("<device>", str(text))


def stop_line(exc):
    """The final one-line report of an escaped exception, free of device paths."""
    text = " ".join(scrub(exc).split())          # one line, whatever the text carries
    return "STOP: %s%s" % (type(exc).__name__, " " + text if text else "")


def cli(argv=None):
    """main() as a process: whatever escapes becomes ONE scrubbed STOP line on stderr.

    An Exception exits 1 and Ctrl-C exits 130. Any other BaseException except
    SystemExit (argparse errors, sys.exit) is reported the same way and exits
    1. Nothing is ever allowed to reach Python's own traceback printer: the
    chain of a Ctrl-C raised inside proxy.reload()'s reconnect loop carries
    pyserial's "could not open port /dev/cu.usbmodem<serial>" text.
    """
    try:
        return main(argv)
    except SystemExit:
        raise
    except BaseException as exc:
        try:
            print(stop_line(exc), file=sys.stderr)
        except BaseException:       # a closed stderr, or a second Ctrl-C while the line is
            pass                    # written, must not turn into a traceback either
        return 130 if isinstance(exc, KeyboardInterrupt) else 1


if __name__ == "__main__":
    sys.exit(cli())
