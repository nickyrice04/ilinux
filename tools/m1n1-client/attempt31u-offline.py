#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""31U Raw/XNU CPU handoff research and GPU receive-ring checks. No discovery, live mode or target operation."""
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
MANIFEST = 'native/boot/attempt31u/source-sha256.txt'
spec = importlib.util.spec_from_file_location('offline31u_prior',
    ROOT / 'tools/m1n1-client/attempt31t-offline.py')
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
need = prior.need
NEW_FILES = {
    'native/boot/attempt31t/source-sha256.txt',
    'native/boot/attempt31t/validation.json',
    'native/boot/attempt31t-m1-offline-2026-10-23.json',
    'native/boot/attempt31t-m1-offline-2026-10-23.md',
    'kernel/experiments/gpu31u/ring.c',
    'kernel/experiments/gpu31u/ring.h',
    'kernel/experiments/gpu31u/test_ring.c',
    'kernel/experiments/gpu31u/README.md',
    'research/native31u-firmware.md',
    'research/native31u-gpu-firmware.md',
    'research/native31u-upstream.md',
    'reverse-engineering/findings/cpu-startup31u/validation.json',
    'reverse-engineering/findings/gpu31u/validation.json',
    'tools/m1n1-client/attempt31u-offline.py',
    'tools/m1n1-client/test_attempt31u_offline.py',
    'tools/m1n1-client/attempt31u-instructions.md',
    'virtualization/jobs/081-offline31u/run.sh',
}
REQUIRED = prior.REQUIRED | NEW_FILES


def source_pins(root=ROOT):
    data = prior.prior.prior.prior.prior.prior.read_regular(root / MANIFEST, 131072)
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
        need(hashlib.sha256(prior.prior.prior.prior.prior.prior.read_regular(path, 4 * 1024 * 1024)).hexdigest()
             == digest, 'source_digest')
        names.add(name)
    need(names == REQUIRED, 'manifest_closure')
    return len(names), hashlib.sha256(data).hexdigest()


def run(args, timeout=120):
    result = subprocess.run(list(map(str, args)), cwd=ROOT,
        stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, check=False)
    need(result.returncode == 0, 'offline_check_failed')
    return result.stdout, result.stderr


def suite(relative):
    stdout, stderr = run([sys.executable, '-I', ROOT / relative])
    output = stdout + stderr
    match = re.search(rb'Ran ([0-9]+) tests? in ', output)
    need(match is not None and int(match[1]) > 0 and b'skipped=' not in output,
         'test_count_or_skip')
    return {'check': relative, 'methods': int(match[1]), 'result': 'PASS'}


def check_previous(value):
    need(type(value) is dict and value.get('result') == 'OFFLINE_PASS_NATIVE_HOLD'
         and value.get('restart_ready') is False
         and value.get('native31t') == 'HOLD / NOT RUN'
         and value.get('gpu_native_acceleration') == 'NOT RUN'
         and value.get('cpu1_execution') == 'UNVERIFIED', 'prior_review_contract')
    need(type(value.get('hardware_operations')) is int and
         value['hardware_operations'] == 0, 'prior_operations')
    for field in ('previous_python_methods', 'new_python_methods'):
        need(type(value.get(field)) is int and value[field] > 0, 'prior_test_count')
    components = value.get('c_components')
    need(type(components) is list and len(components) == 1 and
         {x.get('component') for x in components if type(x) is dict} == {'leases'} and
         all(type(x) is dict and x.get('result') == 'PASS' for x in components), 'prior_codec')


def compile_component(name, compiler):
    need(name == 'ring', 'component_name')
    build = ROOT / 'build/offline31u/intake'
    build.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=name + '-', dir=build) as directory:
        exe = Path(directory) / 'test'
        source = ROOT / 'kernel/experiments/gpu31u'
        run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
             '-O2', source / (name + '.c'), source / ('test_' + name + '.c'),
             '-o', exe])
        stdout, _ = run([exe], timeout=10)
        need(stdout.strip() == ('GPU31U_' + name.upper() + '_PASS').encode('ascii'),
             'c_test_token')
    return {'component': name, 'result': 'PASS', 'language': 'C11',
            'optimization': 'O2', 'hardware_operations': 0}


def main():
    parser = prior.prior.prior.prior.prior.prior.Parser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--cc')
    args = parser.parse_args()
    pins = source_pins()
    compiler = args.cc or shutil.which('cc')
    need(bool(compiler), 'c_compiler_missing')
    stdout, _ = run([sys.executable, '-I', ROOT / 'tools/m1n1-client/attempt31t-offline.py',
                    '--image', args.image.absolute(), '--cc', compiler])
    previous = json.loads(stdout)
    check_previous(previous)
    checks = [suite('tools/m1n1-client/test_attempt31u_offline.py')]
    c_checks = [compile_component(name, compiler) for name in ('ring',)]
    need(source_pins() == pins, 'sources_changed_during_review')
    print(json.dumps({'schema': 1, 'result': 'OFFLINE_PASS_NATIVE_HOLD',
        'source_pins': pins[0], 'source_manifest_sha256': pins[1], 'checks': checks,
        'previous_python_methods': previous['previous_python_methods'] + previous['new_python_methods'],
        'new_python_methods': sum(c['methods'] for c in checks), 'c_components': c_checks,
        'previous_c_groups': 88, 'new_c_groups': 7, 'linux_sanitizers': 'NOT RUN by portable intake',
        'cpu1_execution': 'UNVERIFIED', 'native31u': 'HOLD / NOT RUN',
        'gpu_native_acceleration': 'NOT RUN', 'descriptor_cpu_address_domain': 'UNQUALIFIED',
        'g17c_uat_layout': 'UNKNOWN', 'hardware_operations': 0, 'restart_ready': False,
        'firmware_abi': 'UNKNOWN', 'endpoint_role_mapping': 'UNQUALIFIED',
        'private_rea_reproduced': 'NOT RUN by this intake',
        'upstream_build_reproduced': 'NOT RUN by this intake'}, indent=2, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        reason = str(error) if type(error) is ValueError and str(error).isidentifier() else type(error).__name__
        print(json.dumps({'result': 'OFFLINE_REFUSED_NATIVE_HOLD', 'reason': reason,
                          'restart_ready': False, 'hardware_operations': 0}))
        raise SystemExit(1)
