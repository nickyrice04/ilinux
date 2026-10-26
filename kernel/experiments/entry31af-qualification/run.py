#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify frozen 31AF's whole-image readability dependency with synthetic holes.

No native payload is generated or modified. --self-test performs Python fixture
checks only. Compile/emulation modes are restricted to an isolated Linux guest.
Apple firmware, native hardware and host boot configuration are never accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAYLOAD_SHA = "91d2ce73f79784b78c96e08c606d3622aa3246a7561fdbec4d1066ebe9bfaa7c"
PAYLOAD_BYTES = 393216
PINS = {
    "kernel/experiments/immutable31af-test/run.py": "6dacaebb09888da9b52d4e4ac1ca9b0823622022ca1c8f454d22e1e450c6f534",
    "kernel/experiments/immutable31af-test/bootstrap.S": "c40e44452e531e1de7ecd2646b8766856a82cb0fde79bf3f1f816805e2acbfb8",
    "kernel/experiments/immutable31af-test/README.md": "40cc80293da077be7a96745c76847e8a6f4041c42d5675559d7728ceea689ea0",
    "kernel/experiments/translation31ab/run.py": "26ddc30f52620e84e139a67f2a0a5dfafd7798cae19b77c65645f904e723a756",
    "native/boot/attempt31af/layout.json": "988e21ea24cf0b3a7ab0332877512dc7cbced8262f3e0d996cc3c9717b84cbe7",
}
HOLES = {
    "reserved-first": 0x4000,
    "reserved-middle": 0x2c000,
    "reserved-last": 0x54000,
    "unused-header": 0,
    "unused-normal-text": 0x58000,
}
HOLE_BYTES = 0x4000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def emit(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_sources():
    for name, expected in PINS.items():
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or sha(path.read_bytes()) != expected:
            raise ValueError("frozen source pin mismatch: " + name)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pte_offset(mode, image_offset):
    if mode == "16k-vhe":
        return 0x8000 + ((0x40400000 + image_offset - 0x40000000) // 0x4000) * 8
    if mode == "non-vhe":
        return 0x2000 + (image_offset // 0x1000) * 8
    raise ValueError("unsupported fixture mode")


def with_hole(original_tables, kind, cache, mode):
    baseline = original_tables("valid", cache, mode)
    if kind == "valid":
        return baseline
    offset = HOLES[kind]
    data = bytearray(baseline)
    granule = 0x4000 if mode == "16k-vhe" else 0x1000
    for page in range(offset, offset + HOLE_BYTES, granule):
        pos = pte_offset(mode, page)
        if not struct.unpack_from("<Q", data, pos)[0] & 1:
            raise ValueError("baseline page unexpectedly unmapped")
        struct.pack_into("<Q", data, pos, 0)
    return bytes(data)


def trials():
    for mode in ("non-vhe", "16k-vhe"):
        yield (mode + "-control", mode, "nc", 32, "valid", True)
        for kind in HOLES:
            yield (mode + "-" + kind, mode, "nc", 32, kind, False)


def fixture_check(harness, original_tables):
    base_check = harness.verify_fixture_generators()
    checked = []
    for label, mode, cache, depth, kind, paint in trials():
        baseline = original_tables("valid", cache, mode)
        candidate = with_hole(original_tables, kind, cache, mode)
        granule = 0x4000 if mode == "16k-vhe" else 0x1000
        permitted = set()
        if kind != "valid":
            for page in range(HOLES[kind], HOLES[kind] + HOLE_BYTES, granule):
                pos = pte_offset(mode, page)
                permitted.update(range(pos, pos + 8))
        if any(a != b and i not in permitted for i, (a, b) in enumerate(zip(baseline, candidate))):
            raise AssertionError("hole modifies an unrelated table byte")
        for page in range(0, harness.SIZE, granule):
            value = struct.unpack_from("<Q", candidate, pte_offset(mode, page))[0]
            omitted = kind != "valid" and HOLES[kind] <= page < HOLES[kind] + HOLE_BYTES
            if omitted:
                if value != 0:
                    raise AssertionError("expected omitted page remains mapped")
            elif not value & 1 or not value & 0x80:
                raise AssertionError("unaffected image page lost read-only mapping")
        for page in range(harness.ENTRY, harness.SIZE, granule):
            if not struct.unpack_from("<Q", candidate, pte_offset(mode, page))[0] & 1:
                raise AssertionError("boot entry/helper/vector page is unmapped")
        checked.append({"case": label, "page_table_bytes": len(candidate),
                        "omitted_image_offset": None if paint else HOLES[kind],
                        "omitted_bytes": 0 if paint else HOLE_BYTES,
                        "translation_granule": granule,
                        "expected_paint": paint, "expected_status": 0 if paint else 7})
    return {"status": "PASS", "cases": checked, "frozen_generator_self_test": base_check,
            "compiler_executed": False, "emulator_executed": False,
            "native_hardware": False, "apple_firmware": False}


def qualify_mapping(result, kind):
    # The reused harness truthfully checks unchanged physical bytes. Its generic
    # whole-reservation mapping label does not describe these omission fixtures.
    result.pop("reserved_sptm_readonly", None)
    omitted = None if kind == "valid" else {"offset": HOLES[kind], "bytes": HOLE_BYTES}
    reserved_hole = kind.startswith("reserved-")
    result["image_mapping"] = {
        "all_present_image_pages_readonly": True,
        "whole_image_mapped": kind == "valid",
        "omitted_image_range": omitted,
        "whole_reserved_sptm_mapped_readonly": not reserved_hole,
        "reserved_sptm_has_unmapped_pages": reserved_hole,
        "unmapped_pages_still_have_fixture_physical_storage": True,
    }
    result["qualification"] = "Synthetic dependency demonstration only; actual native reservation mappings and 31AF failure location remain unknown"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--layout", type=Path, default=ROOT / "native/boot/attempt31af/layout.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--qemu")
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--ld", default="ld")
    parser.add_argument("--objcopy", default="objcopy")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    verify_sources()  # Authenticate every reused import/include/transport first.
    harness = load_module("frozen31af_harness", ROOT / "kernel/experiments/immutable31af-test/run.py")
    original_tables = harness.tables
    fixtures = fixture_check(harness, original_tables)
    if args.self_test:
        print(json.dumps(fixtures, sort_keys=True))
        return 0
    if sys.platform != "linux":
        parser.error("compile/emulation runs require the isolated Linux guest; host permits --self-test only")
    if not args.payload or not args.output:
        parser.error("--payload and --output are required unless --self-test")
    output = args.output.resolve()
    source_root = ROOT / "kernel/experiments"
    if output.exists() or output == source_root or source_root in output.parents:
        parser.error("use a fresh output outside all experiment source directories")
    if args.payload.is_symlink() or not args.payload.is_file():
        raise ValueError("payload must be a regular file")
    payload = args.payload.read_bytes()
    if len(payload) != PAYLOAD_BYTES or sha(payload) != PAYLOAD_SHA:
        raise ValueError("requires the exact released 31AF linked payload")
    if args.layout.is_symlink() or sha(args.layout.read_bytes()) != PINS["native/boot/attempt31af/layout.json"]:
        raise ValueError("requires the exact frozen 31AF layout")
    layout = json.loads(args.layout.read_text())
    if layout["payload_sha256"] != PAYLOAD_SHA or layout["symbols"]["native_entry"]["offset"] != 0x5c000:
        raise ValueError("layout geometry does not bind the exact payload")
    output.mkdir(parents=True)
    own_sources = [HERE / "run.py", HERE / "README.md"]
    bindings = [{"file": str(path.relative_to(ROOT)), "sha256": sha(path.read_bytes())}
                for path in own_sources]
    bindings += [{"file": name, "sha256": digest} for name, digest in PINS.items()]
    emit(output / "source-bindings.json", bindings)
    qmp = load_module("frozen31af_qmp", ROOT / "kernel/experiments/translation31ab/run.py")
    harness.tables = lambda kind, cache, mode="non-vhe": with_hole(original_tables, kind, cache, mode)
    harness.REFUSALS = dict(harness.REFUSALS, **{kind: 7 for kind in HOLES})
    report = {"schema": "ilinux-entry31af-qualification-v1", "status": "FAIL", "cases": [],
              "payload_sha256": PAYLOAD_SHA, "payload_bytes": PAYLOAD_BYTES,
              "fixture_checks": fixtures, "apple_firmware": False, "native": "NOT_RUN",
              "payload_executed_in_emulator": bool(args.qemu),
              "native_payload_modified": False,
              "native_failure_diagnosed": False,
              "conclusion_scope": "Finite synthetic image-mapping dependency only"}
    try:
        if args.qemu:
            report["qemu_version"] = subprocess.check_output([args.qemu, "--version"], text=True, timeout=30)
        for trial in trials():
            result = harness.case(qmp.QMP, args.qemu, payload, layout, output, trial,
                                  args.cc, args.ld, args.objcopy)
            result = qualify_mapping(result, trial[4])
            report["cases"].append(result)
            emit(output / trial[0] / "result.json", result)
        report["status"] = "PASS" if args.qemu else "PREPARED_NOT_EXECUTED"
    finally:
        report["source_files_unchanged"] = all(
            sha((ROOT / binding["file"]).read_bytes()) == binding["sha256"] for binding in bindings)
        if not report["source_files_unchanged"]:
            report["status"] = "FAIL"
        report["source_bindings_sha256"] = sha((output / "source-bindings.json").read_bytes())
        emit(output / "results.json", report)
    print(json.dumps({"status": report["status"], "cases": len(report["cases"])}))
    return int(report["status"] == "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())
