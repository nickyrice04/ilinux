#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Review the local-user 31AJ files in memory; never extract, execute or install."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import tarfile
import zlib

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
PREFIX='ilinux31aj/'
SCHEMA='ilinux31aj-kit-v1'
TARGET={'model':'Mac17,6','board':'j716c','chip_id':'0x6050'}
MIB=1024*1024
MEMBERS={'linux/Image','linux/kernel.config','linux/diagnostic.dtb',
 'diagnostic/init','diagnostic/initramfs.cpio.gz','source/diag_init.c','source/readable.h',
 'relink/diag-init.o','evidence/build.json','evidence/vm.json','notices/local-use.txt',
 'licenses/common/LGPL-2.1-or-later.txt','licenses/common/GPL-2.0-only.txt',
 'licenses/common/GPL-3.0-or-later.txt','licenses/gcc/RUNTIME.LIBRARY.EXCEPTION'}
HELPERS={
 'kernel/experiments/direct31ai/transport/inline.py':'774b3ea5561a6b907974932a939282514b756997e1b8645a4b91407a4601c9f0',
 'kernel/experiments/direct31ai/transport/extend_exec.py':'8cb2b0acc68655ed7293fa8e4662a6650177c4d14ce5642c275c7fcbb29f5da8',
 'kernel/experiments/direct31ah/aura/pad_boot.py':'0f3b95bc1075c35916963c30c37c4eee6642c2cae95f264ac4744154c84b6acf',
 'kernel/experiments/direct31ah/linux/fdt_read.py':'97e897fdf12de19afa26a2303b0bcc7377cc28d1078577930f275eca1b590935',
 'kernel/experiments/direct31ah/linux/check_dtb.py':'24b4068bf4be5a5680e4ddab710a2e1fa68ec49794bb12e0b615abec7fcae5c9',
 'kernel/experiments/direct31ah/linux/check_config.py':'2ef1cfcf2e65726e9ac559329544c8ec6c700fb4a77c7d6ac86804eec507ceb6'}
KERNEL_PINS={'linux/Image':'c01483f230aa64013b395291f8a5b8e38ed6c467b61e8a141c621938fda3a56f',
 'linux/kernel.config':'bba7ce251238c3cb6779d884a3442373443f7eed97e19f638afc08fdb9779fd8',
 'linux/diagnostic.dtb':'2c93df25dcbbc6939360ca84b76e21246ca30b6b7e2d0189afb0b1978332cb51'}
BASELINE='2d272aa2b5551d27458826e88b3bdaf86684e2b4fff3aad4876de7021a1caaf3'
BASELINE_BYTES=3997696
ROLLBACK_BYTES=3932160
ROLLBACK_SHA='ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
NOTICE=b'''31AJ SAME-USER LOCAL REVIEW ONLY\nOriginal readable collector; exact prior kernel/DT; no Apple firmware or media.\nStatic glibc public source/notice closure remains INCOMPLETE. No public binary release.\nRAM/pseudo filesystems only; no Linux storage module or block-device open requested.\nAura controller handoff still has real hardware effects. Native performance unmeasured.\nNo installation or boot authorization follows from receiving or verifying these files.\n'''

class Refusal(ValueError):pass
def need(value,reason):
    if not value:raise Refusal(reason)
def sha(data):return hashlib.sha256(data).hexdigest()
def exact_keys(value,keys):need(type(value) is dict and set(value)==set(keys),'FIELDS')
def pairs(items):
    result={}
    for k,v in items:need(k not in result,'DUPLICATE_JSON');result[k]=v
    return result
def decode(data):
    need(type(data) is bytes and len(data)<=256*1024,'JSON_BOUND')
    try:return json.loads(data,object_pairs_hook=pairs)
    except (UnicodeError,ValueError,RecursionError):raise Refusal('JSON') from None
def regular(path,bound):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and 0<before.st_size<=bound,'FILE_BOUND')
        with os.fdopen(fd,'rb',closefd=False) as stream:data=stream.read(bound+1)
        after=os.fstat(fd);stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(len(data)==before.st_size and stamp(before)==stamp(after),'FILE_CHANGED');return data
    finally:os.close(fd)
def metadata(data):return {'bytes':len(data),'sha256':sha(data)}
def record(item,limit,filename=None):
    exact_keys(item,{'bytes','sha256'}|({'filename'} if filename else set()))
    need(type(item['bytes']) is int and 0<item['bytes']<=limit and
         type(item['sha256']) is str and re.fullmatch('[a-f0-9]{64}',item['sha256']),'METADATA')
    if filename:need(item['filename']==filename,'FILENAME')
def checked_file(path,item,limit):
    data=regular(path,limit);need(metadata(data)=={k:item[k] for k in ('bytes','sha256')},'IDENTITY');return data
def gunzip(data,bound):
    d=zlib.decompressobj(31)
    try:out=d.decompress(data,bound+1)
    except zlib.error:raise Refusal('GZIP') from None
    need(len(out)<=bound and d.eof and not d.unused_data and not d.unconsumed_tail,'GZIP_BOUNDARY');return out

def manifest(m):
    exact_keys(m,{'schema','target','delivery','native_authorized','restart_ready','public_binary_release',
                 'libc_source_closure','candidate','runtime','readback','sources'})
    need(m['schema']==SCHEMA and type(m['target']) is dict and m['target']==TARGET,'TARGET')
    need(m['delivery']=='SAME_USER_LOCAL_HANDOFF_ONLY' and m['libc_source_closure']=='INCOMPLETE','DELIVERY')
    need(all(m[k] is False for k in ('native_authorized','restart_ready','public_binary_release')),'AUTHORITY')
    c=m['candidate'];exact_keys(c,{'filename','bytes','sha256','expanded_bytes','expanded_sha256','raw_bytes','raw_sha256'})
    record({k:c[k] for k in ('filename','bytes','sha256')},32*MIB,'aura-31aj-inline.macho.gz')
    need(type(c['expanded_bytes']) is int and 0<c['expanded_bytes']<=160*MIB and
         type(c['raw_bytes']) is int and BASELINE_BYTES<c['raw_bytes']<=32*MIB,'CANDIDATE_BOUND')
    need(all(type(c[k]) is str and re.fullmatch('[a-f0-9]{64}',c[k]) for k in ('expanded_sha256','raw_sha256')),'CANDIDATE_HASH')
    r=m['runtime'];exact_keys(r,{'filename','bytes','sha256','members'})
    record({k:r[k] for k in ('filename','bytes','sha256')},32*MIB,'runtime-31aj.tar.gz')
    exact_keys(r['members'],MEMBERS)
    total=0
    for name,item in r['members'].items():record(item,48*MIB);total+=item['bytes']
    need(total<=64*MIB,'RUNTIME_BOUND')
    for name,digest in KERNEL_PINS.items():need(r['members'][name]['sha256']==digest,'UNCHANGED_KERNEL')
    record(m['readback'],2*MIB,'readback31aj')
    need(type(m['sources']) is dict and set(HELPERS)<=set(m['sources']) and len(m['sources'])<=32,'SOURCES')
    for name,digest in m['sources'].items():
        need(type(name) is str and re.fullmatch('[A-Za-z0-9_.+/-]+',name) and
             not name.startswith('/') and all(x not in ('','.','..') for x in name.split('/')),'SOURCE_PATH')
        need(type(digest) is str and re.fullmatch('[a-f0-9]{64}',digest),'SOURCE_HASH')
    need(all(m['sources'][n]==v for n,v in HELPERS.items()),'FROZEN_HELPER');return m

def archive(data,records):
    plain=gunzip(data,65*MIB);need(len(plain)%512==0,'TAR_ALIGN');at=0;out={}
    while True:
        h=plain[at:at+512];at+=512;need(len(h)==512,'TAR_END')
        if h==bytes(512):
            need(plain[at:at+512]==bytes(512) and len(plain)-at<=10240 and not any(plain[at:]),'TAR_TAIL');break
        need(h[257:265]==b'ustar\x0000' and h[156:157] in (b'0',b'\0') and not any(h[500:]),'TAR_FORMAT')
        for lo,hi in ((100,108),(108,116),(116,124),(124,136),(136,148),(148,156),(329,337),(337,345)):
            need(all(c in b'01234567 \0' for c in h[lo:hi]),'TAR_NUMERIC')
        try:t=tarfile.TarInfo.frombuf(h,'ascii','strict')
        except (tarfile.TarError,ValueError,UnicodeError):raise Refusal('TAR_HEADER') from None
        need(t.name.startswith(PREFIX),'MEMBER_PREFIX');name=t.name[len(PREFIX):]
        need(name in MEMBERS and name not in out and len(out)<len(MEMBERS),'MEMBER_SET')
        need(not t.linkname and not t.issparse() and t.mode==0o644 and not any((t.uid,t.gid,t.devmajor,t.devminor,t.mtime))
             and not t.uname and not t.gname,'TAR_METADATA')
        need(t.size==records[name]['bytes'] and 0<t.size<=48*MIB,'MEMBER_SIZE')
        end=at+t.size;pad=(-t.size)%512;need(end+pad<=len(plain) and not any(plain[end:end+pad]),'MEMBER_BOUND')
        content=plain[at:end];need(sha(content)==records[name]['sha256'],'MEMBER_HASH');out[name]=content;at=end+pad
    need(set(out)==MEMBERS,'MISSING_MEMBER');return out

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

def inspect_payloads(files,m,candidate,repo):
    for name,digest in m['sources'].items():need(sha(regular(repo/name,2*MIB))==digest,'SOURCE_CHANGED')
    extended=load_module('kit31aj_extended',repo/'kernel/experiments/direct31ai/transport/extend_exec.py')
    pad,inline=extended.pad,extended.inline
    info=pad.inspect(candidate);code=info['code'];c=m['candidate']
    need(code['off']==0x10000 and code['size']==pad.CODE_SIZE,'EXEC_GEOMETRY')
    raw=candidate[code['off']:code['off']+c['raw_bytes']]
    need(len(raw)==c['raw_bytes'] and sha(raw)==c['raw_sha256'] and sha(raw[:BASELINE_BYTES])==BASELINE,'BASELINE_OR_RAW')
    need(struct.unpack_from('<Q',raw,0x818)[0]==BASELINE_BYTES and
         not any(candidate[code['off']+len(raw):code['off']+code['size']]),'RUNTIME_OR_PADDING')
    extended.wrapper_identity(candidate,raw,info)
    inline.verify_payload(raw[BASELINE_BYTES:],files['linux/Image'],files['linux/diagnostic.dtb'],files['diagnostic/initramfs.cpio.gz'])
    init=files['diagnostic/init']
    need(inline.initrd_info(files['diagnostic/initramfs.cpio.gz'])['init']==metadata(init),'INIT_BYTES')
    need(files['notices/local-use.txt']==NOTICE,'NOTICE')
    for name in ('diagnostic/init','relink/diag-init.o'):
        b=files[name];kind=2 if name=='diagnostic/init' else 1
        need(len(b)>64 and b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',b,16)==(kind,183),'ELF')
        if kind==2:
            off=struct.unpack_from('<Q',b,32)[0];width,count=struct.unpack_from('<HH',b,54)
            need(width==56 and 1<=count<=128 and off>=64 and off+width*count<=len(b),'ELF_PROGRAM_TABLE')
            need(all(struct.unpack_from('<I',b,off+i*width)[0]!=3 for i in range(count)),'ELF_INTERPRETER')
    build=decode(files['evidence/build.json']);vm=decode(files['evidence/vm.json'])
    need(type(build) is dict and type(vm) is dict,'EVIDENCE_OBJECT')
    need(build.get('status')=='PASS' and build.get('schema')=='ilinux31aj-readable-build-v1' and
         build.get('relink_equal_to_direct_build') is True and build.get('normal_selftest')=='PASS' and
         build.get('intentional_timeout_selftest')=='PASS' and build.get('native_tested') is False,'BUILD')
    for name,source in (('diag_init.c','source/diag_init.c'),('readable.h','source/readable.h')):
        need(sha(files[source])==build['source_binding']['files'][name] and files[source]==regular(repo/'kernel/experiments/direct31aj'/name,256*1024),'COLLECTOR_SOURCE')
    need(build['files']['diag-init']==metadata(init) and build['files']['diag-init.o']==metadata(files['relink/diag-init.o']) and
         build['files']['initramfs-direct31aj.cpio.gz']==metadata(files['diagnostic/initramfs.cpio.gz']),'BUILD_BYTES')
    need(vm.get('status')=='PASS' and vm.get('scope')=='GENERIC_ARM64_VZ_CONTROL' and
         vm.get('passing_cpu_ids')==[0,1,2,3] and all(type(v) is int for v in vm['passing_cpu_ids']) and
         type(vm.get('elapsed_monotonic_ns')) is int and 60_000_000_000<=vm['elapsed_monotonic_ns']<=(1<<64)-1 and
         vm.get('physical_m5_tested') is False,'VM_SCOPE')
    need(vm.get('tested_inputs')=={n:metadata(files[n]) for n in
         ('linux/Image','diagnostic/initramfs.cpio.gz','diagnostic/init')},'VM_INPUT_BINDING')
    return {'segments':len(info['segments']),'embedded_root_verified':True,'unchanged_kernel_verified':True,'generic_vm_seconds':vm['elapsed_monotonic_ns']/1e9}

def review(m,folder,repo=ROOT):
    manifest(m);folder=Path(folder);repo=Path(repo)
    compressed=checked_file(folder/m['candidate']['filename'],m['candidate'],32*MIB)
    candidate=gunzip(compressed,160*MIB);need(len(candidate)==m['candidate']['expanded_bytes'] and sha(candidate)==m['candidate']['expanded_sha256'],'EXPANDED_IDENTITY')
    records=m['runtime']['members'];contents=archive(checked_file(folder/m['runtime']['filename'],m['runtime'],32*MIB),records)
    helper=checked_file(folder/m['readback']['filename'],m['readback'],2*MIB)
    need(len(helper)>=32 and struct.unpack_from('<II',helper)==(0xfeedfacf,0x100000c),'READBACK_ARCH')
    rollback=regular(folder/'m1n1-boot021.bin',ROLLBACK_BYTES)
    need(len(rollback)==ROLLBACK_BYTES and sha(rollback)==ROLLBACK_SHA,'ROLLBACK_IDENTITY')
    detail=inspect_payloads(contents,m,candidate,repo)
    return {'schema':'ilinux31aj-kit-review-v1','status':'OFFLINE_KIT_INTEGRITY_PASS','read_only':True,
      'files_verified':4,'runtime_members':len(contents),'rollback_artifact_verified':True,'extracted':False,'executed':False,
      'device_opened':False,'native_ready':False,'native_authorized':False,'public_binary_release':False,**detail}

def build_archive(files,path):
    need(set(files)==MEMBERS,'MEMBER_SET');buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as archive_out:
        for name in sorted(files):
            data=files[name];info=tarfile.TarInfo(PREFIX+name);info.size=len(data);info.mode=0o644;info.mtime=0
            archive_out.addfile(info,io.BytesIO(data))
    compressor=zlib.compressobj(9,zlib.DEFLATED,31);blob=compressor.compress(buffer.getvalue())+compressor.flush()
    need(len(blob)<=32*MIB,'ARCHIVE_BOUND')
    with Path(path).open('xb') as stream:stream.write(blob)
    return metadata(blob),{name:metadata(data) for name,data in files.items()}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--folder',type=Path,required=True)
    args=parser.parse_args()
    try:result=review(decode(regular(args.manifest,256*1024)),args.folder)
    except (ValueError,OSError,KeyError,TypeError,struct.error,EOFError):
        result={'status':'REFUSED','read_only':True,'extracted':False,'executed':False,'native_ready':False}
    print(json.dumps(result,sort_keys=True));return 0 if result['status']=='OFFLINE_KIT_INTEGRITY_PASS' else 2
if __name__=='__main__':raise SystemExit(main())
