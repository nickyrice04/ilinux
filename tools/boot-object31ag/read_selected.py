#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read the configured lab boot object without changing boot state.

Default: help only. --fixture is offline. --live requires local root on Mac17,6.
Private policy, identifiers, paths and captured command output stay in memory.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
LAB_MOUNT = "/Volumes/iLinux Boot Lab"
LAB_NAME = "iLinux Boot Lab"
MAX_FILE = 8 * 1024 * 1024
MAX_METADATA = 1024 * 1024
MAX_POLICY = 65536
MAX_DER_DEPTH = 12
MAX_DER_NODES = 256
KNOWN = {
    "31AF": (442368, "166bea74bf515473057dfd29dc89127d04768945a451e497cc80a9fc53d4951b"),
    "BOOT021": (3932160, "ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664"),
}
DEFAULT_REFERENCES = {
    "31AF": ROOT / "build/research31af/published-check/ilinux-31af-immutable.macho",
    "BOOT021": ROOT / "build/research31af/package/m1n1-boot021.bin",
}
UUID = re.compile(r"[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\Z")
CONTAINER = re.compile(r"disk[0-9]+\Z")
VOLUME = re.compile(r"disk[0-9]+s[0-9]+\Z")
HASH_COMPONENT = re.compile(rb"(?:[0-9A-Fa-f]{2}){16,64}\Z")


class Refused(Exception):
    """Internal failure. Never print its contents or a chained exception."""


def require(condition):
    if not condition:
        raise Refused()


def uuid(value):
    require(isinstance(value, str) and UUID.fullmatch(value) is not None)
    return value


def container(value):
    require(isinstance(value, str) and CONTAINER.fullmatch(value) is not None)
    return value


def volume(value):
    require(isinstance(value, str) and VOLUME.fullmatch(value) is not None)
    return value


def one(items):
    require(isinstance(items, list) and len(items) == 1)
    return items[0]


def guard_target(lab, current, apfs):
    """Validate supplied disk metadata; perform no command, mount or file read."""
    require(all(isinstance(x, dict) for x in (lab, current, apfs)))
    require(lab.get("VolumeName") == LAB_NAME and lab.get("MountPoint") == LAB_MOUNT)
    require(current.get("MountPoint") == "/")
    group = uuid(lab.get("APFSVolumeGroupID"))
    require(group.lower() != uuid(current.get("APFSVolumeGroupID")).lower())
    lab_uuid = uuid(lab.get("VolumeUUID"))
    require(lab_uuid.lower() != uuid(current.get("VolumeUUID")).lower())
    ref = container(lab.get("APFSContainerReference"))
    containers = apfs.get("Containers")
    require(isinstance(containers, list) and len(containers) <= 128)
    require(all(isinstance(c, dict) for c in containers))
    ct = one([c for c in containers if c.get("ContainerReference") == ref])
    vols = ct.get("Volumes")
    require(isinstance(vols, list) and 0 < len(vols) <= 256)
    require(all(isinstance(v, dict) for v in vols))
    ids = [volume(v.get("DeviceIdentifier")) for v in vols]
    uuids = [uuid(v.get("APFSVolumeUUID")).lower() for v in vols]
    require(len(set(ids)) == len(ids) and len(set(uuids)) == len(uuids))
    system = one([v for v in vols if v["APFSVolumeUUID"].lower() == lab_uuid.lower()])
    require(system.get("Roles") == ["System"] and system.get("Name") == LAB_NAME)
    require(system["DeviceIdentifier"] == volume(lab.get("DeviceIdentifier")))
    preboot = one([v for v in vols if v.get("Roles") == ["Preboot"]])
    return {"group": group, "container": ref, "preboot": preboot}


def guard_preboot(target, info):
    require(isinstance(info, dict))
    entry = target["preboot"]
    require(info.get("APFSContainerReference") == target["container"])
    require(uuid(info.get("VolumeUUID")).lower() == entry["APFSVolumeUUID"].lower())
    require(info.get("VolumeName") == entry.get("Name"))
    require(info.get("DeviceIdentifier") == entry["DeviceIdentifier"])
    mount = info.get("MountPoint")
    require(isinstance(mount, str) and mount.startswith("/") and mount not in ("/", LAB_MOUNT))
    require(all(p not in ("", ".", "..") for p in mount.split("/")[1:]))
    return mount


def parse_policy(raw):
    """Public Asahi labels; component grammar is a local conservative safety cap."""
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_POLICY and b"\0" not in raw)
    values = {}
    for key in (b"coih", b"nsih"):
        require(raw.count(b"(" + key + b")") == 1)
        pattern = rb"(?m)^[^\r\n]*\(" + key + rb"\): ([^\r\n]*)\r?$"
        value = one(re.findall(pattern, raw))
        if value == b"absent":
            values[key.decode()] = None
        else:
            require(HASH_COMPONENT.fullmatch(value) is not None)
            values[key.decode()] = value.decode("ascii")
    if values["coih"] is not None:
        require(values["nsih"] is not None)
    return values


def selected_path(target, preboot_mount, selected):
    require(selected["coih"] is not None and selected["nsih"] is not None)
    return Path(preboot_mount) / target["group"] / "boot" / selected["nsih"] / \
        "System/Library/Caches/com.apple.kernelcaches" / ("kernelcache.custom." + selected["coih"])


def secure_open(path, directory=False):
    """Walk absolute components using openat/O_NOFOLLOW; no symlink traversal."""
    path = os.fspath(path)
    require(isinstance(path, str) and path.startswith("/") and "\0" not in path)
    parts = path.split("/")[1:]
    require(parts and all(p not in ("", ".", "..") for p in parts))
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open("/", flags | os.O_DIRECTORY)
    try:
        for n, part in enumerate(parts):
            child = os.open(part, flags | (os.O_DIRECTORY if directory or n < len(parts) - 1 else 0), dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def secure_read(path, limit=MAX_FILE):
    fd = secure_open(path)
    with os.fdopen(fd, "rb") as f:
        before = os.fstat(f.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        data = f.read(limit + 1)
        after = os.fstat(f.fileno())
        require(len(data) == before.st_size and len(data) <= limit)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns))
        return data


def load_references(paths, workspace=ROOT):
    require(set(paths) == set(KNOWN))
    references = {}
    for label, path in paths.items():
        path = Path(path).absolute()
        require(path != workspace and workspace in path.parents)
        expected_size, expected_hash = KNOWN[label]
        data = secure_read(path, expected_size)
        require(len(data) == expected_size and hashlib.sha256(data).hexdigest() == expected_hash)
        references[label] = data
    return references


def der_tree(data):
    """Bounded DER framing; context a0/a1 metadata stays opaque, including tags."""
    count = [0]

    def node(pos, end, depth):
        count[0] += 1
        require(depth <= MAX_DER_DEPTH and count[0] <= MAX_DER_NODES and pos + 2 <= end)
        tag = data[pos]
        require(tag & 31 != 31 and tag != 0)
        length = data[pos + 1]
        start = pos + 2
        if length & 128:
            n = length & 127
            require(1 <= n <= 4 and start + n <= end and data[start] != 0)
            length = int.from_bytes(data[start:start + n], "big")
            require(length >= 128)
            start += n
        stop = start + length
        require(stop <= end)
        children = []
        if tag & 32 and tag not in (0xa0, 0xa1):
            cursor = start
            while cursor < stop:
                child, cursor = node(cursor, stop, depth + 1)
                children.append(child)
            require(cursor == stop)
        return (tag, start, stop, children), stop

    require(isinstance(data, bytes) and 0 < len(data) <= MAX_FILE)
    root, end = node(0, len(data), 0)
    require(end == len(data))
    return root


def der_payload(data):
    root = der_tree(data)

    def text(node):
        require(node[0] == 0x16 and not node[3])
        value = data[node[1]:node[2]]
        require(all(c < 128 for c in value))
        return value

    require(root[0] == 0x30 and root[3])
    children = root[3]
    magic = text(children[0])
    if magic == b"IMG4":
        require(len(children) >= 2 and children[1][0] == 0x30)
        trailers = [n[0] for n in children[2:]]
        require(all(t in (0xa0, 0xa1) for t in trailers) and len(set(trailers)) == len(trailers))
        children = children[1][3]
        require(children and text(children[0]) == b"IM4P")
    else:
        require(magic == b"IM4P")
    require(len(children) in (4, 5))
    require(len(text(children[1])) == 4 and all(32 <= c < 127 for c in text(children[1])))
    description = text(children[2])
    require(len(description) <= 4096)
    payload = children[3]
    require(payload[0] == 0x04 and not payload[3])
    if len(children) == 5:
        require(children[4][0] == 0x04 and not children[4][3])
    return data[payload[1]:payload[2]]


def identify(data, references):
    for label, expected in references.items():
        if data == expected:
            return label
    try:
        payload = der_payload(data)
    except (Refused, ValueError, IndexError):
        return "UNKNOWN"
    for label, expected in references.items():
        if payload == expected:
            return label
    return "UNKNOWN"


def capture(argv, cap=MAX_METADATA):
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=20, check=False,
                            env={"PATH": "/usr/bin:/usr/sbin:/bin:/sbin", "LANG": "C", "LC_ALL": "C"})
    require(result.returncode == 0 and len(result.stdout) <= cap)
    return result.stdout


def disk_info(target):
    value = plistlib.loads(capture(["/usr/sbin/diskutil", "info", "-plist", target]))
    require(isinstance(value, dict))
    return value


def live(references):
    require(sys.platform == "darwin" and os.geteuid() == 0)
    require(capture(["/usr/sbin/sysctl", "-n", "hw.model"], 64).strip() == b"Mac17,6")
    fd = secure_open(LAB_MOUNT, directory=True)
    os.close(fd)
    lab, current = disk_info(LAB_MOUNT), disk_info("/")
    apfs = plistlib.loads(capture(["/usr/sbin/diskutil", "apfs", "list", "-plist"]))
    target = guard_target(lab, current, apfs)
    preboot_mount = guard_preboot(target, disk_info(target["preboot"]["DeviceIdentifier"]))
    fd = secure_open(preboot_mount, directory=True)
    os.close(fd)
    selected = parse_policy(capture(["/usr/bin/bputil", "-d", "-v", target["group"]], MAX_POLICY))
    if selected["coih"] is None:
        return "NO_CUSTOM_OBJECT"
    return identify(secure_read(selected_path(target, preboot_mount, selected)), references)


def fixture(path, references):
    path = Path(path).absolute()
    require(ROOT in path.parents)
    value = json.loads(secure_read(path, MAX_METADATA))
    target = guard_target(value["lab_info"], value["root_info"], value["apfs_list"])
    mount = guard_preboot(target, value["preboot_info"])
    require(ROOT in Path(mount).absolute().parents)
    selected = parse_policy(value["policy_text"].encode("ascii"))
    if selected["coih"] is None:
        return "NO_CUSTOM_OBJECT"
    return identify(secure_read(selected_path(target, mount, selected)), references)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Local root, M5 target only; no writes or mounts")
    mode.add_argument("--fixture", type=Path, help="Offline synthetic metadata fixture only")
    parser.add_argument("--reference-31af", type=Path, default=DEFAULT_REFERENCES["31AF"])
    parser.add_argument("--reference-boot021", type=Path, default=DEFAULT_REFERENCES["BOOT021"])
    args = parser.parse_args(argv)
    if not args.live and args.fixture is None:
        parser.print_help()
        return 0
    try:
        references = load_references({"31AF": args.reference_31af, "BOOT021": args.reference_boot021})
        label = live(references) if args.live else fixture(args.fixture, references)
    except BaseException:
        # Never stringify an exception: it may include policy/identifiers/paths.
        print(json.dumps({"read_only": True, "match": "REFUSED"}, sort_keys=True))
        return 2
    print(json.dumps({"read_only": True, "match": label}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
