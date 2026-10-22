"""Original31M controller models; no Apple firmware emulation or native calls."""
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31m as j
import test_smp31l as frozen

t, prior, fixtures = frozen.t, frozen.prior, frozen.fixtures
synthetic_image = frozen.synthetic_image
SPANS = (0x1000, 0x1080, 0x1100)


class Fake(frozen.Fake):
    P_DC_CIVAC = 0x30a

    def __init__(self):
        super().__init__()
        self.return_el = 8
        self.ctr = (4 << 16) | (5 << 24)
        self.ctr_leaf_ready = False
        self.cache_trace = []
        self.civac_calls = 0
        self.post_civac_calls = 0
        self.fail_civac = None
        self.trap_civac = None
        self.bad_civac_return = False
        self.show_on_maintenance = False
        self.cache_translation_bad = False
        self.cache_control_corrupt = False
        self.cache_record_post_store = 0
        self.put(0x108188, '<Q', t.BASE+0x1012d0)

    def writemem(self, address, data):
        offset = address-t.HELPER_ADDR
        if offset == 0x220:
            assert not self.hw and data == struct.pack('<2I', 0xd53b0020, 0xd65f03c0)
            self.cache_trace.append(('ctr_store',))
            if self.mutation():
                self.ram[address-t.BASE:address-t.BASE+8] = data
            return
        if offset in SPANS and len(data) == 128:
            assert not self.hw and data == bytes(128)
            self.cache_trace.append(('granule_store', offset))
            if self.mutation():
                self.ram[address-t.BASE:address-t.BASE+128] = data
            return
        return super().writemem(address, data)

    def dc_cvau(self, address, size):
        if address == t.HELPER_ADDR+0x220:
            assert size == 8 and not self.hw
            self.cache_trace.append(('ctr_clean',))
            self.mutation()
            return
        return super().dc_cvau(address, size)

    def ic_ivau(self, address, size):
        if address == (t.HELPER_ADDR | 0xc0000000000)+0x220:
            assert size == 8 and not self.hw
            assert self.cache_trace[-1] == ('ctr_clean',)
            self.cache_trace.append(('ctr_invalidate',))
            self.ctr_leaf_ready = self.mutation()
            return
        return super().ic_ivau(address, size)

    def dc_cvac(self, address, size):
        if address-t.HELPER_ADDR in SPANS and size == 128:
            assert not self.hw
            self.cache_trace.append(('granule_clean', address-t.HELPER_ADDR))
            self.mutation()
            return
        return super().dc_cvac(address, size)

    def request(self, opcode, address, size):
        assert opcode == 0x30a and type(size) is int and size == 64
        assert address-t.HELPER_ADDR in SPANS
        if self.hw:
            assert address-t.HELPER_ADDR in SPANS[:2]
            self.post_civac_calls += 1
        self.civac_calls += 1
        self.cache_trace.append(('civac', address-t.HELPER_ADDR, len(self.hw)))
        okay = self.mutation()
        if self.civac_calls == self.trap_civac:
            self.put(0x110038, '<I', 1)
        if self.civac_calls == self.fail_civac:
            raise TimeoutError('PRIVATE maintenance transport detail')
        target = t.HELPER_ADDR + (0x1000 if self.normal_kind == 'vector' else 0x1080)
        if self.hw and self.show_on_maintenance and address == target:
            self.normal_phase, self.normal_identity = 2, 0x40001
        if self.cache_control_corrupt and not self.hw:
            self.put(t.HELPER_ADDR-t.BASE+0x1178, '<Q', 1)
        return 1 if self.bad_civac_return else 0

    def call(self, address, *args):
        offset = address-(t.HELPER_ADDR | 0xc0000000000)
        if offset == 0x220:
            assert not self.hw and not args and self.ctr_leaf_ready
            assert self.memory(t.HELPER_ADDR+0x220, 8) == struct.pack('<2I', 0xd53b0020, 0xd65f03c0)
            return self.ctr
        if offset in (192, 224, 256, 288) and args:
            physical = args[0] & ~0xe0000000000
            owned = physical-t.HELPER_ADDR
            if owned == 0x220 or any(owned in (base, base+120) for base in SPANS):
                assert not self.hw and self.tail_ready
                if self.cache_translation_bad:
                    return 1
                return (physical & 0x000ffffffffff000) | (2 << 7) | (0xff << 56)
        if offset == 0x200 and args and args[0] == t.HELPER_ADDR+0x1120 and args[1] == j.CONTROL_MARKER:
            assert not self.hw and len(args) == 2
            if self.mutation():
                self.put(args[0]-t.BASE, '<Q', args[1])
            return 0x314b
        if offset == 96 and args and any(t.HELPER_ADDR+base+64 <= args[0] < t.HELPER_ADDR+base+128 for base in SPANS):
            assert not self.hw and len(args) == 1 and args[0] % 8 == 0
            return self.read64(args[0])
        return super().call(address, *args)


class ControllerTests(unittest.TestCase):
    keep_patch = prior.RamTests.keep_patch

    def controller(self):
        self.keep_patch(patch.object(t, 'IMAGE', synthetic_image()))
        self.keep_patch(patch.object(t, 'Fake', Fake))
        self.keep_patch(patch.object(prior.c, 'Controller', j.Controller))
        self.keep_patch(patch.object(fixtures.previous.e.binding, 'read', return_value=dict(live_adt_bound=True)))
        self.keep_patch(patch.object(j, 'verify_recorder'))
        self.keep_patch(patch.object(j.previous, 'verify_recorder'))
        self.keep_patch(patch.object(j.previous.previous, 'verify_recorder'))
        return prior.RamTests.high_controller(self)

    def test_zero_campaign_retains_starts_but_corrects_planned_requests(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        with self.assertRaisesRegex(j.Refusal, '^cpu1_arrival_timeout$'):
            ctl.run()
        self.assertEqual(f.hw, [(0x280688004, 2), (0x280688008, 2)])
        self.assertEqual(ctl.state['requests_planned'], 0)
        self.assertEqual(ctl.state['requests_completed'], 0)
        self.assertEqual(ctl.state['cpu0_cache_control']['result'], 'CPU0_CACHE_CONTROL_PASS')
        self.assertEqual(ctl.state['cpu0_cache_control']['reads_completed'], 48)
        self.assertEqual(ctl.state['cpu0_cache_control']['stores_acknowledged'], 2)
        self.assertEqual(ctl.state['cpu0_cache_control']['maintenance_acknowledged'], 2)
        self.assertFalse(ctl.state['cpu1_prefix_identity_observed'])
        self.assertEqual(ctl.state['cache_visibility_cause'], 'UNKNOWN')
        self.assertGreater(f.post_civac_calls, 0)
        self.assertEqual(ctl.state['cache_maintenance_acknowledged'], f.civac_calls)
        self.assertNotIn(str(t.HELPER_ADDR), json.dumps(journal))

    def test_cached_positive_skips_poststart_maintenance(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        f.normal_phase, f.normal_identity, f.normal_after_starts = 2, 0x40001, 1
        with self.assertRaisesRegex(j.Refusal, '^paired_vector_prefix_observed$'):
            ctl.run()
        self.assertEqual(len(f.hw), 1)
        self.assertEqual(f.post_civac_calls, 0)
        self.assertTrue(ctl.state['cpu1_prefix_identity_observed'])
        self.assertEqual(ctl.state['requests_completed'], 0)

    def test_maintained_positive_stops_at_first_identity(self):
        for kind in ('vector', 'cold'):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.normal_kind, f.normal_after_starts = kind, 1
            f.show_on_maintenance = True
            with self.assertRaisesRegex(j.Refusal, '^paired_'+kind+'_prefix_observed$'):
                ctl.run()
            self.assertEqual(len(f.hw), 1)
            self.assertTrue(ctl.state['cpu1_prefix_identity_observed'])
            self.assertEqual(ctl.state['paired_observation'][kind]['observation_channel'], 'maintained')
            self.assertEqual(ctl.state['requests_completed'], 0)
            self.assertEqual(ctl.state['cache_visibility_cause'], 'UNKNOWN')
            self.doCleanups()

    def test_unsupported_ctr_refuses_before_start_or_civac(self):
        for ctr in (0, 4 << 16, (4 << 16)|(6 << 24), (5 << 16)|(4 << 24), True):
            f, mem, ctl, journal = self.controller()
            f.ctr = ctr
            with self.assertRaises(j.Refusal):
                ctl.run()
            self.assertEqual(f.hw, [])
            self.assertEqual(f.civac_calls, 0)
            self.doCleanups()

    def test_indirections_refuse_before_mutation(self):
        for at, fmt, value in ((0x108188, '<Q', t.BASE+0x1012d8), (0x80fb4, '<H', 1)):
            f, mem, ctl, journal = self.controller()
            f.put(at, fmt, value)
            with self.assertRaises(j.Refusal):
                ctl.run()
            self.assertEqual(f.mutations, 0)
            self.assertEqual(f.hw, [])
            self.doCleanups()

    def test_cpu0_el1_refuses_maintenance_without_changing_regime(self):
        f, mem, ctl, journal = self.controller()
        f.return_el = 4
        with self.assertRaisesRegex(j.Refusal, '^maintenance_requires_cpu0_el2$'):
            ctl.run()
        self.assertEqual(f.hw, [])
        self.assertEqual(f.civac_calls, 0)

    def test_full_granule_mapping_and_canary_fault_prevent_start(self):
        for flag in ('cache_translation_bad', 'cache_control_corrupt'):
            f, mem, ctl, journal = self.controller()
            setattr(f, flag, True)
            with self.assertRaises(j.Refusal):
                ctl.run()
            self.assertEqual(f.hw, [])
            self.doCleanups()

    def test_control_maintenance_failure_never_starts(self):
        for at in (1, 2):
            f, mem, ctl, journal = self.controller()
            f.fail_civac = at
            with self.assertRaises(TimeoutError):
                ctl.run()
            self.assertEqual(f.civac_calls, at)
            self.assertEqual(f.hw, [])
            self.assertEqual(ctl.state['cpu0_cache_control']['result'], 'STOP')
            self.doCleanups()

    def test_poststart_maintenance_failure_preserves_exact_prefix(self):
        for at in range(3, 11):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.fail_civac = at
            with self.assertRaises(TimeoutError):
                ctl.run()
            self.assertEqual(f.civac_calls, at)
            self.assertEqual(len(f.hw), 1 if at <= 6 else 2)
            self.assertEqual(ctl.state['cache_maintenance_acknowledged'], at-1)
            self.assertEqual(ctl.state['requests_completed'], 0)
            self.assertNotIn('PRIVATE', json.dumps(ctl.state))
            self.doCleanups()

    def test_poststart_maintenance_fault_never_acknowledges_or_continues(self):
        for at in range(3, 11):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.trap_civac = at
            with self.assertRaisesRegex(j.Refusal, '^target_exception_or_guard$'):
                ctl.run()
            self.assertEqual(f.civac_calls, at)
            self.assertEqual(len(f.hw), 1 if at <= 6 else 2)
            self.assertEqual(ctl.state['cache_maintenance_acknowledged'], at-1)
            self.doCleanups()

    def test_every_cached_or_maintained_read_failure_stops_at_exact_prefix(self):
        for at in range(1, 49):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.normal_post_read_fail = at
            with self.assertRaises(TimeoutError):
                ctl.run()
            self.assertEqual(f.normal_post_reads, at)
            self.assertEqual(len(f.hw), 1 if at <= 24 else 2)
            self.assertEqual(ctl.state['requests_completed'], 0)
            self.assertNotIn('PRIVATE', json.dumps(ctl.state))
            self.doCleanups()

    def test_partial_and_wrong_identity_never_become_cpu1_proof(self):
        for phase, identity in ((1, 0), (0, 0x40001), (2, 0x40000), (3, 0x40001)):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.normal_phase, f.normal_identity, f.normal_after_starts = phase, identity, 1
            with self.assertRaises(j.Refusal):
                ctl.run()
            self.assertFalse(ctl.state['cpu1_prefix_identity_observed'])
            self.assertEqual(f.post_civac_calls, 0)
            self.assertEqual(ctl.state['requests_completed'], 0)
            self.doCleanups()

    def test_maintenance_return_must_be_exact_zero(self):
        f, mem, ctl, journal = self.controller()
        f.bad_civac_return = True
        with self.assertRaisesRegex(j.Refusal, '^cache_maintenance_return$'):
            ctl.run()
        self.assertEqual(f.hw, [])
        self.assertEqual(f.civac_calls, 1)

    def test_device_arrival_still_stops_without_callback(self):
        f, mem, ctl, journal = self.controller()
        with self.assertRaisesRegex(j.Refusal, '^device_arrival_observed_stop_without_callbacks$'):
            ctl.run()
        self.assertEqual(ctl.state['requests_completed'], 0)

    def test_cache_intent_journal_failure_dispatches_no_maintenance(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        original = ctl.journal
        def journal_fail(state):
            if state.get('cache_maintenance_intents') == 3:
                raise OSError('PRIVATE journal failure')
            original(state)
        ctl.journal = journal_fail
        with self.assertRaises(OSError):
            ctl.run()
        self.assertEqual(f.civac_calls, 2)
        self.assertEqual(len(f.hw), 1)
        self.assertEqual(ctl.state['cache_maintenance_attempted'], 2)
        self.assertNotIn('PRIVATE', json.dumps(ctl.state))

    def test_cache_control_deadline_prevents_starts(self):
        f, mem, ctl, journal = self.controller()
        old_clock = ctl.clock
        ticks = [0]
        def clock():
            if ctl.state['phase'] == 'cpu0_cache_control':
                ticks[0] += 1
                return ticks[0]
            return old_clock()
        ctl.clock = clock
        with self.assertRaisesRegex(j.Refusal, '^cache_control_deadline$'):
            ctl.run()
        self.assertEqual(f.hw, [])
        self.assertEqual(f.civac_calls, 0)

    def test_slow_control_journal_cannot_dispatch_past_deadline(self):
        # Delay after each path's last local journal, including the separate
        # mutation journal, not only at the top of the control method.
        for field, occurrence in (('reads_attempted', 1), ('stores_attempted', 2),
                                  ('maintenance_attempted', 3)):
            f, mem, ctl, journal = self.controller()
            lag, seen = [0], [0]
            old_clock, old_journal = ctl.clock, ctl.journal
            ctl.clock = lambda: old_clock()+lag[0]
            def delayed(state):
                report = state.get('cpu0_cache_control', {})
                if state['phase'] == 'cpu0_cache_control' and report.get(field) == 1:
                    seen[0] += 1
                    if seen[0] == occurrence:
                        lag[0] = 3
                old_journal(state)
            ctl.journal = delayed
            with self.assertRaisesRegex(j.Refusal, '^cache_control_deadline$'):
                ctl.run()
            self.assertEqual(f.hw, [])
            self.assertEqual(f.civac_calls, 0)
            if field == 'reads_attempted':
                self.assertEqual(ctl.state['cpu0_cache_control']['reads_completed'], 0)
            if field == 'stores_attempted':
                self.assertEqual(ctl.state['cpu0_cache_control']['stores_acknowledged'], 0)
            self.doCleanups()

    def test_mutation_faults_have_no_cleanup_or_retries(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        f.normal_phase, f.normal_identity, f.normal_after_starts = 2, 0x40001, 1
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
                self.doCleanups()


if __name__ == '__main__':
    unittest.main()
