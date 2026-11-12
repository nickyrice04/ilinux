#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Sanitize and qualify this collector's generic four-vCPU VM serial result.

Usage: python3 -I check_vm.py PRIVATE_CONSOLE OUTPUT_JSON
Unknown serial lines and JSON fields never enter the output. This is not a
native Apple hardware, Aura, firmware, driver or performance-parity test.
"""
import io
import json
import sys
from pathlib import Path

MAX_INPUT=16*1024*1024
EXPECTED_CPUS={0,1,2,3}
PHASES={'PID1_ENTERED','WORKERS_START','WORKERS_DONE','WORKERS_FAILED',
        'cpu_online','cpu_worker','cpu_worker_join','cpu_workers','memory_smoke',
        'camera_summary','heartbeat','COLLECTION_COMPLETE_NO_REBOOT'}

def integer(value,minimum=0,maximum=(1<<64)-1):
    return type(value) is int and minimum<=value<=maximum

def cpulist(value):
    if type(value) is not str or not value or len(value)>256 or any(c not in '0123456789,-' for c in value):
        raise ValueError('bad CPU list')
    seen=set()
    for part in value.split(','):
        ends=part.split('-')
        if len(ends) not in (1,2) or any(not p for p in ends):raise ValueError('bad CPU list')
        low=int(ends[0]);high=int(ends[-1])
        if not 0<=low<=high<64:raise ValueError('bad CPU list')
        for cpu in range(low,high+1):
            if cpu in seen:raise ValueError('duplicate CPU')
            seen.add(cpu)
    return seen

def inspect(data):
    errors=[]
    def fail(code):
        if code not in errors:errors.append(code)
    records={p:[] for p in PHASES};scopes=[];own_count=0
    if len(data)>MAX_INPUT:
        fail('INPUT_SIZE_LIMIT')
    else:
        for raw in io.BytesIO(data):
            line=raw.strip(b'\r\n')
            if not line.startswith(b'{'):continue
            if len(line)>8192:fail('JSON_LINE_SIZE_LIMIT');continue
            try:r=json.loads(line)
            except (ValueError,UnicodeError):fail('MALFORMED_JSON_LINE');continue
            if type(r) is not dict:continue
            scope=r.get('scope');phase=r.get('phase')
            if scope in ('GENERIC_VM_CONTROL','GENERIC_LINUX_CONTROL','J716C_RAM_DIAGNOSTIC'):
                scopes.append(r)
            if r.get('result')=='REFUSED_WRONG_BOARD':fail('WRONG_BOARD_REFUSAL')
            if type(phase) is str and phase in PHASES:
                records[phase].append(r);own_count+=1
            if own_count>4096:fail('RECORD_COUNT_LIMIT');break
    if len(scopes)!=1 or scopes[0].get('scope')!='GENERIC_VM_CONTROL' or scopes[0].get('physical_m5_claim') is not False:
        fail('EXPLICIT_GENERIC_VM_SCOPE_REQUIRED')
    def singleton(phase):
        items=records[phase]
        if len(items)!=1:fail('MISSING_OR_DUPLICATE_'+phase.upper());return {}
        return items[0]
    start=singleton('PID1_ENTERED');begin=singleton('WORKERS_START')
    done=singleton('WORKERS_DONE');complete=singleton('COLLECTION_COMPLETE_NO_REBOOT')
    if records['WORKERS_FAILED'] or records['cpu_worker_join']:fail('WORKER_FAILURE_OR_TIMEOUT')
    times=[r.get('monotonic_ns') for r in (start,begin,done,complete)]
    elapsed=None
    if not all(integer(t) for t in times) or any(b<a for a,b in zip(times,times[1:])):
        fail('INVALID_PHASE_TIMESTAMPS')
    else:
        elapsed=times[-1]-times[0]
        if elapsed<60000000000:fail('LIVENESS_UNDER_60_SECONDS')
    online=singleton('cpu_online')
    try:
        if cpulist(online.get('value'))!=EXPECTED_CPUS:fail('ONLINE_VCPU_COUNT_OR_IDS')
    except (ValueError,TypeError):fail('INVALID_CPU_ONLINE_LIST')
    workers=records['cpu_worker'];seen=set();worker_times=[];timer_times=[]
    for r in workers:
        cpu=r.get('cpu');actual=r.get('actual_cpu');duration=r.get('elapsed_ns');timer=r.get('observed_sleep_ns')
        if not integer(cpu,0,63) or cpu not in EXPECTED_CPUS or cpu in seen or not integer(actual,0,63) or actual!=cpu:
            fail('WORKER_CPU_IDENTITY')
        if integer(cpu,0,63):seen.add(cpu)
        if r.get('result')!='PASS' or not integer(r.get('iterations'),1) or not integer(duration,250000000):
            fail('WORKER_RESULT_OR_DURATION')
        if r.get('requested_sleep_ns')!=1000000 or not integer(timer,1000000):fail('WORKER_TIMER_RESULT')
        if integer(duration):worker_times.append(duration)
        if integer(timer):timer_times.append(timer)
    if len(workers)!=4 or seen!=EXPECTED_CPUS:fail('FOUR_DISTINCT_PASSING_WORKERS_REQUIRED')
    summary=singleton('cpu_workers');overlap=summary.get('common_interval_ns')
    if summary.get('workers')!=4 or not integer(summary.get('expected_native_workers'),0,0) or summary.get('result')!='PASS' or summary.get('performance_parity_measured') is not False or not integer(overlap,1):
        fail('INVALID_GENERIC_WORKER_SUMMARY')
    if worker_times and integer(overlap) and overlap>min(worker_times):fail('IMPOSSIBLE_COMPUTE_OVERLAP')
    memory=singleton('memory_smoke')
    if memory.get('bytes')!=64*1024*1024 or memory.get('checksum_ok') is not True or memory.get('result')!='PASS' or memory.get('full_bandwidth_benchmark') is not False or not integer(memory.get('read_ns'),1):
        fail('MEMORY_CHECKSUM_CONTROL_REQUIRED')
    heartbeats=records['heartbeat'];seconds=[];heartbeat_times=[]
    for r in heartbeats:
        second=r.get('seconds');stamp=r.get('monotonic_ns')
        if not integer(second,0,59) or not integer(stamp):fail('INVALID_HEARTBEAT');continue
        seconds.append(second);heartbeat_times.append(stamp)
    if seconds!=list(range(60)):fail('COMPLETE_ORDERED_HEARTBEATS_REQUIRED')
    if any(b<=a for a,b in zip(heartbeat_times,heartbeat_times[1:])):fail('NONMONOTONIC_HEARTBEATS')
    if len(heartbeat_times)==60 and heartbeat_times[-1]-heartbeat_times[0]<59000000000:fail('HEARTBEAT_SPAN_UNDER_59_SECONDS')
    if heartbeat_times and all(integer(t) for t in (times[0],times[-1])):
        if heartbeat_times[0]<times[0] or heartbeat_times[-1]>times[-1]:fail('HEARTBEATS_OUTSIDE_PHASE_WINDOW')
    camera_seconds=[]
    for r in records['camera_summary']:
        second=r.get('seconds')
        if not integer(second,0,60):fail('INVALID_CAMERA_TIMESTAMP');continue
        camera_seconds.append(second)
        if r.get('cpu')!='PASS' or r.get('passed')!=4 or r.get('workers')!=4 or not integer(r.get('expected'),0,0) or r.get('timers')!='PASS' or r.get('ram')!='PASS' or r.get('parity') is not False or r.get('overlap_ns')!=overlap:
            fail('CAMERA_SUMMARY_NOT_PASS')
    if camera_seconds!=list(range(0,61,5)):fail('CAMERA_SUMMARIES_THROUGH_60_REQUIRED')
    return {'scope':'GENERIC_ARM64_VZ_CONTROL','status':'PASS' if not errors else 'FAIL',
        'expected_vcpus':4,'passing_cpu_ids':sorted(seen) if not errors else [],
        'worker_count':len(workers),'elapsed_monotonic_ns':elapsed,
        'complete_heartbeats':len(seconds)==60 and seconds==list(range(60)),
        'last_camera_second':max(camera_seconds) if camera_seconds else None,
        'memory_checksum_passed':memory.get('checksum_ok') is True and memory.get('result')=='PASS',
        'physical_m5_tested':False,'firmware_or_bootloader_tested':False,
        'native_driver_qualification':False,'performance_parity_measured':False,
        'raw_console_exported':False,'errors':errors}

def main():
    if len(sys.argv)!=3:raise SystemExit('Usage: check_vm.py PRIVATE_CONSOLE OUTPUT_JSON')
    source,target=map(Path,sys.argv[1:])
    if source.resolve()==target.resolve():raise SystemExit('Use a separate sanitized output path')
    try:
        with source.open('rb') as stream:data=stream.read(MAX_INPUT+1)
        report=inspect(data)
    except OSError:
        report={'scope':'GENERIC_ARM64_VZ_CONTROL','status':'FAIL','raw_console_exported':False,
                'physical_m5_tested':False,'errors':['INPUT_UNREADABLE']}
    target.write_text(json.dumps(report,indent=2)+'\n')
    return report['status']!='PASS'

if __name__=='__main__':raise SystemExit(main())
