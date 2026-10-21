#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Source-pinned offline 31G intake. No USB or live-controller invocation.

Runs only fixed repository Python checks. A pass records offline readiness; a fresh human start remains required for
the separate native command. The symbol file is optional for M1's retained package.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'native/boot/attempt31g/source-sha256.txt'
TESTS = (
    'native/boot/test_smp31g.py',
    'kernel/experiments/smp31g-observation/test_plan.py',
    'kernel/experiments/smp31g-observation/test_tracker.py',
    'kernel/experiments/smp31g-publication/test_audit.py',
    'kernel/experiments/cpu-topology31g/test_topology.py',
    'tools/m1n1-client/test_attempt31g_supervisor.py',
    'kernel/experiments/smp31e-entry/test_permissions.py',
    'kernel/experiments/smp31f-entry/test_telemetry.py',
    'tools/boot-campaign/test_campaign.py',
    'kernel/experiments/smp31e-entry/test_observe.py',
    'kernel/experiments/smp31e-entry/test_audit.py',
    'kernel/experiments/smp31e-observer/test_collector.py',
    'kernel/experiments/smp31e-emulator/test_emulate.py',
    'tools/m1n1-client/test_attempt31g_offline.py',
    'kernel/experiments/smp31f-entry/test_permissions.py',
    'kernel/experiments/cpu-topology31f/test_topology.py',
)
FULL_SYMBOL_TESTS = (
    'kernel/experiments/smp31f-entry/test_recorder_check.py',
)
REQUIRED = {
    'hardware/adt/adt-sanitized.json',
    'kernel/experiments/cpu-topology31f/audit.py',
    'kernel/experiments/cpu-topology31f/capture_linux.py',
    'kernel/experiments/cpu-topology31f/test_topology.py',
    'kernel/experiments/smp31/audit_boot021.py',
    'kernel/experiments/smp31/audit_console31d.py',
    'kernel/experiments/smp31/boot021-ram-layout.json',
    'kernel/experiments/smp31/memory_fixture31c.py',
    'kernel/experiments/smp31/rea-validation.json',
    'kernel/experiments/smp31/renderer.py',
    'kernel/experiments/smp31/test_audit_boot021.py',
    'kernel/experiments/smp31/test_client31b_vm.py',
    'kernel/experiments/smp31/test_client31c_vm.py',
    'kernel/experiments/smp31/test_client31d_vm.py',
    'kernel/experiments/smp31/test_client31e_vm.py',
    'kernel/experiments/smp31/test_client31f_vm.py',
    'kernel/experiments/smp31/test_parser_vm.py',
    'kernel/experiments/smp31/test_renderer.py',
    'kernel/experiments/smp31e-emulator/emulate.py',
    'kernel/experiments/smp31e-emulator/recorder_check.py',
    'kernel/experiments/smp31e-emulator/test_emulate.py',
    'kernel/experiments/smp31e-emulator/test_recorder_check.py',
    'kernel/experiments/smp31e-entry/audit.py',
    'kernel/experiments/smp31e-entry/build_recorder.py',
    'kernel/experiments/smp31e-entry/observe.py',
    'kernel/experiments/smp31e-entry/permission_helper.S',
    'kernel/experiments/smp31e-entry/permissions.py',
    'kernel/experiments/smp31e-entry/recorder.S',
    'kernel/experiments/smp31e-entry/start_helper.S',
    'kernel/experiments/smp31e-entry/telemetry.py',
    'kernel/experiments/smp31e-entry/test_audit.py',
    'kernel/experiments/smp31e-entry/test_observe.py',
    'kernel/experiments/smp31e-entry/test_permissions.py',
    'kernel/experiments/smp31e-entry/test_recorder.py',
    'kernel/experiments/smp31e-entry/test_telemetry.py',
    'kernel/experiments/smp31e-observer/collector.py',
    'kernel/experiments/smp31e-observer/test_collector.py',
    'kernel/experiments/smp31f-entry/audit.py',
    'kernel/experiments/smp31f-entry/builder.py',
    'kernel/experiments/smp31f-entry/permissions.py',
    'kernel/experiments/smp31f-entry/recorder.S',
    'kernel/experiments/smp31f-entry/recorder_check.py',
    'kernel/experiments/smp31f-entry/telemetry.py',
    'kernel/experiments/smp31f-entry/test_permissions.py',
    'kernel/experiments/smp31f-entry/test_recorder_check.py',
    'kernel/experiments/smp31f-entry/test_telemetry.py',
    'kernel/experiments/usb-gadget-dt/fdtedit.py',
    'native/boot/attempt31b/validation.json',
    'native/boot/attempt31c/validation.json',
    'native/boot/attempt31d/console-binding.json',
    'native/boot/attempt31d/validation.json',
    'native/boot/cpu_observe.py',
    'native/boot/dapf_guard.py',
    'native/boot/entry_guard.py',
    'native/boot/fdt.py',
    'native/boot/gpio_guard.py',
    'native/boot/launch.py',
    'native/boot/package-manifest.json',
    'native/boot/smp31_census.py',
    'native/boot/smp31b.py',
    'native/boot/smp31c.py',
    'native/boot/smp31d.py',
    'native/boot/smp31e.py',
    'native/boot/smp31f.py',
    'native/boot/test_smp31_census.py',
    'native/boot/test_smp31b.py',
    'native/boot/test_smp31c.py',
    'native/boot/test_smp31d.py',
    'native/boot/test_smp31e.py',
    'native/boot/test_smp31f.py',
    'reverse-engineering/findings/cpu-startup-2026-10-21/validation.json',
    'tools/boot-campaign/campaign.py',
    'tools/boot-campaign/fixtures/31b-controller.json',
    'tools/boot-campaign/fixtures/31c-controller.json',
    'tools/boot-campaign/fixtures/31d-controller.json',
    'tools/boot-campaign/fixtures/sha256.json',
    'tools/boot-campaign/fixtures/synthetic-partial-entry.json',
    'tools/boot-campaign/fixtures/synthetic-success.json',
    'tools/boot-campaign/test_campaign.py',
    'tools/m1n1-client/attempt31b-supervise.py',
    'tools/m1n1-client/attempt31c-supervise.py',
    'tools/m1n1-client/attempt31d-supervise.py',
    'tools/m1n1-client/attempt31e-instructions.md',
    'tools/m1n1-client/attempt31e-offline.py',
    'tools/m1n1-client/attempt31e-supervisor.py',
    'tools/m1n1-client/attempt31f-instructions.md',
    'tools/m1n1-client/attempt31f-offline.py',
    'tools/m1n1-client/attempt31f-supervisor.py',
    'tools/m1n1-client/m1n1-revision.txt',
    'tools/m1n1-client/pin_check.py',
    'tools/m1n1-client/run.sh',
    'tools/m1n1-client/test_attempt31b_supervise.py',
    'tools/m1n1-client/test_attempt31c_supervise.py',
    'tools/m1n1-client/test_attempt31d_supervise.py',
    'tools/m1n1-client/test_attempt31e_offline.py',
    'tools/m1n1-client/test_attempt31e_supervisor.py',
    'tools/m1n1-client/test_attempt31f_offline.py',
    'tools/m1n1-client/test_attempt31f_supervisor.py',
    'tools/m1n1-client/usb_identity.py',
    'tools/m1n1-client/verify-package.py',
    'virtualization/jobs/059-smp31b/run.sh',
    'virtualization/jobs/060-smp31c/run.sh',
    'virtualization/jobs/061-smp31d/run.sh',
    'virtualization/jobs/064-smp31f/run.sh',
}

REQUIRED.update({
    'kernel/experiments/cpu-topology31g/collect.py',
    'kernel/experiments/cpu-topology31g/test_topology.py',
    'kernel/experiments/cpu-topology31g/topology.py',
    'kernel/experiments/smp31/test_client31g_vm.py',
    'kernel/experiments/smp31g-observation/fixture.py',
    'kernel/experiments/smp31g-observation/live_binding.py',
    'kernel/experiments/smp31g-observation/plan.py',
    'kernel/experiments/smp31g-observation/read32.S',
    'kernel/experiments/smp31g-observation/test_binding_vm.py',
    'kernel/experiments/smp31g-observation/test_plan.py',
    'kernel/experiments/smp31g-observation/test_read32.c',
    'kernel/experiments/smp31g-observation/test_tracker.py',
    'kernel/experiments/smp31g-observation/tracker.py',
    'kernel/experiments/smp31g-publication/audit.py',
    'kernel/experiments/smp31g-publication/test_audit.py',
    'kernel/experiments/t6050-dt/gen_t6050_dt.py',
    'native/boot/attempt31g/controller-review.md',
    'native/boot/attempt31g/controller-validation.md',
    'native/boot/attempt31g/topology-observation.json',
    'native/boot/smp31g.py',
    'native/boot/test_smp31g.py',
    'research/native31g-reset-routing.md',
    'tools/m1n1-client/attempt31g-instructions.md',
    'tools/m1n1-client/attempt31g-offline.py',
    'tools/m1n1-client/attempt31g-supervisor.py',
    'tools/m1n1-client/test_attempt31g_offline.py',
    'tools/m1n1-client/test_attempt31g_supervisor.py',
    'virtualization/jobs/065-smp31g/run.sh',
})

REQUIRED.update({
    'kernel/experiments/smp31/helper31b.S',
    'kernel/experiments/smp31/test_console31d.c',
    'kernel/experiments/smp31/test_helper31b.c',
    'kernel/experiments/smp31/test_loop31b.c',
    'kernel/experiments/smp31e-emulator/README.md',
    'kernel/experiments/smp31e-emulator/first_frame.S',
    'kernel/experiments/smp31e-emulator/test_first_frame.c',
    'kernel/experiments/smp31e-entry/.gitignore',
    'kernel/experiments/smp31e-entry/README.md',
    'kernel/experiments/smp31e-entry/audit.json',
    'kernel/experiments/smp31e-observer/README.md',
    'native/boot/README.md',
    'native/boot/attempt31b-controller-2026-10-21.json',
    'native/boot/attempt31b/validation.md',
    'native/boot/attempt31c-controller-2026-10-21.json',
    'native/boot/attempt31c/review.md',
    'native/boot/attempt31d-controller-2026-10-21.json',
    'native/boot/attempt31d/review.md',
    'native/boot/attempt31e/controller-review.md',
    'native/boot/attempt31e/publication-review.md',
    'native/boot/attempt31e/review.md',
    'native/boot/attempt31f/controller-review.md',
    'native/boot/attempt31f/entry-review.md',
    'native/boot/attempt31f/plan.md',
    'native/boot/attempt31f/startup-review.md',
    'research/testing-strategy-31e.md',
    'reverse-engineering/findings/cpu-startup-2026-10-21/README.md',
    'tools/boot-campaign/README.md',
    'tools/m1n1-client/attempt31b-instructions.md',
    'tools/m1n1-client/attempt31c-instructions.md',
    'tools/m1n1-client/attempt31d-instructions.md',
    'tools/m1n1-client/stage-b-instructions.md',
    'virtualization/jobs/062-smp31e/run.sh',
    'virtualization/jobs/063-smp31e-controller/run.sh',
})


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
    run_check('native/boot/smp31g.py', ['--image', str(args.image.absolute())])
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
        checks=rows, instruction_model=model, native_31g='NOT RUN',
        full_symbol_checks='PASS' if args.symbols is not None else 'NOT RUN: symbol file not supplied',
        cpu1_entry='UNVERIFIED', linux_smp='NOT RUN',
        restart_ready=False, next_step='M1 publishes readiness; human starts the reviewed one-shot session', hardware_operations=0), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        # Avoid publishing private input paths or subprocess output.
        print(json.dumps(dict(result='OFFLINE_REFUSED_NATIVE_HOLD',
            reason=str(exc) if type(exc) is ValueError else type(exc).__name__,
            restart_ready=False, hardware_operations=0)))
        raise SystemExit(1)
