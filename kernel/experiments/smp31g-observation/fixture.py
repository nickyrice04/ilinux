# SPDX-License-Identifier: MIT
"""Original literal synthetic ADT fixture, never captured Apple data."""
import importlib.util
from pathlib import Path
import struct
spec=importlib.util.spec_from_file_location('ram_fixture',Path(__file__).resolve().parents[1]/'smp31/memory_fixture31c.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
u32=lambda v:struct.pack('<I',v)
u64=lambda v:struct.pack('<Q',v)


def adt():
    cpus=[]
    for i in range(18):
        cluster,core=divmod(i,6)
        cpus.append(f.node({'name':('cpu'+str(i)).encode()+b'\0',
            'cpu-id':u32(i), 'reg':u32(cluster<<8|core),
            'cluster-id':u32(cluster), 'die-cluster-id':u32(cluster),
            'cluster-core-id':u32(core)}))
    devices=[]
    for i in range(2):
        row=bytearray(48)
        struct.pack_into('<H',row,26,i+1)
        row[16:19]=(i*8).to_bytes(3,'little')
        name=('MCPU0_'+str(i)).encode();row[32:32+len(name)]=name
        devices.append(bytes(row))
    pmgr=f.node({'name':b'pmgr\0','compatible':b'pmgr,t6050\0',
        'reg':struct.pack('<QQ',0x280600000,0x4000),
        'devices':b''.join(devices),'ps-groups':struct.pack('<III',0,0,0),
        'edt-property-ver':u32(2),
        'acc-cores':b''.join(struct.pack('<IBBBB',i+1,0,i,i%6,i//6) for i in range(18))})
    arm=f.node({'name':b'arm-io\0','#address-cells':u32(2),'#size-cells':u32(2),
                'ranges':struct.pack('<QQQ',0,0,1<<40)},[pmgr])
    chosen=f.node({'name':b'chosen\0','dram-base':u64(f.DRAM_BASE),'dram-size':u64(f.DRAM_SIZE)})
    return f.node({'name':b'device-tree\0','#address-cells':u32(2),'#size-cells':u32(2)},
                  [f.node({'name':b'cpus\0'},cpus),arm,chosen])
