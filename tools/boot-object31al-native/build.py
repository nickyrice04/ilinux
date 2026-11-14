#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build original diagnostic-only C with the installed SDK; never run live modes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('generate31al',HERE/'generate.py')
generate=importlib.util.module_from_spec(spec);spec.loader.exec_module(generate)

def pairs(items):
 result={}
 for key,value in items:
  if key in result:raise ValueError('duplicate key')
  result[key]=value
 return result

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',required=True,type=Path)
 parser.add_argument('--candidate-definition',required=True,type=Path)
 parser.add_argument('--sanitize',action='store_true')
 args=parser.parse_args();out=args.output.absolute()
 if ROOT/'build' not in out.parents or out.exists() or '..' in out.parts or any(p.is_symlink() for p in out.parents):raise ValueError('new build output required')
 blob=args.candidate_definition.read_bytes()
 if len(blob)>16384:raise ValueError('definition bound')
 d=json.loads(blob,object_pairs_hook=pairs)
 if type(d) is not dict or set(d)!={'schema','target','bytes','sha256','publication_authorizes_writes'} or d['schema']!='ilinux31aj-compiled-candidate-v1' or d['target']!={'model':'Mac17,6','board':'j716c','chip_id':'0x6050'} or d['publication_authorizes_writes'] is not False:raise ValueError('definition schema')
 if type(d['bytes']) is not int or not 0<d['bytes']<=160*1024*1024 or type(d['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',d['sha256']):raise ValueError('definition payload')
 names=('build.py','generate.py','diagnostic.h','diagnostic.c','main.c')
 before={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names}
 out.mkdir(parents=True,mode=0o700);proof=generate.generate(out/'sources')
 for name in ('diagnostic.h','diagnostic.c','main.c'):(out/'sources'/name).write_bytes((HERE/name).read_bytes())
 command=['/usr/bin/xcrun','clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-arch','arm64','-mmacosx-version-min=13.0','-DWORKSPACE_ROOT='+json.dumps(str(ROOT)),'-DCANDIDATE_BYTES='+str(d['bytes']),'-DCANDIDATE_SHA256='+json.dumps(d['sha256'])]
 if args.sanitize:command+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
 binary=out/'ilinux31aj-reader'
 command += [str(out/'sources'/name) for name in ('core.c','json.c','state.c','diagnostic.c','main.c')]+['-framework','CoreFoundation','-lcompression','-o',str(binary)]
 subprocess.run(command,check=True,cwd=ROOT)
 compiler=subprocess.run(['/usr/bin/xcrun','clang','--version'],check=True,capture_output=True,text=True).stdout.splitlines()[0]
 sdk=subprocess.run(['/usr/bin/xcrun','--show-sdk-version'],check=True,capture_output=True,text=True).stdout.strip()
 if not 0<len(compiler)<=256 or not compiler.isascii() or not re.fullmatch('[0-9]+(?:[.][0-9]+)*',sdk):raise ValueError('tool version bound')
 if before!={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names}:raise ValueError('source changed')
 receipt={'schema':'ilinux31al-native-build-v1','source_inputs':before,'guard_preservation':proof,'candidate_definition':d,'binary_bytes':binary.stat().st_size,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'system_sdk_only':True,'compiler_version':compiler,'sdk_version':sdk,'abi':'arm64','minimum_macos':'13.0','sanitized':args.sanitize,'live_run':False,'recovery_run':False,'host_changes':False,'native_ready':False}
 (out/'build-result.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'DIAGNOSTIC_ONLY_COMPILED','state_marks_strip_exact':True,'live_run':False,'native_ready':False}))

if __name__=='__main__':
 try:main()
 except (ValueError,OSError,subprocess.CalledProcessError):
  print('{"status":"REFUSED","native_ready":false,"live_run":false}');sys.exit(2)
