#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import tarfile
import unittest

spec = importlib.util.spec_from_file_location("isolate", Path(__file__).with_name("isolate-toolchain.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
FP = "A" * 40
GOOD = "[GNUPG:] GOODSIG 123 public package signer\n[GNUPG:] VALIDSIG " + FP + " 2026 1 0 4 0 1 10 00\n"


class IsolationTests(unittest.TestCase):
    def test_explicit_trusted_signatures(self):
        for trust in ("TRUST_FULLY", "TRUST_ULTIMATE"):
            self.assertEqual(m.signature_status(GOOD + "[GNUPG:] " + trust + " 0 pgp\n", 0)["trust"], trust)

    def test_missing_or_partial_evidence(self):
        for text in (GOOD, "", "[GNUPG:] TRUST_FULLY\n", GOOD + "[GNUPG:] TRUST_MARGINAL\n"):
            with self.assertRaises(ValueError):m.signature_status(text, 0)

    def test_failures_override_valid(self):
        for status in sorted(m.BAD):
            with self.assertRaises(ValueError):
                m.signature_status(GOOD + "[GNUPG:] TRUST_FULLY\n[GNUPG:] " + status + "\n", 0)
        with self.assertRaises(ValueError):m.signature_status(GOOD + "[GNUPG:] TRUST_FULLY\n", 1)

    def test_multiple_or_malformed_signature(self):
        with self.assertRaises(ValueError):m.signature_status(GOOD + GOOD + "[GNUPG:] TRUST_FULLY\n", 0)
        with self.assertRaises(ValueError):m.signature_status(GOOD.replace(FP, "invalid") + "[GNUPG:] TRUST_FULLY\n", 0)

    def test_archive_members(self):
        for path in ("/usr/escape", "usr/../etc/escape"):
            with self.assertRaises(ValueError):m.allowed_member(tarfile.TarInfo(path))
        self.assertFalse(m.allowed_member(tarfile.TarInfo(".INSTALL")))
        self.assertFalse(m.allowed_member(tarfile.TarInfo("etc/config")))
        self.assertTrue(m.allowed_member(tarfile.TarInfo("usr/bin/llvm-config")))
        special = tarfile.TarInfo("usr/device");special.type = tarfile.CHRTYPE
        with self.assertRaises(ValueError):m.allowed_member(special)

    def test_only_package_prefix_assignments_relocate(self):
        text = "prefix=/usr\nincludedir=${prefix}/include\nName: /usr remains text\n"
        self.assertEqual(m.relocate_pc(text, Path("/isolated")),
                         "prefix=/isolated/usr\nincludedir=${prefix}/include\nName: /usr remains text\n")
        self.assertEqual(m.relocate_pc("prefix=/already/usr\n", Path("/isolated")), "prefix=/already/usr\n")


if __name__ == "__main__":unittest.main(verbosity=2)
