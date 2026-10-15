#!/usr/bin/env python3
"""Stage the boot036 Stage-B initramfs or the VM self-test overlay from a pacman root.

usage:
  stage_initramfs.py ship    ROOT INIT AUTHORIZED_KEYS DEST
  stage_initramfs.py overlay ROOT SELFTEST TEST_KEY DEST

Copies the named programs out of ROOT (packages installed by job 041 with
signature checks) with every shared library they need: the program interpreter
and DT_NEEDED entries, resolved inside ROOT/usr/lib, recursively. Symlinks are
resolved inside ROOT, never on the build machine. Lays out Arch's merged /usr,
writes the account and SSH files, and prints one line per entry (mode, size,
SHA-256, path) for the record. Runs inside the job VM.
"""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

SHIP = ("usr/bin/dropbear", "usr/bin/busybox")
TEST = ("usr/bin/dbclient", "usr/bin/ip", "usr/bin/unshare", "usr/bin/nsenter", "usr/bin/ping")
DENIED_APPLETS = {"reboot", "poweroff", "halt", "linuxrc", "init"}
LOADER = "usr/lib/ld-linux-aarch64.so.1"
FILES = {
    "etc/passwd": "root:x:0:0:root:/root:/bin/sh\n",
    "etc/group": "root:x:0:root\n",
    "etc/shells": "/bin/sh\n/usr/bin/sh\n",
    "etc/nsswitch.conf": "passwd: files\ngroup: files\nshadow: files\nhosts: files\n",
    "etc/hosts": "127.0.0.1 localhost\n::1 localhost\n",
    "etc/hostname": "ilinux-j716c\n",
    "etc/profile": 'export PATH=/usr/bin:/usr/sbin:/bin:/sbin\nexport PS1="\\h:\\w# "\n',
}


def inside(root, rel):
    """Resolve rel inside root, following symlinks as root would see them."""
    for _ in range(40):
        path = root / rel
        if not path.is_symlink():
            return rel
        target = os.readlink(path)
        rel = target.lstrip("/") if target.startswith("/") else os.path.normpath(
            os.path.join(os.path.dirname(rel), target))
        if rel.startswith(".."):
            raise SystemExit("symlink escapes the root: " + str(path))
    raise SystemExit("symlink loop: " + rel)


def elf_deps(path):
    """(interpreter, [DT_NEEDED]) of an ELF64 little-endian file, or None if not ELF."""
    data = path.read_bytes()
    if data[:4] != b"\x7fELF":
        return None
    if data[4] != 2 or data[5] != 1:
        raise SystemExit("not ELF64 LE: " + str(path))
    phoff, = struct.unpack_from("<Q", data, 32)
    phentsize, phnum = struct.unpack_from("<HH", data, 54)
    interp, dynamic, loads = None, None, []
    for i in range(phnum):
        p_type, _, offset, vaddr, _, filesz, _, _ = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phentsize)
        if p_type == 3:
            interp = data[offset:offset + filesz].rstrip(b"\0").decode()
        elif p_type == 2:
            dynamic = (offset, filesz)
        elif p_type == 1:
            loads.append((vaddr, offset, filesz))
    needed = []
    if dynamic:
        tags = []
        for j in range(dynamic[1] // 16):
            tag, value = struct.unpack_from("<qQ", data, dynamic[0] + 16 * j)
            if tag == 0:
                break
            tags.append((tag, value))
        strtab = next(value for tag, value in tags if tag == 5)
        strtab = next(offset + strtab - vaddr for vaddr, offset, filesz in loads
                      if vaddr <= strtab < vaddr + filesz)
        for tag, value in tags:
            if tag == 1:
                needed.append(data[strtab + value:data.index(b"\0", strtab + value)].decode())
    return interp, needed


def copy_closure(root, dest, programs):
    todo, done = list(programs), set()
    while todo:
        rel = todo.pop()
        if rel in done:
            continue
        done.add(rel)
        real = inside(root, rel)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / real, target)
        os.chmod(target, 0o755)
        deps = elf_deps(target)
        if deps is None:
            raise SystemExit("not an ELF program or library: " + rel)
        interp, needed = deps
        if interp:
            if os.path.basename(interp) != os.path.basename(LOADER):
                raise SystemExit("unexpected interpreter %s in %s" % (interp, rel))
            todo.append(LOADER)
        todo += ["usr/lib/" + name for name in needed]
    return done


def busybox_applets(root, dest):
    busybox = dest / "usr/bin/busybox"
    command = [str(busybox), "--list"]
    if elf_deps(busybox)[0]:
        command = [str(dest / LOADER), "--library-path", str(dest / "usr/lib"), str(busybox), "--list"]
    applets = subprocess.run(command, check=True, capture_output=True, text=True).stdout.split()
    for applet in sorted(set(applets) - DENIED_APPLETS):
        link = dest / "usr/bin" / applet
        if not link.exists() and not link.is_symlink():
            link.symlink_to("busybox")


def write(dest, rel, text, mode=0o644):
    path = dest / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text if isinstance(text, bytes) else text.encode())
    os.chmod(path, mode)


def packages(root):
    lines = []
    for desc in sorted((root / "var/lib/pacman/local").glob("*/desc")):
        fields = desc.read_text().split("\n\n")
        info = {f.split("\n")[0]: f.split("\n")[1] for f in fields if f.startswith("%")}
        lines.append("%s %s" % (info["%NAME%"], info["%VERSION%"]))
    return "\n".join(lines) + "\n"


def ship(root, init, keys, dest):
    for rel in ("proc", "sys", "dev", "run", "usr/bin", "usr/lib", "var/log"):
        (dest / rel).mkdir(parents=True, exist_ok=True)
    for rel, mode in (("tmp", 0o1777), ("root", 0o700), ("root/.ssh", 0o700), ("etc/dropbear", 0o700)):
        (dest / rel).mkdir(parents=True, exist_ok=True)
        os.chmod(dest / rel, mode)
    for link, target in (("bin", "usr/bin"), ("sbin", "usr/bin"), ("lib", "usr/lib"),
                         ("usr/sbin", "bin"), ("var/run", "../run")):
        (dest / link).symlink_to(target)
    write(dest, "init", Path(init).read_bytes(), 0o755)
    copy_closure(root, dest, SHIP)
    busybox_applets(root, dest)
    for rel, text in FILES.items():
        write(dest, rel, text)
    write(dest, "etc/shadow", "root:*:20376::::::\n", 0o600)
    write(dest, "root/.ssh/authorized_keys", Path(keys).read_bytes(), 0o600)
    write(dest, "etc/ilinux-initramfs.txt",
          "boot036 Stage-B initramfs: /init from kernel/experiments/usb-gadget/init.c;\n"
          "programs from these signed Arch Linux ARM packages:\n" + packages(root))


def overlay(root, selftest, key, dest):
    (dest / "usr/bin").mkdir(parents=True)
    copy_closure(root, dest, TEST)
    write(dest, "etc/ilinux/selftest", Path(selftest).read_bytes(), 0o755)
    write(dest, "etc/ilinux/test-key", Path(key).read_bytes(), 0o600)


def listing(dest):
    for path in sorted(dest.rglob("*")):
        rel = path.relative_to(dest)
        if path.is_symlink():
            print("l %s -> %s" % (rel, os.readlink(path)))
        elif path.is_dir():
            print("d %o %s" % (path.stat().st_mode & 0o7777, rel))
        else:
            data = path.read_bytes()
            print("f %o %d %s %s" % (path.stat().st_mode & 0o7777, len(data),
                                    hashlib.sha256(data).hexdigest(), rel))


def main(argv):
    if len(argv) != 6 or argv[1] not in ("ship", "overlay"):
        raise SystemExit(__doc__)
    root, dest = Path(argv[2]), Path(argv[5])
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (ship if argv[1] == "ship" else overlay)(root, argv[3], argv[4], dest)
    listing(dest)


if __name__ == "__main__":
    main(sys.argv)
