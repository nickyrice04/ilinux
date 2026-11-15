#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the full read-only phase helper with the qualified 31AO policy state.

No helper mode is dispatched here. Recovery admission and every transaction
write remain separate from compilation. Use a fresh workspace build directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INVENTORIES = {
    'native/boot/attempt31ap/source-sha256.txt':
        '1e10cb95acab08adc127a84425c459745681d6c126a441523ec58e630618edf4',
    'native/boot/attempt31ap-source-page/source-sha256.txt':
        '62fad9235d127f9b436699976373bf250aae742c0be82def17291eceb523c378',
}
GENERATOR = 'tools/boot-object31ao-native/generate.py'
FROZEN_NAMES = tuple('tools/boot-object31aj-native/' + name for name in
    ('core.c', 'json.c', 'reader.h', 'state.c', 'main.c')) + (
    GENERATOR, 'tools/boot-object31ao-native/extra_policy.c',
    'tools/boot-object31ao-native/extra_policy.h')
CANDIDATE = {
    'schema': 'ilinux31aj-compiled-candidate-v1',
    'target': {'model': 'Mac17,6', 'board': 'j716c', 'chip_id': '0x6050'},
    'bytes': 153190400,
    'sha256': '1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01',
    'publication_authorizes_writes': False,
}


def require(value):
    if not value:
        raise ValueError('31AQ build refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_source(name, limit=8 * 1024 * 1024):
    path = Path(name)
    require(not path.is_absolute() and bool(path.parts) and
            all(part not in ('.', '..') for part in path.parts))
    descriptor = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for index, part in enumerate(path.parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if index + 1 < len(path.parts):
                flags |= os.O_DIRECTORY
            following = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        data = bytearray()
        while len(data) <= limit:
            piece = os.read(descriptor, min(65536, limit + 1 - len(data)))
            if not piece:
                break
            data.extend(piece)
        after = os.fstat(descriptor)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(len(data) == before.st_size and len(data) <= limit and
                all(getattr(before, key) == getattr(after, key) for key in fields))
        return bytes(data)
    finally:
        os.close(descriptor)


def retained_sources():
    records = {}
    for (name, expected), count in zip(INVENTORIES.items(), (140, 3)):
        raw = read_source(name, 256 * 1024)
        require(sha(raw) == expected)
        lines = raw.decode('ascii').splitlines()
        require(len(lines) == count)
        for line in lines:
            match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
            require(match is not None)
            digest, source = match.groups()
            require(source not in records)
            records[source] = digest
    require(len(records) == 143)
    contents = {name: read_source(name) for name in records}
    require(all(sha(contents[name]) == digest for name, digest in records.items()))
    return records, contents


def pairs(items):
    value = {}
    for key, item in items:
        require(key not in value)
        value[key] = item
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(argv)
    output = args.output.absolute()
    require(ROOT / 'build' in output.parents and '..' not in output.parts and
            not output.exists() and not any(parent.is_symlink() for parent in output.parents))
    records, contents = retained_sources()
    definition = json.loads(contents['tools/boot-object31aj-native/candidate-definition.json'],
                            object_pairs_hook=pairs)
    require(definition == CANDIDATE and type(definition['bytes']) is int and
            definition['publication_authorizes_writes'] is False)
    own_inputs = {'build.py': sha(read_source('tools/boot-object31aq-native/build.py'))}
    generator = types.ModuleType('verified31ao_generator_for31aq')
    generator.__file__ = str(ROOT / GENERATOR)
    exec(compile(contents[GENERATOR], generator.__file__, 'exec'), generator.__dict__)
    output.mkdir(parents=True, mode=0o700)
    source = output / 'sources'
    extension = generator.generate(source)
    observed = (source / 'state.c').read_text()
    old_state = generator.frozen_generator().strip(generator.reverse(observed))
    require(old_state.encode() == contents['tools/boot-object31aj-native/state.c'])
    pure = generator.frozen_generator().strip(observed)
    require('/*31AL+' not in pure and 'D_TEST(' not in pure and
            'D_FALSE(' not in pure and 'diagnostic_' not in pure)
    (source / 'state.observed.c').write_text(observed)
    (source / 'state.c').write_text(pure)
    for name in ('core.c', 'json.c', 'reader.h', 'main.c'):
        original = contents['tools/boot-object31aj-native/' + name]
        (source / name).write_bytes(original)
        require((source / name).read_bytes() == original)
    for name in ('extra_policy.c', 'extra_policy.h'):
        original = contents['tools/boot-object31ao-native/' + name]
        (source / name).write_bytes(original)
    proof = dict(extension, original_full_cli_byte_identical=True,
                 core_json_reader_byte_identical=True,
                 diagnostic_marks_stripped=True, qualified_state_matches_31ao=True,
                 observed_state_sha256=sha(observed.encode()),
                 compiled_state_sha256=sha(pure.encode()))
    binary = output / 'ilinux31aj-reader'
    command = ['/usr/bin/xcrun', 'clang', '-std=c11', '-O2', '-Wall', '-Wextra',
        '-Werror', '-Wno-deprecated-declarations', '-arch', 'arm64',
        '-mmacosx-version-min=13.0', '-DWORKSPACE_ROOT=' + json.dumps(str(ROOT)),
        '-DCANDIDATE_BYTES=' + str(CANDIDATE['bytes']),
        '-DCANDIDATE_SHA256=' + json.dumps(CANDIDATE['sha256'])]
    if args.sanitize:
        command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    command += [str(source / name) for name in ('core.c', 'json.c', 'state.c', 'extra_policy.c', 'main.c')]
    command += ['-framework', 'CoreFoundation', '-lcompression', '-o', str(binary)]
    subprocess.run(command, cwd=ROOT, timeout=60, check=True)
    compiler = subprocess.run(['/usr/bin/xcrun', 'clang', '--version'], capture_output=True,
                              text=True, check=True, timeout=15).stdout.splitlines()[0]
    sdk = subprocess.run(['/usr/bin/xcrun', '--show-sdk-version'], capture_output=True,
                         text=True, check=True, timeout=15).stdout.strip()
    require(0 < len(compiler) <= 256 and compiler.isascii() and
            re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', sdk))
    require(own_inputs == {'build.py': sha(read_source('tools/boot-object31aq-native/build.py'))})
    require(retained_sources()[0] == records)
    receipt = {
        'schema': 'ilinux31aq-native-build-v1', 'source_inputs': own_inputs,
        'source_inventories': INVENTORIES, 'retained_source_pins': records,
        'frozen_inputs': {name: records[name] for name in FROZEN_NAMES},
        'guard_preservation': proof, 'candidate_definition': CANDIDATE,
        'binary_bytes': binary.stat().st_size, 'binary_sha256': sha(binary.read_bytes()),
        'system_sdk_only': True, 'compiler_version': compiler, 'sdk_version': sdk,
        'abi': 'arm64', 'minimum_macos': '13.0', 'sanitized': args.sanitize,
        'live_run': False, 'recovery_run': False, 'host_changes': False, 'native_ready': False,
        'helper_dispatch': 'ORIGINAL_FULL_READ_ONLY_TRANSACTION_PHASE_CLI',
        'boot_or_policy_write_api_added': False,
    }
    (output / 'build-result.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print('{"status":"FULL_READ_ONLY_PHASE_HELPER_COMPILED","live_run":false,"native_ready":false}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError):
        print('{"status":"REFUSED","live_run":false,"native_ready":false}')
        raise SystemExit(2)
