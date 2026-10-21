#!/usr/bin/env python3
"""Actual pinned serializers/BootArgs/ADT with the 31D high-address model."""
import importlib.util
from pathlib import Path
import struct
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
client=sys.argv[1]
sys.path.insert(0,client)
sys.path.insert(0,str(HERE.parents[2]/'native/boot'))
# Ensure imported test fixtures use real parsers, never their host-only stand-in.
sys.argv.extend(['--real-parser',client])
import test_smp31d as tests
import smp31d as c
from m1n1.proxy import M1N1Proxy, UartInterface


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


old=load('old_client',HERE/'test_client31b_vm.py')
fx=tests.prior.fx


class Wire(tests.Fake,old.Wire):
    def __init__(self):
        tests.Fake.__init__(self)
        self.packets=[];self.ba=fx.bootargs();self.adt=fx.adt()
    def proxyreq(self,packet,**kwargs):
        opcode,*args=struct.unpack('<7Q',packet)
        if opcode==3:
            assert not any(args) and not any(kwargs.values())
            self.packets.append(opcode)
            return struct.pack('<QqQ',opcode,0,fx.DRAM_BASE+0x10000)
        if opcode==0x107:
            assert args[0] in (fx.DRAM_BASE+0x10000,fx.DRAM_BASE+0x10001)
            assert not any(args[1:]) and not any(kwargs.values())
            self.packets.append(opcode)
            return struct.pack('<QqQ',opcode,0,self.ba[args[0]-fx.DRAM_BASE-0x10000])
        if opcode==0x308:  # Independent literal P_DC_CVAC.
            assert not any(args[2:]) and not any(kwargs.values())
            self.packets.append(opcode);self.dc_cvac(*args[:2])
            return struct.pack('<QqQ',opcode,0,0)
        return old.Wire.proxyreq(self,packet,**kwargs)
    def readmem(self,address,size):
        if address==fx.DRAM_BASE+0x10000:
            assert size==len(self.ba);return self.ba
        if address==fx.PHYS+fx.ADT_OFFSET:
            assert size==len(self.adt);return self.adt
        return tests.Fake.readmem(self,address,size)
    readstruct=UartInterface.readstruct


with patch.object(tests.prior.t,'BASE',fx.DRAM_BASE+0x20000), \
     patch.object(tests.prior.t,'HELPER_ADDR',fx.DRAM_BASE+0x420000), \
     patch.object(old.t,'BASE',fx.DRAM_BASE+0x20000), \
     patch.object(old.t,'HELPER_ADDR',fx.DRAM_BASE+0x420000), \
     patch.object(c.core,'verify_local'),patch.object(c.core.census,'verify_image'):
    for stage in (None,'reset'):
        wire=Wire();wire.partial=stage
        clock=old.t.Clock();journal=[]
        ctl=c.Controller(wire,M1N1Proxy(wire),tests.prior.t.IMAGE,journal.append,
                         clock=clock,sleep=clock.sleep,metadata=lambda *_:None)
        if stage:
            try:ctl.run()
            except c.Refusal as e:assert str(e)=='cpu1_arrival_timeout'
            else:raise AssertionError('partial state falsely passed')
            assert ctl.state['entry_observation']=='reset_identity_seen'
        else:
            result=ctl.run()
            assert result['result']=='CPU1_ENTRY_AND_REQUESTS_PASS'
            assert result['requests_completed']==2 and result['mutation_requests']==15
        assert wire.packets.count(0x308)==2
        assert all(op not in wire.packets for op in (0x500,0x501,0x502,0x503,0x506))
print('31D-PINNED-CLIENT-PASS: success and partial timeout; real parser and DC CVAC encoding')
