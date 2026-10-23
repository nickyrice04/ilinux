#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Conservative VM package disk preflight; no mutation, installation or network."""
import json
import os
from pathlib import Path
import re
import sys
import tarfile

HEADROOM = 128 * 1024 * 1024
MAX_PACKAGE_SIZE = 2 * 1024 * 1024 * 1024


def fields(text):
    result = {}
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        if not lines or not re.fullmatch(r"%[A-Z0-9_]+%", lines[0]):
            raise ValueError("invalid package database record")
        key = lines[0][1:-1]
        if key in result:
            raise ValueError("duplicate package database field")
        result[key] = lines[1:]
    return result


def one(data, key):
    value = data.get(key)
    if type(value) is not list or len(value) != 1 or not value[0]:
        raise ValueError("missing package metadata")
    return value[0]


def size(value):
    if type(value) is str and re.fullmatch(r"[0-9]{1,12}", value):
        value = int(value)
    if type(value) is not int or not 0 < value <= MAX_PACKAGE_SIZE:
        raise ValueError("invalid installed size")
    return value


def requirements(packages, installed, available):
    if type(available) is not int or available < 0:
        raise ValueError("invalid available space")
    rows, additions, replacement_peak = [], 0, 0
    names = set()
    for package in packages:
        name, version = package["name"], package["version"]
        if type(name) is not str or not re.fullmatch(r"[a-z0-9][a-z0-9+_.-]{0,127}", name):
            raise ValueError("invalid package name")
        if name in names:
            raise ValueError("duplicate package")
        names.add(name)
        if type(version) is not str or not 0 < len(version) <= 128:
            raise ValueError("invalid package version")
        new = size(package["installed_size"])
        old_version, old = installed.get(name, (None, 0))
        if old_version is not None:
            old = size(old)
        if old_version == version and old != new:
            raise ValueError("installed metadata differs at identical version")
        changed = old_version != version
        addition = max(new - old, 0) if changed else 0
        additions += addition
        # No credit for shrinking/replaced packages. Add the entire largest
        # changed package again for extraction/replacement working space.
        replacement_peak = max(replacement_peak, new if changed else 0)
        rows.append({"name": name, "installed_version": old_version,
                     "requested_version": version, "installed_bytes": old,
                     "requested_bytes": new, "positive_delta_bytes": addition})
    required = additions + replacement_peak + HEADROOM
    return {"result": "PACKAGE_SPACE_PASS" if available >= required else "PACKAGE_SPACE_REFUSED",
            "available_bytes": available, "positive_delta_bytes": additions,
            "replacement_peak_bytes": replacement_peak, "headroom_bytes": HEADROOM,
            "required_bytes": required, "packages": rows, "operations": 0,
            "signature_verification": "REQUIRED_BY_PACMAN_BEFORE_INSTALL"}


def installed_records(db, wanted):
    paths = sorted(db.glob("*/desc"))
    if len(paths) > 8192:
        raise ValueError("package database bound")
    result = {}
    for path in paths:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise ValueError("package database file")
        record = fields(path.read_text())
        name = one(record, "NAME")
        if name not in wanted:
            continue
        if name in result:
            raise ValueError("duplicate installed package")
        result[name] = (one(record, "VERSION"), size(one(record, "SIZE")))
    return result


def check_package_info(package, source):
    # Read only the bounded .PKGINFO metadata, never extract or execute scripts.
    with tarfile.open(source / package["filename"], "r:xz") as archive:
        member = archive.getmember(".PKGINFO")
        if not member.isfile() or member.size > 64 * 1024:
            raise ValueError("package info bound")
        text = archive.extractfile(member).read().decode()
    info = {}
    for line in text.splitlines():
        if line.startswith(("pkgname = ", "pkgver = ", "size = ")):
            key, value = line.split(" = ", 1)
            if key in info:
                raise ValueError("duplicate package info")
            info[key] = value
    if (info.get("pkgname") != package["name"] or info.get("pkgver") != package["version"] or
            size(info.get("size")) != package["installed_size"]):
        raise ValueError("pinned package info mismatch")


def main():
    job, source = map(Path, sys.argv[1:])
    packages = json.loads((job / "packages.json").read_text())["packages"]
    for package in packages:
        check_package_info(package, source)
    # A split /usr or package database filesystem needs a separate budget.
    if len({os.stat(p).st_dev for p in ("/", "/usr", "/var/lib/pacman")}) != 1:
        raise ValueError("split package filesystems require explicit budgets")
    usage = os.statvfs("/usr")
    report = requirements(packages, installed_records(Path("/var/lib/pacman/local"),
                          {package["name"] for package in packages}),
                          usage.f_bavail * usage.f_frsize)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "PACKAGE_SPACE_PASS" else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, tarfile.TarError):
        print(json.dumps({"result": "PACKAGE_SPACE_REFUSED", "reason": "METADATA_OR_FILESYSTEM",
                          "operations": 0}, sort_keys=True))
        sys.exit(3)
