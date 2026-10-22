"""31I synthetic lifecycle, fixed-operation parity and isolated entrypoint tests.

Inherits the frozen 31H fault/lifecycle regressions. Native behavior and upper
field semantics remain unproved; these tests exercise only original software.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31i as h
import test_smp31h as frozen
previous, prior, t = frozen.previous, frozen.prior, frozen.t
Fake, TraceProxy = frozen.Fake, frozen.TraceProxy


class ControllerTests(frozen.ControllerTests):
    def controller(self, controller_class=None):
        return super().controller(controller_class or h.Controller)

    def test_31h_preserves_31g_mutations_and_only_adds_bound_state_reads(self):
        # Replace the inherited G/H comparison with exact H/I transaction parity.
        for arrives in (True, False):
            traces, results = [], []
            for cls, high in ((frozen.h.Controller, 0), (h.Controller, 1 << 63)):
                f, mem, ctl, journal = self.controller(cls)
                f.arrival = arrives
                f.rvbar_words = [t.BASE | 1 | high] * 2
                traced = TraceProxy(f)
                ctl.i = ctl.p = traced
                if arrives:
                    result = ctl.run()
                else:
                    with self.assertRaisesRegex(h.Refusal, '^cpu1_arrival_timeout$'):
                        ctl.run()
                    result = ctl.state
                traces.append(traced.requests)
                results.append(result)
                self.assertEqual(f.state_read_count, 8)
                self.assertEqual(result['start_writes_attempted'], 2)
                self.doCleanups()
            self.assertEqual(traces[0], traces[1])
            self.assertEqual(results[1]['experiment'], 'smp31i')
            self.assertEqual(results[1]['mutation_requests'], 74 if arrives else 66)
            self.assertEqual(results[1]['requests_completed'], 8 if arrives else 0)
            for key in ('power_observation', 'cpu_state_observation',
                        'recorder_observation', 'park_verified', 'entry_observation'):
                self.assertEqual(results[0][key], results[1][key])
            observed = results[1]['rvbar_observation']
            self.assertTrue(observed['mirrors_equal'])
            self.assertTrue(all(row['unknown_upper_bits_present'] for row in observed['rows']))
            self.assertTrue(results[1]['reset_format_gate_passed'])
            self.assertTrue(results[1]['reset_readback_decision'])
            self.assertEqual(observed['effective_reset_route'], 'UNKNOWN')

    def test_31h_retains_classification_and_mirror_equality(self):
        # Mismatched mirrors still refuse even when only upper fields differ.
        for bits in (0, 0x800, 2):
            f, mem, ctl, journal = self.controller()
            f.rvbar_words = [t.BASE | 1, t.BASE | 1 | bits | (1 << 63)]
            with self.assertRaisesRegex(h.Refusal, '^reset_format_requires_review$'):
                ctl.run()
            self.assertEqual(ctl.state['experiment'], 'smp31i')
            self.assertFalse(ctl.state['rvbar_observation']['mirrors_equal'])
            self.assertFalse(ctl.state['reset_format_gate_passed'])
            self.assertEqual(ctl.state['reset_readback_decision'], {})
            self.assertEqual(f.mutations, 0)
            self.assertEqual(f.state_read_count, 0)
            self.assertEqual(f.hw, [])
            self.doCleanups()

    def test_equal_mirrors_do_not_allow_wrong_address_or_low_fields(self):
        for bits in (0x800, 2, 1 << 42, 1 << 47, 1 << 12):
            f, mem, ctl, journal = self.controller()
            f.rvbar_words = [t.BASE | 1 | (1 << 63) | bits] * 2
            with self.assertRaises(h.Refusal):
                ctl.run()
            self.assertEqual(f.mutations, 0)
            self.assertEqual(f.state_read_count, 0)
            self.assertEqual(f.hw, [])
            self.assertIs(ctl.p, f)
            self.doCleanups()

    def test_upper_fields_never_relax_guard_acknowledgements(self):
        for field in ('rvbar_fail_at', 'rvbar_trap_at', 'rvbar_ack_fail_at'):
            for at in (1, 2):
                f, mem, ctl, journal = self.controller()
                f.rvbar_words = [t.BASE | 1 | (1 << 63)] * 2
                setattr(f, field, at)
                with self.assertRaises(h.Refusal):
                    ctl.run()
                self.assertEqual(f.mutations, 0)
                self.assertEqual(f.state_read_count, 0)
                self.assertEqual(ctl.state['rvbar_observation']['validated_reads'], at - 1)
                self.assertIs(ctl.p, f)
                self.doCleanups()

    def test_preflight_never_calls_or_reconfigures_consumed31h_gate(self):
        f, mem, ctl, journal = self.controller()
        f.rvbar_words = [t.BASE | 1 | (1 << 63)] * 2
        with patch.object(frozen.h.Controller, 'preflight',
                          side_effect=AssertionError('consumed31H gate called')):
            result = ctl.run()
        self.assertEqual(result['result'], 'CPU1_ENTRY_AND_REQUESTS_PASS')
        self.assertEqual(f.state_read_count, 8)


class EntryTests(unittest.TestCase):
    def test_live_release_hold_precedes_receipt_or_transport(self):
        with patch.object(h, 'LIVE_READY', False), patch.object(h, 'reserve') as reserve, patch.object(h.subprocess, 'check_output') as git:
            with self.assertRaisesRegex(h.Refusal, 'native_release_not_ready'):
                h.live(b'', Path('unused'))
            reserve.assert_not_called()
            git.assert_not_called()

    def test_31i_receipt_is_distinct_exclusive_and_preserves_31h(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(h, 'ROOT', Path(tmp)):
            old = Path(tmp) / 'build/native-intake/attempt31h/consumed.jsonl'
            old.parent.mkdir(parents=True)
            old.write_text('preserve')
            receipt = Path(tmp) / 'build/native-intake/attempt31i/consumed.jsonl'
            with patch.object(h, 'RECEIPT', receipt):
                stream, _ = h.reserve()
                stream.close()
                with self.assertRaises(FileExistsError):
                    h.reserve()
            self.assertEqual(old.read_text(), 'preserve')
            self.assertEqual(json.loads(receipt.read_text())['experiment'], 'smp31i')
        self.assertNotEqual(h.CONFIRM, frozen.h.CONFIRM)
        self.assertNotEqual(h.RECEIPT, frozen.h.RECEIPT)

    def test_live_uses_local_controller_and_closes_synthetic_transport(self):
        transport = SimpleNamespace(timeout=None, write_timeout=None, close=Mock())
        iface = SimpleNamespace(dev=transport)
        proxy = object()
        fake = ModuleType('m1n1.proxy')
        fake.Serial = Mock(return_value=transport)
        fake.UartInterface = Mock(return_value=iface)
        fake.UartInterface.DEFAULT_BAUD_RATE = 115200
        fake.M1N1Proxy = Mock(return_value=proxy)
        result = dict(experiment='smp31i', result='CPU1_ENTRY_AND_REQUESTS_PASS', linux_boot='NOT RUN')
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
                    patch.object(frozen.h, 'Controller', side_effect=AssertionError('wrong controller')):
                actual = h.live(b'synthetic image', Path('synthetic-client'))
                selected.assert_called_once_with(iface, proxy, b'synthetic image', journal)
                controller.run.assert_called_once_with()
                self.assertEqual(actual['experiment'], 'smp31i')
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
            common = ['smp31i.py', '--image', str(image)]
            with patch.object(h, 'LIVE_READY', False), patch.object(h, 'verify_recorder'), \
                    patch.object(h, 'verify_sources', return_value='synthetic-pin'), \
                    patch.object(h, 'live') as live, contextlib.redirect_stdout(io.StringIO()):
                with patch.object(sys, 'argv', common):
                    self.assertEqual(h.main(), 0)
                live.assert_not_called()
                with patch.object(sys, 'argv', common + ['--live', '--confirm', frozen.h.CONFIRM]):
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
            path = Path(tmp) / 'tools/m1n1-client/attempt31i-offline.py'
            path.parent.mkdir(parents=True)
            path.write_text('synthetic')
            intake = SimpleNamespace(source_pins=Mock(return_value=([], 'new-digest')))
            with patch.object(h, 'module', return_value=intake) as load:
                self.assertEqual(h.verify_sources(), 'new-digest')
                load.assert_called_once_with('intake31i', 'tools/m1n1-client/attempt31i-offline.py')
                intake.source_pins.assert_called_once_with(Path(tmp))
                intake.source_pins.side_effect = ValueError('source_digest_mismatch')
                with self.assertRaisesRegex(h.Refusal, 'source_digest_mismatch'):
                    h.verify_sources()


if __name__ == '__main__':
    unittest.main()
