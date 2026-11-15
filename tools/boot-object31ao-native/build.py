#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a pure syntax checker, not a Recovery collector or boot installer."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = ('build.py', 'generate.py', 'extra_policy.c', 'extra_policy.h', 'parse_check.c')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(argv)
    output = args.output.absolute()
    if ROOT / 'build' not in output.parents or output.exists() or '..' in output.parts or any(p.is_symlink() for p in output.parents):
        raise ValueError('new workspace output required')
    spec = importlib.util.spec_from_file_location('policy_extension31ao', HERE / 'generate.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    inputs = {name: sha((HERE / name).read_bytes()) for name in INPUTS}
    output.mkdir(parents=True, mode=0o700)
    source = output / 'sources'
    proof = generator.generate(source)
    base = (ROOT / 'tools/boot-object31aj-native/state.c').read_text()
    proposed = generator.frozen_generator().strip((source / 'state.c').read_text())
    prefix = ('#include <stdbool.h>\n#include <stdint.h>\n#include <stddef.h>\n'
              '#include <ctype.h>\n#include <stdlib.h>\n#include <stdio.h>\n'
              '#include <string.h>\n#include <strings.h>\n#include "extra_policy.h"\n'
              '#define POLICY_LIMIT 65536\n'
              'typedef struct {const unsigned char *p;size_t n;} Bytes;\n'
              'static const char *refusal_reason="preflightRefused";\n')
    for name, state in (('old', base), ('proposed', proposed)):
        pure = generator.parser_source(state)
        # Observation-only branch locations. Removing these exact marks gives
        # back the extracted real parser byte-for-byte. No predicate changes.
        mark = '{parse_failure_line=__LINE__;goto done;}'
        observed = pure.replace('goto done;', mark)
        if observed.replace(mark, 'goto done;') != pure:
            raise ValueError('parser observation reversal mismatch')
        body = (prefix + 'static unsigned parse_failure_line;\n' + observed + '\n'
                'bool ' + name + '_policy_parse(const unsigned char *data,size_t length)'
                '{parse_failure_line=0;Policy value;return policy((Bytes){data,length},&value);}\n'
                'unsigned ' + name + '_policy_failure(void){return parse_failure_line;}\n')
        (source / (name + '_parse.c')).write_text(body)
    (source / 'parse_check.c').write_bytes((HERE / 'parse_check.c').read_bytes())
    binary = output / 'desktop-parser'
    command = ['/usr/bin/xcrun', 'clang', '-std=c11', '-O2', '-Wall', '-Wextra',
               '-Werror', '-Wno-deprecated-declarations', '-arch', 'arm64',
               '-mmacosx-version-min=13.0']
    if args.sanitize:
        command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    command += [str(source / name) for name in ('old_parse.c', 'proposed_parse.c',
                                               'extra_policy.c', 'parse_check.c')]
    command += ['-o', str(binary)]
    subprocess.run(command, check=True, cwd=ROOT, timeout=60)
    compiler = subprocess.run(['/usr/bin/xcrun', 'clang', '--version'],
                              capture_output=True, text=True, check=True).stdout.splitlines()[0]
    sdk = subprocess.run(['/usr/bin/xcrun', '--show-sdk-version'],
                         capture_output=True, text=True, check=True).stdout.strip()
    if inputs != {name: sha((HERE / name).read_bytes()) for name in INPUTS}:
        raise ValueError('source changed')
    receipt = {'schema': 'ilinux31ao-desktop-parser-build-v1',
               'source_inputs': inputs, 'guard_preservation': proof,
               'binary_bytes': binary.stat().st_size,
               'binary_sha256': sha(binary.read_bytes()), 'compiler': compiler,
               'sdk': sdk, 'abi': 'arm64', 'minimum_macos': '13.0',
               'sanitized': args.sanitize, 'contains_host_capture_api': False,
               'Recovery_collector_built': False, 'native_ready': False}
    (output / 'build-result.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print('{"status":"PURE_DESKTOP_PARSER_COMPILED","native_ready":false}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError):
        print('{"status":"REFUSED","native_ready":false}')
        raise SystemExit(2)
