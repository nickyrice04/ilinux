#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build/review a fixed local-user RAM diagnostic; never extract or execute it."""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path,PurePosixPath
import re
import sys
import tarfile
import tempfile
import zlib

_spec=importlib.util.spec_from_file_location('direct31ai_policy',Path(__file__).with_name('policy.py'))
p=importlib.util.module_from_spec(_spec);sys.modules[_spec.name]=p;_spec.loader.exec_module(p)
SCHEMA='ilinux-direct31ai-local-diagnostic-v1'
FILENAME='ilinux-direct31ai-diagnostic.tar.gz'
MAX_COMPRESSED=64*1024*1024
MAX_TOTAL=64*1024*1024
MAX_FILE=48*1024*1024
MAX_FILES=48
README=b'''31AI LOCAL-USER DIAGNOSTIC REVIEW ONLY
Exact tested 31AH kernel/RAM diagnostic, newly delivered and independently bound.
Baseline Aura reference only; no loader is installed by this archive.
No Apple firmware, identity, credentials, modules, storage filesystem or raw logs.
Do not extract, execute, boot, install or publicly upload this review archive.
Source, relink object and clearly labelled common license texts accompany review.
Full public libc corresponding-source closure is incomplete. No public Release.
Generic four-vCPU liveness does not prove physical M5 cores, drivers or parity.
No host settings, security, volumes or firmware change is authorized by this file.
'''
NOTICE=b'''Original collector source: MIT (SPDX identifier in source/diag_init.c).
The executable is statically linked against the recorded glibc and GCC runtimes.
Common SPDX license texts and the installed GCC exception accompany it under
licenses/. These are not complete glibc-specific attribution or source closure.
The object was freshly compiled from the frozen source and relinked byte-equal
to the privately tested executable; evidence/relink.json records that control.
This local handoff is for the same user's own computers and is not a public
binary Release. Including an object and notices does not claim complete public
libc corresponding-source delivery. Do not upload the archive or binary/root.
Public source origins: https://sourceware.org/glibc/ and https://gcc.gnu.org/.
No host application or Apple code is included.
'''

def safe_name(name):
    if type(name) is not str or not re.fullmatch(r'[A-Za-z0-9_.+/-]{1,200}',name):raise p.Refusal('member_name')
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '.' in path.parts or path.as_posix()!=name or not name.startswith(p.ROOT):raise p.Refusal('member_path')
    return name

def validate_manifest(m):
    if type(m) is not dict or m.get('schema')!=SCHEMA or m.get('target')!=p.TARGET:raise p.Refusal('manifest_identity')
    if set(m)!={'schema','target','delivery','bindings','native_authorized','restart_ready','firmware_change_authorized','public_binary_release','package'}:raise p.Refusal('unknown_manifest_field')
    if m.get('delivery')!='SAME_USER_LOCAL_HANDOFF_ONLY' or not p.typed_equal(m.get('bindings'),p.BINDINGS):raise p.Refusal('manifest_binding')
    for name in ('native_authorized','restart_ready','firmware_change_authorized','public_binary_release'):
        if m.get(name) is not False:raise p.Refusal('not_offline_local_handoff')
    package=m.get('package')
    if type(package) is not dict or set(package)!={'filename','bytes','sha256','files'} or package.get('filename')!=FILENAME:raise p.Refusal('package_metadata')
    if type(package.get('bytes')) is not int or not 0<package['bytes']<=MAX_COMPRESSED or not re.fullmatch('[a-f0-9]{64}',str(package.get('sha256'))):raise p.Refusal('compressed_geometry')
    files=package.get('files')
    if type(files) is not dict or not len(p.REQUIRED)<=len(files)<=MAX_FILES:raise p.Refusal('member_inventory')
    short=set();total=0
    for name,record in files.items():
        safe_name(name);relative=name.removeprefix(p.ROOT);short.add(relative)
        if relative not in p.REQUIRED and relative not in {'licenses/'+n for n in p.NOTICE_PROVENANCE}:raise p.Refusal('file_allowlist')
        if type(record) is not dict or set(record)!={'bytes','sha256'} or type(record['bytes']) is not int or not 0<=record['bytes']<=MAX_FILE or not re.fullmatch('[a-f0-9]{64}',str(record['sha256'])):raise p.Refusal('member_metadata')
        total+=record['bytes']
    if not p.REQUIRED<=short or total>MAX_TOTAL:raise p.Refusal('missing_or_oversize_inventory')
    for name,digest in p.PINS.items():
        if files[p.ROOT+name]['sha256']!=digest:raise p.Refusal('manifest_frozen_pin')
    return package

def read_archive(path,package):
    """Strict single-gzip USTAR reader; bytes stay in bounded memory."""
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise p.Refusal('package_file')
    def stat(stream):
        s=os.fstat(stream.fileno());return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    with path.open('rb') as stream:
        before=stat(stream)
        if before[2]!=package['bytes'] or not 0<before[2]<=MAX_COMPRESSED:raise p.Refusal('package_size')
        compressed=stream.read(MAX_COMPRESSED+1)
        if stat(stream)!=before or len(compressed)!=package['bytes'] or p.sha(compressed)!=package['sha256']:raise p.Refusal('package_integrity')
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
    try:data=decoder.decompress(compressed,MAX_TOTAL+MAX_FILES*1024+10240+1)
    except zlib.error:raise p.Refusal('package_gzip_crc') from None
    if len(data)>MAX_TOTAL+MAX_FILES*1024+10240 or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise p.Refusal('package_gzip_bounds')
    at=0;files={};total=0
    while True:
        header=data[at:at+512];at+=512
        if len(header)!=512:raise p.Refusal('missing_tar_end')
        if header==bytes(512):
            if data[at:at+512]!=bytes(512):raise p.Refusal('missing_second_tar_end')
            at+=512;tail=data[at:]
            if len(tail)>10240 or len(tail)%512 or any(tail):raise p.Refusal('tar_trailing_payload')
            break
        if header[257:265]!=b'ustar\x0000' or header[156:157] not in (b'0',b'\0'):raise p.Refusal('nonregular_or_extension_header')
        for low,high in ((100,108),(108,116),(116,124),(124,136),(136,148),(148,156),(329,337),(337,345)):
            if any(c not in b'01234567 \0' for c in header[low:high]):raise p.Refusal('noncanonical_tar_number')
        if any(header[500:]):raise p.Refusal('nonzero_tar_reserved_bytes')
        try:member=tarfile.TarInfo.frombuf(header,'ascii','strict')
        except (tarfile.TarError,ValueError,UnicodeError):raise p.Refusal('tar_header') from None
        name=safe_name(member.name)
        if name in files or name not in package['files'] or len(files)>=MAX_FILES:raise p.Refusal('unexpected_or_duplicate_member')
        if member.linkname or member.issparse() or member.mode!=0o644 or member.uid or member.gid or member.uname or member.gname or member.devmajor or member.devminor:raise p.Refusal('tar_metadata')
        record=package['files'][name]
        if member.size!=record['bytes'] or not 0<=member.size<=MAX_FILE:raise p.Refusal('tar_member_size')
        end=at+member.size;pad=(-member.size)%512;total+=member.size
        if total>MAX_TOTAL or end+pad>len(data):raise p.Refusal('tar_payload_bounds')
        content=data[at:end]
        if any(data[end:end+pad]) or p.sha(content)!=record['sha256']:raise p.Refusal('tar_member_integrity')
        files[name]=content;at=end+pad
    if set(files)!=set(package['files']):raise p.Refusal('missing_member')
    return files,total

def review(manifest,archive,repo):
    package=validate_manifest(manifest);files,total=read_archive(archive,package)
    if files[p.ROOT+'README.txt']!=README or files[p.ROOT+'notices/local-use.txt']!=NOTICE:raise p.Refusal('local_delivery_notice')
    detail=p.validate_payloads(files,repo)
    return {'schema':'ilinux-direct31ai-review-result-v1','status':'OFFLINE_DIAGNOSTIC_INTEGRITY_PASS',
        'files_verified':len(files),'expanded_bytes':total,'package_sha256':package['sha256'],
        'read_only':True,'extracted':False,'executed':False,'device_opened':False,
        'native_ready':False,'native_authorized':False,'public_binary_release':False,
        'glibc_public_source_closure':'INCOMPLETE',**detail}

def build(repo,kernel,vm,relink,output,manifest):
    if output.exists() or manifest.exists() or output.name!=FILENAME:raise p.Refusal('existing_or_wrong_output')
    files={}
    def add(name,path):
        safe_name(p.ROOT+name)
        if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_FILE:raise p.Refusal('regular_bounded_input_required')
        files[p.ROOT+name]=path.read_bytes()
    for name,source in {'linux/Image':'Image','linux/kernel.config':'kernel.config',
        'linux/t6050-j716c-diagnostic.dtb':'t6050-j716c-diagnostic.dtb',
        'diagnostic/diag-init':'diag-init','diagnostic/initramfs.cpio.gz':'initramfs-direct31ah.cpio.gz',
        'evidence/source-bindings.json':'input-source-files.json'}.items():add(name,kernel/source)
    add('source/diag_init.c',repo/'kernel/experiments/direct31ah/linux/diag_init.c')
    add('evidence/vm.json',vm);add('evidence/relink.json',relink/'relink-result.json')
    add('relink/diag-init.o',relink/'diag-init.o')
    add('references/31ah-manifest.json',repo/'native/boot/attempt31ah/manifest.json')
    receipt=p.decode(files[p.ROOT+'evidence/relink.json']);notices=p.validate_relink(receipt)
    for name in notices:add('licenses/'+name,relink/'licenses'/name)
    for name,data in {'README.txt':README,'notices/local-use.txt':NOTICE,
                     'bindings.json':p.canonical(p.BINDINGS),'policy/storage.json':p.canonical(p.STORAGE)}.items():files[p.ROOT+name]=data
    p.validate_payloads(files,repo)
    output.parent.mkdir(parents=True,exist_ok=True);manifest.parent.mkdir(parents=True,exist_ok=True)
    entries={n:{'bytes':len(b),'sha256':p.sha(b)} for n,b in sorted(files.items())}
    # Stage each file on its destination filesystem. Publish only after full
    # validation, with no-clobber hard links and the manifest last. If the pair
    # cannot be completed, remove only the exact archive link we created.
    with tempfile.TemporaryDirectory(prefix='.31ai-tar-',dir=output.parent) as td, \
         tempfile.TemporaryDirectory(prefix='.31ai-manifest-',dir=manifest.parent) as md:
        staged=Path(td)/FILENAME;staged_manifest=Path(md)/'manifest.json'
        with staged.open('xb') as raw:
            with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=1794441600) as gz:
                with tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as tar:
                    for name,data in sorted(files.items()):
                        info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=1794441600
                        tar.addfile(info,io.BytesIO(data))
        package=staged.read_bytes()
        result={'schema':SCHEMA,'target':p.TARGET,'delivery':'SAME_USER_LOCAL_HANDOFF_ONLY',
            'native_authorized':False,'restart_ready':False,'firmware_change_authorized':False,
            'public_binary_release':False,'bindings':p.BINDINGS,
            'package':{'filename':FILENAME,'bytes':len(package),'sha256':p.sha(package),'files':entries}}
        validate_manifest(result);reviewed=review(result,staged,repo)
        staged_manifest.write_text(json.dumps(result,indent=2)+'\n')
        linked=False;complete=False
        try:
            os.link(staged,output);linked=True
            os.link(staged_manifest,manifest);complete=True
        finally:
            if linked and not complete:
                try:
                    if os.path.samefile(output,staged):output.unlink()
                except FileNotFoundError:pass
        return reviewed

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    default_repo=Path(__file__).resolve().parents[4]
    b=commands.add_parser('build');b.add_argument('--repo',type=Path,default=default_repo)
    for name in ('kernel-out','vm-receipt','relink-out','output','manifest'):b.add_argument('--'+name,type=Path,required=True)
    r=commands.add_parser('review');r.add_argument('--repo',type=Path,default=default_repo)
    r.add_argument('--manifest',type=Path,required=True);r.add_argument('--package',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='build':result=build(args.repo,args.kernel_out,args.vm_receipt,args.relink_out,args.output,args.manifest)
    else:
        if args.manifest.is_symlink() or args.manifest.stat().st_size>128*1024:raise p.Refusal('manifest_file')
        result=review(p.decode(args.manifest.read_bytes()),args.package,args.repo)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    try:main()
    except (p.Refusal,OSError,EOFError,UnicodeError,ValueError,KeyError,TypeError,RecursionError,tarfile.TarError):
        print(json.dumps({'status':'REFUSED','read_only':True,'extracted':False,'executed':False,'native_ready':False}))
        raise SystemExit(2)
