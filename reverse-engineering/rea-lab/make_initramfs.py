#!/usr/bin/env python3
"""Make a diskless analysis initramfs without running downloaded host code.

Only the digest-pinned Alpine rootfs is accepted. All paths are relative,
and archive contents are written as newc records, never extracted on macOS.
"""
import argparse
import gzip
import hashlib
import io
import stat
import tarfile
from pathlib import Path, PurePosixPath

SHA256 = "5552106ac866be0c46fdff7a2991a1ed85c0464301a1ac87454c41739d5b6431"


def record(out, name, mode, data=b"", rdev=(0, 0)):
    encoded = name.encode() + b"\0"
    fields = (1, mode, 0, 0, 1, 0, len(data), 0, 0, *rdev, len(encoded), 0)
    header = b"070701" + b"".join(f"{x:08x}".encode() for x in fields)
    out.write(header + encoded)
    out.write(b"\0" * (-(len(header) + len(encoded)) % 4))
    out.write(data)
    out.write(b"\0" * (-len(data) % 4))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("rootfs", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--modules", type=Path, help="directory of uncompressed modules matching the boot kernel")
    args = p.parse_args()
    archive = args.rootfs.read_bytes()
    if hashlib.sha256(archive).hexdigest() != SHA256:
        p.error("Alpine 3.23.0 aarch64 rootfs digest mismatch")
    source = Path(__file__).resolve().parent
    with args.output.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as out:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            for entry in tar:
                path = PurePosixPath(entry.name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("unsafe archive path")
                name = str(path)
                if name == ".":
                    continue
                if entry.isdir():
                    record(out, name, stat.S_IFDIR | entry.mode)
                elif entry.issym():
                    record(out, name, stat.S_IFLNK | entry.mode, entry.linkname.encode())
                elif entry.isfile() or entry.islnk():
                    with tar.extractfile(entry) as f:
                        record(out, name, stat.S_IFREG | entry.mode, f.read())
                else:
                    raise ValueError(f"unsupported archive entry: {name}")
        for name in ("init", "net-config"):
            record(out, name, stat.S_IFREG | 0o755, (source / name).read_bytes())
        if args.modules:
            record(out, "modules", stat.S_IFDIR | 0o755)
            for module in sorted(args.modules.glob("*.ko")):
                record(out, "modules/" + module.name, stat.S_IFREG | 0o644, module.read_bytes())
        record(out, "dev/console", stat.S_IFCHR | 0o600, rdev=(5, 1))
        record(out, "dev/null", stat.S_IFCHR | 0o666, rdev=(1, 3))
        record(out, "TRAILER!!!", 0)
    print(f"Created {args.output}; verified Alpine SHA256 {SHA256}")


if __name__ == "__main__":
    main()
