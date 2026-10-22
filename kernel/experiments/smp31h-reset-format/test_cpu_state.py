"""Synthetic sequencing/failure tests; no transport, firmware or hardware."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('cpu_state31h', Path(__file__).with_name('cpu_state.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class TrackerTests(unittest.TestCase):
    def test_fixed_addresses_width_and_cpu_boundaries(self):
        self.assertEqual(c.ADDRESSES, (0x210050100, 0x210150100))
        self.assertEqual(c.READ_BYTES, 4)
        self.assertEqual(c.REGISTER_OFFSET, 0x100)
        self.assertEqual([c.address(cpu) for cpu in (0, 1)], list(c.ADDRESSES))
        for cpu in (True, False, -1, 2, 18, 0.0, '0', None):
            with self.subTest(cpu=cpu), self.assertRaises(c.ObservationError):
                c.address(cpu)

    def test_complete_sequence_low_bytes_only_and_no_semantic_claim(self):
        tracker = c.Tracker()
        log, reads = [], []
        values = ((0xabcd0000, 0x12340000), (0xabcd0000, 0x12340001),
                  (0xabcd0001, 0x12340001), (0xabcd00fe, 0x123400ff))
        for index, phase in enumerate(c.PHASES):
            def read(cpu):
                self.assertEqual(log[-1]['reads_attempted'], len(reads) + 1)
                self.assertEqual(log[-1]['reads_completed'], len(reads))
                reads.append((phase, cpu))
                return values[index][cpu]
            tracker.sample(phase, read, log.append)
        report = tracker.report()
        self.assertEqual(reads, [(phase, cpu) for phase in c.PHASES for cpu in (0, 1)])
        self.assertEqual(report['reads_attempted'], 8)
        self.assertEqual(report['reads_completed'], 8)
        self.assertTrue(all(row['complete'] for row in report['samples']))
        self.assertEqual([row['cores_equal'] for row in report['samples']], [True, False, True, False])
        self.assertEqual([row['cpu1']['changed_from_baseline'] for row in report['samples']],
                         [None, True, True, True])
        self.assertEqual([row['cpu0']['changed_from_baseline'] for row in report['samples']],
                         [None, False, True, True])
        for key in ('entry_execution', 'reset_release', 'running_state'):
            self.assertEqual(report[key], 'NOT_ESTABLISHED')
        self.assertEqual(report['program_counter'], 'NOT_OBSERVED')
        self.assertEqual(report['t6050_register_semantics'], 'UNKNOWN')
        payload = json.dumps(log)
        for pair in values:
            for value in pair:
                self.assertNotIn(str(value), payload)
                self.assertNotIn(hex(value), payload)
        for address in c.ADDRESSES:
            self.assertNotIn(str(address), payload)
            self.assertNotIn(hex(address), payload)

    def test_report_and_persist_snapshots_cannot_mutate_tracker(self):
        tracker = c.Tracker()
        def mutate(report):
            report['samples'].clear()
            report['error'] = 'forged'
        tracker.sample('before_start', lambda cpu: cpu, mutate)
        report = tracker.report()
        report['samples'][0]['cpu0']['low_byte'] = 999
        self.assertEqual(tracker.report()['samples'][0]['cpu0']['low_byte'], 0)
        self.assertIsNone(tracker.report()['error'])

    def test_every_read_failure_preserves_prefix_and_freezes(self):
        for fail in range(1, 9):
            with self.subTest(fail=fail):
                tracker, reads, log = c.Tracker(), [], []
                def read(cpu):
                    reads.append(cpu)
                    if len(reads) == fail:
                        raise TimeoutError('private full register or transport detail')
                    return 0x1234000f
                with self.assertRaisesRegex(c.ObservationError, 'cpu_state_read_failed'):
                    for phase in c.PHASES:
                        tracker.sample(phase, read, log.append)
                report = tracker.report()
                self.assertEqual(report['reads_attempted'], fail)
                self.assertEqual(report['reads_completed'], fail - 1)
                self.assertFalse(report['samples'][-1]['complete'])
                self.assertEqual(report['samples'][-1]['cpu0'] is not None, fail % 2 == 0)
                self.assertIsNone(report['samples'][-1]['cpu1'])
                self.assertNotIn('private', json.dumps(log))
                before = list(reads)
                with self.assertRaisesRegex(c.ObservationError, 'cpu_state_read_failed'):
                    tracker.sample('final', read, log.append)
                self.assertEqual(reads, before)

    def test_invalid_values_at_every_read_are_never_committed(self):
        for invalid in (True, False, -1, 1 << 32, None, 'private', 1.0, *c.INVALID_WORDS):
            for fail in range(1, 9):
                tracker, count = c.Tracker(), 0
                def read(cpu):
                    nonlocal count
                    count += 1
                    return invalid if count == fail else 0
                with self.subTest(value=invalid, fail=fail), self.assertRaises(c.ObservationError):
                    for phase in c.PHASES:
                        tracker.sample(phase, read, lambda report: None)
                report = tracker.report()
                self.assertEqual(report['reads_completed'], fail - 1)
                self.assertEqual(report['reads_attempted'], fail)
                self.assertNotIn('private', json.dumps(report))

    def test_zero_and_high_non_sentinel_words_are_valid(self):
        for value, expected in ((0, 0), (0xff, 255), (0xffffff00, 0),
                                (0xfffffffe, 254), (0x12340000, 0)):
            self.assertEqual(c.low_byte(value), expected)

    def test_wrong_phase_order_and_types_freeze_before_read(self):
        for prefix, phase in ((0, 'final'), (0, True), (0, None),
                              (1, 'before_start'), (1, 'after_second_start')):
            tracker, reads = c.Tracker(), []
            for initial in c.PHASES[:prefix]:
                tracker.sample(initial, lambda cpu: 0, lambda report: None)
            with self.assertRaisesRegex(c.ObservationError, 'cpu_state_sample_order'):
                tracker.sample(phase, lambda cpu: reads.append(cpu), lambda report: None)
            self.assertEqual(reads, [])
            self.assertEqual(tracker.report()['reads_attempted'], prefix * 2)
            with self.assertRaisesRegex(c.ObservationError, 'cpu_state_sample_order'):
                tracker.sample(c.PHASES[prefix], lambda cpu: self.fail('read after fault'), lambda _: None)

    def test_eighth_read_is_absolute_limit_no_repeat_or_extra_phase(self):
        tracker, reads = c.Tracker(), []
        def read(cpu):
            reads.append(cpu)
            return 0
        for phase in c.PHASES:
            tracker.sample(phase, read, lambda _: None)
        for phase in ('final', 'before_start', 'extra'):
            with self.assertRaises(c.ObservationError):
                tracker.sample(phase, read, lambda _: None)
        self.assertEqual(len(reads), c.MAX_READS)

    def test_partial_pair_is_durable_before_second_read(self):
        tracker, log = c.Tracker(), []
        def read(cpu):
            if cpu == 1:
                self.assertEqual(log[-1]['samples'][0]['cpu0']['low_byte'], 7)
                self.assertIsNone(log[-1]['samples'][0]['cpu1'])
                self.assertFalse(log[-1]['samples'][0]['complete'])
                raise TimeoutError()
            return 7
        with self.assertRaises(c.ObservationError):
            tracker.sample('before_start', read, log.append)
        self.assertEqual(log[-1], tracker.report())

    def test_each_journal_failure_stops_before_further_read(self):
        # Per pair: first intent/result, second intent/result, complete.
        for fail in range(1, 21):
            tracker, reads, journal_calls = c.Tracker(), [], 0
            def read(cpu):
                reads.append(cpu)
                return 1
            def persist(report):
                nonlocal journal_calls
                journal_calls += 1
                if journal_calls == fail:
                    raise OSError('private journal destination')
            with self.assertRaisesRegex(c.ObservationError, 'cpu_state_journal_failed'):
                for phase in c.PHASES:
                    tracker.sample(phase, read, persist)
            report = tracker.report()
            self.assertTrue(report['journal_failed'])
            self.assertEqual(journal_calls, fail)
            self.assertNotIn('private', json.dumps(report))
            count = len(reads)
            with self.assertRaises(c.ObservationError):
                tracker.sample('final', read, persist)
            self.assertEqual(len(reads), count)
            self.assertEqual(journal_calls, fail)

    def test_read_failure_remains_first_if_error_journal_also_fails(self):
        tracker = c.Tracker()
        def read(_):
            raise OSError('private read')
        def persist(report):
            if report['error'] is not None:
                raise OSError('private journal')
        with self.assertRaisesRegex(c.ObservationError, 'cpu_state_read_failed'):
            tracker.sample('before_start', read, persist)
        self.assertTrue(tracker.report()['journal_failed'])
        self.assertEqual(tracker.report()['error'], 'cpu_state_read_failed')

    def test_interrupts_preserve_partial_prefix_and_stop(self):
        for exception in (KeyboardInterrupt, SystemExit):
            tracker, calls, log = c.Tracker(), [], []
            def read(cpu):
                calls.append(cpu)
                if cpu == 1:
                    raise exception()
                return 15
            with self.assertRaises(exception):
                tracker.sample('before_start', read, log.append)
            report = tracker.report()
            self.assertEqual(report['reads_attempted'], 2)
            self.assertEqual(report['reads_completed'], 1)
            self.assertEqual(report['error'], 'cpu_state_read_interrupted')
            self.assertEqual(log[-1], report)
            with self.assertRaises(c.ObservationError):
                tracker.sample('before_start', read, log.append)
            self.assertEqual(calls, [0, 1])

    def test_reentrant_callback_or_reader_cannot_continue(self):
        for at_persist in (True, False):
            tracker, reads = c.Tracker(), []
            def nested():
                with self.assertRaises(c.ObservationError):
                    tracker.sample('before_start', lambda _: self.fail('nested read'), lambda _: None)
            def read(cpu):
                reads.append(cpu)
                if not at_persist:
                    nested()
                return 0
            def persist(report):
                if at_persist:
                    nested()
            with self.assertRaisesRegex(c.ObservationError, 'cpu_state_reentrant_sample'):
                tracker.sample('before_start', read, persist)
            self.assertEqual(reads, [] if at_persist else [0])
            self.assertEqual(tracker.report()['reads_completed'], 0)

    def test_invalid_callbacks_freeze_without_io(self):
        for reader, persist, reason in ((None, lambda _: None, 'cpu_state_reader_not_callable'),
                                       (lambda _: self.fail('read'), None, 'cpu_state_persist_not_callable')):
            tracker = c.Tracker()
            with self.assertRaisesRegex(c.ObservationError, reason):
                tracker.sample('before_start', reader, persist)
            self.assertEqual(tracker.report()['reads_attempted'], 0)


if __name__ == '__main__':
    unittest.main()
