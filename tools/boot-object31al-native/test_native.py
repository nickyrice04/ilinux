#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original C diagnostics over synthetic CF/files/children; never live modes."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SANITIZE='--sanitize' in sys.argv
if SANITIZE:sys.argv.remove('--sanitize')
spec=importlib.util.spec_from_file_location('frozen31aj_fixture_functions',ROOT/'tools/boot-object31aj-native/test_native.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
spec=importlib.util.spec_from_file_location('generator31al_tested',HERE/'generate.py')
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)

def sha(data):return hashlib.sha256(data).hexdigest()

HARNESS=r'''#include "diagnostic.h"
#include "state.c"
int main(int argc,char **argv){
 if(argc==2&&!strcmp(argv[1],"__child")){fputs("SYNTHETIC_SECRET_MUST_NOT_ESCAPE",stdout);return 7;}
 if(argc==2&&!strcmp(argv[1],"__bound")){for(int i=0;i<40;i++)putchar('S');return 0;}
 diagnostic_reset(true);diagnostic_note(DS_LAB_INFO,DK_FORMAT,DR_PLIST_DICTIONARY);
 if(argc==2&&!strcmp(argv[1],"admission")){
  Profile p={0};Snapshot s={0};strcpy(p.sha,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");strcpy(s.profile_sha,p.sha);s.synthetic=s.guarded=s.paired=s.original_full=s.lab_permissive=s.policy_complete=s.selected_exact=true;strcpy(s.selected,"31AF");
  diagnostic.collected=true;diagnostic_note(DS_INITIAL_ADMISSION,DK_GUARD,DR_INITIAL_ADMISSION_GUARD);
  if(validate_snapshot(&s,NULL,&p,NULL,"initial-admission",true)){diagnostic.valid=true;diagnostic_note(DS_INITIAL_ADMISSION,DK_NONE,DR_NONE);}diagnostic_print(&diagnostic);return diagnostic.valid?0:2;
 }
 const char *args[]={argv[0],argc==2&&!strcmp(argv[1],"boundchild")?"__bound":"__child",NULL};uint8_t *data=NULL;size_t n=0;
 bool ok=capture(args,argc==2&&!strcmp(argv[1],"boundchild")?8:256,&data,&n);free(data);
 if(argc==2&&!strcmp(argv[1],"sequence")){const char *later[]={argv[0],"__bound",NULL};uint8_t *other=NULL;size_t count=0;capture(later,256,&other,&count);free(other);}
 if(ok)diagnostic_fail(DS_LAB_INFO,DK_FORMAT,DR_PLIST_DICTIONARY);diagnostic_print(&diagnostic);return ok?0:2;
}'''

class Diagnostic(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  base=ROOT/'build/boot-object31al-native/tests';base.mkdir(parents=True,exist_ok=True)
  cls.directory=Path(tempfile.mkdtemp(prefix='synthetic-',dir=base)).resolve()
  cls.plain=bytes((i*17^(i>>4))&255 for i in range(65536))
  definition={'schema':'ilinux31aj-compiled-candidate-v1','target':{'model':'Mac17,6','board':'j716c','chip_id':'0x6050'},'bytes':len(cls.plain),'sha256':sha(cls.plain),'publication_authorizes_writes':False}
  d=cls.directory/'definition.json';d.write_text(json.dumps(definition))
  command=[sys.executable,'-I',str(HERE/'build.py'),'--output',str(cls.directory/'compiled'),'--candidate-definition',str(d)]
  if SANITIZE:command.append('--sanitize')
  r=subprocess.run(command,text=True,capture_output=True,timeout=45)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  cls.binary=cls.directory/'compiled/ilinux31aj-reader';blob=cls.binary.read_bytes()
  cls.profile={'schema':'ilinux31aj-recovery-profile-v1','target':definition['target'],'files':{'candidate':{'name':'candidate.macho','bytes':len(cls.plain),'sha256':sha(cls.plain)},'helper':{'name':'ilinux31aj-reader','bytes':len(blob),'sha256':sha(blob)},'rollback':{'name':'m1n1-boot021.bin','bytes':3932160,'sha256':'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'}},'native_deadline_ms':90000,'raw_policy_strategy':'ctrr_only','initial_payload':'31AF','final_payload':'BOOT021','publication_authorizes_writes':False}
  cls.profile_path=cls.directory/'profile.json';cls.profile_path.write_text(json.dumps(cls.profile))
  sources=cls.directory/'compiled/sources';(sources/'harness.c').write_text(HARNESS)
  cls.harness=cls.directory/'capture-harness'
  args=['xcrun','clang','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-arch','arm64','-DWORKSPACE_ROOT='+json.dumps(str(ROOT)),'-DCANDIDATE_BYTES='+str(len(cls.plain)),'-DCANDIDATE_SHA256='+json.dumps(sha(cls.plain))]
  if SANITIZE:args+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
  args += [str(sources/n) for n in ('core.c','json.c','diagnostic.c','harness.c')]+['-framework','CoreFoundation','-lcompression','-o',str(cls.harness)]
  r=subprocess.run(args,text=True,capture_output=True,timeout=45)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 @classmethod
 def tearDownClass(cls):shutil.rmtree(cls.directory)
 def setUp(self):
  self.scratch=Path(tempfile.mkdtemp(prefix='case-',dir=self.directory));self.addCleanup(shutil.rmtree,self.scratch)
 def invoke(self,*args,profile=True):
  command=[str(self.binary),*map(str,args)]
  if profile:command+=['--profile',str(self.profile_path)]
  r=subprocess.run(command,text=True,capture_output=True,timeout=15)
  self.assertEqual(r.stderr,'')
  return r,json.loads(r.stdout) if r.stdout.startswith('{') else r.stdout
 def fixture(self,change=None):
  selected=self.scratch/'selected.bin';selected.write_bytes(self.plain);value=old.metadata(selected)
  if change:change(value)
  path=self.scratch/'fixture.plist';path.write_bytes(plistlib.dumps(value))
  return self.invoke('--diagnose-fixture',path)
 def record(self):
  return {'schema':'ilinux31al-snapshot-diagnostic-v1','scope':'SYNTHETIC_CONTROL','status':'REFUSED','stage':'PROFILE','failure_kind':'FORMAT','reason':'PROFILE_BINDING','command':'NONE','command_exit':None,'stdout_bytes':0,'snapshot_collected':False,'initial_admission_valid':False,'read_only':True,'writes_authorized':False,'native_ready':False,'identifiers_returned':False,'policy_values_returned':False}
 def validate(self,value):
  path=self.scratch/'diagnostic.json';path.write_text(json.dumps(value));return self.invoke('--validate-diagnostic',path)
 def assert_refused(self,result,kind=None,reason=None,collected=False):
  r,d=result;self.assertEqual(r.returncode,2,d);self.assertEqual(d['status'],'REFUSED');self.assertEqual(d['snapshot_collected'],collected);self.assertFalse(d['initial_admission_valid'])
  for k in ('writes_authorized','native_ready','identifiers_returned','policy_values_returned'):self.assertIs(d[k],False)
  self.assertIs(d['read_only'],True)
  if kind:self.assertEqual(d['failure_kind'],kind,d)
  if reason:self.assertEqual(d['reason'],reason,d)
  return d
 def test_default_and_help_are_inert(self):
  for args in ((),('--help',)):
   r,text=self.invoke(*args,profile=False);self.assertEqual(r.returncode,0);self.assertIn('Default: help; no host query',text)
 def test_write_private_rng_and_full_snapshot_modes_not_exposed(self):
  for flag in ('--snapshot','--snapshot-value','--target-group-private','--generate-comparison-key','--capability-check','--verify-file','--stage'):
   self.assert_refused(self.invoke(flag,profile=False),'FORMAT','ARGUMENTS')
 def test_profile_self_binding_and_unknown_keys_refused(self):
  for changed in (dict(self.profile,secret='SECRET_PRIVATE_MARKER'),dict(self.profile,publication_authorizes_writes=True)):
   p=self.scratch/'bad-profile.json';p.write_text(json.dumps(changed));r,d=self.invoke('--diagnose-fixture',self.scratch/'absent','--profile',p,profile=False);self.assert_refused((r,d),'FORMAT','PROFILE_BINDING');self.assertNotIn('SECRET',json.dumps(d))
 def test_profile_helper_hash_tamper_refused_before_fixture(self):
  p=copy.deepcopy(self.profile);p['files']['helper']['sha256']='b'*64;path=self.scratch/'p.json';path.write_text(json.dumps(p));self.assert_refused(self.invoke('--diagnose-fixture',self.scratch/'absent','--profile',path,profile=False),'FORMAT','PROFILE_BINDING')
 def test_duplicate_and_mixed_cli_options_refused(self):
  for args in (('--diagnose-fixture','missing','--target-volume','/Volumes/iLinux Boot Lab'),('--diagnose-fixture','one','--validate-diagnostic','two'),('--diagnose-fixture','one','--profile',self.profile_path)):
   self.assert_refused(self.invoke(*args),'FORMAT','ARGUMENTS')
 def test_frozen_guards_strip_to_identical_sources(self):
  source=self.directory/'compiled/sources'
  for name in ('core.c','json.c','reader.h'):self.assertEqual(sha((source/name).read_bytes()),generator.FROZEN[name])
  self.assertEqual(sha(generator.strip((source/'state.c').read_text()).encode()),generator.FROZEN['state.c'])
 def test_successful_collection_unknown_or_candidate_is_separate_initial_guard(self):
  d=self.assert_refused(self.fixture(),'GUARD','INITIAL_ADMISSION_GUARD',True);self.assertEqual(d['stage'],'INITIAL_ADMISSION');self.assertEqual(d['command'],'NONE')
 def test_unreadable_selected_object_does_not_fail_collection(self):
  d=self.assert_refused(self.fixture(lambda v:v.update(selected_file=str(self.scratch/'missing'))),'GUARD','INITIAL_ADMISSION_GUARD',True);self.assertEqual(d['stage'],'INITIAL_ADMISSION')
 def test_fixture_file_missing_symlink_and_bound_are_format(self):
  self.assert_refused(self.invoke('--diagnose-fixture',self.scratch/'absent'),'FORMAT','FIXTURE_INPUT')
  target=self.scratch/'target';target.write_bytes(b'x');link=self.scratch/'link';link.symlink_to(target);self.assert_refused(self.invoke('--diagnose-fixture',link),'FORMAT','FIXTURE_INPUT')
  with target.open('wb') as f:f.truncate(1048577)
  self.assert_refused(self.invoke('--diagnose-fixture',target),'FORMAT','FIXTURE_INPUT')
 def test_fixture_wrong_plist_shape_has_fixed_format_stage(self):
  f=self.scratch/'wrong.plist';f.write_bytes(plistlib.dumps(['SECRET_METADATA']));d=self.assert_refused(self.invoke('--diagnose-fixture',f),'FORMAT','PLIST_DICTIONARY');self.assertEqual(d['stage'],'FIXTURE_FORMAT');self.assertNotIn('SECRET',json.dumps(d))
 def test_recovery_model_and_root_guards_remain_guard(self):
  for key,val in (('recovery',False),('root',False),('model','SECRET_MODEL')):
   self.assert_refused(self.fixture(lambda v:v.update({key:val})),'GUARD','RECOVERY_ENVIRONMENT')
 def test_pairing_and_environment_are_explicit_guards(self):
  for oldtext,newtext,reason in (('Pairing: Paired','Pairing: Unpaired','NOT_PAIRED'),('one true recoveryOS','ordinary recoveryOS','NOT_ONE_TRUE_RECOVERY')):
   self.assert_refused(self.fixture(lambda v:v.update(lab_policy=v['lab_policy'].replace(oldtext,newtext))),'GUARD',reason)
 def test_original_security_and_ctrr_are_explicit_guards(self):
  self.assert_refused(self.fixture(lambda v:v.update(original_policy=old.policy('Full',ctrr='disabled',paired=False))),'GUARD','ORIGINAL_CTRR_GUARD')
  self.assert_refused(self.fixture(lambda v:v.update(original_policy=v['original_policy'].replace('Security Mode: Full','Security Mode: Reduced'))),'GUARD','ORIGINAL_SECURITY_GUARD')
 def test_known_metadata_guard_and_format_labels_distinguish_fields(self):
  cases=(('lab_info','Internal',False,'GUARD','LAB_INTERNAL_TRUE'),('original_info','MountPoint','SECRET_MOUNT','GUARD','ORIGINAL_MOUNT'),('lab_info','APFSVolumeGroupID','SECRET_GROUP','FORMAT','LAB_GROUP_FORMAT'),('data_info','APFSVolumeGroupID',old.uuid(99),'GUARD','DATA_GROUP_MATCH'),('preboot_info','MountPoint',4,'FORMAT','PREBOOT_MOUNT_FORMAT'))
  for source,key,val,kind,reason in cases:self.assert_refused(self.fixture(lambda v:v[source].update({key:val})),kind,reason)
 def test_shared_groups_and_wrong_roles_still_refuse(self):
  self.assert_refused(self.fixture(lambda v:v['original_info'].update(APFSVolumeGroupID=v['lab_info']['APFSVolumeGroupID'])),'GUARD','DISTINCT_GROUPS')
  self.assert_refused(self.fixture(lambda v:v['apfs_list']['Containers'][0]['Volumes'][0].update(Roles=['Data'])),'GUARD','LAB_SYSTEM_MATCH')
 def test_missing_duplicate_malformed_semantic_policy_fields_are_distinct(self):
  cases=(lambda p:p.replace('(sip0): 0\n',''),lambda p:p+'(sip0): 0\n',lambda p:p.replace('(sip0): 0','(sip0): SECRET_VALUE'))
  for change,reason in zip(cases,('SEMANTIC_SIP0_MISSING','SEMANTIC_SIP0_DUPLICATE','SEMANTIC_SIP0_MALFORMED')):
   d=self.assert_refused(self.fixture(lambda v:v.update(lab_policy=change(v['lab_policy']))),'FORMAT',reason);self.assertEqual(d['stage'],'LAB_POLICY');self.assertNotIn('SECRET',json.dumps(d))
 def test_metadata_cardinality_malformed_and_unknown_are_finite(self):
  cases=(lambda p:p.replace('(rpnh): '+'d'*96+'\n',''),lambda p:p.replace('(ronh): '+'f'*96,'(ronh): SECRET'),lambda p:p+'(SECRET_UNKNOWN_TAG): SECRET_VALUE\n')
  for change,reason in zip(cases,('RPNH_CARDINALITY','RONH_MALFORMED','MALFORMED_TAGS')):
   self.assert_refused(self.fixture(lambda v:v.update(lab_policy=change(v['lab_policy']))),'FORMAT',reason)
  d=self.assert_refused(self.fixture(lambda v:v.update(lab_policy=v['lab_policy']+'(zzzz): SECRET_VALUE\n')),'FORMAT','UNSUPPORTED_METADATA');self.assertNotIn('zzzz',json.dumps(d));self.assertNotIn('SECRET',json.dumps(d))
 def test_policy_contradiction_and_reread_drift_are_consistency(self):
  self.assert_refused(self.fixture(lambda v:v.update(lab_policy=v['lab_policy'].replace('(sip2): absent','(sip2): 1'))),'CONSISTENCY','POLICY_CONTRADICTION')
  self.assert_refused(self.fixture(lambda v:v.update(lab_policy_after=v['lab_policy'].replace('(sip0): 0','(sip0): 1'))),'CONSISTENCY','POLICY_CHANGED')
 def test_snapshot_does_not_emit_identifiers_private_paths_or_policy_values(self):
  d=self.assert_refused(self.fixture(lambda v:v.update(extra_secret='SECRET_METADATA_AND_PATH')),'GUARD','INITIAL_ADMISSION_GUARD',True)
  text=json.dumps(d)
  for secret in ('SECRET',old.uuid(11),str(self.scratch),'d'*96,'Full','Permissive','selected_payload','profile_sha256'):self.assertNotIn(secret,text)
 def test_own_child_nonzero_exit_and_stdout_count_without_output(self):
  r=subprocess.run([str(self.harness),'child'],text=True,capture_output=True,timeout=10);d=json.loads(r.stdout);self.assertEqual(r.returncode,2);self.assertEqual(d['failure_kind'],'CAPTURE');self.assertEqual(d['reason'],'CAPTURE_EXIT');self.assertEqual(d['command_exit'],7);self.assertEqual(d['stdout_bytes'],len('SYNTHETIC_SECRET_MUST_NOT_ESCAPE'));self.assertNotIn('SECRET',r.stdout);self.assertEqual(r.stderr,'')
 def test_first_capture_failure_keeps_exit_and_count_after_later_success(self):
  r=subprocess.run([str(self.harness),'sequence'],text=True,capture_output=True,timeout=10);d=json.loads(r.stdout);self.assertEqual(r.returncode,2);self.assertEqual(d['reason'],'CAPTURE_EXIT');self.assertEqual(d['command_exit'],7);self.assertEqual(d['stdout_bytes'],len('SYNTHETIC_SECRET_MUST_NOT_ESCAPE'));self.assertEqual(d['stage'],'LAB_INFO')
 def test_own_child_stdout_bound_is_observation_only(self):
  r=subprocess.run([str(self.harness),'boundchild'],text=True,capture_output=True,timeout=10);d=json.loads(r.stdout);self.assertEqual(r.returncode,2);self.assertEqual(d['reason'],'CAPTURE_BOUND');self.assertEqual(d['stdout_bytes'],9);self.assertFalse(d['snapshot_collected'])
 def test_original_initial_admission_validator_pass_control(self):
  r=subprocess.run([str(self.harness),'admission'],text=True,capture_output=True,timeout=10);d=json.loads(r.stdout);self.assertEqual(r.returncode,0);self.assertTrue(d['initial_admission_valid']);self.assertEqual(d['status'],'INITIAL_ADMISSION_PASS');self.assertEqual(self.validate(d)[0].returncode,0)
 def test_validator_reprints_only_exact_allowlisted_refusal(self):
  value=self.record();r,d=self.validate(value);self.assertEqual(r.returncode,0);self.assertEqual(d,value)
  r,d=self.fixture();r2,d2=self.validate(d);self.assertEqual(r2.returncode,0);self.assertEqual(d,d2)
 def test_validator_unknown_keys_enums_and_secret_values_never_echo(self):
  for field,val in (('secret','SECRET_VALUE'),('stage','SECRET_VALUE'),('scope','SECRET_VALUE'),('reason','SECRET_VALUE'),('command','SECRET_VALUE')):
   value=self.record();value[field]=val;r,d=self.validate(value);self.assertEqual(r.returncode,2);self.assertNotIn('SECRET',json.dumps(d));self.assertEqual(d['reason'],'DIAGNOSTIC_FORMAT')
 def test_validator_requires_exact_boolean_null_number_types_and_bounds(self):
  for field,val in (('read_only',1),('writes_authorized',0),('stdout_bytes',True),('stdout_bytes',1048578),('command_exit',True),('command_exit',256),('command_exit',-1),('native_ready',True)):
   value=self.record();value[field]=val;self.assertEqual(self.validate(value)[0].returncode,2)
 def test_validator_rejects_inconsistent_kind_status_and_collection(self):
  for edits in ({'failure_kind':'CAPTURE'},{'initial_admission_valid':True},{'status':'INITIAL_ADMISSION_PASS'},{'snapshot_collected':True},{'reason':'CAPTURE_EXIT','failure_kind':'CAPTURE','command_exit':0}):
   value=self.record();value.update(edits);self.assertEqual(self.validate(value)[0].returncode,2)
 def test_validator_duplicate_keys_deep_json_and_oversize_refused(self):
  path=self.scratch/'bad.json'
  for data in ('{"schema":1,"schema":2}','{"a":'*20+'0'+'}'*20,'x'*8193):
   path.write_text(data);r,d=self.invoke('--validate-diagnostic',path);self.assertEqual(r.returncode,2);self.assertEqual(d['reason'],'DIAGNOSTIC_FORMAT')
 def test_validator_file_symlink_and_system_alias_fixture_remain_refused(self):
  path=self.scratch/'safe.json';path.write_text(json.dumps(self.record()));link=self.scratch/'alias.json';link.symlink_to(path);r,_=self.invoke('--validate-diagnostic',link);self.assertEqual(r.returncode,2)
  alias=self.scratch/'private';alias.symlink_to(self.scratch,target_is_directory=True);r,_=self.invoke('--validate-diagnostic',alias/'safe.json');self.assertEqual(r.returncode,2)

if __name__=='__main__':unittest.main(verbosity=2)
