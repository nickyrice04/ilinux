#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline AX build only. No helper mode, query, mount or writer is run."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
AW_RECEIPT='e4974d3cd3de650bba2824fb6071e4834c6b86fc713d6b28f48407ba53bf16a3'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def sha(data):return hashlib.sha256(data).hexdigest()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args(argv);out=args.output.absolute()
    if ROOT/'build' not in out.parents or '..' in out.parts or out.exists() or any(p.is_symlink() for p in out.parents):
        raise ValueError('new workspace output required')
    receipt_bytes=(ROOT/'native/boot/attempt31aw-offline-2026-11-15.json').read_bytes()
    if sha(receipt_bytes)!=AW_RECEIPT:raise ValueError('frozen AW receipt differs')
    frozen=json.loads(receipt_bytes)['source_sha256']
    if len(frozen)!=14 or any(sha((ROOT/name).read_bytes())!=digest for name,digest in frozen.items()):
        raise ValueError('AW frozen inputs differ')
    aw_builder=load('verified_aw_builder_for_ax',ROOT/'tools/boot-object31aw-native/build.py')
    aw=load('verified_aw_generator_for_ax',ROOT/'tools/boot-object31aw-native/generate.py')
    ax=load('original_ax_generator',HERE/'generate.py')
    names=('build.py','generate.py','controller.c','read_diagnostics.h','codec.c','codec.h','policy_contract.c','policy_contract.h','transition_state.inc','transition_flow.inc','test_native.py','test_policy.py','policy_probe.c')
    own={str((HERE/name).relative_to(ROOT)):sha((HERE/name).read_bytes()) for name in names}
    proof=ax.safety_proof((ROOT/'tools/boot-object31aw-native/controller.c').read_text(),(HERE/'controller.c').read_text(),aw)
    out.mkdir(parents=True,mode=0o700)
    reference=out/'aw-reference'
    # Reuse the exact qualified AW derivation and all retained checks. Its
    # compiler output is workspace scratch only; it is never dispatched.
    aw_builder.main(['--output',str(reference)])
    previous=json.loads((reference/'build-result.json').read_text())
    source=out/'sources';source.mkdir(mode=0o700)
    for path in (reference/'sources').iterdir():
        if path.is_file():(source/path.name).write_bytes(path.read_bytes())
    changed,count=ax.state_transform((source/'state.c').read_text());(source/'state.c').write_text(changed)
    (source/'json.c').write_text(ax.json_transform((source/'json.c').read_text()))
    for name in ('controller.c','read_diagnostics.h','codec.c','codec.h','policy_contract.c','policy_contract.h','transition_state.inc','transition_flow.inc'):
        (source/name).write_bytes((HERE/name).read_bytes())
    candidate=previous['candidate_definition'];binary=out/'ilinux31ax-reader'
    command=['/usr/bin/xcrun','clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations',
        '-arch','arm64','-mmacosx-version-min=13.0','-DWORKSPACE_ROOT='+json.dumps(str(ROOT)),
        '-DCANDIDATE_BYTES='+str(candidate['bytes']),'-DCANDIDATE_SHA256='+json.dumps(candidate['sha256'])]
    if args.sanitize:command+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    command +=[str(source/name) for name in ('codec.c','json.c','extra_policy.c','policy_contract.c','controller.c')]
    command +=['-framework','CoreFoundation','-lcompression','-o',str(binary)]
    subprocess.run(command,cwd=ROOT,check=True,timeout=90)
    if any(sha((ROOT/name).read_bytes())!=digest for name,digest in frozen.items()) or any(sha((ROOT/name).read_bytes())!=digest for name,digest in own.items()):
        raise ValueError('source changed during build')
    receipt={'schema':'ilinux31ax-native-build-v1','source_inputs':own,'frozen_aw_inputs':frozen,
        'retained_source_pins':previous['retained_source_pins'],'candidate_definition':candidate,
        'guard_preservation':dict(proof,typed_state_reversible=True,typed_state_patches=count),
        'binary_bytes':binary.stat().st_size,'binary_sha256':sha(binary.read_bytes()),'sanitized':args.sanitize,
        'compiled_source_sha256':{p.name:sha(p.read_bytes()) for p in source.iterdir() if p.is_file()},
        'compiler_version':previous['compiler_version'],'sdk_version':previous['sdk_version'],
        'live_run':False,'host_changes':False,'native_ready':False,'kit_created':False}
    (out/'build-result.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('{"status":"AX_CONTROLLER_COMPILED","live_run":false,"native_ready":false}')


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError):
        print('{"status":"REFUSED","live_run":false,"native_ready":false}')
        raise SystemExit(2)
