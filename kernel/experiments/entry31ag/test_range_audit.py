#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("entry31ag_range_audit", HERE / "range_audit.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Public metadata for the original 31AF candidate, not Apple executable content.
LEGACY = {
    "kclo": 0xfffffe0007000000, "kcep": 0xfffffe0007060000,
    "kcrf": 0, "kcrz": 0x64000, "kcsf": 0x8000, "kcsz": 0x54000,
    "kcxf": 0, "kcxz": 0, "kcbf": 0x60000, "kcbz": 0x4000,
    "kcwf": 0x64000, "kcwz": 0x4000, "kclf": 0x68000, "kclz": 0x4000,
}
INPUTS = {"image_bytes": 0x6c000, "load_base": 0xfffffe0007000000,
          "expected_reserved_offset": 0x8000, "expected_reserved_bytes": 0x54000}


class RangeTests(unittest.TestCase):
    def test_recorded_legacy_metadata_is_inconsistent_under_explicit_producer(self):
        result = module.audit(LEGACY, **INPUTS)
        self.assertEqual(result["status"], "CONDITIONAL_INCONSISTENCY")
        self.assertEqual(result["conditional_producer_reserved"]["end_offset"], 0xb8000)
        self.assertIn("reserved_start_differs_from_declared_segment", result["issues"])
        self.assertIn("reserved_range_exceeds_materialized_image", result["issues"])
        self.assertFalse(result["native_failure_cause_proven"])
        self.assertFalse(result["native_binding_verified"])
        self.assertFalse(result["new_native_boot_ready"])

    def test_matching_prefix_remains_only_conditionally_consistent(self):
        properties = dict(LEGACY, kcrz=0x8000)
        result = module.audit(properties, **INPUTS)
        self.assertEqual(result["status"], "CONDITIONAL_CONSISTENCY")
        self.assertEqual(result["issues"], [])
        self.assertFalse(result["image_acceptance_proven"])

    def test_kcsf_does_not_select_the_reserved_start(self):
        properties = dict(LEGACY, kcrz=0x8000, kcsf=0)
        first = module.audit(properties, **INPUTS)
        second = module.audit(dict(properties, kcsf=0xffffffffffffffff), **INPUTS)
        self.assertEqual(first["conditional_producer_reserved"], second["conditional_producer_reserved"])
        self.assertEqual(first["issues"], second["issues"])
        self.assertFalse(second["kcsf_semantics_applied"])

    def test_zero_reserved_size_is_a_contract_inconsistency(self):
        result = module.audit(dict(LEGACY, kcrz=0x8000, kcsz=0), **INPUTS)
        self.assertIn("reserved_size_zero", result["issues"])

    def test_misaligned_reserved_range_is_not_silently_rounded(self):
        result = module.audit(dict(LEGACY, kcrz=0x8001), **INPUTS)
        self.assertIn("reserved_range_not_16k_aligned", result["issues"])
        self.assertEqual(result["conditional_producer_reserved"]["offset"], 0x8001)

    def test_relative_extent_overflow_is_reported_without_wrapping(self):
        result = module.audit(dict(LEGACY, kcrz=0xffffffffffffc000, kcsz=0x8000), **INPUTS)
        self.assertIn("producer_reserved_range_overflows_u64", result["issues"])
        self.assertIsNone(result["conditional_producer_reserved"]["end_offset"])
        self.assertIsNone(result["conditional_producer_reserved"]["base"])

    def test_absolute_address_overflow_is_reported(self):
        supplied = dict(INPUTS, load_base=0xfffffffffff00000)
        result = module.audit(dict(LEGACY, kcrz=0x100000), **supplied)
        self.assertIn("producer_reserved_range_overflows_u64", result["issues"])
        self.assertIsNone(result["conditional_producer_reserved"]["base"])

    def test_caller_image_extent_overflow_is_invalid_input(self):
        with self.assertRaises(ValueError):
            module.audit(LEGACY, **dict(INPUTS, load_base=0xfffffffffffc0000))

    def test_declared_reservation_must_fit_explicit_image(self):
        with self.assertRaises(ValueError):
            module.audit(LEGACY, **dict(INPUTS, image_bytes=0x40000))

    def test_wrong_declared_size_is_reported(self):
        result = module.audit(dict(LEGACY, kcrz=0x8000), **dict(INPUTS, expected_reserved_bytes=0x50000))
        self.assertIn("reserved_size_differs_from_declared_segment", result["issues"])

    def test_boolean_is_not_u64_metadata(self):
        with self.assertRaises(ValueError): module.audit(dict(LEGACY, kcsz=True), **INPUTS)

    def test_negative_and_wide_properties_are_rejected(self):
        for value in (-1, 1 << 64):
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.audit(dict(LEGACY, kcrz=value), **INPUTS)

    def test_unknown_fields_do_not_enter_a_public_report(self):
        with self.assertRaises(ValueError): module.audit(dict(LEGACY, unrelated="private"), **INPUTS)

    def test_missing_properties_are_rejected(self):
        properties = dict(LEGACY); del properties["kcep"]
        with self.assertRaises(ValueError): module.audit(properties, **INPUTS)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(ValueError): module.properties_from_text('{"kcrz":0,"kcrz":32768}')

    def test_input_alignment_is_required(self):
        with self.assertRaises(ValueError): module.audit(LEGACY, **dict(INPUTS, load_base=INPUTS["load_base"] + 1))

    def test_other_property_geometry_is_explicitly_out_of_scope(self):
        properties = dict(LEGACY, kcrz=0x8000, kcbf=1, kcbz=3)
        result = module.audit(properties, **INPUTS)
        self.assertEqual(result["status"], "CONDITIONAL_CONSISTENCY")
        self.assertFalse(result["other_regions_audited"])

    def test_inputs_are_unchanged(self):
        properties = copy.deepcopy(LEGACY); before = copy.deepcopy(properties)
        module.audit(properties, **INPUTS)
        self.assertEqual(properties, before)


if __name__ == "__main__":
    unittest.main()
