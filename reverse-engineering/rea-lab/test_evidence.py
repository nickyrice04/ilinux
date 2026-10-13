import copy
import unittest
from check_evidence import inspect, sha


class EvidenceGate(unittest.TestCase):
    def setUp(self):
        self.carrier = b"header!!" + b"12345678"
        self.derived = b"12345678"
        self.manifest = {"source_sha256": sha(self.carrier), "derived_sha256": sha(self.derived),
                         "member": "synthetic", "mappings": [{"vmaddr": "0x1000", "bytes": 8,
                         "source_offset": 8, "derived_offset": 0}]}
        self.evidence = {"evidence_id": "synthetic-test", "subject": {"digest": {"sha256": sha(self.derived)}},
                         "normalized_result": {"procedure": {"name": "fixture", "body": {
                         "available": True, "ranges": [{"start": "0x1000", "end": "0x1007"}]}},
                         "assembly": ["0x1000: fixture", "0x1004: fixture"],
                         "native_value_flow": {"operations": [{"address": "0x1000", "block_membership": "member"}]}}}

    def check(self):
        return inspect(self.evidence, self.manifest, self.carrier, self.derived)

    def test_pass_requires_manual_review(self):
        self.assertEqual(self.check()["pseudocode_gate"], "manual_review_required")

    def test_provider_membership_does_not_override_bounds(self):
        self.evidence["normalized_result"]["native_value_flow"]["operations"].append(
            {"address": "0x1008", "block_membership": "member"})
        result = self.check()
        self.assertEqual(result["pseudocode_gate"], "rejected_cross_boundary")
        self.assertEqual(result["pcode_outside_body"], 1)

    def test_wrong_target_fails(self):
        self.evidence["subject"]["digest"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.check()

    def test_truncated_pseudocode_rejected_inside_valid_bounds(self):
        self.evidence["normalized_result"]["pseudocode"] = "/* WARNING: Bad instruction */ halt_baddata();"
        self.assertEqual(self.check()["pseudocode_gate"], "rejected_truncated_control_flow")

    def test_unresolved_jump_is_visible_and_still_needs_review(self):
        self.evidence["normalized_result"]["pseudocode"] = "/* Could not recover jumptable */"
        result = self.check()
        self.assertEqual(result["pseudocode_gate"], "manual_review_required")
        self.assertIn("unresolved_indirect_jump", result["decompiler_warning_classes"])

    def test_changed_payload_fails_even_with_updated_digest(self):
        self.derived = b"XXXXXXXX"
        self.manifest["derived_sha256"] = sha(self.derived)
        self.evidence["subject"]["digest"]["sha256"] = sha(self.derived)
        with self.assertRaises(ValueError):
            self.check()

    def test_duplicate_instruction_cannot_mask_gap(self):
        self.evidence["normalized_result"]["assembly"] = ["0x1000: fixture"] * 2
        with self.assertRaises(ValueError):
            self.check()

    def test_overlapping_ranges_fail(self):
        body = self.evidence["normalized_result"]["procedure"]["body"]
        body["ranges"].append(copy.deepcopy(body["ranges"][0]))
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
