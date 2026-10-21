"""31D RAM-only console isolation, partial progress, and fault regressions."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31d as d
import test_smp31c as prior

BaseFake = prior.t.Fake


class Fake(BaseFake):
    def __init__(self):
        super().__init__()
        self.put(0x110030, '<Q', 0x288e28000)
        self.put(0x35a4a0, '<Q', 0x505200000)
        self.put(0x35a4a8, '<I', 4)
        self.published = set()
        self.trace = []
        self.partial = None
        self.ignore_zero = False

    def write64(self, address, value):
        offset = address - prior.t.BASE
        if offset not in (0x110030, 0x35a4a0):
            return super().write64(address, value)
        assert not self.hw and value == 0
        self.trace.append(('ram_zero', offset))
        if self.mutation() and not self.ignore_zero: self.put(offset, '<Q', 0)

    def dc_cvac(self, address, size):
        offset = address - prior.t.BASE
        assert not self.hw and offset in (0x110030, 0x35a4a0) and size == 8
        self.trace.append(('publish_zero', offset))
        if self.mutation():
            assert self.memory(address, size) == bytes(8) or self.ignore_zero
            self.published.add(offset)

    def write32(self, address, value):
        if address in (0x280688004, 0x280688008): self.trace.append(('start', address))
        return super().write32(address, value)

    def enter(self):
        # Source-backed failure model, NOT a claim this happened in 31C.
        if self.published != {0x110030, 0x35a4a0}: return
        if self.partial == 'none': return
        if self.partial == 'stack':
            self.put(0x90028, '<Q', prior.t.BASE + 0x178000); return
        if self.partial in ('reset', 'spin', 'bad'):
            self.put(0x90020, '<QQ', 0x40001, prior.t.BASE + 0x178000)
            if self.partial == 'spin': self.put(0x90250, '<Q', 0x40001)
            if self.partial == 'bad': self.put(0x90020, '<Q', 0x40002)
            return
        super().enter()


class ControllerTests(unittest.TestCase):
    keep_patch = prior.RamTests.keep_patch

    def controller(self, old=False):
        self.keep_patch(patch.object(prior.t, 'Fake', Fake))
        if not old: self.keep_patch(patch.object(prior.c, 'Controller', d.Controller))
        return prior.RamTests.high_controller(self)

    def test_control_model_times_out_without_console_change(self):
        f, mem, ctl, journal = self.controller(old=True)
        with self.assertRaisesRegex(d.Refusal, 'cpu1_arrival_timeout'): ctl.run()
        self.assertEqual(ctl.state['mutation_requests'], 9)
        self.assertEqual(ctl.state['start_writes_acknowledged'], 2)

    def test_complete_exact_scope_and_publication_order(self):
        f, mem, ctl, journal = self.controller()
        result = ctl.run()
        self.assertEqual(result['experiment'], 'smp31d')
        self.assertEqual(result['result'], 'CPU1_ENTRY_AND_REQUESTS_PASS')
        self.assertEqual(result['mutation_requests'], 15)
        self.assertEqual(result['requests_completed'], 2)
        self.assertEqual(result['entry_observation'], 'arrival_flag_seen')
        self.assertEqual(f.trace, [('ram_zero', 0x110030), ('publish_zero', 0x110030),
            ('ram_zero', 0x35a4a0), ('publish_zero', 0x35a4a0),
            ('start', 0x280688004), ('start', 0x280688008)])
        self.assertEqual(f.hw, [(0x280688004, 2), (0x280688008, 2)])
        self.assertNotIn(str(prior.t.BASE), json.dumps(result))
        self.assertEqual(ctl.state['linux_boot'], 'NOT RUN')

    def test_each_partial_progress_survives_timeout(self):
        for partial, expected in [('none','no_reset_record_seen'),
                ('stack','stack_publication_seen'), ('reset','reset_identity_seen'),
                ('spin','spin_identity_seen')]:
            with self.subTest(partial=partial):
                f, mem, ctl, journal = self.controller(); f.partial = partial
                with self.assertRaisesRegex(d.Refusal,'cpu1_arrival_timeout'): ctl.run()
                self.assertEqual(ctl.state['entry_observation'],expected)
                self.assertEqual(ctl.state['requests_completed'],0)
                self.assertFalse(ctl.state['cpu1_arrival_verified'])
                self.assertEqual(ctl.state['mutation_requests'],13)
                self.assertLessEqual(ctl.clock(),3.1)
                self.doCleanups()

    def test_wrong_partial_identity_stops_without_request(self):
        f, mem, ctl, journal = self.controller(); f.partial = 'bad'
        with self.assertRaisesRegex(d.Refusal,'cpu1_reset_record_changed'): ctl.run()
        self.assertEqual(ctl.state['entry_observation'],'unexpected_reset_record')
        self.assertEqual(ctl.state['requests_completed'],0)

    def test_non_usb_refused_before_allocation(self):
        for active in (0,1,2,3,12,0xffffffff):
            f, mem, ctl, journal = self.controller(); f.put(0x35a4a8,'<I',active)
            with self.assertRaisesRegex(d.Refusal,'proxy_not_direct_usb'): ctl.run()
            self.assertEqual(f.mutations,0)
            self.doCleanups()

    def test_unknown_bases_and_already_disabled_refuse_before_allocation(self):
        for bases, reason in [((1,0x505200000),'diagnostic_uart_base_mismatch'),
                              ((0,0),'diagnostic_uarts_already_disabled')]:
            f, mem, ctl, journal = self.controller()
            for offset, value in zip((0x110030,0x35a4a0),bases): f.put(offset,'<Q',value)
            with self.assertRaisesRegex(d.Refusal,reason): ctl.run()
            self.assertEqual(f.mutations,0)
            self.doCleanups()

    def test_one_uart_already_disabled_is_supported(self):
        f, mem, ctl, journal = self.controller(); f.put(0x110030,'<Q',0)
        result=ctl.run()
        self.assertEqual(result['diagnostic_uart_check']['enabled_count'],1)
        self.assertEqual(result['requests_completed'],2)

    def test_lost_zero_readback_prevents_start(self):
        f, mem, ctl, journal = self.controller(); f.ignore_zero=True
        with self.assertRaisesRegex(d.Refusal,'diagnostic_uart_readback'): ctl.run()
        self.assertEqual(f.hw,[])

    def test_every_mutation_fault_or_lost_reply_never_retries(self):
        for mode in ('trap_mutation','fail_mutation'):
            for at in range(1,16):
                with self.subTest(mode=mode,at=at):
                    f, mem, ctl, journal = self.controller(); setattr(f,mode,at)
                    with self.assertRaises((d.Refusal,TimeoutError)): ctl.run()
                    self.assertLessEqual(len(f.hw),2)
                    self.assertEqual(ctl.state['mutation_requests'],at)
                    with self.assertRaisesRegex(d.Refusal,'already_used'): ctl.run()
                    if at <= 11: self.assertEqual(f.hw,[])
                    self.doCleanups()

    def test_receipt_is_new_exclusive_namespace(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d,'ROOT',Path(tmp)):
            old=Path(tmp)/'build/native-intake/attempt31c/consumed.jsonl'
            old.parent.mkdir(parents=True);old.write_text('preserve')
            new=Path(tmp)/'build/native-intake/attempt31d/consumed.jsonl'
            stream,_=d.reserve(new);stream.close()
            with self.assertRaises(FileExistsError): d.reserve(new)
            self.assertEqual(old.read_text(),'preserve')
            self.assertEqual(json.loads(new.read_text())['experiment'],'smp31d')


if __name__ == '__main__': unittest.main()
