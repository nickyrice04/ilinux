#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Future explicitly authorized lab-Data copy. Default is help; no live calls.

The production CLI has no target override. Tests inject a workspace fixture
backend into _stage; they never invoke --stage or construct the live backend.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import types
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
INVENTORY='native/boot/attempt31aj-kit/source-sha256.txt'
PROFILE='native/boot/attempt31aj-kit/recovery-profile.json'
GUARD='tools/boot-object31ag/read_selected.py'
GUARD_SHA='0728fae7dd30fd2ef14dacdf9e25028614f239c254c8fc40c3f8866fde32dc47'
LAB='/Volumes/iLinux Boot Lab'
DATA='/Volumes/iLinux Boot Lab - Data'
BASE=DATA+'/Users/Shared/iLinuxBoot'
DESTINATION='31aj-kit'
STATE='31aj-state'


def module(name):
    s=importlib.util.spec_from_file_location('recovery31aj_stage_'+name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


profile=module('profile');preparation=module('prepare')


def require(value):
    if not value:raise ValueError('staging refused')


def checked_sources(root,inventory):
    path=preparation.checked_path(inventory,root)
    require(path==root/INVENTORY)
    require(0<path.stat().st_size<=256*1024)
    data,hashes=preparation.source_closure(root,path)
    require({PROFILE,GUARD,'tools/recovery31aj/stage_lab.py',
             'tools/recovery31aj/test_stage_lab.py'}<=set(hashes))
    require(hashes[GUARD]==GUARD_SHA)
    guard=preparation.checked_path(GUARD,root).read_bytes()
    require(hashlib.sha256(guard).hexdigest()==GUARD_SHA)
    # Only original, frozen, digest-verified project source is loaded.
    frozen=types.ModuleType('frozen31ag_staging');frozen.__file__=str(root/GUARD)
    exec(compile(guard,str(root/GUARD),'exec'),frozen.__dict__)
    p=preparation.checked_path(PROFILE,root);require(0<p.stat().st_size<=16384)
    raw=p.read_bytes();value=profile.load(raw);require(raw==profile.canonical(value))
    require(hashlib.sha256(raw).hexdigest()==hashes[PROFILE])
    return data,hashes,frozen,raw,value


def guard_metadata(value,frozen):
    require(type(value) is dict and set(value)=={'platform','euid','model','lab','data','original','apfs'})
    require(value['platform']=='darwin' and type(value['euid']) is int and value['euid']==0)
    require(value['model']=='Mac17,6')
    lab,data,original=value['lab'],value['data'],value['original']
    require(all(type(v) is dict and v.get('Internal') is True for v in (lab,data,original)))
    require(original.get('VolumeName')=='Macintosh HD' and original.get('MountPoint')=='/')
    require(data.get('VolumeName')=='iLinux Boot Lab - Data' and data.get('MountPoint')==DATA)
    require(data.get('FileVault') is False)
    target=frozen.guard_target(lab,original,value['apfs'])
    require(data.get('APFSContainerReference')==target['container']==original.get('APFSContainerReference'))
    require(frozen.uuid(data.get('APFSVolumeGroupID')).lower()==target['group'].lower())
    duuid=frozen.uuid(data.get('VolumeUUID')).lower();ddev=frozen.volume(data.get('DeviceIdentifier'))
    require(duuid not in (frozen.uuid(lab['VolumeUUID']).lower(),frozen.uuid(original['VolumeUUID']).lower()))
    containers=value['apfs']['Containers'];ct=frozen.one([c for c in containers if c['ContainerReference']==target['container']])
    entry=frozen.one([v for v in ct['Volumes'] if v['APFSVolumeUUID'].lower()==duuid])
    require(entry.get('Roles')==['Data'] and entry.get('Name')=='iLinux Boot Lab - Data' and entry.get('DeviceIdentifier')==ddev)
    # Private identities are compared only in memory and never returned by receipts.
    return (target['group'].lower(),target['container'],duuid,ddev,
            frozen.uuid(original['APFSVolumeGroupID']).lower())


class LiveBackend:
    synthetic=False
    def observe(self,frozen):
        require(sys.platform=='darwin' and os.geteuid()==0)
        model=frozen.capture(['/usr/sbin/sysctl','-n','hw.model'],64).strip().decode('ascii')
        return {'platform':sys.platform,'euid':os.geteuid(),'model':model,
          'lab':frozen.disk_info(LAB),'data':frozen.disk_info(DATA),'original':frozen.disk_info('/'),
          'apfs':frozen.plistlib.loads(frozen.capture(['/usr/sbin/diskutil','apfs','list','-plist']))}


def fingerprint(info):
    return (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def digest_fd(fd,expected):
    before=os.fstat(fd);require(stat.S_ISREG(before.st_mode) and before.st_size==expected['bytes'])
    os.lseek(fd,0,os.SEEK_SET);h=hashlib.sha256();total=0
    while True:
        chunk=os.read(fd,1024*1024)
        if not chunk:break
        total+=len(chunk);require(total<=expected['bytes']);h.update(chunk)
    require(total==expected['bytes'] and h.hexdigest()==expected['sha256'])
    require(fingerprint(before)==fingerprint(os.fstat(fd)))
    return fingerprint(before)


def absent_at(fd,name):
    try:os.stat(name,dir_fd=fd,follow_symlinks=False)
    except FileNotFoundError:return True
    return False


def _stage(prepared,inventory,backend=None,root=ROOT):
    """Production target is fixed; injected synthetic target stays within root."""
    root=Path(root).resolve();source_record,hashes,frozen,raw,value=checked_sources(root,inventory)
    prepared=Path(prepared)
    if not prepared.is_absolute():prepared=root/prepared
    require(root/'build' in prepared.parents)
    preparation.checked_path(prepared,root,False)
    records={item['name']:dict(item) for item in value['files'].values()}
    records['profile.json']={'name':'profile.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    require(prepared.is_dir() and set(p.name for p in prepared.iterdir())==set(records))
    fds={};fingerprints={};base_fd=dest_fd=None;created=False;created_files=[]
    backend=LiveBackend() if backend is None else backend
    try:
        # Verify all four source files before querying or opening the lab target.
        for name,item in records.items():
            path=preparation.checked_path(prepared/name,root)
            fd=frozen.secure_open(path);fds[name]=fd;fingerprints[name]=digest_fd(fd,item)
        if backend.synthetic:
            fixture=Path(backend.fixture_root)
            require(fixture.is_absolute() and root in fixture.parents)
            base=fixture/'lab-data/Users/Shared/iLinuxBoot'
            preparation.checked_path(base,root,False)
        else:
            require(type(backend) is LiveBackend);base=Path(BASE)
            # System/Data paths and every base path component must be real dirs.
            for path in (LAB,DATA):
                fd=frozen.secure_open(path,directory=True);os.close(fd)
        binding=guard_metadata(backend.observe(frozen),frozen)
        base_fd=frozen.secure_open(base,directory=True)
        require(absent_at(base_fd,STATE) and absent_at(base_fd,DESTINATION))
        require(checked_sources(root,inventory)[:2]==(source_record,hashes))
        for name,item in records.items():
            require(digest_fd(fds[name],item)==fingerprints[name])
            current=frozen.secure_open(prepared/name)
            try:require(fingerprint(os.fstat(current))==fingerprints[name])
            finally:os.close(current)
        # New destination, never overwrite or remove an existing kit/state.
        os.mkdir(DESTINATION,0o700,dir_fd=base_fd);created=True
        dest_fd=os.open(DESTINATION,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=base_fd)
        os.fchmod(dest_fd,0o700)
        for name,item in records.items():
            mode=0o700 if name=='ilinux31aj-reader' else 0o600
            out=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode,dir_fd=dest_fd)
            created_files.append(name)
            try:
                os.fchmod(out,mode);os.lseek(fds[name],0,os.SEEK_SET);h=hashlib.sha256();total=0
                while True:
                    chunk=os.read(fds[name],1024*1024)
                    if not chunk:break
                    total+=len(chunk);require(total<=item['bytes']);h.update(chunk)
                    at=0
                    while at<len(chunk):
                        wrote=os.write(out,chunk[at:]);require(wrote>0);at+=wrote
                require(total==item['bytes'] and h.hexdigest()==item['sha256'])
                require(fingerprint(os.fstat(fds[name]))==fingerprints[name]);os.fsync(out)
            finally:os.close(out)
        os.fsync(dest_fd)
        os.fsync(base_fd)
        require(guard_metadata(backend.observe(frozen),frozen)==binding)
        require(checked_sources(root,inventory)[:2]==(source_record,hashes))
        for name,item in records.items():
            require(digest_fd(fds[name],item)==fingerprints[name])
            current=frozen.secure_open(prepared/name)
            try:require(fingerprint(os.fstat(current))==fingerprints[name])
            finally:os.close(current)
            copied=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=dest_fd)
            try:digest_fd(copied,item)
            finally:os.close(copied)
        # The held descriptor alone is insufficient: a concurrent directory
        # rename must not turn a successful receipt into a different named kit.
        current_base=frozen.secure_open(base,directory=True)
        try:
            named=os.fstat(current_base);held=os.fstat(base_fd)
            require((named.st_dev,named.st_ino)==(held.st_dev,held.st_ino))
        finally:os.close(current_base)
        named=os.stat(DESTINATION,dir_fd=base_fd,follow_symlinks=False)
        held=os.fstat(dest_fd)
        require(stat.S_ISDIR(named.st_mode) and
                (named.st_dev,named.st_ino)==(held.st_dev,held.st_ino))
        require(set(os.listdir(dest_fd))==set(records))
        require(absent_at(base_fd,STATE))
        return {'schema':'ilinux31aj-lab-data-staging-v1','scope':'SYNTHETIC_CONTROL' if backend.synthetic else 'MACOS_LAB_DATA_STAGE',
          'staged':True,'files':{n:{'bytes':v['bytes'],'sha256':v['sha256']} for n,v in sorted(records.items())},
          'boot_settings_changed':False,'policy_read':False,'boot_object_installed':False,
          'default_changed':False,'volume_created':False,'native_ready':False}
    except BaseException as exc:
        # Cleanup touches only files created inside our new private directory.
        if created:
            if dest_fd is not None:
                for name in created_files:
                    try:os.unlink(name,dir_fd=dest_fd)
                    except OSError:pass
            try:
                current=os.stat(DESTINATION,dir_fd=base_fd,follow_symlinks=False)
                ours=os.fstat(dest_fd) if dest_fd is not None else None
                if ours is not None and (current.st_dev,current.st_ino)==(ours.st_dev,ours.st_ino):
                    os.rmdir(DESTINATION,dir_fd=base_fd)
            except OSError:pass
        if isinstance(exc,frozen.Refused):raise ValueError('staging refused') from None
        raise
    finally:
        for fd in fds.values():os.close(fd)
        if dest_fd is not None:os.close(dest_fd)
        if base_fd is not None:os.close(base_fd)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',action='store_true',help='Future authorized lab Data write; no boot/security changes')
    parser.add_argument('--prepared',type=Path);parser.add_argument('--inventory',type=Path)
    args=parser.parse_args(argv)
    if not args.stage:parser.print_help();return 0
    try:
        require(args.prepared is not None and args.inventory is not None)
        result=_stage(args.prepared,args.inventory)
    except BaseException:
        result={'schema':'ilinux31aj-lab-data-staging-v1','status':'REFUSED',
          'staging_outcome':'NOT_CONFIRMED','boot_settings_changed':False,'native_ready':False}
        print(json.dumps(result,sort_keys=True));return 2
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
