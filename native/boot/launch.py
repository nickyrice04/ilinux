#!/usr/bin/env python3
"""Verify an iLinux boot package offline; optionally launch an approved RAM test.

Default execution never imports m1n1 or opens USB. No installer is included.
"""
import argparse
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
sys.path.insert(0, str(HERE.parents[1] / "tools/m1n1-client"))
import usb_identity

M1N1_COMMIT = "57a9339ffd1876e78297b17d34dece8cff8fa1ba"
BOOTARGS = ("console=tty0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 "
            "cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused "
            "clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 "
            "earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init")
CONFIRM = "BOOT-J716C-RAM-DIAGNOSTIC"


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


def ensure_no_secondaries(proxy):
    # The pinned m1n1 spin-table flag tracks started secondaries; boot CPU's
    # flag remains zero. Check all MAX_CPUS entries, not only this SKU's 18.
    if any(proxy.smp_is_alive(cpu) for cpu in range(32)):
        raise ValueError("secondary already started; restart the fresh m1n1 entry")


def launch_session(iface, proxy, utils_factory, manifest, files):
    """Transport-injected to test failure paths without physical hardware."""
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
    utils = utils_factory(proxy)
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
    print("Board/framebuffer PASS; allocating RAM for diagnostic payloads.", flush=True)
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
    initrd = files["initramfs-stage-b.cpio.gz"]
    initrd_addr = utils.memalign(65536, len(initrd))
    print("Uploading DT, initramfs and kernel to RAM.", flush=True)
    iface.writemem(dt_addr, dtb)
    iface.writemem(initrd_addr, initrd)
    iface.writemem(kernel, image)
    print("RAM upload complete; preparing effective DT and hardware handoff.", flush=True)
    proxy.kboot_set_chosen("bootargs", BOOTARGS)
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
    if args[:len(BOOTARGS.split())] != BOOTARGS.split():
        raise ValueError("prepared DT bootargs differ from fixed diagnostic arguments")
    if any(a not in ("idle=nop", "arm64.nowfxt") for a in args[len(BOOTARGS.split()):]):
        raise ValueError("unexpected appended bootargs")
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


def connect_and_launch(device, m1n1, manifest, files):
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
        raise TimeoutError("launch exceeded 180 seconds; do not automatically retry")

    old = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(180)
    try:
        transport = Serial(selected, UartInterface.DEFAULT_BAUD_RATE)
        iface = UartInterface(device=transport)
        iface.tty_enable = False
        iface.dev.timeout = 15
        launch_session(iface, M1N1Proxy(iface), ProxyUtils, manifest, files)
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
    parser.add_argument("--launch", action="store_true", help="LIVE RAM boot; requires separate user authorization")
    parser.add_argument("--device", help="auto, or the exact descriptor-verified primary callout")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--m1n1", type=Path, default=HERE.parents[1] / "third_party/m1n1")
    args = parser.parse_args(argv)
    if args.launch and (args.confirm != CONFIRM or args.device is None):
        parser.error("live launch requires --device and --confirm " + CONFIRM)
    if not args.launch and (args.device is not None or args.confirm):
        parser.error("offline mode does not accept device/confirmation arguments")
    manifest, files = verify_package(args.package)
    print("Package PASS: all files match the repository manifest.")
    print("Mode:", "LIVE RAM LAUNCH" if args.launch else "OFFLINE ONLY; USB not opened")
    print("Boot arguments:", BOOTARGS)
    if args.launch:
        connect_and_launch(args.device, args.m1n1, manifest, files)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("STOP:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
