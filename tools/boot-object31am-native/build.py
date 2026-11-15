#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build original 31AM with frozen admission sources and the installed SDK only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = {
    'tools/boot-object31al-native/generate.py': 'f6d4b336b0f95f3793cf849618e6fe1b9542da3421b53787436304e7bfb1adca',
    'tools/boot-object31al-native/diagnostic.c': 'f40efbf9bb1366e00faff3acd32cd876619992599a4cff70beff877b783efae3',
    'tools/boot-object31al-native/diagnostic.h': 'bd79bb8be0502e3125856100d674d6a1ba5c4948fdfe7da13ee0a0cdaaac9ad5',
}
def sha(data): return hashlib.sha256(data).hexdigest()
def pairs(items):
    result = {}
    for k, v in items:
        if k in result: raise ValueError('duplicate key')
        result[k] = v
    return result
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--candidate-definition', required=True, type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args(); out = args.output.absolute()
    if ROOT / 'build' not in out.parents or out.exists() or '..' in out.parts or any(p.is_symlink() for p in out.parents): raise ValueError('new workspace output required')
    raw = args.candidate_definition.read_bytes()
    if not 0 < len(raw) <= 16384: raise ValueError('definition bound')
    d = json.loads(raw, object_pairs_hook=pairs)
    if type(d) is not dict or set(d) != {'schema','target','bytes','sha256','publication_authorizes_writes'} or d['schema'] != 'ilinux31aj-compiled-candidate-v1' or d['target'] != {'model':'Mac17,6','board':'j716c','chip_id':'0x6050'} or d['publication_authorizes_writes'] is not False: raise ValueError('definition schema')
    if type(d['bytes']) is not int or not 0 < d['bytes'] <= 160*1024*1024 or type(d['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',d['sha256']): raise ValueError('definition payload')
    frozen = {n: (ROOT / n).read_bytes() for n in FROZEN}
    if any(sha(frozen[n]) != h for n,h in FROZEN.items()): raise ValueError('frozen source mismatch')
    name = 'tools/boot-object31al-native/generate.py'
    spec = importlib.util.spec_from_file_location('frozen_generator31am', ROOT / name)
    generator = importlib.util.module_from_spec(spec)
    exec(compile(frozen[name], str(ROOT / name), 'exec'), generator.__dict__)
    names = ('build.py','preboot.c','preboot.h','main.c','result.c')
    inputs = {n: sha((HERE/n).read_bytes()) for n in names}
    out.mkdir(parents=True, mode=0o700); source = out / 'sources'
    proof = generator.generate(source)
    for n in ('preboot.c','preboot.h','main.c','result.c'): (source/n).write_bytes((HERE/n).read_bytes())
    for n in ('diagnostic.c','diagnostic.h'): (source/n).write_bytes(frozen['tools/boot-object31al-native/'+n])
    binary = out / 'ilinux31aj-reader'
    command = ['/usr/bin/xcrun','clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-arch','arm64','-mmacosx-version-min=13.0','-DWORKSPACE_ROOT='+json.dumps(str(ROOT)),'-DCANDIDATE_BYTES='+str(d['bytes']),'-DCANDIDATE_SHA256='+json.dumps(d['sha256'])]
    if args.sanitize: command += ['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    command += [str(source/n) for n in ('core.c','json.c','preboot.c','result.c','main.c')] + ['-framework','CoreFoundation','-lcompression','-o',str(binary)]
    subprocess.run(command, check=True, cwd=ROOT)
    compiler = subprocess.run(['/usr/bin/xcrun','clang','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    sdk = subprocess.run(['/usr/bin/xcrun','--show-sdk-version'],capture_output=True,text=True,check=True).stdout.strip()
    if not 0 < len(compiler) <= 256 or not compiler.isascii() or not re.fullmatch('[0-9]+(?:[.][0-9]+)*',sdk): raise ValueError('tool version')
    if inputs != {n:sha((HERE/n).read_bytes()) for n in names} or any(sha((ROOT/n).read_bytes()) != h for n,h in FROZEN.items()): raise ValueError('source changed')
    receipt = {'schema':'ilinux31am-native-build-v1','source_inputs':inputs,'frozen_inputs':FROZEN,'guard_preservation':proof,'candidate_definition':d,'binary_bytes':binary.stat().st_size,'binary_sha256':sha(binary.read_bytes()),'system_sdk_only':True,'compiler_version':compiler,'sdk_version':sdk,'abi':'arm64','minimum_macos':'13.0','sanitized':args.sanitize,'live_run':False,'recovery_run':False,'host_changes':False,'native_ready':False}
    (out/'build-result.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('{"status":"CONDITIONAL_PREBOOT_COMPILED","live_run":false,"native_ready":false}')
if __name__ == '__main__':
    try: main()
    except (ValueError,OSError,subprocess.CalledProcessError):
        print('{"status":"REFUSED","native_ready":false,"live_run":false}');sys.exit(2)
