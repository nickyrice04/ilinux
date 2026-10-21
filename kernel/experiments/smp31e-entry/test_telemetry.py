#!/usr/bin/env python3
"""Original pure recorder-publication tests; no device or privileged execution."""
import importlib.util
import itertools
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('telemetry', Path(__file__).with_name('telemetry.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
BASE = 1 << 40
IDENT = m.CPU1_MPIDR


def reader(words, calls=None):
    pending = iter(words)
    def read(address):
        if calls is not None:
            calls.append(address)
        return next(pending)
    return read


class TelemetryTests(unittest.TestCase):
    def test_initial_zero_means_only_no_publication_seen(self):
        result = m.classify((0, 0, 0, 0, 0))
        self.assertEqual(result['state'], 'no_recorder_publication_seen')
        self.assertFalse(result['complete'])
        self.assertFalse(result['identity_seen'])
        self.assertIsNone(result['exception_level'])

    def test_all_stable_phases(self):
        for phase, identity, level, name in (
                (0, IDENT, 0, 'identity_store_seen'),
                (1, IDENT, 0, 'identity_phase_seen'),
                (2, IDENT, 8, 'before_sctlr_phase_seen'),
                (255, IDENT, 0, 'unsupported_el_phase_seen')):
            with self.subTest(phase=phase):
                result = m.classify((phase, identity, level, m.MASK64, phase))
                self.assertEqual(result['state'], name)
                self.assertFalse(result['complete'])
                for key in ('exception_level', 'mmu_enabled', 'data_cache_enabled',
                            'instruction_cache_enabled'):
                    self.assertIsNone(result[key])

    def test_complete_only_exports_el_and_selected_cache_bits(self):
        for el in (1, 2, 3):
            for mask in range(8):
                sctlr = (mask & 1) | ((mask & 2) << 1) | ((mask & 4) << 10)
                result = m.classify((3, IDENT, el * 4, sctlr, 3))
                self.assertTrue(result['complete'])
                self.assertEqual(result['exception_level'], el)
                self.assertEqual(result['mmu_enabled'], bool(mask & 1))
                self.assertEqual(result['data_cache_enabled'], bool(mask & 2))
                self.assertEqual(result['instruction_cache_enabled'], bool(mask & 4))
                self.assertNotIn('sctlr', result)
                self.assertNotIn('mpidr', result)

    def test_changing_phase_never_promotes_torn_data(self):
        for before, afters in m._ALLOWED_AFTER.items():
            for after in afters - {before}:
                identity = 0 if before == 0 else IDENT
                result = m.classify((before, identity, m.MASK64, m.MASK64, after))
                self.assertEqual(result['state'], 'publication_in_progress')
                self.assertFalse(result['complete'])
                self.assertIsNone(result['exception_level'])

    def test_every_monotonic_store_read_interleaving(self):
        count = 0
        # Each state is memory after one ordinary recorder store. Interleaving
        # only ordered stores/loads is explicit; this does not model caches.
        for el in (4, 8, 12):
            states = [(0, 0, 0, 0), (0, IDENT, 0, 0), (1, IDENT, 0, 0),
                      (1, IDENT, el, 0), (2, IDENT, el, 0),
                      (2, IDENT, el, 0x1005), (3, IDENT, el, 0x1005)]
            for times in itertools.combinations_with_replacement(range(len(states)), 5):
                words = tuple(states[t][column] for t, column in zip(times, (0, 1, 2, 3, 0)))
                result = m.classify(words)
                self.assertEqual(result['complete'], words[0] == words[-1] == 3)
                if result['complete']:
                    self.assertEqual(result['exception_level'], el // 4)
                    self.assertTrue(result['mmu_enabled'])
                count += 1
        self.assertEqual(count, 1386)

    def test_unsupported_el_interleavings(self):
        states = [(0, 0, 0, 0), (0, IDENT, 0, 0), (1, IDENT, 0, 0),
                  (1, IDENT, 0, 0), (255, IDENT, 0, 0)]
        count = 0
        for times in itertools.combinations_with_replacement(range(len(states)), 5):
            words = tuple(states[t][column] for t, column in zip(times, (0, 1, 2, 3, 0)))
            self.assertFalse(m.classify(words)['complete'])
            count += 1
        self.assertEqual(count, 126)

    def test_invalid_phases_and_edges(self):
        for before, after in itertools.product((0, 1, 2, 3, 255), repeat=2):
            if after not in m._ALLOWED_AFTER[before]:
                with self.assertRaisesRegex(m.TelemetryError, 'phase_regression'):
                    m.classify((before, IDENT, 8, 0, after))
        for phase in (4, 254, 256, m.MASK64):
            with self.assertRaisesRegex(m.TelemetryError, 'unknown_recorder_phase'):
                m.classify((phase, IDENT, 8, 0, phase))

    def test_strict_identity_and_complete_el(self):
        for phase in (1, 2, 3, 255):
            with self.assertRaisesRegex(m.TelemetryError, 'identity_missing'):
                m.classify((phase, 0, 8, 0, phase))
        for identity in (1, IDENT + 1, m.MASK64):
            with self.assertRaisesRegex(m.TelemetryError, 'unexpected_recorder_identity'):
                m.classify((0, identity, 0, 0, 0))
        for el in (0, 1, 2, 3, 16, m.MASK64):
            with self.assertRaisesRegex(m.TelemetryError, 'completed_recorder_el_invalid'):
                m.classify((3, IDENT, el, 0, 3))
        for el in (4, 8, 12):
            with self.assertRaisesRegex(m.TelemetryError, 'unsupported_el_phase_inconsistent'):
                m.classify((255, IDENT, el, 0, 255))

    def test_unused_fields_uninterpreted_before_complete(self):
        for phase in (0, 1, 2):
            result = m.classify((phase, IDENT, m.MASK64, m.MASK64, phase))
            self.assertIsNone(result['exception_level'])
            self.assertIsNone(result['mmu_enabled'])

    def test_malformed_words_and_shapes(self):
        for bad in (None, True, False, -1, 1 << 64, 'private', 1.0):
            for column in range(5):
                words = [3, IDENT, 8, 0, 3]; words[column] = bad
                with self.assertRaisesRegex(m.TelemetryError, 'invalid_record_word'):
                    m.classify(words)
        for shape in (None, {}, (), [0] * 4, [0] * 6, '00000'):
            with self.assertRaisesRegex(m.TelemetryError, 'invalid_record_shape'):
                m.classify(shape)

    def test_fixed_absolute_read_order(self):
        calls = []
        result = m.sample(reader((3, IDENT, 8, 0x1005, 3), calls), BASE)
        self.assertEqual(calls, [BASE + x for x in m.SAMPLE_OFFSETS])
        self.assertEqual(result['reads_attempted'], 5)
        self.assertEqual(result['reads_completed'], 5)
        self.assertTrue(result['complete'])

    def test_read_failures_stop_at_every_boundary_and_hide_text(self):
        for fail in range(5):
            calls = []
            def read(address):
                calls.append(address)
                if len(calls) == fail + 1:
                    raise OSError('/private/sensitive value 12345')
                return (2, IDENT, 8, 0, 2)[len(calls) - 1]
            with self.assertRaises(m.TelemetryError) as raised:
                m.sample(read, BASE)
            error = raised.exception
            self.assertEqual(str(error), 'recorder_read_failed')
            self.assertEqual(error.reads_attempted, fail + 1)
            self.assertEqual(error.reads_completed, fail)
            self.assertEqual(error.phase_before, 2 if fail else None)
            self.assertEqual(len(calls), fail + 1)

    def test_bad_read_values_stop_without_more_reads(self):
        for fail, bad in itertools.product(range(5), (None, True, -1, 1 << 64, 'private')):
            words = [2, IDENT, 8, 0, 2]; words[fail] = bad
            calls = []
            with self.assertRaisesRegex(m.TelemetryError, 'invalid_read64_result'):
                m.sample(reader(words, calls), BASE)
            self.assertEqual(len(calls), fail + 1)
        calls = []
        with self.assertRaisesRegex(m.TelemetryError, 'unknown_recorder_phase'):
            m.sample(reader((99,), calls), BASE)
        self.assertEqual(len(calls), 1)

    def test_bad_configuration_does_not_read(self):
        calls = []
        for base in (None, True, -1, 0, BASE + 8, 1 << 64, (1 << 64) - 0x4000):
            with self.assertRaisesRegex(m.TelemetryError, 'invalid_sampler_configuration'):
                m.sample(reader((0,) * 5, calls), base)
        with self.assertRaisesRegex(m.TelemetryError, 'invalid_sampler_configuration'):
            m.sample(None, BASE)
        self.assertEqual(calls, [])

    def test_tracker_monotonic_progress_and_sticky_complete(self):
        tracker = m.Tracker()
        for words in ((0, 0, 0, 0, 0), (0, IDENT, 0, 0, 1),
                      (1, IDENT, 8, 0, 2), (2, IDENT, 8, 0x1005, 3),
                      (3, IDENT, 8, 0x1005, 3), (3, IDENT, 8, 0x1005, 3)):
            result = tracker.sample(reader(words), BASE)
            self.assertIsNone(result['error'])
        self.assertTrue(result['complete'])
        self.assertEqual(result['samples_completed'], 6)
        self.assertEqual(result['reads_attempted'], 30)
        self.assertEqual(result['highest_phase_seen'], 3)
        self.assertEqual(result['exception_level'], 2)
        result['exception_level'] = 0
        self.assertEqual(tracker.report()['exception_level'], 2)

    def test_tracker_refuses_cross_sample_branch_and_identity_regression(self):
        for first, second, reason in (
                ((2, IDENT, 8, 0, 2), (1, IDENT, 8, 0, 1), 'cross_sample_regression'),
                ((2, IDENT, 8, 0, 2), (255, IDENT, 0, 0, 255), 'cross_sample_regression'),
                ((0, IDENT, 0, 0, 0), (0, 0, 0, 0, 0), 'identity_regression')):
            tracker = m.Tracker()
            tracker.sample(reader(first), BASE)
            result = tracker.sample(reader(second), BASE)
            self.assertIn(reason, result['error'])
            self.assertTrue(result['closed'])
            self.assertEqual(result['reads_attempted'], 10)

    def test_tracker_preserves_phase_on_read_failure_then_closes(self):
        tracker = m.Tracker()
        calls = []
        result = tracker.sample(reader((2,), calls), BASE)
        self.assertEqual(result['highest_phase_seen'], 2)
        self.assertFalse(result['complete'])
        self.assertEqual(result['reads_attempted'], 2)
        self.assertEqual(result['reads_completed'], 1)
        again = tracker.sample(reader((3, IDENT, 8, 0x1005, 3), calls), BASE)
        self.assertEqual(again, result)
        self.assertEqual(len(calls), 2)

    def test_tracker_completed_fields_cannot_change(self):
        for second in ((3, IDENT, 4, 0x1005, 3), (3, IDENT, 8, 0, 3)):
            tracker = m.Tracker()
            tracker.sample(reader((3, IDENT, 8, 0x1005, 3)), BASE)
            result = tracker.sample(reader(second), BASE)
            self.assertEqual(result['error'], 'completed_recorder_changed')
            self.assertTrue(result['complete'])
            self.assertEqual(result['exception_level'], 2)

    def test_tracker_budget_and_limit_validation(self):
        for bad in (0, 257, True, -1, 1.0, None):
            with self.assertRaisesRegex(m.TelemetryError, 'invalid_sample_limit'):
                m.Tracker(max_samples=bad)
        tracker = m.Tracker(max_samples=1)
        calls = []
        tracker.sample(reader((0,) * 5, calls), BASE)
        result = tracker.sample(reader((0,) * 5, calls), BASE)
        self.assertEqual(result['error'], 'recorder_sample_budget_exhausted')
        self.assertEqual(len(calls), 5)
        self.assertEqual(result['samples_attempted'], 1)

    def test_tracker_interrupt_counts_and_closes(self):
        for interrupt in (KeyboardInterrupt, SystemExit):
            for fail in range(5):
                tracker = m.Tracker(); calls = []
                def read(address):
                    calls.append(address)
                    if len(calls) == fail + 1:
                        raise interrupt('private')
                    return (2, IDENT, 8, 0, 2)[len(calls) - 1]
                with self.assertRaises(interrupt):
                    tracker.sample(read, BASE)
                result = tracker.report()
                self.assertEqual(result['error'], 'recorder_read_interrupted')
                self.assertEqual(result['reads_attempted'], fail + 1)
                self.assertEqual(result['reads_completed'], fail)
                self.assertTrue(result['closed'])
                self.assertEqual(result['highest_phase_seen'], 2 if fail else None)

    def test_tracker_reentrancy_stops_further_reads(self):
        tracker = m.Tracker(); calls = []
        def read(address):
            calls.append(address)
            tracker.sample(lambda unused: 0, BASE)
            return 0
        result = tracker.sample(read, BASE)
        self.assertEqual(result['error'], 'reentrant_recorder_sample')
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['reads_attempted'], 1)

    def test_report_never_contains_raw_identity_registers_or_addresses(self):
        tracker = m.Tracker()
        result = tracker.sample(reader((3, IDENT, 8, m.MASK64, 3)), BASE)
        text = json.dumps(result)
        for secret in (str(BASE), str(IDENT), str(m.MASK64)):
            self.assertNotIn(secret, text)
        self.assertNotIn('sctlr', result)
        self.assertNotIn('mpidr', result)


if __name__ == '__main__':
    unittest.main()
