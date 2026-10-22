#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""VM-only: real pinned proxy serialization and BootArgs/ADT through full 31L.

No serial transport is constructed. All target effects are independent literal
allowlists and synthetic Fake memory. The caller verifies the client checkout
pin; this file must not execute its third-party imports on the macOS host.
"""
import json
import importlib.util
from pathlib import Path
import struct
import sys
from unittest.mock import patch

if sys.platform != 'linux':
    raise SystemExit('31L serializer test requires the isolated Linux VM')
if len(sys.argv) != 2:
    raise SystemExit('usage: test_client31l_vm.py PINNED_PROXYCLIENT_DIRECTORY')

HERE = Path(__file__).resolve().parent
CLIENT = Path(sys.argv[1]).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(CLIENT))
sys.path.insert(0, str(ROOT / 'native/boot'))
# Set this BEFORE importing fixture modules. Their stand-in parser must never
# be installed in sys.modules for this real-client integration run.
sys.argv.extend(['--real-parser', str(CLIENT)])
import test_smp31l as tests
import smp31l as c
from m1n1.proxy import M1N1Proxy, UartInterface
import m1n1.adt as real_adt
import m1n1.tgtypes as real_types

assert Path(real_adt.__file__).resolve().is_relative_to(CLIENT)
assert Path(real_types.__file__).resolve().is_relative_to(CLIENT)
assert tests.prior.REAL is True
fx, t = tests.prior.fx, tests.t
spec=importlib.util.spec_from_file_location('ps_fixture',ROOT/'kernel/experiments/smp31g-observation/fixture.py')
pf=importlib.util.module_from_spec(spec);spec.loader.exec_module(pf)

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
             192: 2, 224: 2, 256: 2, 288: 2, 320: 1, 352: 3, 384: 2, 512: 3}
# Independent expected addresses, not imported from the controller or tracker.
CPU_STATE_ADDRESSES = (0x210050100, 0x210150100)


class Wire(tests.Fake):
    def __init__(self):
        super().__init__()
        self.packets = []
        self.call_offsets = []
        self.bootargs_reads = self.adt_reads = 0
        self.adt = pf.adt()
        self.ba = fx.bootargs(adt_size=len(self.adt))
        self.rvbar_bit11 = False
        self.rvbar_words = [t.BASE | 1 | (1 << 63)] * 2

    def read64(self, address):
        value = super().read64(address)
        if self.rvbar_bit11 and address == 0x210150000:
            # Synthetic unknown-format bit only. Keep frozen G fixtures intact.
            return value | 0x800
        return value

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
        if opcode in (0x104, 0x105) and args[0] in CPU_STATE_ADDRESSES:
            assert opcode == 0x105 and not self.hw, 'CPU state requires guarded32 baseline'
        if opcode == 0x002 and args[1] in CPU_STATE_ADDRESSES:
            assert offset in (192, 256, 384) and argc == 2, 'CPU state helper width/access'
            assert bool(self.hw) is (offset == 384), 'CPU state helper phase'
        if offset == 512:
            assert not self.hw, 'CPU0 control store after startup'
            assert args[1] in (t.BASE+0x90b20, t.HELPER_ADDR+0x1120), 'CPU0 control address'
            marker = 0x314b435055304f4b if args[1] == t.BASE+0x90b20 else 0x314c435055304f4b
            assert args[2] in (0, marker), 'CPU0 control value'
        if offset == 96 and t.BASE+0x90a80 <= args[1] < t.BASE+0x90b40:
            assert args[1] % 8 == 0, 'record read alignment'
            assert (t.BASE+0x90a80 <= args[1] < t.BASE+0x90ac0 or
                    t.BASE+0x90b00 <= args[1] < t.BASE+0x90b40), 'record gap'
            assert args[1] < t.BASE+0x90b00 or not self.hw, 'control read after startup'
        if offset == 96 and t.HELPER_ADDR+0x1000 <= args[1] < t.HELPER_ADDR+0x1140:
            assert args[1] % 8 == 0, 'normal record alignment'
            assert any(t.HELPER_ADDR+lo <= args[1] < t.HELPER_ADDR+lo+64
                       for lo in (0x1000, 0x1080, 0x1100)), 'normal record gap'
            assert args[1] < t.HELPER_ADDR+0x1100 or not self.hw, 'normal control after start'
        assert offset != 160, 'callbacks not authorized in31L'
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
    forbidden += [packet(0x104, address) for address in CPU_STATE_ADDRESSES]
    forbidden += [packet(2, helper + offset, address)
                  for offset in (96, 224, 288, 384)
                  for address in CPU_STATE_ADDRESSES]
    forbidden += [packet(2, helper+512, t.BASE+offset, 0)
                  for offset in (0x90a40, 0x90a80, 0x90ac0, 0x90b18, 0x90b28)]
    forbidden += [packet(2, helper+512, t.BASE+0x90b20, 1),
                  packet(2, helper+96, t.BASE+0x90ac0),
                  packet(2, helper+96, t.BASE+0x90b01)]
    for data in forbidden:
        try:
            wire.proxyreq(data)
        except AssertionError:
            pass
        else:
            raise AssertionError('forbidden packet accepted')
    assert not wire.packets and not wire.hw and wire.mutations == 0


def make_controller(primary_el, partial=False):
    wire = Wire()
    wire.return_el = primary_el
    if partial:
        wire.partial = 'none'
        wire.recorder_phase = 2
    clock, journal = t.Clock(), []
    controller = c.Controller(wire, M1N1Proxy(wire), t.IMAGE,
        lambda state: journal.append(json.loads(json.dumps(state))),
        clock=clock, sleep=clock.sleep, metadata=lambda *_: None)
    return wire, controller, clock, journal



def run_case(el, phase=0, identity=0, kind='vector', starts=2, arrival=False, fault=None):
    wire, ctl, _, journal = make_controller(el)
    wire.arrival = arrival
    wire.normal_phase, wire.normal_identity = phase, identity
    wire.normal_kind, wire.normal_after_starts = kind, starts
    if fault:
        setattr(wire, fault[0], fault[1])
    try:
        ctl.run()
    except (c.Refusal, ValueError, TimeoutError) as exc:
        reason = str(exc) if type(exc) is not TimeoutError else 'transport_timeout'
    else:
        raise AssertionError('visibility campaign continued')
    state = ctl.state
    assert state['requests_completed'] == 0 and 160 not in wire.call_offsets
    assert 'PRIVATE_SYNTHETIC' not in json.dumps(journal)
    assert wire.bootargs_reads >= 1 and wire.adt_reads >= 1
    if not fault:
        assert state['cpu0_normal_control']['result'] == 'CPU0_NORMAL_CONTROL_PASS'
        if phase == 2 and identity == 0x40001:
            assert state['cpu1_prefix_identity_observed']
            assert reason == 'normal_'+kind+'_prefix_observed'
            assert len(wire.hw) == starts
        elif phase == 2:
            assert not state['cpu1_prefix_identity_observed']
            assert reason == 'normal_identity_unexpected'
        elif phase or identity:
            assert reason == 'normal_'+kind+'_prefix_observed'
            assert not state['cpu1_prefix_identity_observed']
        elif arrival:
            assert reason == 'device_arrival_observed_stop_without_callbacks'
        else:
            assert reason == 'cpu1_arrival_timeout'
            assert not state['cpu1_prefix_identity_observed']
    elif fault[0] == 'normal_post_read_fail':
        assert wire.normal_post_reads == fault[1] and len(wire.hw) == 1
        assert wire.packets[-1][0] == 2
        assert wire.packets[-1][1][0] == (t.HELPER_ADDR | 0xc0000000000)+96
    return dict(el=el//4, phase=phase, identity_committed=state['cpu1_prefix_identity_observed'],
                kind=kind, starts=len(wire.hw), reason=reason, callbacks=0,
                fault_kind=fault[0] if fault else None)

image = tests.synthetic_image()
with patch.object(t, 'BASE', fx.DRAM_BASE+0x20000), \
     patch.object(t, 'HELPER_ADDR', fx.DRAM_BASE+0x420000), \
     patch.object(t, 'IMAGE', bytes(image)), \
     patch.object(c.core, 'verify_local'), \
     patch.object(c.core.census, 'verify_image'), \
     patch.object(c, 'verify_recorder'), \
     patch.object(c.previous, 'verify_recorder'):
    check_wire_refusals()
    results = [run_case(el) for el in (4,8)]
    results += [run_case(el, phase, identity, kind, starts)
                for el in (4,8) for kind in ('vector','cold') for starts in (1,2)
                for phase,identity in ((2,0x40001),(1,0),(0,0x40001),(2,0x40000))]
    results += [run_case(el, arrival=True) for el in (4,8)]
    results += [run_case(el, fault=(kind, True)) for el in (4,8)
                for kind in ('normal_bad_translation','normal_drop_marker')]
    results += [run_case(8, fault=('normal_read_fail', at)) for at in range(1,9)]
    results += [run_case(el, fault=('normal_post_read_fail', at)) for el in (4,8) for at in range(1,7)]
print('31L-PINNED-CLIENT-PASS: '+json.dumps(results,sort_keys=True))
