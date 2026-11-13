#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify exact original source inventory and local artifacts; render inert pages.

Output must be new and within repository build/. No Recovery tools are invoked.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def module(name):
    s=importlib.util.spec_from_file_location('recovery31aj_'+name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


profile=module('profile');renderer=module('render')


def checked_path(path,root,exists=True):
    path=Path(path)
    if not path.is_absolute():path=root/path
    if '..' in path.parts:raise ValueError('path traversal')
    try:parts=path.relative_to(root).parts
    except ValueError as e:raise ValueError('workspace path required') from e
    current=root
    for part in parts:
        current/=part
        if current.is_symlink():raise ValueError('symlink')
    if exists and not current.is_file():raise ValueError('regular file required')
    return current


def sha_file(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def source_closure(root,inventory):
    data=checked_path(inventory,root).read_bytes()
    if not 0<len(data)<=256*1024:raise ValueError('inventory bound')
    result={}
    for line in data.decode('ascii').splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)',line)
        if not m:raise ValueError('source inventory grammar')
        digest,name=m.groups();p=PurePosixPath(name)
        if p.is_absolute() or str(p)!=name or '..' in p.parts or name in result:raise ValueError('source inventory path')
        f=checked_path(name,root)
        if f.stat().st_size>8*1024*1024 or sha_file(f)!=digest:raise ValueError('source inventory mismatch')
        result[name]=digest
    required={'tools/recovery31aj/'+name for name in ('profile.py','model.py','render.py','prepare.py','test_recovery.py','README.md')}
    if not required<=set(result):raise ValueError('complete Recovery source closure required')
    return data,result


def prepare(profile_path,kit_path,inventory,output,root=ROOT):
    root=Path(root).resolve()
    source_data,source_hashes=source_closure(root,inventory)
    p=checked_path(profile_path,root)
    if not 0<p.stat().st_size<=16384:raise ValueError('profile input bound')
    data=p.read_bytes();value=profile.load(data)
    if data!=profile.canonical(value):raise ValueError('canonical profile required')
    kit=Path(kit_path)
    if not kit.is_absolute():kit=root/kit
    snapshots={}
    for role,item in value['files'].items():
        f=checked_path(kit/item['name'],root)
        if f.stat().st_size!=item['bytes'] or sha_file(f)!=item['sha256']:raise ValueError('artifact mismatch')
        snapshots[role]=(f,f.stat().st_size,sha_file(f))
    destination=checked_path(output,root,False)
    if root/'build' not in destination.parents or destination.exists():raise ValueError('new output below build required')
    generated={'profile.json':data,'install-paste.txt':renderer.render(value,'install').encode(),
               'restore-paste.txt':renderer.render(value,'restore').encode(),
               'recovery.html':renderer.page(value).encode()}
    if source_closure(root,inventory)!=(source_data,source_hashes):raise ValueError('source changed during preparation')
    for f,size,digest in snapshots.values():
        if f.stat().st_size!=size or sha_file(f)!=digest:raise ValueError('artifact changed during preparation')
    report={'schema':'ilinux31aj-recovery-preparation-v1','source_inventory_sha256':hashlib.sha256(source_data).hexdigest(),
            'profile_sha256':profile.digest(value),'verified_source_count':len(source_hashes),
            'output':{n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in generated.items()},
            'write_authorized':False,'native_ready':False,'live_recovery_admission':'UNKNOWN'}
    destination.mkdir(parents=True,mode=0o700)
    for name,d in generated.items():(destination/name).write_bytes(d)
    (destination/'receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',required=True);p.add_argument('--kit',required=True)
    p.add_argument('--source-inventory',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    try:print(json.dumps(prepare(a.profile,a.kit,a.source_inventory,a.output),sort_keys=True));return 0
    except (ValueError,OSError,UnicodeError):
        print('{"status":"REFUSED","write_authorized":false,"native_ready":false}');return 2


if __name__=='__main__':raise SystemExit(main())
