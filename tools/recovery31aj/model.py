#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit bounded sanitized assertions for actual31AF→candidate→intendedboot021.

No observation is authenticated by this model. No command, device or path is used.
"""
import importlib.util
import json
from pathlib import Path
import sys

spec=importlib.util.spec_from_file_location('recovery31aj_profile',Path(__file__).with_name('profile.py'))
profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
SNAPSHOT_KEYS={'context','target_bound','original_security','lab_security','lab_ctrr','payload',
               'unrelated_lab_policy_matches','original_semantic_policy_matches','default_entry',
               'comparison_key_bound','protected_policy_matches'}
EDGES={
 'start':{'initial'},'initial':{'recovery_admission'},
 'recovery_admission':{'comparison_key_created'},
 'comparison_key_created':{'recovery_initial','unresolved_return'},'recovery_initial':{'candidate_attempt'},
 'candidate_attempt':{'candidate_postcondition','recovery_restore','unresolved_return'},
 'candidate_postcondition':{'native_window','recovery_restore'},'native_window':{'recovery_restore'},
 'recovery_restore':{'ctrr_attempt','raw_policy_postcondition','unresolved_return'},
 'ctrr_attempt':{'raw_policy_postcondition','unresolved_return'},
 'raw_policy_postcondition':{'boot021_attempt','unresolved_return'},
 'boot021_attempt':{'boot021_postcondition','unresolved_return'},
 'boot021_postcondition':{'original_return'},'original_return':set(),'unresolved_return':set()}
SNAPSHOTS={'initial','recovery_admission','recovery_initial','candidate_postcondition','recovery_restore',
           'raw_policy_postcondition','boot021_postcondition','original_return','unresolved_return'}
ATTEMPTS={'candidate_attempt','ctrr_attempt','boot021_attempt'}


def need(ok,reason):
    if not ok:raise ValueError(reason)


def snapshot(facts,stage):
    need(type(facts) is dict and set(facts)==SNAPSHOT_KEYS,'snapshot schema')
    need(facts['context'] in ('original_desktop','lab_paired_1tr','unknown'),'snapshot context')
    need(facts['target_bound'] is True,'target not bound')
    need(facts['original_security']=='Full' and facts['lab_security']=='Permissive','unexpected security mode')
    need(facts['lab_ctrr'] in ('enabled','disabled','unknown'),'CTRR enum')
    need(facts['payload'] in ('31AF','candidate','BOOT021','NONE','UNKNOWN'),'payload enum')
    need(facts['default_entry'] in ('original','lab','unknown'),'default enum')
    for key in ('unrelated_lab_policy_matches','original_semantic_policy_matches'):
        need(facts[key] is True,'semantic policy comparison not verified')
    if stage in ('initial','recovery_admission'):
        need(facts['comparison_key_bound'] is False and facts['protected_policy_matches']=='NOT_COMPARED','keyless admission only')
    elif stage!='unresolved_return':
        need(facts['comparison_key_bound'] is True and facts['protected_policy_matches'] is True,'private metadata comparison not bound or preserved')
    else:
        need(type(facts['comparison_key_bound']) is bool and facts['protected_policy_matches'] in (True,'NOT_COMPARED'),'unresolved comparison state')
    expected_context='original_desktop' if stage in ('initial','original_return','unresolved_return') else 'lab_paired_1tr'
    need(facts['context']==expected_context,'wrong phase context')
    if stage in ('initial','recovery_admission','recovery_initial'):need(facts['payload']=='31AF','actual initial31AF required')
    if stage=='candidate_postcondition':need(facts['payload']=='candidate' and facts['lab_ctrr']=='enabled','candidate not verified')
    if stage=='raw_policy_postcondition':need(facts['lab_ctrr']=='disabled','raw policy not disabled')
    if stage in ('boot021_postcondition','original_return'):
        need(facts['payload']=='BOOT021' and facts['lab_ctrr']=='disabled','intended final boot021 not observed')
    if stage=='original_return':need(facts['default_entry']=='original','default not independently restored')


def analyze(document):
    need(type(document) is dict and set(document)=={'schema','origin','profile','events'},'document schema')
    need(document['schema']=='ilinux31aj-transaction-model-v1' and document['origin'] in ('SYNTHETIC','SANITIZED_ASSERTIONS'),'model origin')
    plan=profile.validate(document['profile']);events=document['events']
    need(type(events) is list and 0<len(events)<=20,'event bound')
    current='start';attempts=set();native_count=0;candidate_result=None;previous=None;initial_ctrr=None;key_result=None
    for item in events:
        need(type(item) is dict and set(item)=={'stage','facts'},'event schema')
        stage,facts=item['stage'],item['facts']
        need(type(stage) is str and stage in EDGES[current],'phase order')
        if stage in SNAPSHOTS:
            snapshot(facts,stage)
            if stage=='initial':initial_ctrr=facts['lab_ctrr']
            if stage in ('recovery_admission','recovery_initial'):need(facts['lab_ctrr']==initial_ctrr,'initial policy changed before enrollment')
            if stage=='recovery_initial':need(key_result=='exit_zero','comparison key generation not completed')
            if stage=='native_window':raise ValueError('internal snapshot stage')
            if stage=='candidate_postcondition':need(candidate_result=='exit_zero','no native proposal after ambiguous install')
            if stage=='raw_policy_postcondition' and current=='recovery_restore':
                need(previous['lab_ctrr']=='disabled','unrecorded policy transition')
        elif stage=='comparison_key_created':
            need(type(facts) is dict and set(facts)=={'result','source','bytes','private_mode_verified','new_file'},'key generation schema')
            need(facts['result'] in ('exit_zero','exit_nonzero','timeout','interrupted'),'key generation result')
            need(facts['source']=='SYSTEM_RNG' and facts['new_file'] is True,'original new random key required')
            need(type(facts['bytes']) is int and 0<=facts['bytes']<=32,'comparison key byte bound')
            need(type(facts['private_mode_verified']) is bool,'key private mode assertion')
            if facts['result']=='exit_zero':need(facts['bytes']==32 and facts['private_mode_verified'] is True,'comparison key postcondition')
            key_result=facts['result']
        elif stage in ATTEMPTS:
            need(type(facts) is dict and set(facts)=={'result'},'attempt schema')
            need(facts['result'] in ('exit_zero','exit_nonzero','timeout','interrupted'),'attempt result')
            need(stage not in attempts,'mutation retry')
            attempts.add(stage)
            if stage=='candidate_attempt':candidate_result=facts['result']
            if stage=='ctrr_attempt':need(previous['lab_ctrr']=='enabled','unnecessary or unknown policy preparation')
        elif stage=='native_window':
            need(type(facts) is dict and set(facts)=={'elapsed_ms','external_stop','screen'},'native schema')
            need(candidate_result=='exit_zero' and native_count==0,'native retry or failed install')
            need(type(facts['elapsed_ms']) is int and 0<facts['elapsed_ms']<=plan['native_deadline_ms'],'native deadline')
            need(facts['external_stop'] is True and facts['screen'] in ('summary','partial','logo','blank','fault'),'external stop')
            native_count+=1
        previous=facts;current=stage
    return {'schema':'ilinux31aj-transaction-model-result-v1','state':current,
            'status':'MODEL_COMPLETE' if current=='original_return' else 'MODEL_UNRESOLVED' if current=='unresolved_return' else 'MODEL_PARTIAL',
            'native_windows':native_count,'attempts':sorted(attempts),
            'hardware_state_verified':False,'restoration_verified':False,'write_authorized':False,'native_ready':False}


def main():
    data=sys.stdin.buffer.read(65537)
    try:
        need(len(data)<=65536,'input bound')
        result=analyze(json.loads(data,object_pairs_hook=profile.pairs))
    except (ValueError,TypeError,KeyError,UnicodeError):
        result={'schema':'ilinux31aj-transaction-model-result-v1','status':'REFUSED',
                'hardware_state_verified':False,'restoration_verified':False,'write_authorized':False,'native_ready':False}
    print(json.dumps(result,sort_keys=True));return 2 if result['status']=='REFUSED' else 0


if __name__=='__main__':raise SystemExit(main())
