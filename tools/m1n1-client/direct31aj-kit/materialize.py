#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Materialize four already verified files into a NEW workspace build directory."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
p=module('materialize31aj_package',HERE/'package.py')

def destination(path,repo):
    path=Path(path).absolute();repo=Path(repo).resolve()
    p.need(repo/'build' in path.parents and '..' not in path.parts and not path.exists(),'NEW_WORKSPACE_OUTPUT')
    p.need(not any(x.is_symlink() for x in (path,*path.parents)),'OUTPUT_SYMLINK');return path

def output_parent(path,repo):
    """Walk/create workspace directories through stable no-follow descriptors."""
    current=os.open(repo,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parent.relative_to(repo).parts:
            try:os.mkdir(part,0o700,dir_fd=current)
            except FileExistsError:pass
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current)
            os.close(current);current=child
        return current
    except BaseException:
        os.close(current);raise

def prepare(manifest_path,folder,profile_path,output,repo=ROOT):
    repo=Path(repo).resolve();output=destination(output,repo)
    sidecar=destination(output.with_name(output.name+'.materialization.json'),repo)
    m=p.decode(p.regular(manifest_path,256*1024));result=p.review(m,folder,repo)
    profile_path=Path(profile_path).absolute()
    try:relative=profile_path.relative_to(repo).as_posix()
    except ValueError:raise p.Refusal('WORKSPACE_PROFILE') from None
    blob=p.regular(profile_path,16384)
    p.need(relative in m['sources'] and p.sha(blob)==m['sources'][relative],'PROFILE_SOURCE_BINDING')
    p.need('tools/recovery31aj/profile.py' in m['sources'],'PROFILE_READER_BINDING')
    reader_path=repo/'tools/recovery31aj/profile.py'
    source=p.regular(reader_path,65536)
    p.need(p.sha(source)==m['sources']['tools/recovery31aj/profile.py'],'PROFILE_READER_BINDING')
    profile=types.ModuleType('materialize31aj_profile');profile.__file__=str(reader_path)
    exec(compile(source,str(reader_path),'exec'),profile.__dict__)
    value=profile.load(blob);p.need(blob==profile.canonical(value),'CANONICAL_PROFILE')
    c=m['candidate'];h=m['readback'];roles=value['files']
    p.need(roles['candidate']['bytes']==c['expanded_bytes'] and roles['candidate']['sha256']==c['expanded_sha256'] and
      roles['helper']['bytes']==h['bytes'] and roles['helper']['sha256']==h['sha256'],'PROFILE_ARTIFACT_BINDING')
    folder=Path(folder)
    candidate=p.gunzip(p.checked_file(folder/c['filename'],c,32*p.MIB),160*p.MIB)
    p.need(len(candidate)==c['expanded_bytes'] and p.sha(candidate)==c['expanded_sha256'],'EXPANDED_IDENTITY')
    reader=p.checked_file(folder/h['filename'],h,2*p.MIB)
    rollback=p.regular(folder/'m1n1-boot021.bin',p.ROLLBACK_BYTES)
    p.need(len(rollback)==p.ROLLBACK_BYTES and p.sha(rollback)==p.ROLLBACK_SHA,'ROLLBACK_IDENTITY')
    files={'profile.json':blob,'candidate.macho':candidate,'ilinux31aj-reader':reader,'m1n1-boot021.bin':rollback}
    receipt={'schema':'ilinux31aj-workspace-materialization-v1','status':'VERIFIED_WORKSPACE_FILES_CREATED',
      'files':{n:p.metadata(data) for n,data in files.items()},'profile_sha256':profile.digest(value),
      'source_review':result['status'],'destination_scope':'NEW_WORKSPACE_BUILD_DIRECTORY',
      'archive_members_extracted':False,'executed':False,'lab_data_changed':False,'boot_settings_changed':False,
      'native_ready':False,'writes_authorized':False}
    # Recheck after the lengthy review, then use no-follow relative opens.
    destination(output,repo);destination(sidecar,repo)
    parent_fd=output_parent(output,repo);directory_fd=None
    try:
        os.mkdir(output.name,0o700,dir_fd=parent_fd)
        directory_fd=os.open(output.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd)
        for name,data in files.items():
            fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,
                       0o700 if name=='ilinux31aj-reader' else 0o600,dir_fd=directory_fd)
            with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        fd=os.open(sidecar.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent_fd)
        with os.fdopen(fd,'w') as stream:
            stream.write(json.dumps(receipt,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
        os.fsync(directory_fd);os.fsync(parent_fd)
    finally:
        if directory_fd is not None:os.close(directory_fd)
        os.close(parent_fd)
    return receipt

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','folder','profile','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    try:result=prepare(args.manifest,args.folder,args.profile,args.output)
    except (ValueError,OSError,KeyError,TypeError,EOFError):
        result={'status':'REFUSED','lab_data_changed':False,'boot_settings_changed':False,'native_ready':False}
    print(json.dumps(result,sort_keys=True));return 0 if result['status']=='VERIFIED_WORKSPACE_FILES_CREATED' else 2
if __name__=='__main__':raise SystemExit(main())
