#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the read-only Recovery companion from frozen engine and 31AO schema.

Compilation never dispatches the helper, queries policy, mounts a filesystem or
changes a boot object. Default argparse help is inert. Use a new build directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INVENTORIES = {
    'native/boot/attempt31am/source-sha256.txt':
        '0d080629d2cb8ae35d347431cc754ab8bd45807f8a83f17b26b03e8c78b65231',
    'native/boot/attempt31ao/source-sha256.txt':
        'bb3d962e80bbe4c265f9a5d0557f77df61a3d09648ebd48d296284aa9bda91d6',
}
FROZEN_NAMES = (
    'tools/boot-object31al-native/diagnostic.c',
    'tools/boot-object31al-native/diagnostic.h',
    'tools/boot-object31am-native/preboot.c',
    'tools/boot-object31am-native/preboot.h',
    'tools/boot-object31am-native/main.c',
    'tools/boot-object31am-native/result.c',
    'tools/boot-object31ao-native/generate.py',
    'tools/boot-object31ao-native/extra_policy.c',
    'tools/boot-object31ao-native/extra_policy.h',
)
GENERATOR = 'tools/boot-object31ao-native/generate.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition):
    if not condition:
        raise ValueError('31AP build refused')


def read_source(name, limit=8 * 1024 * 1024):
    parts = Path(name).parts
    require(not Path(name).is_absolute() and bool(parts) and
            all(part not in ('.', '..') for part in parts))
    path = ROOT / name
    require(not any(parent.is_symlink() for parent in path.parents) and not path.is_symlink())
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        require(0 < info.st_size <= limit)
        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(descriptor, min(65536, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(descriptor)
        require(len(data) == info.st_size and len(data) <= limit and
                (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns))
        return bytes(data)
    finally:
        os.close(descriptor)


def retained_sources():
    records = {}
    expected_counts = (111, 14)
    for (inventory, expected), count in zip(INVENTORIES.items(), expected_counts):
        raw = read_source(inventory, 256 * 1024)
        require(sha(raw) == expected)
        lines = raw.decode('ascii').splitlines()
        require(len(lines) == count)
        for line in lines:
            match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
            require(match is not None)
            digest, name = match.groups()
            require(name not in records)
            records[name] = digest
    require(len(records) == 125)
    contents = {name: read_source(name) for name in records}
    require(all(sha(contents[name]) == expected for name, expected in records.items()))
    return records, contents


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result)
        result[key] = value
    return result


def definition(path):
    absolute = path.absolute()
    require('..' not in absolute.parts and
            (ROOT / 'build' in absolute.parents or
             absolute == ROOT / 'tools/boot-object31aj-native/candidate-definition.json'))
    raw = read_source(str(absolute.relative_to(ROOT)), 16384)
    value = json.loads(raw, object_pairs_hook=pairs)
    require(type(value) is dict and set(value) ==
            {'schema', 'target', 'bytes', 'sha256', 'publication_authorizes_writes'})
    require(value['schema'] == 'ilinux31aj-compiled-candidate-v1' and
            value['target'] == {'model': 'Mac17,6', 'board': 'j716c', 'chip_id': '0x6050'} and
            value['publication_authorizes_writes'] is False)
    require(type(value['bytes']) is int and 0 < value['bytes'] <= 160 * 1024 * 1024 and
            type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']))
    return raw, value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate-definition', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(argv)
    output = args.output.absolute()
    require(ROOT / 'build' in output.parents and not output.exists() and
            '..' not in output.parts and not any(parent.is_symlink() for parent in output.parents))
    definition_bytes, candidate = definition(args.candidate_definition)
    records, contents = retained_sources()
    own_inputs = {'build.py': sha(read_source('tools/boot-object31ap-native/build.py'))}
    generator = types.ModuleType('verified31ao_generator_for31ap')
    generator.__file__ = str(ROOT / GENERATOR)
    exec(compile(contents[GENERATOR], generator.__file__, 'exec'), generator.__dict__)
    output.mkdir(parents=True, mode=0o700)
    source = output / 'sources'
    extension_proof = generator.generate(source)
    for name in FROZEN_NAMES:
        if name == GENERATOR:
            continue
        (source / Path(name).name).write_bytes(contents[name])
    frozen_state = generator.reverse((source / 'state.c').read_text())
    require(generator.frozen_generator().strip(frozen_state).encode() ==
            contents['tools/boot-object31aj-native/state.c'])
    for name in FROZEN_NAMES:
        if name != GENERATOR:
            require((source / Path(name).name).read_bytes() == contents[name])
    for name in ('core.c', 'json.c', 'reader.h'):
        require((source / name).read_bytes() == contents['tools/boot-object31aj-native/' + name])
    proof = dict(extension_proof, preboot_engine_byte_identical=True,
                 cli_result_byte_identical=True, diagnostic_support_byte_identical=True)
    binary = output / 'ilinux31aj-reader'
    command = ['/usr/bin/xcrun', 'clang', '-std=c11', '-O2', '-Wall', '-Wextra',
        '-Werror', '-Wno-deprecated-declarations', '-arch', 'arm64',
        '-mmacosx-version-min=13.0', '-DWORKSPACE_ROOT=' + json.dumps(str(ROOT)),
        '-DCANDIDATE_BYTES=' + str(candidate['bytes']),
        '-DCANDIDATE_SHA256=' + json.dumps(candidate['sha256'])]
    if args.sanitize:
        command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    command += [str(source / name) for name in
                ('core.c', 'json.c', 'preboot.c', 'extra_policy.c', 'result.c', 'main.c')]
    command += ['-framework', 'CoreFoundation', '-lcompression', '-o', str(binary)]
    subprocess.run(command, cwd=ROOT, timeout=60, check=True)
    compiler = subprocess.run(['/usr/bin/xcrun', 'clang', '--version'], capture_output=True,
                              text=True, check=True, timeout=15).stdout.splitlines()[0]
    sdk = subprocess.run(['/usr/bin/xcrun', '--show-sdk-version'], capture_output=True,
                         text=True, check=True, timeout=15).stdout.strip()
    require(0 < len(compiler) <= 256 and compiler.isascii() and
            re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', sdk))
    require(own_inputs == {'build.py': sha(read_source('tools/boot-object31ap-native/build.py'))})
    require(definition(args.candidate_definition)[0] == definition_bytes)
    require(retained_sources()[0] == records)
    receipt = {
        'schema': 'ilinux31ap-native-build-v1', 'source_inputs': own_inputs,
        'source_inventories': INVENTORIES,
        'retained_source_pins': records,
        'frozen_inputs': {name: records[name] for name in FROZEN_NAMES},
        'guard_preservation': proof, 'candidate_definition': candidate,
        'binary_bytes': binary.stat().st_size, 'binary_sha256': sha(binary.read_bytes()),
        'system_sdk_only': True, 'compiler_version': compiler, 'sdk_version': sdk,
        'abi': 'arm64', 'minimum_macos': '13.0', 'sanitized': args.sanitize,
        'live_run': False, 'recovery_run': False, 'host_changes': False, 'native_ready': False,
    }
    (output / 'build-result.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print('{"status":"READ_ONLY_POLICY_COMPANION_COMPILED","live_run":false,"native_ready":false}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError):
        print('{"status":"REFUSED","live_run":false,"native_ready":false}')
        raise SystemExit(2)
