# SPDX-License-Identifier: MIT
"""Synthetic bounded-enumeration tests: no real queries, devices or sleeps."""
import copy
import importlib.util
import json
from pathlib import Path
import plistlib
import stat
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('connection31j', HERE / 'usb_connection31j.py')
connection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(connection)


def device(stem='PRIVATE_SYNTHETIC', vid=0x1209, pid=0x316d):
    return {'IOObjectClass': 'IOUSBHostDevice', 'idVendor': vid, 'idProduct': pid,
            'USB Serial Number': 'PRIVATE_SYNTHETIC_SERIAL', 'IORegistryEntryChildren': [
                {'IOObjectClass': 'IOUSBHostInterface', 'bInterfaceNumber': number,
                 'bInterfaceClass': 10, 'IORegistryEntryChildren': [
                     {'IOObjectClass': 'IOSerialBSDClient',
                      'IOCalloutDevice': '/dev/cu.usbmodem' + stem + str(number)}]}
                for number in (1, 3)]}


def archive(roots=None, binary=False):
    return plistlib.dumps([device()] if roots is None else roots,
                         fmt=plistlib.FMT_BINARY if binary else plistlib.FMT_XML)


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class OuterRefusal(ValueError):
    pass


class ConnectionTests(unittest.TestCase):
    def run_case(self, raws=None, durations=None, query_error=None, returncode=0,
                 lstat_error=None, mode=stat.S_IFCHR, progress=None, clock=None,
                 sleeper=None, platform='darwin'):
        raws = [archive()] if raws is None else raws
        timer = clock if clock is not None else FakeClock()
        durations = [0.0] * len(raws) if durations is None else durations
        calls, snapshots = [], []

        def query(*args, **kwargs):
            index = len(calls)
            calls.append((args, kwargs))
            if query_error is not None:
                raise query_error
            if hasattr(timer, 'value'):
                timer.value += durations[min(index, len(durations) - 1)]
            return SimpleNamespace(stdout=raws[min(index, len(raws) - 1)],
                                   stderr=b'PRIVATE_SYNTHETIC_STDERR', returncode=returncode)

        def notify(report):
            snapshots.append(copy.deepcopy(report))
            if progress is not None:
                progress(report, timer)

        pause = Mock(side_effect=sleeper if sleeper is not None else timer.sleep)
        path = error = None
        with patch.object(connection.sys, 'platform', platform), \
                patch.object(connection.subprocess, 'run', side_effect=query) as run, \
                patch.object(connection.host.identity.Path, 'lstat',
                             return_value=SimpleNamespace(st_mode=mode), side_effect=lstat_error) as lstat, \
                patch('builtins.open', side_effect=AssertionError('No file/device open')):
            try:
                path, report = connection.discover_primary(notify, timer, pause)
            except connection.ConnectionRefusal as exc:
                error, report = exc, exc.report
        for public in [report, *snapshots]:
            rendered = json.dumps(public, allow_nan=False)
            for private in ('PRIVATE_SYNTHETIC', '/dev/', '/Users/', 'Traceback'):
                self.assertNotIn(private, rendered)
            self.assertFalse(public['native_ready'])
            self.assertEqual((public['device_opens'], public['target_requests']), (0, 0))
        if error is not None:
            for private in ('PRIVATE_SYNTHETIC', '/dev/', '/Users/'):
                self.assertNotIn(private, str(error) + repr(error))
        self.assertLessEqual(run.call_count, 4)
        for args, kwargs in calls:
            self.assertEqual(args, (list(connection.host.QUERY),))
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertTrue(kwargs['capture_output'])
            self.assertFalse(kwargs['check'])
            self.assertGreater(kwargs['timeout'], 0)
            self.assertLessEqual(kwargs['timeout'], 3.0)
        return SimpleNamespace(path=path, report=report, error=error, run=run,
                               lstat=lstat, pause=pause, snapshots=snapshots, clock=timer)

    def test_empty_then_primary_returns_once_without_opening(self):
        got = self.run_case(raws=[b'', archive()])
        self.assertIsNone(got.error)
        self.assertEqual(got.path, '/dev/cu.usbmodemPRIVATE_SYNTHETIC1')
        self.assertTrue(got.report['ready'])
        self.assertEqual(got.report['query_attempts'], 2)
        self.assertEqual(got.report['query_returns'], 2)
        self.assertEqual([r['category'] for r in got.report['observations']],
                         ['empty_stdout_unresolved', 'primary_verified'])
        self.assertEqual(len(got.snapshots), 4)
        self.assertEqual([r['query_attempts'] for r in got.snapshots], [0, 1, 1, 2])
        got.pause.assert_called_once_with(1.0)
        got.lstat.assert_called_once()

    def test_primary_immediately_stops_enumeration(self):
        got = self.run_case(raws=[archive(), b'PRIVATE_SYNTHETIC'])
        self.assertIsNone(got.error)
        got.run.assert_called_once()
        got.pause.assert_not_called()

    def test_only_empty_or_classified_zero_candidates_can_repeat(self):
        for raw in (b'', archive([]), archive([device(pid=1)])):
            with self.subTest(raw_kind=bool(raw)):
                got = self.run_case(raws=[raw])
                self.assertEqual(got.error.reason, 'enumeration_unavailable')
                self.assertFalse(got.report['ready'])
                self.assertEqual(got.run.call_count, 4)
                self.assertEqual(got.pause.call_count, 3)
                self.assertEqual(len(got.snapshots), 8)
                got.lstat.assert_not_called()

    def test_m1_fixture_empty_category_is_preserved_without_invented_counts(self):
        fixture = json.loads((ROOT / 'native/boot/attempt31j-host-m1-2026-10-21.json').read_text())
        got = self.run_case(raws=[b'', archive()])
        row = got.report['observations'][0]
        for key in ('category', 'phase', 'inventory_classified', 'primary_verified', 'stdout_kind'):
            self.assertEqual(row[key], fixture[key])
        self.assertNotIn('primary_candidates', row)
        self.assertNotIn('modem_interfaces', row)

    def test_malformed_input_stops_first_observation(self):
        for raw in (b' ', b'\n\t', b'PRIVATE_SYNTHETIC', b'<?xml?><plist><array>',
                    b'bplist00PRIVATE_SYNTHETIC', b'junk\n' + archive(), b' ' + archive(),
                    plistlib.dumps({}), plistlib.dumps([{'IORegistryEntryChildren': {}}])):
            got = self.run_case(raws=[raw, archive()])
            self.assertIsNotNone(got.error)
            self.assertNotIn(got.error.reason, connection.WAITABLE)
            got.run.assert_called_once()
            got.pause.assert_not_called()
            got.lstat.assert_not_called()

    def test_binary_archive_and_exact_metadata_succeed(self):
        got = self.run_case(raws=[archive(binary=True)])
        self.assertIsNone(got.error)
        self.assertEqual(got.report['observations'][0]['stdout_kind'], 'binary_plist')

    def test_query_failure_and_timeout_never_repeat(self):
        cases = ((subprocess.TimeoutExpired('PRIVATE_SYNTHETIC', 3, output=b'PRIVATE_SYNTHETIC'), 'query_timeout'),
                 (FileNotFoundError('PRIVATE_SYNTHETIC'), 'query_executable_missing'),
                 (PermissionError('PRIVATE_SYNTHETIC'), 'query_permission_denied'),
                 (OSError('PRIVATE_SYNTHETIC'), 'query_failed'))
        for error, reason in cases:
            got = self.run_case(query_error=error)
            self.assertEqual(got.error.reason, reason)
            self.assertEqual(got.report['query_returns'], 0)
            got.run.assert_called_once()
            got.pause.assert_not_called()
            self.assertEqual(len(got.snapshots), 2)
        got = self.run_case(returncode=1)
        self.assertEqual(got.error.reason, 'query_nonzero_exit')
        self.assertEqual(got.report['query_returns'], 1)
        got.run.assert_called_once()

    def test_ambiguous_identity_never_selects_a_path(self):
        got = self.run_case(raws=[archive([device('ONE'), device('TWO')]), archive()])
        self.assertEqual(got.error.reason, 'ambiguous_primary_candidates')
        got.run.assert_called_once()
        got.lstat.assert_not_called()
        got.pause.assert_not_called()

    def test_metadata_types_do_not_weaken_exact_identity(self):
        for key, value in (('idVendor', 4617.0), ('idProduct', '12653'),
                           ('bInterfaceNumber', True), ('bInterfaceClass', 10.0)):
            root = device()
            node = root if key.startswith('id') else root['IORegistryEntryChildren'][0]
            node[key] = value
            got = self.run_case(raws=[archive([root]), archive()])
            self.assertEqual(got.error.reason, 'invalid_registry_shape')
            got.run.assert_called_once()
            got.lstat.assert_not_called()

    def test_stale_symlink_and_regular_paths_stop_immediately(self):
        for error, mode, reason in ((FileNotFoundError('/dev/PRIVATE_SYNTHETIC'), stat.S_IFCHR, 'primary_path_absent'),
                                    (PermissionError('/dev/PRIVATE_SYNTHETIC'), stat.S_IFCHR, 'primary_path_access_denied'),
                                    (None, stat.S_IFLNK, 'primary_path_not_character'),
                                    (None, stat.S_IFREG, 'primary_path_not_character')):
            got = self.run_case(lstat_error=error, mode=mode)
            self.assertEqual(got.error.reason, reason)
            got.run.assert_called_once()
            got.lstat.assert_called_once()
            got.pause.assert_not_called()

    def test_callback_failure_before_query_keeps_scheduled_prefix(self):
        fault = OSError('/Users/PRIVATE_SYNTHETIC')
        def fail(report, timer):
            raise fault
        got = self.run_case(progress=fail)
        self.assertEqual(got.error.reason, 'progress_callback_failed')
        self.assertIs(got.error.callback_exception, fault)
        self.assertEqual(got.report['query_attempts'], 0)
        self.assertEqual(got.report['observations'][0]['state'], 'scheduled')
        got.run.assert_not_called()
        got.pause.assert_not_called()

    def test_callback_failure_after_query_keeps_completed_prefix(self):
        fault = OuterRefusal('controller_deadline')
        def fail(report, timer):
            if report['observations'][-1]['state'] == 'complete':
                raise fault
        got = self.run_case(raws=[b'', archive()], progress=fail)
        self.assertEqual(got.error.reason, 'progress_callback_failed')
        self.assertIs(got.error.callback_exception, fault)
        self.assertEqual(got.report['observations'][0]['category'], 'empty_stdout_unresolved')
        got.run.assert_called_once()
        got.pause.assert_not_called()

    def test_callback_cannot_mutate_gate_state(self):
        def mutate(report, timer):
            report['query_attempts'] = 999
            report['observations'].clear()
            report['ready'] = True
        got = self.run_case(raws=[b'', archive()], progress=mutate)
        self.assertIsNone(got.error)
        self.assertEqual(got.report['query_attempts'], 2)
        self.assertEqual(len(got.report['observations']), 2)

    def test_callback_elapsed_time_counts_before_query_and_after_success(self):
        for at_state, expected_queries in (('scheduled', 0), ('complete', 1)):
            def delay(report, timer):
                if report['observations'][-1]['state'] == at_state:
                    timer.value += 15
            got = self.run_case(progress=delay)
            self.assertEqual(got.error.reason, 'discovery_deadline')
            self.assertEqual(got.run.call_count, expected_queries)
            self.assertFalse(got.report['ready'])

    def test_remaining_budget_caps_query_timeout(self):
        def delay(report, timer):
            if report['observations'][-1]['state'] == 'scheduled':
                timer.value += 13
        got = self.run_case(progress=delay, durations=[0.5])
        self.assertIsNone(got.error)
        self.assertEqual(got.run.call_args.kwargs['timeout'], 2.0)
        self.assertEqual(got.report['elapsed_seconds'], 13.5)

    def test_deadline_consumed_in_query_never_returns_ready(self):
        got = self.run_case(durations=[15.0])
        self.assertEqual(got.error.reason, 'discovery_deadline')
        self.assertEqual(got.report['observations'][0]['category'], 'primary_verified')
        self.assertFalse(got.report['ready'])
        got.run.assert_called_once()
        got.pause.assert_not_called()
        self.assertEqual(len(got.snapshots), 2)

    def test_insufficient_wait_budget_and_sleep_overshoot_stop(self):
        got = self.run_case(raws=[b''], durations=[14.0])
        self.assertEqual(got.error.reason, 'discovery_deadline')
        got.pause.assert_not_called()
        timer = FakeClock()
        def overshoot(seconds):
            timer.value += 15
        got = self.run_case(raws=[b''], clock=timer, sleeper=overshoot)
        self.assertEqual(got.error.reason, 'discovery_deadline')
        got.run.assert_called_once()
        got.pause.assert_called_once_with(1.0)

    def test_clock_invalid_or_regressed_never_queries_again(self):
        for value in (float('nan'), float('inf'), True, 'PRIVATE_SYNTHETIC', 10 ** 400):
            timer = FakeClock()
            timer.value = value
            got = self.run_case(clock=timer)
            self.assertEqual(got.error.reason, 'clock_invalid')
            got.run.assert_not_called()
        def regress(report, timer):
            timer.value -= 1
        got = self.run_case(progress=regress)
        self.assertEqual(got.error.reason, 'clock_regressed')
        got.run.assert_not_called()

    def test_outer_deadline_and_interrupt_provenance_survive_each_boundary(self):
        for fault in (OuterRefusal('controller_deadline'), KeyboardInterrupt()):
            got = self.run_case(query_error=fault)
            self.assertIs(got.error.callback_exception, fault)
            got.run.assert_called_once()
            got.pause.assert_not_called()
            got = self.run_case(lstat_error=fault)
            self.assertIs(got.error.callback_exception, fault)
            got.run.assert_called_once()
            def fail_sleep(seconds):
                raise fault
            got = self.run_case(raws=[b''], sleeper=fail_sleep)
            self.assertIs(got.error.callback_exception, fault)
            self.assertEqual(got.error.reason, 'enumeration_wait_failed')
            got.run.assert_called_once()
            class BadClock(FakeClock):
                def __call__(self):
                    raise fault
            got = self.run_case(clock=BadClock())
            self.assertIs(got.error.callback_exception, fault)
            got.run.assert_not_called()

    def test_query_deadline_survives_later_progress_journal_failure(self):
        deadline = OuterRefusal('controller_deadline')
        journal_failure = OSError('/Users/PRIVATE_SYNTHETIC')
        def fail_after(report, timer):
            if report['observations'][-1]['state'] == 'complete':
                raise journal_failure
        got = self.run_case(query_error=deadline, progress=fail_after)
        self.assertEqual(got.error.reason, 'progress_callback_failed')
        self.assertIs(got.error.callback_exception, deadline)
        self.assertEqual(got.error.interruptions, (deadline, journal_failure))
        self.assertTrue(got.report['progress_callback_failed'])
        self.assertEqual(got.report['observations'][0]['category'], 'query_failed')
        got.run.assert_called_once()
        got.pause.assert_not_called()

    def test_clock_deadline_survives_later_progress_journal_failure(self):
        deadline = OuterRefusal('controller_deadline')
        journal_failure = OSError('/Users/PRIVATE_SYNTHETIC')
        class BrokenAfterQuery(FakeClock):
            def __call__(self):
                if self.value > 100:
                    raise deadline
                return self.value
        def fail_after(report, timer):
            if report['observations'][-1]['state'] == 'complete':
                raise journal_failure
        got = self.run_case(clock=BrokenAfterQuery(), durations=[1], progress=fail_after)
        self.assertEqual(got.error.interruptions, (deadline, journal_failure))
        self.assertIs(got.error.callback_exception, deadline)
        self.assertEqual(got.report['observations'][0]['category'], 'primary_verified')
        self.assertFalse(got.report['ready'])
        got.run.assert_called_once()
        got.pause.assert_not_called()

    def test_later_outer_deadline_remains_available_after_ordinary_query_error(self):
        query_fault = OSError('PRIVATE_SYNTHETIC')
        deadline = OuterRefusal('controller_deadline')
        def fail_after(report, timer):
            if report['observations'][-1]['state'] == 'complete':
                raise deadline
        got = self.run_case(query_error=query_fault, progress=fail_after)
        self.assertEqual(got.error.interruptions, (query_fault, deadline))
        outer = next(exc for exc in got.error.interruptions if isinstance(exc, OuterRefusal))
        self.assertIs(outer, deadline)
        got.run.assert_called_once()
        got.pause.assert_not_called()

    def test_math_isfinite_valueerror_preserves_outer_deadline(self):
        for failure_call in (1, 2):
            deadline = OuterRefusal('controller_deadline')
            real = connection.math.isfinite
            calls = []
            def fault(value):
                calls.append(value)
                if len(calls) == failure_call:
                    raise deadline
                return real(value)
            with patch.object(connection.math, 'isfinite', side_effect=fault):
                got = self.run_case()
            self.assertEqual(got.error.reason, 'clock_invalid')
            self.assertIs(got.error.callback_exception, deadline)
            got.run.assert_not_called()
            got.pause.assert_not_called()

    def test_platform_failure_has_zero_query_intents(self):
        got = self.run_case(platform='linux')
        self.assertEqual(got.error.reason, 'unsupported_platform')
        self.assertEqual(got.report['query_attempts'], 0)
        got.run.assert_not_called()
        got.pause.assert_not_called()


if __name__ == '__main__':
    unittest.main()
