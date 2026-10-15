#!/usr/bin/env python3
"""Build the private hv package: pinned manifest, staging directory and archive.

Input is the VM job's out/ directory (virtualization/jobs/0NN-*/out) holding
export/{m1n1-hv.bin, m1n1-hv-symbols.txt, System.map[-bootNNN], toolchain.txt}.
Everything that matters is cross-checked before anything is written:
the patch files named on the command line must be the ones the job recorded in
toolchain.txt, the version marker and symbol offsets come from the build, and
each guest's System.map is tied to a guest Image digest.

Private iLinux tooling; never for upstream.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile

HERE = Path(__file__).resolve().parent
M1N1_COMMIT = "57a9339ffd1876e78297b17d34dece8cff8fa1ba"
REQUIRED_SYMBOLS = ("kboot_prepare_hv_guest", "hv_ilinux_timers_reset", "ilinux_crumb")
OFFSET_SYMBOLS = {"dt": "hv_dt_pointer_offset",
                  "hv_ilinux_single_cpu": "hv_single_cpu_offset",
                  "hv_ilinux_init_failed": "hv_init_failed_offset"}
PRIVATE_OPCODE = 0x7F0


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_nm(text):
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3:
            out.setdefault(parts[2], int(parts[0], 16))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="VM job out directory (contains export/)")
    ap.add_argument("--name", required=True, help="package name, e.g. ilinux-j716c-hv003")
    ap.add_argument("--marker", required=True, help="m1n1 version marker, e.g. ilinux-57a9339-hv003")
    ap.add_argument("--patch", type=Path, action="append", required=True,
                    help="m1n1 patch files in application order")
    ap.add_argument("--guest", action="append", required=True, metavar="IMAGE_SHA256=PACKAGE=MAPFILE",
                    help="guest Image digest, guest package name and its System.map file in export/")
    ap.add_argument("--destination", type=Path, required=True)
    ap.add_argument("--manifest-out", type=Path, default=HERE / "hv-manifest.json",
                    help="where to write the manifest (default: the repository's native/hv/hv-manifest.json)")
    ap.add_argument("--build", default="make -j6 ARCH= BUILDSTD=1 with M1N1_VERSION_TAG set per package")
    args = ap.parse_args(argv)

    export = args.out / "export"
    hv = (export / "m1n1-hv.bin").read_bytes()
    symbols_text = (export / "m1n1-hv-symbols.txt").read_text()
    syms = parse_nm(symbols_text)
    toolchain = (export / "toolchain.txt").read_text()

    patches = []
    for path in args.patch:
        digest = sha(path.read_bytes())
        if digest not in toolchain:
            raise SystemExit("patch %s (%s) is not the one the job recorded in toolchain.txt" % (path.name, digest))
        patches.append({"file": path.name, "sha256": digest})

    marker = ("##m1n1_ver##" + args.marker).encode()
    if hv.count(marker + b"\0") != 1:
        raise SystemExit("version marker must occur exactly once in m1n1-hv.bin")
    marker_offset = hv.index(marker + b"\0")

    for name in REQUIRED_SYMBOLS:
        if name not in syms:
            raise SystemExit("symbol missing from the build: " + name)
    offsets = {}
    for symbol, key in OFFSET_SYMBOLS.items():
        if symbol not in syms or not syms[symbol] < len(hv):
            raise SystemExit("symbol offset missing or outside the image: " + symbol)
        offsets[key] = syms[symbol]

    guests = {}
    files = {"m1n1-hv.bin": hv, "m1n1-hv-symbols.txt": symbols_text.encode(),
             "toolchain.txt": toolchain.encode()}
    for spec in args.guest:
        digest, package, mapfile = spec.split("=")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise SystemExit("bad guest digest: " + digest)
        data = (export / mapfile).read_bytes()
        files[mapfile] = data
        guests[digest] = {"package": package, "system_map": mapfile}

    manifest = {
        "schema": 2,
        "package": args.name,
        "target": "Mac17,6 / J716c / t6050",
        "native_tested": False,
        "m1n1_commit": M1N1_COMMIT,
        "m1n1_patches": patches,
        "m1n1_build": args.build,
        "hv_version_marker": "##m1n1_ver##" + args.marker,
        "hv_version_offset": marker_offset,
        "hv_private_opcode": PRIVATE_OPCODE,
        "required_symbols": list(REQUIRED_SYMBOLS),
        "guests": guests,
        "files": {n: {"size": len(b), "sha256": sha(b)} for n, b in sorted(files.items())},
    }
    manifest.update(offsets)
    encoded = (json.dumps(manifest, indent=2) + "\n").encode()
    archive = args.destination / (args.name + ".tar.gz")
    if archive.exists() or archive.is_symlink():
        # Checked before the manifest is written: a refused run must not rewrite it.
        raise SystemExit("archive already exists: " + str(archive))
    args.manifest_out.write_bytes(encoded)

    members = dict(files)
    members["hv-manifest.json"] = encoded
    sums = "".join("%s  %s\n" % (sha(b), n) for n, b in sorted(members.items())).encode()
    members["SHA256SUMS"] = sums
    args.destination.mkdir(parents=True, exist_ok=True)
    with archive.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as tar:
            for name, content in sorted(members.items()):
                entry = tarfile.TarInfo(args.name + "/" + name)
                entry.size = len(content)
                entry.mode = 0o644
                tar.addfile(entry, io.BytesIO(content))
    stage = args.destination / args.name
    stage.mkdir(exist_ok=True)
    for name, content in members.items():
        (stage / name).write_bytes(content)
    digest = sha(archive.read_bytes())
    (args.destination / "SHA256SUMS").write_text("%s  %s\n" % (digest, archive.name))
    print("Package %s: %d bytes, SHA-256 %s" % (archive.name, archive.stat().st_size, digest))
    print("hv image %s %d bytes; marker at %d" % (sha(hv), len(hv), marker_offset))
    return 0


if __name__ == "__main__":
    sys.exit(main())
