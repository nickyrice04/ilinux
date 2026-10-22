"""Original31N contract/fault models. No target I/O or Apple firmware emulation."""
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31n as j
import test_smp31m as frozen

t, prior, fixtures = frozen.t, frozen.prior, frozen.fixtures
synthetic_image = frozen.synthetic_image
PAIR_WORDS = (0xd2900008, 0xf2b00d08, 0xf2c00048, 0x52800049,
              0xd5033f9f, 0xb9000509, 0xd5033f9f, 0xb9000909,
              0xd5033f9f, 0xd28629c0, 0xd65f03c0)
PAIR_BYTES = struct.pack('<11I', *PAIR_WORDS)


class Fake(frozen.Fake):
    def __init__(self):
        super().__init__()
        self.pair_ready = False
        self.pair_calls = 0
        self.pair_fault = None
        self.pair_trace = []
        self.pair_after_calls = []
        self.pair_translation_bad = False
        self.pair_bad_readback = False
        self.pair_corrupt_padding = False
        self.pair_drop_initialization = False

    def writemem(self, address, data):
        if address == t.HELPER_ADDR+0x240:
            assert not self.hw and data in (PAIR_BYTES, bytes(64))
            self.pair_trace.append('initialize' if len(data) == 64 else 'write')
            if self.mutation() and not (len(data) == 64 and self.pair_drop_initialization):
                self.ram[address-t.BASE:address-t.BASE+len(data)] = data
                if len(data) == 44 and self.pair_bad_readback:
                    self.ram[address-t.BASE] ^= 1
                if len(data) == 44 and self.pair_corrupt_padding:
                    self.ram[address-t.BASE+63] = 1
            return
        return super().writemem(address, data)

    def dc_cvac(self, address, size):
        if address == t.HELPER_ADDR+0x240:
            assert not self.hw and size == 44 and self.pair_trace[-1] == 'write'
            self.pair_trace.append('clean')
            self.mutation()
            return
        return super().dc_cvac(address, size)

    def ic_ivau(self, address, size):
        if address == (t.HELPER_ADDR | 0xc0000000000)+0x240:
            assert not self.hw and size == 44 and self.pair_trace[-1] == 'clean'
            self.pair_trace.append('invalidate')
            self.pair_ready = self.mutation()
            return
        return super().ic_ivau(address, size)

    def call(self, address, *args):
        offset = address-(t.HELPER_ADDR | 0xc0000000000)
        if self.pair_calls and offset != 0x240:
            self.pair_after_calls.append((offset, args))
        assert offset != 352, '31N must not dispatch the legacy single-store leaf'
        if offset in (192, 224, 256, 288) and args:
            physical = args[0] & ~0xe0000000000
            if physical-t.HELPER_ADDR in (0x240, 0x268):
                assert not self.hw and self.tail_ready and len(args) == 1
                return 1 if self.pair_translation_bad else (
                    (physical & 0x000ffffffffff000) | (2 << 7) | (0xff << 56))
        if offset == 0x240:
            assert not args and not self.hw and self.pair_calls == 0 and self.pair_ready
            assert self.memory(t.HELPER_ADDR+0x240, 64) == PAIR_BYTES+bytes(20)
            self.pair_calls += 1
            self.pair_trace.append('dispatch')
            okay = self.mutation()
            if self.pair_fault == 'before_first':
                raise TimeoutError('PRIVATE pair before first')
            if okay:
                self.hw.append((0x280688004, 2))
            if self.pair_fault == 'between':
                raise TimeoutError('PRIVATE pair between stores')
            if okay:
                self.hw.append((0x280688008, 2))
            if self.pair_fault == 'after_second':
                raise TimeoutError('PRIVATE pair after second')
            if self.pair_fault == 'guard_after':
                self.put(0x110038, '<I', 1)
            if okay and self.arrival:
                self.enter()
            return 0 if self.pair_fault == 'bad_return' else 0x314e
        return super().call(address, *args)


class ControllerTests(unittest.TestCase):
    keep_patch = prior.RamTests.keep_patch

    def controller(self):
        self.keep_patch(patch.object(t, 'IMAGE', synthetic_image()))
        self.keep_patch(patch.object(t, 'Fake', Fake))
        self.keep_patch(patch.object(prior.c, 'Controller', j.Controller))
        self.keep_patch(patch.object(fixtures.previous.e.binding, 'read',
                                     return_value=dict(live_adt_bound=True)))
        for mod in (j, j.previous, j.previous.previous, j.previous.previous.previous):
            self.keep_patch(patch.object(mod, 'verify_recorder'))
        return prior.RamTests.high_controller(self)

    def timeout_campaign(self, ctl):
        with self.assertRaisesRegex(j.Refusal, '^cpu1_arrival_timeout$'):
            ctl.run()

    def test_consecutive_pair_acknowledges_both_only_after_clean_return(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        self.timeout_campaign(ctl)
        self.assertEqual(f.hw, [(0x280688004, 2), (0x280688008, 2)])
        self.assertEqual(f.pair_calls, 1)
        self.assertEqual(f.pair_trace, ['initialize', 'write', 'clean', 'invalidate', 'dispatch'])
        self.assertEqual(ctl.state['start_writes_attempted'], 2)
        self.assertEqual(ctl.state['start_writes_acknowledged'], 2)
        pair = ctl.state['start_pair']
        self.assertTrue(pair['intent_durable'])
        self.assertTrue(pair['diagnostics_verified'])
        self.assertEqual(pair['possible_completed_stores'], [2])
        self.assertFalse(pair['pair_atomic'])
        self.assertFalse(pair['completion_proves_cpu1_execution'])
        self.assertEqual(ctl.state['requests_completed'], 0)
        self.assertEqual(ctl.state['requests_planned'], 0)
        self.assertEqual(ctl.state['native_linux_smp'], 'NOT RUN')
        self.assertNotIn(str(t.HELPER_ADDR), json.dumps(journal))

    def test_three_actual_power_and_opaque_samples_no_fake_first_sample(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        self.timeout_campaign(ctl)
        for field in ('power_observation', 'cpu_state_observation'):
            report = ctl.state[field]
            self.assertEqual([row['phase'] for row in report['samples']],
                             ['before_start', 'after_second_start', 'final'])
            self.assertEqual(report['reads_attempted'], 6)
            self.assertEqual(report['reads_completed'], 6)
            self.assertEqual(report['omitted_phases'], ['after_first_start'])
            self.assertEqual(report['error'], None)
            self.assertTrue(all(row['complete'] for row in report['samples']))

    def test_pair_lost_reply_preserves_zero_one_or_two_uncertainty(self):
        for fault, count in (('before_first', 0), ('between', 1), ('after_second', 2)):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.pair_fault = fault
            with self.assertRaises(TimeoutError):
                ctl.run()
            self.assertEqual(len(f.hw), count)
            self.assertEqual(f.pair_calls, 1)
            self.assertEqual(f.pair_after_calls, [])
            self.assertEqual(ctl.state['start_writes_acknowledged'], 0)
            self.assertEqual(ctl.state['start_pair']['possible_completed_stores'], [0, 1, 2])
            self.assertFalse(ctl.state['start_pair']['reply_received'])
            self.assertNotIn('PRIVATE', json.dumps(ctl.state))
            self.assertEqual(len(ctl.state['power_observation']['samples']), 1)
            before = f.mutations
            with self.assertRaisesRegex(j.Refusal, 'already_used'):
                ctl.run()
            self.assertEqual(f.mutations, before)
            self.doCleanups()

    def test_bad_return_never_queries_after_unrecognized_reply(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        f.pair_fault = 'bad_return'
        with self.assertRaisesRegex(j.Refusal, '^start_pair_return_token$'):
            ctl.run()
        self.assertTrue(ctl.state['start_pair']['reply_received'])
        self.assertFalse(ctl.state['start_pair']['return_token_matched'])
        self.assertEqual(ctl.state['start_writes_acknowledged'], 0)
        self.assertEqual(f.pair_after_calls, [])

    def test_guard_fault_after_token_never_acknowledges_or_samples(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        f.pair_fault = 'guard_after'
        with self.assertRaisesRegex(j.Refusal, '^target_exception_or_guard$'):
            ctl.run()
        self.assertEqual(ctl.state['start_writes_acknowledged'], 0)
        self.assertEqual(ctl.state['start_pair']['possible_completed_stores'], [0, 1, 2])
        self.assertTrue(ctl.state['start_pair']['return_token_matched'])
        self.assertFalse(ctl.state['start_pair']['diagnostics_verified'])
        self.assertEqual(f.pair_after_calls, [(96, (t.BASE+0x110038,))])

    def test_pair_padding_and_publication_refusals_never_start(self):
        for flag in ('pair_translation_bad', 'pair_bad_readback', 'pair_corrupt_padding', 'occupied'):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            if flag == 'occupied':
                f.put(t.HELPER_ADDR-t.BASE+0x27f, '<B', 1)
                f.pair_drop_initialization = True
            else:
                setattr(f, flag, True)
            with self.assertRaises(j.Refusal):
                ctl.run()
            self.assertEqual(f.pair_calls, 0)
            self.assertEqual(f.hw, [])
            self.doCleanups()

    def test_owned_heap_reuse_is_initialized_before_leaf_publication(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        f.put(t.HELPER_ADDR-t.BASE+0x27f, '<B', 0x55)
        self.timeout_campaign(ctl)
        self.assertTrue(ctl.state['start_pair_publication']['owned_span_initialized'])
        self.assertEqual(f.memory(t.HELPER_ADDR+0x240, 64), PAIR_BYTES+bytes(20))

    def test_cached_and_maintained_positive_stop_after_pair_without_callbacks(self):
        for kind in ('vector', 'cold'):
            for maintained in (False, True):
                f, mem, ctl, journal = self.controller()
                f.arrival = False
                f.normal_kind = kind
                f.show_on_maintenance = maintained
                if not maintained:
                    f.normal_phase, f.normal_identity = 2, 0x40001
                with self.assertRaisesRegex(j.Refusal, '^paired_'+kind+'_prefix_observed$'):
                    ctl.run()
                self.assertEqual(len(f.hw), 2)
                self.assertEqual(f.pair_calls, 1)
                self.assertTrue(ctl.state['cpu1_prefix_identity_observed'])
                self.assertEqual(ctl.state['requests_completed'], 0)
                self.doCleanups()

    def test_device_arrival_also_stops_without_callback(self):
        f, mem, ctl, journal = self.controller()
        with self.assertRaisesRegex(j.Refusal, '^device_arrival_observed_stop_without_callbacks$'):
            ctl.run()
        self.assertEqual(f.pair_calls, 1)
        self.assertEqual(ctl.state['requests_completed'], 0)

    def test_pair_intent_journal_failure_dispatches_no_store(self):
        for fail_at in (1, 2):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            old, count = ctl.journal, [0]
            def fail(row):
                if row.get('start_pair', {}).get('result') == 'START_PAIR_INTENT':
                    count[0] += 1
                    if count[0] == fail_at:
                        raise OSError('PRIVATE intent journal')
                old(row)
            ctl.journal = fail
            with self.assertRaises(OSError):
                ctl.run()
            self.assertEqual(f.pair_calls, 0)
            self.assertEqual(ctl.state['start_writes_attempted'], 0)
            self.assertEqual(ctl.state['start_writes_acknowledged'], 0)
            self.assertFalse(ctl.state['start_pair']['dispatch_attempted'])
            self.assertEqual(ctl.state['start_pair']['possible_completed_stores'], [0])
            self.doCleanups()

    def test_completion_journal_failure_does_not_undo_ack_or_read_further(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        old = ctl.journal
        def fail(row):
            if row.get('start_pair', {}).get('result') == 'START_PAIR_COMPLETION_CONFIRMED':
                raise OSError('PRIVATE completion journal')
            old(row)
        ctl.journal = fail
        with self.assertRaises(OSError):
            ctl.run()
        self.assertEqual(ctl.state['start_writes_acknowledged'], 2)
        self.assertEqual(f.pair_after_calls, [(96, (t.BASE+0x110038,))])
        self.assertEqual(len(ctl.state['power_observation']['samples']), 1)

    def test_state_change_before_pair_refuses_and_retains_freshness_evidence(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        old = ctl.prepare_start_pair
        def changed():
            old()
            f.put(j.core.OFF['target'], '<I', 2)
        ctl.prepare_start_pair = changed
        with self.assertRaisesRegex(j.Refusal, '^state_changed_before_start_pair$'):
            ctl.run()
        self.assertEqual(f.pair_calls, 0)
        self.assertEqual(f.hw, [])

    def test_poststart_cached_and_maintained_read_faults_never_retry_pair(self):
        for at in range(1, 25):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.normal_post_read_fail = at
            with self.assertRaises(TimeoutError):
                ctl.run()
            self.assertEqual(f.normal_post_reads, at)
            self.assertEqual(f.pair_calls, 1)
            self.assertEqual(len(f.hw), 2)
            self.assertEqual(ctl.state['requests_completed'], 0)
            self.doCleanups()

    def test_power_and_opaque_read_failures_keep_actual_phase_prefix(self):
        for flag, field, counter in (
                ('ps_fail_at', 'power_observation', 'ps_read_count'),
                ('state_fail_at', 'cpu_state_observation', 'state_read_count'),
                ('state_trap_at', 'cpu_state_observation', 'state_read_count')):
            for at in range(1, 7):
                f, mem, ctl, journal = self.controller()
                f.arrival = False
                setattr(f, flag, at)
                with self.assertRaises((j.Refusal, TimeoutError)):
                    ctl.run()
                report = ctl.state[field]
                self.assertEqual(getattr(f, counter), at)
                self.assertEqual(report['reads_attempted'], at)
                self.assertEqual(report['reads_completed'], at-1)
                self.assertEqual([row['phase'] for row in report['samples']],
                                 list(j.PHASES[:(at+1)//2]))
                self.assertTrue(report['phase_adapter_failed'])
                self.assertEqual(f.pair_calls, int(at > 2))
                self.assertEqual(ctl.state['requests_completed'], 0)
                self.assertNotIn('PRIVATE', json.dumps(ctl.state))
                self.doCleanups()

    def test_all_mutation_prefix_failures_stop_without_cleanup(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        f.normal_phase, f.normal_identity = 2, 0x40001
        with self.assertRaises(j.Refusal):
            ctl.run()
        count = f.mutations
        self.doCleanups()
        for mode in ('fail_mutation', 'trap_mutation'):
            for at in range(1, count+1):
                f, mem, ctl, journal = self.controller()
                f.arrival = False
                setattr(f, mode, at)
                with self.assertRaises((j.Refusal, TimeoutError)):
                    ctl.run()
                self.assertEqual(f.mutations, at)
                self.assertLessEqual(f.pair_calls, 1)
                self.doCleanups()


class PhaseTests(unittest.TestCase):
    def test_actual_phase_order_has_six_reads_and_preserves_snapshot(self):
        tracker = j.ThreePhaseTracker(j.vector.ps_tracker.Tracker())
        rows, reads = [], []
        def read(cpu):
            reads.append(cpu)
            return 0xff
        for phase in j.PHASES:
            tracker.sample(phase, read, rows.append)
        self.assertEqual(reads, [0, 1]*3)
        self.assertEqual(rows[0]['samples'][0]['cpu0'], None)
        self.assertEqual([r['phase'] for r in tracker.report()['samples']], list(j.PHASES))
        with self.assertRaisesRegex(ValueError, 'phase_order'):
            tracker.sample('final', read, rows.append)
        self.assertEqual(len(reads), 6)

    def test_missing_intermediate_phase_is_rejected_before_any_read(self):
        tracker = j.ThreePhaseTracker(j.vector.ps_tracker.Tracker())
        tracker.sample('before_start', lambda _: 0, lambda _: None)
        with self.assertRaisesRegex(ValueError, 'phase_order'):
            tracker.sample('after_first_start', lambda _: self.fail('unexpected read'), lambda _: None)
        with self.assertRaises(ValueError):
            tracker.sample('after_second_start', lambda _: self.fail('retry after error'), lambda _: None)

    def test_journal_failure_freezes_phase_adapter_before_read(self):
        tracker = j.ThreePhaseTracker(j.vector.ps_tracker.Tracker())
        def fail(_):
            raise OSError('PRIVATE failed journal')
        with self.assertRaises(OSError):
            tracker.sample('before_start', lambda _: self.fail('read despite journal failure'), fail)
        self.assertTrue(tracker.failed)
        with self.assertRaises(ValueError):
            tracker.sample('before_start', lambda _: self.fail('read after error'), lambda _: None)

    def test_swallowed_reentrant_refusal_still_freezes_outer_sample(self):
        tracker = j.ThreePhaseTracker(j.vector.ps_tracker.Tracker())
        def reenter(_):
            try:
                tracker.sample('before_start', lambda _: self.fail('nested read'), lambda _: None)
            except ValueError:
                pass
        with self.assertRaises(j.Refusal):
            tracker.sample('before_start', lambda _: self.fail('outer read'), reenter)
        self.assertTrue(tracker.failed)
        self.assertEqual(tracker.report()['reads_completed'], 0)


if __name__ == '__main__':
    unittest.main()
