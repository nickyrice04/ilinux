#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject the exact original released 31AD bytes, supplied locally by the caller.

No candidate binary is committed. This explicitly distinguishes the old guard's
false reassurance from the corrected finite data-order invariant.
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
OLD_IMAGE_SHA256 = "406be900521795608073fa9f050f4e5f00b595793c95b0a155e510893cc16309"
OLD_VALIDATOR_SHA256 = "733b11da74aac377bd6d73df5802c89d4702a177e8232e1dbcea0df98c0705a1"


def load(name, path, expected=None):
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular source file required")
    if expected is not None and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("frozen old validator source changed")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = load("released31ad_validator", HERE.parent / "bootimage31ad/validate_ordered.py",
           OLD_VALIDATOR_SHA256)
new = load("datafirst31ae_validator", HERE / "validate_ordered.py")
CANDIDATE = None


class Rejected31ADTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if CANDIDATE is None or CANDIDATE.is_symlink() or not CANDIDATE.is_file():
            raise ValueError("supply the regular original 31AD candidate file")
        cls.data = CANDIDATE.read_bytes()
        if len(cls.data) != 0x30000 or hashlib.sha256(cls.data).hexdigest() != OLD_IMAGE_SHA256:
            raise ValueError("candidate is not the exact released original 31AD bytes")

    def test_exact_released_31ad_identity(self):
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), OLD_IMAGE_SHA256)

    def test_frozen_old_full_validator_and_range_guard_pass(self):
        self.assertEqual(old.validate(self.data)["status"], "STRUCTURAL_PROFILE_PASS")
        self.assertEqual(old.range_check(self.data)["status"], "CHECKED_SPLIT_RANGE_PASS")

    def test_new_complete_profile_rejects_observed_data_subtraction(self):
        with self.assertRaisesRegex(ValueError, "data-to-text ordering would underflow"):
            new.validate(self.data)

    def test_new_range_guard_rejects_observed_data_subtraction(self):
        with self.assertRaisesRegex(ValueError, "data-to-text ordering would underflow"):
            new.range_check(self.data)

    def test_each_original_header_and_arithmetic_profile_rejects(self):
        for offset, kind in ((0, 12), (0x4000, 2)):
            segments = old.parse(self.data, offset, kind)["segments"]
            by_name = {s["name"]: s for s in segments}
            self.assertEqual(by_name[b"__TEXT_EXEC"]["offset"], 0x8000)
            self.assertEqual(by_name[b"__DATA_SPTM"]["offset"], 0xC000)
            with self.subTest(header=offset), self.assertRaisesRegex(ValueError, "data-to-text ordering"):
                new.split_range(segments, len(self.data))
            for profile in (False, True):
                with self.subTest(header=offset, profile=profile), self.assertRaisesRegex(
                        ValueError, "text-exec-minus-data"):
                    new.profile_arithmetic(segments, len(self.data), profile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    CANDIDATE = args.candidate
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Rejected31ADTests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
