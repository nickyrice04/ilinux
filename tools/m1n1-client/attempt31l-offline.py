#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline 31L intake; source/image binding and original model tests only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('frozen_intake31k',ROOT/'tools/m1n1-client/attempt31k-offline.py')
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
MANIFEST='native/boot/attempt31l/source-sha256.txt'
TESTS=previous.TESTS+(
    'kernel/experiments/smp31l-candidate/test_candidate.py',
    'kernel/experiments/smp31l-observer/test_observer.py',
    'native/boot/test_smp31l.py',
    'tools/m1n1-client/test_attempt31l_offline.py',
    'tools/m1n1-client/test_attempt31l_supervisor.py',
)
FULL_SYMBOL_TESTS=previous.FULL_SYMBOL_TESTS
REQUIRED=previous.REQUIRED | set(TESTS) | {
    'native/boot/attempt31k/source-sha256.txt',
    'native/boot/smp31l.py',
    'tools/m1n1-client/attempt31l-offline.py',
    'tools/m1n1-client/attempt31l-supervisor.py',
    'tools/m1n1-client/attempt31l-instructions.md',
    'kernel/experiments/smp31/test_client31l_vm.py',
    'virtualization/jobs/071-smp31l/run.sh',
    'research/native31l-entry.md',
    'research/native31l-platform-prepare.md',
    'research/native31l-first-fetch.md',
    'reverse-engineering/findings/cpu-startup31l-first-fetch/validation.json',
    'reverse-engineering/findings/cpu-startup31l/entry-provenance-validation.json',
    'reverse-engineering/findings/cpu-startup31l-platform/validation.json',
    'native/boot/attempt31l/controller-review.md',
    'native/boot/attempt31l/controller-validation.md',
    'kernel/experiments/smp31l-candidate/audit.py',
    'kernel/experiments/smp31l-candidate/builder.py',
    'kernel/experiments/smp31l-candidate/model.py',
    'kernel/experiments/smp31l-candidate/prefix.S',
    'kernel/experiments/smp31l-candidate/README.md',
    'kernel/experiments/smp31l-candidate/validation.json',
    'kernel/experiments/smp31l-observer/observer.py',
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
        need(not relative.is_absolute() and '..' not in relative.parts and
             relative.as_posix() == name and name not in seen,
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
        image_test = (test.endswith('test_emulate.py') or test in FULL_SYMBOL_TESTS or
                      test in ('kernel/experiments/smp31k-entry/test_tripwire.py',
                               'kernel/experiments/smp31l-candidate/test_candidate.py'))
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
    run_check('kernel/experiments/smp31k-entry/audit.py', emulator_args)
    run_check('kernel/experiments/smp31k-control/audit.py', ['--image', str(args.image.absolute())])
    rows.append(dict(check='cold_entry_and_cpu0_control_exact_image_audits', result='PASS'))
    run_check('native/boot/smp31l.py', ['--image', str(args.image.absolute())])
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
        checks=rows, instruction_model=model, native_31l='NOT RUN',
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
