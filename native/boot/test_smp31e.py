"""Full31E lifecycle/fault models. No USB/native execution or Apple artifacts."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import smp31e as e
import test_smp31d as previous
prior = previous.prior
t = prior.t


class Fake(previous.Fake):
    def __init__(self):
        super().__init__()
        self.permissions_bad = self.identity_writable = False
        self.alias_denied = self.corrupt_adjacent = False
        self.missing_recorder = False
        self.recorder_phase = 3
        self.code_trace = []
        self.return_el = 4
        self.hcr = 0x32488000038
        self.query_count = 0
        self.fail_query = None
        self.record_read_failure = None
        self.record_reads = 0
        self.tail_ready = False
        self.put(0x8fc, '<I', 0x528009e0)

    def memory(self, address, size):
        if address & 0xa0000000000 == 0xa0000000000:
            address &= ~0xa0000000000
        return super().memory(address, size)

    def writemem(self, address, data):
        if address == t.HELPER_ADDR + 192:
            assert data == e.HELPER_EXTENSION and not self.hw
            self.code_trace.append(('tail_write',))
            if self.mutation():
                self.ram[address-t.BASE:address-t.BASE+len(data)] = data
            return
        return super().writemem(address, data)

    def dc_cvau(self, address, size):
        if address == t.HELPER_ADDR + 192:
            assert size == 176 and not self.hw
            self.code_trace.append(('tail_clean',))
            self.mutation(); return
        return super().dc_cvau(address, size)

    def ic_ivau(self, address, size):
        if address == (t.HELPER_ADDR | 0xc0000000000) + 192:
            assert size == 176 and not self.hw
            self.code_trace.append(('tail_invalidate',))
            self.tail_ready = self.mutation(); return
        if address-t.BASE in (0xa00, 0x8fc):
            assert size == (204 if address-t.BASE == 0xa00 else 4) and not self.hw
            self.code_trace.append(('invalidate_code', address-t.BASE))
            self.mutation(); return
        return super().ic_ivau(address, size)

    def dc_cvac(self, address, size):
        if address & 0xa0000000000 == 0xa0000000000:
            offset = (address & ~0xa0000000000)-t.BASE
            assert (offset,size) in ((0xa00,204),(0x8fc,4)) and not self.hw
            self.code_trace.append(('clean_code',offset))
            self.mutation(); return
        return super().dc_cvac(address, size)

    def write32(self, address, value):
        if address & 0xa0000000000 == 0xa0000000000:
            offset = (address & ~0xa0000000000)-t.BASE
            assert not self.hw
            if offset == 0x8fc:
                assert self.code_trace[-1] == ('invalidate_code',0xa00)
                assert self.ram[0xa00:0xacc] == e.RECORDER
                assert value == 0x14000041
                self.code_trace.append(('hook',))
            else:
                assert 0xa00 <= offset < 0xacc and offset % 4 == 0
                assert value == struct.unpack_from('<I',e.RECORDER,offset-0xa00)[0]
                if offset == 0xa00: self.code_trace.append(('body',))
            if self.mutation() and not self.alias_denied:
                self.put(offset,'<I',value)
                if self.corrupt_adjacent: self.ram[0xad0] = 1
            return
        assert address not in (0x280688004,0x280688008), 'guarded hardware start forbidden'
        return super().write32(address,value)

    def call(self, address, *args):
        offset = address-(t.HELPER_ADDR | 0xc0000000000)
        if offset in (192,224,256,288,320):
            assert self.tail_ready and not self.hw
            self.query_count += 1
            if self.fail_query == self.query_count: raise TimeoutError('private transport data')
            if offset == 320:
                assert not args
                return self.hcr if self.return_el == 8 else 0
            assert len(args) == 1 and offset in ((192,224) if self.return_el == 4 else (256,288))
            va=args[0]; physical=va & ~0xa0000000000
            is_alias=va!=physical; is_write=offset in (224,288)
            assert physical-t.BASE in (0x8fc,0xa00,0xac8,0x90a40,0x90a78)
            if self.permissions_bad: return 1 | (4<<1)
            if is_write and not is_alias and physical-t.BASE < 0x1000 and not self.identity_writable:
                return 1 | (13<<1)
            return (physical & 0x000ffffffffff000) | (2<<7) | ((0xff if physical-t.BASE<0x1000 else 0)<<56)
        if offset == 352:
            assert args in ((0x280688004,2),(0x280688008,2))
            okay=self.mutation()
            self.hw.append(args)
            if okay and args[0]==0x280688008 and self.arrival:self.enter()
            return 0x31e if okay else 0
        if offset == 96 and args and t.BASE+0x90a40 <= args[0] < t.BASE+0x90a80:
            assert len(args) == 1 and args[0]%8 == 0
            self.record_reads += 1
            if self.record_read_failure == self.record_reads: raise TimeoutError('private target data')
            return self.read64(args[0])
        return super().call(address,*args)

    def enter(self):
        assert self.ram[0x8fc:0x900] == e.BRANCH
        assert self.ram[0xa00:0xacc] == e.RECORDER
        if not self.missing_recorder:
            self.put(0x90a40,'<4Q',self.recorder_phase,4,0x40001,0)
        if self.partial == 'mpidr':
            self.put(0x90020,'<Q',0x40001); return
        return super().enter()


class ControllerTests(unittest.TestCase):
    keep_patch = prior.RamTests.keep_patch
    def controller(self):
        image=bytearray(t.IMAGE); struct.pack_into('<I',image,0x8fc,0x528009e0)
        self.keep_patch(patch.object(t,'IMAGE',bytes(image)))
        self.keep_patch(patch.object(t,'Fake',Fake))
        self.keep_patch(patch.object(prior.c,'Controller',e.Controller))
        return prior.RamTests.high_controller(self)

    def test_success_scope_order_and_eight_requests(self):
        f,mem,ctl,j=self.controller(); result=ctl.run()
        self.assertEqual(result['result'],'CPU1_ENTRY_AND_REQUESTS_PASS')
        self.assertEqual(result['requests_completed'],8)
        self.assertEqual(result['mutation_requests'],80)
        self.assertTrue(result['park_verified'])
        self.assertTrue(result['recorder_observation']['complete'])
        self.assertEqual(result['recorder_observation']['exception_level'],1)
        self.assertEqual(f.hw,[(0x280688004,2),(0x280688008,2)])
        self.assertEqual(f.code_trace,[('tail_write',),('tail_clean',),('tail_invalidate',),
            ('body',),('clean_code',0xa00),('invalidate_code',0xa00),
            ('hook',),('clean_code',0x8fc),('invalidate_code',0x8fc)])
        self.assertEqual(result['linux_boot'],'NOT RUN')
        self.assertEqual(len(result['request_roundtrips_ms']),8)
        self.assertNotIn(str(t.BASE),json.dumps(result))
        self.assertNotIn('0x',json.dumps(result))

    def test_el2_vhe_uses_el2_queries(self):
        f,mem,ctl,j=self.controller();f.return_el=8
        self.assertEqual(ctl.run()['result'],'CPU1_ENTRY_AND_REQUESTS_PASS')

    def test_wrong_regime_or_permissions_never_publishes_code_or_starts(self):
        for field,value in [('return_el',12),('hcr',0),('permissions_bad',True),('identity_writable',True)]:
            with self.subTest(field=field):
                f,mem,ctl,j=self.controller();f.return_el=8;setattr(f,field,value)
                with self.assertRaises(e.Refusal): ctl.run()
                self.assertFalse(f.hw)
                self.assertNotIn(('body',),f.code_trace)
                self.doCleanups()

    def test_code_write_readback_failure_and_adjacent_corruption_no_start(self):
        for field in ('alias_denied','corrupt_adjacent'):
            f,mem,ctl,j=self.controller();setattr(f,field,True)
            with self.assertRaises(e.Refusal): ctl.run()
            self.assertFalse(f.hw)
            self.doCleanups()

    def test_all_mutation_faults_and_lost_acknowledgments_stop_without_retry(self):
        for mode in ('trap_mutation','fail_mutation'):
            for at in range(1,81):
                with self.subTest(mode=mode,at=at):
                    f,mem,ctl,j=self.controller();setattr(f,mode,at)
                    with self.assertRaises((e.Refusal,TimeoutError)): ctl.run()
                    self.assertEqual(ctl.state['mutation_requests'],at)
                    self.assertLessEqual(len(f.hw),2)
                    if at <= 70: self.assertFalse(f.hw)
                    before=list(f.writes)
                    with self.assertRaisesRegex(e.Refusal,'already_used'): ctl.run()
                    self.assertEqual(f.writes,before)
                    self.doCleanups()

    def test_every_applied_mutation_with_lost_reply_is_not_repeated(self):
        for at in range(1,81):
            with self.subTest(at=at):
                f,mem,ctl,j=self.controller()
                def wrap(operation):
                    def call(*args):
                        before=f.mutations
                        value=operation(*args)
                        if f.mutations==at and f.mutations>before:
                            raise TimeoutError('private lost acknowledgment after applied operation')
                        return value
                    return call
                for method in ('memalign','writemem','dc_cvau','ic_ivau','dc_cvac',
                               'write32','write64','smp_set_wfe_mode','call'):
                    setattr(f,method,wrap(getattr(f,method)))
                with self.assertRaises(TimeoutError):ctl.run()
                self.assertEqual(f.mutations,at)
                self.assertLessEqual(len(f.hw),2)
                self.assertEqual(ctl.state['mutation_requests'],at)
                if at<=70:self.assertFalse(f.hw)
                self.doCleanups()

    def test_every_permission_query_failure_stops_before_code_write(self):
        for at in range(1,18):
            f,mem,ctl,j=self.controller();f.fail_query=at
            with self.assertRaises(TimeoutError):ctl.run()
            self.assertEqual(f.query_count,at)
            self.assertNotIn(('body',),f.code_trace)
            self.assertFalse(f.hw)
            self.doCleanups()

    def test_early_entry_after_first_write_retains_record_and_stops(self):
        f,mem,ctl,j=self.controller();original=f.call
        def early(address,*args):
            value=original(address,*args)
            if address==(t.HELPER_ADDR | 0xc0000000000)+352 and args[0]==0x280688004:
                f.enter()
            return value
        f.call=early
        with self.assertRaisesRegex(e.Refusal,'cpu1_state_changed_before_second_start'):ctl.run()
        self.assertEqual(f.hw,[(0x280688004,2)])
        self.assertTrue(ctl.state['recorder_observation']['complete'])
        self.assertEqual(ctl.state['requests_completed'],0)

    def test_interrupt_preserves_partial_sampler_report(self):
        f,mem,ctl,j=self.controller();original=f.call
        def interrupted(address,*args):
            if address==(t.HELPER_ADDR | 0xc0000000000)+96 and args==(t.BASE+0x90a50,):
                raise KeyboardInterrupt()
            return original(address,*args)
        f.call=interrupted
        with self.assertRaises(KeyboardInterrupt):ctl.run()
        self.assertEqual(ctl.state['recorder_observation']['error'],'recorder_read_interrupted')
        self.assertEqual(ctl.state['recorder_observation']['reads_attempted'],2)
        self.assertEqual(ctl.state['recorder_observation']['highest_phase_seen'],3)
        self.assertEqual(ctl.state['requests_completed'],0)

    def test_timeout_retains_early_phases_and_mpidr_first_publication(self):
        for stage,phase in [('none',1),('none',2),('none',3),('mpidr',3),('reset',3),('spin',3)]:
            with self.subTest(stage=stage,phase=phase):
                f,mem,ctl,j=self.controller();f.partial=stage;f.recorder_phase=phase
                with self.assertRaisesRegex(e.Refusal,'cpu1_arrival_timeout'):ctl.run()
                self.assertEqual(ctl.state['recorder_observation']['highest_phase_seen'],phase)
                self.assertEqual(ctl.state['requests_completed'],0)
                self.assertLessEqual(ctl.clock(),3.1)
                if stage=='mpidr':self.assertEqual(ctl.state['entry_observation'],'mpidr_publication_seen')
                self.doCleanups()

    def test_no_record_is_not_success_or_proof_of_no_execution(self):
        f,mem,ctl,j=self.controller();f.partial='none';f.missing_recorder=True
        with self.assertRaisesRegex(e.Refusal,'cpu1_arrival_timeout'):ctl.run()
        self.assertEqual(ctl.state['recorder_observation']['state'],'no_recorder_publication_seen')
        self.assertEqual(ctl.state['requests_completed'],0)

    def test_arrival_without_instrumentation_never_requests(self):
        f,mem,ctl,j=self.controller();f.missing_recorder=True
        with self.assertRaisesRegex(e.Refusal,'arrival_without_complete_recorder'):ctl.run()
        self.assertTrue(ctl.state['cpu1_arrival_verified'])
        self.assertEqual(ctl.state['requests_completed'],0)

    def test_each_first_record_read_failure_retains_safe_progress(self):
        for at in range(1,6):
            f,mem,ctl,j=self.controller();f.record_read_failure=at
            with self.assertRaisesRegex(e.Refusal,'recorder_read_failed'):ctl.run()
            self.assertEqual(f.record_reads,at)
            self.assertEqual(ctl.state['recorder_observation']['reads_attempted'],at)
            self.assertEqual(ctl.state['requests_completed'],0)
            self.assertNotIn('private',json.dumps(ctl.state))
            self.doCleanups()

    def test_stalled_and_late_requests_never_repeat(self):
        f,mem,ctl,j=self.controller();f.complete=False
        with self.assertRaisesRegex(e.Refusal,'cpu1_request_timeout'):ctl.run()
        self.assertEqual(f.events,1)
        self.assertEqual(ctl.state['requests_completed'],0)

    def test_stale_timer_is_failure(self):
        f,mem,ctl,j=self.controller();f.stale_timer=True
        with self.assertRaisesRegex(e.Refusal,'counter_not_progressing'):ctl.run()
        self.assertEqual(ctl.state['requests_completed'],2)
        self.assertFalse(ctl.state['park_verified'])

    def test_once_receipt_and_previous_evidence_untouched(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(e,'ROOT',Path(tmp)):
            old=Path(tmp)/'build/native-intake/attempt31d/consumed.jsonl'
            old.parent.mkdir(parents=True);old.write_text('preserve')
            new=Path(tmp)/'build/native-intake/attempt31e/consumed.jsonl'
            stream,_=e.reserve(new);stream.close()
            with self.assertRaises(FileExistsError):e.reserve(new)
            self.assertEqual(old.read_text(),'preserve')


if __name__=='__main__':unittest.main()
