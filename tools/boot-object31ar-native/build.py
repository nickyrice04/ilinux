#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the original 31AR controller; never dispatch it on the host."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load_aq():
    spec = importlib.util.spec_from_file_location('pinned_aq_for_ar', ROOT/'tools/boot-object31aq-native/build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--sanitize', action='store_true')
    a = p.parse_args()
    aq = load_aq()
    out = a.output.absolute()
    aq.require(ROOT/'build' in out.parents and '..' not in out.parts and not out.exists()
               and not any(x.is_symlink() for x in out.parents))
    records, contents = aq.retained_sources()
    own = {str(path.relative_to(ROOT)): aq.sha(path.read_bytes()) for path in
           (HERE/'build.py', HERE/'controller.c', ROOT/'tools/boot-object31aq-native/build.py')}
    generator = types.ModuleType('qualified_ao_for_ar')
    generator.__file__ = str(ROOT/aq.GENERATOR)
    exec(compile(contents[aq.GENERATOR], generator.__file__, 'exec'), generator.__dict__)
    out.mkdir(parents=True, mode=0o700)
    source = out/'sources'
    proof = generator.generate(source)
    observed = (source/'state.c').read_text()
    aq.require(generator.frozen_generator().strip(generator.reverse(observed)).encode() ==
               contents['tools/boot-object31aj-native/state.c'])
    pure = generator.frozen_generator().strip(observed)
    aq.require('diagnostic_' not in pure and 'D_TEST(' not in pure and '/*31AL+' not in pure)
    (source/'state.c').write_text(pure)
    for name in ('core.c', 'json.c', 'reader.h'):
        (source/name).write_bytes(contents['tools/boot-object31aj-native/'+name])
    for name in ('extra_policy.c', 'extra_policy.h'):
        (source/name).write_bytes(contents['tools/boot-object31ao-native/'+name])
    (source/'controller.c').write_bytes((HERE/'controller.c').read_bytes())
    binary = out/'ilinux31aj-reader'
    command = ['/usr/bin/xcrun', 'clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
               '-Wno-deprecated-declarations', '-arch', 'arm64', '-mmacosx-version-min=13.0',
               '-DWORKSPACE_ROOT='+json.dumps(str(ROOT)),
               '-DCANDIDATE_BYTES='+str(aq.CANDIDATE['bytes']),
               '-DCANDIDATE_SHA256='+json.dumps(aq.CANDIDATE['sha256'])]
    if a.sanitize:
        command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    command += [str(source/name) for name in ('core.c', 'json.c', 'extra_policy.c', 'controller.c')]
    command += ['-framework', 'CoreFoundation', '-lcompression', '-o', str(binary)]
    subprocess.run(command, cwd=ROOT, check=True, timeout=90)
    aq.require(aq.retained_sources()[0] == records)
    aq.require(all(aq.sha((ROOT/name).read_bytes()) == value for name,value in own.items()))
    compiler = subprocess.run(['/usr/bin/xcrun','clang','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    sdk = subprocess.run(['/usr/bin/xcrun','--show-sdk-version'],capture_output=True,text=True,check=True).stdout.strip()
    receipt = dict(schema='ilinux31ar-native-build-v1', source_inputs=own,
                   retained_source_pins=records, binary_bytes=binary.stat().st_size,
                   binary_sha256=aq.sha(binary.read_bytes()), candidate_definition=aq.CANDIDATE,
                   compiler_version=compiler, sdk_version=sdk, sanitized=a.sanitize,
                   qualified_state_sha256=aq.sha(pure.encode()), guard_preservation=proof,
                   live_run=False, host_changes=False, native_ready=False)
    (out/'build-result.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('{"status":"CONTROLLER_COMPILED","live_run":false,"native_ready":false}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError,OSError,subprocess.SubprocessError):
        print('{"status":"REFUSED","live_run":false,"native_ready":false}')
        raise SystemExit(2)
