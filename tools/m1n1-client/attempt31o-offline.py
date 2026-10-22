#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31O offline evidence and firmware-structure review. No live mode exists."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'native/boot/attempt31o/source-sha256.txt'
IMAGE_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
DATA_SHA = 'b43f7a31f6d980c6205f029dd80b2dc5ec0a2a52d7d3d801019736d9dcb5d11b'
N_MANIFEST_SHA = '00dea9b06831a0e3d57fff4d2f92103ea469c887779ae5bce661bf0e0523e70a'


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


previous = module('intake31o_frozen_n', 'tools/m1n1-client/attempt31n-offline.py')
TESTS = ('kernel/experiments/smp31o-evidence/test_evidence.py',
         'kernel/experiments/smp31o-evidence/test_rcfg.py',
         'tools/m1n1-client/test_attempt31o_offline.py')
REQUIRED = previous.REQUIRED | set(TESTS) | {
    'native/boot/attempt31n/source-sha256.txt',
    'native/boot/attempt31n/validation.json',
    'native/boot/attempt31n-2026-10-22-result.md',
    'native/boot/attempt31n-controller-2026-10-22.json',
    'native/boot/attempt31n-supervisor-2026-10-22.json',
    'kernel/experiments/smp31o-evidence/evidence.py',
    'kernel/experiments/smp31o-evidence/rcfg.py',
    'kernel/experiments/smp31o-evidence/README.md',
    'tools/m1n1-client/attempt31o-offline.py',
    'tools/m1n1-client/attempt31o-instructions.md',
    'research/native31o-controller-audit.md',
    'research/native31o-firmware.md',
    'research/native31o-upstream.md',
    'reverse-engineering/findings/cpu-startup31o/validation.json',
    'virtualization/jobs/074-smp31o/run.sh',
}


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def read_regular(path, limit):
    """Bound local input reads, reject links/devices, never echo their names."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit, 'input_size_or_type')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        need(0 < len(data) <= limit and len(data) == info.st_size, 'input_changed_or_oversize')
        return data
    finally:
        os.close(fd)


def source_pins(root=ROOT):
    data = read_regular(root / MANIFEST, 65536)
    names = set()
    for line in data.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        need(match is not None, 'manifest_syntax')
        digest, name = match.groups()
        rel = Path(name)
        need(not rel.is_absolute() and '..' not in rel.parts and
             rel.as_posix() == name and name not in names, 'manifest_path')
        path = root / rel
        need(not any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)),
             'source_symlink')
        need(hashlib.sha256(read_regular(path, 4 * 1024 * 1024)).hexdigest() == digest,
             'source_digest')
        names.add(name)
    need(names == REQUIRED, 'manifest_closure')
    n_manifest = read_regular(root / 'native/boot/attempt31n/source-sha256.txt', 65536)
    need(hashlib.sha256(n_manifest).hexdigest() == N_MANIFEST_SHA, 'frozen_n_manifest')
    return len(names), hashlib.sha256(data).hexdigest()


def run_check(name, args=()):
    result = subprocess.run([sys.executable, '-I', str(ROOT / name), *map(str, args)],
                            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                            timeout=45, check=False)
    need(result.returncode == 0, 'offline_check_failed')
    return result.stdout, result.stderr


def json_check(name, args=()):
    stdout, _ = run_check(name, args)
    value = json.loads(stdout)
    need(type(value) is dict, 'check_result_type')
    return value


def verify_firmware_summary(value):
    # The child reopens the file. Bind its own parsed bytes, not just our
    # earlier read, to the reviewed artifact; replacements must not pass.
    need(value.get('result') == 'RCfg_STRUCTURAL_PASS' and
         value.get('sha256') == DATA_SHA and value.get('size_bytes') == 459150 and
         value.get('command_count') == 22855 and value.get('named_sequence_count') == 417 and
         value.get('evaluated_conditions') is False and
         value.get('firmware_emulator') is False and
         type(value.get('native_operations')) is int and value['native_operations'] == 0,
         'firmware_summary_not_matching_input')


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments')


def main():
    parser = Parser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path)
    parser.add_argument('--ibootdata', type=Path)
    args = parser.parse_args()
    pins = source_pins()
    image_bytes = read_regular(args.image, 4 * 1024 * 1024)
    need(hashlib.sha256(image_bytes).hexdigest() == IMAGE_SHA, 'image_digest')
    checks, methods = [], 0
    for name in TESTS:
        stdout, stderr = run_check(name)
        output = stdout + stderr
        match = re.search(rb'Ran ([0-9]+) tests? in ', output)
        need(match is not None and b'skipped=' not in output, 'test_count_or_skip')
        count = int(match[1]); need(count > 0, 'empty_suite')
        methods += count
        checks.append(dict(check=name, methods=count, result='PASS'))
    evidence = {}
    for attempt in ('m', 'n'):
        report = ROOT / f'native/boot/attempt31{attempt}-controller-2026-10-22.json'
        evidence[attempt] = json_check('kernel/experiments/smp31o-evidence/evidence.py',
                                      ['--report', report])
        need(evidence[attempt].get('classification') == 'NATURAL_TIMEOUT_WITHOUT_VISIBLE_ENTRY' and
             evidence[attempt].get('cpu1_execution') == 'UNVERIFIED' and
             evidence[attempt].get('hardware_operations') == 0,
             'consumed_evidence_contract')
    audit_args = ['--image', args.image.absolute()]
    symbols_bytes = None
    if args.symbols is not None:
        symbols_bytes = read_regular(args.symbols, 256 * 1024)
        audit_args += ['--symbols', args.symbols.absolute()]
    # Use the old tool for its exact image contract, never pass it a newer
    # report pretending to have its accepted historical 31K schema.
    contract = json_check('kernel/experiments/smp31l-analysis/entry_contract.py', audit_args)
    need(contract.get('result') == 'OFFLINE_ENTRY_CONTRACT_PASS' and
         contract.get('hardware_emulator') is False, 'entry_contract')
    candidate = module('prefix_audit31o', 'kernel/experiments/smp31l-candidate/audit.py').audit(
        image_bytes, symbols_bytes)
    need(candidate.get('result') == 'STATIC_NORMAL_PREFIX_AUDIT_PASS', 'normal_prefix_audit')
    data_summary = dict(result='NOT RUN', reason='optional_private_input_not_supplied')
    if args.ibootdata is not None:
        need(hashlib.sha256(read_regular(args.ibootdata, 8 * 1024 * 1024)).hexdigest() == DATA_SHA,
             'ibootdata_digest')
        data_summary = json_check('kernel/experiments/smp31o-evidence/rcfg.py',
                                  ['--input', args.ibootdata.absolute()])
        verify_firmware_summary(data_summary)
    need(source_pins() == pins, 'sources_changed_during_review')
    print(json.dumps(dict(schema=1, result='OFFLINE_REVIEW_PASS_NATIVE_HOLD',
        source_pins=pins[0], source_manifest_sha256=pins[1], unit_test_methods=methods,
        checks=checks, consumed_evidence=evidence, entry_contract=contract,
        normal_prefix_audit=candidate, firmware_structure=data_summary,
        cpu1_execution='UNVERIFIED', native31o='HOLD / NOT RUN', linux_smp='NOT RUN',
        restart_ready=False, hardware_operations=0, firmware_emulator=False,
        next_step='Review firmware prerequisite evidence; no automatic physical attempt'),
        indent=2, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        reason = str(exc) if type(exc) is ValueError and str(exc).isidentifier() else type(exc).__name__
        print(json.dumps(dict(result='OFFLINE_REFUSED_NATIVE_HOLD', reason=reason,
                              restart_ready=False, hardware_operations=0)))
        raise SystemExit(1)
