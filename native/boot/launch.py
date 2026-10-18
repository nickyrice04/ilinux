#!/usr/bin/env python3
"""Verify an iLinux boot package offline; optionally launch an approved RAM test.

Default execution never imports m1n1 or opens USB. No installer is included.
"""
import argparse
import base64
import collections
import hashlib
import json
from pathlib import Path
import signal
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fdt import check_stage_b
import dapf_guard
import entry_guard
import gpio_guard
sys.path.insert(0, str(HERE.parents[1] / "tools/m1n1-client"))
import usb_identity

M1N1_COMMIT = "57a9339ffd1876e78297b17d34dece8cff8fa1ba"
BOOTARGS = ("console=tty0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 "
            "cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused "
            "clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 "
            "earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init "
            "ilinux_probe_diag=1")
CONFIRM = "BOOT-J716C-RAM-DIAGNOSTIC"
# Omarchy-style RAM root (VM job 039): the same package, gates and Image with another
# initrd and fixed arguments. These omit idle=nop arm64.nowfxt: the pinned m1n1 appends
# exactly those on M4 and later (kboot.c, !apple_sysregs_unlocked), and they are required.
RAMROOT_BOOTARGS = ("console=tty0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 "
                    "pd_ignore_unused clk_ignore_unused quiet")
RAMROOT_CONFIRM = "BOOT-J716C-RAM-ROOT"
RAMROOT_RECORD = HERE / "ramroot-manifest.json"
# Omarchy itself (VM job 045, built by Omarchy's installer): the RAM-root package, gates and
# arguments with a 2.34 GB image. Only the deadline, the client heap and the pin differ.
OMARCHY_CONFIRM = "BOOT-J716C-OMARCHY-ROOT"
OMARCHY_RECORD = HERE / "omarchy-root-manifest.json"
M1N1_APPEND = ("idle=nop", "arm64.nowfxt")
# heap: ProxyUtils' heap_size, from which kernel, DT and initrd are placed; None keeps its 1 GiB.
Profile = collections.namedtuple("Profile", "initrd bootargs label confirm deadline exact_append heap")
PROFILES = {
    "stage-b": Profile("initramfs-stage-b.cpio.gz", BOOTARGS, "diagnostic", CONFIRM, 180, False, None),
    # 300 s: the upload alone is ~227 MB, 45-57 s at the observed 4-5 MB/s.
    "ramroot": Profile("ramroot.cpio.zst", RAMROOT_BOOTARGS, "RAM-root", RAMROOT_CONFIRM, 300, True, None),
    # 900 s: ~2.38 GB, 444.5 s at attempt 20's 5.36 MB/s, 596 s at 4 MB/s. 1 GiB of heap leaves
    # ~1.03 GB for an initrd; 3 GiB holds this one with ~0.8 GB to spare.
    "omarchy": Profile("ramroot.cpio.zst", RAMROOT_BOOTARGS, "Omarchy RAM-root", OMARCHY_CONFIRM, 900,
                       True, 3 * 1024**3),
}
STAGE_B = PROFILES["stage-b"]
PROXY_RATES = (5e6, 4e6)   # observed m1n1 USB proxy upload rates, bytes/s (roadmap.md, Phase 3)
KEY_TYPES = ("ssh-ed25519", "sk-ssh-ed25519@openssh.com", "ecdsa-sha2-nistp256",
             "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521",
             "sk-ecdsa-sha2-nistp256@openssh.com", "ssh-rsa")


def verify_package(directory):
    manifest = json.loads((HERE / "package-manifest.json").read_text())
    if manifest["m1n1_commit"] != M1N1_COMMIT:
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


def verify_ramroot(path, image, record_file=None):
    """Return the recorded RAM-root build and its bytes; refuse any other image or Image."""
    record = json.loads((record_file or RAMROOT_RECORD).read_text())
    if hashlib.sha256(image).hexdigest() != record["image_sha256"]:
        raise ValueError("package Image differs from the Image the RAM root was built for")
    if path.is_symlink() or not path.is_file() or path.stat().st_size != record["size"]:
        raise ValueError("RAM root missing, not a regular file or size mismatch")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError("RAM root checksum mismatch: not the recorded build")
    if data[:4] != b"\x28\xb5\x2f\xfd":
        raise ValueError("RAM root is not a zstd frame")
    return record, data


def newc_cpio(entries):
    """Uncompressed newc cpio of (name, mode, data): root-owned, mtime 0, then the trailer."""
    out = b""
    for ino, (name, mode, data) in enumerate(entries + [("TRAILER!!!", 0, b"")], 1):
        if name == "TRAILER!!!":
            ino = 0
        nlink = 2 if mode & 0o170000 == 0o040000 else 1
        fields = (ino, mode, 0, 0, nlink, 0, len(data), 0, 0, 0, 0, len(name) + 1, 0)
        out += b"070701" + b"".join(b"%08X" % f for f in fields) + name.encode() + b"\0"
        out += b"\0" * (-len(out) % 4) + data + b"\0" * (-len(data) % 4)
    return out


def operator_key_cpio(text):
    """Return a cpio holding /etc/ssh/authorized_keys.d/root and the keys' fingerprints.

    Plain OpenSSH public keys only: no options, no private keys; comments are dropped.
    Same layout as job 039's VM-tested key overlay: directories 0755, file 0600, root.
    """
    if len(text) > 16384:
        raise ValueError("operator key file is larger than 16 KiB")
    try:
        lines = [line.split() for line in text.decode("ascii").splitlines() if line.strip()]
    except UnicodeDecodeError:
        raise ValueError("operator key file is not ASCII") from None
    if not 1 <= len(lines) <= 8:
        raise ValueError("operator key file must hold 1 to 8 public keys")
    keys, prints = [], []
    for fields in lines:
        if len(fields) < 2 or fields[0] not in KEY_TYPES:
            raise ValueError("operator key file holds something other than a plain public key")
        try:
            blob = base64.b64decode(fields[1], validate=True)
        except ValueError:
            raise ValueError("operator key data is not base64") from None
        length = int.from_bytes(blob[:4], "big")
        if blob[4:4 + length] != fields[0].encode():
            raise ValueError("operator key type does not match its key data")
        keys.append("%s %s\n" % (fields[0], fields[1]))
        digest = base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip("=")
        prints.append("%s SHA256:%s" % (fields[0], digest))
    return newc_cpio([("etc", 0o40755, b""), ("etc/ssh", 0o40755, b""),
                      ("etc/ssh/authorized_keys.d", 0o40755, b""),
                      ("etc/ssh/authorized_keys.d/root", 0o100600, "".join(keys).encode())]), prints


def ramroot_initrd(image, overlay=b""):
    # Linux unpacks an uncompressed cpio after a compressed one only at a 4-byte offset
    # and skips the zero padding before it.
    return image + b"\0" * (-len(image) % 4) + overlay if overlay else image


def upload_estimate(files, profile):
    """Bytes written over the proxy and the seconds they take at each observed rate."""
    total = sum(len(files[n]) for n in ("Image", profile.initrd, "t6050-j716c-stage-b.dtb"))
    return total, [total / rate for rate in PROXY_RATES]


def ensure_no_secondaries(proxy):
    # The pinned m1n1 spin-table flag tracks started secondaries; boot CPU's
    # flag remains zero. Check all MAX_CPUS entries, not only this SKU's 18.
    if any(proxy.smp_is_alive(cpu) for cpu in range(32)):
        raise ValueError("secondary already started; restart the fresh m1n1 entry")


def check_profile(profile):
    if profile not in PROFILES.values():
        raise ValueError("unknown launch profile; only stage-b, ramroot and omarchy exist")


def launch_session(iface, proxy, utils_factory, manifest, files, profile=STAGE_B):
    """Transport-injected to test failure paths without physical hardware."""
    check_profile(profile)
    proxy.nop()
    if proxy.get_chipid() != 0x6050:
        raise ValueError("target chip is not t6050")
    base = proxy.get_base()
    marker = manifest["m1n1_version_marker"].encode("ascii") + b"\0"
    if iface.readmem(base + manifest["m1n1_version_offset"], len(marker)) != marker:
        raise ValueError("target m1n1 does not match packaged build")
    ensure_no_secondaries(proxy)
    print("Target PASS: t6050, packaged m1n1 marker, no started secondaries.", flush=True)
    # No m1n1.setup, bootstrap_port, PMU reset, shell, cpufreq_init or SMP start.
    # ProxyUtils sets up a RAM heap and reads boot arguments; it is not read-only.
    print("Initializing controller RAM utilities.", flush=True)
    utils = utils_factory(proxy) if profile.heap is None else utils_factory(proxy, heap_size=profile.heap)
    print("Reading target ADT root compatibility.", flush=True)
    # LazyADT already represents the root. In the pinned API, ["/"] looks
    # for an empty-named child and raises KeyError; it does not return root.
    try:
        compatible = utils.adt.compatible
    except (KeyError, AttributeError) as exc:
        raise ValueError("target ADT root compatibility unavailable (%s)" %
                         type(exc).__name__) from None
    if not isinstance(compatible, (list, tuple)) or "J716cAP" not in compatible:
        raise ValueError("target board is not J716c")
    if not utils.ba.video.base or not utils.ba.video.width or not utils.ba.video.height:
        raise ValueError("m1n1 has no boot framebuffer")
    gpio_guard.check_adt(utils.adt)
    print("GPIO ADT PASS: main controller 221 pins/7 groups; exclusions 5,6,7,112,141 match.", flush=True)
    print("Board/framebuffer PASS; allocating RAM for %s payloads." % profile.label, flush=True)
    dapf_plan = dapf_guard.prepare(iface, base, files["m1n1.bin"], utils.adt)
    print("DAPF layout PASS: AOP has DART/GAPF only; RAM correction planned.", flush=True)
    image = files["Image"]
    # Respect ARM64 Image.text_offset instead of assuming it is always zero.
    text_offset, image_size = struct.unpack_from("<QQ", image, 8)
    if text_offset > 2 * 1024 * 1024 or image_size < len(image) or image_size > 512 * 1024**2:
        raise ValueError("unsupported Image memory layout")
    kernel = utils.memalign(2 * 1024 * 1024, text_offset + image_size) + text_offset
    dtb = files["t6050-j716c-stage-b.dtb"]
    dt_addr = utils.memalign(65536, len(dtb))
    initrd = files[profile.initrd]
    initrd_addr = utils.memalign(65536, len(initrd))
    print("Uploading DT, initramfs and kernel to RAM.", flush=True)
    iface.writemem(dt_addr, dtb)
    iface.writemem(initrd_addr, initrd)
    iface.writemem(kernel, image)
    print("RAM upload complete; preparing effective DT and hardware handoff.", flush=True)
    proxy.kboot_set_chosen("bootargs", profile.bootargs)
    proxy.kboot_set_initrd(initrd_addr, len(initrd))
    if proxy.kboot_prepare_dt(dt_addr) != 0:
        raise ValueError("m1n1 DT preparation failed")
    # Read back the effective DT after all m1n1 fixups. Never save it: m1n1
    # adds target serial/MAC data. Validate only the allowed boot properties.
    prepared = proxy.read64(base + manifest["m1n1_dt_pointer_offset"])
    if not prepared:
        raise ValueError("m1n1 returned no prepared DT")
    header = iface.readmem(prepared, 8)
    magic, total = struct.unpack(">II", header)
    if magic != 0xD00DFEED or not 40 <= total <= 2 * 1024 * 1024:
        raise ValueError("invalid prepared DT size")
    tree = check_stage_b(iface.readmem(prepared, total), prepared=True)
    args = tree.get("/chosen", {}).get("bootargs", b"").rstrip(b"\0").decode("ascii").split()
    fixed = profile.bootargs.split()
    if args[:len(fixed)] != fixed:
        raise ValueError("prepared DT bootargs differ from fixed %s arguments" % profile.label)
    if profile.exact_append:
        if args[len(fixed):] != list(M1N1_APPEND):
            raise ValueError("prepared DT lacks m1n1's exact idle=nop arm64.nowfxt append")
    elif any(a not in M1N1_APPEND for a in args[len(fixed):]):
        raise ValueError("unexpected appended bootargs")
    print("Hardware DT PASS: J716c/t6050 CPU topology, AIC3 and timer routes verified.", flush=True)
    descriptor = entry_guard.plan(image, tree)
    ensure_no_secondaries(proxy)
    dapf_guard.apply(iface, dapf_plan)
    print("DAPF RAM table corrected: omitted absent AOP DAPF; other entries retained.", flush=True)
    entry_guard.apply(iface, kernel, descriptor)
    print("Early framebuffer PASS: kernel RAM descriptor checked and populated.", flush=True)
    proxy.dc_cvau(kernel, len(image))
    proxy.ic_ivau(kernel, len(image))
    utils.msr("DAIF", 0xC0)
    print("Preflight PASS; handing off. Observe the M5 display; USB console ends here.", flush=True)
    proxy.kboot_boot(kernel)
    # kboot_boot shuts down the proxy/USB on handoff; no ttymode/hang/retry.


def connect_and_launch(device, m1n1, manifest, files, profile=STAGE_B):
    check_profile(profile)
    pin = subprocess.check_output(["git", "-C", str(m1n1), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(m1n1), "status", "--porcelain", "--untracked-files=no"], text=True)
    if pin != M1N1_COMMIT or dirty:
        raise ValueError("client must be the clean pinned m1n1 checkout")
    # Imports occur only after the explicit live-launch gates and pin checks.
    sys.path.insert(0, str(m1n1 / "proxyclient"))
    # Repeat descriptor discovery immediately before opening the transport.
    # Never infer identity from a serial-containing filename or choose a fallback.
    try:
        selected = usb_identity.select_primary(usb_identity.discover(), device)
    except Exception as exc:
        raise ValueError("USB identity check failed (%s); no port opened" %
                         type(exc).__name__) from None
    print("Primary verified: VID:PID 1209:316d, CDC data interface 1; path redacted.")
    from m1n1.proxy import UartInterface, M1N1Proxy, Serial
    from m1n1.proxyutils import ProxyUtils
    transport = None

    def timeout(*_):
        raise TimeoutError("launch exceeded %d seconds; do not automatically retry" % profile.deadline)

    old = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(profile.deadline)
    try:
        transport = Serial(selected, UartInterface.DEFAULT_BAUD_RATE)
        iface = UartInterface(device=transport)
        iface.tty_enable = False
        iface.dev.timeout = 15
        launch_session(iface, M1N1Proxy(iface), ProxyUtils, manifest, files, profile)
    except OSError as exc:
        # Serial errors may embed target identifiers in the callout path.
        raise RuntimeError("USB transport failed (%s); do not automatically retry" %
                           type(exc).__name__) from None
    finally:
        try:
            if transport is not None:
                try:
                    transport.close()
                except OSError as exc:
                    raise RuntimeError("USB close failed (%s); do not automatically retry" %
                                       type(exc).__name__) from None
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="stage-b",
                        help="stage-b (default): diagnostic initramfs; ramroot: job 039's RAM root; "
                             "omarchy: job 045's Omarchy root (2.34 GB, about 7.5 min of upload)")
    parser.add_argument("--ramroot", type=Path, help="ramroot/omarchy profile: the recorded ramroot.cpio.zst")
    parser.add_argument("--operator-key", type=Path,
                        help="ramroot/omarchy profile, optional: OpenSSH public key file for root")
    parser.add_argument("--launch", action="store_true", help="LIVE RAM boot; requires separate user authorization")
    parser.add_argument("--device", help="auto, or the exact descriptor-verified primary callout")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--m1n1", type=Path, default=HERE.parents[1] / "third_party/m1n1")
    args = parser.parse_args(argv)
    profile = PROFILES[args.profile]
    if profile is STAGE_B and (args.ramroot is not None or args.operator_key is not None):
        parser.error("--ramroot and --operator-key require --profile ramroot or omarchy")
    if profile is not STAGE_B and args.ramroot is None:
        parser.error("--profile %s requires --ramroot" % args.profile)
    if args.launch and (args.confirm != profile.confirm or args.device is None):
        parser.error("live launch requires --device and --confirm " + profile.confirm)
    if not args.launch and (args.device is not None or args.confirm):
        parser.error("offline mode does not accept device/confirmation arguments")
    manifest, files = verify_package(args.package)
    print("Package PASS: all files match the repository manifest.")
    if profile is not STAGE_B:
        files = dict(files)
        record_file = OMARCHY_RECORD if profile is PROFILES["omarchy"] else RAMROOT_RECORD
        record, image = verify_ramroot(args.ramroot, files["Image"], record_file)
        print("RAM root PASS: %s bytes match %s (%s)." % (
            format(record["size"], ","), record_file.name, record["source"]))
        overlay = b""
        if args.operator_key is not None:
            overlay, prints = operator_key_cpio(args.operator_key.read_bytes())
            for line in prints:
                print("Operator key for root:", line)
        else:
            print("Operator key: none; only keys built into the image can log in.")
        files[profile.initrd] = ramroot_initrd(image, overlay)
    print("Mode:", "LIVE RAM LAUNCH" if args.launch else "OFFLINE ONLY; USB not opened")
    print("Boot arguments:", profile.bootargs)
    if profile is not STAGE_B:
        print("m1n1 must append:", " ".join(M1N1_APPEND))
        total, seconds = upload_estimate(files, profile)
        times = ", ".join("%.1f s at %g MB/s" % (s, rate / 1e6) for s, rate in zip(seconds, PROXY_RATES))
        print("Upload estimate: %s bytes (Image %s, initrd %s, DT %s): %s "
              "(Inferred: size / observed proxy rate). Deadline %d s." % (
                  format(total, ","), format(len(files["Image"]), ","),
                  format(len(files[profile.initrd]), ","),
                  format(len(files["t6050-j716c-stage-b.dtb"]), ","), times, profile.deadline))
    if args.launch:
        connect_and_launch(args.device, args.m1n1, manifest, files, profile)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("STOP:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
