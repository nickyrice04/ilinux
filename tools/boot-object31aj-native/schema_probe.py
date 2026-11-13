#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""M5-only read-only metadata-presence probe. Default is help; no values or IDs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import time
import types
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
PIN='0728fae7dd30fd2ef14dacdf9e25028614f239c254c8fc40c3f8866fde32dc47'
FIELDS={'auxp','auxi','auxr','rpnh','ronh','prot','hrlp','losv','spih','stng'}
STAGES={'LOCAL_ROOT','HELPER','HARDWARE','VOLUME_METADATA','ORIGINAL_VOLUME','TARGET_GUARD','LAB_POLICY','ORIGINAL_POLICY'}
stage='LOCAL_ROOT'
failure_kind='GUARD'
failure_reason='GUARD_REFUSED'
partial_roles={}
policy_diagnostic=None
READ_REASONS={'BPUTIL_EXEC_FAILURE','BPUTIL_TIMEOUT','BPUTIL_EXIT_NONZERO',
              'BPUTIL_STDOUT_EMPTY','BPUTIL_STDOUT_LIMIT','BPUTIL_CAPTURE_FAILURE',
              'BPUTIL_INTERRUPTED'}
FORMAT_REASONS={'INVALID_POLICY_BYTES','POLICY_NUL','NO_KNOWN_METADATA_ROWS',
                'MALFORMED_METADATA_ROWS','EMPTY_METADATA_ROWS',
                'DUPLICATE_METADATA_ROWS','CONFLICTING_METADATA_PRESENCE'}

class ProbeFailure(ValueError):pass

def fail(kind,reason):
    global failure_kind,failure_reason
    if (kind=='READ' and reason in READ_REASONS) or (kind=='FORMAT' and reason in FORMAT_REASONS):
        failure_kind,failure_reason=kind,reason
    else:failure_kind,failure_reason='GUARD','GUARD_REFUSED'
    raise ProbeFailure()

def summarize(raw):
    if type(raw) is not bytes or not 0<len(raw)<=65536:fail('FORMAT','INVALID_POLICY_BYTES')
    if b'\0' in raw:fail('FORMAT','POLICY_NUL')
    rows={};malformed=set()
    for line in raw.splitlines():
        match=re.search(rb'\(([A-Za-z0-9]{4})\)\s*:\s*([^\r\n]*)$',line)
        if match and match[1].decode('ascii') in FIELDS:
            key=match[1].decode('ascii')
            value=match[2].strip()
            presence='EMPTY' if not value else 'ABSENT' if value.lower()==b'absent' else 'PRESENT'
            rows.setdefault(key,[]).append(presence)
        else:
            for tag in re.findall(rb'\(([A-Za-z0-9]{4})\)',line):
                key=tag.decode('ascii')
                if key in FIELDS:malformed.add(key)
    states={key:set(values) for key,values in rows.items()}
    duplicates=sorted(key for key,values in rows.items() if len(values)>1)
    conflicting=sorted(key for key,values in states.items() if 'PRESENT' in values and 'ABSENT' in values)
    empty=sorted(key for key,values in states.items() if 'EMPTY' in values)
    reason=('CONFLICTING_METADATA_PRESENCE' if conflicting else
            'MALFORMED_METADATA_ROWS' if malformed else 'EMPTY_METADATA_ROWS' if empty else
            'DUPLICATE_METADATA_ROWS' if duplicates else 'NO_KNOWN_METADATA_ROWS' if not rows else None)
    return {'known_metadata_present':sorted(k for k,v in states.items() if v=={'PRESENT'}),
            'known_metadata_absent':sorted(k for k,v in states.items() if v=={'ABSENT'}),
            'known_metadata_unseen':sorted(FIELDS-set(rows)-malformed),
            'known_metadata_duplicated':duplicates,
            'known_metadata_conflicting_presence':conflicting,
            'known_metadata_empty':empty,'known_metadata_malformed':sorted(malformed),
            'known_metadata_row_counts':{k:len(rows[k]) for k in sorted(rows)},
            'all_fixed_fields_observed':set(rows)==FIELDS and not malformed,
            'format_qualified':reason is None,'format_reason':reason}

def collect_process(process,cap=65536,seconds=20):
    """Bounded capture: stderr is drained and discarded, retaining one boolean."""
    output=bytearray();stderr_present=False;stderr_complete=False;reason=None;selector=selectors.DefaultSelector()
    deadline=time.monotonic()+seconds
    try:
        for stream,label in ((process.stdout,'OUT'),(process.stderr,'ERR')):
            os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,label)
        while selector.get_map():
            remaining=deadline-time.monotonic()
            if remaining<=0:reason='BPUTIL_TIMEOUT';break
            for key,_ in selector.select(min(remaining,0.1)):
                try:chunk=os.read(key.fileobj.fileno(),4096)
                except BlockingIOError:continue
                if not chunk:
                    if key.data=='ERR':stderr_complete=True
                    selector.unregister(key.fileobj);continue
                if key.data=='ERR':stderr_present=True
                else:
                    room=cap+1-len(output);output.extend(chunk[:room])
                    if len(output)>cap:reason='BPUTIL_STDOUT_LIMIT';break
            if reason:break
        if not reason:
            try:process.wait(timeout=max(0.001,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:reason='BPUTIL_TIMEOUT'
    except KeyboardInterrupt:reason='BPUTIL_INTERRUPTED'
    except (OSError,ValueError):reason='BPUTIL_CAPTURE_FAILURE'
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:reason='BPUTIL_TIMEOUT'
        for stream in (process.stdout,process.stderr):
            if stream:stream.close()
    exit_code=process.returncode
    if type(exit_code) is not int or not -255<=exit_code<=255:exit_code=None
    if not reason:
        if exit_code!=0:reason='BPUTIL_EXIT_NONZERO'
        elif not output:reason='BPUTIL_STDOUT_EMPTY'
    diagnostic={'failure_kind':'READ' if reason else None,'failure_reason':reason,
                'bputil_exit':exit_code,'stdout_bytes':len(output),
                'stderr_present':stderr_present,'stderr_complete':stderr_complete,
                'stdout_limit_exceeded':len(output)>cap}
    return bytes(output),diagnostic

def capture_policy(group):
    """Only the already guarded group reaches the fixed read-only bputil call."""
    global policy_diagnostic
    try:
        process=subprocess.Popen(['/usr/bin/bputil','-d','-v',group],stdin=subprocess.DEVNULL,
          stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,
          env={'PATH':'/usr/bin:/usr/sbin:/bin:/sbin','LANG':'C','LC_ALL':'C'})
    except OSError:
        policy_diagnostic={'failure_kind':'READ','failure_reason':'BPUTIL_EXEC_FAILURE',
          'bputil_exit':None,'stdout_bytes':0,'stderr_present':False,'stderr_complete':False,
          'stdout_limit_exceeded':False}
        fail('READ','BPUTIL_EXEC_FAILURE')
    raw,policy_diagnostic=collect_process(process)
    if policy_diagnostic['failure_reason']:fail('READ',policy_diagnostic['failure_reason'])
    return raw

def load_helper():
    path=ROOT/'tools/boot-object31ag/read_selected.py'
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        if not 0<before.st_size<=65536:raise ValueError('helper')
        data=stream.read(65537);after=os.fstat(stream.fileno())
    stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if len(data)!=before.st_size or stamp(before)!=stamp(after):raise ValueError('helper')
    if hashlib.sha256(data).hexdigest()!=PIN:raise ValueError('helper')
    b=types.ModuleType('frozen31ag');b.__file__=str(path);exec(compile(data,str(path),'exec'),b.__dict__)
    return b

def run():
    global stage,partial_roles,policy_diagnostic,failure_kind,failure_reason
    stage='LOCAL_ROOT'
    partial_roles={};policy_diagnostic=None;failure_kind='GUARD';failure_reason='GUARD_REFUSED'
    if sys.platform!='darwin' or os.geteuid()!=0:raise ValueError('local root')
    stage='HELPER';b=load_helper()
    stage='HARDWARE'
    b.require(b.capture(['/usr/sbin/sysctl','-n','hw.model'],64).strip()==b'Mac17,6')
    stage='VOLUME_METADATA'
    lab,current=b.disk_info(b.LAB_MOUNT),b.disk_info('/')
    stage='ORIGINAL_VOLUME'
    b.require(current.get('VolumeName')=='Macintosh HD')
    stage='TARGET_GUARD'
    target=b.guard_target(lab,current,b.plistlib.loads(b.capture(['/usr/sbin/diskutil','apfs','list','-plist'])))
    roles=partial_roles;issues=[]
    for role,group in (('LAB',target['group']),('ORIGINAL',b.uuid(current['APFSVolumeGroupID']))):
        stage='LAB_POLICY' if role=='LAB' else 'ORIGINAL_POLICY'
        policy_diagnostic=None
        try:
            raw=capture_policy(group)
            summary=summarize(raw)
            roles[role]={'read_diagnostic':policy_diagnostic,'metadata':summary}
            if not summary['format_qualified']:fail('FORMAT',summary['format_reason'])
        except ProbeFailure:
            roles.setdefault(role,{'read_diagnostic':policy_diagnostic,'metadata':None})
            roles[role].update(failure_kind=failure_kind,failure_reason=failure_reason)
            issues.append((stage,failure_kind,failure_reason,policy_diagnostic))
    if issues:
        stage,failure_kind,failure_reason,policy_diagnostic=issues[0]
        raise ProbeFailure()
    return {'read_only':True,'metadata_obtained':True,'roles':roles,
            'policy_values_returned':False,'identifiers_returned':False,'settings_changed':False}

def main(argv=None):
    global partial_roles,policy_diagnostic,failure_kind,failure_reason
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    args=parser.parse_args(argv)
    if not args.live:parser.print_help();return 0
    partial_roles={};policy_diagnostic=None;failure_kind='GUARD';failure_reason='GUARD_REFUSED'
    try:result=run()
    except BaseException:
        kind=failure_kind if failure_kind in {'GUARD','READ','FORMAT'} else 'GUARD'
        reasons=READ_REASONS|FORMAT_REASONS|{'GUARD_REFUSED'}
        result={'read_only':True,'metadata_obtained':False,'failed_stage':stage if stage in STAGES else 'REFUSED',
          'failure_kind':kind,'failure_reason':failure_reason if failure_reason in reasons else 'GUARD_REFUSED',
          'roles':partial_roles,'policy_read_diagnostic':policy_diagnostic,
          'partial_metadata_obtained':any(v.get('metadata') is not None for v in partial_roles.values()),
          'policy_values_returned':False,'identifiers_returned':False,'settings_changed':False}
    print(json.dumps(result,sort_keys=True));return 0 if result.get('metadata_obtained') else 2
if __name__=='__main__':raise SystemExit(main())
