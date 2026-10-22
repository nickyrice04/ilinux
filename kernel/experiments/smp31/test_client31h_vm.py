#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""VM-only: real pinned proxy serialization and BootArgs/ADT through full 31H.

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
    raise SystemExit('31H serializer test requires the isolated Linux VM')
if len(sys.argv) != 2:
    raise SystemExit('usage: test_client31h_vm.py PINNED_PROXYCLIENT_DIRECTORY')

HERE = Path(__file__).resolve().parent
CLIENT = Path(sys.argv[1]).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(CLIENT))
sys.path.insert(0, str(ROOT / 'native/boot'))
# Set this BEFORE importing fixture modules. Their stand-in parser must never
# be installed in sys.modules for this real-client integration run.
sys.argv.extend(['--real-parser', str(CLIENT)])
import test_smp31h as tests
import smp31h as c
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
             192: 2, 224: 2, 256: 2, 288: 2, 320: 1, 352: 3, 384: 2}
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


def check_rvbar(wire, state, bit11=False):
    rvbar = state['rvbar_observation']
    assert rvbar['state'] == 'complete' and rvbar['error'] is None
    assert (rvbar['read_attempts'], rvbar['read_returns'],
            rvbar['guard_check_attempts'], rvbar['validated_reads']) == (2, 2, 2, 2)
    assert rvbar['pending_cpu_id'] is None
    assert rvbar['mirrors_equal'] is (not bit11)
    assert rvbar['exact_entry_offset'] == rvbar['effective_reset_route'] == 'UNKNOWN'
    assert [row['cpu_id'] for row in rvbar['rows']] == [0, 1]
    assert [row['unknown_low_bits_class'] for row in rvbar['rows']] == [
        'zero', 'bit11_only' if bit11 else 'zero']
    assert [row['bit11_set'] for row in rvbar['rows']] == [False, bit11]
    assert [row['firmware_format_field_relation'] for row in rvbar['rows']] == [
        'image_base', 'image_base_plus_0x800' if bit11 else 'image_base']
    assert all(row['legacy_page_field_matches_vectors'] and row['legacy_lock_bit0']
               and not row['unknown_upper_bits_present'] for row in rvbar['rows'])
    rvbar_indices = [i for i, (opcode, args) in enumerate(wire.packets)
                     if opcode == 0x104 and args[0] in (0x210050000, 0x210150000)]
    assert [wire.packets[i] for i in rvbar_indices] == [
        (0x104, (0x210050000,)), (0x104, (0x210150000,))]
    assert all(wire.packets[i + 1] == (0x008, ()) for i in rvbar_indices)
    return rvbar_indices


def check_cpu_state_packets(wire, primary_el, attempts=8, translations=2):
    helper = t.HELPER_ADDR | 0xc0000000000
    read_entry = 192 if primary_el == 4 else 256
    # Every packet mentioning either literal register must be exactly one of
    # these two AT queries, two guarded32 reads, or six fixed32 helper calls.
    state_packets = [(i, opcode, args)
                     for i, (opcode, args) in enumerate(wire.packets)
                     if any(address in args for address in CPU_STATE_ADDRESSES)]
    expected = [(0x002, (helper + read_entry, address))
                for address in CPU_STATE_ADDRESSES][:translations]
    reads = [(0x105, (address,)) for address in CPU_STATE_ADDRESSES]
    reads += [(0x002, (helper + 384, address))
              for _ in range(3) for address in CPU_STATE_ADDRESSES]
    expected += reads[:attempts]
    assert [(opcode, args) for _, opcode, args in state_packets] == expected
    assert wire.state_read_count == attempts
    start_indices = [i for i, (opcode, args) in enumerate(wire.packets)
                     if opcode == 0x002 and args[0] == helper + 352]
    if start_indices:
        assert all(i < start_indices[0] for i, _, _ in state_packets[:translations + 2])
        for n, (index, _, _) in enumerate(state_packets[translations:]):
            if n >= 2:
                assert index > start_indices[0 if n < 4 else 1]
        assert all(opcode == 0x002 for opcode, _ in wire.packets[start_indices[0]:])
    return [i for i, _, _ in state_packets[translations:]]


def check_state_report(state, attempts=8, completed=8):
    report = state['cpu_state_observation']
    assert report['reads_attempted'] == attempts
    assert report['reads_completed'] == completed
    assert report['entry_execution'] == report['reset_release'] == 'NOT_ESTABLISHED'
    assert report['running_state'] == 'NOT_ESTABLISHED'
    assert report['program_counter'] == 'NOT_OBSERVED'
    assert report['t6050_register_semantics'] == 'UNKNOWN'
    assert len(report['samples']) == (attempts + 1) // 2
    for n, row in enumerate(report['samples']):
        assert row['phase'] == ('before_start', 'after_first_start',
                                'after_second_start', 'final')[n]
        assert row['complete'] is (2 * n + 2 <= completed)
        for cpu in (0, 1):
            observed = row['cpu' + str(cpu)]
            if 2 * n + cpu < completed:
                assert observed['low_byte'] == (0x10 if cpu == 0 or n >= 2 else 0)
                assert observed['changed_from_baseline'] is (
                    None if n == 0 else cpu == 1 and n >= 2)
            else:
                assert observed is None
    return report


def run_case(primary_el, partial=False):
    wire, controller, clock, journal = make_controller(primary_el, partial)
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
        assert state['mutation_requests'] == 66
        assert 160 not in wire.call_offsets
        assert clock() <= 3.1
    else:
        state = controller.run()
        assert state['result'] == 'CPU1_ENTRY_AND_REQUESTS_PASS'
        assert state['requests_completed'] == 8 and state['mutation_requests'] == 74
        assert state['park_verified'] and state['recorder_observation']['complete']
        assert wire.call_offsets.count(160) == 8
    assert state['permissions']['primary_exception_level'] == primary_el // 4
    assert state['experiment'] == 'smp31h'
    rvbar_indices = check_rvbar(wire, state)
    assert state['reset_format_gate_passed']
    assert state['permissions']['passed']
    assert all(value is True for key, value in state['ram_check'].items()
               if key != 'bootargs_revision')
    assert state['ram_check']['bootargs_revision'] == 3
    assert wire.bootargs_reads == wire.adt_reads == 2
    assert wire.hw == [(0x280688004, 2), (0x280688008, 2)]
    assert wire.call_offsets.count(352) == 2
    assert wire.call_offsets.count(384) == 12  # Six PS + six CPU-state reads.
    assert state['power_binding']['live_adt_bound']
    assert state['power_observation']['reads_completed'] == 8
    state_indices = check_cpu_state_packets(wire, primary_el)
    assert state['cpu_state_permissions'] == {'0': True, '1': True}
    assert check_state_report(state)['error'] is None
    diagnostics = (0x002, ((t.HELPER_ADDR | 0xc0000000000) + 96, t.BASE + 0x110038))
    # Each read is bracketed by the fixed, non-clearing diagnostic helper.
    # Derive neither its literal offset nor its diagnostic address from the
    # implementation under test.
    assert all(wire.packets[i - 1] == diagnostics and wire.packets[i + 1] == diagnostics
               for i in state_indices)
    assert wire.call_offsets.count(320) == 1
    selected = (192, 224) if primary_el == 4 else (256, 288)
    rejected = (256, 288) if primary_el == 4 else (192, 224)
    assert all(offset in wire.call_offsets for offset in selected)
    assert all(offset not in wire.call_offsets for offset in rejected)
    assert sum(offset in selected for offset in wire.call_offsets) == 20
    assert {96, 112} <= set(wire.call_offsets)
    opcodes = [op for op, args in wire.packets]
    assert opcodes.count(0x308) == 4  # Two RAM UART zeroes plus body and hook.
    assert all(op not in opcodes for op in (0x500, 0x501, 0x502, 0x503, 0x506))
    assert state['linux_boot'] == 'NOT RUN'
    assert not any(op == 0x101 and args[0] in (0x280688004, 0x280688008)
                   for op, args in wire.packets)
    return {'primary_el': primary_el // 4, 'partial_record_timeout': partial,
            'rvbar_reads': len(rvbar_indices), 'cpu_state_read_bytes': 4,
            'cpu_state_guarded_reads': 2, 'cpu_state_helper_reads': 6,
            'rvbar_observation': 'TWO_EXISTING_READS_CLASSIFIED',
            'requests_completed': state['requests_completed'],
            'real_bootargs_adt': True, 'guarded_startup_stores': 0,
            'start_helper_calls': 2}


def run_reset_format_refusal(primary_el):
    wire, controller, _, journal = make_controller(primary_el)
    wire.rvbar_bit11 = True
    try:
        controller.run()
    except c.Refusal as error:
        assert str(error) == 'reset_format_requires_review'
    else:
        raise AssertionError('unknown reset format proceeded')
    state = controller.state
    check_rvbar(wire, state, bit11=True)
    check_cpu_state_packets(wire, primary_el, attempts=0, translations=0)
    assert not state['reset_format_gate_passed']
    assert state['mutation_requests'] == wire.mutations == 0
    assert state['start_writes_attempted'] == 0 and not wire.hw
    assert state['cpu_state_observation'] == state['cpu_state_permissions'] == {}
    assert not wire.call_offsets and state['linux_boot'] == 'NOT RUN'
    return {'primary_el': primary_el // 4, 'reset_format_refusal': True,
            'mutations': 0, 'cpu_state_reads': 0}


def run_state_read_fault(primary_el, at, partial=False):
    wire, controller, _, journal = make_controller(primary_el, partial)
    wire.state_fail_at = at
    try:
        controller.run()
    except c.Refusal as error:
        expected = ('cpu1_arrival_timeout' if partial and at >= 7
                    else 'cpu_state_read_failed')
        assert str(error) == expected
    else:
        raise AssertionError('failed CPU-state read proceeded')
    state = controller.state
    indices = check_cpu_state_packets(wire, primary_el, attempts=at)
    report = check_state_report(state, attempts=at, completed=at - 1)
    assert report['error'] == 'cpu_state_read_failed'
    assert indices[-1] == len(wire.packets) - 1, 'target request after failed read'
    starts = 0 if at <= 2 else 1 if at <= 4 else 2
    assert state['start_writes_attempted'] == len(wire.hw) == starts
    assert wire.hw == [(0x280688004, 2), (0x280688008, 2)][:starts]
    assert wire.call_offsets.count(352) == starts
    assert wire.call_offsets.count(160) == (8 if not partial and at >= 7 else 0)
    if partial and at >= 7:
        assert state['terminal_observation_error'] == 'cpu_state_read_failed'
        assert state['mutation_requests'] == 66
    else:
        assert state['terminal_observation_error'] is None
    assert state['linux_boot'] == 'NOT RUN'
    payload = json.dumps(journal)
    assert 'private' not in payload
    assert str(0x12345610) not in payload and str(0x12345600) not in payload
    return {'primary_el': primary_el // 4, 'state_fault_at': at,
            'natural_timeout_preserved': partial and at >= 7,
            'first_fault_stopped': True, 'cpu_state_reads': len(indices)}


def run_state_translation_refusal(primary_el):
    wire, controller, _, _ = make_controller(primary_el)
    wire.state_bad_translation = True
    try:
        controller.run()
    except c.Refusal as error:
        assert str(error).startswith('cpu_state_')
    else:
        raise AssertionError('invalid CPU-state translation proceeded')
    check_cpu_state_packets(wire, primary_el, attempts=0, translations=1)
    state = controller.state
    assert state['cpu_state_permissions'] == {'0': False}
    assert state['start_writes_attempted'] == 0 and not wire.hw
    assert state['cpu_state_observation'] == {}
    return {'primary_el': primary_el // 4, 'cpu_state_translation_refused': True,
            'cpu_state_reads': 0, 'start_helper_calls': 0}


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
    results = [run_case(el, partial=partial)
               for el in (4, 8) for partial in (False, True)]
    results += [run_reset_format_refusal(el) for el in (4, 8)]
    results += [run_state_translation_refusal(el) for el in (4, 8)]
    results += [run_state_read_fault(8, at, partial=partial)
                for partial in (False, True) for at in range(1, 9)]
print('31H-PINNED-CLIENT-PASS: ' + json.dumps(results, sort_keys=True))
