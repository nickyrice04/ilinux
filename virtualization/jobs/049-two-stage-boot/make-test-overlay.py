#!/usr/bin/env python3
"""Assemble job 049's Mac-side test overlay: an uncompressed newc cpio that run-qemu.sh appends after
stage one (out/stage1.cpio.zst, unchanged) and the VM-built test base (python3, the Linux usb-pipe, the
VM key), so the test and the M1's files can change without the VM and its lock.

It holds, root-owned:
  * the test overlay, virtualization/jobs/049-two-stage-boot/test-overlay/: the M1's part against stage
    one (ilinux049-m1.service, m1-stage1.sh), the hook that adds the stage-two probe to the unpacked root,
    that probe and the shared helpers;
  * the M1's own files from the working tree, as the M1 runs them, under usr/local/lib/ilinux-test/m1/
    (a repository root in miniature): tools/m1n1-client/m5-stage2.py, tools/m1n1-client/m5-ssh-config,
    native/boot/omarchy-root-manifest.json (with --manifest, the given pin record in its place, e.g. one in
    build/ that waits for its handoff);
  * the unit enablement as symlinks, and serial-getty@hvc0 masked so that no login prompt shares the
    test console;
  * with --omarchy-key PUB: that public key as /etc/ssh/authorized_keys.d/omarchy, root-owned 0644 as
    stage one installs the operator's (job 039's layout), so the test logs in as omarchy too.
Only public material: the VM key pair comes from the VM-built test base.

usage: make-test-overlay.py --out FILE [--omarchy-key PUB] [--list]
"""
import argparse
import hashlib
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TEST = HERE / "test-overlay"
M1 = "usr/local/lib/ilinux-test/m1/"
M1_FILES = ("tools/m1n1-client/m5-stage2.py", "tools/m1n1-client/m5-ssh-config")
PIN = "native/boot/omarchy-root-manifest.json"   # where the M1 keeps stage two's pin (m5-stage2.py's default)
LINKS = {
    "etc/systemd/system/multi-user.target.wants/ilinux049-m1.service": "/etc/systemd/system/ilinux049-m1.service",
    "etc/systemd/system/serial-getty@hvc0.service": "/dev/null",
}
KEY_MARKERS = (b"PRIVATE KEY-----", b"BEGIN OPENSSH PRIVATE")


def tree(src):
    """(path relative to src, mode, data) of every regular file under src."""
    for path in sorted(src.rglob("*")):
        if path.name == ".DS_Store":
            continue
        if path.is_symlink():
            raise SystemExit("symlink in an overlay source: %s" % path)
        if path.is_file():
            executable = path.stat().st_mode & 0o111
            yield path.relative_to(src).as_posix(), 0o755 if executable else 0o644, path.read_bytes()


def collect(omarchy_key=None, manifest=PIN):
    """{path: (mode, data)} for files and symlinks."""
    files = {}
    if omarchy_key is not None:
        key = Path(omarchy_key).read_bytes()
        if len(key.splitlines()) != 1 or not key.startswith(b"ssh-ed25519 "):
            raise SystemExit("--omarchy-key must be one ssh-ed25519 public key line")
        files["etc/ssh/authorized_keys.d/omarchy"] = (stat.S_IFREG | 0o644, key)
    for rel, mode, data in tree(TEST):
        files[rel] = (stat.S_IFREG | mode, data)
    for rel in M1_FILES:
        files[M1 + rel] = (stat.S_IFREG | 0o644, (REPO / rel).read_bytes())
    # stage two's pin record, at the path the M1 keeps it (a record in build/ before its handoff)
    path = Path(manifest)
    files[M1 + PIN] = (stat.S_IFREG | 0o644, (path if path.is_absolute() else REPO / path).read_bytes())
    for path, target in LINKS.items():
        files[path] = (stat.S_IFLNK | 0o777, target.encode())
    for path, (_, data) in files.items():
        if any(marker in data for marker in KEY_MARKERS):
            raise SystemExit("private key material in the overlay: %s" % path)
        if path.startswith("/") or ".." in path.split("/"):
            raise SystemExit("bad path in the overlay: " + path)
    return files


def directories(paths):
    """Every parent directory of the paths, shallowest first (all 0755, as they are in the root)."""
    found = set()
    for path in paths:
        parts = path.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            found.add("/".join(parts[:i]))
    return sorted(found, key=lambda d: (d.count("/"), d))


def newc(entries):
    """Uncompressed newc cpio of (name, mode, data): root-owned, mtime 0, with the trailer."""
    out = bytearray()
    for ino, (name, mode, data) in enumerate(entries + [("TRAILER!!!", 0, b"")], 1):
        if name == "TRAILER!!!":
            ino = 0
        nlink = 2 if stat.S_ISDIR(mode) else 1
        fields = (ino, mode, 0, 0, nlink, 0, len(data), 0, 0, 0, 0, len(name) + 1, 0)
        out += b"070701" + b"".join(b"%08X" % f for f in fields) + name.encode() + b"\0"
        out += b"\0" * (-len(out) % 4) + data
        out += b"\0" * (-len(out) % 4)
    return bytes(out)


def build(omarchy_key=None, manifest=PIN):
    files = collect(omarchy_key, manifest)
    entries = [(d, stat.S_IFDIR | 0o755, b"") for d in directories(files)]
    entries += [(path, mode, data) for path, (mode, data) in sorted(files.items())]
    return newc(entries), entries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, help="the cpio to write")
    parser.add_argument("--list", action="store_true", help="print every entry with its mode and SHA-256")
    parser.add_argument("--omarchy-key", help="a public key to authorize for omarchy (root-owned 0644)")
    parser.add_argument("--manifest", default=PIN,
                        help="stage two's pin record for the M1's copy (default %(default)s), relative to the repository")
    args = parser.parse_args(argv)
    blob, entries = build(args.omarchy_key, args.manifest)
    Path(args.out).write_bytes(blob)
    if args.list:
        for name, mode, data in entries:
            kind = "d" if stat.S_ISDIR(mode) else "l" if stat.S_ISLNK(mode) else "-"
            print("%s %04o %8d %s %s" % (kind, mode & 0o7777, len(data),
                                         hashlib.sha256(data).hexdigest()[:12] if data else "-" * 12, name))
    print("test overlay: %d entries (%d directories), %d bytes, SHA-256 %s" % (
        len(entries), sum(stat.S_ISDIR(m) for _, m, _ in entries), len(blob), hashlib.sha256(blob).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
