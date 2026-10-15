"""boot036 control-channel contract for the kernel config and the Stage-B initramfs.

Kernel config: boot035's, with the gadget stack built in. Only USB_LIBCOMPOSITE
and USB_CONFIGFS are set (m -> y); Kconfig then turns the twelve gadget
function and helper symbols they select from m into y. Nothing else changes.
The kernel.config carried by every package since boot024 is job 020's; the
tree that builds the Images has since re-detected the toolchain (rustc), so
against a packaged config only toolchain-detection lines may differ as well.
A symbol that is absent counts as "n" (Kconfig omits invisible symbols).

Initramfs: a gzip-compressed newc cpio with a static /init, dropbear and
busybox (with their shared libraries) from signed Arch Linux ARM packages, and
root's authorized key. It must not contain the VM self-test (/etc/ilinux), a
private key, a set-id file, or a file not owned by root.
"""
import gzip
import struct

from kconfig_guard import TOOLCHAIN, config_delta, parse_config, toolchain_differences  # noqa: F401

CONFIG_SET = ("USB_LIBCOMPOSITE", "USB_CONFIGFS")
CONFIG_DERIVED = ("USB_F_ACM", "USB_U_SERIAL", "USB_U_ETHER", "USB_F_SERIAL", "USB_F_OBEX",
                  "USB_F_NCM", "USB_F_ECM", "USB_F_EEM", "USB_F_SUBSET", "USB_F_RNDIS",
                  "USB_F_MASS_STORAGE", "USB_F_FS")
CONFIG_KEEP = {"USB_CONFIGFS_EEM": "y", "USB_GADGET": "y", "USB_DWC3": "y",
               "USB_DWC3_DUAL_ROLE": "y", "CONFIGFS_FS": "y", "IPV6": "y", "UNIX98_PTYS": "y"}
REQUIRED = ("init", "usr/bin/dropbear", "usr/bin/busybox", "usr/bin/sh",
            "usr/lib/ld-linux-aarch64.so.1", "usr/lib/libc.so.6", "etc/passwd", "etc/shells",
            "root", "root/.ssh", "root/.ssh/authorized_keys", "etc/dropbear",
            "proc", "sys", "dev", "run", "tmp")
SYMLINKS = {"bin": "usr/bin", "sbin": "usr/bin", "lib": "usr/lib", "usr/sbin": "bin"}
FORBIDDEN_PREFIXES = ("etc/ilinux/",)
DENIED_APPLETS = ("reboot", "poweroff", "halt", "linuxrc")
KEY_MARKERS = (b"PRIVATE KEY", b"ssh-ed25519", b"ssh-rsa", b"ecdsa-sha2", b"ssh-dss")


def check_config(before_text, after_text, allow_toolchain=False):
    """Raise unless the config delta is exactly the gadget stack going from m to y.

    allow_toolchain: also accept toolchain-detection differences (a packaged
    baseline); returns their names."""
    delta = config_delta(before_text, after_text)
    toolchain = sorted(n for n in delta if allow_toolchain and TOOLCHAIN.fullmatch(n))
    changed = sorted(set(delta) - set(toolchain))
    expected = sorted(CONFIG_SET + CONFIG_DERIVED)
    if changed != expected:
        raise ValueError("kernel config delta differs: unexpected %s, missing %s" % (
            sorted(set(changed) - set(expected)), sorted(set(expected) - set(changed))))
    for name in expected:
        if delta[name] != ("m", "y"):
            raise ValueError("CONFIG_%s must go from m to y" % name)
    after = parse_config(after_text)
    for name, value in CONFIG_KEEP.items():
        if after.get(name) != value:
            raise ValueError("CONFIG_%s must stay %s" % (name, value))
    return toolchain


def cpio_entries(blob):
    """Entries of a gzip-compressed newc cpio: {name: (mode, uid, gid, data)}."""
    data = gzip.decompress(blob)
    entries, pos = {}, 0
    while True:
        if data[pos:pos + 6] != b"070701":
            raise ValueError("initramfs is not a newc cpio")
        fields = [int(data[pos + 6 + 8 * i:pos + 14 + 8 * i], 16) for i in range(13)]
        _, mode, uid, gid, _, _, size, _, _, _, _, namesize, _ = fields
        name_start = pos + 110
        name = data[name_start:name_start + namesize - 1].decode("utf-8")
        body = (name_start + namesize + 3) & ~3
        pos = (body + size + 3) & ~3
        if name == "TRAILER!!!":
            break
        name = name[2:] if name.startswith("./") else name
        if name in entries:
            raise ValueError("duplicate initramfs entry: " + name)
        entries[name] = (mode, uid, gid, data[body:body + size])
    if data[pos:].strip(b"\0"):
        raise ValueError("data after the cpio trailer")
    return entries


def _elf_static(image):
    if image[:4] != b"\x7fELF" or image[4] != 2 or image[18] != 183:   # ELF64, AArch64
        raise ValueError("/init is not an AArch64 ELF64")
    phoff, = struct.unpack_from("<Q", image, 32)
    phentsize, phnum = struct.unpack_from("<HH", image, 54)
    for i in range(phnum):
        if struct.unpack_from("<I", image, phoff + i * phentsize)[0] == 3:   # PT_INTERP
            raise ValueError("/init must be statically linked")


def check_initramfs(blob, authorized_key):
    """Raise unless the Stage-B initramfs matches the control-channel contract."""
    entries = cpio_entries(blob)
    for name in REQUIRED:
        if name not in entries:
            raise ValueError("initramfs lacks " + name)
    for name, target in SYMLINKS.items():
        mode, _, _, data = entries.get(name, (0, 0, 0, b""))
        if mode & 0o170000 != 0o120000 or data.decode() != target:
            raise ValueError("initramfs symlink %s must point to %s" % (name, target))
    for name, (mode, uid, gid, data) in entries.items():
        if uid or gid:
            raise ValueError("initramfs file not owned by root: " + name)
        if mode & 0o6000:
            raise ValueError("set-id file in initramfs: " + name)
        if name.startswith(FORBIDDEN_PREFIXES) or name == "etc/ilinux":
            raise ValueError("VM self-test content in shipped initramfs: " + name)
        # Programs name key algorithms; any other file holding key material is refused.
        if (mode & 0o170000 == 0o100000 and not data.startswith(b"\x7fELF")
                and name != "root/.ssh/authorized_keys"
                and any(marker in data for marker in KEY_MARKERS)):
            raise ValueError("key material outside authorized_keys: " + name)
        if name.rsplit("/", 1)[-1] in DENIED_APPLETS:
            raise ValueError("denied applet in initramfs: " + name)
    mode, _, _, init = entries["init"]
    if mode & 0o170000 != 0o100000 or not mode & 0o100:
        raise ValueError("/init must be an executable regular file")
    _elf_static(init)
    mode, _, _, keys = entries["root/.ssh/authorized_keys"]
    if mode & 0o077 or entries["root/.ssh"][0] & 0o077 or entries["root"][0] & 0o077:
        raise ValueError("root's SSH files must not be group/other accessible")
    if keys.strip() != authorized_key.strip() or keys.count(b"\n") != 1:
        raise ValueError("authorized_keys must hold exactly the expected key")
    if entries["usr/bin/sh"][0] & 0o170000 != 0o120000 or entries["usr/bin/sh"][3] != b"busybox":
        raise ValueError("/bin/sh must be busybox")
    return entries
