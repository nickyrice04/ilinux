#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a deterministic, RAM-only initramfs containing one static init."""
import gzip
import hashlib
import json
import struct
import sys
from pathlib import Path

def newc_entry(name,data,mode,ino):
    encoded=name.encode('ascii')+b'\0'
    fields=[ino,mode,0,0,1,0,len(data),0,0,0,0,len(encoded),0]
    head=b'070701'+b''.join(f'{v:08x}'.encode() for v in fields)
    out=head+encoded;out+=b'\0'*(-len(out)%4);out+=data;out+=b'\0'*(-len(data)%4)
    return out

def build(exe):
    if len(exe)<64 or exe[:4]!=b'\x7fELF' or exe[4]!=2 or exe[5]!=1:
        raise ValueError('need ELF64 little endian')
    if struct.unpack_from('<H',exe,18)[0]!=183:raise ValueError('need AArch64')
    if struct.unpack_from('<H',exe,16)[0] not in (2,3) or struct.unpack_from('<H',exe,52)[0]!=64:
        raise ValueError('invalid ELF executable header')
    phoff=struct.unpack_from('<Q',exe,32)[0];phsize,phnum=struct.unpack_from('<HH',exe,54)
    if phsize!=56 or not 1<=phnum<=128 or phoff<64 or phoff+phsize*phnum>len(exe):raise ValueError('bad program table')
    loads=0
    for i in range(phnum):
        ptype,_,offset,_,_,size,memsize,_=struct.unpack_from('<2I6Q',exe,phoff+i*phsize)
        if ptype==3:
            raise ValueError('init must be statically linked')
        if ptype==1:
            loads+=1
            if offset+size>len(exe) or size>memsize:raise ValueError('invalid load segment')
    if not loads:raise ValueError('missing executable load segment')
    buf=bytearray();ino=1
    for name in ('dev','proc','sys','run'):
        buf+=newc_entry(name,b'',0o040755,ino);ino+=1
    buf+=newc_entry('init',exe,0o100755,ino);ino+=1
    buf+=newc_entry('TRAILER!!!',b'',0,ino)
    return gzip.compress(bytes(buf),compresslevel=9,mtime=0)

if __name__=='__main__':
    source,target=map(Path,sys.argv[1:])
    if source.resolve()==target.resolve():raise ValueError('use separate output')
    out=build(source.read_bytes());target.write_bytes(out)
    print(json.dumps({'scope':'OFFLINE_RAM_INITRAMFS','entries':['dev','proc','sys','run','init'],
        'static_aarch64_init':True,'storage_modules':False,'private_keys':False,
        'bytes':len(out),'sha256':hashlib.sha256(out).hexdigest(),'native_qualified':False}))
