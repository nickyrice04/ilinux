# SPDX-License-Identifier: MIT
"""Original offline controls. Executed shell is rewritten to private fake tools.

No real bputil/kmutil, private group getter, Recovery query or volume is used.
The rollback digest is simulated in shell-flow tests; exact pins have separate
profile tests. These controls do not qualify Recovery or a real selected object.
"""
import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent


def load(name):
    s=importlib.util.spec_from_file_location('recovery31aj_test_'+name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


profile=load('profile');model=load('model');render=load('render');prepare=load('prepare')


def plan():
    return {'schema':profile.SCHEMA,'target':dict(profile.TARGET),'files':{
      'candidate':{'name':'candidate.macho','bytes':16,'sha256':'a'*64},
      'helper':{'name':'ilinux31aj-reader','bytes':16,'sha256':'b'*64},
      'rollback':{'name':'m1n1-boot021.bin','bytes':profile.ROLLBACK_BYTES,'sha256':profile.ROLLBACK_SHA}},
      'native_deadline_ms':90000,'raw_policy_strategy':'ctrr_only','initial_payload':'31AF',
      'final_payload':'BOOT021','publication_authorizes_writes':False}


def snap(stage,payload=None,ctrr=None):
    return {'context':'original_desktop' if stage in ('initial','original_return','unresolved_return') else 'lab_paired_1tr',
      'target_bound':True,'original_security':'Full','lab_security':'Permissive',
      'lab_ctrr':ctrr or ('disabled' if stage in ('raw_policy_postcondition','boot021_postcondition','original_return') else 'enabled' if stage=='candidate_postcondition' else 'unknown'),
      'payload':payload or ('31AF' if stage in ('initial','recovery_admission','recovery_initial') else 'candidate' if stage in ('candidate_postcondition','recovery_restore') else 'BOOT021'),
      'unrelated_lab_policy_matches':True,'original_semantic_policy_matches':True,
      'comparison_key_bound':stage not in ('initial','recovery_admission'),
      'protected_policy_matches':'NOT_COMPARED' if stage in ('initial','recovery_admission') else True,
      'default_entry':'original' if stage=='original_return' else 'unknown'}


def document():
    events=[]
    for stage in ('initial','recovery_admission','comparison_key_created','recovery_initial','candidate_attempt','candidate_postcondition','native_window','recovery_restore','ctrr_attempt','raw_policy_postcondition','boot021_attempt','boot021_postcondition','original_return'):
        if stage.endswith('_attempt'):facts={'result':'exit_zero'}
        elif stage=='comparison_key_created':facts={'result':'exit_zero','source':'SYSTEM_RNG','bytes':32,'private_mode_verified':True,'new_file':True}
        elif stage=='native_window':facts={'elapsed_ms':90000,'external_stop':True,'screen':'summary'}
        else:facts=snap(stage,ctrr='enabled' if stage=='recovery_restore' else None)
        events.append({'stage':stage,'facts':facts})
    return {'schema':'ilinux31aj-transaction-model-v1','origin':'SYNTHETIC','profile':plan(),'events':events}


def event(document,stage):return next(row['facts'] for row in document['events'] if row['stage']==stage)


class ProfileTests(unittest.TestCase):
    def test_canonical_round_trip(self):
        v=plan();self.assertEqual(profile.load(profile.canonical(v)),v)
    def test_duplicate_key(self):
        with self.assertRaises(ValueError):profile.load(b'{"schema":1,"schema":2}')
    def test_no_write_authority(self):
        p=plan();p['publication_authorizes_writes']=True
        with self.assertRaises(ValueError):profile.validate(p)
    def test_raw_reset_strategy_refused(self):
        p=plan();p['raw_policy_strategy']='nc'
        with self.assertRaises(ValueError):profile.validate(p)
    def test_old_candidate_refused(self):
        for pin in (profile.ROLLBACK_SHA,profile.INITIAL_SHA,profile.OLD_CANDIDATE):
            p=plan();p['files']['candidate']['sha256']=pin
            with self.assertRaises(ValueError):profile.validate(p)
    def test_rollback_pin_immutable(self):
        p=plan();p['files']['rollback']['bytes']-=1
        with self.assertRaises(ValueError):profile.validate(p)
    def test_hostile_names_bounds_and_types(self):
        for role,key,value in [('helper','name','../x'),('candidate','bytes',True),('helper','bytes',9*1024*1024),('candidate','sha256','A'*64)]:
            p=plan();p['files'][role][key]=value
            with self.assertRaises(ValueError):profile.validate(p)
    def test_wrong_target_or_extra_field_refused(self):
        for key,value in [('target',{'model':'other'}),('extra',False)]:
            p=plan();p[key]=value
            with self.assertRaises(ValueError):profile.validate(p)


class ModelTests(unittest.TestCase):
    def test_actual31af_complete_and_no_authority(self):
        r=model.analyze(document());self.assertEqual(r['status'],'MODEL_COMPLETE')
        for k in ('write_authorized','native_ready','hardware_state_verified','restoration_verified'):self.assertIs(r[k],False)
    def test_no_fabricated_boot021_initial(self):
        d=document();d['events'][0]['facts']['payload']='BOOT021'
        with self.assertRaises(ValueError):model.analyze(d)
    def test_transient_no_custom_object_allowed(self):
        d=document();event(d,'raw_policy_postcondition')['payload']='NONE'
        self.assertEqual(model.analyze(d)['status'],'MODEL_COMPLETE')
    def test_initial_ctrr_must_not_change_without_write(self):
        d=document();d['events'][1]['facts']['lab_ctrr']='enabled'
        with self.assertRaises(ValueError):model.analyze(d)
    def test_policy_drift_refused(self):
        for key in ('unrelated_lab_policy_matches','original_semantic_policy_matches'):
            d=document();event(d,'raw_policy_postcondition')[key]=False
            with self.assertRaises(ValueError):model.analyze(d)
    def test_failed_timeout_interrupted_cannot_boot(self):
        for result in ('exit_nonzero','timeout','interrupted'):
            d=document();event(d,'candidate_attempt')['result']=result
            with self.assertRaises(ValueError):model.analyze(d)
    def test_unknown_ctrr_no_blind_reset(self):
        d=document();event(d,'recovery_restore')['lab_ctrr']='unknown'
        with self.assertRaises(ValueError):model.analyze(d)
    def test_native_deadline_external_stop(self):
        for key,value in [('elapsed_ms',90001),('elapsed_ms',True),('external_stop',False)]:
            d=document();event(d,'native_window')[key]=value
            with self.assertRaises(ValueError):model.analyze(d)
    def test_default_restoration_is_separate(self):
        d=document();d['events'][-1]['facts']['default_entry']='unknown'
        with self.assertRaises(ValueError):model.analyze(d)
    def test_unresolved_return_does_not_claim_restored(self):
        d=document();d['events']=d['events'][:5]+[{'stage':'unresolved_return','facts':snap('unresolved_return','UNKNOWN')}]
        r=model.analyze(d);self.assertEqual(r['status'],'MODEL_UNRESOLVED');self.assertIs(r['restoration_verified'],False)
    def test_no_unbound_snapshot_after_admission(self):
        d=document();event(d,'recovery_initial')['comparison_key_bound']=False
        with self.assertRaises(ValueError):model.analyze(d)
    def test_protected_metadata_drift_refused(self):
        d=document();event(d,'candidate_postcondition')['protected_policy_matches']=False
        with self.assertRaises(ValueError):model.analyze(d)
    def test_key_generation_failure_cannot_enroll(self):
        for result in ('exit_nonzero','timeout','interrupted'):
            d=document();event(d,'comparison_key_created')['result']=result
            with self.assertRaises(ValueError):model.analyze(d)
    def test_key_generation_must_be_new_private_32_bytes(self):
        for key,value in (('source','APPLE_KEY'),('bytes',31),('private_mode_verified',False),('new_file',False)):
            d=document();event(d,'comparison_key_created')[key]=value
            with self.assertRaises(ValueError):model.analyze(d)


FAKE=r'''#!/usr/bin/env python3
import hashlib,hmac,json,os,pathlib,stat,sys
p=pathlib.Path;root=p(os.environ['FAKE_ROOT']);a=sys.argv[1:];role=p(sys.argv[0]).name
s=json.loads((root/'machine.json').read_text());prof=json.loads((root/'profile.json').read_text())
def save(): (root/'machine.json').write_text(json.dumps(s))
def stop(code=2):sys.exit(code)
if role=='id':print('0');stop(0)
if role=='hash':
 f=p(a[0]);print(prof['files']['rollback']['sha256'] if f.name=='m1n1-boot021.bin' else hashlib.sha256(f.read_bytes()).hexdigest());stop(0)
if role=='stat':
 f=p(a[-1]);fmt=a[-2]
 if fmt=='%z':print(f.stat().st_size)
 elif fmt=='%u:%Lp':print('0:'+oct(f.stat().st_mode&511)[2:])
 else:stop()
 stop(0)
if role in ('bputil','kmutil'):
 if role=='kmutil' and (a[:2]!=['configure-boot','--custom-boot-object'] or '--volume' not in a):stop()
 op='ctrr' if role=='bputil' else 'boot021' if '--raw' in a else 'candidate'
 with (root/'mutations.jsonl').open('a') as f:f.write(json.dumps({'op':op,'argv':a})+'\n')
 rc=s.get(op+'_rc',0)
 if rc==0 or s.get('change_on_error'):
  s['payload']='NONE' if op=='ctrr' else 'BOOT021' if op=='boot021' else 'CANDIDATE'
  s['ctrr']='disabled' if op in ('ctrr','boot021') else 'enabled'
  if op=='candidate' and s.get('metadata_change_after_candidate'):s['lab_metadata']='CHANGED'
 save();stop(rc)
if role!='ilinux31aj-reader':stop()
if a[:2]==['--capability-check','recovery-transaction-v2']:
 if len(a)!=4 or a[2]!='--profile' or not p(a[3]).is_file():stop()
 stop(2 if s.get('cap_fail') else 0)
if '--generate-comparison-key' in a:
 info=os.fstat(1)
 if not stat.S_ISREG(info.st_mode) or info.st_size or info.st_mode&511!=384 or info.st_uid!=os.geteuid():stop()
 if s.get('keygen_rc'):stop(s['keygen_rc'])
 sys.stdout.buffer.write(b'K'*s.get('keygen_bytes',32));sys.stdout.buffer.flush();os.fsync(1);stop(0)
def bound_metadata():
 if '--comparison-key' not in a:return {'metadata_bound':False,'comparison_key_id':'NONE','lab_metadata_hmac':'NONE','original_metadata_hmac':'NONE'}
 try:
  path=p(a[a.index('--comparison-key')+1]);key=path.read_bytes()
  if len(key)!=32 or path.is_symlink() or path.stat().st_mode&511!=384:stop()
 except (OSError,IndexError):stop()
 out={'metadata_bound':True,'comparison_key_id':hashlib.sha256(b'ID'+key).hexdigest()}
 for role in ('lab','original'):
  message=(role+s.get(role+'_metadata','STABLE')).encode()
  out[role+'_metadata_hmac']=hmac.new(key,message,hashlib.sha256).hexdigest()
 return out
if '--snapshot' in a:
 s['reads']=s.get('reads',0)+1;save()
 if s.get('read_fail'):stop()
 out={'payload':s.get('payload'),'ctrr':s.get('ctrr'),'guard':not s.get('guard_fail'),
  'semantic':not s.get('semantic_fail'),'origin':'SYNTHETIC','profile':hashlib.sha256((root/'profile.json').read_bytes()).hexdigest()}
 out.update(bound_metadata());print(json.dumps(out));stop(0)
if '--validate-snapshot' in a:
 f=json.loads(p(a[a.index('--validate-snapshot')+1]).read_text());phase=a[a.index('--phase')+1]
 binding=bound_metadata()
 if phase=='initial-admission':
  if f.get('metadata_bound') or binding['metadata_bound']:stop()
 elif not f.get('metadata_bound') or not binding['metadata_bound'] or f.get('comparison_key_id')!=binding['comparison_key_id']:stop()
 if '--baseline' in a:
  try:b=json.loads(p(a[a.index('--baseline')+1]).read_text())
  except (ValueError,OSError):stop()
  if b.get('origin')!='SYNTHETIC' or b.get('profile')!=f.get('profile'):stop()
  for k in ('comparison_key_id','lab_metadata_hmac','original_metadata_hmac'):
   if b.get(k)!=f.get(k):stop()
 if not f['guard'] or not f['semantic']:stop()
 if phase in ('initial','initial-admission'):ok=f['payload']=='31AF'
 elif phase=='candidate':ok=f['payload']=='CANDIDATE' and f['ctrr']=='enabled' and not s.get('candidate_post_fail')
 elif phase=='before-restore':ok=True
 elif phase=='raw-policy':ok=f['ctrr']=='disabled'
 elif phase=='restored':ok=f['payload']=='BOOT021' and f['ctrr']=='disabled'
 else:ok=False
 stop(0 if ok else 2)
if '--snapshot-value' in a:
 if not bound_metadata()['metadata_bound']:stop()
 f=json.loads(p(a[1]).read_text());print(f['ctrr']);stop(0)
if '--target-group-private' in a:
 if not bound_metadata()['metadata_bound']:stop()
 if s.get('guard_fail'):stop()
 print('00000000-0000-0000-0000-000000000000');stop(0)
stop()
'''


class ShellFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.lab=self.root/'lab';self.original=self.root/'original';self.data=self.root/'data'
        for x in (self.lab,self.original):(x/'System/Library/CoreServices').mkdir(parents=True)
        self.kit=self.data/'Users/Shared/iLinuxBoot/31aj-kit';self.kit.mkdir(parents=True)
        self.state=self.kit.with_name('31aj-state');(self.root/'tmp').mkdir();(self.root/'tty').touch()
        self.bin=self.root/'fakebin';self.bin.mkdir()
        for name in ('id','stat','hash','bputil','kmutil'):
            f=self.bin/name;f.write_text(FAKE);f.chmod(0o700)
        helper=self.kit/'ilinux31aj-reader';helper.write_text(FAKE);helper.chmod(0o700)
        candidate=self.kit/'candidate.macho';candidate.write_bytes(b'new-readable-31aj')
        (self.kit/'m1n1-boot021.bin').write_bytes(b'\0'*profile.ROLLBACK_BYTES)
        self.p=plan()
        for role,file in [('helper',helper),('candidate',candidate)]:
            self.p['files'][role].update(bytes=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
        canonical=profile.canonical(self.p);(self.kit/'profile.json').write_bytes(canonical);(self.root/'profile.json').write_bytes(canonical)
        self.machine(payload='31AF',ctrr='unknown')
    def machine(self,**changes):
        f=self.root/'machine.json';s=json.loads(f.read_text()) if f.exists() else {};s.update(changes);f.write_text(json.dumps(s))
    def calls(self):
        f=self.root/'mutations.jsonl';return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
    def run_block(self,op):
        text=render.render(self.p,op)
        for a,b in ((render.KIT,str(self.kit)),(render.STATE,str(self.state)),(render.LAB,str(self.lab)),(render.ORIGINAL,str(self.original))):text=text.replace(a,b)
        for tool in ('id','stat','bputil','kmutil'):text=text.replace('/usr/bin/'+tool,str(self.bin/tool))
        begin=text.index('hash_file() {');end=text.index('\n',begin)
        text=text[:begin]+'hash_file() { "'+str(self.bin/'hash')+'" "$1"; }'+text[end:]
        text=text.replace('/private/tmp/ilinux31aj.',str(self.root/'tmp/ilinux31aj.')).replace('/dev/tty',str(self.root/'tty'))
        for forbidden in ('/usr/bin/bputil','/usr/bin/kmutil','/Volumes/','/dev/tty','/private/tmp/'):
            self.assertNotIn(forbidden,text)
        env=dict(os.environ,FAKE_ROOT=str(self.root))
        return subprocess.run(['/bin/bash','--noprofile','--norc'],input=text,text=True,env=env,capture_output=True,timeout=12)
    def install(self):
        r=self.run_block('install');self.assertEqual(r.returncode,0,r.stdout+r.stderr);return r
    def test_success_install_restore_repeat_readonly(self):
        installed=self.install();self.assertEqual(self.run_block('restore').returncode,0)
        self.assertEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate','ctrr','boot021'])
        self.assertEqual(self.calls()[1]['argv'][:2],['-c','-v'])
        for index in (0,2):
            argv=self.calls()[index]['argv']
            self.assertEqual(argv[:2],['configure-boot','--custom-boot-object'])
            self.assertIn('--volume',argv);self.assertNotIn('-c',argv);self.assertNotIn('-v',argv)
        self.assertIn('--compress',self.calls()[0]['argv'])
        self.assertEqual(self.calls()[2]['argv'][3:8],['--raw','--entry-point','2048','--lowest-virtual-address','0'])
        self.assertNotIn('-n',sum([x['argv'] for x in self.calls()],[]))
        self.assertTrue((self.state/'baseline.json').is_file())
        key=self.state/'comparison.key';self.assertEqual(key.stat().st_size,32);self.assertEqual(key.stat().st_mode&511,384)
        self.assertNotIn(key.read_bytes().decode(),installed.stdout+installed.stderr)
        base=json.loads((self.state/'baseline.json').read_text());self.assertTrue(base['metadata_bound'])
        self.assertEqual(len(base['lab_metadata_hmac']),64);self.assertEqual(len(base['original_metadata_hmac']),64)
    def test_install_replay_refused(self):
        self.install();self.assertNotEqual(self.run_block('install').returncode,0);self.assertEqual(len(self.calls()),1)
    def test_capability_refusal_before_mutation(self):
        self.machine(cap_fail=True);self.assertNotEqual(self.run_block('install').returncode,0);self.assertEqual(self.calls(),[])
    def test_wrong_target_or_mode_refused_before_mutation(self):
        self.machine(guard_fail=True);self.assertNotEqual(self.run_block('install').returncode,0);self.assertEqual(self.calls(),[])
    def test_profile_changed_refused(self):
        (self.kit/'profile.json').write_text('{}');self.assertNotEqual(self.run_block('install').returncode,0);self.assertEqual(self.calls(),[])
    def test_helper_changed_refused(self):
        with (self.kit/'ilinux31aj-reader').open('a') as f:f.write('# changed\n')
        self.assertNotEqual(self.run_block('install').returncode,0);self.assertEqual(self.calls(),[])
    def failed_install(self,rc):
        self.machine(candidate_rc=rc)
        r=self.run_block('install');self.assertNotEqual(r.returncode,0)
        self.assertTrue((self.state/'candidate.json').is_file())
        self.assertEqual(len(self.calls()),1)
        self.assertNotEqual(self.run_block('install').returncode,0)
    def test_install_nonzero_readback_no_retry(self):self.failed_install(1)
    def test_install_timeout_status_readback_no_retry(self):self.failed_install(124)
    def test_install_interrupt_status_readback_no_retry(self):self.failed_install(130)
    def test_candidate_postcondition_failure(self):
        self.machine(candidate_post_fail=True);self.assertNotEqual(self.run_block('install').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate'])
    def test_disabled_ctrr_skips_policy(self):
        self.install();self.machine(ctrr='disabled');self.assertEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate','boot021'])
    def test_unknown_ctrr_refuses(self):
        self.install();self.machine(ctrr='unknown');self.assertNotEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate'])
    def test_policy_failure_no_raw_same_run_no_policy_retry(self):
        self.install();self.machine(ctrr_rc=124)
        self.assertNotEqual(self.run_block('restore').returncode,0);self.assertTrue((self.state/'raw-policy.json').is_file())
        self.assertNotEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate','ctrr'])
    def test_policy_ambiguous_but_disabled_can_resume_raw_only(self):
        self.install();self.machine(ctrr_rc=130,change_on_error=True)
        self.assertNotEqual(self.run_block('restore').returncode,0)
        self.assertEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate','ctrr','boot021'])
    def test_raw_failure_no_retry(self):
        self.install();self.machine(boot021_rc=1)
        self.assertNotEqual(self.run_block('restore').returncode,0)
        self.assertNotEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate','ctrr','boot021'])
    def test_restore_independent_candidate_missing(self):
        self.install();(self.kit/'candidate.macho').unlink();self.assertEqual(self.run_block('restore').returncode,0)
    def test_semantic_drift_blocks_restore(self):
        self.install();self.machine(semantic_fail=True);self.assertNotEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate'])
    def test_corrupt_persistent_baseline_refused(self):
        self.install();(self.state/'baseline.json').write_text('{}')
        self.assertNotEqual(self.run_block('restore').returncode,0);self.assertEqual(len(self.calls()),1)
    def test_symlink_state_refused(self):
        self.state.symlink_to(self.root/'unrelated');self.assertNotEqual(self.run_block('install').returncode,0);self.assertEqual(self.calls(),[])
    def test_failed_key_generation_stops_before_candidate(self):
        self.machine(keygen_rc=1);self.assertNotEqual(self.run_block('install').returncode,0)
        self.assertEqual(self.calls(),[]);self.assertFalse((self.state/'baseline.json').exists())
    def test_short_key_generation_stops_before_candidate(self):
        self.machine(keygen_bytes=31);self.assertNotEqual(self.run_block('install').returncode,0)
        self.assertEqual(self.calls(),[]);self.assertFalse((self.state/'baseline.json').exists())
    def test_missing_persistent_key_blocks_restore(self):
        self.install();(self.state/'comparison.key').unlink();self.assertNotEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate'])
    def test_unsafe_persistent_key_mode_blocks_restore(self):
        self.install();(self.state/'comparison.key').chmod(0o640);self.assertNotEqual(self.run_block('restore').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate'])
    def test_symlink_key_blocks_restore(self):
        self.install();key=self.state/'comparison.key';key.rename(self.state/'other-key');key.symlink_to(self.state/'other-key')
        self.assertNotEqual(self.run_block('restore').returncode,0);self.assertEqual(len(self.calls()),1)
    def test_swapped_key_cannot_rebind_saved_baseline(self):
        self.install();(self.state/'comparison.key').write_bytes(b'X'*32)
        self.assertNotEqual(self.run_block('restore').returncode,0);self.assertEqual(len(self.calls()),1)
    def test_original_protected_metadata_drift_blocks_restore(self):
        self.install();self.machine(original_metadata='CHANGED')
        self.assertNotEqual(self.run_block('restore').returncode,0);self.assertEqual(len(self.calls()),1)
    def test_lab_protected_metadata_drift_after_install_blocks_boot(self):
        self.machine(metadata_change_after_candidate=True);self.assertNotEqual(self.run_block('install').returncode,0)
        self.assertEqual([x['op'] for x in self.calls()],['candidate'])
        base=json.loads((self.state/'baseline.json').read_text());post=json.loads((self.state/'candidate.json').read_text())
        self.assertNotEqual(base['lab_metadata_hmac'],post['lab_metadata_hmac'])


class RenderTests(unittest.TestCase):
    def test_both_blocks_parse_in_bash(self):
        for op in ('install','restore'):
            r=subprocess.run(['/bin/bash','--noprofile','--norc','-n'],input=render.render(plan(),op),text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)
    def test_no_automated_boot_default_or_reset(self):
        t=render.render(plan(),'install')+render.render(plan(),'restore')
        for word in ('/usr/sbin/bless','/sbin/reboot','bputil -n','--permissive-security','curl ','wget '):self.assertNotIn(word,t)
    def test_html_contains_complete_escaped_blocks(self):
        t=render.page(plan());self.assertIn('First visit',t);self.assertIn('&lt;/dev/tty',t)
    def test_readonly_textareas_roundtrip_exact_shell_blocks(self):
        class Boxes(HTMLParser):
            def __init__(self):super().__init__(convert_charrefs=True);self.boxes={};self.current=None
            def handle_starttag(self,tag,attrs):
                if tag=='textarea':
                    attrs=dict(attrs);self.current=attrs['id'];self.boxes[self.current]={'attrs':attrs,'text':''}
            def handle_endtag(self,tag):
                if tag=='textarea':self.current=None
            def handle_data(self,data):
                if self.current is not None:self.boxes[self.current]['text']+=data
        parser=Boxes();parser.feed(render.page(plan()));parser.close()
        self.assertEqual(set(parser.boxes),{'install-block','restore-block'})
        for operation in ('install','restore'):
            box=parser.boxes[operation+'-block']
            self.assertEqual(box['text'],render.render(plan(),operation))
            self.assertIn('readonly',box['attrs']);self.assertEqual(box['attrs']['spellcheck'],'false')
            self.assertEqual(box['attrs']['wrap'],'off');self.assertNotIn('autofocus',box['attrs'])
    def test_copy_page_has_no_script_form_autofocus_or_event_handlers(self):
        class Passive(HTMLParser):
            def handle_starttag(inner,tag,attrs):
                self.assertNotIn(tag,{'script','form','iframe','object','embed'})
                for key,value in attrs:
                    self.assertNotEqual(key,'autofocus');self.assertFalse(key.startswith('on'))
                    self.assertNotIn('javascript:',value or '')
        text=render.page(plan());Passive().feed(text)
        for instruction in ('Command+A','Command+C','Quit the browser','open Terminal','paste once'):
            self.assertIn(instruction,text)
    def test_workspace_and_output_boundaries(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'link').symlink_to(root)
            for path in (root/'link/x',root/'../x',Path('/dev/null')):
                with self.assertRaises(ValueError):prepare.checked_path(path,root,False)


class PreparationTests(unittest.TestCase):
    """Synthetic source closure; raw artifact digest alone uses an explicit fake."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();src=self.root/'tools/recovery31aj';src.mkdir(parents=True)
        rows=[]
        for name in ('profile.py','model.py','render.py','prepare.py','test_recovery.py','README.md'):
            data=(HERE/name).read_bytes();(src/name).write_bytes(data)
            rows.append(hashlib.sha256(data).hexdigest()+'  tools/recovery31aj/'+name)
        self.inventory=self.root/'source-sha256.txt';self.inventory.write_text('\n'.join(rows)+'\n')
        self.kit=self.root/'build/kit';self.kit.mkdir(parents=True)
        self.p=plan()
        for role,item in self.p['files'].items():
            data=b'\0'*profile.ROLLBACK_BYTES if role=='rollback' else (role+'-synthetic').encode()
            (self.kit/item['name']).write_bytes(data)
            if role!='rollback':item.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        self.pfile=self.kit/'profile.json';self.pfile.write_bytes(profile.canonical(self.p))
        original=prepare.sha_file
        self.fake_hash=mock.patch.object(prepare,'sha_file',side_effect=lambda p:profile.ROLLBACK_SHA if p.name=='m1n1-boot021.bin' else original(p))
        self.fake_hash.start();self.addCleanup(self.fake_hash.stop)
    def call(self,output='build/pages'):
        return prepare.prepare(self.pfile,self.kit,self.inventory,self.root/output,root=self.root)
    def test_complete_inert_package_and_no_authority(self):
        r=self.call();self.assertIs(r['write_authorized'],False);self.assertEqual(r['live_recovery_admission'],'UNKNOWN')
        out=self.root/'build/pages';self.assertEqual(len(list(out.iterdir())),5)
        for name,item in r['output'].items():self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),item['sha256'])
    def test_existing_output_refused(self):
        self.call()
        with self.assertRaises(ValueError):self.call()
    def test_source_change_refused(self):
        (self.root/'tools/recovery31aj/model.py').write_text('# changed\n')
        with self.assertRaises(ValueError):self.call()
        self.assertFalse((self.root/'build/pages').exists())
    def test_source_inventory_missing_member_refused(self):
        rows=self.inventory.read_text().splitlines();self.inventory.write_text('\n'.join(rows[:-1])+'\n')
        with self.assertRaises(ValueError):self.call()
    def test_duplicate_inventory_refused(self):
        rows=self.inventory.read_text();self.inventory.write_text(rows+rows.splitlines()[0]+'\n')
        with self.assertRaises(ValueError):self.call()
    def test_candidate_mismatch_refused(self):
        (self.kit/'candidate.macho').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.call()
    def test_noncanonical_profile_refused(self):
        self.pfile.write_text(json.dumps(self.p))
        with self.assertRaises(ValueError):self.call()
    def test_profile_size_bound_before_read(self):
        self.pfile.write_bytes(b' '*16385)
        with self.assertRaises(ValueError):self.call()
    def test_output_outside_build_refused(self):
        with self.assertRaises(ValueError):self.call('other/pages')


if __name__=='__main__':unittest.main()
