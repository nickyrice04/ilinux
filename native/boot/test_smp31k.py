"""31K CPU0 control, contained cold entry, and connection lifecycle; synthetic only."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import plistlib
import stat
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31k as j
import test_smp31i as frozen

t, TraceProxy = frozen.t, frozen.TraceProxy
import test_smp31h as fixtures
prior = fixtures.prior


# Literal model bytes and spans are independent of the production encoders.
CONTROL_LEAF = struct.pack('<4I', 0xf9000001, 0xd5033f9f, 0xd2862960, 0xd65f03c0)
CONTROL_MARKER = 0x314b435055304f4b
COLD_WORDS = (0x90000480, 0x912a0000, 0xd2800028, 0xf9000008,
    0xd5033f9f, 0xd53800a8, 0xd3405d08, 0xf9000808, 0xd5033f9f,
    0xd2800048, 0xf9000008, 0xd5033f9f, 0xd5384249, 0xf9000409,
    0xd5033f9f, 0xd2800068, 0xf9000008, 0xd5033f9f, 0x14000000)
COLD_BODY = struct.pack('<19I', *COLD_WORDS)


def synthetic_image():
    image = bytearray(t.IMAGE)
    struct.pack_into('<I', image, 0, 0xd2800609)
    struct.pack_into('<I', image, 0x800, 0xaa0003f3)
    return bytes(image)


class Fake(fixtures.Fake):
    """Original software model, not a simulator of unknown reset firmware."""
    def __init__(self):
        super().__init__()
        self.rvbar_words = [t.BASE | 1 | (1 << 63)] * 2
        self.control_ready = False
        self.control_reads = self.control_stores = 0
        self.control_read_fail = self.control_store_fail = None
        self.control_drop_marker = self.control_drop_restore = False
        self.control_corrupt_guard = self.control_bad_return = False
        self.control_bad_translation = self.cold_bad_translation = False
        self.cold_phase = 0
        self.cold_identity = 0x40001
        self.cold_el = 4
        self.cold_after_starts = 2
        self.cold_reads = 0
        self.cold_read_fail = None
        self.cold_armed = False
        self.cold_trace = []

    def writemem(self, address, data):
        if address == t.HELPER_ADDR + 512:
            assert data == CONTROL_LEAF and not self.hw
            if self.mutation():
                self.ram[address-t.BASE:address-t.BASE+16] = data
            return
        return super().writemem(address, data)

    def dc_cvau(self, address, size):
        if address == t.HELPER_ADDR + 512:
            assert size == 16 and not self.hw
            self.mutation()
            return
        return super().dc_cvau(address, size)

    def ic_ivau(self, address, size):
        if address == (t.HELPER_ADDR | 0xc0000000000) + 512:
            assert size == 16 and not self.hw
            self.control_ready = self.mutation()
            return
        if address-t.BASE in (0xb00, 0x800):
            assert size == (76 if address-t.BASE == 0xb00 else 4) and not self.hw
            self.cold_trace.append(('invalidate', address-t.BASE))
            if self.mutation() and address-t.BASE == 0x800:
                self.cold_armed = True
            return
        return super().ic_ivau(address, size)

    def dc_cvac(self, address, size):
        if address & 0xa0000000000 == 0xa0000000000:
            offset = (address & ~0xa0000000000)-t.BASE
            if offset in (0xb00, 0x800):
                assert size == (76 if offset == 0xb00 else 4) and not self.hw
                self.cold_trace.append(('clean', offset))
                self.mutation()
                return
        return super().dc_cvac(address, size)

    def write32(self, address, value):
        if address & 0xa0000000000 == 0xa0000000000:
            offset = (address & ~0xa0000000000)-t.BASE
            if offset == 0x800 or 0xb00 <= offset < 0xb4c:
                assert not self.hw and offset % 4 == 0
                if offset == 0x800:
                    assert value == 0x140000c0
                    assert self.ram[0xb00:0xb4c] == COLD_BODY
                    assert self.cold_trace[-1] == ('invalidate', 0xb00)
                else:
                    assert value == COLD_WORDS[(offset-0xb00)//4]
                self.cold_trace.append(('store', offset))
                if self.mutation():
                    self.put(offset, '<I', value)
                return
        return super().write32(address, value)

    def call(self, address, *args):
        offset = address-(t.HELPER_ADDR | 0xc0000000000)
        if offset in (192, 224, 256, 288) and args:
            va = args[0]
            physical = va & ~0xe0000000000
            rel = physical-t.BASE
            helper = physical == t.HELPER_ADDR+512
            cold_code = rel in (0x800, 0xb00, 0xb48)
            cold_ram = rel in (0x90a80, 0x90ab8)
            control_ram = rel in (0x90b00, 0x90b38)
            if helper or cold_code or cold_ram or control_ram:
                assert not self.hw and self.tail_ready and len(args) == 1
                assert offset in ((192, 224) if self.return_el == 4 else (256, 288))
                is_write = offset in (224, 288)
                if helper:
                    assert va == (physical | 0xc0000000000) and not is_write
                if (helper or control_ram) and self.control_bad_translation:
                    return 1
                if (cold_code or cold_ram) and self.cold_bad_translation:
                    return 1
                if cold_code and is_write and va == physical:
                    return 1 | (13 << 1)
                return (physical & 0x000ffffffffff000) | (2 << 7) | (
                    (0xff if helper or cold_code else 0) << 56)
        if offset == 512:
            assert self.control_ready and not self.hw and len(args) == 2
            assert args[0] == t.BASE+0x90b20 and args[1] in (0, CONTROL_MARKER)
            self.control_stores += 1
            if self.control_stores == self.control_store_fail:
                raise TimeoutError('PRIVATE_SYNTHETIC control store')
            okay = self.mutation()
            drop = self.control_drop_marker if args[1] else self.control_drop_restore
            if okay and not drop:
                self.put(0x90b20, '<Q', args[1])
            if args[1] and self.control_corrupt_guard:
                self.put(0x90b00, '<Q', 1)
            return 0 if self.control_bad_return else 0x314b
        if offset == 96 and args and t.BASE+0x90b00 <= args[0] < t.BASE+0x90b40:
            assert len(args) == 1 and args[0] % 8 == 0 and not self.hw
            self.control_reads += 1
            if self.control_reads == self.control_read_fail:
                raise TimeoutError('PRIVATE_SYNTHETIC control read')
            return self.read64(args[0])
        if offset == 96 and args and t.BASE+0x90a80 <= args[0] < t.BASE+0x90ac0:
            assert len(args) == 1 and args[0] % 8 == 0
            self.cold_reads += 1
            if self.cold_read_fail == self.cold_reads:
                raise TimeoutError('PRIVATE_SYNTHETIC cold read')
            if self.cold_armed and len(self.hw) >= self.cold_after_starts and self.cold_phase:
                self.put(0x90a80, '<3Q', self.cold_phase, self.cold_el, self.cold_identity)
            return self.read64(args[0])
        return super().call(address, *args)


class ControllerTests(unittest.TestCase):
    keep_patch = prior.RamTests.keep_patch

    def controller(self):
        self.keep_patch(patch.object(t, 'IMAGE', synthetic_image()))
        self.keep_patch(patch.object(t, 'Fake', Fake))
        self.keep_patch(patch.object(prior.c, 'Controller', j.Controller))
        self.keep_patch(patch.object(fixtures.previous.e.binding, 'read',
                                     return_value=dict(live_adt_bound=True)))
        # Only immutable input identity is replaced for synthetic bytes.
        # Freshness, runtime readback, translations and wire behavior remain.
        self.keep_patch(patch.object(j, 'verify_recorder'))
        return prior.RamTests.high_controller(self)

    def test_success_scope_control_restore_and_cold_publication(self):
        for level in (4, 8):
            f, mem, ctl, journal = self.controller()
            f.return_el = level
            result = ctl.run()
            self.assertEqual(result['result'], 'CPU1_ENTRY_AND_REQUESTS_PASS')
            self.assertEqual(result['experiment'], 'smp31k')
            self.assertEqual(result['requests_completed'], 8)
            self.assertEqual(result['mutation_requests'], 103)
            self.assertEqual(f.hw, [(0x280688004, 2), (0x280688008, 2)])
            report = result['cpu0_control']
            self.assertEqual(report['result'], 'CPU0_OBSERVER_CONTROL_PASS')
            self.assertEqual((f.control_reads, f.control_stores), (24, 2))
            self.assertEqual(f.memory(t.BASE+0x90b00, 64), bytes(64))
            self.assertTrue(report['original_restored'])
            self.assertEqual(report['cpu1_execution'], 'NOT_TESTED')
            self.assertTrue(result['cold_entry_armed'])
            self.assertEqual(result['cold_observation']['highest_phase_seen'], 0)
            self.assertEqual(result['cold_publication'], {'body_verified': True,
                'hook_verified': True, 'whole_text_verified': True})
            self.assertEqual(result['linux_boot'], 'NOT RUN')
            self.assertNotIn(str(t.BASE), json.dumps(journal))
            self.assertNotIn('PRIVATE_SYNTHETIC', json.dumps(journal))
            self.doCleanups()

    def test_no_marker_remains_timeout_and_no_cpu1_proof(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        with self.assertRaisesRegex(j.Refusal, '^cpu1_arrival_timeout$'):
            ctl.run()
        self.assertEqual(ctl.state['cpu0_control']['result'], 'CPU0_OBSERVER_CONTROL_PASS')
        self.assertFalse(ctl.state['cpu1_arrival_verified'])
        self.assertEqual(ctl.state['cold_observation']['highest_phase_seen'], 0)
        self.assertEqual(ctl.state['requests_completed'], 0)
        self.assertEqual(ctl.state['mutation_requests'], 95)

    def test_nonzero_scratch_or_tripwire_refuses_without_erasing(self):
        for offset in (0x90a80, 0x90ab8, 0x90b00, 0x90b38):
            f, mem, ctl, journal = self.controller()
            f.put(offset, '<Q', 9)
            with self.assertRaisesRegex(j.Refusal, '^new_record_not_fresh$'):
                ctl.run()
            self.assertEqual(f.read64(t.BASE+offset), 9)
            self.assertEqual(f.mutations, 0)
            self.assertEqual(f.hw, [])
            self.doCleanups()

    def test_control_all_failed_reads_stop_without_cleanup_or_start(self):
        for at in range(1, 25):
            f, mem, ctl, journal = self.controller()
            f.control_read_fail = at
            with self.assertRaisesRegex(j.Refusal, 'control_'):
                ctl.run()
            self.assertEqual(f.control_reads, at)
            self.assertEqual(f.control_stores, 0 if at <= 8 else 1 if at <= 16 else 2)
            self.assertEqual(f.hw, [])
            self.assertFalse(f.cold_armed)
            self.assertNotIn('PRIVATE_SYNTHETIC', json.dumps(journal))
            self.doCleanups()

    def test_control_failed_stores_stop_without_retry(self):
        for at in (1, 2):
            f, mem, ctl, journal = self.controller()
            f.control_store_fail = at
            with self.assertRaisesRegex(j.Refusal, 'control_'):
                ctl.run()
            self.assertEqual(f.control_stores, at)
            self.assertEqual(f.control_reads, 8*at)
            self.assertEqual(f.hw, [])
            self.assertFalse(f.cold_armed)
            self.doCleanups()

    def test_control_semantic_failures_prevent_start(self):
        for field in ('control_drop_marker', 'control_drop_restore',
                      'control_corrupt_guard', 'control_bad_return'):
            f, mem, ctl, journal = self.controller()
            setattr(f, field, True)
            with self.assertRaises(j.Refusal):
                ctl.run()
            self.assertEqual(f.hw, [])
            self.assertFalse(f.cold_armed)
            self.assertEqual(ctl.state['cpu0_control']['result'], 'STOP')
            self.doCleanups()

    def test_extra_translation_failures_prevent_start(self):
        for field in ('control_bad_translation', 'cold_bad_translation'):
            f, mem, ctl, journal = self.controller()
            setattr(f, field, True)
            with self.assertRaisesRegex(j.Refusal, '^extra_permission_translation_fault$'):
                ctl.run()
            self.assertEqual(f.hw, [])
            self.assertFalse(f.cold_armed)
            self.assertEqual(f.control_stores, 0 if field.startswith('control') else 2)
            self.doCleanups()

    def test_cold_phases_stop_without_cpu1_callbacks_or_park_claim(self):
        for phase in (1, 2, 3):
            for starts in (0, 1, 2):
                f, mem, ctl, journal = self.controller()
                f.arrival = False
                f.cold_phase, f.cold_after_starts = phase, starts
                with self.assertRaisesRegex(j.Refusal, '^cold_entry_observed$'):
                    ctl.run()
                report = ctl.state['cold_observation']
                self.assertEqual(report['highest_phase_seen'], phase)
                self.assertEqual(report['identity_status'], 'not_committed' if phase == 1 else 'expected_cpu1')
                self.assertEqual(report['exception_level'], 1 if phase == 3 else None)
                self.assertFalse(report['park_verified'])
                self.assertEqual(len(f.hw), starts)
                self.assertFalse(ctl.state['cpu1_arrival_verified'])
                self.assertEqual(ctl.state['requests_completed'], 0)
                self.assertEqual(report['reset_route'], 'UNKNOWN')
                self.doCleanups()

    def test_cold_wrong_identity_or_el_is_terminal(self):
        for identity, el, reason in ((0x40000, 4, 'unexpected_cold_identity'),
                                    (0x50000, 4, 'unexpected_cold_identity'),
                                    (0x40001, 0, 'committed_cold_el_invalid')):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.cold_phase, f.cold_identity, f.cold_el = 3, identity, el
            with self.assertRaisesRegex(j.Refusal, '^'+reason+'$'):
                ctl.run()
            self.assertEqual(ctl.state['requests_completed'], 0)
            self.assertFalse(ctl.state['cpu1_arrival_verified'])
            self.assertNotIn(str(identity), json.dumps(journal))
            self.doCleanups()

    def test_cold_read_failures_stop_at_exact_prefix(self):
        for at in range(1, 5):
            f, mem, ctl, journal = self.controller()
            f.cold_read_fail = at
            with self.assertRaisesRegex(j.Refusal, '^cold_record_read_failed$'):
                ctl.run()
            report = ctl.state['cold_observation']
            self.assertEqual(report['reads_attempted'], at)
            self.assertEqual(report['reads_completed'], at-1)
            self.assertEqual(f.cold_reads, at)
            self.assertEqual(f.hw, [])
            self.assertNotIn('PRIVATE_SYNTHETIC', json.dumps(journal))
            self.doCleanups()

    def test_all_new_mutation_faults_stop_at_exact_prefix(self):
        # Previous prepare uses 64 mutations; K adds29 before either start.
        # Fault each new operation at both lost-reply and target-fault edges.
        for mode in ('fail_mutation', 'trap_mutation'):
            for at in range(65, 94):
                f, mem, ctl, journal = self.controller()
                setattr(f, mode, at)
                with self.assertRaises((j.Refusal, TimeoutError)):
                    ctl.run()
                self.assertEqual(f.mutations, at)
                self.assertEqual(ctl.state['mutation_requests'], at)
                self.assertEqual(f.hw, [])
                self.assertEqual(ctl.state['start_writes_attempted'], 0)
                self.doCleanups()

    def test_new_bulk_read_and_guard_faults_have_no_followup_read(self):
        def selected(ctl, address, size):
            return (ctl.state['phase'] in ('cpu0_observer_control',
                    'cold_entry_permissions', 'cold_entry_publish') or
                    (ctl.state['phase'] == 'preflight' and size == 64 and
                     address-t.BASE in (0x90a80, 0x90b00)))
        f, mem, ctl, journal = self.controller()
        trace = TraceProxy(f)
        ctl.i = ctl.p = trace
        total = [0]
        original = f.readmem
        def count(address, size):
            if selected(ctl, address, size):
                total[0] += 1
            return original(address, size)
        f.readmem = count
        ctl.run()
        boundaries = total[0]
        self.assertGreater(boundaries, 30)
        self.doCleanups()
        for mode in ('transport', 'guard'):
            for at in range(1, boundaries+1):
                f, mem, ctl, journal = self.controller()
                trace = TraceProxy(f)
                ctl.i = ctl.p = trace
                original = f.readmem
                seen = [0]
                def read(address, size):
                    chosen = selected(ctl, address, size)
                    if chosen:
                        seen[0] += 1
                    if chosen and seen[0] == at and mode == 'transport':
                        raise TimeoutError('PRIVATE_SYNTHETIC bulk read')
                    value = original(address, size)
                    if chosen and seen[0] == at and mode == 'guard':
                        f.pending_fault = 1
                        f.put(0x110038, '<I', 1)
                    return value
                f.readmem = read
                with self.assertRaises((j.Refusal, TimeoutError)):
                    ctl.run()
                self.assertEqual(seen[0], at)
                self.assertEqual(f.hw, [])
                last = trace.requests[-1]
                if mode == 'transport':
                    self.assertEqual(last[0], 'readmem')
                else:
                    self.assertIn(last[0], ('call', 'get_exc_count'))
                    if last[0] == 'call':
                        self.assertEqual(last[1], ((t.HELPER_ADDR | 0xc0000000000)+96,
                                                   t.BASE+0x110038))
                self.doCleanups()

    def test_control_outer_deadline_survives_without_restore(self):
        f, mem, ctl, journal = self.controller()
        original = f.call
        def call(address, *args):
            if (address == (t.HELPER_ADDR | 0xc0000000000)+96 and
                    args == (t.BASE+0x90b00,) and f.control_stores == 1):
                raise j.Refusal('controller_deadline')
            return original(address, *args)
        f.call = call
        with self.assertRaisesRegex(j.Refusal, '^controller_deadline$'):
            ctl.run()
        self.assertEqual(f.control_stores, 1)
        self.assertEqual(f.read64(t.BASE+0x90b20), CONTROL_MARKER)
        self.assertEqual(f.hw, [])

    def test_cold_publication_at_callback_boundary_prevents_callback(self):
        f, mem, ctl, journal = self.controller()
        original = f.call
        def call(address, *args):
            if ctl.state['phase'] == 'cpu1_requests':
                f.cold_phase = 3
            return original(address, *args)
        f.call = call
        with self.assertRaisesRegex(j.Refusal, '^cold_entry_observed$'):
            ctl.run()
        self.assertTrue(ctl.state['cpu1_arrival_verified'])
        self.assertEqual(len(f.hw), 2)
        self.assertEqual(ctl.state['requests_completed'], 0)
        self.assertFalse(any(row[0] == 'publish' for row in f.writes))
        self.assertFalse(ctl.state['cold_observation']['park_verified'])

    def test_each_new_journal_failure_has_no_followup_target_operation(self):
        phases = ('cpu0_observer_control', 'cold_entry_permissions', 'cold_entry_publish')
        f, mem, ctl, journal = self.controller()
        selected = []
        previous = ctl.journal
        def count(state):
            if state['phase'] in phases:
                selected.append(state['phase'])
            previous(state)
        ctl.journal = count
        ctl.run()
        total = len(selected)
        self.assertEqual(total, 66)
        self.doCleanups()
        for at in range(1, total+1):
            f, mem, ctl, journal = self.controller()
            traced = TraceProxy(f)
            ctl.i = ctl.p = traced
            before = ctl.journal
            selected = [0]
            fault_boundary = []
            def fail(state):
                if state['phase'] in phases:
                    selected[0] += 1
                    if selected[0] == at:
                        fault_boundary.append(len(traced.requests))
                        raise OSError('PRIVATE_SYNTHETIC journal')
                before(state)
            ctl.journal = fail
            with self.assertRaises((j.Refusal, OSError)):
                ctl.run()
            self.assertEqual(len(fault_boundary), 1)
            self.assertEqual(len(traced.requests), fault_boundary[0])
            self.assertEqual(f.hw, [])
            self.assertNotIn('PRIVATE_SYNTHETIC', json.dumps(journal))
            self.doCleanups()


def archive():
    return plistlib.dumps([{'IOObjectClass': 'IOUSBHostDevice', 'idVendor': 0x1209,
        'idProduct': 0x316d, 'USB Serial Number': 'PRIVATE_SYNTHETIC',
        'IORegistryEntryChildren': [{'IOObjectClass': 'IOUSBHostInterface',
            'bInterfaceNumber': 1, 'bInterfaceClass': 10,
            'IORegistryEntryChildren': [{'IOObjectClass': 'IOSerialBSDClient',
                'IOCalloutDevice': '/dev/cu.usbmodemPRIVATE_SYNTHETIC'}]}]}])


class Clock:
    def __init__(self):
        self.value = 0.0
    def __call__(self):
        return self.value
    def sleep(self, value):
        self.value += value


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.object(j, 'ROOT', self.root))
        self.native = self.root / 'build/native-intake/attempt31k/consumed.jsonl'
        self.connect = self.native.with_name('connection.jsonl')
        self.stack.enter_context(patch.object(j, 'RECEIPT', self.native))
        self.stack.enter_context(patch.object(j, 'CONNECTION_RECEIPT', self.connect))
        self.stack.enter_context(patch.object(j, 'LIVE_READY', True))
        self.image = self.stack.enter_context(patch.object(j, 'verify_recorder'))
        self.sources = self.stack.enter_context(patch.object(j, 'verify_sources', return_value='synthetic-pin'))
        self.client = self.stack.enter_context(patch.object(j, 'verify_client'))
        self.signal = self.stack.enter_context(patch.object(j.signal, 'signal'))
        self.alarm = self.stack.enter_context(patch.object(j.signal, 'alarm'))
        self.stack.enter_context(patch.object(j.os, 'fsync'))
        self.transport = SimpleNamespace(timeout=None, write_timeout=None, close=Mock())
        self.iface = SimpleNamespace(dev=self.transport)
        self.serial = Mock(return_value=self.transport)
        self.uart = Mock(return_value=self.iface)
        self.uart.DEFAULT_BAUD_RATE = 115200
        self.proxy = Mock(return_value=object())
        self.backend = self.stack.enter_context(patch.object(j, 'load_client',
            return_value=(self.serial, self.uart, self.proxy)))
        self.controller = SimpleNamespace(state=dict(experiment='smp31k', phase='preflight',
            mutation_requests=0, start_writes_attempted=0, linux_boot='NOT RUN'),
            run=Mock(return_value=dict(experiment='smp31k', phase='complete',
                result='CPU1_ENTRY_AND_REQUESTS_PASS', mutation_requests=74,
                start_writes_attempted=2, linux_boot='NOT RUN')))
        self.construct = self.stack.enter_context(patch.object(j, 'Controller', return_value=self.controller))
        self.observation = dict(schema='usb_connection31j', ready=True,
            native_ready=False, device_opens=0, target_requests=0,
            observations=[], query_attempts=1, query_returns=1)
        self.discover = self.stack.enter_context(patch.object(j.connection, 'discover_primary',
            side_effect=self.discovered))

    def discovered(self, progress):
        progress(dict(self.observation, ready=False))
        return '/dev/cu.usbmodemPRIVATE_SYNTHETIC', dict(self.observation)

    def run_live(self):
        result = j.live(b'synthetic image', Path('synthetic-client'))
        text = json.dumps(result)
        if self.connect.exists():
            text += self.connect.read_text()
        if self.native.exists():
            text += self.native.read_text()
        for forbidden in ('PRIVATE_SYNTHETIC', '/dev/', '/Users/', 'Traceback'):
            self.assertNotIn(forbidden, text)
        self.assertLessEqual(self.serial.call_count, 1)
        return result

    def rows(self, path):
        return [json.loads(line) for line in path.read_text().splitlines()]

    def assert_preopen(self, result):
        self.assertFalse(result['native_attempt_consumed'])
        self.assertEqual(result['device_opens'], 0)
        self.assertFalse(result['connection']['serial_open_attempted'])
        self.assertNotIn('mutation_requests', result)
        self.assertNotIn('start_writes_attempted', result)
        self.serial.assert_not_called()
        self.construct.assert_not_called()
        self.assertFalse(self.native.exists())

    def test_hold_and_input_gates_precede_connection_reservation(self):
        with patch.object(j, 'LIVE_READY', False):
            with self.assertRaisesRegex(j.Refusal, 'native_release_not_ready'):
                j.live(b'', Path('unused'))
        self.image.assert_not_called()
        self.sources.assert_not_called()
        self.discover.assert_not_called()
        for checked in (self.image, self.sources, self.client):
            checked.side_effect = j.Refusal('synthetic_gate')
            with self.assertRaisesRegex(j.Refusal, 'synthetic_gate'):
                j.live(b'', Path('unused'))
            checked.side_effect = None
            self.assertFalse(self.connect.exists())
            self.assertFalse(self.native.exists())
        self.backend.assert_not_called()

    def test_success_order_precise_flags_and_private_path(self):
        def opened(*args, **kwargs):
            self.assertTrue(self.native.exists())
            latest = self.rows(self.connect)[-1]['connection']
            self.assertTrue(latest['native_attempt_consumed'])
            self.assertEqual(latest['phase'], 'serial_open')
            self.assertFalse(latest['serial_open_returned'])
            return self.transport
        self.serial.side_effect = opened
        result = self.run_live()
        self.assertEqual(result['result'], 'CPU1_ENTRY_AND_REQUESTS_PASS')
        self.assertTrue(result['native_attempt_consumed'])
        self.assertNotIn('device_opens', result)
        conn = result['connection']
        for field in ('discovery_completed', 'source_recheck_passed', 'client_import_returned',
                      'serial_open_attempted', 'serial_open_returned', 'uart_init_returned',
                      'controller_construction_attempted', 'controller_constructed', 'transport_closed'):
            self.assertTrue(conn[field], field)
        self.assertEqual(conn['discovery_scope'], 'cached_registry_only')
        self.assertEqual(conn['discovery_observation']['device_opens'], 0)
        self.assertEqual(self.sources.call_count, 2)
        self.assertEqual(self.client.call_count, 2)
        self.serial.assert_called_once_with('/dev/cu.usbmodemPRIVATE_SYNTHETIC', 115200,
                                            timeout=2, write_timeout=2)
        self.alarm.assert_any_call(60)
        self.assertEqual(self.alarm.call_args.args, (0,))
        phases = [row['connection']['phase'] for row in self.rows(self.connect)]
        for first, second in zip(('discovery', 'discovery_complete', 'source_recheck',
                                  'client_import', 'native_reservation', 'serial_open',
                                  'uart_init', 'controller_construction'),
                                 ('discovery_complete', 'source_recheck', 'client_import',
                                  'native_reservation', 'serial_open', 'uart_init',
                                  'controller_construction', 'controller_run')):
            self.assertLess(phases.index(first), phases.index(second))

    def test_discovery_refusal_has_only_connection_receipt_and_no_backend(self):
        failed = dict(self.observation, ready=False)
        self.discover.side_effect = j.connection.ConnectionRefusal('enumeration_unavailable', failed)
        result = self.run_live()
        self.assertEqual(result['reason'], 'enumeration_unavailable')
        self.assert_preopen(result)
        self.backend.assert_not_called()
        self.assertEqual(result['connection']['discovery_observation'], failed)
        self.assertTrue(self.connect.exists())

    def test_source_or_client_change_after_discovery_stops_before_import(self):
        for gate in ('sources', 'client'):
            with self.subTest(gate=gate):
                if self.connect.exists():
                    self.connect.unlink()  # Only an owned synthetic fixture.
                self.sources.side_effect = ['synthetic-pin', 'changed'] if gate == 'sources' else None
                self.client.side_effect = [None, j.Refusal('client_revision_or_dirty')] if gate == 'client' else None
                result = self.run_live()
                self.assertEqual(result['reason'], 'sources_changed_during_discovery'
                                 if gate == 'sources' else 'client_revision_or_dirty')
                self.assertTrue(result['connection']['discovery_completed'])
                self.assert_preopen(result)
                self.backend.assert_not_called()

    def test_import_failure_remains_preopen_and_unconsumed(self):
        self.backend.side_effect = RuntimeError('PRIVATE_SYNTHETIC import path')
        result = self.run_live()
        self.assertEqual(result['reason'], 'client_import_failed')
        self.assertTrue(result['connection']['client_import_attempted'])
        self.assertFalse(result['connection']['client_import_returned'])
        self.assert_preopen(result)

    def test_serial_failure_consumes_but_does_not_invent_open_count(self):
        self.serial.side_effect = OSError('PRIVATE_SYNTHETIC serial path')
        result = self.run_live()
        self.assertEqual(result['reason'], 'serial_open_failed')
        self.assertTrue(result['native_attempt_consumed'])
        self.assertTrue(result['connection']['serial_open_attempted'])
        self.assertFalse(result['connection']['serial_open_returned'])
        self.assertNotIn('device_opens', result)
        self.assertNotIn('mutation_requests', result)
        self.uart.assert_not_called()
        self.transport.close.assert_not_called()

    def test_late_connection_errors_close_once_and_never_rediscover(self):
        for mock, phase, attempted, returned in (
                (self.uart, 'uart_init', 'uart_init_attempted', 'uart_init_returned'),
                (self.proxy, 'proxy_init', 'proxy_init_attempted', 'proxy_init_returned'),
                (self.construct, 'controller_construction', 'controller_construction_attempted', 'controller_constructed')):
            with self.subTest(phase=phase):
                for path in (self.connect, self.native):
                    if path.exists():
                        path.unlink()
                for call in (self.serial, self.uart, self.proxy, self.construct, self.discover, self.transport.close):
                    call.reset_mock()
                mock.side_effect = RuntimeError('PRIVATE_SYNTHETIC')
                result = self.run_live()
                mock.side_effect = None
                self.assertEqual(result['reason'], phase + '_failed')
                self.assertTrue(result['native_attempt_consumed'])
                self.assertTrue(result['connection'][attempted])
                self.assertFalse(result['connection'][returned])
                self.assertNotIn('mutation_requests', result)
                self.discover.assert_called_once()
                self.serial.assert_called_once()
                self.transport.close.assert_called_once()

    def test_native_journal_forces_j_label_even_during_inherited_constructor(self):
        def construct(iface, proxy, image, journal):
            journal({'experiment': 'smp31b', 'phase': 'constructed'})
            return self.controller
        self.construct.side_effect = construct
        self.run_live()
        self.assertTrue(all(row['experiment'] == 'smp31k' for row in self.rows(self.native)))

    def test_outer_deadline_and_interrupt_provenance_survive_discovery(self):
        for cause, expected in ((j.Refusal('controller_deadline'), 'controller_deadline'),
                                (KeyboardInterrupt('PRIVATE_SYNTHETIC'), 'controller_interrupted')):
            if self.connect.exists():
                self.connect.unlink()
            report = dict(self.observation, ready=False, query_attempts=1)
            self.discover.side_effect = j.connection.ConnectionRefusal('progress_callback_failed', report,
                                                                       callback_exception=cause)
            result = self.run_live()
            self.assertEqual(result['reason'], expected)
            self.assertEqual(result['connection']['discovery_observation']['query_attempts'], 1)
            self.assert_preopen(result)

    def test_outer_deadline_during_transport_close_remains_visible(self):
        self.transport.close.side_effect = j.Refusal('controller_deadline')
        result = self.run_live()
        self.assertEqual(result['result'], 'STOP')
        self.assertEqual(result['reason'], 'controller_deadline')
        self.assertEqual(result['finalization_error'], 'controller_deadline')
        self.assertFalse(result['connection']['transport_closed'])

    def test_discovery_secondary_failures_cannot_mask_outer_deadline(self):
        for causes in ((j.Refusal('controller_deadline'), OSError('PRIVATE_SYNTHETIC')),
                       (ValueError('PRIVATE_SYNTHETIC'), j.Refusal('controller_deadline'))):
            if self.connect.exists():
                self.connect.unlink()
            report = dict(self.observation, ready=False, query_attempts=1)
            self.discover.side_effect = j.connection.ConnectionRefusal(
                'progress_callback_failed', report, interruptions=causes)
            result = self.run_live()
            self.assertEqual(result['reason'], 'controller_deadline')
            self.assertTrue(result['controller_deadline_observed'])
            self.assert_preopen(result)

    def test_exclusive_connection_receipt_prevents_any_discovery(self):
        self.connect.parent.mkdir(parents=True)
        self.connect.write_text('preserve')
        result = self.run_live()
        self.assertEqual(self.connect.read_text(), 'preserve')
        self.assertEqual(result['reason'], 'connection_receipt_already_exists')
        self.assert_preopen(result)
        self.discover.assert_not_called()
        self.backend.assert_not_called()

    def test_exclusive_native_receipt_is_preserved_without_open(self):
        self.native.parent.mkdir(parents=True)
        self.native.write_text('preserve')
        result = self.run_live()
        self.assertEqual(self.native.read_text(), 'preserve')
        self.assertEqual(result['reason'], 'native_receipt_already_exists')
        self.assertFalse(result['native_attempt_consumed'])
        self.assertTrue(result['connection']['native_reservation_attempted'])
        self.assertEqual(result['device_opens'], 0)
        self.serial.assert_not_called()

    def test_real_connection_module_through_live_wrapper(self):
        self.discover.side_effect = None
        # Recover the function shadowed by the setUp patch without importing a backend.
        spec = importlib.util.spec_from_file_location('real_connection_test31j',
            Path(j.__file__).resolve().parents[2] / 'tools/m1n1-client/usb_connection31j.py')
        real = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(real)
        cases = (([b'', archive()], None, True, 2, 'primary_verified'),
                 ([plistlib.dumps([]), archive()], None, True, 2, 'primary_verified'),
                 ([b'PRIVATE_SYNTHETIC'], None, False, 1, 'invalid_plist'),
                 ([b''] * 4, None, False, 4, 'enumeration_unavailable'),
                 ([], subprocess.TimeoutExpired('PRIVATE_SYNTHETIC', 3), False, 1, 'query_timeout'))
        original_lstat = Path.lstat
        def lstat(path):
            if str(path).startswith('/dev/cu.usbmodem'):
                return SimpleNamespace(st_mode=stat.S_IFCHR)
            return original_lstat(path)
        for outputs, error, succeeds, calls, reason in cases:
            with self.subTest(reason=reason, outputs=len(outputs)):
                for path in (self.connect, self.native):
                    if path.exists():
                        path.unlink()
                for call in (self.serial, self.backend, self.construct, self.transport.close):
                    call.reset_mock()
                clock = Clock()
                side_effect = error or [SimpleNamespace(stdout=raw, stderr=b'', returncode=0) for raw in outputs]
                with patch.object(j, 'connection', real), \
                        patch.object(real.sys, 'platform', 'darwin'), \
                        patch.object(real.subprocess, 'run', side_effect=side_effect) as query, \
                        patch.object(Path, 'lstat', autospec=True, side_effect=lstat), \
                        patch.object(real, 'discover_primary', wraps=lambda progress:
                            real._Discovery(progress, clock, clock.sleep).run()):
                    result = self.run_live()
                self.assertEqual(query.call_count, calls)
                self.assertEqual(result['connection']['discovery_observation']['reason'], reason)
                if succeeds:
                    self.assertEqual(result['result'], 'CPU1_ENTRY_AND_REQUESTS_PASS')
                    self.serial.assert_called_once()
                    self.assertTrue(result['native_attempt_consumed'])
                else:
                    self.assert_preopen(result)
                    self.backend.assert_not_called()

    def test_connection_journal_failure_retains_progress_and_stops(self):
        original = j.reserve_journal
        report = dict(self.observation, ready=False, query_attempts=1)
        def discover(progress):
            progress(report)
            raise AssertionError('Must stop on journal failure')
        self.discover.side_effect = discover
        def reserve(path, initial, on_created=None):
            stream, journal = original(path, initial, on_created)
            def checked(row):
                if row.get('connection', {}).get('discovery_observation'):
                    raise OSError('PRIVATE_SYNTHETIC journal')
                journal(row)
            return stream, checked
        with patch.object(j, 'reserve_journal', side_effect=reserve):
            result = self.run_live()
        self.assertEqual(result['reason'], 'connection_journal_failed')
        self.assertEqual(result['connection']['discovery_observation'], report)
        self.assertTrue(result['connection']['connection_journal_failed'])
        self.assert_preopen(result)

    def test_native_reservation_write_failure_is_still_consumed(self):
        original = j.reserve_journal
        def reserve(path, initial, on_created=None):
            if path == self.native:
                with patch.object(j.os, 'fsync', side_effect=OSError('PRIVATE_SYNTHETIC')):
                    return original(path, initial, on_created)
            return original(path, initial, on_created)
        with patch.object(j, 'reserve_journal', side_effect=reserve):
            result = self.run_live()
        self.assertTrue(self.native.exists())
        self.assertTrue(result['native_attempt_consumed'])
        self.assertEqual(result['device_opens'], 0)
        self.serial.assert_not_called()

    def test_final_journal_deadline_does_not_become_success(self):
        original = j.reserve_journal
        def reserve(path, initial, on_created=None):
            stream, journal = original(path, initial, on_created)
            def checked(row):
                if path == self.native and 'controller_elapsed_seconds' in row:
                    raise j.Refusal('controller_deadline')
                journal(row)
            return stream, checked
        with patch.object(j, 'reserve_journal', side_effect=reserve):
            result = self.run_live()
        self.assertEqual(result['result'], 'STOP')
        self.assertEqual(result['reason'], 'controller_deadline')
        self.assertTrue(result['connection']['native_journal_failed'])

    def test_cleanup_failure_cannot_erase_deadline_after_controller_failure(self):
        self.controller.run.side_effect = j.Refusal('cpu1_arrival_timeout')
        self.transport.close.side_effect = j.Refusal('controller_deadline')
        original = j.reserve_journal
        def reserve(path, initial, on_created=None):
            stream, journal = original(path, initial, on_created)
            def checked(row):
                if path == self.native and 'controller_elapsed_seconds' in row:
                    raise OSError('PRIVATE_SYNTHETIC')
                journal(row)
            return stream, checked
        with patch.object(j, 'reserve_journal', side_effect=reserve):
            result = self.run_live()
        self.assertEqual(result['reason'], 'cpu1_arrival_timeout')
        self.assertEqual(result['finalization_error'], 'controller_deadline')
        self.assertTrue(result['controller_deadline_observed'])
        self.assertTrue(result['connection']['native_journal_failed'])

    def test_main_is_offline_by_default_and_has_own_token(self):
        image = self.root / 'synthetic.bin'
        image.write_bytes(b'synthetic')
        common = ['smp31k.py', '--image', str(image)]
        with contextlib.redirect_stdout(io.StringIO()), patch.object(j, 'live') as live:
            with patch.object(sys, 'argv', common):
                self.assertEqual(j.main(), 0)
            self.discover.assert_not_called()
            live.assert_not_called()
            with patch.object(sys, 'argv', common + ['--live', '--confirm', frozen.h.CONFIRM]):
                with self.assertRaisesRegex(j.Refusal, 'confirmation'):
                    j.main()
            with patch.object(sys, 'argv', common + ['--live', '--confirm', j.CONFIRM]):
                live.return_value = {'result': 'CPU1_ENTRY_AND_REQUESTS_PASS'}
                self.assertEqual(j.main(), 0)
            live.assert_called_once_with(b'synthetic', self.root / 'third_party/m1n1')
        self.assertNotEqual(j.CONFIRM, frozen.h.CONFIRM)
        self.assertNotEqual(j.RECEIPT, frozen.h.RECEIPT)


class SourceTests(unittest.TestCase):
    def test_sources_bind_the_new_intake(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(j, 'ROOT', Path(tmp)):
            with self.assertRaisesRegex(j.Refusal, 'source_intake_missing'):
                j.verify_sources()
            path = Path(tmp) / 'tools/m1n1-client/attempt31k-offline.py'
            path.parent.mkdir(parents=True)
            path.write_text('synthetic')
            intake = SimpleNamespace(source_pins=Mock(return_value=([], 'new-digest')))
            with patch.object(j, 'module', return_value=intake) as load:
                self.assertEqual(j.verify_sources(), 'new-digest')
                load.assert_called_once_with('intake31k', 'tools/m1n1-client/attempt31k-offline.py')
                intake.source_pins.assert_called_once_with(Path(tmp))


if __name__ == '__main__':
    unittest.main()
