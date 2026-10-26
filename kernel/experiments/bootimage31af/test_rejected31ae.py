#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Distinguish immutable 31AF from the exact locally supplied consumed 31AE.

The previous candidate passed installation but produced no visible entry marker.
This regression claims only byte identity and distinct structural profiles.
No binary fixture is committed and neither image is executed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OLD_IMAGE_SHA256 = "ccdc9c8c8ef78fda2d9e2a56550919d0c20030037486215d194e8762a85748aa"
OLD_VALIDATOR_SHA256 = "5eae5a3b8ce2b5964ebf074dab29304f42a7d8e1226bf069acc63758532c4f78"


def load(name, path, expected=None):
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular source file required")
    if expected is not None and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("frozen old validator source changed")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load("consumed31ae_validator", HERE.parent / "bootimage31ae/validate_ordered.py",
           OLD_VALIDATOR_SHA256)
new = load("immutable31af_validator", HERE / "validate.py")
CANDIDATE = None


class Rejected31AETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if CANDIDATE is None or CANDIDATE.is_symlink() or not CANDIDATE.is_file():
            raise ValueError("supply the regular exact original 31AE candidate file")
        cls.data = CANDIDATE.read_bytes()
        if len(cls.data) != 0x30000 or hashlib.sha256(cls.data).hexdigest() != OLD_IMAGE_SHA256:
            raise ValueError("candidate is not the exact consumed original 31AE bytes")

    def test_exact_consumed_31ae_identity(self):
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), OLD_IMAGE_SHA256)

    def test_frozen_old_complete_profile_passes(self):
        self.assertEqual(old.validate(self.data)["status"], "STRUCTURAL_PROFILE_PASS")

    def test_new_complete_profile_rejects_exact_consumed_image(self):
        with self.assertRaisesRegex(ValueError, "complete image size"):
            new.validate(self.data)

    def test_padding_old_image_does_not_repair_new_geometry(self):
        with self.assertRaisesRegex(ValueError, "payload mapping mismatch"):
            new.validate(self.data + bytes(0x3C000))

    def test_both_old_headers_have_different_reservation_and_entry(self):
        for offset, kind in ((0, 12), (0x4000, 2)):
            parsed = old.parse(self.data, offset, kind)
            by_name = {s["name"]: s for s in parsed["segments"]}
            self.assertEqual(by_name[b"__DATA_SPTM"]["size"], 0xC000)
            self.assertEqual(by_name[b"__TEXT_BOOT_EXEC"]["offset"], 0x18000)
            self.assertEqual(parsed["thread"], [0xFFFFFE0007018000])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    CANDIDATE = args.candidate
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Rejected31AETests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
