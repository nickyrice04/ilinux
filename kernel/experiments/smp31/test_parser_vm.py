#!/usr/bin/env python3
"""Exercise the real pinned ADT parser with synthetic non-identifying metadata.

Run inside the VM: python3 -I test_parser_vm.py /mnt/m1n1-source/proxyclient
"""
import importlib.util
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

sys.path.insert(0, sys.argv[1])
from m1n1.adt import ADTNodeStruct
s = importlib.util.spec_from_file_location('census', Path(__file__).resolve().parents[3] / 'native/boot/smp31_census.py')
c = importlib.util.module_from_spec(s)
s.loader.exec_module(c)


def node(name, properties, children=()):
    properties = {'name': name.encode()+b'\0', **properties}
    props = [dict(name=k, size=len(v), value=v) for k, v in properties.items()]
    return dict(property_count=len(props), child_count=len(children), properties=props, children=list(children))


cpus=[]
for i in range(18):
    cpus.append(node('cpu%d' % i, {
        'cpu-id': struct.pack('<I', i), 'reg': struct.pack('<I', (i//6)<<8 | i%6),
        'cpu-impl-reg': struct.pack('<QQ',0x210050000+(i//6)*0x1000000+(i%6)*0x100000,0x9018),
        'cluster-type': b'M\0' if i < 12 else b'P\0',
        'state': b'running\0' if i==0 else b'waiting\0'}))
root=node('device-tree', {'compatible':b'J716cAP\0'}, [node('cpus', {}, cpus),
     node('arm-io', {}, [node('pmgr', {'compatible':b'pmgr,t6050\0',
         'devices': bytes(96), 'clusters':struct.pack('<6H',6,0,6,6,6,12)})])])
raw=ADTNodeStruct.build(root)


class Fake:
    revision = 3
    def get_bootargs_rev(self): return 0x800001000, self.revision
    def readstruct(self, addr, schema):
        assert addr == 0x800001000
        return SimpleNamespace(devtree_size=len(raw), devtree=0x800010000,
            virt_base=0x800000000, phys_base=0x800000000, mem_size=0x100000)
    def readmem(self, addr, size):
        assert (addr,size)==(0x800010000,len(raw))
        return raw


f=Fake()
c.read_metadata(f,f)
f.revision=2
c.read_metadata(f,f)
f.revision=4
try:
    c.read_metadata(f,f)
except c.CensusRefusal:
    pass
else:
    raise AssertionError('unknown revision admitted')
print('REAL-ADT-PARSER-PASS: synthetic 18-CPU board, no USB, no target writes')
