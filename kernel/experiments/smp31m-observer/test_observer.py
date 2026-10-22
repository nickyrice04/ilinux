"""Original callback fault-prefix tests; no target or hardware emulation."""
import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location('observer31m', Path(__file__).with_name('observer.py'))
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
HELPER = 0x10000800000
CTR = (5 << 24) | (4 << 16)


class QualificationTests(unittest.TestCase):
    def test_three_supported_geometries(self):
        for dmin, cwg in ((4, 4), (4, 5), (5, 5)):
            q = m.qualify(HELPER, 8, m.HCR_VHE_HOST, (cwg << 24) | (dmin << 16))
            self.assertEqual(q.data_min_line_bytes, 4 << dmin)
            self.assertEqual(q.writeback_granule_bytes, 4 << cwg)
            for name, offset in m.RECORDS.items():
                address = m.record_address(q, name)
                self.assertEqual(address, HELPER + offset)
                self.assertEqual(address % q.writeback_granule_bytes, 0)
                self.assertLessEqual(address + q.writeback_granule_bytes, HELPER + m.CONTROL_OFFSET)

    def test_unknown_or_oversized_cwg_refuses(self):
        for cwg in (0, 1, 2, 3, *range(6, 16)):
            with self.subTest(cwg=cwg), self.assertRaises(m.ObservationError):
                m.qualify(HELPER, 8, m.HCR_VHE_HOST, (cwg << 24) | (4 << 16))

    def test_dmin_is_not_substituted_for_maximum_granule(self):
        for dmin, cwg in ((5, 4), (4, 6), (4, 0), (3, 4), (6, 6)):
            with self.subTest(dmin=dmin, cwg=cwg), self.assertRaises(m.ObservationError):
                m.qualify(HELPER, 8, m.HCR_VHE_HOST, (cwg << 24) | (dmin << 16))

    def test_wrong_cpu0_regime_refuses(self):
        for level, hcr in ((4, 0), (0, 0), (True, 0), (12, 0),
                           (8, m.HCR_VHE_HOST | 1), (8, 1 << 34), (8, 1 << 27),
                           (8, True), (8, -1)):
            with self.subTest(level=level, hcr=hcr), self.assertRaises(m.ObservationError):
                m.qualify(HELPER, level, hcr, CTR)

    def test_unrelated_hcr_bits_do_not_change_qualified_regime(self):
        self.assertEqual(m.qualify(HELPER, 8, m.HCR_VHE_HOST | (1 << 23), CTR).helper, HELPER)

    def test_helper_and_ctr_types_are_not_coerced(self):
        for helper in (True, 0, -0x4000, HELPER+8, 1 << 41, 0xc0000000000):
            with self.subTest(helper=helper), self.assertRaises(m.ObservationError):
                m.qualify(helper, 8, m.HCR_VHE_HOST, CTR)
        for ctr in (True, '0x05040000', -1, 1 << 64, float(CTR)):
            with self.subTest(ctr=ctr), self.assertRaises(m.ObservationError):
                m.qualify(HELPER, 8, m.HCR_VHE_HOST, ctr)

    def test_public_report_omits_private_binding(self):
        report = m.qualify(HELPER, 8, m.HCR_VHE_HOST, CTR).public()
        self.assertNotIn('helper', report)
        self.assertNotIn('ctr', report)
        self.assertFalse(report['effects_limited_to_cpu0'])
        self.assertEqual(report['cpu1_cache_state'], 'UNKNOWN')

    def test_clean_ownership_requires_literal_true(self):
        q = m.qualify(HELPER, 8, m.HCR_VHE_HOST, CTR)
        for key in ('initialized_clean', 'cpu0_stores_frozen'):
            for value in (False, 1, None, 'true'):
                flags = dict(initialized_clean=True, cpu0_stores_frozen=True)
                flags[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(m.ObservationError):
                    m.PairedTracker(q, 'vector', **flags)

    def test_bad_record_name_refuses_before_callbacks(self):
        q = m.qualify(HELPER, 8, m.HCR_VHE_HOST, CTR)
        for name in (None, True, '', 'control', 'VECTOR'):
            with self.subTest(name=name), self.assertRaises(m.ObservationError):
                m.PairedTracker(q, name, initialized_clean=True, cpu0_stores_frozen=True)

    def test_leaf_does_not_overlap_any_record_or_previous_control_leaf(self):
        self.assertGreaterEqual(m.CTR_LEAF_OFFSET, 0x210)
        self.assertLessEqual(m.CTR_LEAF_OFFSET + len(m.CTR_LEAF), 0x1000)
        self.assertEqual(len(m.CTR_LEAF), 8)


class PairedTests(unittest.TestCase):
    def fixture(self, values=(0,)*6, fail_at=None, exception=None, result=0, journal_fail=None):
        tracker = m.PairedTracker(m.qualify(HELPER, 8, m.HCR_VHE_HOST, CTR), 'vector',
                                 initialized_clean=True, cpu0_stores_frozen=True)
        events, reports, words = [], [], iter(values)
        def event(kind, *args):
            events.append((kind, *args))
            if len(events) == fail_at:
                raise exception if exception is not None else TimeoutError('PRIVATE transport detail')
        def read(address):
            event('read', address)
            return next(words)
        def maintain(address, size):
            event('civac', address, size)
            return result
        def journal(report):
            reports.append(report)
            if len(reports) == journal_fail:
                raise OSError('PRIVATE disk detail')
        return tracker, events, reports, read, maintain, journal

    def test_exact_zero_sequence_and_effect_scope(self):
        t, events, reports, read, maintain, journal = self.fixture()
        out = t.sample(read, maintain, journal)
        at = HELPER + 0x1000
        self.assertEqual(events, [('read', at), ('read', at+8), ('read', at),
                                  ('civac', at, 64), ('read', at), ('read', at+8), ('read', at)])
        self.assertEqual((out['maintenance_intents'], out['maintenance_attempted'],
                          out['maintenance_acknowledged']), (1, 1, 1))
        self.assertEqual((out['reads_attempted'], out['reads_completed']), (6, 6))
        self.assertEqual(out['samples_completed'], 1)
        self.assertEqual(out['cpu1_execution'], 'UNVERIFIED')
        self.assertFalse(out['negative_excludes_execution'])
        self.assertFalse(out['effects_limited_to_cpu0'])
        self.assertFalse(t.closed)
        self.assertEqual(reports[0]['maintenance_intents'], 1)
        self.assertEqual(reports[0]['maintenance_attempted'], 0)
        self.assertEqual(reports[1]['maintenance_acknowledged'], 1)

    def test_cached_identity_skips_maintenance(self):
        t, events, _, read, maintain, journal = self.fixture((2, 0x40001, 2))
        out = t.sample(read, maintain, journal)
        self.assertEqual(len(events), 3)
        self.assertEqual(out['maintenance_intents'], 0)
        self.assertEqual(out['observation_channel'], 'cached')
        self.assertEqual(out['identity_status'], 'expected_cpu1')
        self.assertEqual(out['cpu1_execution'], 'PREFIX_IDENTITY_OBSERVED')
        self.assertTrue(t.closed)

    def test_maintained_identity_does_not_claim_cache_cause(self):
        t, events, _, read, maintain, journal = self.fixture((0, 0, 0, 2, 0x40001, 2))
        out = t.sample(read, maintain, journal)
        self.assertEqual(len(events), 7)
        self.assertEqual(out['observation_channel'], 'maintained')
        self.assertEqual(out['identity_status'], 'expected_cpu1')
        self.assertEqual(out['visibility_cause'], 'UNKNOWN')
        self.assertTrue(t.closed)

    def test_partial_snapshots_close_without_identity_claim(self):
        for part in ((1, 0, 1), (0, 0x40001, 0), (0, 0x40001, 2), (1, 0x99999, 2)):
            for channel in ('cached', 'maintained'):
                words = part if channel == 'cached' else (0, 0, 0) + part
                with self.subTest(part=part, channel=channel):
                    t, events, _, read, maintain, journal = self.fixture(words)
                    out = t.sample(read, maintain, journal)
                    self.assertTrue(t.closed)
                    self.assertTrue(out['any_record_seen'])
                    self.assertEqual(out['identity_status'], 'not_committed')
                    self.assertEqual(out['cpu1_execution'], 'UNVERIFIED')
                    self.assertEqual(len(events), 3 if channel == 'cached' else 7)

    def test_each_target_fault_closes_and_preserves_prefix(self):
        for failure in range(1, 8):
            for exc in (TimeoutError('PRIVATE target'), ValueError('PRIVATE value'), KeyboardInterrupt()):
                with self.subTest(failure=failure, exc=type(exc).__name__):
                    t, events, _, read, maintain, journal = self.fixture(fail_at=failure, exception=exc)
                    with self.assertRaises(type(exc)):
                        t.sample(read, maintain, journal)
                    self.assertEqual(len(events), failure)
                    self.assertTrue(t.closed)
                    self.assertEqual(t.state['error'], 'maintenance_interrupted')
                    self.assertNotIn('PRIVATE', str(t.state))
                    self.assertEqual(t.state['maintenance_attempted'], int(failure >= 4))
                    self.assertEqual(t.state['maintenance_acknowledged'], int(failure > 4))
                    with self.assertRaisesRegex(m.ObservationError, 'maintenance_tracker_closed'):
                        t.sample(read, maintain, journal)
                    self.assertEqual(len(events), failure)

    def test_bad_maintenance_result_has_no_following_reads(self):
        for result in (None, True, False, 1, -1, '0'):
            with self.subTest(result=result):
                t, events, _, read, maintain, journal = self.fixture(result=result)
                with self.assertRaisesRegex(m.ObservationError, 'maintenance_return'):
                    t.sample(read, maintain, journal)
                self.assertEqual(len(events), 4)
                self.assertEqual(t.state['maintenance_acknowledged'], 0)

    def test_journal_failure_before_or_after_maintenance_has_no_followup(self):
        for index in (1, 2):
            t, events, reports, read, maintain, journal = self.fixture(journal_fail=index)
            with self.assertRaises(OSError):
                t.sample(read, maintain, journal)
            self.assertEqual(len(reports), index)
            self.assertEqual(len(events), 3 if index == 1 else 4)
            self.assertTrue(t.state['journal_failed'])
            self.assertTrue(t.closed)
            self.assertNotIn('PRIVATE', str(t.state))

    def test_invalid_phases_and_identities_close_without_more_actions(self):
        for part in ((3, 0, 3), (True, 0, 0), (2, 0x40000, 2),
                     (2, 0x40001, 1), (2, -1, 2), (2, 0, 2)):
            t, events, _, read, maintain, journal = self.fixture(part)
            with self.subTest(part=part), self.assertRaises(m.ObservationError):
                t.sample(read, maintain, journal)
            self.assertTrue(t.closed)
            self.assertLessEqual(len(events), 3)
            self.assertEqual(t.state['maintenance_attempted'], 0)

    def test_report_and_journal_copies_cannot_mutate_state(self):
        t, _, reports, read, maintain, journal = self.fixture()
        out = t.sample(read, maintain, journal)
        reports[0]['cached']['complete'] = False
        out['maintained']['complete'] = False
        self.assertTrue(t.state['cached']['complete'])
        self.assertTrue(t.state['maintained']['complete'])

    def test_sample_budget_refuses_without_callbacks(self):
        t, events, _, read, maintain, journal = self.fixture()
        t.state['samples_attempted'] = m.MAX_SAMPLES
        with self.assertRaisesRegex(m.ObservationError, 'maintenance_sample_budget'):
            t.sample(read, maintain, journal)
        self.assertFalse(events)
        self.assertTrue(t.closed)

    def test_repeated_zero_cycles_count_actual_intents(self):
        t, events, _, read, maintain, journal = self.fixture((0,)*12)
        t.sample(read, maintain, journal)
        out = t.sample(read, maintain, journal)
        self.assertEqual(len(events), 14)
        self.assertEqual(out['samples_completed'], 2)
        self.assertEqual(out['reads_completed'], 12)
        self.assertEqual(out['maintenance_acknowledged'], 2)


if __name__ == '__main__':
    unittest.main()
