#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the original fixture adapter with the installed SDK; never run it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PINNED = {
    'core.c': '2e9882eae113e24ba2023fa2843fe8447f3da4ec7e022591d5ca46d987bfcdd8',
    'reader.h': 'bfa3bfe2af667e4b54db1913c80a35d9da4e343cddbc182464d08be674fcbf99',
}
REAL_CANDIDATE = (153190400, '1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01')


def build(output, sanitize=False, candidate=REAL_CANDIDATE, oracle=None):
    output = Path(output).absolute()
    if (not str(output).startswith(str(ROOT / 'build') + '/') or output.exists() or
            any(p.is_symlink() for p in output.parents) or
            any(p in ('', '.', '..') for p in str(output).split('/')[1:])):
        raise ValueError('new workspace build output required')
    size, digest = candidate
    if type(size) is not int or not 0 < size <= 160 * 1024 * 1024 or not re.fullmatch(r'[a-f0-9]{64}', digest):
        raise ValueError('candidate definition refused')
    inputs = {name: (ROOT / 'tools/boot-object31aj-native' / name).read_bytes()
              for name in PINNED}
    if any(hashlib.sha256(inputs[name]).hexdigest() != digest for name, digest in PINNED.items()):
        raise ValueError('frozen core source pin differs')
    own = {name: (HERE / name).read_bytes() for name in ('diagnostics.c', 'diagnostics.h', 'fixture.c')}
    output.mkdir(parents=True, mode=0o700)
    source = output / 'sources'
    source.mkdir(mode=0o700)
    for name, data in {**inputs, **own}.items():
        (source / name).write_bytes(data)
    binary = output / 'object31at-diagnostics'
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-deprecated-declarations',
             '-arch', 'arm64', '-mmacosx-version-min=13.0',
             '-DWORKSPACE_ROOT=' + json.dumps(str(ROOT)), '-DCANDIDATE_BYTES=' + str(size),
             '-DCANDIDATE_SHA256=' + json.dumps(digest)]
    if sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    command = ['/usr/bin/xcrun', 'clang', *flags, '-I', str(source),
               str(source / 'diagnostics.c'), str(source / 'fixture.c'),
               '-framework', 'CoreFoundation', '-lcompression', '-o', str(binary)]
    subprocess.run(command, check=True, capture_output=True, timeout=30, cwd=ROOT)
    if oracle is not None:
        # Own fixture-only differential harness; the original core is compiled
        # separately here without the diagnostics adapter translation unit.
        (source / 'oracle.c').write_bytes(oracle)
        subprocess.run(['/usr/bin/xcrun', 'clang', *flags, '-I', str(source),
                        str(source / 'core.c'), str(source / 'oracle.c'),
                        '-framework', 'CoreFoundation', '-lcompression',
                        '-o', str(output / 'original-oracle')],
                       check=True, capture_output=True, timeout=30, cwd=ROOT)
    if any((ROOT / 'tools/boot-object31aj-native' / name).read_bytes() != data for name, data in inputs.items()):
        raise ValueError('frozen source changed during build')
    receipt = {
        'schema': 'ilinux31at-object-diagnostics-build-v1', 'original_source_sha256': PINNED,
        'own_source_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in own.items()},
        'candidate_bytes': size, 'candidate_sha256': digest,
        'synthetic_candidate_definition': candidate != REAL_CANDIDATE,
        'sanitized': sanitize, 'system_sdk_only': True, 'native_ready': False,
        'host_queries': False, 'controller_integrated': False,
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
    }
    (output / 'build-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return binary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(argv)
    try:
        build(args.output, args.sanitize)
    except (OSError, ValueError, subprocess.SubprocessError):
        print('{"status":"REFUSED","native_ready":false}')
        return 2
    print('{"status":"ORIGINAL_ADAPTER_COMPILED","native_ready":false,"controller_integrated":false}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
