#!/usr/bin/env python3
"""Run the verified boot033 diagnostic kernel at EL1 under a private m1n1 HV.

Private iLinux tooling (never for upstream). Default execution is offline:
it verifies both packages and opens no USB port. A live run:

1. checks the installed boot021 m1n1 exactly like native/boot/launch.py, then
   repeats the guarded register census (hv_regs.py) in the same boot;
2. chainloads the private hv002 m1n1 into RAM (no RVBAR writes, no disk);
3. re-verifies the target, gates on hv002's single-CPU/ECV flags, and
   prepares the effective DT with the same checks as the native launcher;
4. starts Linux as a single-CPU EL1 guest. The kernel log is mirrored to the
   HV virtual UART (USB interface 3); Ctrl-C enters the HV shell.

Nothing is installed; power off returns the machine to Macintosh HD.
"""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BOOT = HERE.parent / "boot"
sys.path.insert(0, str(BOOT))
import launch  # noqa: E402  (boot033 package gates and fixed constants)
import dapf_guard  # noqa: E402
import entry_guard  # noqa: E402
import gpio_guard  # noqa: E402
from fdt import check_stage_b  # noqa: E402
sys.path.insert(0, str(HERE))
import hv_regs  # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / "tools/m1n1-client"))
import usb_identity  # noqa: E402

CONFIRM = "HV-J716C-RAM-DIAGNOSTIC"
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

# Chainload stub (as upstream chainload.py), pre-assembled and checked
# against clang: copy x3 bytes x1 -> x2 with cache maintenance, then jump.
STUB = bytes.fromhex("2414c1a8" "441400a9" "227b0bd5" "22750bd5"
                     "42400091" "634000d1" "43ffffb5" "41000058"
                     "20001fd6")

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


def stub(entry):
    return STUB + struct.pack("<Q", entry)


def parse_nm(text):
    """`nm -an` output: offset, type, name. m1n1 links at 0 = its RAM base."""
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3:
            out.setdefault(parts[2], int(parts[0], 16))
    return out


def verify_hv_package(directory, image):
    m = manifest()
    if m["m1n1_commit"] != launch.M1N1_COMMIT:
        raise ValueError("hv build is not based on the pinned m1n1")
    patch = (HERE / Path(m["m1n1_patch"]).name).read_bytes()
    if hashlib.sha256(patch).hexdigest() != m["m1n1_patch_sha256"]:
        raise ValueError("hv patch differs from the manifest")
    if hashlib.sha256(image).hexdigest() != m["guest_image_sha256"]:
        raise ValueError("guest Image is not the one this hv package was built for")
    loaded = {}
    for name, info in m["files"].items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != info["size"]:
            raise ValueError("missing file or size mismatch: " + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != info["sha256"]:
            raise ValueError("checksum mismatch: " + name)
        loaded[name] = data
    hv = loaded["m1n1-hv.bin"]
    marker = m["hv_version_marker"].encode() + b"\0"
    off = m["hv_version_offset"]
    if hv[off:off + len(marker)] != marker:
        raise ValueError("hv version marker not at the recorded offset")
    syms = parse_nm(loaded["m1n1-hv-symbols.txt"].decode("ascii"))
    for symbol, key in HV_SYMBOLS.items():
        if syms.get(symbol) != m[key]:
            raise ValueError("hv symbol offset differs from the build: " + symbol)
    for required in ("kboot_prepare_hv_guest", "hv_ilinux_timers_reset"):
        if required not in syms:
            raise ValueError("hv build lacks " + required + " (not an hv002 build)")
    if not all(m[key] < len(hv) for key in HV_SYMBOLS.values()):
        raise ValueError("hv symbol outside the loaded image")
    with hv_dapf_pin(hv):
        dapf_guard.verify_image(hv)
    check_system_map(loaded["System.map"].decode("ascii"), image)
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


def chainload(iface, proxy, utils, hv_image, blob_api, bootargs_types):
    """upstream chainload.py -r. RVBARs are never written; upstream also
    skips them here, because a raw image entering at base + 0x800 keeps
    the current page-aligned base."""
    image = hv_image + b"\0\0\0\0"
    new_base = utils.base
    entry = new_base + 0x800
    names, find_boot_blobs, copy_boot_blobs, blob_type = blob_api
    blobs, image_size = find_boot_blobs(utils.adt["chosen"]["memory-map"]._properties,
                                        names, align_up(len(image), 0x4000))
    bootargs_off = image_size
    image_size += 0x4000
    image_addr = utils.malloc(image_size)
    copy_boot_blobs(proxy, [(n, s, z, image_addr + o) for n, s, z, o in blobs])
    utils.compressed_writemem(image_addr, image, True)
    proxy.dc_cvau(image_addr, len(image))
    mm = utils.adt["chosen"]["memory-map"]
    for name, _, size, off in blobs:
        mm._properties[name] = (new_base + off, size)
        mm._types[name] = blob_type
    mm.BootArgs = (new_base + bootargs_off, 0x4000)
    utils.push_adt()
    tba = utils.ba.copy()
    tba.top_of_kernel_data = new_base + image_size
    iface.writemem(image_addr + bootargs_off, bootargs_types[tba.revision].build(tba))
    code = stub(entry)
    stub_addr = image_addr + image_size
    iface.writemem(stub_addr, code)
    proxy.dc_cvau(stub_addr, len(code))
    proxy.ic_ivau(stub_addr, len(code))
    # reload() waits for the new m1n1 and reopens the port if USB re-enumerates.
    proxy.reload(stub_addr, new_base + bootargs_off, image_addr, new_base, image_size)


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
    from m1n1.proxy import UartInterface, Serial
    selected = usb_identity.select_primary(usb_identity.discover(), device)
    transport = Serial(selected, UartInterface.DEFAULT_BAUD_RATE)
    iface = UartInterface(device=transport)
    iface.dev.timeout = 15
    return transport, iface


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
                raise ValueError("hv m1n1 did not answer after chainload; power off") from None
            sleep(0.5)


def connect_and_run(device, m1n1, files, hv_files, m, logfile, symbols):
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

    def timeout(*_):
        raise TimeoutError("preflight exceeded 300 seconds; do not automatically retry")

    old = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(300)
    transport = None
    try:
        transport, iface = open_primary(device)
        proxy = M1N1Proxy(iface)
        boot_m = json.loads((BOOT / "package-manifest.json").read_text())
        check_target(iface, proxy, proxy.get_base(), boot_m["m1n1_version_marker"],
                     boot_m["m1n1_version_offset"])
        print("Target PASS: t6050, installed boot021, no started secondaries.", flush=True)
        utils = ProxyUtils(proxy)
        register_preflight(utils, (ProxyError,))
        print("Register preflight PASS: ECV present; HV start/exception/FIQ registers readable.",
              flush=True)
        blob_type = (Array(2, Int64ul), False)
        chainload(iface, proxy, utils, hv_files["m1n1-hv.bin"],
                  (BOOT_BLOBS, find_boot_blobs, copy_boot_blobs, blob_type),
                  {0: BootArgs_r1, 1: BootArgs_r1, 2: BootArgs_r2, 3: BootArgs_r3})
        label = m["hv_version_marker"].rsplit("-", 1)[-1]
        print("Chainloaded %s into RAM; re-verifying the port." % label, flush=True)
        transport.close()
        transport, iface, proxy = reconnect(device, M1N1Proxy)
        check_target(iface, proxy, proxy.get_base(), m["hv_version_marker"],
                     m["hv_version_offset"])
        print("Target PASS: %s running, no started secondaries." % label, flush=True)
        utils = ProxyUtils(proxy, heap_size=128 * MIB, m1n1_heap=128 * MIB)
        hv = HV(iface, proxy, utils)
        hv.emulate_sprr = False
        hv.init()
        check_hv_flags(proxy, utils.base, m)
        print("HV PASS: single-CPU mode, ECV timer traps on; guest timers masked at source.",
              flush=True)
        if logfile:
            hv.set_logfile(logfile.open("w"))
        hv.load_system_map(str(symbols))
        layout = prepare_guest(iface, proxy, utils, files, hv_files, m)
        map_guest(hv, utils, layout, irange, TraceMode.OFF)
        hook_cpu_start(hv, irange, TraceMode.RESERVED)
        signal.alarm(0)
        start_guest(hv, proxy, iface, layout["kernel"], layout["dt"], IODEV)
        print("STOP: hv_start returned (HV refused start or guest exited).", flush=True)
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
        if transport is not None:
            with contextlib.suppress(OSError):
                transport.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True, help="boot033 package")
    parser.add_argument("--hv-package", type=Path, required=True, help="hv m1n1 package (hv002)")
    parser.add_argument("--launch", action="store_true",
                        help="LIVE RAM boot under the HV; requires separate user authorization")
    parser.add_argument("--device", help="auto, or the exact descriptor-verified primary callout")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--log", type=Path, help="HV event log (keep local; ignored path)")
    parser.add_argument("--m1n1", type=Path, default=HERE.parents[1] / "third_party/m1n1")
    args = parser.parse_args(argv)
    if args.launch and (args.confirm != CONFIRM or args.device is None):
        parser.error("live launch requires --device and --confirm " + CONFIRM)
    if not args.launch and (args.device is not None or args.confirm):
        parser.error("offline mode does not accept device/confirmation arguments")
    _, files = verify_guest_package(args.package)
    m, hv_files = verify_hv_package(args.hv_package, files["Image"])
    print("Package PASS: boot033 guest and %s m1n1 match their manifests."
          % m["hv_version_marker"].rsplit("-", 1)[-1])
    print("Mode:", "LIVE HV RAM LAUNCH" if args.launch else "OFFLINE ONLY; USB not opened")
    print("Boot arguments:", HV_BOOTARGS)
    if args.launch:
        return connect_and_run(args.device, args.m1n1, files, hv_files, m, args.log,
                               args.hv_package / "System.map")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("STOP:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
