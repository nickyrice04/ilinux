#!/usr/bin/env python3
"""Assemble job 046's Mac-side overlay: an uncompressed newc cpio that the boot test appends to the
VM-built base root, so the files under test can change without the VM (and its shared lock).

It holds, root-owned:
  * the RAM root's own overlay, omarchy-arm64/ram-root/overlay/ (the gadget script, the sshd unit
    and drop-ins, /etc/environment, ...): what is being tested,
  * the test overlay, virtualization/jobs/046-usb-ssh-pipe/test-overlay/ (the self-test service and
    script, the ssh configuration, the HTTPS server, the private-network drop-in),
  * tools/m1n1-client/connect-proxy.py, the M1's proxy, run by the self-test,
  * the unit enablement as symlinks (the self-test service, the masks, the default target).
Only public material: the keys and the certificate come from the VM-built base.

usage: make-overlay.py --out FILE [--list]
"""
import argparse
import hashlib
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PRODUCT = REPO / "omarchy-arm64/ram-root/overlay"
TEST = HERE / "test-overlay"
PROXY = REPO / "tools/m1n1-client/connect-proxy.py"
MASKED = ("systemd-firstboot.service", "getty@tty1.service", "serial-getty@hvc0.service",
          "systemd-networkd-wait-online.service", "systemd-homed.service")
LINKS = {
    "etc/systemd/system/multi-user.target.wants/ilinux-selftest.service": "/etc/systemd/system/ilinux-selftest.service",
    "etc/systemd/system/default.target": "/usr/lib/systemd/system/multi-user.target",
}
LINKS.update({"etc/systemd/system/" + unit: "/dev/null" for unit in MASKED})
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


def collect():
    """{path: (mode, data)} for files and symlinks; later sources replace earlier ones."""
    files = {}
    for src in (PRODUCT, TEST):
        for rel, mode, data in tree(src):
            files[rel] = (stat.S_IFREG | mode, data)
    files["usr/local/lib/ilinux-test/connect-proxy.py"] = (stat.S_IFREG | 0o644, PROXY.read_bytes())
    for path, target in LINKS.items():
        files[path] = (stat.S_IFLNK | 0o777, target.encode())
    for path, (_, data) in files.items():
        if any(marker in data for marker in KEY_MARKERS):
            raise SystemExit("private key material in the overlay: %s" % path)
        if path.startswith("/") or ".." in path.split("/"):
            raise SystemExit("bad path in the overlay: " + path)
    return files


def directories(paths):
    """Every parent directory of the paths, shallowest first."""
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


def build():
    files = collect()
    entries = [(d, stat.S_IFDIR | 0o755, b"") for d in directories(files)]
    entries += [(path, mode, data) for path, (mode, data) in sorted(files.items())]
    return newc(entries), entries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, help="the cpio to write")
    parser.add_argument("--list", action="store_true", help="print every entry with its mode and SHA-256")
    args = parser.parse_args(argv)
    blob, entries = build()
    Path(args.out).write_bytes(blob)
    if args.list:
        for name, mode, data in entries:
            kind = "d" if stat.S_ISDIR(mode) else "l" if stat.S_ISLNK(mode) else "-"
            print("%s %04o %8d %s %s" % (kind, mode & 0o7777, len(data),
                                         hashlib.sha256(data).hexdigest()[:12] if data else "-" * 12, name))
    print("overlay: %d entries (%d directories), %d bytes, SHA-256 %s" % (
        len(entries), sum(stat.S_ISDIR(m) for _, m, _ in entries), len(blob), hashlib.sha256(blob).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
