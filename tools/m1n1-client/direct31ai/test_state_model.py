#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic state transitions only; no Apple API, volume or camera access."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("state_model", HERE / "state_model.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
CANDIDATE = "a" * 64  # Synthetic content digest, not a bootable artifact.


def sample(stage, obj="boot021", ctrr="disabled", context="lab_paired_1tr",
           default="lab"):
    return {"stage": stage, "facts": {
        "context": context, "target_binding": "distinct_lab_verified",
        "original_security": "full", "lab_security": "permissive",
        "lab_ctrr": ctrr, "selected_object": obj,
        "selected_object_sha256": M.BOOT021_SHA256 if obj == "boot021" else CANDIDATE,
        "default_entry": default, "unrelated_lab_policy_matches_baseline": True,
    }}


def attempt(stage, result="exit_zero"):
    return {"stage": stage, "facts": {"result": result}}


def document():
    plan = {key: True for key in M.REQUIRED_REVIEWS}
    plan.update(target=M.TARGET.copy(), candidate_sha256=CANDIDATE,
                rollback_sha256=M.BOOT021_SHA256, rollback_bytes=M.BOOT021_BYTES,
                native_deadline_ms=90000, capture_mode="screen_only")
    return {"schema": M.SCHEMA, "origin": "SYNTHETIC", "plan": plan, "events": [
        sample("baseline", context="original_desktop", default="original"),
        sample("recovery_before_candidate"), attempt("candidate_attempt"),
        sample("candidate_postcondition", "candidate", "enabled"),
        {"stage": "native_window", "facts": {
            "elapsed_ms": 65000, "external_stop_observed": True, "screen": "diagnostic_summary"}},
        sample("recovery_before_restore", "candidate", "enabled"),
        attempt("raw_policy_attempt"),
        sample("raw_policy_postcondition", "candidate"), attempt("boot021_attempt"),
        sample("boot021_postcondition"),
        sample("original_return", context="original_desktop", default="original"),
    ]}


class StateModel(unittest.TestCase):
    def refused(self, doc, reason=None):
        with self.assertRaises(M.Refusal) as caught:
            M.analyze(doc)
        if reason is not None:
            self.assertEqual(str(caught.exception), reason)

    def test_complete_path_is_only_offline_assertions(self):
        result = M.analyze(document())
        self.assertEqual(result["status"], "OFFLINE_MODEL_COMPLETE")
        self.assertTrue(result["restoration_assertions_complete"])
        self.assertEqual(result["native_windows_modelled"], 1)
        for key in ("hardware_state_verified", "restoration_verified", "native_execution_proven",
                    "native_ready", "writes_authorized", "host_queried"):
            self.assertIs(result[key], False)

    def test_hold_with_no_machine_observations(self):
        d = document(); d["events"] = []
        for key in M.REQUIRED_REVIEWS:
            d["plan"][key] = "unknown"
        d["plan"]["candidate_sha256"] = "unknown"
        r = M.analyze(d)
        self.assertEqual(r["status"], "OFFLINE_HOLD")
        self.assertEqual(len(r["missing_reviews"]), len(M.REQUIRED_REVIEWS) + 1)

    def test_actual_assertion_origin_still_does_not_verify_hardware(self):
        d = document(); d["origin"] = "SANITIZED_ASSERTIONS"
        self.assertFalse(M.analyze(d)["input_claims_independently_verified"])

    def test_candidate_exit_zero_alone_cannot_allow_boot(self):
        d = document(); del d["events"][3]
        self.refused(d, "transition_order")

    def test_failed_candidate_can_restore_without_retry(self):
        d = document(); d["events"][2]["facts"]["result"] = "exit_nonzero"
        del d["events"][3:5]
        self.assertEqual(M.analyze(d)["status"], "OFFLINE_MODEL_COMPLETE")
        self.assertEqual(M.analyze(d)["native_windows_modelled"], 0)

    def test_candidate_timeout_may_have_changed_object_and_policy(self):
        d = document(); d["events"][2]["facts"]["result"] = "timeout"
        del d["events"][3:5]
        self.assertEqual(M.analyze(d)["status"], "OFFLINE_MODEL_COMPLETE")

    def test_failed_candidate_must_not_boot_even_if_object_matches(self):
        d = document(); d["events"][2]["facts"]["result"] = "timeout"
        self.refused(d, "candidate_attempt_not_successful")

    def test_timeout_raw_restore_needs_fresh_matching_postcondition(self):
        d = document(); d["events"][8]["facts"]["result"] = "timeout"
        self.assertTrue(M.analyze(d)["restoration_assertions_complete"])
        del d["events"][9]
        self.refused(d, "transition_order")

    def test_failed_policy_attempt_can_only_continue_after_disabled_readback(self):
        d = document(); d["events"][6]["facts"]["result"] = "interrupted"
        self.assertTrue(M.analyze(d)["restoration_assertions_complete"])
        d["events"][7]["facts"]["lab_ctrr"] = "enabled"
        self.refused(d, "raw_ctrr_not_disabled")

    def test_raw_after_macho_without_policy_restore_refused(self):
        d = document(); del d["events"][6:8]
        self.refused(d, "transition_order")

    def test_replacing_raw_bytes_does_not_establish_policy_restoration(self):
        d = document(); d["events"][9]["facts"]["lab_ctrr"] = "enabled"
        self.refused(d, "raw_ctrr_not_disabled")

    def test_skip_policy_change_only_when_already_observed_disabled(self):
        d = document(); d["events"][2]["facts"]["result"] = "exit_nonzero"
        d["events"] = d["events"][:3] + [sample("recovery_before_restore"),
            sample("raw_policy_postcondition")] + d["events"][8:]
        self.assertTrue(M.analyze(d)["restoration_assertions_complete"])

    def test_unrecorded_ctrr_change_is_not_an_observation_shortcut(self):
        d = document(); d["events"][5]["facts"]["lab_ctrr"] = "disabled"
        self.refused(d, "unrecorded_ctrr_change")

    def test_unrecorded_object_change_refused(self):
        d = document(); d["events"][5] = sample("recovery_before_restore", ctrr="enabled")
        self.refused(d, "unrecorded_object_change")

    def test_legacy31af_unknown_blocks_new_install_sequence(self):
        d = document(); d["plan"]["legacy31af_reconciled"] = "unknown"
        self.refused(d, "legacy_restore_unconfirmed")

    def test_original_security_downgrade_refused_at_every_snapshot(self):
        for index, event in enumerate(document()["events"]):
            if event["stage"] in M.SNAPSHOT_STAGES:
                with self.subTest(stage=event["stage"]):
                    d = document(); d["events"][index]["facts"]["original_security"] = "permissive"
                    self.refused(d, "original_not_full")

    def test_unknown_object_never_treated_as_boot021(self):
        d = document(); d["events"][0]["facts"].update(
            selected_object="unknown", selected_object_sha256="unknown")
        self.refused(d, "object_unknown")

    def test_candidate_label_with_wrong_digest_refused(self):
        d = document(); d["events"][3]["facts"]["selected_object_sha256"] = M.BOOT021_SHA256
        self.refused(d, "selected_object_digest_mismatch")

    def test_other_lab_policy_bits_must_be_preserved(self):
        d = document(); d["events"][7]["facts"]["unrelated_lab_policy_matches_baseline"] = "unknown"
        self.refused(d, "unrelated_lab_policy_not_verified")

    def test_unknown_ctrr_cannot_count_as_disabled(self):
        d = document(); d["events"][7]["facts"]["lab_ctrr"] = "unknown"
        self.refused(d, "ctrr_unknown")

    def test_unknown_default_cannot_count_as_original_restoration(self):
        d = document(); d["events"][-1]["facts"]["default_entry"] = "unknown"
        self.refused(d, "default_unknown")

    def test_return_to_desktop_does_not_prove_default(self):
        d = document(); d["events"][-1]["facts"]["default_entry"] = "lab"
        self.refused(d, "original_default_not_verified")

    def test_wrong_or_ordinary_recovery_never_authorizes_modelled_writes(self):
        for context in ("ordinary_recovery", "original_recovery", "unknown"):
            with self.subTest(context=context):
                d = document(); d["events"][1]["facts"]["context"] = context
                self.refused(d, "context_not_qualified")

    def test_target_must_be_distinct_lab(self):
        d = document(); d["events"][1]["facts"]["target_binding"] = "wrong_target"
        self.refused(d, "target_not_verified")

    def test_every_review_gate_required_before_candidate_attempt(self):
        for key in M.REQUIRED_REVIEWS:
            if key == "legacy31af_reconciled":
                continue
            with self.subTest(key=key):
                d = document(); d["plan"][key] = "unknown"
                self.refused(d, "review_gate_open")

    def test_unknown_candidate_cannot_pass_with_true_review_flags(self):
        d = document(); d["plan"]["candidate_sha256"] = "unknown"
        self.refused(d, "candidate_digest_unknown")

    def test_old_approval_field_is_not_accepted(self):
        d = document(); d["plan"]["authorization_receipt"] = "31AF"
        self.refused(d, "plan_schema")

    def test_second_boot_or_automatic_retry_refused(self):
        for index in (2, 4, 6, 8):
            with self.subTest(index=index):
                d = document(); d["events"].insert(index + 1, copy.deepcopy(d["events"][index]))
                self.refused(d, "transition_order")

    def test_native_window_needs_external_stop_and_bounded_observation(self):
        d = document(); d["events"][4]["facts"]["external_stop_observed"] = False
        self.refused(d, "external_stop_not_observed")
        d = document(); d["events"][4]["facts"]["elapsed_ms"] = 90001
        self.refused(d, "native_overrun")

    def test_logo_or_diagnostic_screen_is_not_cpu_execution_proof(self):
        for screen in ("logo_only", "no_output", "fault", "diagnostic_summary"):
            with self.subTest(screen=screen):
                d = document(); d["events"][4]["facts"]["screen"] = screen
                self.assertFalse(M.analyze(d)["native_execution_proven"])

    def test_policy_model_does_not_claim_usb_control(self):
        for mode in ("screen_only", "usb_and_screen"):
            d = document(); d["plan"]["capture_mode"] = mode
            self.assertFalse(M.analyze(d)["native_ready"])

    def test_rollback_requires_exact_known_boot021_pin(self):
        d = document(); d["plan"]["rollback_sha256"] = "b" * 64
        self.refused(d, "wrong_boot021_digest")
        d = document(); d["plan"]["rollback_bytes"] += 1
        self.refused(d, "wrong_boot021_size")

    def test_bool_is_not_integer_or_review_evidence(self):
        d = document(); d["plan"]["native_deadline_ms"] = True
        self.refused(d, "native_deadline")
        d = document(); d["plan"]["firmware_pair_qualified"] = 1
        self.refused(d, "review_field_type")

    def test_private_identifier_field_refused_without_echo(self):
        d = document(); d["events"][0]["facts"]["volume_uuid"] = "SYNTHETIC-PRIVATE-MARKER"
        self.refused(d, "snapshot_schema")

    def test_event_count_bound(self):
        d = document(); d["events"] *= M.MAX_EVENTS
        self.refused(d, "event_bound")


class CLI(unittest.TestCase):
    def run_cli(self, payload):
        r = subprocess.run([sys.executable, "-I", str(HERE / "state_model.py")],
                           input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=5, check=False)
        return r, json.loads(r.stdout)

    def test_complete_cli_is_still_not_permission(self):
        r, result = self.run_cli(json.dumps(document()).encode())
        self.assertEqual(r.returncode, 0)
        self.assertFalse(result["writes_authorized"])
        self.assertEqual(r.stderr, b"")

    def test_oversized_input_is_bounded(self):
        r, result = self.run_cli(b" " * (M.MAX_INPUT + 1))
        self.assertEqual(r.returncode, 2)
        self.assertEqual(result["reason"], "input_bound")

    def test_duplicate_json_key_refused(self):
        r, result = self.run_cli(b'{"schema":"one","schema":"two"}')
        self.assertEqual(r.returncode, 2)
        self.assertEqual(result["reason"], "duplicate_json_key")

    def test_deep_json_refused_without_traceback(self):
        r, result = self.run_cli(b"[" * 2000 + b"0" + b"]" * 2000)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stderr, b"")
        self.assertEqual(result["status"], "REFUSED")

    def test_private_unknown_field_not_echoed(self):
        d = document(); d["serial"] = "SYNTHETIC-PRIVATE-MARKER"
        r, result = self.run_cli(json.dumps(d).encode())
        self.assertEqual(r.returncode, 2)
        self.assertNotIn(b"SYNTHETIC-PRIVATE-MARKER", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
