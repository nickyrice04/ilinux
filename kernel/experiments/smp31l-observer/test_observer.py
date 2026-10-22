"""Original fault-prefix tests; no target or hardware emulation."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('normal31l', Path(__file__).with_name('observer.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ADDRESS = 0x10000801000


class Observe(unittest.TestCase):
    def sample(self, words):
        tracker = m.Tracker()
        it = iter(words)
        return tracker, tracker.sample(lambda _: next(it), ADDRESS)

    def test_zero_is_not_execution_disproof(self):
        tracker, report = self.sample([0, 0, 0])
        self.assertFalse(tracker.closed)
        self.assertEqual(report['cpu1_execution'], 'UNVERIFIED')

    def test_committed_cpu1(self):
        tracker, report = self.sample([2, 0x40001, 2])
        self.assertTrue(tracker.closed)
        self.assertEqual(report['identity_status'], 'expected_cpu1')
        self.assertEqual(report['device_visibility'], 'UNTESTED')

    def test_partial_and_uncommitted_identity_stop_without_identity_claim(self):
        for words in ([0, 0x40001, 0], [0, 0x99999, 0], [1, 0, 1],
                      [0, 0x40001, 2], [1, 0x40001, 2]):
            with self.subTest(words=words):
                tracker, report = self.sample(words)
                self.assertTrue(tracker.closed)
                self.assertTrue(report['any_record_seen'])
                self.assertEqual(report['identity_status'], 'not_committed')

    def test_invalid_and_regressed_phases(self):
        for words in ([9, 0, 9], [1, 0, 0], [2, 0x40001, 1], [True, 0, 0]):
            tracker = m.Tracker()
            it = iter(words)
            with self.assertRaises(ValueError):
                tracker.sample(lambda _: next(it), ADDRESS)
            self.assertTrue(tracker.closed)

    def test_wrong_committed_identity(self):
        for identity in (0, 0x40000, 0x80000, 0xdeadbeef):
            with self.assertRaisesRegex(ValueError, 'normal_identity_unexpected'):
                self.sample([2, identity, 2])

    def test_each_failed_read_retains_prefix_and_stops(self):
        for failure in range(3):
            calls = []
            tracker = m.Tracker()
            def read(address):
                calls.append(address)
                if len(calls) == failure+1:
                    raise TimeoutError('private diagnostic')
                return [2, 0x40001, 2][len(calls)-1]
            with self.assertRaises(TimeoutError):
                tracker.sample(read, ADDRESS)
            self.assertEqual(len(calls), failure+1)
            self.assertEqual(tracker.state['reads_completed'], failure)
            self.assertNotIn('private', str(tracker.state))
            with self.assertRaisesRegex(ValueError, 'normal_tracker_closed'):
                tracker.sample(read, ADDRESS)
            self.assertEqual(len(calls), failure+1)

    def test_probe_addresses_and_attributes(self):
        helper = ADDRESS - 0x1000
        probes = m.probes(helper)
        self.assertEqual(len(probes), 12)
        self.assertEqual({p['attr'] for p in probes}, {255})
        self.assertEqual({p['shareability'] for p in probes}, {2})
        self.assertTrue(all(helper+0x1000 <= p['address'] <= helper+0x1138 for p in probes))

    def test_foreign_value_error_is_not_published(self):
        tracker = m.Tracker()
        def read(_):
            raise ValueError('PRIVATE_SYNTHETIC device detail')
        with self.assertRaises(ValueError):
            tracker.sample(read, ADDRESS)
        self.assertEqual(tracker.state['error'], 'normal_read_interrupted')
        self.assertNotIn('PRIVATE_SYNTHETIC', str(tracker.state))

    def test_reject_address_aliases_and_overflow(self):
        for address in (0, True, ADDRESS, 1 << 41, 0xc0000000000):
            with self.assertRaises(ValueError):
                m.record_address(address, 'vector')


class Control(unittest.TestCase):
    def fixture(self, fail_at=None, failure=None, corrupt=False):
        memory, calls, reports = [0]*8, [], []
        def before(kind, value):
            calls.append((kind, value))
            if len(calls) == fail_at:
                raise failure if failure is not None else TimeoutError('private path')
        def read(offset):
            before('read', offset)
            return memory[offset//8]
        def store(value):
            before('write', value)
            memory[4] = value
            if corrupt and value:
                memory[7] = 1
            return m.RETURN_VALUE
        return memory, calls, reports, read, store

    def test_control_passes_and_restores(self):
        memory, calls, reports, read, store = self.fixture()
        report = m.cpu0_control(read, store, reports.append, lambda: 0, lambda: 0)
        self.assertEqual(report['result'], 'CPU0_NORMAL_CONTROL_PASS')
        self.assertEqual(report['reads_completed'], 24)
        self.assertEqual(report['writes_acknowledged'], 2)
        self.assertEqual(memory, [0]*8)
        self.assertEqual(len(calls), 26)

    def test_every_target_failure_stops_without_cleanup(self):
        for index in range(1, 27):
            for failure in (TimeoutError('private target'), KeyboardInterrupt()):
                with self.subTest(index=index, failure=type(failure).__name__):
                    memory, calls, reports, read, store = self.fixture(index, failure)
                    with self.assertRaises(type(failure)):
                        m.cpu0_control(read, store, reports.append, lambda: 0, lambda: 0)
                    self.assertEqual(len(calls), index)
                    self.assertEqual(reports[-1]['result'], 'STOP')
                    self.assertNotIn('private', str(reports[-1]))

    def test_canary_corruption_has_no_restoration_write(self):
        memory, calls, reports, read, store = self.fixture(corrupt=True)
        with self.assertRaisesRegex(ValueError, 'normal_control_marker_or_canary'):
            m.cpu0_control(read, store, reports.append, lambda: 0, lambda: 0)
        self.assertEqual(sum(kind == 'write' for kind, _ in calls), 1)

    def test_journal_failure_prevents_target_dispatch(self):
        memory, calls, reports, read, store = self.fixture()
        def journal(_):
            raise OSError('disk')
        with self.assertRaises(OSError):
            m.cpu0_control(read, store, journal, lambda: 0, lambda: 0)
        self.assertFalse(calls)

    def test_control_foreign_value_error_is_not_published(self):
        memory, calls, reports, read, store = self.fixture(1, ValueError('PRIVATE_SYNTHETIC detail'))
        with self.assertRaises(ValueError):
            m.cpu0_control(read, store, reports.append, lambda: 0, lambda: 0)
        self.assertEqual(reports[-1]['error'], 'normal_control_interrupted')
        self.assertNotIn('PRIVATE_SYNTHETIC', str(reports[-1]))

    def test_start_intent_and_bad_clock_prevent_target_dispatch(self):
        for starts, clock in ((lambda: 1, lambda: 0), (lambda: True, lambda: 0),
                              (lambda: 0, lambda: float('nan'))):
            memory, calls, reports, read, store = self.fixture()
            with self.assertRaises(ValueError):
                m.cpu0_control(read, store, reports.append, starts, clock)
            self.assertFalse(calls)

    def test_deadline_after_journal_prevents_dispatch(self):
        memory, calls, reports, read, store = self.fixture()
        clock_values = iter((0, 2))
        with self.assertRaisesRegex(ValueError, 'normal_control_deadline'):
            m.cpu0_control(read, store, reports.append, lambda: 0, lambda: next(clock_values))
        self.assertFalse(calls)
        self.assertEqual(reports[-1]['read_intents'], 1)
        self.assertEqual(reports[-1]['reads_attempted'], 0)


if __name__ == '__main__':
    unittest.main()
