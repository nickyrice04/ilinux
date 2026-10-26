#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise frozen31AF entry assumptions with an EL1 and raw-argument control.

Only run compilation/emulation in the isolated Linux job VM. This creates no
native image, calls no monitor service, and never loads Apple firmware.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAYLOAD_SHA = "91d2ce73f79784b78c96e08c606d3622aa3246a7561fdbec4d1066ebe9bfaa7c"
PINS = {
    "kernel/experiments/immutable31af-test/run.py": "6dacaebb09888da9b52d4e4ac1ca9b0823622022ca1c8f454d22e1e450c6f534",
    "kernel/experiments/immutable31af-test/bootstrap.S": "c40e44452e531e1de7ecd2646b8766856a82cb0fde79bf3f1f816805e2acbfb8",
    "kernel/experiments/translation31ab/run.py": "26ddc30f52620e84e139a67f2a0a5dfafd7798cae19b77c65645f904e723a756",
    "native/boot/attempt31af/layout.json": "988e21ea24cf0b3a7ab0332877512dc7cbced8262f3e0d996cc3c9717b84cbe7",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def emit(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--layout", type=Path, default=ROOT / "native/boot/attempt31af/layout.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qemu", required=True)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--ld", default="ld")
    parser.add_argument("--objcopy", default="objcopy")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("compile/emulation requires the isolated Linux job VM")
    for name, expected in PINS.items():
        p = ROOT / name
        if p.is_symlink() or sha(p.read_bytes()) != expected:
            raise ValueError("frozen dependency mismatch: " + name)
    if args.payload.is_symlink() or not args.payload.is_file():
        raise ValueError("payload must be a regular file")
    payload = args.payload.read_bytes()
    if len(payload) != 393216 or sha(payload) != PAYLOAD_SHA:
        raise ValueError("requires the exact frozen31AF payload")
    if args.layout.is_symlink() or sha(args.layout.read_bytes()) != PINS["native/boot/attempt31af/layout.json"]:
        raise ValueError("requires the frozen31AF layout")
    output = args.output.resolve()
    if output.exists() or output == ROOT / "kernel/experiments" or ROOT / "kernel/experiments" in output.parents:
        parser.error("use a fresh output outside all experiment source directories")
    layout = json.loads(args.layout.read_text())
    output.mkdir(parents=True)
    sources = [HERE / name for name in ("run.py", "bootstrap-el1.S", "classify.py", "test_classify.py", "README.md")]
    bindings = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p.read_bytes())} for p in sources]
    bindings += [{"file": name, "sha256": digest} for name, digest in PINS.items()]
    emit(output / "source-bindings.json", bindings)
    harness = load("entry31ag_frozen_harness", ROOT / "kernel/experiments/immutable31af-test/run.py")
    qmp = load("entry31ag_frozen_qmp", ROOT / "kernel/experiments/translation31ab/run.py")
    classifier = load("entry31ag_classifier", HERE / "classify.py")
    original_arguments, original_command = harness.arguments, harness.command
    active_kind = [None]

    def arguments(kind, depth):
        result = original_arguments("valid", depth)
        if kind == "raw-bootargs":
            data, reason, boot, monitor = result
            return data, harness.ARGS, 0, 0
        return result

    def command(argv, out, label):
        if active_kind[0] == "el1-cold" and label == "bootstrap-compile":
            argv = [str(HERE / "bootstrap-el1.S") if word == str(harness.HERE / "bootstrap.S") else word
                    for word in argv]
        return original_command(argv, out, label)

    harness.arguments, harness.command = arguments, command
    harness.REFUSALS = dict(harness.REFUSALS, **{"el1-cold": 2, "raw-bootargs": 1})
    trials = [("el2-resident-cold", "non-vhe", "nc", 32, "valid", True),
              ("el1-resident-cold", "non-vhe", "nc", 32, "el1-cold", False),
              ("el2-raw-bootargs", "non-vhe", "nc", 32, "raw-bootargs", False)]
    report = {"schema": "ilinux-entry31ag-runtime-v1", "status": "FAIL", "cases": [],
              "payload_sha256": PAYLOAD_SHA, "native": "NOT_RUN", "apple_firmware": False,
              "native_payload_generated": False,
              "loaded_memory_model": "Original instruction bytes; reservation populated with existing synthetic A5 sentinel"}
    try:
        report["qemu_version"] = subprocess.check_output([args.qemu, "--version"], text=True, timeout=30)
        for trial in trials:
            active_kind[0] = trial[4]
            case = harness.case(qmp.QMP, args.qemu, payload, layout, output, trial,
                                args.cc, args.ld, args.objcopy)
            pstate = int(case["registers"]["PSTATE"], 16)
            wanted_el = 1 if trial[4] == "el1-cold" else 2
            if (pstate >> 2) & 3 != wanted_el:
                raise RuntimeError("case did not actually execute at the requested EL")
            case["observed_entry_el"] = wanted_el
            case["argument_profile"] = "raw-x0-BootArgs" if trial[4] == "raw-bootargs" else "resident-cold"
            if wanted_el == 1:
                case.pop("fixture_tcr", None)
                case.pop("fixture_hcr", None)
                case["mode"] = "EL1h-translation-disabled"
                case["translation_granule"] = None
                case["fixture_el1_mmu"] = False
                case["image_pages_permission_qualification"] = "Physical unchanged-byte check only; EL1 translation is disabled"
                case.pop("reserved_sptm_readonly", None)
            report["cases"].append(case)
            emit(output / trial[0] / "result.json", case)
        report["status"] = "PASS"
        emit(output / "classification.json", classifier.classify(report))
    finally:
        report["source_files_unchanged"] = all(sha((ROOT / b["file"]).read_bytes()) == b["sha256"] for b in bindings)
        if not report["source_files_unchanged"]:
            report["status"] = "FAIL"
        report["source_bindings_sha256"] = sha((output / "source-bindings.json").read_bytes())
        emit(output / "results.json", report)
    print(json.dumps({"status": report["status"], "cases": len(report["cases"])}))
    return int(report["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
