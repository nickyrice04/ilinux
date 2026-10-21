#!/usr/bin/env python3
"""Real pinned serializers + raw BootArgs/ADT + high-address CPU1 model."""
import importlib.util
from pathlib import Path
import struct
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,sys.argv[1])
sys.path.insert(0,str(HERE.parents[2]/'native/boot'))
import smp31c as c
from m1n1.proxy import M1N1Proxy, UartInterface


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


old=load('old_client',HERE/'test_client31b_vm.py')
fx=load('fixture',HERE/'memory_fixture31c.py')


class Wire(old.Wire):
    def __init__(self):
        super().__init__(); self.ba=fx.bootargs(); self.adt=fx.adt()
    def proxyreq(self,packet,**kwargs):
        opcode,*args=struct.unpack('<7Q',packet)
        if opcode == 3:
            assert not any(args) and not any(kwargs.values())
            self.packets.append(opcode)
            return struct.pack('<QqQ',opcode,0,fx.DRAM_BASE+0x10000)
        if opcode == 0x107:  # P_READ8, the real client's revision decoding.
            assert args[0] in (fx.DRAM_BASE+0x10000,fx.DRAM_BASE+0x10001)
            assert not any(args[1:]) and not any(kwargs.values())
            self.packets.append(opcode)
            return struct.pack('<QqQ',opcode,0,self.ba[args[0]-fx.DRAM_BASE-0x10000])
        return super().proxyreq(packet,**kwargs)
    def readmem(self,address,size):
        if address == fx.DRAM_BASE+0x10000:
            assert size == len(self.ba); return self.ba
        if address == fx.PHYS+fx.ADT_OFFSET:
            assert size == len(self.adt); return self.adt
        return super().readmem(address,size)
    readstruct=UartInterface.readstruct


with patch.object(old.t,'BASE',fx.DRAM_BASE+0x20000), \
     patch.object(old.t,'HELPER_ADDR',fx.DRAM_BASE+0x420000), \
     patch.object(c.core,'verify_local'), patch.object(c.core.census,'verify_image'):
    wire=Wire(); clock=old.t.Clock(); journal=[]
    ctl=c.Controller(wire,M1N1Proxy(wire),old.t.IMAGE,journal.append,
                     clock=clock,sleep=clock.sleep,metadata=lambda *_:None)
    result=ctl.run()
    assert result['result']=='CPU1_ENTRY_AND_REQUESTS_PASS'
    assert result['ram_check']['chosen_base_matches'] and result['ram_check']['image_within_usable']
    assert result['requests_completed']==2 and result['mutation_requests']==11
    assert all(op not in wire.packets for op in (0x500,0x501,0x502,0x503,0x506))
print('31C-PINNED-CLIENT-HIGH-ADDRESS-PASS: real revision/struct/ADT parsing, unchanged CPU1 sequence')
