"""31J target parity and host connection lifecycle; synthetic data only."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31j as j
import test_smp31i as frozen

t, TraceProxy = frozen.t, frozen.TraceProxy


class ControllerTests(frozen.ControllerTests):
    def controller(self, controller_class=None):
        return super().controller(controller_class or j.Controller)

    def test_31h_preserves_31g_mutations_and_only_adds_bound_state_reads(self):
        for arrives in (True, False):
            traces, results = [], []
            for cls in (frozen.h.Controller, j.Controller):
                f, mem, ctl, journal = self.controller(cls)
                f.arrival = arrives
                f.rvbar_words = [t.BASE | 1 | (1 << 63)] * 2
                traced = TraceProxy(f)
                ctl.i = ctl.p = traced
                if arrives:
                    result = ctl.run()
                else:
                    with self.assertRaisesRegex(j.Refusal, '^cpu1_arrival_timeout$'):
                        ctl.run()
                    result = ctl.state
                traces.append(traced.requests)
                results.append(dict(result))
                self.assertEqual(f.state_read_count, 8)
                self.doCleanups()
            self.assertEqual(traces[0], traces[1])
            self.assertEqual(results[0].pop('experiment'), 'smp31i')
            self.assertEqual(results[1].pop('experiment'), 'smp31j')
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[1]['mutation_requests'], 74 if arrives else 66)
            self.assertEqual(results[1]['start_writes_attempted'], 2)

    def test_31h_retains_classification_and_mirror_equality(self):
        for bits in (0, 0x800, 2):
            f, mem, ctl, journal = self.controller()
            f.rvbar_words = [t.BASE | 1, t.BASE | 1 | bits | (1 << 63)]
            with self.assertRaisesRegex(j.Refusal, '^reset_format_requires_review$'):
                ctl.run()
            self.assertEqual(ctl.state['experiment'], 'smp31j')
            self.assertFalse(ctl.state['rvbar_observation']['mirrors_equal'])
            self.assertFalse(ctl.state['reset_format_gate_passed'])
            self.assertEqual(f.mutations, 0)
            self.assertEqual(f.state_read_count, 0)
            self.doCleanups()

    def test_every_target_method_is_inherited(self):
        # Python 3.13+ adds compiler metadata that is absent on the host's
        # older interpreter. None is a method or a target-behavior override.
        metadata = {'__module__', '__doc__', '__static_attributes__', '__firstlineno__'}
        self.assertEqual(set(j.Controller.__dict__) - metadata, {'__init__'})
        self.assertEqual({name for name, value in j.Controller.__dict__.items()
                          if callable(value)}, {'__init__'})
        for name in ('preflight', 'run', 'sample_power', 'prepare_cpu_state_reads'):
            self.assertIs(getattr(j.Controller, name), getattr(frozen.h.Controller, name))


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
        self.native = self.root / 'build/native-intake/attempt31j/consumed.jsonl'
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
        self.controller = SimpleNamespace(state=dict(experiment='smp31j', phase='preflight',
            mutation_requests=0, start_writes_attempted=0, linux_boot='NOT RUN'),
            run=Mock(return_value=dict(experiment='smp31j', phase='complete',
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
        self.assertTrue(all(row['experiment'] == 'smp31j' for row in self.rows(self.native)))

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
        common = ['smp31j.py', '--image', str(image)]
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
            path = Path(tmp) / 'tools/m1n1-client/attempt31j-offline.py'
            path.parent.mkdir(parents=True)
            path.write_text('synthetic')
            intake = SimpleNamespace(source_pins=Mock(return_value=([], 'new-digest')))
            with patch.object(j, 'module', return_value=intake) as load:
                self.assertEqual(j.verify_sources(), 'new-digest')
                load.assert_called_once_with('intake31j', 'tools/m1n1-client/attempt31j-offline.py')
                intake.source_pins.assert_called_once_with(Path(tmp))


if __name__ == '__main__':
    unittest.main()
