#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline 31I intake; source/image binding and original model tests only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('frozen_intake31h',ROOT/'tools/m1n1-client/attempt31h-offline.py')
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
MANIFEST='native/boot/attempt31i/source-sha256.txt'
TESTS=previous.TESTS+(
    'native/boot/test_smp31i.py',
    'kernel/experiments/smp31i-readback/test_gate.py',
    'tools/m1n1-client/test_attempt31i_offline.py',
    'tools/m1n1-client/test_attempt31i_supervisor.py',
)
FULL_SYMBOL_TESTS=previous.FULL_SYMBOL_TESTS
REQUIRED=previous.REQUIRED | set(TESTS) | {
    'native/boot/attempt31h/source-sha256.txt',
    'native/boot/attempt31h-controller-2026-10-21.json',
    'native/boot/smp31i.py',
    'kernel/experiments/smp31i-readback/gate.py',
    'kernel/experiments/smp31/test_client31i_vm.py',
    'tools/m1n1-client/attempt31i-offline.py',
    'tools/m1n1-client/attempt31i-supervisor.py',
    'tools/m1n1-client/attempt31i-instructions.md',
    'virtualization/jobs/067-smp31i/run.sh',
    'research/native31i-readback.md',
    'native/boot/attempt31i/controller-review.md',
    'native/boot/attempt31i/controller-validation.md',
}


def need(condition, why):
    if not condition:
        raise ValueError(why)

def source_pins(root=ROOT):
    manifest = root / MANIFEST
    need(manifest.is_file() and not manifest.is_symlink(), 'manifest_file')
    data = manifest.read_bytes()
    need(0 < len(data) < 65536, 'manifest_size')
    seen = set()
    for line in data.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        need(match is not None, 'manifest_syntax')
        digest, name = match.groups()
        relative = Path(name)
        need(not relative.is_absolute() and '..' not in relative.parts and name not in seen,
             'manifest_path')
        path = root / relative
        need(not any(p.is_symlink() for p in [path, *path.parents]
                     if p.is_relative_to(root)), 'source_symlink')
        need(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
             'source_digest')
        seen.add(name)
    need(REQUIRED <= seen, 'manifest_incomplete')
    return len(seen), hashlib.sha256(data).hexdigest()

def run_check(name, args):
    # Fixed repository commands only. No shell, environment override, target
    # transport, arbitrary executable, retry or resume parameter exists.
    result = subprocess.run([sys.executable, '-I', str(ROOT / name), *args],
                            cwd=ROOT, stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=30, check=False)
    need(result.returncode == 0, 'offline_check_failed:' + name)
    return result.stdout, result.stderr

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path)
    args = parser.parse_args()
    need(args.image.is_file() and not args.image.is_symlink(), 'image_file')
    pins, digest = source_pins()
    emulator_args = ['--image', str(args.image.absolute())]
    if args.symbols is not None:
        need(args.symbols.is_file() and not args.symbols.is_symlink(), 'symbol_file')
        emulator_args += ['--symbols', str(args.symbols.absolute())]
    rows, total = [], 0
    selected = TESTS + (FULL_SYMBOL_TESTS if args.symbols is not None else ())
    for test in selected:
        image_test = test.endswith('test_emulate.py') or test in FULL_SYMBOL_TESTS
        stdout, stderr = run_check(test, emulator_args if image_test else [])
        output = stdout + stderr
        count = re.search(rb'Ran ([0-9]+) tests? in ', output)
        need(count is not None and b'skipped=' not in output, 'test_count_or_skip')
        methods = int(count.group(1))
        need(methods > 0, 'empty_suite')
        rows.append(dict(check=test, methods=methods, result='PASS'))
        total += methods
    if args.symbols is not None:
        stdout, _ = run_check('kernel/experiments/smp31f-entry/audit.py',
                             emulator_args)
        audit = json.loads(stdout)
        need(audit['result'] == 'STATIC_VECTOR_ENTRY_AUDIT_PASS', 'entry_audit')
        rows.append(dict(check='complete_entry_image_and_symbol_audit', result='PASS'))
        stdout, _ = run_check('kernel/experiments/smp31f-entry/recorder_check.py', emulator_args)
        recorder = json.loads(stdout)
        need(recorder.get('result') == 'OFFLINE_VECTOR_FIRST_EQUIVALENCE_PASS_NATIVE_HOLD' and
             isinstance(recorder.get('scenarios'), list) and len(recorder['scenarios']) == 13,
             'recorder_model_contract')
        rows.append(dict(check='stackless_recorder_equivalence', result='PASS', scenarios=13))
    run_check('native/boot/smp31i.py', ['--image', str(args.image.absolute())])
    rows.append(dict(check='native_controller_offline_source_image_helper_check', result='PASS'))
    stdout, _ = run_check('kernel/experiments/smp31e-emulator/emulate.py', emulator_args)
    model = json.loads(stdout)
    symbol_mode = 'full_symbol_digest' if args.symbols is not None else 'reviewed_layout_only'
    need(model.get('result') == 'MODELED_ENTRY_MATRIX' and
         model.get('native_execution') == 'NOT RUN' and model.get('hardware_model') is False and
         model.get('symbol_validation') == symbol_mode, 'model_result_contract')
    scenarios = model.get('scenarios', [])
    need(isinstance(scenarios, list) and len(scenarios) == 8 and
         {row.get('case') for row in scenarios} == {'table_miss', 'table_hit',
          'matching_zero_stack', 'el2_miss', 'el3_shared', 'mpidr_high_bits',
          'last_slot_hit', 'other_entry'} and
         all(row.get('result') == 'MODELED_FIRST_FRAME_STORE' and
             row.get('native_execution') == 'NOT RUN' and row.get('hardware_model') is False and
             row.get('symbol_validation') == symbol_mode for row in scenarios),
         'model_scenario_contract')
    need(source_pins() == (pins, digest), 'sources_changed_during_intake')
    print(json.dumps(dict(result='OFFLINE_CHECKS_PASS_AWAIT_HUMAN_START',
        source_pins=pins, source_manifest_sha256=digest, unit_test_methods=total,
        checks=rows, instruction_model=model, native_31i='NOT RUN',
        full_symbol_checks='PASS' if args.symbols is not None else 'NOT RUN: symbol file not supplied',
        cpu1_entry='UNVERIFIED', linux_smp='NOT RUN',
        restart_ready=False, next_step='M1 publishes independent intake; human starts one supervised lab session', hardware_operations=0), indent=2))

if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        # Avoid publishing private input paths or subprocess output.
        print(json.dumps(dict(result='OFFLINE_REFUSED_NATIVE_HOLD',
            reason=str(exc) if type(exc) is ValueError else type(exc).__name__,
            restart_ready=False, hardware_operations=0)))
        raise SystemExit(1)
