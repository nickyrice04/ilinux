"""Original synthetic controller integration; not Apple firmware emulation."""
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31l as j
import test_smp31k as frozen

t, prior, fixtures = frozen.t, frozen.prior, frozen.fixtures
synthetic_image = frozen.synthetic_image
MARKER = 0x314c435055304f4b
SPANS = (0x1000, 0x1080, 0x1100)


def literal_prefix(kind):
    address = t.HELPER_ADDR + (0x1000 if kind == 'vector' else 0x1080)
    code, target = (0xc00, 0xa00) if kind == 'vector' else (0xd00, 0xb00)
    words = [0xd2800008 | ((address & 65535) << 5)]
    words += [0xf2800008 | (half << 21) | (((address >> (16*half)) & 65535) << 5)
              for half in (1, 2, 3)]
    words += [0xd2800029, 0xf9000109, 0xd5033f9f, 0xd53800a9, 0xd3405d29,
              0xf9000509, 0xd5033f9f, 0xd2800049, 0xf9000109, 0xd5033f9f,
              0x14000000 | (((target-code-56)//4) & 0x3ffffff)]
    return struct.pack('<15I', *words)


class Fake(frozen.Fake):
    def __init__(self):
        super().__init__()
        self.normal_phase = 0
        self.normal_identity = 0
        self.normal_kind = 'vector'
        self.normal_after_starts = 2
        self.normal_reads = 0
        self.normal_read_fail = None
        self.normal_post_read_fail = None
        self.normal_post_reads = 0
        self.normal_bad_translation = False
        self.normal_drop_marker = False
        self.normal_armed = False
        self.normal_trace = []

    def enter(self):
        # Inject a Device-only visible arrival. This deliberately does not
        # emulate CPU1 attributes; the independent instruction model does.
        assert self.ram[:4] == struct.pack('<I', 0x14000300)
        original = bytes(self.ram[:4])
        self.ram[:4] = j.vector.BRANCH
        try:
            return super().enter()
        finally:
            self.ram[:4] = original

    def writemem(self, address, data):
        if address-t.HELPER_ADDR in SPANS:
            assert not self.hw and data == bytes(64)
            if self.mutation():
                self.ram[address-t.BASE:address-t.BASE+64] = data
            return
        return super().writemem(address, data)

    def write32(self, address, value):
        rel = (address & ~0xa0000000000)-t.BASE
        if (0xc00 <= rel < 0xc3c or 0xd00 <= rel < 0xd3c or
                (rel, value) in ((0, 0x14000300), (0x800, 0x14000140))):
            assert address & 0xa0000000000 == 0xa0000000000 and not self.hw
            if rel in (0, 0x800):
                code = 0xc00 if rel == 0 else 0xd00
                kind = 'vector' if rel == 0 else 'cold'
                assert self.memory(t.BASE+code, 60) == literal_prefix(kind)
                assert self.normal_trace[-1] == ('invalidate', code)
            else:
                kind, code = ('vector', 0xc00) if rel < 0xd00 else ('cold', 0xd00)
                assert value == struct.unpack_from('<I', literal_prefix(kind), rel-code)[0]
            self.normal_trace.append(('store', rel))
            if self.mutation():
                self.put(rel, '<I', value)
            return
        return super().write32(address, value)

    def dc_cvac(self, address, size):
        if address-t.HELPER_ADDR in SPANS:
            assert not self.hw and size == 64
            self.mutation()
            return
        rel = (address & ~0xa0000000000)-t.BASE
        if rel in (0xc00, 0xd00) or (rel in (0, 0x800) and self.normal_trace):
            assert not self.hw and size == (60 if rel in (0xc00, 0xd00) else 4)
            self.normal_trace.append(('clean', rel))
            self.mutation()
            return
        return super().dc_cvac(address, size)

    def ic_ivau(self, address, size):
        rel = address-t.BASE
        if rel in (0xc00, 0xd00) or (rel in (0, 0x800) and self.normal_trace):
            assert not self.hw and size == (60 if rel in (0xc00, 0xd00) else 4)
            self.normal_trace.append(('invalidate', rel))
            if self.mutation() and rel == 0x800:
                self.normal_armed = True
            return
        return super().ic_ivau(address, size)

    def call(self, address, *args):
        off = address-(t.HELPER_ADDR | 0xc0000000000)
        if off in (192, 224, 256, 288) and args:
            physical = args[0] & ~0xe0000000000
            rel, allocated = physical-t.BASE, physical-t.HELPER_ADDR
            if (rel in (0xc00, 0xc38, 0xd00, 0xd38) or
                    any(allocated in (base, base+56) for base in SPANS)):
                assert not self.hw and self.tail_ready and len(args) == 1
                if self.normal_bad_translation:
                    return 1
                return (physical & 0x000ffffffffff000) | (2 << 7) | (0xff << 56)
        if off == 512 and args and args[0] == t.HELPER_ADDR+0x1120:
            assert not self.hw and len(args) == 2 and args[1] in (0, MARKER)
            if self.mutation() and not (self.normal_drop_marker and args[1]):
                self.put(args[0]-t.BASE, '<Q', args[1])
            return 0x314b
        if off == 96 and args and any(t.HELPER_ADDR+base <= args[0] < t.HELPER_ADDR+base+64 for base in SPANS):
            assert len(args) == 1 and args[0] % 8 == 0
            assert args[0] < t.HELPER_ADDR+0x1100 or not self.hw
            self.normal_reads += 1
            if self.hw:
                self.normal_post_reads += 1
                if self.normal_post_reads == self.normal_post_read_fail:
                    raise TimeoutError('PRIVATE_SYNTHETIC normal post-start read')
            if self.normal_reads == self.normal_read_fail:
                raise TimeoutError('PRIVATE_SYNTHETIC normal read')
            if self.normal_armed and len(self.hw) >= self.normal_after_starts:
                target = t.HELPER_ADDR + (0x1000 if self.normal_kind == 'vector' else 0x1080)
                self.put(target-t.BASE, '<QQ', self.normal_phase, self.normal_identity)
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
        return prior.RamTests.high_controller(self)

    def test_zero_channels_remain_unknown_and_preserve_start_commands(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        with self.assertRaisesRegex(j.Refusal, '^cpu1_arrival_timeout$'):
            ctl.run()
        self.assertEqual(f.hw, [(0x280688004, 2), (0x280688008, 2)])
        self.assertEqual(ctl.state['cpu0_normal_control']['result'], 'CPU0_NORMAL_CONTROL_PASS')
        self.assertFalse(ctl.state['cpu1_prefix_identity_observed'])
        self.assertEqual(ctl.state['requests_completed'], 0)
        self.assertTrue(ctl.state['normal_publication']['whole_text_verified'])
        self.assertNotIn(str(t.HELPER_ADDR), json.dumps(journal))

    def test_normal_identity_stops_without_callbacks(self):
        for kind in ('vector', 'cold'):
            for starts in (1, 2):
                f, mem, ctl, journal = self.controller()
                f.arrival = False
                f.normal_phase, f.normal_identity = 2, 0x40001
                f.normal_kind, f.normal_after_starts = kind, starts
                with self.assertRaisesRegex(j.Refusal, '^normal_'+kind+'_prefix_observed$'):
                    ctl.run()
                self.assertEqual(len(f.hw), starts)
                self.assertTrue(ctl.state['cpu1_prefix_identity_observed'])
                self.assertEqual(ctl.state['requests_completed'], 0)
                self.assertEqual(ctl.state['device_visibility_cause'], 'UNKNOWN')
                self.doCleanups()

    def test_partial_and_wrong_identity_never_become_cpu1_proof(self):
        for phase, identity in ((1, 0), (0, 0x40001), (2, 0x40000)):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.normal_phase, f.normal_identity = phase, identity
            with self.assertRaises((j.Refusal, ValueError)):
                ctl.run()
            self.assertFalse(ctl.state['cpu1_prefix_identity_observed'])
            self.assertEqual(ctl.state['requests_completed'], 0)
            self.doCleanups()

    def test_normal_mapping_or_control_failure_prevents_starts(self):
        for flag in ('normal_bad_translation', 'normal_drop_marker'):
            f, mem, ctl, journal = self.controller()
            setattr(f, flag, True)
            with self.assertRaises(j.Refusal):
                ctl.run()
            self.assertEqual(f.hw, [])
            self.assertFalse(ctl.state['normal_entry_armed'])
            self.doCleanups()

    def test_normal_padding_freshness_prevents_mutation(self):
        for code in (0xc00, 0xd00):
            f, mem, ctl, journal = self.controller()
            f.put(code, '<I', 1)
            with self.assertRaises((j.Refusal, j.core.census.CensusRefusal)):
                ctl.run()
            self.assertEqual(f.mutations, 0)
            self.doCleanups()

    def test_existing_complete_arrival_stops_before_callbacks(self):
        f, mem, ctl, journal = self.controller()
        with self.assertRaisesRegex(j.Refusal, '^device_arrival_observed_stop_without_callbacks$'):
            ctl.run()
        self.assertEqual(ctl.state['requests_completed'], 0)

    def test_post_start_read_failure_stops_at_exact_prefix(self):
        for at in range(1, 7):
            f, mem, ctl, journal = self.controller()
            f.arrival = False
            f.normal_post_read_fail = at
            with self.assertRaises(TimeoutError):
                ctl.run()
            self.assertEqual(f.normal_post_reads, at)
            self.assertEqual(len(f.hw), 1)
            self.assertEqual(ctl.state['requests_completed'], 0)
            self.doCleanups()

    def test_new_mutation_faults_stop_without_cleanup(self):
        f, mem, ctl, journal = self.controller()
        f.arrival = False
        with self.assertRaises(j.Refusal):
            ctl.run()
        last = f.mutations-2
        self.doCleanups()
        for mode in ('fail_mutation', 'trap_mutation'):
            for at in range(94, last+1):
                f, mem, ctl, journal = self.controller()
                setattr(f, mode, at)
                with self.assertRaises((j.Refusal, TimeoutError)):
                    ctl.run()
                self.assertEqual(f.mutations, at)
                self.assertEqual(f.hw, [])
                self.doCleanups()


if __name__ == '__main__':
    unittest.main()
