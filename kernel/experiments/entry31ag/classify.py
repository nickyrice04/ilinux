#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify bounded entry evidence without promoting a blank or VM into native proof.

This validates supported report fields; it does not authenticate their provenance.
It reads no machine state, raw register dump, installed object or private artifact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PAYLOAD_SHA = "91d2ce73f79784b78c96e08c606d3622aa3246a7561fdbec4d1066ebe9bfaa7c"
REFUSAL_STAGES = {
    1: "entry-reason-refusal", 2: "entry-level-refusal", 3: "hcr-profile-refusal",
    5: "mmu-profile-refusal", 6: "translation-format-refusal", 7: "image-readability-refusal",
    8: "boot-record-readability-refusal", 9: "monitor-record-readability-refusal",
    10: "helper-version-refusal", 11: "count-readability-refusal", 12: "count-range-refusal",
    13: "table-readability-refusal", 14: "table-format-refusal", 15: "video-format-refusal",
    16: "framebuffer-plan-refusal", 17: "framebuffer-translation-refusal",
    18: "framebuffer-physical-address-refusal", 19: "framebuffer-attribute-refusal",
    20: "framebuffer-alias-refusal", 23: "endianness-refusal", 24: "translation-control-refusal",
    25: "cache-line-refusal", 26: "cache-extent-refusal",
}


def classify(report):
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    result = {"schema": "ilinux-entry-evidence31ag-v1", "native_entry": "UNCONFIRMED",
              "pre_entry_failure_proven": False, "apple_update_required_proven": False,
              "new_native_boot_ready": False,
              "provenance_authenticated": False}
    schema = report.get("schema")
    if schema == "ilinux-attempt31af-human-result-v1":
        observed = report.get("native_observation")
        if not isinstance(observed, dict):
            raise ValueError("human report lacks native observation")
        if type(observed.get("attempted")) is not bool or type(observed.get("marker_reported")) is not bool:
            raise ValueError("observation attempted/marker must be Boolean")
        if observed["marker_reported"] and not observed["attempted"]:
            raise ValueError("reported marker contradicts unattempted observation")
        result.update(environment="human-reported-native", installation="NOT_INDEPENDENTLY_VERIFIED",
                      outcome="marker-reported" if observed["marker_reported"] else "no-marker-reported",
                      furthest_supported_stage="HUMAN_REPORTED_PIXEL_VISIBILITY" if observed["marker_reported"] else "UNKNOWN")
        if observed["marker_reported"]:
            result["native_entry"] = "HUMAN_REPORTED; not independently authenticated"
        result["next_requirement"] = "qualified loader/entry evidence; complete or confirm existing restoration"
        return result
    if schema != "ilinux-entry31ag-runtime-v1":
        raise ValueError("unsupported evidence schema")
    if report.get("native") != "NOT_RUN" or report.get("apple_firmware") is not False:
        raise ValueError("this runtime schema describes only standard emulator evidence")
    if report.get("payload_sha256") != PAYLOAD_SHA or report.get("status") != "PASS":
        raise ValueError("runtime report must bind a passing frozen-payload run")
    cases = report.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("runtime cases missing")
    states = []
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or case.get("status") != "PASS" or case.get("native") != "NOT_RUN":
            raise ValueError("case is not a passing emulator observation")
        name = case.get("case")
        if not isinstance(name, str) or not name or len(name) > 80 or name in seen:
            raise ValueError("invalid or duplicate case")
        seen.add(name)
        phase, code = case.get("phase"), case.get("diagnostic_status")
        if type(phase) is not int or type(code) is not int:
            raise ValueError("phase/status must be integers")
        if type(case.get("painted_pixels")) is not int or case["painted_pixels"] < 0:
            raise ValueError("painted pixel count must be a nonnegative integer")
        if phase == 7 and code == 0 and case.get("painted_pixels") == 8192:
            stage = "emulated-paint-complete"
        elif phase == 0x80 and code in REFUSAL_STAGES and case.get("painted_pixels") == 0:
            stage = REFUSAL_STAGES[code]
        else:
            raise ValueError("unsupported or contradictory terminal state")
        states.append({"case": name, "observed_in_emulator": stage})
    result.update(environment="standard-arm-emulator", states=states,
                  furthest_supported_stage="EMULATOR_ONLY",
                  next_requirement="qualified native readback or equivalent positive control")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.report.is_symlink() or not args.report.is_file() or args.report.stat().st_size > 1024 * 1024:
        parser.error("report must be a regular JSON file no larger than1MiB")
    try:
        result = classify(json.loads(args.report.read_text()))
    except (ValueError, TypeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
