#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""31P original CPU/GPU offline checks. No native mode or hardware interface."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'native/boot/attempt31p/source-sha256.txt'
ADT_SHA = '6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af'


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prior = load('offline31p_prior', 'tools/m1n1-client/attempt31o-offline.py')
NEW_FILES = {
    # Frozen 31O invokes this original checker but omitted it from its closure.
    'kernel/experiments/smp31l-analysis/entry_contract.py',
    'native/boot/attempt31o/source-sha256.txt',
    'native/boot/attempt31o/validation.json',
    'hardware/adt/adt-sanitized.json',
    'kernel/experiments/gpu31p/contract.py',
    'kernel/experiments/gpu31p/test_contract.py',
    'kernel/experiments/gpu31p/segments.c',
    'kernel/experiments/gpu31p/segments.h',
    'kernel/experiments/gpu31p/test_segments.c',
    'kernel/experiments/gpu31p/README.md',
    'kernel/experiments/gpu31p/adt-validation.json',
    'research/native31p-firmware.md',
    'research/native31p-gpu-contract.md',
    'research/native31p-gpu-build.md',
    'research/native31p-environment.md',
    'reverse-engineering/findings/cpu-startup31p/validation.json',
    'tools/m1n1-client/attempt31p-offline.py',
    'tools/m1n1-client/test_attempt31p_offline.py',
    'tools/m1n1-client/attempt31p-instructions.md',
    'virtualization/jobs/075-gpu31p/run.sh',
    'virtualization/jobs/075-gpu31p/kernel.sh',
    'virtualization/jobs/075-gpu31p/verify-inputs.py',
    'virtualization/jobs/075-gpu31p/package-space.py',
    'virtualization/jobs/075-gpu31p/test_package_space.py',
    'virtualization/jobs/075-gpu31p/isolate-toolchain.py',
    'virtualization/jobs/075-gpu31p/llvm-config-relocated.py',
    'virtualization/jobs/075-gpu31p/test_isolation.py',
    'virtualization/jobs/075-gpu31p/README.md',
    'virtualization/jobs/075-gpu31p/sources.json',
    'virtualization/jobs/075-gpu31p/packages.json',
    'virtualization/jobs/075-gpu31p/validation.json',
    'virtualization/jobs/076-offline31p/run.sh',
}
REQUIRED = prior.REQUIRED | NEW_FILES
need = prior.need


def source_pins(root=ROOT):
    data = prior.read_regular(root / MANIFEST, 131072)
    names = set()
    for line in data.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        need(match is not None, 'manifest_syntax')
        digest, name = match.groups()
        rel = Path(name)
        need(not rel.is_absolute() and '..' not in rel.parts and
             rel.as_posix() == name and name not in names, 'manifest_path')
        path = root / rel
        need(not any(p.is_symlink() for p in (path, *path.parents)
                     if p.is_relative_to(root)), 'source_symlink')
        need(hashlib.sha256(prior.read_regular(path, 4 * 1024 * 1024)).hexdigest()
             == digest, 'source_digest')
        names.add(name)
    need(names == REQUIRED, 'manifest_closure')
    return len(names), hashlib.sha256(data).hexdigest()


def run(args, timeout=120):
    result = subprocess.run(list(map(str, args)), cwd=ROOT,
                            stdin=subprocess.DEVNULL, capture_output=True,
                            timeout=timeout, check=False)
    need(result.returncode == 0, 'offline_check_failed')
    return result.stdout, result.stderr


def json_run(relative, args=()):
    stdout, _ = run([sys.executable, '-I', ROOT / relative, *args])
    result = json.loads(stdout)
    need(type(result) is dict, 'check_result_type')
    return result


def suite(relative):
    stdout, stderr = run([sys.executable, '-I', ROOT / relative])
    output = stdout + stderr
    count = re.search(rb'Ran ([0-9]+) tests? in ', output)
    need(count is not None and b'skipped=' not in output, 'test_count_or_skip')
    need(int(count[1]) > 0, 'empty_suite')
    return dict(check=relative, methods=int(count[1]), result='PASS')


def compile_codec(compiler):
    # Only our original, pinned C files are compiled/executed on the host.
    build_root = ROOT / 'build/offline31p/intake'
    build_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='codec-', dir=build_root) as directory:
        executable = Path(directory) / 'segments-test'
        run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
             '-O2', ROOT / 'kernel/experiments/gpu31p/segments.c',
             ROOT / 'kernel/experiments/gpu31p/test_segments.c', '-o', executable])
        stdout, _ = run([executable], timeout=10)
        # The exact success token is bound to the source and its assertion suite.
        need(stdout.strip() == b'GPU31P_SEGMENTS_PASS', 'codec_test_token')
    return dict(result='PASS', language='C11', optimization='O2',
                sanitizers='NOT RUN by this portable intake', hardware_operations=0)


def verify_gpu_summary(value):
    need(type(value) is dict and value.get('schema') == 'ilinux-gpu31p-contract-v1'
         and value.get('status') == 'STRUCTURAL_PASS'
         and value.get('sanitized_adt_sha256') == ADT_SHA
         and value.get('native_validation') == 'NOT_RUN'
         and value.get('gpu_enablement') == 'HOLD'
         and value.get('descriptor_cpu_address_domain') == 'UNQUALIFIED'
         and value.get('uat_layout') == 'UNKNOWN'
         and value.get('firmware_abi') == 'UNKNOWN', 'gpu_summary_contract')
    for key in ('hardware_operations', 'cpu_memory_reservations_generated',
                'mmio_writes_generated'):
        need(type(value.get(key)) is int and value[key] == 0,
             'gpu_summary_native_operation')
    need(type(value.get('role_count')) is int and value['role_count'] == 2,
         'gpu_summary_roles')


def main():
    parser = prior.Parser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--cc')
    args = parser.parse_args()
    pins = source_pins()
    compiler = args.cc or shutil.which('cc')
    need(bool(compiler), 'c_compiler_missing')
    previous = json_run('tools/m1n1-client/attempt31o-offline.py',
                        ['--image', args.image.absolute()])
    need(previous.get('result') == 'OFFLINE_REVIEW_PASS_NATIVE_HOLD' and
         previous.get('restart_ready') is False and
         type(previous.get('hardware_operations')) is int and
         previous['hardware_operations'] == 0, 'prior_review_contract')
    checks = [suite('kernel/experiments/gpu31p/test_contract.py'),
              suite('virtualization/jobs/075-gpu31p/test_package_space.py'),
              suite('virtualization/jobs/075-gpu31p/test_isolation.py'),
              suite('tools/m1n1-client/test_attempt31p_offline.py')]
    codec = compile_codec(compiler)
    topology = json_run('kernel/experiments/gpu31p/contract.py',
                        ['--adt', ROOT / 'hardware/adt/adt-sanitized.json'])
    verify_gpu_summary(topology)
    need(source_pins() == pins, 'sources_changed_during_review')
    print(json.dumps(dict(schema=1, result='OFFLINE_PASS_NATIVE_HOLD',
        source_pins=pins[0], source_manifest_sha256=pins[1], checks=checks,
        previous_python_methods=previous['unit_test_methods'],
        new_python_methods=sum(check['methods'] for check in checks),
        original_c_codec=codec, gpu_contract=topology,
        cpu1_execution='UNVERIFIED', native31p='HOLD / NOT RUN',
        gpu_native_acceleration='NOT RUN', restart_ready=False,
        hardware_operations=0, private_rea_reproduced='NOT RUN on M1',
        upstream_build_reproduced='NOT RUN by this intake'),
        indent=2, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        reason = str(error) if type(error) is ValueError and str(error).isidentifier() else type(error).__name__
        print(json.dumps(dict(result='OFFLINE_REFUSED_NATIVE_HOLD', reason=reason,
                              restart_ready=False, hardware_operations=0)))
        raise SystemExit(1)
