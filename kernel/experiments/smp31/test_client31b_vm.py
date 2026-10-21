#!/usr/bin/env python3
"""Controller through the real pinned client's request serializer, no USB."""
import importlib.util
from pathlib import Path
import struct
import sys

sys.path.insert(0, sys.argv[1])
from m1n1.proxy import M1N1Proxy
path = Path(__file__).resolve().parents[3] / 'native/boot/test_smp31b.py'
s = importlib.util.spec_from_file_location('tests', path)
t = importlib.util.module_from_spec(s); s.loader.exec_module(t)


class Wire(t.Fake):
    def __init__(self):
        super().__init__()
        self.packets = []
    def proxyreq(self, packet, **kwargs):
        assert len(packet) == 56 and not any(kwargs.values()), 'unexpected proxy mode'
        opcode, *args = struct.unpack('<7Q', packet)
        self.packets.append(opcode)
        # Literal protocol IDs, checked independently of controller method names.
        method, argc = {0:('nop',0), 4:('get_base',0),
            0x13:('get_chipid',0), 0x008:('get_exc_count',0),
            0x100:('write64',2), 0x101:('write32',2),
            0x104:('read64',1), 0x105:('read32',1),
            0x302:('ic_ivau',2), 0x309:('dc_cvau',2),
            0x504:('smp_set_wfe_mode',1), 0x505:('smp_is_alive',1),
            0x602:('memalign',2), 2:('call',None)}[opcode]
        if opcode == 2:
            offset = args[0] - (t.HELPER_ADDR | t.c.RX_ALIAS)
            argc = 3 if offset in (112,160) else 2 if offset == 96 else 1
        assert not any(args[argc:]), 'unexpected extra arguments'
        callargs=args[:argc]
        if method == 'smp_set_wfe_mode': callargs=[bool(callargs[0])]
        value = getattr(self, method)(*callargs)
        return struct.pack('<QqQ', opcode, 0, value or 0)


w = Wire()
clock, journal = t.Clock(), []
ctl = t.c.Controller(w, M1N1Proxy(w), t.IMAGE, journal.append,
    clock=clock, sleep=clock.sleep, metadata=lambda *_: None,
    bounds=lambda *_: (t.BASE, t.BASE+0x800000))
assert t.run(ctl)['result'] == 'CPU1_ENTRY_AND_REQUESTS_PASS'
assert all(op not in w.packets for op in (0x500,0x501,0x502,0x503,0x506))
print('PINNED-CLIENT-PASS: exact request encoding; no bulk start/stop/SMP-call/wait opcode')
