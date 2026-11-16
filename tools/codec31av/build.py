#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build only the original, inert-by-default workspace codec differential."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PINS = {
    'core.c': '2e9882eae113e24ba2023fa2843fe8447f3da4ec7e022591d5ca46d987bfcdd8',
    'reader.h': 'bfa3bfe2af667e4b54db1913c80a35d9da4e343cddbc182464d08be674fcbf99',
}
CANDIDATE = (153190400, '1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01')


def build(output, sanitize=False):
    output = Path(output).absolute()
    if (not str(output).startswith(str(ROOT / 'build') + '/') or output.exists()
            or any(p.is_symlink() for p in output.parents)
            or any(p in ('', '.', '..') for p in str(output).split('/')[1:])):
        raise ValueError('new workspace build output required')
    source = {name: (ROOT / 'tools/boot-object31aj-native' / name).read_bytes() for name in PINS}
    if any(hashlib.sha256(data).hexdigest() != PINS[name] for name, data in source.items()):
        raise ValueError('frozen source changed')
    source['probe.c'] = (HERE / 'probe.c').read_bytes()
    source['buffer_proposal.c'] = (HERE / 'buffer_proposal.c').read_bytes()
    output.mkdir(mode=0o700, parents=True)
    directory = output / 'source'
    directory.mkdir(mode=0o700)
    for name, data in source.items():
        (directory / name).write_bytes(data)
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-deprecated-declarations',
             '-arch', 'arm64', '-mmacosx-version-min=13.0',
             '-DWORKSPACE_ROOT=' + json.dumps(str(ROOT)),
             '-DCANDIDATE_BYTES=' + str(CANDIDATE[0]), '-DCANDIDATE_SHA256=' + json.dumps(CANDIDATE[1])]
    if sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    binary = output / 'codec31av'
    subprocess.run(['/usr/bin/xcrun', 'clang', *flags, '-I', str(directory),
                    str(directory / 'probe.c'), '-framework', 'CoreFoundation',
                    '-lcompression', '-o', str(binary)], check=True, capture_output=True, timeout=40)
    receipt = {'schema': 'ilinux31av-own-codec-build-v1', 'sanitized': sanitize,
               'source_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in source.items()},
               'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
               'system_sdk_only': True, 'native_ready': False, 'controller_integrated': False}
    (output / 'build-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return binary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    try:
        build(args.output, args.sanitize)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Compiler output stays local; no data/policy inspection occurs.
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr.decode(errors='replace'))
        raise
    print('{"status":"BUILT","native_ready":false,"controller_integrated":false}')
