#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original synthetic read schedules; never connects to a native target."""
import importlib.util
import itertools
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('collector.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE = 1 << 40
MPIDR = 0x40001
NORMAL_TOP = BASE + 0x178000
FRESH_MPIDR = (1 << 64) - 1
# Independent literals make a mistakenly changed acquisition order fail.
EXPECTED_ORDER = (0x90258, 0x90250, 0x90020, 0x90028, 0x94000, 0x94008,
                  0x9ffe8, 0x9ffc8, 0x9ffb8, 0x9fd48, 0x9fd18)


def initial_memory():
    return {
        0x90258: 0, 0x90250: 0, 0x90020: FRESH_MPIDR, 0x90028: 0,
        0x94000: 0xd1a631e0d1a631e0, 0x94008: 0xd1a631e0d1a631e0,
        0x9ffe8: 0, 0x9ffc8: 0, 0x9ffb8: 0, 0x9fd48: 0, 0x9fd18: 0,
    }


class Memory:
    def __init__(self):
        self.words = initial_memory()
        self.calls = []
        self.before = {}
        self.after = {}

    def __call__(self, offset):
        call = len(self.calls)
        self.calls.append(offset)
        if call in self.before:
            self.before[call](self.words)
        value = self.words[offset]
        if call in self.after:
            self.after[call](self.words)
        return value

    def arrive(self):
        self.words.update({0x90258: 1, 0x90250: MPIDR,
                           0x90020: MPIDR, 0x90028: NORMAL_TOP})


class CollectorTests(unittest.TestCase):
    def test_fixed_order_allowlist_and_size(self):
        mem = Memory()
        result = m.Collector(mem, BASE, max_samples=1).sample()
        self.assertEqual(tuple(mem.calls), EXPECTED_ORDER)
        self.assertEqual(m.READ_ALLOWLIST, frozenset(EXPECTED_ORDER))
        self.assertEqual(m.STACK_TOP - m.STACK_BOTTOM, 48 * 1024)
        self.assertEqual(result['read_calls'], 11)
        self.assertEqual(result['last_identity_stage'], 'no_reset_record_seen')
        self.assertEqual(result['reason'], 'sample_budget_exhausted')

    def test_both_partial_publication_orders(self):
        for changes, stage in [({0x90020: MPIDR}, 'mpidr_publication_seen'),
                               ({0x90028: NORMAL_TOP}, 'stack_publication_seen')]:
            mem = Memory()
            mem.words.update(changes)
            result = m.Collector(mem, BASE).sample()
            self.assertFalse(result['closed'])
            self.assertEqual(result['last_identity_stage'], stage)
            self.assertFalse(result['arrival_observed'])

    def test_all_140_monotonic_publication_interleavings(self):
        # Four producer stores can happen at five boundaries around the first
        # four reader loads. These schedules are independent of the classifier.
        for first, second in [(0x90020, 0x90028), (0x90028, 0x90020)]:
            sequence = (first, second, 0x90250, 0x90258)
            values = {0x90020: MPIDR, 0x90028: NORMAL_TOP, 0x90250: MPIDR, 0x90258: 1}
            for boundaries in itertools.combinations_with_replacement(range(5), 4):
                mem = Memory()
                for boundary in set(boundaries):
                    updates = {offset: values[offset] for position, offset in enumerate(sequence)
                               if boundaries[position] == boundary}
                    mem.before[boundary] = lambda words, updates=updates: words.update(updates)
                with self.subTest(order=sequence, schedule=boundaries):
                    result = m.Collector(mem, BASE).sample()
                    self.assertNotEqual(result['reason'], 'identity_inconsistent')
                    self.assertEqual(result['samples_completed'], 1)
                    # Only a flag already visible at the first load can count.
                    self.assertEqual(result['arrival_observed'], boundaries[-1] == 0)

    def test_late_flag_waits_for_next_explicit_sample(self):
        mem = Memory()
        mem.after[0] = lambda words: mem.arrive()
        collector = m.Collector(mem, BASE)
        first = collector.sample()
        self.assertEqual(first['last_identity_stage'], 'spin_identity_seen')
        self.assertFalse(first['arrival_observed'])
        second = collector.sample()
        self.assertTrue(second['arrival_observed'])
        self.assertEqual(second['reason'], 'arrival_observed_only')
        self.assertEqual(second['read_calls'], 22)

    def test_nonzero_flag_requires_complete_identity(self):
        for missing in (0x90250, 0x90020, 0x90028):
            mem = Memory()
            mem.arrive()
            mem.words[missing] = initial_memory()[missing]
            result = m.Collector(mem, BASE).sample()
            self.assertEqual(result['reason'], 'identity_inconsistent')
            self.assertEqual(result['read_calls'], 4)
            self.assertFalse(result['arrival_observed'])

    def test_bad_identity_and_unreviewed_callback_count_refuse(self):
        for offset, value, reason in [(0x90020, 0x40002, 'identity_inconsistent'),
                                      (0x90028, BASE + 0xa0000, 'identity_inconsistent'),
                                      (0x90250, 0x40002, 'identity_inconsistent'),
                                      (0x90258, 2, 'unexpected_flag_count')]:
            mem = Memory()
            mem.arrive()
            mem.words[offset] = value
            result = m.Collector(mem, BASE).sample()
            self.assertEqual(result['reason'], reason)
            self.assertEqual(result['read_calls'], 4)

    def test_lower_canary_corruption_stops_before_frame_reads(self):
        for offset, count in [(0x94000, 5), (0x94008, 6)]:
            mem = Memory()
            mem.words[offset] ^= 1
            result = m.Collector(mem, BASE).sample()
            self.assertEqual(result['reason'], 'lower_canary_changed')
            self.assertEqual(result['read_calls'], count)
            self.assertFalse(result['last_sample_canaries_intact'])

    def test_sticky_markers_survive_stack_slot_reuse(self):
        mem = Memory()
        mem.words[0x9ffe8] = BASE + 0x974
        collector = m.Collector(mem, BASE)
        first = collector.sample()
        mem.words[0x9ffe8] = 0
        mem.words[0x9ffb8] = BASE + 0x32958
        second = collector.sample()
        self.assertTrue(first['recognized_frame_remnants']['reset_c_non_el3_frame'])
        self.assertTrue(second['recognized_frame_remnants']['reset_c_non_el3_frame'])
        self.assertTrue(second['recognized_frame_remnants']['init_cpu_frame'])
        self.assertFalse(second['entry_authorized'])
        self.assertFalse(second['current_pc_known'])

    def test_errors_at_every_read_stop_without_retry_or_exception_echo(self):
        for failing in range(11):
            mem = Memory()
            mem.words[0x9ffe8] = BASE + 0x974
            def reader(offset):
                if len(mem.calls) == failing:
                    mem.calls.append(offset)
                    raise RuntimeError('PRIVATE_VALUE_SHOULD_NOT_LEAK')
                return mem(offset)
            collector = m.Collector(reader, BASE)
            result = collector.sample()
            self.assertEqual(result['reason'], 'read_error')
            self.assertEqual(result['read_calls'], failing + 1)
            self.assertEqual(result['samples_completed'], 0)
            self.assertNotIn('PRIVATE_VALUE', json.dumps(result))
            self.assertEqual(result['recognized_frame_remnants']['reset_c_non_el3_frame'], failing > 6)
            for _ in range(3):
                self.assertEqual(collector.sample(), result)
            self.assertEqual(len(mem.calls), failing + 1)

    def test_invalid_reader_values_fail_at_every_position(self):
        for bad in (True, -1, 1 << 64, 1.5, 'PRIVATE_VALUE', b'PRIVATE_VALUE', None):
            for failing in range(11):
                mem = Memory()
                def reader(offset):
                    if len(mem.calls) == failing:
                        mem.calls.append(offset)
                        return bad
                    return mem(offset)
                result = m.Collector(reader, BASE).sample()
                self.assertEqual(result['reason'], 'invalid_read64_result')
                self.assertEqual(result['read_calls'], failing + 1)
                self.assertNotIn('PRIVATE_VALUE', json.dumps(result))

    def test_maximum_budget_and_excessive_calls(self):
        mem = Memory()
        collector = m.Collector(mem, BASE, max_samples=256)
        for _ in range(300):
            result = collector.sample()
        self.assertEqual(result['samples_attempted'], 256)
        self.assertEqual(result['samples_completed'], 256)
        self.assertEqual(result['read_calls'], 2816)
        self.assertEqual(len(mem.calls), 2816)
        self.assertEqual(result['reason'], 'sample_budget_exhausted')

    def test_arrival_closes_without_authorizing_any_hardware_operation(self):
        mem = Memory()
        mem.arrive()
        collector = m.Collector(mem, BASE)
        result = collector.sample()
        for _ in range(10):
            self.assertEqual(collector.sample(), result)
        self.assertEqual(len(mem.calls), 11)
        self.assertTrue(result['arrival_observed'])
        self.assertFalse(result['entry_authorized'])
        self.assertFalse(result['native_deployment_ready'])
        self.assertEqual(result['hardware_compatibility_claim'], 'NONE')

    def test_reports_contain_no_raw_ram_or_reference_to_mutable_state(self):
        mem = Memory()
        mem.words[0x9ffe8] = BASE + 0x974
        collector = m.Collector(mem, BASE)
        report = collector.sample()
        for raw in (BASE, BASE + 0x974, m.CANARY, FRESH_MPIDR):
            self.assertNotIn(str(raw), json.dumps(report))
            self.assertNotIn(hex(raw), json.dumps(report))
        report['recognized_frame_remnants']['reset_c_non_el3_frame'] = False
        self.assertTrue(collector.report()['recognized_frame_remnants']['reset_c_non_el3_frame'])

    def test_no_reader_calls_during_construction_or_reporting(self):
        mem = Memory()
        collector = m.Collector(mem, BASE)
        self.assertEqual(collector.report()['reason'], 'not_sampled')
        self.assertEqual(mem.calls, [])

    def test_invalid_constructor_inputs_never_read(self):
        mem = Memory()
        for base, limit in [(True, 1), (0, 1), (BASE + 8, 1), (-1, 1),
                            (1 << 64, 1), (((1 << 64) - 0x4000), 1),
                            (BASE, True), (BASE, 0), (BASE, 257), (BASE, 1.5)]:
            with self.assertRaisesRegex(ValueError, '^invalid_collector_configuration$'):
                m.Collector(mem, base, max_samples=limit)
        self.assertEqual(mem.calls, [])

    def test_reentrant_sample_closes_without_nested_reads(self):
        mem = Memory()
        def reader(offset):
            collector.sample()
            return mem(offset)
        collector = m.Collector(reader, BASE)
        result = collector.sample()
        self.assertEqual(result['reason'], 'reentrant_sample')
        self.assertEqual(result['read_calls'], 1)
        self.assertEqual(result['samples_completed'], 0)

    def test_user_interrupt_closes_and_propagates(self):
        def interrupted(offset):
            raise KeyboardInterrupt()
        collector = m.Collector(interrupted, BASE)
        with self.assertRaises(KeyboardInterrupt):
            collector.sample()
        result = collector.sample()
        self.assertEqual(result['reason'], 'read_interrupted')
        self.assertEqual(result['read_calls'], 1)

    def test_fixed_private_read_gate_cannot_read_extra_offsets(self):
        mem = Memory()
        collector = m.Collector(mem, BASE)
        with self.assertRaisesRegex(m._Abort, '^offset_not_allowlisted$'):
            collector._read(0x280688004)
        self.assertEqual(mem.calls, [])


if __name__ == '__main__':
    unittest.main()
