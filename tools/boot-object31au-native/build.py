#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build original AU transaction diagnostics; never dispatch live modes."""
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


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(argv)
    aq = load('qualified_aq_for_au', ROOT/'tools/boot-object31aq-native/build.py')
    au = load('original_au_transforms', HERE/'generate.py')
    out = args.output.absolute()
    aq.require(ROOT/'build' in out.parents and '..' not in out.parts and not out.exists()
               and not any(p.is_symlink() for p in out.parents))
    records, contents = aq.retained_sources()
    extras = [HERE/name for name in ('build.py','generate.py','controller.c','read_diagnostics.h')]
    extras += [ROOT/'tools/object31at-diagnostics'/name for name in ('diagnostics.c','diagnostics.h')]
    extras += [ROOT/'tools/boot-object31ar-native/controller.c', ROOT/'tools/boot-object31aq-native/build.py']
    own = {str(p.relative_to(ROOT)):aq.sha(p.read_bytes()) for p in extras}
    aq.require(own['tools/boot-object31ar-native/controller.c']=='6f170d548a95d17bee075ac9aaded9e250c050718efc76271afcabb722195ab1')
    aq.require(own['tools/object31at-diagnostics/diagnostics.c']=='499ca044cc24860925b21483a82851546c3fb4cb390e60527826bab8f40254aa')
    aq.require(own['tools/object31at-diagnostics/diagnostics.h']=='c26693ec53d7cd3589cb90ad9d7f6e618b41b972a30ab025cda80ddf0cdb51b2')
    old_controller=(ROOT/'tools/boot-object31ar-native/controller.c').read_text()
    new_controller=(HERE/'controller.c').read_text()
    def transport(text):
        return text[text.index('static int interactive_child('):text.index('static int run_writer(')]
    aq.require(transport(old_controller)==transport(new_controller))
    generator = types.ModuleType('qualified_ao_for_au')
    generator.__file__ = str(ROOT/aq.GENERATOR)
    exec(compile(contents[aq.GENERATOR], generator.__file__, 'exec'), generator.__dict__)
    out.mkdir(parents=True,mode=0o700)
    source = out/'sources'
    proof = generator.generate(source)
    observed = (source/'state.c').read_text()
    aq.require(generator.frozen_generator().strip(generator.reverse(observed)).encode()==contents['tools/boot-object31aj-native/state.c'])
    pure = generator.frozen_generator().strip(observed)
    aq.require('diagnostic_' not in pure and 'D_TEST(' not in pure and '/*31AL+' not in pure)
    changed, reversed_state, count = au.state_transform(pure)
    aq.require(reversed_state==pure)
    (source/'state.c').write_text(changed)
    for name in ('core.c','reader.h'):
        (source/name).write_bytes(contents['tools/boot-object31aj-native/'+name])
    original_json = contents['tools/boot-object31aj-native/json.c'].decode()
    (source/'json.c').write_text(au.json_transform(original_json))
    for name in ('extra_policy.c','extra_policy.h'):
        (source/name).write_bytes(contents['tools/boot-object31ao-native/'+name])
    for name in ('controller.c','read_diagnostics.h'):
        (source/name).write_bytes((HERE/name).read_bytes())
    for name in ('diagnostics.c','diagnostics.h'):
        (source/name).write_bytes((ROOT/'tools/object31at-diagnostics'/name).read_bytes())
    binary = out/'ilinux31au-reader'
    command = ['/usr/bin/xcrun','clang','-std=c11','-O2','-Wall','-Wextra','-Werror',
               '-Wno-deprecated-declarations','-arch','arm64','-mmacosx-version-min=13.0',
               '-DWORKSPACE_ROOT='+json.dumps(str(ROOT)),
               '-DCANDIDATE_BYTES='+str(aq.CANDIDATE['bytes']),
               '-DCANDIDATE_SHA256='+json.dumps(aq.CANDIDATE['sha256'])]
    if args.sanitize:
        command += ['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    command += [str(source/name) for name in ('diagnostics.c','json.c','extra_policy.c','controller.c')]
    command += ['-framework','CoreFoundation','-lcompression','-o',str(binary)]
    subprocess.run(command,cwd=ROOT,check=True,timeout=90)
    aq.require(aq.retained_sources()[0]==records)
    aq.require(all(aq.sha((ROOT/name).read_bytes())==value for name,value in own.items()))
    compiler=subprocess.run(['/usr/bin/xcrun','clang','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    sdk=subprocess.run(['/usr/bin/xcrun','--show-sdk-version'],capture_output=True,text=True,check=True).stdout.strip()
    receipt=dict(schema='ilinux31au-native-build-v1',source_inputs=own,retained_source_pins=records,
        binary_bytes=binary.stat().st_size,binary_sha256=aq.sha(binary.read_bytes()),candidate_definition=aq.CANDIDATE,
        compiler_version=compiler,sdk_version=sdk,sanitized=args.sanitize,qualified_state_sha256=aq.sha(changed.encode()),
        guard_preservation=dict(proof,AU_exact_reversal=True,AU_state_edits=count,original_recognizer_byte_identical=True,
            initial_payload='BOOT021',initial_ctrr='disabled',candidate_ctrr='enabled',transport_changed=False),
        live_run=False,host_changes=False,native_ready=False)
    (out/'build-result.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('{"status":"CONTROLLER_COMPILED","live_run":false,"native_ready":false}')


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError,subprocess.SubprocessError):
        print('{"status":"REFUSED","live_run":false,"native_ready":false}')
        raise SystemExit(2)
