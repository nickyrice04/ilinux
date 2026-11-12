#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic serial controls for the generic-only sanitizer."""
import importlib.util
import json
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('check_vm',Path(__file__).with_name('check_vm.py'))
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)

def fixture():
    records=[{'scope':'GENERIC_VM_CONTROL','physical_m5_claim':False},
        {'phase':'PID1_ENTERED','monotonic_ns':1000000000},
        {'phase':'WORKERS_START','monotonic_ns':1100000000},
        {'phase':'cpu_online','value':'0-3'}]
    records += [{'phase':'cpu_worker','cpu':i,'actual_cpu':i,'iterations':1024,
        'elapsed_ns':250000000,'requested_sleep_ns':1000000,'observed_sleep_ns':1100000,'result':'PASS'} for i in range(4)]
    records += [{'phase':'cpu_workers','workers':4,'expected_native_workers':0,
        'common_interval_ns':240000000,'result':'PASS','performance_parity_measured':False},
        {'phase':'WORKERS_DONE','monotonic_ns':1400000000},
        {'phase':'memory_smoke','bytes':67108864,'read_ns':1000000,'checksum_ok':True,'result':'PASS','full_bandwidth_benchmark':False}]
    for second in range(60):
        if second%5==0:records.append(camera(second))
        records.append({'phase':'heartbeat','seconds':second,'monotonic_ns':1500000000+second*1000000000})
    records += [camera(60),{'phase':'COLLECTION_COMPLETE_NO_REBOOT','monotonic_ns':61500000000}]
    return records

def camera(second):return {'phase':'camera_summary','seconds':second,'cpu':'PASS','passed':4,'workers':4,
    'expected':0,'timers':'PASS','ram':'PASS','overlap_ns':240000000,'parity':False}
def parse(records,prefix=b''):return checker.inspect(prefix+b'\n'.join(json.dumps(r).encode() for r in records))
def phase(records,name):return next(r for r in records if r.get('phase')==name)

class VMControl(unittest.TestCase):
    def test_complete_generic_capture(self):self.assertEqual(parse(fixture())['status'],'PASS')
    def test_native_scope_rejected(self):
        r=fixture();r[0]['scope']='J716C_RAM_DIAGNOSTIC';self.assertEqual(parse(r)['status'],'FAIL')
    def test_selftest_is_not_a_kernel_boot(self):
        r=fixture();r[0]['scope']='GENERIC_LINUX_CONTROL';self.assertEqual(parse(r)['status'],'FAIL')
    def test_three_vcpus_rejected(self):
        r=fixture();phase(r,'cpu_online')['value']='0-2';self.assertEqual(parse(r)['status'],'FAIL')
    def test_duplicate_core_execution_rejected(self):
        r=fixture();phase(r,'cpu_worker')['actual_cpu']=1;self.assertEqual(parse(r)['status'],'FAIL')
    def test_worker_timeout_rejected(self):
        r=fixture();r.append({'phase':'cpu_worker_join','result':'TIMEOUT'});self.assertEqual(parse(r)['status'],'FAIL')
    def test_impossible_compute_overlap_rejected(self):
        r=fixture();phase(r,'cpu_workers')['common_interval_ns']=1000000000;self.assertEqual(parse(r)['status'],'FAIL')
    def test_fabricated_fast_heartbeat_counter_rejected(self):
        r=fixture()
        for x in r:
            if x.get('phase')=='heartbeat':x['monotonic_ns']=1500000000+x['seconds']
        self.assertEqual(parse(r)['status'],'FAIL')
    def test_timer_short_sleep_rejected(self):
        r=fixture();phase(r,'cpu_worker')['observed_sleep_ns']=1;self.assertEqual(parse(r)['status'],'FAIL')
    def test_memory_corruption_rejected(self):
        r=fixture();phase(r,'memory_smoke')['checksum_ok']=False;self.assertEqual(parse(r)['status'],'FAIL')
    def test_capture_under_one_minute_rejected(self):
        r=fixture();phase(r,'COLLECTION_COMPLETE_NO_REBOOT')['monotonic_ns']=2000000000;self.assertEqual(parse(r)['status'],'FAIL')
    def test_missing_final_camera_summary_rejected(self):
        r=[x for x in fixture() if not (x.get('phase')=='camera_summary' and x['seconds']==60)]
        self.assertEqual(parse(r)['status'],'FAIL')
    def test_failed_summary_rejected(self):
        r=fixture();phase(r,'camera_summary')['cpu']='FAIL';self.assertEqual(parse(r)['status'],'FAIL')
    def test_repeated_boot_capture_rejected(self):
        r=fixture();self.assertEqual(parse(r+r)['status'],'FAIL')
    def test_unknown_fields_and_serial_not_exported(self):
        r=fixture();r[0]['unknown_identifier']='SYNTHETIC_SECRET_SHOULD_NOT_APPEAR'
        out=parse(r,b'raw serial SYNTHETIC_SERIAL_SHOULD_NOT_APPEAR\n')
        self.assertEqual(out['status'],'PASS');self.assertNotIn('SYNTHETIC_',json.dumps(out))
    def test_partial_json_fails_without_echoing(self):
        out=parse(fixture(),b'{"scope":"SECRET_NO_ECHO"\n')
        self.assertEqual(out['status'],'FAIL');self.assertNotIn('SECRET_NO_ECHO',json.dumps(out))
    def test_unknown_fields_wrong_type_do_not_crash(self):
        r=fixture();r.append({'scope':[],'phase':[]});self.assertEqual(parse(r)['status'],'PASS')
    def test_oversize_input_rejected(self):
        self.assertEqual(checker.inspect(b'x'*(checker.MAX_INPUT+1))['status'],'FAIL')

if __name__=='__main__':unittest.main(verbosity=2)
