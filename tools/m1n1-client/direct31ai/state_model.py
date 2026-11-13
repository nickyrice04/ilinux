#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit a sanitized, OFFLINE boot/restoration model; never query or change a Mac.

Reads bounded JSON from stdin and writes JSON to stdout. Every assertion is
caller supplied. A complete model is neither verified hardware nor permission.
"""
import hashlib
import json
import re
import sys

SCHEMA = "ilinux-direct31ai-restoration-model-v1"
TARGET = {"model": "Mac17,6", "board": "j716c", "chip_id": "0x6050"}
BOOT021_SHA256 = "ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664"
BOOT021_BYTES = 3932160
MAX_INPUT = 64 * 1024
MAX_EVENTS = 16
MAX_NATIVE_MS = 90000
REQUIRED_REVIEWS = (
    "legacy31af_reconciled", "global_firmware_identity_reviewed",
    "paired_iboot_identity_reviewed", "firmware_pair_qualified",
    "candidate_and_ram_root_bound", "rollback_policy_recipe_reviewed",
    "paired_recovery_and_original_return_reviewed",
    "ram_only_diagnostic_reviewed", "external_stop_reviewed",
)
SNAPSHOT_KEYS = {
    "context", "target_binding", "original_security", "lab_security",
    "lab_ctrr", "selected_object", "selected_object_sha256", "default_entry",
    "unrelated_lab_policy_matches_baseline",
}
SNAPSHOT_STAGES = {
    "baseline", "recovery_before_candidate", "candidate_postcondition",
    "recovery_before_restore", "raw_policy_postcondition",
    "boot021_postcondition", "original_return",
}
ATTEMPT_STAGES = {"candidate_attempt", "raw_policy_attempt", "boot021_attempt"}
ALLOWED = {
    "start": {"baseline"},
    "baseline": {"recovery_before_candidate"},
    "recovery_before_candidate": {"candidate_attempt"},
    # An ambiguous/failed configure must be reconciled, never inferred unchanged.
    "candidate_attempt": {"candidate_postcondition", "recovery_before_restore"},
    "candidate_postcondition": {"native_window", "recovery_before_restore"},
    "native_window": {"recovery_before_restore"},
    "recovery_before_restore": {"raw_policy_attempt", "raw_policy_postcondition"},
    "raw_policy_attempt": {"raw_policy_postcondition"},
    "raw_policy_postcondition": {"boot021_attempt"},
    "boot021_attempt": {"boot021_postcondition"},
    "boot021_postcondition": {"original_return"},
    "original_return": set(),
}


class Refusal(ValueError):
    """A fixed, nonidentifying reason, never caller-provided text."""


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def exact_keys(value, keys, reason):
    require(type(value) is dict and set(value) == set(keys), reason)


def tri(value):
    return type(value) is bool or value == "unknown"


def sha(value):
    return type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def pairs(values):
    result = {}
    for key, value in values:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def validate_plan(plan):
    exact_keys(plan, set(REQUIRED_REVIEWS) | {
        "target", "candidate_sha256", "rollback_sha256", "rollback_bytes",
        "native_deadline_ms", "capture_mode",
    }, "plan_schema")
    require(plan["target"] == TARGET, "wrong_target")
    require(sha(plan["candidate_sha256"]) or plan["candidate_sha256"] == "unknown",
            "candidate_digest")
    require(plan["candidate_sha256"] != BOOT021_SHA256, "candidate_is_rollback")
    require(plan["rollback_sha256"] == BOOT021_SHA256, "wrong_boot021_digest")
    require(type(plan["rollback_bytes"]) is int and
            plan["rollback_bytes"] == BOOT021_BYTES, "wrong_boot021_size")
    require(type(plan["native_deadline_ms"]) is int and
            0 < plan["native_deadline_ms"] <= MAX_NATIVE_MS, "native_deadline")
    require(plan["capture_mode"] in ("screen_only", "usb_and_screen"), "capture_mode")
    for key in REQUIRED_REVIEWS:
        require(tri(plan[key]), "review_field_type")


def snapshot(facts, plan):
    exact_keys(facts, SNAPSHOT_KEYS, "snapshot_schema")
    require(facts["context"] in (
        "original_desktop", "lab_paired_1tr", "ordinary_recovery",
        "original_recovery", "unknown"), "context_value")
    require(facts["target_binding"] in (
        "distinct_lab_verified", "wrong_target", "unknown"), "target_binding_value")
    for key in ("original_security", "lab_security"):
        require(facts[key] in ("full", "reduced", "permissive", "unknown"),
                "security_value")
    require(facts["lab_ctrr"] in ("enabled", "disabled", "unknown"), "ctrr_value")
    require(facts["default_entry"] in ("original", "lab", "other", "unknown"),
            "default_value")
    require(facts["selected_object"] in ("boot021", "candidate", "other", "unknown"),
            "object_value")
    digest = facts["selected_object_sha256"]
    require(sha(digest) or digest == "unknown", "selected_digest")
    require(tri(facts["unrelated_lab_policy_matches_baseline"]), "policy_field_type")
    require(facts["target_binding"] == "distinct_lab_verified", "target_not_verified")
    require(facts["original_security"] == "full", "original_not_full")
    require(facts["lab_security"] == "permissive", "lab_policy_not_qualified")
    require(facts["unrelated_lab_policy_matches_baseline"] is True,
            "unrelated_lab_policy_not_verified")
    require(facts["lab_ctrr"] != "unknown", "ctrr_unknown")
    require(facts["selected_object"] in ("boot021", "candidate"), "object_unknown")
    expected = (BOOT021_SHA256 if facts["selected_object"] == "boot021"
                else plan["candidate_sha256"])
    require(digest == expected, "selected_object_digest_mismatch")
    require(facts["default_entry"] in ("original", "lab"), "default_unknown")


def analyze(document):
    exact_keys(document, {"schema", "origin", "plan", "events"}, "document_schema")
    require(document["schema"] == SCHEMA, "schema")
    require(document["origin"] in ("SYNTHETIC", "SANITIZED_ASSERTIONS"), "origin")
    plan = document["plan"]
    validate_plan(plan)
    events = document["events"]
    require(type(events) is list and len(events) <= MAX_EVENTS, "event_bound")
    current = "start"
    native_windows = 0
    last_candidate_result = None
    previous = None
    last_object = last_ctrr = None
    object_may_have_changed = ctrr_may_have_changed = False
    for event in events:
        exact_keys(event, {"stage", "facts"}, "event_schema")
        stage, facts = event["stage"], event["facts"]
        require(type(stage) is str and stage in ALLOWED[current], "transition_order")
        if stage in SNAPSHOT_STAGES:
            snapshot(facts, plan)
            observed_object = facts["selected_object_sha256"]
            require(last_object is None or object_may_have_changed or
                    observed_object == last_object, "unrecorded_object_change")
            require(last_ctrr is None or ctrr_may_have_changed or
                    facts["lab_ctrr"] == last_ctrr, "unrecorded_ctrr_change")
            context = "original_desktop" if stage in (
                "baseline", "original_return") else "lab_paired_1tr"
            require(facts["context"] == context, "context_not_qualified")
            if stage in ("baseline", "recovery_before_candidate",
                         "boot021_postcondition", "original_return"):
                require(facts["selected_object"] == "boot021", "boot021_not_observed")
                require(facts["lab_ctrr"] == "disabled", "raw_ctrr_not_disabled")
            if stage in ("baseline", "original_return"):
                require(facts["default_entry"] == "original", "original_default_not_verified")
            if stage == "baseline":
                require(plan["legacy31af_reconciled"] is True, "legacy_restore_unconfirmed")
            if stage == "candidate_postcondition":
                require(last_candidate_result == "exit_zero", "candidate_attempt_not_successful")
                require(facts["selected_object"] == "candidate", "candidate_not_observed")
                require(facts["lab_ctrr"] == "enabled", "direct_ctrr_not_enabled")
            if stage == "raw_policy_postcondition":
                require(facts["lab_ctrr"] == "disabled", "raw_ctrr_not_disabled")
                if current == "recovery_before_restore":
                    require(previous["lab_ctrr"] == "disabled", "policy_change_unrecorded")
            last_object, last_ctrr = observed_object, facts["lab_ctrr"]
            object_may_have_changed = ctrr_may_have_changed = False
        elif stage in ATTEMPT_STAGES:
            exact_keys(facts, {"result"}, "attempt_schema")
            require(facts["result"] in (
                "exit_zero", "exit_nonzero", "timeout", "interrupted"), "attempt_result")
            require(all(plan[key] is True for key in REQUIRED_REVIEWS), "review_gate_open")
            require(sha(plan["candidate_sha256"]), "candidate_digest_unknown")
            if stage == "candidate_attempt":
                last_candidate_result = facts["result"]
                object_may_have_changed = ctrr_may_have_changed = True
            if stage == "raw_policy_attempt":
                require(previous["lab_ctrr"] == "enabled", "unnecessary_policy_attempt")
                ctrr_may_have_changed = True
            if stage == "boot021_attempt":
                object_may_have_changed = ctrr_may_have_changed = True
        elif stage == "native_window":
            exact_keys(facts, {"elapsed_ms", "external_stop_observed", "screen"},
                       "native_window_schema")
            require(type(facts["elapsed_ms"]) is int and
                    0 < facts["elapsed_ms"] <= plan["native_deadline_ms"], "native_overrun")
            require(facts["external_stop_observed"] is True, "external_stop_not_observed")
            require(facts["screen"] in (
                "diagnostic_summary", "logo_only", "no_output", "fault"), "screen_value")
            native_windows += 1
        previous = facts
        current = stage
    reviews_missing = [key for key in REQUIRED_REVIEWS if plan[key] is not True]
    if plan["candidate_sha256"] == "unknown":
        reviews_missing.append("candidate_sha256")
    complete = current == "original_return"
    return {
        "schema": "ilinux-direct31ai-restoration-model-result-v1",
        "status": "OFFLINE_MODEL_COMPLETE" if complete else "OFFLINE_HOLD",
        "origin": document["origin"], "last_stage": current,
        "next_model_stages": sorted(ALLOWED[current]),
        "missing_reviews": reviews_missing,
        "native_windows_modelled": native_windows,
        "restoration_assertions_complete": complete,
        "input_claims_independently_verified": False,
        "hardware_state_verified": False, "restoration_verified": False,
        "native_execution_proven": False, "native_ready": False,
        "writes_authorized": False, "host_queried": False,
        "external_stop_is_physical_human_action": True,
    }


def main():
    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    require(len(raw) <= MAX_INPUT, "input_bound")
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    result = analyze(document)
    # Bind the exact accepted assertions without copying identifiers/free text.
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Refusal as error:
        print(json.dumps({"status": "REFUSED", "reason": str(error),
                          "host_queried": False, "native_ready": False,
                          "writes_authorized": False}))
        raise SystemExit(2)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        print(json.dumps({"status": "REFUSED", "reason": "invalid_bounded_json",
                          "host_queried": False, "native_ready": False,
                          "writes_authorized": False}))
        raise SystemExit(2)
