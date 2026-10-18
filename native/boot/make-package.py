#!/usr/bin/env python3
"""Package whitelisted VM outputs; write pinned manifest, archive and checksum."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fdt import check_stage_b, properties
import kconfig_guard

FILES = ("Image", "t6050-j716c.dtb", "initramfs.cpio.gz", "kernel.config",
         "t6050-j716c-stage-b.dtb", "initramfs-stage-b.cpio.gz", "m1n1.bin",
         "m1n1-build-config.h", "m1n1-LICENSE", "m1n1-revision.txt", "diag-init.c", "toolchain.txt")
ORIGINAL = {
    "Image": "f9cf7c0046712cdf60e686e7a13d998b3e4d1b55a1d64de5dba997aa9a77f704",
    "t6050-j716c.dtb": "5d6fe64812b05e8c5d42ce3b97e3ede4c675e7a9a59d8fcf85d6906ef8daac9e",
    "initramfs.cpio.gz": "15565c4bc7371dd40ce6387305af40391140fda5a871e9012aebd65e95162618",
}
# kernel/experiments/usb-gadget/init.c as each control-channel package was built with it (boot036
# and boot037: f9b63de; boot038: bd814ad; boot039: 2026-10-16; boot040: 2026-10-18), so a package
# rebuilds after it moves on.
INIT_SOURCE = {
    "ilinux-j716c-boot036": "8987f9a85c247e603adee6e981485b755e0ce6c8cbb04d9218db9417c720c086",
    "ilinux-j716c-boot037": "8987f9a85c247e603adee6e981485b755e0ce6c8cbb04d9218db9417c720c086",
    "ilinux-j716c-boot038": "ed29c046d26cf9360d37b9e6d263ce84b722eb62b5b37b906151ba4b0f6e2940",
    "ilinux-j716c-boot039": "8ba20c9352694df9dc99a13ab0f83980ba5508c3bf688cc8649ce8da4c69d7c5",
    "ilinux-j716c-boot040": "58c68268b2f05ad2d5f5f1e25478814ec019211a405342e7c9cc256c359e22de",
}
# The Image a package may carry when it is allowed to differ from its baseline and the baseline
# comparison therefore no longer covers it: boot040's is job 041's reproducible build of the boot036
# tree plus kernel/experiments/usb-gadget/dart-diag (2026-10-18).
IMAGE_SOURCE = {
    "ilinux-j716c-boot040": "a53d1d47467480d4b56d87c7b1365e9a5c28fd9ee9e5f0164a3e734f85526ad9",
}
NAME = "ilinux-j716c-boot021"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="VM job out directory containing export/")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--name", choices=(NAME, "ilinux-j716c-boot022", "ilinux-j716c-boot024", "ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"), default=NAME)
    parser.add_argument("--previous-package", type=Path, help="boot032/boot035/boot036/boot037: verified previous package directory for the exact DT-delta check; boot039: boot036's, for the initramfs delta; boot040: boot039's")
    parser.add_argument("--authorized-key", type=Path, help="boot036-boot040: the one public key root's authorized_keys must hold")
    parser.add_argument("--record-dir", type=Path, default=HERE, help="where package-manifest.json, intake-manifest-sha256.txt and archive-sha256.txt go (default native/boot: the current handoff)")
    args = parser.parse_args()
    data = {name: (args.out / "export" / name).read_bytes() for name in FILES}
    checks = {n: {"size": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in data.items()}
    for name, digest in ORIGINAL.items():
        if name == "Image" and args.name in ("ilinux-j716c-boot024", "ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
            continue
        if checks[name]["sha256"] != digest:
            raise ValueError("original job-020 artifact changed: " + name)
    # kernel.config must be the config embedded in the Image (boot024-035: toolchain lines only).
    kconfig_guard.check(args.name, data["Image"], data["kernel.config"])
    check_stage_b(data["t6050-j716c-stage-b.dtb"])
    forbidden = {"serial-number", "mac-address", "local-mac-address", "system-id",
                 "uuid", "ecid", "unique-chip-id", "die-id", "nonce"}
    for name in ("t6050-j716c.dtb", "t6050-j716c-stage-b.dtb"):
        if any(forbidden.intersection(node) for node in properties(data[name]).values()):
            raise ValueError("identifying properties in package DT")
    symbols = {}
    if args.name in ("ilinux-j716c-boot022", "ilinux-j716c-boot024", "ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        previous = {"ilinux-j716c-boot022": "boot021", "ilinux-j716c-boot024": "boot022",
                    "ilinux-j716c-boot025": "boot024", "ilinux-j716c-boot027": "boot025", "ilinux-j716c-boot028": "boot027", "ilinux-j716c-boot029": "boot028", "ilinux-j716c-boot030": "boot029", "ilinux-j716c-boot031": "boot030", "ilinux-j716c-boot032": "boot031", "ilinux-j716c-boot033": "boot032", "ilinux-j716c-boot034": "boot033", "ilinux-j716c-boot035": "boot034", "ilinux-j716c-boot036": "boot035", "ilinux-j716c-boot037": "boot036", "ilinux-j716c-boot038": "boot036", "ilinux-j716c-boot039": "boot036", "ilinux-j716c-boot040": "boot039"}[args.name]
        allowed_changes = {"t6050-j716c-stage-b.dtb"} if previous == "boot021" else {"Image"}
        if args.name == "ilinux-j716c-boot032":
            allowed_changes.add("t6050-j716c-stage-b.dtb")
        if args.name == "ilinux-j716c-boot035":
            allowed_changes = {"t6050-j716c-stage-b.dtb"}   # the boot034 Image stays byte-identical
        if args.name == "ilinux-j716c-boot036":   # USB control channel; m1n1 and the generic files stay
            allowed_changes = {"Image", "kernel.config", "t6050-j716c-stage-b.dtb",
                               "initramfs-stage-b.cpio.gz", "diag-init.c", "toolchain.txt"}
        if args.name == "ilinux-j716c-boot037":   # MTP input path; the control channel and m1n1 stay
            allowed_changes = {"Image", "kernel.config", "t6050-j716c-stage-b.dtb"}
        if args.name == "ilinux-j716c-boot038":   # ACM + ECM gadget: only the initramfs and its source
            allowed_changes = {"initramfs-stage-b.cpio.gz", "diag-init.c", "toolchain.txt"}
        if args.name == "ilinux-j716c-boot039":   # bulk-only gser gadget: /init and its source only
            allowed_changes = {"initramfs-stage-b.cpio.gz", "diag-init.c"}
        if args.name == "ilinux-j716c-boot040":   # DART fault diagnostics: the Image (patched apple-dart), /init and its source
            allowed_changes = {"Image", "initramfs-stage-b.cpio.gz", "diag-init.c"}
        baseline = json.loads((HERE / (previous + "-package-manifest.json")).read_text())
        for name, info in baseline["files"].items():
            if name not in allowed_changes and checks[name] != info:
                raise ValueError("unexpected payload change: " + name)
        if args.name == "ilinux-j716c-boot032":
            if args.previous_package is None:
                raise ValueError("boot032 needs --previous-package for exact DT-delta check")
            before_blob = (args.previous_package / "t6050-j716c-stage-b.dtb").read_bytes()
            if hashlib.sha256(before_blob).hexdigest() != baseline["files"]["t6050-j716c-stage-b.dtb"]["sha256"]:
                raise ValueError("prior DT digest mismatch")
            before = properties(before_blob)
            after = properties(data["t6050-j716c-stage-b.dtb"])
            import gpio_guard
            if "gpio-reserved-ranges" in before[gpio_guard.PATH]:
                raise ValueError("prior DT already contains exclusions")
            before[gpio_guard.PATH]["gpio-reserved-ranges"] = gpio_guard.RANGES
            if before != after:
                raise ValueError("DT delta exceeds the approved GPIO exclusion property")
        if args.name == "ilinux-j716c-boot035":
            if args.previous_package is None:
                raise ValueError("boot035 needs --previous-package for exact DT-delta check")
            before_blob = (args.previous_package / "t6050-j716c-stage-b.dtb").read_bytes()
            if hashlib.sha256(before_blob).hexdigest() != baseline["files"]["t6050-j716c-stage-b.dtb"]["sha256"]:
                raise ValueError("prior DT digest mismatch")
            before = properties(before_blob)
            after = properties(data["t6050-j716c-stage-b.dtb"])
            removed = sorted(set(before) - set(after))
            labels = sorted(before[path].get("label", b"").rstrip(b"\0").decode() for path in removed)
            if labels != ["smc_i2cm%d" % i for i in range(7)] or set(after) - set(before):
                raise ValueError("DT delta must be exactly the seven smc_i2cm power domains")
            for path in removed:
                del before[path]
            if before != after:
                raise ValueError("DT delta exceeds the removal of the smc_i2cm power domains")
        if args.name == "ilinux-j716c-boot036":
            import control_channel
            import usb_dt
            if args.previous_package is None or args.authorized_key is None:
                raise ValueError("boot036 needs --previous-package and --authorized-key")
            prior = {}
            for name in ("t6050-j716c-stage-b.dtb", "kernel.config"):
                prior[name] = (args.previous_package / name).read_bytes()
                if hashlib.sha256(prior[name]).hexdigest() != baseline["files"][name]["sha256"]:
                    raise ValueError("prior digest mismatch: " + name)
            usb_dt.check_delta(properties(prior["t6050-j716c-stage-b.dtb"]),
                               properties(data["t6050-j716c-stage-b.dtb"]))
            toolchain_lines = control_channel.check_config(
                prior["kernel.config"].decode(), data["kernel.config"].decode(), allow_toolchain=True)
            if checks["diag-init.c"]["sha256"] != INIT_SOURCE[args.name]:
                raise ValueError("diag-init.c is not the init.c boot036 was built with")
            authorized_key = args.authorized_key.read_bytes()
            control_channel.check_initramfs(data["initramfs-stage-b.cpio.gz"], authorized_key)
        if args.name == "ilinux-j716c-boot038":
            import control_channel
            if args.authorized_key is None:
                raise ValueError("boot038 needs --authorized-key")
            if checks["diag-init.c"]["sha256"] != INIT_SOURCE[args.name]:
                raise ValueError("diag-init.c is not the init.c boot038 was built with")
            if b"functions/acm.GS0" not in data["diag-init.c"] or b"functions/ecm.usb" not in data["diag-init.c"] \
                    or b"functions/eem.usb" in data["diag-init.c"]:
                raise ValueError("boot038's init must set up ACM + ECM and no EEM")
            authorized_key = args.authorized_key.read_bytes()
            control_channel.check_initramfs(data["initramfs-stage-b.cpio.gz"], authorized_key)
        if args.name == "ilinux-j716c-boot039":
            import control_channel
            if args.previous_package is None or args.authorized_key is None:
                raise ValueError("boot039 needs --previous-package (boot036's) and --authorized-key")
            prior = (args.previous_package / "initramfs-stage-b.cpio.gz").read_bytes()
            if hashlib.sha256(prior).hexdigest() != baseline["files"]["initramfs-stage-b.cpio.gz"]["sha256"]:
                raise ValueError("prior digest mismatch: initramfs-stage-b.cpio.gz")
            if checks["diag-init.c"]["sha256"] != INIT_SOURCE[args.name]:
                raise ValueError("diag-init.c is not the init.c boot039 was built with")
            authorized_key = args.authorized_key.read_bytes()
            entries = control_channel.check_initramfs(data["initramfs-stage-b.cpio.gz"], authorized_key)
            # One bulk-only function (gser) and no ACM/ECM/EEM/NCM/RNDIS, in the source and in
            # the /init actually packed; the initramfs is boot036's apart from /init.
            control_channel.check_bulk_only_init(data["diag-init.c"], entries["init"][3])
            control_channel.check_init_only_delta(prior, data["initramfs-stage-b.cpio.gz"])
        if args.name == "ilinux-j716c-boot040":
            import control_channel
            if args.previous_package is None or args.authorized_key is None:
                raise ValueError("boot040 needs --previous-package (boot039's) and --authorized-key")
            prior = (args.previous_package / "initramfs-stage-b.cpio.gz").read_bytes()
            if hashlib.sha256(prior).hexdigest() != baseline["files"]["initramfs-stage-b.cpio.gz"]["sha256"]:
                raise ValueError("prior digest mismatch: initramfs-stage-b.cpio.gz")
            if checks["diag-init.c"]["sha256"] != INIT_SOURCE[args.name]:
                raise ValueError("diag-init.c is not the init.c boot040 was built with")
            authorized_key = args.authorized_key.read_bytes()
            entries = control_channel.check_initramfs(data["initramfs-stage-b.cpio.gz"], authorized_key)
            # The boot039 gadget contract stays; the initramfs is boot039's apart from /init, which
            # carries the DART diagnostics; the Image carries the apple-dart fault-report patch and
            # (the baseline comparison above) boot039's kernel config byte for byte.
            control_channel.check_bulk_only_init(data["diag-init.c"], entries["init"][3])
            control_channel.check_dart_diag_init(entries["init"][3])
            control_channel.check_init_only_delta(prior, data["initramfs-stage-b.cpio.gz"])
            control_channel.check_dart_diag_image(data["Image"])
            if checks["Image"]["sha256"] != IMAGE_SOURCE[args.name]:
                raise ValueError("Image is not the boot040 Image job 041 built (boot036's tree plus the DART "
                                 "fault-report patch, reproducible build)")
        if args.name == "ilinux-j716c-boot037":
            import control_channel
            import mtp_input
            if args.previous_package is None or args.authorized_key is None:
                raise ValueError("boot037 needs --previous-package and --authorized-key")
            prior = {}
            for name in ("t6050-j716c-stage-b.dtb", "kernel.config"):
                prior[name] = (args.previous_package / name).read_bytes()
                if hashlib.sha256(prior[name]).hexdigest() != baseline["files"][name]["sha256"]:
                    raise ValueError("prior digest mismatch: " + name)
            mtp_input.check_delta(properties(prior["t6050-j716c-stage-b.dtb"]),
                                  properties(data["t6050-j716c-stage-b.dtb"]))
            mtp_input.check_config(prior["kernel.config"].decode(), data["kernel.config"].decode())
            mtp_input.check_image(data["Image"])
            # The control channel is how boot037's input is verified: its contract stays enforced.
            if checks["diag-init.c"]["sha256"] != INIT_SOURCE[args.name]:
                raise ValueError("diag-init.c is not the init.c boot037 was built with")
            authorized_key = args.authorized_key.read_bytes()
            control_channel.check_initramfs(data["initramfs-stage-b.cpio.gz"], authorized_key)
        symbols = {"_base": 0, "version_tag": baseline["m1n1_version_offset"],
                   "dt": baseline["m1n1_dt_pointer_offset"]}
    else:
        for line in (args.out / "m1n1-symbols.txt").read_text().splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[2] in ("_base", "version_tag", "dt"):
                symbols[fields[2]] = int(fields[0], 16)
    if symbols.get("_base") != 0:
        raise ValueError("unexpected m1n1 ELF base")
    marker = "##m1n1_ver##ilinux-57a9339-boot021"
    start = symbols["version_tag"]
    if data["m1n1.bin"][start:start + len(marker) + 1] != marker.encode() + b"\0":
        raise ValueError("m1n1 version offset does not match binary")
    manifest = {
        "schema": 1, "package": args.name, "target": "Mac17,6 / J716c / t6050",
        "native_tested": False,
        "linux_base": "77cb8f24c2381a8abb7272d7bbdec548d6426a8a",
        "linux_patches": "kernel/patches/t6050/0001-0007; job-020 Image unchanged",
        "m1n1_commit": "57a9339ffd1876e78297b17d34dece8cff8fa1ba",
        "m1n1_build": "make -j6 ARCH= BUILDSTD=1; no appended payload; no local patches",
        "m1n1_version_marker": marker,
        "m1n1_version_offset": start,
        "m1n1_dt_pointer_offset": symbols["dt"],
        "files": checks,
    }
    if args.name in ("ilinux-j716c-boot024", "ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        from entry_guard import descriptor_offset
        manifest["linux_patches"] = ("kernel/patches/t6050/0001-0007 plus "
                                     "kernel/experiments/early-framebuffer/apply.py; job-024")
        manifest["early_framebuffer_descriptor_offset"] = descriptor_offset(data["Image"])
        if args.name in ("ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
            manifest["linux_patches"] += "; kernel/experiments/aic-t6050/t6050-bringup.patch; job-025"
    if args.name in ("ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; kernel/experiments/deferred-probe/apply.py; job-027"
    if args.name in ("ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; kernel/experiments/schedule-boundary/apply.py; job-028"
    if args.name in ("ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; kernel/experiments/context-display/apply.py; job-029"
    if args.name in ("ilinux-j716c-boot030", "ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; kernel/experiments/probe-path/apply.py; job-030"
    if args.name in ("ilinux-j716c-boot031", "ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; kernel/experiments/gpio-handoff/apply.py; job-031"
    if args.name in ("ilinux-j716c-boot032", "ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; kernel/experiments/gpio-reserved/apply.py; job-032; Stage-B gpio-reserved-ranges"
    if args.name in ("ilinux-j716c-boot033", "ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; kernel/experiments/scheduler-ram-only/apply.py; job-033"
    if args.name in ("ilinux-j716c-boot034", "ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; kernel/experiments/genpd-sync-state/apply.py; job-036"
    if args.name in ("ilinux-j716c-boot035", "ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += "; Stage-B DT without the SMC-owned smc_i2cm0-6 power domains; job-038"
    if args.name in ("ilinux-j716c-boot036", "ilinux-j716c-boot037", "ilinux-j716c-boot038", "ilinux-j716c-boot039", "ilinux-j716c-boot040"):
        manifest["linux_patches"] += ("; USB control channel: gadget stack built in, dwc3 peripheral "
                                      "cores with ATC 0-2 domains left to m1n1, EEM gadget + dropbear "
                                      "initramfs (kernel/experiments/usb-gadget); job-041")
        manifest["control_channel_authorized_key"] = authorized_key.decode().strip()
    if args.name == "ilinux-j716c-boot036":
        # boot024-035 shipped job 020's kernel.config; this one is the config that built the Image.
        manifest["kernel_config_toolchain_lines_vs_boot035"] = toolchain_lines
    if args.name == "ilinux-j716c-boot038":
        manifest["linux_patches"] += ("; control channel gadget revised: CDC-ACM kernel-log port + CDC-ECM "
                                      "network in one configuration (macOS 26.0.1 on the controller has no "
                                      "EEM driver); Image, config and DT identical to boot036; job-041")
    if args.name == "ilinux-j716c-boot039":
        manifest["linux_patches"] += ("; control channel gadget revised again: one bulk-only generic serial "
                                      "function (gser: vendor class 0xff, bulk IN + bulk OUT, no interrupt "
                                      "endpoint) carries the kernel log, written only by the M5; no network "
                                      "function; dwc3 debugfs state in the status line; only /init differs "
                                      "from boot036; job-041")
        manifest["control_channel_function"] = {"configfs": "gser.GS0", "bcdDevice": "0x0139",
                                                "interface_class": "0xff",
                                                "endpoints": ["bulk IN", "bulk OUT"]}
    if args.name == "ilinux-j716c-boot040":
        manifest["linux_patches"] += ("; boot039's bulk-only gser log port unchanged; DART fault diagnostics after "
                                      "attempt 21: the Image adds kernel/experiments/usb-gadget/dart-diag (part 1: "
                                      "the apple-dart t8110 fault handler reports and acknowledges an interrupt it "
                                      "does not recognise and names each instance at probe; part 2: a DART whose "
                                      "PARAMS3 reports version 2.2 or later is reported and acknowledged in that "
                                      "version's fault layout, with a bound of 256 acknowledged interrupts; "
                                      "translation and protection untouched), /init adds the dwc3 bus-error "
                                      "address, the DART identity and a read-only DART register snapshot per port "
                                      "(both layouts), short [usbN] lines and the streamer stop at the first bus "
                                      "error; config and DT identical to boot039; job-041")
        manifest["control_channel_function"] = {"configfs": "gser.GS0", "bcdDevice": "0x0139",
                                                "interface_class": "0xff",
                                                "endpoints": ["bulk IN", "bulk OUT"]}
        manifest["dart_diagnostics"] = {"kernel_patches": ["kernel/experiments/usb-gadget/dart-diag/dart-diag.patch",
                                                           "kernel/experiments/usb-gadget/dart-diag/dart-diag-2-gen22.patch"],
                                        "apple_dart_c_before": "f48a05cf9ae17cc1871211cfd7a634f75d3bcdc131c0d7e896a8c8a80451a845",
                                        "apple_dart_c_after_part1": "1ed5acf9588650cf9fb7dbba950433c60bbf30d8d0aa3c54f6a4345484db6f29",
                                        "apple_dart_c_after": "b3eb0da83235164e2d514c106ec134d6e24c335ba6e36e0124534fb60ca9b288",
                                        "v2_2_layout_source": "kernel/experiments/usb-gadget/dart-diag/rea-dart-2026-10-18.md",
                                        "init_reads_dart_registers": "through /dev/mem, 32-bit loads, instances 0 and 1 of each port's dart-usbN, both layouts by PARAMS3 version"}
    if args.name == "ilinux-j716c-boot037":
        manifest["linux_patches"] += ("; MTP input path (kernel/experiments/mtp-input): "
                                      "driver-contracts dockchannel-hid 0001 + patches/0002 ring transport, "
                                      "HIDRAW/HID_APPLE/HID_MAGICMOUSE/APPLE_RTKIT_HELPER built in, Stage-B DT "
                                      "with the MTP nodes (stream id 1); job-042")
        manifest["mtp_input"] = {"dt_nodes": list(mtp_input.NEW_NODES), "dart": mtp_input.DART,
                                 "stream_ids": list(mtp_input.SIDS),
                                 "config_set": sorted(mtp_input.CONFIG_SET),
                                 "kernel_parameters_not_in_fixed_arguments": ["dockchannel_hid.mtp_poll_ms=100"]}
    encoded = (json.dumps(manifest, indent=2) + "\n").encode()
    (args.record_dir / "package-manifest.json").write_bytes(encoded)
    data["package-manifest.json"] = encoded
    data["SHA256SUMS"] = "".join(f"{hashlib.sha256(b).hexdigest()}  {n}\n" for n, b in sorted(data.items())).encode()
    (args.record_dir / "intake-manifest-sha256.txt").write_text(hashlib.sha256(data["SHA256SUMS"]).hexdigest() + "\n")
    args.destination.mkdir(parents=True, exist_ok=True)
    archive = args.destination / (args.name + ".tar.gz")
    with archive.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as tar:
            for name, content in sorted(data.items()):
                entry = tarfile.TarInfo(args.name + "/" + name)
                entry.size = len(content)
                entry.mode = 0o644
                tar.addfile(entry, io.BytesIO(content))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sums = f"{digest}  {archive.name}\n"
    (args.destination / "SHA256SUMS").write_text(sums)
    (args.record_dir / "archive-sha256.txt").write_text(sums)
    print(f"Package: {archive.name}; {archive.stat().st_size} bytes; SHA-256 {digest}")


if __name__ == "__main__":
    main()
