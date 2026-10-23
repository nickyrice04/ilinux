#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the public data inputs before executing any upstream build in the VM."""
import hashlib
import json
from pathlib import Path
import sys


def check(path, size, digest):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise ValueError("input file type or size mismatch")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    if h.hexdigest() != digest:
        raise ValueError("input digest mismatch")


def main():
    job, source = map(Path, sys.argv[1:])
    count = 0
    for manifest, key in (("sources.json", "sources"), ("packages.json", "packages")):
        data = json.loads((job / manifest).read_text())
        if data["schema"] != 1:
            raise ValueError("unsupported manifest")
        for row in data[key]:
            name = row["filename"]
            if Path(name).name != name:
                raise ValueError("nonlocal filename")
            check(source / name, row["size"], row["sha256"])
            count += 1
            if key == "packages":
                check(source / (name + ".sig"), row["signature_size"], row["signature_sha256"])
                count += 1
    print(json.dumps({"result": "INPUT_HASHES_PASS", "files": count,
                      "package_trust": "PENDING_PACMAN_VERIFICATION",
                      "native_operations": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
