#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline known-payload identity primitive; no live reads, codecs or writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
MIB=1024*1024
MAX_RAW=160*MIB
MAX_COMPRESSED=32*MIB
MAX_OPAQUE=64*1024
KNOWN={
 '31AI':(153190400,'0d43feada6d758fcfea2ce78b4fd9f21ae4b7a7450ab06ba9e8c6c06b834dc4d'),
 'BOOT021':(3932160,'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'),
 '31AF':(442368,'166bea74bf515473057dfd29dc89127d04768945a451e497cc80a9fc53d4951b')}
PIN_SOURCES={
 'native/boot/attempt31ai/candidate-manifest.json':'b925270559b58a3ff27e4fd955d124b0c7bf3fc193b408e9a8de5c43f5cac8cb',
 'tools/boot-object31ag/read_selected.py':'0728fae7dd30fd2ef14dacdf9e25028614f239c254c8fc40c3f8866fde32dc47'}

class Refusal(ValueError):pass
def need(ok,code):
    if not ok:raise Refusal(code)
def known_label(data):
    candidates=[label for label,(size,_) in KNOWN.items() if len(data)==size]
    digest=hashlib.sha256(data).hexdigest() if candidates else None
    return next((label for label in candidates if digest==KNOWN[label][1]),'UNKNOWN')

def header(data,pos,end):
    need(0<=pos and pos+2<=end<=len(data),'DER_BOUNDS')
    tag=data[pos];need(tag!=0 and tag&31!=31,'DER_TAG')
    length=data[pos+1];start=pos+2
    if length&128:
        count=length&127
        need(1<=count<=4 and start+count<=end and data[start]!=0,'DER_LENGTH')
        length=int.from_bytes(data[start:start+count],'big');start+=count
        need(length>=128,'DER_LENGTH')
    stop=start+length;need(stop<=end,'DER_BOUNDS')
    return tag,start,stop

def fields(data,start,end,limit):
    result=[]
    while start<end:
        need(len(result)<limit,'DER_FIELDS')
        item=header(data,start,end);result.append(item);start=item[2]
    need(start==end,'DER_BOUNDS')
    return result

def text(data,node,limit=4096):
    tag,start,end=node;need(tag==0x16,'DER_TEXT')
    need(end-start<=limit,'DER_TEXT_BOUND')
    value=data[start:end];need(all(c<128 for c in value),'DER_TEXT')
    return value

def number(data,node):
    tag,start,end=node;value=data[start:end]
    need(tag==2 and 1<=len(value)<=9 and not value[0]&128,'DER_INTEGER')
    need(len(value)==1 or value[0]!=0 or value[1]&128,'DER_INTEGER')
    return int.from_bytes(value,'big')

def framed(data):
    tag,start,end=header(data,0,len(data))
    need(tag==0x30 and end==len(data),'DER_ROOT_OR_TRAILER')
    nodes=fields(data,start,end,7);need(nodes,'DER_FIELDS')
    magic=text(data,nodes[0],4);opaque=False;kind='IM4P'
    if magic==b'IMG4':
        need(2<=len(nodes)<=4 and nodes[1][0]==0x30,'IMG4_FIELDS')
        tags=[n[0] for n in nodes[2:]]
        need(tags in ([],[0xa0],[0xa1],[0xa0,0xa1]),'IMG4_CONTEXTS')
        need(all(n[2]-n[1]<=MAX_OPAQUE for n in nodes[2:]),'OPAQUE_SIZE')
        opaque=bool(tags);kind='IMG4'
        nodes=fields(data,nodes[1][1],nodes[1][2],7)
        need(nodes and text(data,nodes[0],4)==b'IM4P','IM4P_MAGIC')
    else:need(magic==b'IM4P','IM4P_MAGIC')
    need(4<=len(nodes)<=7,'IM4P_FIELDS')
    ptype=text(data,nodes[1],4);description=text(data,nodes[2])
    need(len(ptype)==4 and all(32<=c<127 for c in ptype) and len(description)<=4096,'IM4P_METADATA')
    need(nodes[3][0]==4,'IM4P_PAYLOAD')
    extra=nodes[4:];keybag=False;declared=None
    if extra and extra[-1][0]==0xa0:
        need(extra[-1][2]-extra[-1][1]<=MAX_OPAQUE,'OPAQUE_SIZE')
        opaque=True;extra=extra[:-1]
    if extra and extra[0][0]==4:
        need(extra[0][2]-extra[0][1]<=MAX_OPAQUE,'OPAQUE_SIZE')
        keybag=True;extra=extra[1:]
    if extra:
        need(len(extra)==1 and extra[0][0]==0x30,'IM4P_EXTRA_ORDER')
        integers=fields(data,extra[0][1],extra[0][2],2)
        need(len(integers)==2 and number(data,integers[0])==1,'COMPRESSION_METADATA')
        declared=number(data,integers[1]);need(0<declared<=MAX_RAW,'DECLARED_SIZE')
    payload=nodes[3]
    return data[payload[1]:payload[2]],kind,keybag,opaque,declared

def family(data):
    if data.startswith(b'\x1f\x8b\x08'):return 'GZIP'
    if data[:4] in (b'bvx2',b'bvx1',b'bvx-',b'bvxn',b'bvx$'):return 'LZFSE_MAGIC'
    if data.startswith(b'complzss'):return 'UNSUPPORTED_LZSS_MAGIC'
    return 'NONE_RECOGNIZED'

def report(data):
    return {'schema':'ilinux31aj-offline-payload-v1','scope':'OFFLINE_KNOWN_PAYLOAD_IDENTITY_ONLY',
      'read_only':True,'status':'UNKNOWN','reason':'NOT_KNOWN','payload_label':'UNKNOWN',
      'input_bytes':len(data) if type(data) is bytes else 0,'payload_bytes':0,
      'framing':'RAW','compression':'NONE_RECOGNIZED','declared_output_bytes':None,
      'opaque_metadata_present':False,'keybag_present':False,'injected_codec_used':False,
      'decompressed':False,'decrypted':False,'container_authenticity_verified':False,
      'opaque_semantics_verified':False,'selection_verified':False,'restoration_verified':False,
      'bootability_verified':False,'write_authorized':False}

def inspect_payload(data,codec=None):
    """codec(family, encoded_bytes, exact_output_limit)->(bytes,consumed,eof).

    The trusted injected provider must bound its allocation/work and certify EOF.
    No provider is supplied by this module or accepted from CLI input.
    """
    result=report(data)
    try:
        need(type(data) is bytes and 0<len(data)<=MAX_RAW,'INPUT_BOUND')
        label=known_label(data)
        if label!='UNKNOWN':
            result.update(status='EXACT_KNOWN_PAYLOAD',reason='EXACT_BYTES',payload_label=label,payload_bytes=len(data));return result
        payload=data;declared=None
        if data[:1]==b'\x30':
            payload,kind,keybag,opaque,declared=framed(data)
            result.update(framing=kind,keybag_present=keybag,opaque_metadata_present=opaque,
                          declared_output_bytes=declared)
        result['payload_bytes']=len(payload);compression=family(payload);result['compression']=compression
        if result['keybag_present']:
            need(len(data)<=MAX_COMPRESSED,'COMPRESSED_INPUT_BOUND')
            result['reason']='OPAQUE_KEYBAG_BLOCKED';return result
        if compression=='NONE_RECOGNIZED':
            if declared is not None:raise Refusal('COMPRESSION_METADATA_CONFLICT')
        else:
            need(len(data)<=MAX_COMPRESSED,'COMPRESSED_INPUT_BOUND')
            if compression=='UNSUPPORTED_LZSS_MAGIC':result['reason']='CODEC_UNSUPPORTED';return result
            if compression=='GZIP':
                need(declared is None and len(payload)>=18,'COMPRESSION_METADATA_CONFLICT')
                declared=int.from_bytes(payload[-4:],'little')
                need(0<declared<=MAX_RAW,'DECLARED_SIZE');result['declared_output_bytes']=declared
            if declared not in {size for size,_ in KNOWN.values()}:
                result['reason']='DECLARED_SIZE_NOT_KNOWN';return result
            if codec is None:result['reason']='INJECTED_CODEC_REQUIRED';return result
            result['injected_codec_used']=True
            try:decoded=codec(compression,payload,declared)
            except Exception:raise Refusal('CODEC_FAILED') from None
            need(type(decoded) is tuple and len(decoded)==3,'CODEC_CONTRACT')
            content,consumed,eof=decoded
            need(type(content) is bytes and len(content)==declared and len(content)<=MAX_RAW and
                 type(consumed) is int and consumed==len(payload) and eof is True,'CODEC_BOUNDARY')
            payload=content;result.update(decompressed=True,payload_bytes=len(payload))
        label=known_label(payload)
        if label!='UNKNOWN':result.update(status='EXACT_KNOWN_PAYLOAD',reason='EXACT_BYTES',payload_label=label)
        return result
    except Refusal as error:
        result.update(status='REFUSED',reason=error.args[0],payload_label='UNKNOWN');return result

def read_workspace(path,limit):
    path=Path(path).absolute();need(ROOT in path.parents,'WORKSPACE_ONLY')
    parts=os.fspath(path).split('/')[1:];need(all(p not in ('','.','..') for p in parts),'PATH_COMPONENT')
    flags=os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK
    fd=os.open('/',flags|os.O_DIRECTORY)
    try:
        for i,part in enumerate(parts):
            child=os.open(part,flags|(os.O_DIRECTORY if i<len(parts)-1 else 0),dir_fd=fd)
            os.close(fd);fd=child
        with os.fdopen(fd,'rb',closefd=False) as stream:
            before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and 0<before.st_size<=limit,'FILE_BOUND')
            data=stream.read(limit+1);after=os.fstat(fd)
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(len(data)==before.st_size and stamp(before)==stamp(after),'FILE_CHANGED');return data
    finally:os.close(fd)

def verify_pin_sources():
    for name,digest in PIN_SOURCES.items():
        need(hashlib.sha256(read_workspace(ROOT/name,65536)).hexdigest()==digest,'FROZEN_PIN_SOURCE_CHANGED')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path)
    args=parser.parse_args(argv)
    if args.fixture is None:parser.print_help();return 0
    try:
        verify_pin_sources();result=inspect_payload(read_workspace(args.fixture,MAX_RAW))
    except Exception:
        result=report(b'');result.update(status='REFUSED',reason='WORKSPACE_FIXTURE_REFUSED')
    print(json.dumps(result,sort_keys=True));return 2 if result['status']=='REFUSED' else 0

if __name__=='__main__':raise SystemExit(main())
