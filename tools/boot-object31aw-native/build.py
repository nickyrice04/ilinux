#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build isolated AW integration with system SDK; never dispatch helper modes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = {
 'tools/boot-object31au-native/controller.c': 'dcfc50ae41e89643408f7a255939cf69317bce79782d97f41023f529eec6ef60',
 'tools/boot-object31au-native/generate.py': '07422693f3b5bb3f50d8285efbe2c73349ad5d8e85c5d610d0d358448db4c66c',
 'tools/codec31av/buffer_proposal.c': 'a64b78a2dccfa3ee986d8a9d421d799d7c8aec48c727a965090b4bd145ec312a',
 'native/boot/attempt31au-package/source-sha256.txt': '975364a78be8ae44247ceddb7ea63b72b04ea240baf541006f94a2cba92f3865',
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_inputs(aq):
    for name, digest in FROZEN.items():
        aq.require(aq.sha(aq.read_source(name)) == digest)
    inventory = aq.read_source('native/boot/attempt31au-package/source-sha256.txt').decode('ascii').splitlines()
    aq.require(len(inventory) == 190)
    records = {}
    for line in inventory:
        match = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9_./-]+)', line)
        aq.require(match is not None)
        digest, name = match.groups()
        aq.require(name not in records and aq.sha(aq.read_source(name)) == digest)
        records[name] = digest
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(argv)
    aq = load('qualified_aq_for_aw', ROOT/'tools/boot-object31aq-native/build.py')
    aw = load('original_aw_derivation', HERE/'generate.py')
    out = args.output.absolute()
    aq.require(ROOT/'build' in out.parents and '..' not in out.parts and not out.exists()
               and not any(p.is_symlink() for p in out.parents))
    frozen = frozen_inputs(aq)
    records, contents = aq.retained_sources()
    au = types.ModuleType('verified_au_for_aw')
    au.__file__ = str(ROOT/'tools/boot-object31au-native/generate.py')
    exec(compile(aq.read_source('tools/boot-object31au-native/generate.py'), au.__file__, 'exec'), au.__dict__)
    old_controller = aq.read_source('tools/boot-object31au-native/controller.c').decode()
    own_names = ('build.py','generate.py','controller.c','read_diagnostics.h','codec.c','codec.h','test_native.py')
    own = {str((HERE/name).relative_to(ROOT)): aq.sha((HERE/name).read_bytes()) for name in own_names}
    new_controller = (HERE/'controller.c').read_text()
    safety = aw.safety_proof(old_controller, new_controller)
    generator = types.ModuleType('qualified_ao_for_aw')
    generator.__file__ = str(ROOT/aq.GENERATOR)
    exec(compile(contents[aq.GENERATOR], generator.__file__, 'exec'), generator.__dict__)
    out.mkdir(parents=True, mode=0o700)
    source = out/'sources'
    qualified = generator.generate(source)
    observed = (source/'state.c').read_text()
    aq.require(generator.frozen_generator().strip(generator.reverse(observed)).encode() == contents['tools/boot-object31aj-native/state.c'])
    pure = generator.frozen_generator().strip(observed)
    changed, au_state = aw.state_transform(pure, au)
    (source/'state.c').write_text(changed)
    for name in ('core.c','reader.h'):
        (source/name).write_bytes(contents['tools/boot-object31aj-native/'+name])
    (source/'json.c').write_text(aw.json_transform(contents['tools/boot-object31aj-native/json.c'].decode(), au))
    for name in ('extra_policy.c','extra_policy.h'):
        (source/name).write_bytes(contents['tools/boot-object31ao-native/'+name])
    for name in ('controller.c','read_diagnostics.h','codec.c','codec.h'):
        (source/name).write_bytes((HERE/name).read_bytes())
    buffer_source = aq.read_source('tools/codec31av/buffer_proposal.c').decode()
    (source/'buffer_proposal.c').write_text(aw.buffer_transform(buffer_source))
    binary = out/'ilinux31aw-reader'
    command = ['/usr/bin/xcrun','clang','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-Wno-deprecated-declarations','-arch','arm64','-mmacosx-version-min=13.0',
        '-DWORKSPACE_ROOT='+json.dumps(str(ROOT)), '-DCANDIDATE_BYTES='+str(aq.CANDIDATE['bytes']),
        '-DCANDIDATE_SHA256='+json.dumps(aq.CANDIDATE['sha256'])]
    if args.sanitize:
        command += ['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    command += [str(source/name) for name in ('codec.c','json.c','extra_policy.c','controller.c')]
    command += ['-framework','CoreFoundation','-lcompression','-o',str(binary)]
    subprocess.run(command, cwd=ROOT, check=True, timeout=90)
    aq.require(frozen_inputs(aq) == frozen and aq.retained_sources()[0] == records)
    aq.require(all(aq.sha((ROOT/name).read_bytes()) == digest for name,digest in own.items()))
    compiler = subprocess.run(['/usr/bin/xcrun','clang','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    sdk = subprocess.run(['/usr/bin/xcrun','--show-sdk-version'],capture_output=True,text=True,check=True).stdout.strip()
    receipt = {'schema':'ilinux31aw-native-build-v1','source_inputs':own,'retained_source_pins':frozen,
        'qualified_sources':records,'binary_bytes':binary.stat().st_size,'binary_sha256':aq.sha(binary.read_bytes()),
        'candidate_definition':aq.CANDIDATE,'compiler_version':compiler,'sdk_version':sdk,'sanitized':args.sanitize,
        'qualified_state_sha256':aq.sha(changed.encode()),'derived_AU_state_sha256':aq.sha(au_state.encode()),
        'guard_preservation':dict(qualified,**safety,buffer_failure_labels_only_reversal=True,
            original_core_reader_byte_identical=True,initial_payload='BOOT021',initial_ctrr='disabled',candidate_ctrr='enabled'),
        'compiled_source_sha256':{p.name:aq.sha(p.read_bytes()) for p in source.iterdir() if p.is_file()},
        'live_run':False,'host_changes':False,'native_ready':False,'kit_created':False}
    (out/'build-result.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('{"status":"CONTROLLER_COMPILED","live_run":false,"native_ready":false}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError,OSError,subprocess.SubprocessError):
        print('{"status":"REFUSED","live_run":false,"native_ready":false}')
        raise SystemExit(2)
