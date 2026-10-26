#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("entry31ag_classify", HERE / "classify.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def runtime():
    return {"schema": "ilinux-entry31ag-runtime-v1", "native": "NOT_RUN", "apple_firmware": False,
            "payload_sha256": module.PAYLOAD_SHA, "status": "PASS", "cases": [
                {"case": "control", "status": "PASS", "native": "NOT_RUN", "phase": 7,
                 "diagnostic_status": 0, "painted_pixels": 8192},
                {"case": "el1", "status": "PASS", "native": "NOT_RUN", "phase": 128,
                 "diagnostic_status": 2, "painted_pixels": 0}]}


def human(marker=False):
    return {"schema": "ilinux-attempt31af-human-result-v1",
            "native_observation": {"attempted": True, "marker_reported": marker}}


class EvidenceTests(unittest.TestCase):
    def test_real_human_blank_never_implies_preentry_or_vendor_failure(self):
        import json
        report = json.loads((HERE.parents[2] / "native/boot/attempt31af-human-2026-10-26-result.json").read_text())
        result = module.classify(report)
        self.assertEqual(result["native_entry"], "UNCONFIRMED")
        self.assertFalse(result["pre_entry_failure_proven"])
        self.assertFalse(result["apple_update_required_proven"])
        self.assertFalse(result["new_native_boot_ready"])

    def test_human_marker_keeps_observation_qualification(self):
        result = module.classify(human(True))
        self.assertIn("HUMAN_REPORTED", result["native_entry"])
        self.assertFalse(result["provenance_authenticated"])

    def test_emulated_paint_never_becomes_native_entry(self):
        result = module.classify(runtime())
        self.assertEqual(result["native_entry"], "UNCONFIRMED")
        self.assertEqual(result["states"][0]["observed_in_emulator"], "emulated-paint-complete")
        self.assertEqual(result["states"][1]["observed_in_emulator"], "entry-level-refusal")

    def test_emulator_schema_rejects_native_claim(self):
        report = runtime(); report["native"] = "PASS"
        with self.assertRaises(ValueError): module.classify(report)

    def test_emulator_schema_rejects_firmware_claim(self):
        report = runtime(); report["apple_firmware"] = True
        with self.assertRaises(ValueError): module.classify(report)

    def test_partial_paint_cannot_be_complete(self):
        report = runtime(); report["cases"][0]["painted_pixels"] = 8191
        with self.assertRaises(ValueError): module.classify(report)

    def test_refusal_with_pixels_is_contradictory(self):
        report = runtime(); report["cases"][1]["painted_pixels"] = 1
        with self.assertRaises(ValueError): module.classify(report)

    def test_unknown_status_is_not_guessed(self):
        report = runtime(); report["cases"][1]["diagnostic_status"] = 999
        with self.assertRaises(ValueError): module.classify(report)

    def test_unbound_payload_is_rejected(self):
        report = runtime(); report["payload_sha256"] = "0" * 64
        with self.assertRaises(ValueError): module.classify(report)

    def test_unattempted_marker_is_rejected(self):
        report = human(True); report["native_observation"]["attempted"] = False
        with self.assertRaises(ValueError): module.classify(report)

    def test_bool_is_not_integer_status(self):
        report = runtime(); report["cases"][1]["diagnostic_status"] = True
        with self.assertRaises(ValueError): module.classify(report)

    def test_bool_is_not_pixel_count(self):
        report = runtime(); report["cases"][1]["painted_pixels"] = False
        with self.assertRaises(ValueError): module.classify(report)

    def test_duplicate_case_does_not_add_evidence(self):
        report = runtime(); report["cases"].append(copy.deepcopy(report["cases"][0]))
        with self.assertRaises(ValueError): module.classify(report)


if __name__ == "__main__":
    unittest.main()
