#!/usr/bin/env python3
"""Resolve boot021 UART loads/zero-return branches from its exact public image.

Pure offline parsing; no target or downloaded-code execution. The behavioral
UART harness separately compiles the digest-pinned public source in the VM.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

IMAGE_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
SOURCES = {
 'uart.c':'1dfdb722238ed1f28eb544291c8fc70a407c2387d9a0c323188282de08dc0a81',
 'dockchannel_uart.c':'452639469ad946d3d33c2d7b6e9db081205c6cadf639d8776eac69299da45949',
 'iodev.c':'b5966d13f018761bd2bf051a4e4e4c25ac2f9775b66c06e917ac1440568e15f2',
 'iodev.h':'1210a80029f3b99a89f4fb880a10e2389bed0139e3e1db9d7c389cdcb9fa90df',
}

def require(ok, why):
    if not ok: raise ValueError(why)


def signed(value,bits):
    return value-(1<<bits) if value & (1<<(bits-1)) else value


def resolve(image,start,expected,ret):
    words=struct.unpack_from('<16I',image,start)
    adrp,load,cbz=words[0],words[2],words[3]
    require(adrp & 0x9f000000 == 0x90000000,'ADRP')
    page=(start & ~4095)+(signed(((adrp>>29)&3)|(((adrp>>5)&0x7ffff)<<2),21)<<12)
    require(load & 0xffc00000 == 0xf9400000,'LDR64')
    require((load>>5)&31 == adrp&31,'base register')
    target=page+((load>>10)&0xfff)*8
    require(target==expected,'RAM variable offset')
    require(cbz & 0xff000000 == 0xb4000000 and cbz&31 == load&31,'CBZ64')
    destination=start+12+signed((cbz>>5)&0x7ffff,19)*4
    require(destination==ret and struct.unpack_from('<I',image,ret)[0]==0xd65f03c0,'zero returns')
    return {'function_offset':hex(start),'ram_variable_offset':hex(target),
            'zero_return_offset':hex(destination),'zero_returns_before_mmio':True}


def audit(image,source):
    require(hashlib.sha256(image).hexdigest()==IMAGE_SHA,'image digest')
    for name,digest in SOURCES.items():
        require(hashlib.sha256((source/'src'/name).read_bytes()).hexdigest()==digest,'source '+name)
    return {'image_sha256':IMAGE_SHA,'source_sha256':SOURCES,
        'functions':[resolve(image,0x347a0,0x35a4a0,0x347c8),
                     resolve(image,0x1a360,0x110030,0x1a39c)],
        'result':'OFFLINE_CONSOLE_BINDING_PASS','native_cpu1':'NOT RUN'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(audit(a.image.read_bytes(),a.source),indent=2))
