#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""VM-only: real pinned proxy serialization and BootArgs/ADT through full 31F.

No serial transport is constructed. All target effects are independent literal
allowlists and synthetic Fake memory. The caller verifies the client checkout
pin; this file must not execute its third-party imports on the macOS host.
"""
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch

if sys.platform != 'linux':
    raise SystemExit('31F serializer test requires the isolated Linux VM')
if len(sys.argv) != 2:
    raise SystemExit('usage: test_client31f_vm.py PINNED_PROXYCLIENT_DIRECTORY')

HERE = Path(__file__).resolve().parent
CLIENT = Path(sys.argv[1]).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(CLIENT))
sys.path.insert(0, str(ROOT / 'native/boot'))
# Set this BEFORE importing fixture modules. Their stand-in parser must never
# be installed in sys.modules for this real-client integration run.
sys.argv.extend(['--real-parser', str(CLIENT)])
import test_smp31f as tests
import smp31f as c
from m1n1.proxy import M1N1Proxy, UartInterface
import m1n1.adt as real_adt
import m1n1.tgtypes as real_types

assert Path(real_adt.__file__).resolve().is_relative_to(CLIENT)
assert Path(real_types.__file__).resolve().is_relative_to(CLIENT)
assert tests.prior.REAL is True
fx, t = tests.prior.fx, tests.t

# Deliberately literal protocol numbers and argument counts; never derive this
# allowlist from the tested proxy class or the controller's named methods.
OPCODES = {
    0x000: ('nop', 0), 0x003: ('bootargs_pointer', 0),
    0x004: ('get_base', 0), 0x008: ('get_exc_count', 0),
    0x013: ('get_chipid', 0),
    0x100: ('write64', 2), 0x101: ('write32', 2),
    0x104: ('read64', 1), 0x105: ('read32', 1),
    0x107: ('bootargs_byte', 1),
    0x302: ('ic_ivau', 2), 0x308: ('dc_cvac', 2),
    0x309: ('dc_cvau', 2),
    0x504: ('smp_set_wfe_mode', 1), 0x505: ('smp_is_alive', 1),
    0x602: ('memalign', 2),
}
# Counts include the function address. The only MMIO start path is +352.
CALL_ARGC = {0: 1, 16: 1, 32: 1, 48: 1, 64: 1, 80: 1,
             96: 2, 112: 3, 160: 3,
             192: 2, 224: 2, 256: 2, 288: 2, 320: 1, 352: 3}


class Wire(tests.Fake):
    def __init__(self):
        super().__init__()
        self.packets = []
        self.call_offsets = []
        self.bootargs_reads = self.adt_reads = 0
        self.ba, self.adt = fx.bootargs(), fx.adt()

    def proxyreq(self, packet, **kwargs):
        assert type(packet) is bytes and len(packet) == 56, 'packet size/type'
        assert not any(kwargs.values()), 'unexpected proxy mode'
        opcode, *args = struct.unpack('<7Q', packet)
        # Once start is attempted, guarded reads/writes and exception-counter
        # clear RPCs are forbidden. The controller uses only unguarded helpers.
        assert not self.hw or opcode == 0x002, 'guarded RPC after startup'
        if opcode == 0x002:
            offset = args[0] - (t.HELPER_ADDR | 0xc0000000000)
            assert offset in CALL_ARGC, 'unreviewed helper offset'
            argc, method = CALL_ARGC[offset], 'call'
        else:
            assert opcode in OPCODES, 'opcode not allowlisted'
            method, argc = OPCODES[opcode]
            offset = None
        assert not any(args[argc:]), 'unexpected extra arguments'
        # Refuse startup writes even before the first helper start; this is
        # independent of Fake's broader inherited historical write support.
        if opcode == 0x101:
            assert args[0] not in (0x280688004, 0x280688008), 'guarded startup store'
        self.packets.append((opcode, tuple(args[:argc])))
        if offset is not None:
            self.call_offsets.append(offset)
        if method == 'bootargs_pointer':
            value = fx.DRAM_BASE + 0x10000
        elif method == 'bootargs_byte':
            assert args[0] in (fx.DRAM_BASE + 0x10000, fx.DRAM_BASE + 0x10001)
            value = self.ba[args[0] - fx.DRAM_BASE - 0x10000]
        else:
            callargs = args[:argc]
            if method == 'smp_set_wfe_mode':
                assert callargs[0] in (0, 1)
                callargs = [bool(callargs[0])]
            value = getattr(self, method)(*callargs)
        return struct.pack('<QqQ', opcode, 0, value or 0)

    def readmem(self, address, size):
        assert not self.hw, 'bulk read after startup'
        if address == fx.DRAM_BASE + 0x10000:
            assert size == len(self.ba)
            self.bootargs_reads += 1
            return self.ba
        if address == fx.PHYS + fx.ADT_OFFSET:
            assert size == len(self.adt)
            self.adt_reads += 1
            return self.adt
        return super().readmem(address, size)

    readstruct = UartInterface.readstruct


def packet(opcode, *args):
    assert len(args) <= 6
    return struct.pack('<7Q', opcode, *args, *([0] * (6 - len(args))))


def check_wire_refusals():
    wire = Wire()
    helper = t.HELPER_ADDR | 0xc0000000000
    forbidden = [packet(op) for op in (0x500, 0x501, 0x502, 0x503, 0x506)]
    forbidden += [packet(0x101, address, 2) for address in (0x280688004, 0x280688008)]
    forbidden += [packet(2, helper + 128), packet(2, helper + 352, 1, 2, 3),
                  packet(2, helper + 96, t.BASE + 0x90a40, 1),
                  packet(0, 1), bytes(55)]
    for data in forbidden:
        try:
            wire.proxyreq(data)
        except AssertionError:
            pass
        else:
            raise AssertionError('forbidden packet accepted')
    assert not wire.packets and not wire.hw and wire.mutations == 0


def run_case(primary_el, partial=False):
    wire = Wire()
    wire.return_el = primary_el
    if partial:
        wire.partial = 'none'
        wire.recorder_phase = 2
    clock, journal = t.Clock(), []
    controller = c.Controller(wire, M1N1Proxy(wire), t.IMAGE,
        lambda state: journal.append(json.loads(json.dumps(state))),
        clock=clock, sleep=clock.sleep, metadata=lambda *_: None)
    if partial:
        try:
            controller.run()
        except c.Refusal as error:
            assert str(error) == 'cpu1_arrival_timeout'
        else:
            raise AssertionError('partial recorder falsely passed')
        state = controller.state
        assert state['recorder_observation']['highest_phase_seen'] == 2
        assert not state['recorder_observation']['complete']
        assert state['requests_completed'] == 0 and not state['cpu1_arrival_verified']
        assert 160 not in wire.call_offsets
        assert clock() <= 3.1
    else:
        state = controller.run()
        assert state['result'] == 'CPU1_ENTRY_AND_REQUESTS_PASS'
        assert state['requests_completed'] == 8 and state['mutation_requests'] == 71
        assert state['park_verified'] and state['recorder_observation']['complete']
        assert wire.call_offsets.count(160) == 8
    assert state['permissions']['primary_exception_level'] == primary_el // 4
    assert state['permissions']['passed']
    assert all(value is True for key, value in state['ram_check'].items()
               if key != 'bootargs_revision')
    assert state['ram_check']['bootargs_revision'] == 3
    assert wire.bootargs_reads == wire.adt_reads == 1
    assert wire.hw == [(0x280688004, 2), (0x280688008, 2)]
    assert wire.call_offsets.count(352) == 2
    assert wire.call_offsets.count(320) == 1
    selected = (192, 224) if primary_el == 4 else (256, 288)
    rejected = (256, 288) if primary_el == 4 else (192, 224)
    assert all(offset in wire.call_offsets for offset in selected)
    assert all(offset not in wire.call_offsets for offset in rejected)
    assert sum(offset in selected for offset in wire.call_offsets) == 16
    assert {96, 112} <= set(wire.call_offsets)
    opcodes = [op for op, args in wire.packets]
    assert opcodes.count(0x308) == 4  # Two RAM UART zeroes plus body and hook.
    assert all(op not in opcodes for op in (0x500, 0x501, 0x502, 0x503, 0x506))
    assert state['linux_boot'] == 'NOT RUN'
    assert not any(op == 0x101 and args[0] in (0x280688004, 0x280688008)
                   for op, args in wire.packets)
    return {'primary_el': primary_el // 4, 'partial_record_timeout': partial,
            'requests_completed': state['requests_completed'],
            'real_bootargs_adt': True, 'guarded_startup_stores': 0,
            'start_helper_calls': 2}


# Only immutable-input pin validation is replaced for the original synthetic
# image. Real wire serialization and real BootArgs/ADT parsing stay intact.
image = bytearray(t.IMAGE)
struct.pack_into('<I', image, 0x0, 0xd2800609)
with patch.object(t, 'BASE', fx.DRAM_BASE + 0x20000), \
     patch.object(t, 'HELPER_ADDR', fx.DRAM_BASE + 0x420000), \
     patch.object(t, 'IMAGE', bytes(image)), \
     patch.object(c.core, 'verify_local'), \
     patch.object(c.core.census, 'verify_image'):
    check_wire_refusals()
    results = [run_case(4), run_case(8), run_case(4, partial=True)]
print('31F-PINNED-CLIENT-PASS: ' + json.dumps(results, sort_keys=True))
