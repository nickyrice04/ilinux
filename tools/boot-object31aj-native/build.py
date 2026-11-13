#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile original C with the installed SDK; never install or run live modes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCES=('core.c','json.c','state.c','main.c')

def pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('duplicate key')
        result[key]=value
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate-definition',type=Path)
    parser.add_argument('--sanitize',action='store_true',help='Own-code ASan/UBSan fixture build only')
    args=parser.parse_args()
    output=args.output.absolute()
    if ROOT not in output.parents or output.exists() or any(p.is_symlink() for p in output.parents):raise ValueError('new workspace output required')
    definition=None
    if args.candidate_definition:
        blob=args.candidate_definition.read_bytes()
        if len(blob)>16384:raise ValueError('definition bound')
        definition=json.loads(blob,object_pairs_hook=pairs)
        if set(definition)!={'schema','target','bytes','sha256','publication_authorizes_writes'} or definition['schema']!='ilinux31aj-compiled-candidate-v1' or definition['target']!={'model':'Mac17,6','board':'j716c','chip_id':'0x6050'} or definition['publication_authorizes_writes'] is not False:raise ValueError('definition identity')
        if type(definition['bytes']) is not int or not 0<definition['bytes']<=160*1024*1024 or not isinstance(definition['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',definition['sha256']):raise ValueError('definition payload')
    inputs=(*SOURCES,'reader.h','build.py')
    hashes={str((HERE/name).relative_to(ROOT)):hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in inputs}
    output.mkdir(parents=True,mode=0o700)
    binary=output/'ilinux31aj-reader'
    flags=['-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-arch','arm64','-mmacosx-version-min=13.0','-DWORKSPACE_ROOT='+json.dumps(str(ROOT))]
    if definition:flags+=['-DCANDIDATE_BYTES='+str(definition['bytes']),'-DCANDIDATE_SHA256='+json.dumps(definition['sha256'])]
    if args.sanitize:flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    command=['xcrun','clang',*flags,*[str(HERE/name) for name in SOURCES],'-framework','CoreFoundation','-lcompression','-o',str(binary)]
    subprocess.run(command,check=True,cwd=ROOT)
    after={str((HERE/name).relative_to(ROOT)):hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in inputs}
    if after!=hashes:raise ValueError('source changed during build')
    receipt={'schema':'ilinux31aj-native-build-v1','original_sources':hashes,'candidate_configured':bool(definition),'candidate_definition':definition,'binary_bytes':binary.stat().st_size,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'system_sdk_only':True,'sanitized':args.sanitize,'abi':'arm64','minimum_macos':'13.0','live_run':False,'recovery_run':False,'host_changes':False,'native_ready':False}
    (output/'build-result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'ORIGINAL_C_COMPILED','candidate_configured':bool(definition),'live_run':False,'native_ready':False}))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError):
        print(json.dumps({'status':'REFUSED','live_run':False,'native_ready':False}));sys.exit(2)
