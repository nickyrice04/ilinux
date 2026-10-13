#!/usr/bin/env python3
"""Read matching modules from the project's existing Arch rootfs archive.

Nothing from the archive is executed on the host. No archive path is extracted.
"""
import argparse
import hashlib
import json
import struct
import tarfile
from pathlib import Path

VERSION = "7.1.6-1-aarch64-ARCH"
MODULES = {
    "fs/fuse/fuse.ko", "fs/fuse/virtiofs.ko", "net/core/failover.ko",
    "drivers/net/net_failover.ko", "drivers/net/virtio_net.ko",
}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("arch_rootfs", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    found = {}
    prefix = f"usr/lib/modules/{VERSION}/kernel/"
    with tarfile.open(args.arch_rootfs, "r|gz") as archive:
        for member in archive:
            name = member.name.removeprefix("./")
            relative = name.removeprefix(prefix)
            if not name.startswith(prefix) or relative not in MODULES:
                continue
            if relative in found or not member.isfile() or member.size > 2 * 1024 * 1024:
                raise ValueError("unexpected module archive entry")
            data = archive.extractfile(member).read()
            if data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", data, 18)[0] != 183:
                raise ValueError("module is not little-endian ARM64 ELF")
            if f"vermagic={VERSION} ".encode() not in data:
                raise ValueError("module kernel version mismatch")
            found[relative] = data
    if set(found) != MODULES:
        raise ValueError("archive lacks required modules; do not mix kernel versions")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"kernel_release": VERSION, "modules": []}
    for name, data in sorted(found.items()):
        destination = args.output / Path(name).name
        with destination.open("xb") as out:
            out.write(data)
        manifest["modules"].append({"name": destination.name, "sha256": hashlib.sha256(data).hexdigest()})
    with (args.output / "manifest.json").open("x") as out:
        out.write(json.dumps(manifest, indent=2) + "\n")
