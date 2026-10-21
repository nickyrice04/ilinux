#!/usr/bin/env python3
"""Original pure recorder tests: no devices or privileged execution."""
import importlib.util
import itertools
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('telemetry31f', Path(__file__).with_name('telemetry.py'))
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
    def test_first_mrs_fault_leaves_marker_without_identity_or_el(self):
        result = m.classify((1, 0, 0, 0, 1))
        self.assertEqual(result['state'], 'pre_mrs_entry_phase_seen')
        self.assertEqual(result['identity_status'], 'not_committed')
        self.assertFalse(result['identity_recorded'])
        self.assertFalse(result['identity_seen'])
        self.assertFalse(result['complete'])
        self.assertIsNone(result['exception_level'])
        self.assertIsNone(result['error'])

    def test_current_el_fault_preserves_committed_cpu1_identity(self):
        result = m.classify((2, IDENT, 0, 0, 2))
        self.assertEqual(result['state'], 'identity_phase_seen')
        self.assertTrue(result['identity_recorded'])
        self.assertTrue(result['identity_seen'])
        self.assertEqual(result['observed_cpu_id'], 1)
        self.assertIsNone(result['exception_level'])
        self.assertFalse(result['complete'])

    def test_sctlr_fault_preserves_el_without_inventing_cache_bits(self):
        for el in (1, 2, 3):
            result = m.classify((3, IDENT, el * 4, 0, 3))
            self.assertEqual(result['exception_level'], el)
            self.assertFalse(result['complete'])
            self.assertTrue(all(result[key] is None for key in m.CACHE_KEYS))

    def test_zero_phase_only_means_no_publication_observed(self):
        result = m.classify((0, 0, 0, 0, 0))
        self.assertEqual(result['state'], 'no_recorder_publication_seen')
        self.assertFalse(result['complete'])

    def test_future_fields_uninterpreted_in_early_phases(self):
        for phase, ident, el, cache in itertools.product((0, 1), (0, IDENT, m.MASK64),
                                                       (0, 8, m.MASK64), (0, m.MASK64)):
            result = m.classify((phase, ident, el, cache, phase))
            self.assertFalse(result['identity_seen'])
            self.assertFalse(result['identity_recorded'])
            self.assertIsNone(result['exception_level'])
            self.assertIsNone(result['error'])
            self.assertTrue(all(result[key] is None for key in m.CACHE_KEYS))
        result = m.classify((2, IDENT, m.MASK64, m.MASK64, 2))
        self.assertIsNone(result['exception_level'])
        self.assertIsNone(result['error'])

    def test_full_known18_identity_classification_and_wrong_cpu_stop(self):
        seen = set()
        for cpu in range(18):
            cluster, core = divmod(cpu, 6)
            kind, name, prefix = ('M', 'Performance', 4) if cpu < 12 else ('P', 'Super', 1)
            mpidr = prefix << 16 | cluster << 8 | core
            result = m.classify((4, mpidr, 8, 0x1005, 4))
            self.assertEqual(result['observed_cpu_id'], cpu)
            self.assertEqual(result['observed_cluster'], cluster)
            self.assertEqual(result['observed_core'], core)
            self.assertEqual(result['observed_core_type'], kind)
            self.assertEqual(result['observed_macos_class'], name)
            self.assertEqual(result['identity_mapping_evidence'], 'expected_mpidr_map')
            self.assertEqual(result['complete'], cpu == 1)
            self.assertEqual(result['error'], None if cpu == 1 else 'unexpected_recorder_identity')
            seen.add(mpidr)
        self.assertEqual(len(seen), 18)

    def test_unknown_identity_does_not_default_to_efficiency(self):
        for ident in (0, 1, IDENT + 5, 0x40106, 0x10206, 0x80040001, m.MASK64):
            result = m.classify((2, ident, 0, 0, 2))
            self.assertEqual(result['identity_status'], 'unknown')
            self.assertIsNone(result['observed_cpu_id'])
            self.assertIsNone(result['observed_core_type'])
            self.assertIsNone(result['observed_macos_class'])
            self.assertEqual(result['error'], 'unexpected_recorder_identity')
            self.assertFalse(result['complete'])

    def test_complete_only_exports_selected_cache_bits(self):
        for el, mask in itertools.product((1, 2, 3), range(8)):
            sctlr = (mask & 1) | ((mask & 2) << 1) | ((mask & 4) << 10)
            result = m.classify((4, IDENT, el * 4, sctlr, 4))
            self.assertTrue(result['complete'])
            self.assertEqual(result['exception_level'], el)
            for bit, key in enumerate(m.CACHE_KEYS):
                self.assertEqual(result[key], bool(mask & (1 << bit)))
            self.assertNotIn('sctlr', result)
            self.assertNotIn('mpidr', result)

    def test_changing_phase_does_not_promote_completion_or_future_fields(self):
        for before, afters in m._ALLOWED_AFTER.items():
            for after in afters - {before}:
                identity = IDENT if before in m.IDENTITY_PHASES else m.MASK64
                result = m.classify((before, identity, m.MASK64, m.MASK64, after))
                self.assertEqual(result['state'], 'publication_in_progress')
                self.assertFalse(result['complete'])
                self.assertIsNone(result['exception_level'])
                self.assertIsNone(result['error'])

    def test_every_monotonic_publication_interleaving(self):
        count = 0
        # Ordinary store/read interleavings only. This is not a cache model.
        for el in (4, 8, 12):
            states = [(0, 0, 0, 0), (1, 0, 0, 0), (1, IDENT, 0, 0),
                      (2, IDENT, 0, 0), (2, IDENT, el, 0), (3, IDENT, el, 0),
                      (3, IDENT, el, 0x1005), (4, IDENT, el, 0x1005)]
            for times in itertools.combinations_with_replacement(range(len(states)), 5):
                words = tuple(states[t][column] for t, column in zip(times, (0, 1, 2, 3, 0)))
                result = m.classify(words)
                self.assertIsNone(result['error'])
                self.assertEqual(result['complete'], words[0] == words[-1] == 4)
                self.assertEqual(result['identity_seen'], words[0] >= 2)
                if result['exception_level'] is not None:
                    self.assertEqual(result['exception_level'], el // 4)
                    self.assertEqual(words[0], words[-1])
                count += 1
        self.assertEqual(count, 2376)

    def test_unsupported_el_interleavings(self):
        states = [(0, 0, 0, 0), (1, 0, 0, 0), (1, IDENT, 0, 0),
                  (2, IDENT, 0, 0), (2, IDENT, 0, 0), (3, IDENT, 0, 0),
                  (255, IDENT, 0, 0)]
        count = 0
        for times in itertools.combinations_with_replacement(range(len(states)), 5):
            words = tuple(states[t][column] for t, column in zip(times, (0, 1, 2, 3, 0)))
            result = m.classify(words)
            self.assertFalse(result['complete'])
            # Phase3 may expose an unsupported CurrentEL before phase255.
            self.assertIn(result['error'], (None, 'committed_recorder_el_invalid',
                                           'unsupported_recorder_el'))
            count += 1
        self.assertEqual(count, 462)

    def test_invalid_phases_and_branches(self):
        for before, after in itertools.product(m.PHASES, repeat=2):
            if after not in m._ALLOWED_AFTER[before]:
                with self.assertRaisesRegex(m.TelemetryError, 'phase_regression'):
                    m.classify((before, IDENT, 8, 0, after))
        for phase in (5, 254, 256, m.MASK64):
            with self.assertRaisesRegex(m.TelemetryError, 'unknown_recorder_phase'):
                m.classify((phase, IDENT, 8, 0, phase))

    def test_invalid_and_unsupported_el(self):
        for el, phase in itertools.product((0, 1, 2, 3, 16, m.MASK64), (3, 4)):
            result = m.classify((phase, IDENT, el, 0, phase))
            self.assertEqual(result['error'], 'committed_recorder_el_invalid')
            self.assertFalse(result['complete'])
        for el in (4, 8, 12):
            result = m.classify((255, IDENT, el, 0, 255))
            self.assertEqual(result['error'], 'unsupported_el_phase_inconsistent')
        self.assertEqual(m.classify((255, IDENT, 0, 0, 255))['state'], 'unsupported_el_phase_seen')
        self.assertEqual(m.classify((255, IDENT, 0, 0, 255))['error'], 'unsupported_recorder_el')

    def test_unsupported_el_closes_tracker_without_polling_or_completion(self):
        tracker = m.Tracker(); calls = []
        result = tracker.sample(reader((255, IDENT, 0, 0, 255), calls), BASE)
        self.assertEqual(result['error'], 'unsupported_recorder_el')
        self.assertEqual(result['highest_phase_seen'], 255)
        self.assertEqual(result['observed_cpu_id'], 1)
        self.assertTrue(result['closed'])
        self.assertFalse(result['complete'])
        self.assertEqual(tracker.sample(reader((4, IDENT, 8, 0, 4), calls), BASE), result)
        self.assertEqual(len(calls), 5)

    def test_malformed_words_and_shapes(self):
        for bad, column in itertools.product((None, True, False, -1, 1 << 64, 'private', 1.0), range(5)):
            words = [4, IDENT, 8, 0, 4]; words[column] = bad
            with self.assertRaisesRegex(m.TelemetryError, 'invalid_record_word'):
                m.classify(words)
        for shape in (None, {}, (), [0] * 4, [0] * 6, '00000'):
            with self.assertRaisesRegex(m.TelemetryError, 'invalid_record_shape'):
                m.classify(shape)

    def test_fixed_read_order_and_wrong_identity_is_bracketed(self):
        for ident in (IDENT, 0x10200, m.MASK64):
            calls = []
            result = m.sample(reader((4, ident, 8, 0x1005, 4), calls), BASE)
            self.assertEqual(calls, [BASE + x for x in m.SAMPLE_OFFSETS])
            self.assertEqual(result['reads_attempted'], 5)
            self.assertEqual(result['reads_completed'], 5)

    def test_read_failures_stop_at_each_boundary_and_hide_exception_text(self):
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

    def test_tracker_progress_with_el_phase_then_changing_phase(self):
        tracker = m.Tracker()
        records = ((0, 0, 0, 0, 0), (1, 0, 0, 0, 1), (2, IDENT, 0, 0, 2),
                   (3, IDENT, 8, 0, 3), (3, IDENT, 8, 0x1005, 4),
                   (4, IDENT, 8, 0x1005, 4), (4, IDENT, 8, 0x1005, 4))
        for words in records:
            result = tracker.sample(reader(words), BASE)
            self.assertIsNone(result['error'])
        self.assertTrue(result['complete'])
        self.assertEqual(result['samples_completed'], len(records))
        self.assertEqual(result['reads_attempted'], 5 * len(records))
        self.assertEqual(result['highest_phase_seen'], 4)
        self.assertEqual(result['exception_level'], 2)
        result['observed_cpu_id'] = 99
        self.assertEqual(tracker.report()['observed_cpu_id'], 1)

    def test_tracker_wrong_identity_retained_then_no_more_reads(self):
        tracker = m.Tracker(); calls = []
        result = tracker.sample(reader((2, 0x10200, 0, 0, 2), calls), BASE)
        self.assertEqual(result['error'], 'unexpected_recorder_identity')
        self.assertEqual(result['observed_cpu_id'], 12)
        self.assertEqual(result['observed_macos_class'], 'Super')
        self.assertTrue(result['identity_sample_complete'])
        self.assertTrue(result['closed'])
        self.assertFalse(result['complete'])
        self.assertEqual(tracker.sample(reader((4, IDENT, 8, 0, 4), calls), BASE), result)
        self.assertEqual(len(calls), 5)

    def test_tracker_cross_sample_phase_regression_closes(self):
        for first, second in (((2, IDENT, 0, 0, 2), (1, 0, 0, 0, 1)),
                              ((4, IDENT, 8, 0, 4), (3, IDENT, 8, 0, 3))):
            tracker = m.Tracker()
            tracker.sample(reader(first), BASE)
            result = tracker.sample(reader(second), BASE)
            self.assertEqual(result['error'], 'recorder_cross_sample_regression')
            self.assertTrue(result['closed'])

    def test_tracker_committed_identity_cannot_disappear(self):
        tracker = m.Tracker()
        tracker.sample(reader((2, IDENT, 0, 0, 2)), BASE)
        result = tracker.sample(reader((2, 0, 0, 0, 2)), BASE)
        self.assertEqual(result['error'], 'unexpected_recorder_identity')
        self.assertTrue(result['identity_seen'])
        self.assertEqual(result['identity_status'], 'unknown')

    def test_tracker_retains_phase_and_partial_identity_on_failure(self):
        for ident, cpu in ((IDENT, 1), (0x10200, 12), (m.MASK64, None)):
            tracker = m.Tracker()
            result = tracker.sample(reader((2, ident)), BASE)
            self.assertEqual(result['error'], 'recorder_read_failed')
            self.assertEqual(result['highest_phase_seen'], 2)
            self.assertEqual(result['observed_cpu_id'], cpu)
            self.assertFalse(result['identity_sample_complete'])
            self.assertEqual(result['reads_attempted'], 3)
            self.assertEqual(result['reads_completed'], 2)
            self.assertFalse(result['complete'])

    def test_tracker_el_and_completed_fields_cannot_change(self):
        for first, second, reason in (
                ((3, IDENT, 8, 0, 3), (3, IDENT, 4, 0, 3), 'committed_recorder_el_changed'),
                ((3, IDENT, 8, 0, 3), (255, IDENT, 0, 0, 255), 'unsupported_recorder_el'),
                ((4, IDENT, 8, 0x1005, 4), (4, IDENT, 8, 0, 4), 'completed_recorder_changed')):
            tracker = m.Tracker()
            tracker.sample(reader(first), BASE)
            result = tracker.sample(reader(second), BASE)
            self.assertEqual(result['error'], reason)
            self.assertEqual(result['exception_level'], 2)

    def test_tracker_budget_and_limit_validation(self):
        for bad in (0, 257, True, -1, 1.0, None):
            with self.assertRaisesRegex(m.TelemetryError, 'invalid_sample_limit'):
                m.Tracker(max_samples=bad)
        tracker = m.Tracker(max_samples=1); calls = []
        tracker.sample(reader((0,) * 5, calls), BASE)
        result = tracker.sample(reader((0,) * 5, calls), BASE)
        self.assertEqual(result['error'], 'recorder_sample_budget_exhausted')
        self.assertEqual(len(calls), 5)

    def test_tracker_interrupt_counts_closes_and_retains_partial_identity(self):
        for interrupt, fail in itertools.product((KeyboardInterrupt, SystemExit), range(5)):
            tracker = m.Tracker(); calls = []
            def read(address):
                calls.append(address)
                if len(calls) == fail + 1:
                    raise interrupt('private')
                return (2, IDENT, 0, 0, 2)[len(calls) - 1]
            with self.assertRaises(interrupt):
                tracker.sample(read, BASE)
            result = tracker.report()
            self.assertEqual(result['error'], 'recorder_read_interrupted')
            self.assertEqual(result['reads_attempted'], fail + 1)
            self.assertEqual(result['reads_completed'], fail)
            self.assertTrue(result['closed'])
            self.assertEqual(result['observed_cpu_id'], 1 if fail >= 2 else None)

    def test_tracker_reentrancy_stops_further_reads(self):
        tracker = m.Tracker(); calls = []
        def read(address):
            calls.append(address)
            tracker.sample(lambda unused: 0, BASE)
            return 0
        result = tracker.sample(read, BASE)
        self.assertEqual(result['error'], 'reentrant_recorder_sample')
        self.assertEqual(len(calls), 1)

    def test_no_public_summary_contains_raw_registers_or_addresses(self):
        for ident in (IDENT, 0x10200, m.MASK64):
            tracker = m.Tracker()
            result = tracker.sample(reader((4, ident, 8, m.MASK64, 4)), BASE)
            text = json.dumps(result)
            for raw in (str(BASE), str(ident), str(m.MASK64)):
                self.assertNotIn(raw, text)
            self.assertNotIn('sctlr', result)
            self.assertNotIn('mpidr', result)


if __name__ == '__main__':
    unittest.main()
