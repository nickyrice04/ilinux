"""Tests for make-overlay.py: the cpio the kernel unpacks over the base root.

    python3 -I virtualization/jobs/046-usb-ssh-pipe/test_make_overlay.py
"""
import importlib.util
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("make_overlay", HERE / "make-overlay.py")
make_overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_overlay)


def parse_newc(blob):
    """The way init/initramfs.c reads it: entries (name, mode, uid, gid, nlink, data), strict alignment."""
    entries, pos = [], 0
    while True:
        assert pos % 4 == 0 and blob[pos:pos + 6] == b"070701", "entry %d is not aligned newc" % len(entries)
        fields = [int(blob[pos + 6 + 8 * i:pos + 14 + 8 * i], 16) for i in range(13)]
        end = pos + 110 + fields[11]
        name = blob[pos + 110:end - 1].decode()
        assert blob[end - 1] == 0
        body = (end + 3) & ~3
        data = blob[body:body + fields[6]]
        pos = (body + fields[6] + 3) & ~3
        if name == "TRAILER!!!":
            assert pos == len(blob), "bytes after the trailer"
            return entries
        entries.append((name, fields[1], fields[2], fields[3], fields[4], data))


class OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob, _ = make_overlay.build()
        cls.entries = parse_newc(cls.blob)
        cls.by_name = {e[0]: e for e in cls.entries}

    def test_everything_is_root_owned_and_parents_come_first(self):
        seen = set()
        for name, mode, uid, gid, nlink, data in self.entries:
            self.assertEqual((uid, gid), (0, 0), name)
            self.assertFalse(name.startswith("/") or ".." in name.split("/"), name)
            parent = name.rsplit("/", 1)[0] if "/" in name else ""
            self.assertTrue(parent == "" or parent in seen, "%s comes before its directory %s" % (name, parent))
            if stat.S_ISDIR(mode):
                seen.add(name)

    def test_product_files_are_in_with_their_modes(self):
        gadget = self.by_name["usr/local/lib/ilinux/usb-gadget.sh"]
        self.assertEqual(stat.S_IMODE(gadget[1]), 0o755)
        self.assertTrue(gadget[5].startswith(b"#!/bin/sh"))
        self.assertIn(b"gser.ssh", gadget[5])
        self.assertEqual(stat.S_IMODE(self.by_name["init"][1]), 0o755)
        self.assertEqual(stat.S_IMODE(self.by_name["etc/ssh/sshd_config.d/25-ilinux-usb-pipe.conf"][1]), 0o644)
        self.assertIn(b"HTTPS_PROXY=http://127.0.0.1:3128", self.by_name["etc/environment"][5])
        for unit in ("ilinux-sshd-tty@.service", "ilinux-usb-gadget@.service", "ilinux-selftest.service"):
            self.assertIn("etc/systemd/system/" + unit, self.by_name)
        self.assertIn("etc/systemd/system/ilinux-sshd-tty@.service.d/test-private-network.conf", self.by_name)
        self.assertEqual(stat.S_IMODE(self.by_name["usr/local/lib/ilinux-test/selftest.sh"][1]), 0o755)
        proxy = self.by_name["usr/local/lib/ilinux-test/connect-proxy.py"]
        self.assertEqual(proxy[5], (HERE.parents[2] / "tools/m1n1-client/connect-proxy.py").read_bytes())

    def test_unit_enablement_is_by_symlink(self):
        want = {"etc/systemd/system/multi-user.target.wants/ilinux-selftest.service": "/etc/systemd/system/ilinux-selftest.service",
                "etc/systemd/system/default.target": "/usr/lib/systemd/system/multi-user.target",
                "etc/systemd/system/getty@tty1.service": "/dev/null",
                "etc/systemd/system/serial-getty@hvc0.service": "/dev/null"}
        for path, target in want.items():
            entry = self.by_name[path]
            self.assertTrue(stat.S_ISLNK(entry[1]), path)
            self.assertEqual(entry[5], target.encode(), path)
        self.assertIn("etc/systemd/system/multi-user.target.wants", self.by_name)

    def test_no_private_key_material_and_no_junk(self):
        for name, mode, uid, gid, nlink, data in self.entries:
            self.assertNotIn(b"PRIVATE KEY-----", data, name)
            self.assertNotEqual(Path(name).name, ".DS_Store")
        self.assertNotIn("usr/local/lib/ilinux-test/test-key", self.by_name)   # the keys come from the VM-built base

    def test_no_system_directory_is_repermissioned(self):
        for name, mode, *_ in self.entries:
            if stat.S_ISDIR(mode):
                self.assertEqual(stat.S_IMODE(mode), 0o755, name)

    def test_refuses_private_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "overlay"
            (src / "etc").mkdir(parents=True)
            (src / "etc/key").write_bytes(b"-----BEGIN OPENSSH PRIVATE KEY-----\nAAAA\n")
            old = make_overlay.PRODUCT
            make_overlay.PRODUCT = src
            try:
                with self.assertRaises(SystemExit):
                    make_overlay.collect()
            finally:
                make_overlay.PRODUCT = old

    def test_deterministic(self):
        self.assertEqual(make_overlay.build()[0], self.blob)


if __name__ == "__main__":
    unittest.main()
