"""31H synthetic lifecycle and dispatch tests: no USB or native execution.

Inherits every frozen31G lifecycle/fault regression and adds command parity,
partial preflight evidence, privacy and local-entrypoint checks. The model
cannot establish the semantics of unknown RVBAR bits or CPU reset behavior.
"""
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31h as h
import test_smp31g as previous

prior, t = previous.prior, previous.t


class Fake(previous.Fake):
    def __init__(self):
        super().__init__()
        self.rvbar_words = [t.BASE | 1, t.BASE | 1]
        self.rvbar_reads = []
        self.rvbar_fail_at = self.rvbar_trap_at = self.rvbar_ack_fail_at = None
        self.rvbar_ack_pending = None
        self.state_read_count = 0
        self.state_fail_at = self.state_trap_at = self.state_delay_at = None
        self.state_bad_translation = False

    def state_read(self, address):
        assert address in (0x210050100, 0x210150100)
        self.state_read_count += 1
        if self.state_read_count == self.state_fail_at:
            raise TimeoutError('private state transport detail')
        if self.state_read_count == self.state_trap_at:
            self.pending_fault = 1
            self.put(0x110038, '<I', 1)
        return 0x12345610 if address == 0x210050100 or len(self.hw) == 2 else 0x12345600

    def read32(self, address):
        if address in (0x210050100, 0x210150100):
            assert not self.hw, 'guarded state read after start'
            return self.state_read(address)
        return super().read32(address)

    def call(self, address, *args):
        offset = address - (t.HELPER_ADDR | 0xc0000000000)
        if args and args[0] in (0x210050100, 0x210150100):
            assert len(args) == 1
            if offset in (192, 256):
                assert self.power_ready and not self.hw
                return 1 if self.state_bad_translation else args[0] & ~0xfff
            assert offset == 384 and self.power_ready and self.hw
            return self.state_read(args[0])
        return super().call(address, *args)

    def read64(self, address):
        if address in (0x210050000, 0x210150000):
            assert not self.hw, 'RVBAR read after CPU1 start'
            self.rvbar_reads.append(address)
            number = len(self.rvbar_reads)
            if number == self.rvbar_fail_at:
                raise TimeoutError('private raw transport detail')
            self.rvbar_ack_pending = number
            if number == self.rvbar_trap_at:
                self.pending_fault = 1
            return self.rvbar_words[number - 1]
        return super().read64(address)

    def get_exc_count(self):
        pending, self.rvbar_ack_pending = self.rvbar_ack_pending, None
        if pending is not None and pending == self.rvbar_ack_fail_at:
            raise TimeoutError('private raw guard detail')
        return super().get_exc_count()


class TraceProxy:
    """Record only external iface/proxy requests, not model internals."""
    def __init__(self, wrapped):
        self.wrapped, self.requests = wrapped, []

    def __getattr__(self, name):
        member = getattr(self.wrapped, name)
        if not callable(member):
            return member

        def call(*args, **kwargs):
            self.requests.append((name, args, kwargs))
            return member(*args, **kwargs)
        return call


class ControllerTests(previous.ControllerTests):
    def controller(self, controller_class=None):
        image = bytearray(t.IMAGE)
        struct.pack_into('<I', image, 0, 0xd2800609)
        self.keep_patch(patch.object(t, 'IMAGE', bytes(image)))
        self.keep_patch(patch.object(t, 'Fake', Fake))
        self.keep_patch(patch.object(prior.c, 'Controller', controller_class or h.Controller))
        self.keep_patch(patch.object(previous.e.binding, 'read', return_value=dict(live_adt_bound=True)))
        return prior.RamTests.high_controller(self)

    def test_31h_preserves_31g_mutations_and_only_adds_bound_state_reads(self):
        for arrives in (True, False):
            traces, results = [], []
            for cls in (previous.e.Controller, h.Controller):
                f, mem, ctl, journal = self.controller(cls)
                f.arrival = arrives
                traced = TraceProxy(f)
                ctl.i = ctl.p = traced
                if arrives:
                    result = ctl.run()
                else:
                    with self.assertRaisesRegex(h.Refusal, 'cpu1_arrival_timeout'):
                        ctl.run()
                    result = ctl.state
                self.assertIs(ctl.p, traced)
                self.assertEqual(f.rvbar_reads, [0x210050000, 0x210150000])
                traces.append(traced.requests)
                results.append(result)
                self.doCleanups()
            # Compare every write/cache/start operation independently of the
            # added observation/diagnostic reads. Startup mutability is unchanged.
            def mutations(trace):
                return [(n, a, k) for n, a, k in trace if n in
                        ('write32', 'write64', 'writemem', 'dc_cvac', 'dc_cvau',
                         'ic_ivau', 'smp_set_wfe_mode', 'memalign') or
                        (n == 'call' and a[0] - (t.HELPER_ADDR | 0xc0000000000) in (160, 352))]
            self.assertEqual(mutations(traces[0]), mutations(traces[1]))
            extra = [row for row in traces[1] if row[0] in ('read32', 'call') and
                     any(value in (0x210050100, 0x210150100) for value in row[1])]
            self.assertEqual(len(extra), 10)  # 2 translations + 8 reads
            self.assertEqual(results[1]['mutation_requests'], 74 if arrives else 66)
            self.assertEqual(results[1]['start_writes_attempted'], 2)
            self.assertEqual(results[1]['requests_completed'], 8 if arrives else 0)
            for key in ('power_observation', 'recorder_observation', 'park_verified',
                        'entry_observation', 'linux_boot', 'request_roundtrips_ms'):
                self.assertEqual(results[0][key], results[1][key])

    def test_31h_retains_classification_and_mirror_equality(self):
        for bits, expected in ((0, 'zero'), (0x800, 'bit11_only'), (2, 'other')):
            f, mem, ctl, journal = self.controller()
            f.rvbar_words = [t.BASE | 1, t.BASE | 1 | bits | (1 << 63)]
            with self.assertRaisesRegex(h.Refusal, 'reset_format_requires_review'):
                ctl.run()
            report = ctl.state['rvbar_observation']
            self.assertEqual(report['state'], 'complete')
            self.assertEqual(report['validated_reads'], 2)
            self.assertEqual(report['read_attempts'], 2)
            self.assertFalse(report['mirrors_equal'])
            self.assertEqual(report['rows'][1]['unknown_low_bits_class'], expected)
            self.assertTrue(report['rows'][1]['unknown_upper_bits_present'])
            self.assertEqual(report['exact_entry_offset'], 'UNKNOWN')
            self.assertEqual(report['effective_reset_route'], 'UNKNOWN')
            self.assertFalse(ctl.state['restart_ready'])
            self.assertEqual(ctl.state['experiment'], 'smp31h')
            self.assertEqual(f.mutations, 0)
            self.assertEqual(f.state_read_count, 0)
            self.assertIs(ctl.p, f)
            payload = json.dumps(journal)
            for word in f.rvbar_words:
                self.assertNotIn(str(word), payload)
                self.assertNotIn(hex(word), payload)
            self.assertNotIn('private', payload)
            self.doCleanups()

    def test_cpu_state_all_read_failures_preserve_prefix_and_stop(self):
        for failure in ('state_fail_at', 'state_trap_at'):
            for at in range(1, 9):
                f, mem, ctl, journal = self.controller()
                setattr(f, failure, at)
                with self.assertRaises((TimeoutError, h.Refusal)):
                    ctl.run()
                report = ctl.state['cpu_state_observation']
                self.assertEqual(report['reads_attempted'], at)
                self.assertEqual(report['reads_completed'], at - 1)
                self.assertIsNotNone(report['error'])
                self.assertEqual(f.state_read_count, at)
                self.assertEqual(len(f.hw), 0 if at <= 2 else 1 if at <= 4 else 2)
                self.assertNotIn('private', json.dumps(journal))
                self.assertNotIn(str(0x12345610), json.dumps(journal))
                self.doCleanups()

    def test_cpu_state_translation_failure_prevents_first_access_and_start(self):
        f, mem, ctl, journal = self.controller()
        f.state_bad_translation = True
        with self.assertRaises(h.Refusal):
            ctl.run()
        self.assertEqual(f.state_read_count, 0)
        self.assertEqual(f.hw, [])

    def test_cpu_state_delayed_read_stops_before_followup(self):
        f, mem, ctl, journal = self.controller()
        original = f.state_read
        def delayed(address):
            value = original(address)
            ctl.sleep(1.1)
            return value
        f.state_read = delayed
        traced = TraceProxy(f)
        ctl.p = traced
        with self.assertRaisesRegex(h.Refusal, 'cpu_state_observation_deadline'):
            ctl.run()
        self.assertEqual(f.state_read_count, 1)
        self.assertEqual(f.hw, [])
        self.assertEqual(ctl.state['cpu_state_observation']['reads_completed'], 0)
        self.assertEqual(traced.requests[-1], ('read32', (0x210050100,), {}))

    def test_cpu_state_journal_failure_retains_terminal_flag_without_more_reads(self):
        for completed in (0, 1):
            f, mem, ctl, journal = self.controller()
            original = ctl.journal
            def failed(state):
                row = state.get('cpu_state_observation', {})
                if row.get('reads_attempted') == 1 and row.get('reads_completed') == completed:
                    raise OSError('private journal detail')
                original(state)
            ctl.journal = failed
            with self.assertRaisesRegex(h.Refusal, 'cpu_state_journal_failed'):
                ctl.run()
            report = ctl.state['cpu_state_observation']
            self.assertTrue(report['journal_failed'])
            self.assertEqual(report['error'], 'cpu_state_journal_failed')
            self.assertEqual(f.state_read_count, completed)
            self.assertEqual(f.hw, [])
            self.doCleanups()

    def test_cpu_state_timeout_final_failure_preserves_arrival_reason(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        f.state_fail_at = 7
        with self.assertRaisesRegex(h.Refusal, '^cpu1_arrival_timeout$'):
            ctl.run()
        self.assertEqual(ctl.state['terminal_observation_error'], 'cpu_state_read_failed')
        self.assertEqual(f.state_read_count, 7)
        self.assertEqual(ctl.state['cpu_state_observation']['reads_completed'], 6)

    def test_outer_controller_deadline_during_persistence_keeps_reason(self):
        for completed in (0, 1):
            f, mem, ctl, journal = self.controller()
            original = ctl.journal
            def expired(state):
                row = state.get('cpu_state_observation', {})
                if row.get('reads_attempted') == 1 and row.get('reads_completed') == completed:
                    raise h.Refusal('controller_deadline')
                original(state)
            ctl.journal = expired
            with self.assertRaisesRegex(h.Refusal, '^controller_deadline$'):
                ctl.run()
            self.assertTrue(ctl.state['cpu_state_observation']['journal_failed'])
            self.assertEqual(f.state_read_count, completed)
            self.assertEqual(f.hw, [])
            self.doCleanups()

    def test_31h_read_intent_is_journaled_before_dispatch_and_ack(self):
        f, mem, ctl, journal = self.controller()
        read, ack = f.read64, f.get_exc_count

        def reading(address):
            if address in (0x210050000, 0x210150000):
                record = journal[-1]['rvbar_observation']
                self.assertEqual(record['read_attempts'], len(f.rvbar_reads) + 1)
                self.assertEqual(record['validated_reads'], len(f.rvbar_reads))
            return read(address)

        def acknowledging():
            if f.rvbar_ack_pending is not None:
                record = journal[-1]['rvbar_observation']
                self.assertEqual(record['guard_check_attempts'], f.rvbar_ack_pending)
                self.assertEqual(record['validated_reads'], f.rvbar_ack_pending - 1)
            return ack()

        f.read64, f.get_exc_count = reading, acknowledging
        ctl.run()
        self.assertTrue(ctl.state['rvbar_observation']['mirrors_equal'])

    def test_31h_partial_read_and_guard_failures_stop_before_mutation(self):
        for field, reason in (('rvbar_fail_at', 'rvbar_read_failed'),
                              ('rvbar_trap_at', 'rvbar_exception_ack_nonzero_or_invalid'),
                              ('rvbar_ack_fail_at', 'rvbar_exception_ack_failed')):
            for at in (1, 2):
                with self.subTest(field=field, at=at):
                    f, mem, ctl, journal = self.controller()
                    setattr(f, field, at)
                    with self.assertRaisesRegex(h.Refusal, reason):
                        ctl.run()
                    report = ctl.state['rvbar_observation']
                    self.assertEqual(report['validated_reads'], at - 1)
                    self.assertEqual(report['read_attempts'], at)
                    self.assertEqual(report['error'], reason)
                    self.assertIsNone(report['pending_cpu_id'])
                    self.assertIs(ctl.p, f)
                    self.assertEqual(f.mutations, 0)
                    self.assertEqual(f.hw, [])
                    self.assertNotIn('private', json.dumps(journal))
                    before = list(f.rvbar_reads)
                    with self.assertRaisesRegex(h.Refusal, 'already_used'):
                        ctl.run()
                    self.assertEqual(f.rvbar_reads, before)
                    self.doCleanups()

    def test_31h_malformed_read_is_not_validated_before_guard_reply(self):
        for word in (0, (1 << 64) - 1, 0xbad0bad0bad0bad0, True, -1, 1 << 64):
            f, mem, ctl, journal = self.controller()
            f.rvbar_words[1] = word
            with self.assertRaises(h.Refusal):
                ctl.run()
            report = ctl.state['rvbar_observation']
            self.assertEqual(report['validated_reads'], 1)
            self.assertEqual(report['guard_check_attempts'], 2)
            self.assertEqual(f.mutations, 0)
            self.assertIs(ctl.p, f)
            self.doCleanups()

    def test_31h_inherited_rvbar_gates_remain_effective(self):
        for word in (lambda: t.BASE, lambda: (t.BASE + 0x1000) | 1):
            f, mem, ctl, journal = self.controller()
            f.rvbar_words[1] = word()
            with self.assertRaises(h.Refusal):
                ctl.run()
            self.assertEqual(ctl.state['rvbar_observation']['validated_reads'], 2)
            self.assertIs(ctl.p, f)
            self.assertEqual(f.mutations, 0)
            self.doCleanups()

    def test_31h_outer_preflight_failure_and_interrupt_restore_proxy(self):
        for exc in (h.Refusal('outer_preflight'), KeyboardInterrupt()):
            f, mem, ctl, journal = self.controller()
            with patch.object(previous.e.Controller, 'preflight', side_effect=exc):
                with self.assertRaises(type(exc)):
                    ctl.run()
            self.assertIs(ctl.p, f)
            self.assertEqual(ctl.state['rvbar_observation']['error'], 'rvbar_preflight_aborted')
            self.assertEqual(f.mutations, 0)
            self.doCleanups()

    def test_31h_observation_journal_failure_prevents_read(self):
        f, mem, ctl, journal = self.controller()
        original = ctl.journal

        def failed(state):
            if state.get('rvbar_observation', {}).get('read_attempts') == 1:
                raise OSError('private journal path')
            original(state)

        ctl.journal = failed
        with self.assertRaisesRegex(h.Refusal, 'rvbar_journal_failed'):
            ctl.run()
        self.assertIs(ctl.p, f)
        self.assertEqual(f.rvbar_reads, [])
        self.assertEqual(f.mutations, 0)


class EntryTests(unittest.TestCase):
    def test_live_release_hold_precedes_receipt_or_transport(self):
        with patch.object(h, 'LIVE_READY', False), patch.object(h, 'reserve') as reserve, patch.object(h.subprocess, 'check_output') as git:
            with self.assertRaisesRegex(h.Refusal, 'native_release_not_ready'):
                h.live(b'', Path('unused'))
            reserve.assert_not_called()
            git.assert_not_called()

    def test_31h_receipt_is_distinct_exclusive_and_preserves_31g(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(h, 'ROOT', Path(tmp)):
            old = Path(tmp) / 'build/native-intake/attempt31g/consumed.jsonl'
            old.parent.mkdir(parents=True)
            old.write_text('preserve')
            receipt = Path(tmp) / 'build/native-intake/attempt31h/consumed.jsonl'
            with patch.object(h, 'RECEIPT', receipt):
                stream, _ = h.reserve()
                stream.close()
                with self.assertRaises(FileExistsError):
                    h.reserve()
            self.assertEqual(old.read_text(), 'preserve')
            self.assertEqual(json.loads(receipt.read_text())['experiment'], 'smp31h')
        self.assertNotEqual(h.CONFIRM, previous.e.CONFIRM)
        self.assertNotEqual(h.RECEIPT, previous.e.RECEIPT)

    def test_live_uses_local_controller_and_closes_synthetic_transport(self):
        transport = SimpleNamespace(timeout=None, write_timeout=None, close=Mock())
        iface = SimpleNamespace(dev=transport)
        proxy = object()
        fake = ModuleType('m1n1.proxy')
        fake.Serial = Mock(return_value=transport)
        fake.UartInterface = Mock(return_value=iface)
        fake.UartInterface.DEFAULT_BAUD_RATE = 115200
        fake.M1N1Proxy = Mock(return_value=proxy)
        result = dict(experiment='smp31h', result='CPU1_ENTRY_AND_REQUESTS_PASS', linux_boot='NOT RUN')
        controller = SimpleNamespace(run=Mock(return_value=result), state=result)
        stream, journal = io.StringIO(), Mock()
        saved_path = list(sys.path)
        try:
            with patch.dict(sys.modules, {'m1n1.proxy': fake}), \
                    patch.object(h, 'LIVE_READY', True), \
                    patch.object(h.subprocess, 'check_output', side_effect=[h.core.census.launch.M1N1_COMMIT, b'']), \
                    patch.object(h, 'reserve', return_value=(stream, journal)), \
                    patch.object(h.signal, 'signal'), patch.object(h.signal, 'alarm'), \
                    patch.object(h.core.census.launch.usb_identity, 'discover', return_value=[]), \
                    patch.object(h.core.census.launch.usb_identity, 'select_primary', return_value='synthetic'), \
                    patch.object(h, 'Controller', return_value=controller) as selected, \
                    patch.object(previous.e, 'Controller', side_effect=AssertionError('wrong controller')):
                actual = h.live(b'synthetic image', Path('synthetic-client'))
                selected.assert_called_once_with(iface, proxy, b'synthetic image', journal)
                controller.run.assert_called_once_with()
                self.assertEqual(actual['experiment'], 'smp31h')
                self.assertEqual(actual['result'], 'CPU1_ENTRY_AND_REQUESTS_PASS')
                transport.close.assert_called_once_with()
                self.assertTrue(stream.closed)
                fake.Serial.assert_called_once_with('synthetic', 115200, timeout=2, write_timeout=2)
        finally:
            sys.path[:] = saved_path

    def test_main_dispatch_and_confirmation_are_local_and_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'synthetic.bin'
            image.write_bytes(b'synthetic')
            common = ['smp31h.py', '--image', str(image)]
            with patch.object(h, 'LIVE_READY', False), patch.object(h.previous, 'verify_recorder'), \
                    patch.object(h, 'verify_sources', return_value='synthetic-pin'), \
                    patch.object(h, 'live') as live, contextlib.redirect_stdout(io.StringIO()):
                with patch.object(sys, 'argv', common):
                    self.assertEqual(h.main(), 0)
                live.assert_not_called()
                with patch.object(sys, 'argv', common + ['--live', '--confirm', previous.e.CONFIRM]):
                    with self.assertRaisesRegex(h.Refusal, 'confirmation'):
                        h.main()
                with patch.object(sys, 'argv', common + ['--live', '--confirm', h.CONFIRM]):
                    with self.assertRaisesRegex(h.Refusal, 'native_release_not_ready'):
                        h.main()
                live.assert_not_called()
                with patch.object(h, 'LIVE_READY', True), \
                        patch.object(sys, 'argv', common + ['--live', '--confirm', h.CONFIRM]):
                    live.return_value = {'result': 'CPU1_ENTRY_AND_REQUESTS_PASS'}
                    self.assertEqual(h.main(), 0)
                live.assert_called_once_with(b'synthetic', h.ROOT / 'third_party/m1n1')

    def test_sources_require_new_intake_and_propagate_only_fixed_refusal(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(h, 'ROOT', Path(tmp)):
            with self.assertRaisesRegex(h.Refusal, 'source_intake_missing'):
                h.verify_sources()
            path = Path(tmp) / 'tools/m1n1-client/attempt31h-offline.py'
            path.parent.mkdir(parents=True)
            path.write_text('synthetic')
            intake = SimpleNamespace(source_pins=Mock(return_value=([], 'new-digest')))
            with patch.object(h, 'module', return_value=intake) as load:
                self.assertEqual(h.verify_sources(), 'new-digest')
                load.assert_called_once_with('intake31h', 'tools/m1n1-client/attempt31h-offline.py')
                intake.source_pins.assert_called_once_with(Path(tmp))
                intake.source_pins.side_effect = ValueError('source_digest_mismatch')
                with self.assertRaisesRegex(h.Refusal, 'source_digest_mismatch'):
                    h.verify_sources()


if __name__ == '__main__':
    unittest.main()
