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

FILES = ("Image", "t6050-j716c.dtb", "initramfs.cpio.gz", "kernel.config",
         "t6050-j716c-stage-b.dtb", "initramfs-stage-b.cpio.gz", "m1n1.bin",
         "m1n1-build-config.h", "m1n1-LICENSE", "m1n1-revision.txt", "diag-init.c", "toolchain.txt")
ORIGINAL = {
    "Image": "f9cf7c0046712cdf60e686e7a13d998b3e4d1b55a1d64de5dba997aa9a77f704",
    "t6050-j716c.dtb": "5d6fe64812b05e8c5d42ce3b97e3ede4c675e7a9a59d8fcf85d6906ef8daac9e",
    "initramfs.cpio.gz": "15565c4bc7371dd40ce6387305af40391140fda5a871e9012aebd65e95162618",
}
NAME = "ilinux-j716c-boot021"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="VM job out directory containing export/")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--name", choices=(NAME, "ilinux-j716c-boot022", "ilinux-j716c-boot024", "ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031"), default=NAME)
    args = parser.parse_args()
    data = {name: (args.out / "export" / name).read_bytes() for name in FILES}
    checks = {n: {"size": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in data.items()}
    for name, digest in ORIGINAL.items():
        if name == "Image" and args.name in ("ilinux-j716c-boot024", "ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031"):
            continue
        if checks[name]["sha256"] != digest:
            raise ValueError("original job-020 artifact changed: " + name)
    check_stage_b(data["t6050-j716c-stage-b.dtb"])
    forbidden = {"serial-number", "mac-address", "local-mac-address", "system-id",
                 "uuid", "ecid", "unique-chip-id", "die-id", "nonce"}
    for name in ("t6050-j716c.dtb", "t6050-j716c-stage-b.dtb"):
        if any(forbidden.intersection(node) for node in properties(data[name]).values()):
            raise ValueError("identifying properties in package DT")
    symbols = {}
    if args.name in ("ilinux-j716c-boot022", "ilinux-j716c-boot024", "ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031"):
        previous = {"ilinux-j716c-boot022": "boot021", "ilinux-j716c-boot024": "boot022",
                    "ilinux-j716c-boot025": "boot024", "ilinux-j716c-boot027": "boot025", "ilinux-j716c-boot028": "boot027", "ilinux-j716c-boot029": "boot028", "ilinux-j716c-boot030": "boot029", "ilinux-j716c-boot031": "boot030"}[args.name]
        allowed_change = "t6050-j716c-stage-b.dtb" if previous == "boot021" else "Image"
        baseline = json.loads((HERE / (previous + "-package-manifest.json")).read_text())
        for name, info in baseline["files"].items():
            if name != allowed_change and checks[name] != info:
                raise ValueError("unexpected payload change: " + name)
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
    if args.name in ("ilinux-j716c-boot024", "ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031"):
        from entry_guard import descriptor_offset
        manifest["linux_patches"] = ("kernel/patches/t6050/0001-0007 plus "
                                     "kernel/experiments/early-framebuffer/apply.py; job-024")
        manifest["early_framebuffer_descriptor_offset"] = descriptor_offset(data["Image"])
        if args.name in ("ilinux-j716c-boot025", "ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031"):
            manifest["linux_patches"] += "; kernel/experiments/aic-t6050/t6050-bringup.patch; job-025"
    if args.name in ("ilinux-j716c-boot027", "ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031"):
        manifest["linux_patches"] += "; kernel/experiments/deferred-probe/apply.py; job-027"
    if args.name in ("ilinux-j716c-boot028", "ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031"):
        manifest["linux_patches"] += "; kernel/experiments/schedule-boundary/apply.py; job-028"
    if args.name in ("ilinux-j716c-boot029", "ilinux-j716c-boot030", "ilinux-j716c-boot031"):
        manifest["linux_patches"] += "; kernel/experiments/context-display/apply.py; job-029"
    if args.name in ("ilinux-j716c-boot030", "ilinux-j716c-boot031"):
        manifest["linux_patches"] += "; kernel/experiments/probe-path/apply.py; job-030"
    if args.name == "ilinux-j716c-boot031":
        manifest["linux_patches"] += "; kernel/experiments/gpio-handoff/apply.py; job-031"
    encoded = (json.dumps(manifest, indent=2) + "\n").encode()
    (HERE / "package-manifest.json").write_bytes(encoded)
    data["package-manifest.json"] = encoded
    data["SHA256SUMS"] = "".join(f"{hashlib.sha256(b).hexdigest()}  {n}\n" for n, b in sorted(data.items())).encode()
    (HERE / "intake-manifest-sha256.txt").write_text(hashlib.sha256(data["SHA256SUMS"]).hexdigest() + "\n")
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
    (HERE / "archive-sha256.txt").write_text(sums)
    print(f"Package: {archive.name}; {archive.stat().st_size} bytes; SHA-256 {digest}")


if __name__ == "__main__":
    main()
