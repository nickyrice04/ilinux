"""boot036 config and initramfs contract: the expected payload passes, deviations fail closed."""
import gzip
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import control_channel as cc  # noqa: E402

KEY = b"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleExampleExampleExampleExampleExampl test\n"
BOOT035_CONFIG = HERE.parents[1] / "build/native-boot035/verified/kernel.config"


def static_elf():
    header = bytearray(64)
    header[:4], header[4], header[5] = b"\x7fELF", 2, 1
    struct.pack_into("<H", header, 18, 183)
    struct.pack_into("<Q", header, 32, 64)
    struct.pack_into("<HH", header, 54, 56, 1)
    return bytes(header) + struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0x400000, 120, 120, 0x10000)


def dynamic_elf():
    data = bytearray(static_elf())
    struct.pack_into("<I", data, 64, 3)   # PT_INTERP instead of PT_LOAD
    return bytes(data)


def entries():
    d, f, l = 0o040000, 0o100000, 0o120000
    tree = {
        "init": (f | 0o755, static_elf()), "usr": (d | 0o755, b""), "usr/bin": (d | 0o755, b""),
        "usr/bin/dropbear": (f | 0o755, b"\x7fELF ... ssh-ed25519 ... PRIVATE KEY ..."),
        "usr/bin/busybox": (f | 0o755, b"\x7fELF busybox"), "usr/bin/sh": (l | 0o777, b"busybox"),
        "usr/bin/ls": (l | 0o777, b"busybox"), "usr/lib": (d | 0o755, b""),
        "usr/lib/ld-linux-aarch64.so.1": (f | 0o755, b"\x7fELF ld"),
        "usr/lib/libc.so.6": (f | 0o755, b"\x7fELF libc"),
        "etc": (d | 0o755, b""), "etc/passwd": (f | 0o644, b"root:x:0:0:root:/root:/bin/sh\n"),
        "etc/shells": (f | 0o644, b"/bin/sh\n"), "etc/dropbear": (d | 0o700, b""),
        "root": (d | 0o700, b""), "root/.ssh": (d | 0o700, b""),
        "root/.ssh/authorized_keys": (f | 0o600, KEY),
        "bin": (l | 0o777, b"usr/bin"), "sbin": (l | 0o777, b"usr/bin"), "lib": (l | 0o777, b"usr/lib"),
        "usr/sbin": (l | 0o777, b"bin"),
    }
    for name in ("proc", "sys", "dev", "run"):
        tree[name] = (d | 0o755, b"")
    tree["tmp"] = (d | 0o1777, b"")
    return tree


def newc(tree, uid=0, trailer_garbage=b""):
    out = bytearray()
    for i, (name, (mode, data)) in enumerate(sorted(tree.items()) + [("TRAILER!!!", (0, b""))]):
        raw = ("./" + name if name != "TRAILER!!!" else name).encode() + b"\0"
        fields = (i + 1, mode, uid, 0, 1, 0, len(data), 0, 0, 0, 0, len(raw), 0)
        out += b"070701" + b"".join(b"%08X" % v for v in fields) + raw
        out += b"\0" * (-len(out) % 4) + data
        out += b"\0" * (-len(out) % 4)
    return gzip.compress(bytes(out + trailer_garbage), mtime=0)


class InitramfsTests(unittest.TestCase):
    def test_contract_passes(self):
        cc.check_initramfs(newc(entries()), KEY)

    def test_deviations(self):
        def change(fn):
            tree = entries()
            fn(tree)
            return newc(tree)
        f = 0o100000
        cases = {
            "selftest shipped": change(lambda t: t.__setitem__("etc/ilinux/selftest", (f | 0o755, b"#!/bin/sh"))),
            "private key file": change(lambda t: t.__setitem__(
                "etc/dropbear/key", (f | 0o600, b"-----BEGIN OPENSSH PRIVATE KEY-----"))),
            "second key": change(lambda t: t.__setitem__(
                "root/.ssh/authorized_keys", (f | 0o600, KEY + KEY))),
            "other key": change(lambda t: t.__setitem__(
                "root/.ssh/authorized_keys", (f | 0o600, KEY.replace(b"Example", b"Elpmaxe")))),
            "world-readable keys": change(lambda t: t.__setitem__("root/.ssh/authorized_keys", (f | 0o644, KEY))),
            "open .ssh": change(lambda t: t.__setitem__("root/.ssh", (0o040755, b""))),
            "setuid": change(lambda t: t.__setitem__("usr/bin/busybox", (f | 0o4755, b"\x7fELF"))),
            "dynamic init": change(lambda t: t.__setitem__("init", (f | 0o755, dynamic_elf()))),
            "init not executable": change(lambda t: t.__setitem__("init", (f | 0o644, static_elf()))),
            "missing dropbear": change(lambda t: t.pop("usr/bin/dropbear")),
            "reboot applet": change(lambda t: t.__setitem__("usr/bin/reboot", (0o120777, b"busybox"))),
            "bin not merged": change(lambda t: t.__setitem__("bin", (0o040755, b""))),
            "sh not busybox": change(lambda t: t.__setitem__("usr/bin/sh", (0o120777, b"dash"))),
            "non-root owner": newc(entries(), uid=1000),
            "data after trailer": newc(entries(), trailer_garbage=b"070701"),
            "not newc": gzip.compress(b"0707070000"),
        }
        for name, blob in cases.items():
            with self.subTest(case=name), self.assertRaises(ValueError):
                cc.check_initramfs(blob, KEY)


class ConfigTests(unittest.TestCase):
    BEFORE = "\n".join(["CONFIG_USB_GADGET=y", "CONFIG_USB_DWC3=y", "CONFIG_USB_DWC3_DUAL_ROLE=y",
                        "CONFIG_CONFIGFS_FS=y", "CONFIG_IPV6=y", "CONFIG_UNIX98_PTYS=y",
                        "CONFIG_USB_CONFIGFS_EEM=y", "# CONFIG_USB_DUMMY_HCD is not set"]
                       + ["CONFIG_%s=m" % n for n in cc.CONFIG_SET + cc.CONFIG_DERIVED])

    def after(self):
        return self.BEFORE.replace("=m", "=y")

    def test_expected_delta(self):
        cc.check_config(self.BEFORE, self.after())

    def test_deviations(self):
        cases = {
            "nothing changed": self.BEFORE,
            "dummy_hcd shipped": self.after().replace("# CONFIG_USB_DUMMY_HCD is not set", "CONFIG_USB_DUMMY_HCD=y"),
            "one function left a module": self.after().replace("CONFIG_USB_F_EEM=y", "CONFIG_USB_F_EEM=m"),
            "EEM removed": self.after().replace("CONFIG_USB_CONFIGFS_EEM=y", "# CONFIG_USB_CONFIGFS_EEM is not set"),
            "extra symbol": self.after() + "\nCONFIG_FTRACE=y",
        }
        for name, text in cases.items():
            with self.subTest(case=name), self.assertRaises(ValueError):
                cc.check_config(self.BEFORE, text)

    def test_toolchain_drift(self):
        before = self.BEFORE + "\nCONFIG_RUSTC_VERSION=0\nCONFIG_CC_HAS_COUNTED_BY=y"
        after = self.after() + "\nCONFIG_RUSTC_VERSION=109900\n# CONFIG_RUST is not set"
        with self.assertRaises(ValueError):
            cc.check_config(before, after)            # strict: a baseline tree config
        self.assertEqual(cc.check_config(before, after, allow_toolchain=True),
                         ["CC_HAS_COUNTED_BY", "RUSTC_VERSION"])   # absent RUST counts as n
        self.assertEqual(cc.toolchain_differences(before, before.replace("=0", "=109900")),
                         ["RUSTC_VERSION"])
        for option in ("CONFIG_RUST=y", "CONFIG_FTRACE=y", "CONFIG_USB_F_EEM=n"):
            with self.subTest(option=option), self.assertRaises(ValueError):
                cc.check_config(before, after + "\n" + option, allow_toolchain=True)
            with self.subTest(drift=option), self.assertRaises(ValueError):
                cc.toolchain_differences(before, before + "\n" + option)

    @unittest.skipUnless(BOOT035_CONFIG.is_file(), "boot035 package not extracted in build/")
    def test_real_boot035_config_shape(self):
        values = cc.parse_config(BOOT035_CONFIG.read_text())
        for name in cc.CONFIG_SET + cc.CONFIG_DERIVED:
            self.assertEqual(values.get(name), "m", name)
        for name, value in cc.CONFIG_KEEP.items():
            self.assertEqual(values.get(name), value, name)


if __name__ == "__main__":
    unittest.main()
