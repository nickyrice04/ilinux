#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original SDK/CF/filesystem controls; never dispatch production live modes."""
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

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SANITIZE = '--sanitize' in sys.argv
if SANITIZE: sys.argv.remove('--sanitize')
spec = importlib.util.spec_from_file_location('frozen31aj_metadata', ROOT/'tools/boot-object31aj-native/test_native.py')
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
def sha(data): return hashlib.sha256(data).hexdigest()

OVERLAY_HARNESS = r'''#include "preboot.h"
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <string.h>
#include <stdio.h>
static int old_child=-1,observed_fd=-1;static bool observed_closed=false;static struct stat original_child;static const char *mount_name;static const char *test_source="/dev/disk9s3";
static int overlay_fstat(int fd,struct stat *out){int rc=fstat(fd,out);if(!rc&&fd!=old_child&&out->st_dev==original_child.st_dev&&out->st_ino==original_child.st_ino){out->st_dev=(dev_t)111;out->st_ino=(ino_t)222;}return rc;}
static int overlay_fstatat(int fd,const char *name,struct stat *out,int flags){int rc=fstatat(fd,name,out,flags);if(!rc&&!strcmp(name,"preboot")){out->st_dev=(dev_t)111;out->st_ino=(ino_t)222;}return rc;}
static int overlay_fstatfs(int fd,struct statfs *out){observed_fd=fd;memset(out,0,sizeof(*out));strcpy(out->f_mntonname,mount_name);strcpy(out->f_mntfromname,test_source);strcpy(out->f_fstypename,"apfs");out->f_flags=MNT_RDONLY;return 0;}
static int overlay_close(int fd){if(fd==observed_fd)observed_closed=true;return close(fd);}
#define fstat overlay_fstat
#define fstatat overlay_fstatat
#define fstatfs overlay_fstatfs
#define close overlay_close
#include "preboot.c"
#undef fstat
#undef fstatat
#undef fstatfs
#undef close
int main(int argc,char **argv){
 if(argc!=3)return 2;PBScratch scratch={.fd=-1,.child_fd=-1};
 if(!scratch_open(&scratch,argv[1],true)||mkdirat(scratch.fd,"preboot",0700))return 2;
 scratch.child_created=true;scratch.child_fd=openat(scratch.fd,"preboot",O_RDONLY|O_DIRECTORY|O_NOFOLLOW);old_child=scratch.child_fd;
 if(old_child<0||fstat(old_child,&original_child))return 2;scratch.child=original_child;mount_name=scratch.mount;test_source=argv[2];
 PBContext context={0};PBMetadata metadata={.mounted=true};strcpy(metadata.mount,scratch.mount);strcpy(metadata.identity.preboot_device,"disk9s3");bool readonly=false;
 bool accepted=mount_binding(&context,&scratch,&metadata,true,&readonly);
 printf("{\"accepted\":%s,\"read_only\":%s,\"fresh_fd\":%s,\"fresh_fd_closed\":%s}\n",accepted?"true":"false",readonly?"true":"false",observed_fd>=0&&observed_fd!=old_child?"true":"false",observed_closed?"true":"false");
 close(old_child);unlinkat(scratch.fd,"preboot",AT_REMOVEDIR);close(scratch.fd);return 0;
}'''

class ConditionalPreboot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = ROOT/'build/boot-object31am-native/tests'; base.mkdir(parents=True, exist_ok=True)
        cls.directory = Path(tempfile.mkdtemp(prefix='synthetic-', dir=base)).resolve()
        cls.plain = bytes((i*17^(i>>4))&255 for i in range(65536))
        definition = {'schema':'ilinux31aj-compiled-candidate-v1','target':{'model':'Mac17,6','board':'j716c','chip_id':'0x6050'},'bytes':len(cls.plain),'sha256':sha(cls.plain),'publication_authorizes_writes':False}
        path = cls.directory/'definition.json'; path.write_text(json.dumps(definition))
        command = [sys.executable,'-I',str(HERE/'build.py'),'--output',str(cls.directory/'compiled'),'--candidate-definition',str(path)]
        if SANITIZE: command.append('--sanitize')
        r = subprocess.run(command, capture_output=True, text=True, timeout=45)
        if r.returncode: raise RuntimeError(r.stdout+r.stderr)
        cls.binary = cls.directory/'compiled/ilinux31aj-reader'
        cls.profile = {'schema':'ilinux31aj-recovery-profile-v1','target':definition['target'],'files':{'candidate':{'name':'candidate.macho','bytes':len(cls.plain),'sha256':sha(cls.plain)},'helper':{'name':'ilinux31aj-reader','bytes':cls.binary.stat().st_size,'sha256':sha(cls.binary.read_bytes())},'rollback':{'name':'m1n1-boot021.bin','bytes':3932160,'sha256':'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'}},'native_deadline_ms':90000,'raw_policy_strategy':'ctrr_only','initial_payload':'31AF','final_payload':'BOOT021','publication_authorizes_writes':False}
        cls.profile_path = cls.directory/'profile.json'; cls.profile_path.write_text(json.dumps(cls.profile))
        cls.build = json.loads((cls.directory/'compiled/build-result.json').read_bytes())
        source = cls.directory/'compiled/sources'
        (source/'source-harness.c').write_text('#include "preboot.c"\n#include <stdio.h>\nint main(int argc,char **argv){if(argc!=3)return 2;if(!strcmp(argv[1],"__invalid")||!strcmp(argv[1],"__invalid_complete")){PBResult r;pb_reset(&r,true);r.attempted=true;r.complete=!strcmp(argv[1],"__invalid_complete");bool v=pb_print(&r);return r.complete?(v?0:2):0;}printf("%s\\n",source_matches(argv[1],argv[2])?"true":"false");return 0;}\n')
        cls.harness = cls.directory/'source-harness'
        command = ['/usr/bin/xcrun','clang','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-arch','arm64','-DWORKSPACE_ROOT='+json.dumps(str(ROOT)),'-DCANDIDATE_BYTES='+str(len(cls.plain)),'-DCANDIDATE_SHA256='+json.dumps(sha(cls.plain))]
        if SANITIZE: command += ['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        command += [str(source/n) for n in ('core.c','json.c','result.c','source-harness.c')] + ['-framework','CoreFoundation','-lcompression','-o',str(cls.harness)]
        r = subprocess.run(command, capture_output=True, text=True, timeout=45)
        if r.returncode: raise RuntimeError(r.stdout+r.stderr)
        (source/'overlay-harness.c').write_text(OVERLAY_HARNESS)
        cls.overlay = cls.directory/'overlay-harness'
        command[-1]=str(cls.overlay)
        command[command.index(str(source/'source-harness.c'))]=str(source/'overlay-harness.c')
        r=subprocess.run(command,capture_output=True,text=True,timeout=45)
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.directory)
    def setUp(self):
        self.case = Path(tempfile.mkdtemp(prefix='case-',dir=self.directory)); self.addCleanup(shutil.rmtree,self.case)
        self.scratch = self.case/'ilinux31am.ABC123'; self.scratch.mkdir(mode=0o700)
        selected = self.case/'selected.bin'; selected.write_bytes(self.plain)
        self.value = old.metadata(selected)
        before = copy.deepcopy(self.value); before['preboot_info']['MountPoint']=''; before['kernel_mounted']=False
        after = copy.deepcopy(self.value); after['preboot_info']['MountPoint']=str(self.scratch/'preboot'); after['kernel_mounted']=True
        final = copy.deepcopy(before)
        self.value['preboot_info']['MountPoint']=str(self.scratch/'preboot')
        self.value.update(preflight_before=before,preflight_before_again=copy.deepcopy(before),preflight_after=after,preflight_cleanup=copy.deepcopy(after),preflight_final=final)
    def invoke(self,*args,profile=True):
        command = [str(self.binary),*map(str,args)]
        if profile: command += ['--profile',str(self.profile_path)]
        r = subprocess.run(command,capture_output=True,text=True,timeout=15)
        self.assertEqual(r.stderr,'')
        return r,json.loads(r.stdout) if r.stdout.startswith('{') else r.stdout
    def run_fixture(self):
        path = self.case/'fixture.plist'; path.write_bytes(plistlib.dumps(self.value))
        return self.invoke('--diagnose-fixture',path,'--scratch',self.scratch)
    def validate(self,value):
        path=self.case/'result.json';path.write_text(json.dumps(value));return self.invoke('--validate-result',path)
    def assert_safe(self,result,reason=None):
        r,value=result;self.assertEqual(r.returncode,2,value);self.assertEqual(value['status'],'REFUSED')
        for key in ('preboot_write_requested','boot_object_installed','security_settings_changed','native_ready','identifiers_returned','policy_values_returned'): self.assertIs(value[key],False)
        if reason: self.assertEqual(value['reason'],reason,value)
        self.assertNotIn('SYNTHETIC_PRIVATE',r.stdout)
        return value
    def already_mounted(self):
        for phase in ('preflight_before','preflight_before_again'):
            self.value[phase]['preboot_info']['MountPoint']='/Volumes/Preboot';self.value[phase]['kernel_mounted']=True
        self.value['preboot_info']['MountPoint']='/Volumes/Preboot'
    def test_default_help_inert_and_no_write_modes(self):
        for args in ((),('--help',)):
            r,out=self.invoke(*args,profile=False);self.assertEqual(r.returncode,0);self.assertIn('inert',out)
        for flag in ('--install','--restore','--repair','--force','--snapshot','--target-group-private'):
            self.assert_safe(self.invoke(flag,profile=False),'ARGUMENTS')
    def test_profile_hash_and_extra_fields_refuse_before_fixture(self):
        value=copy.deepcopy(self.profile);value['files']['helper']['sha256']='a'*64
        p=self.case/'bad-profile.json';p.write_text(json.dumps(value))
        self.assert_safe(self.invoke('--diagnose-fixture','absent','--scratch',self.scratch,'--profile',p,profile=False),'PROFILE_BINDING')
    def test_absent_mounted_key_with_kernel_absence_prepares_and_cleans(self):
        result=self.assert_safe(self.run_fixture(),'DIAGNOSTIC_REFUSED')
        self.assertEqual(result['initial_state'],'UNMOUNTED_EMPTY');self.assertTrue(result['mount_attempted']);self.assertTrue(result['mount_created']);self.assertTrue(result['mount_read_only_verified']);self.assertEqual(result['cleanup'],'UNMOUNTED');self.assertEqual(result['unmount_exit'],0)
        self.assertIsNotNone(result['diagnostic']);self.assertFalse((self.scratch/'preboot').exists())
        rc,loaded=self.validate(result);self.assertEqual(rc.returncode,0);self.assertEqual(loaded,result)
    def test_existing_valid_mount_left_untouched(self):
        self.already_mounted();result=self.assert_safe(self.run_fixture(),'DIAGNOSTIC_REFUSED')
        self.assertEqual(result['initial_state'],'MOUNTED_VALID');self.assertFalse(result['mount_attempted']);self.assertEqual(result['cleanup'],'NOT_NEEDED');self.assertIsNone(result['unmount_exit']);self.assertFalse((self.scratch/'preboot').exists())
    def test_absence_of_kernel_proof_is_not_inferred_unmounted(self):
        self.value['preflight_before'].pop('kernel_mounted')
        result=self.assert_safe(self.run_fixture(),'KERNEL_MOUNT_STATE');self.assertFalse(result['mount_attempted'])
    def test_optional_mounted_type_and_contradiction_refuse(self):
        for value,reason in ((4,'MOUNTED_FIELD'),(True,'STATE_CONTRADICTION')):
            with self.subTest(value=value):
                self.value['preflight_before']['preboot_info']['Mounted']=value
                result=self.assert_safe(self.run_fixture(),reason);self.assertFalse(result['mount_attempted'])
    def test_unsafe_existing_paths_stop_without_mount(self):
        self.already_mounted()
        for path in ('','/','relative','/Volumes/../Preboot','/Volumes/Preboot/'):
            with self.subTest(path=path):
                self.value['preflight_before']['preboot_info']['MountPoint']=path
                result=self.assert_safe(self.run_fixture(),'PATH_UNSAFE');self.assertFalse(result['mount_attempted'])
    def test_unmounted_nonempty_path_is_inconsistent(self):
        self.value['preflight_before']['preboot_info']['MountPoint']='/Volumes/Preboot'
        result=self.assert_safe(self.run_fixture(),'STATE_CONTRADICTION');self.assertFalse(result['mount_attempted'])
    def test_second_identity_change_prevents_mount(self):
        info=self.value['preflight_before_again'];u=old.uuid(77);info['preboot_info']['VolumeUUID']=u;info['apfs_list']['Containers'][0]['Volumes'][2]['APFSVolumeUUID']=u
        result=self.assert_safe(self.run_fixture(),'IDENTITY_CHANGED');self.assertFalse(result['mount_attempted'])
    def test_missing_or_nonstr_path_does_not_mount(self):
        self.value['preflight_before']['preboot_info'].pop('MountPoint')
        self.assert_safe(self.run_fixture(),'PATH_FORMAT')
    def test_existing_child_never_overwritten(self):
        child=self.scratch/'preboot';child.mkdir();(child/'foreign').write_text('KEEP')
        result=self.assert_safe(self.run_fixture(),'CHILD_EXISTS');self.assertFalse(result['mount_attempted']);self.assertEqual((child/'foreign').read_text(),'KEEP')
    def test_bad_scratch_modes_and_alias_refuse(self):
        self.scratch.chmod(0o755);self.assert_safe(self.run_fixture(),'SCRATCH_BINDING');self.scratch.chmod(0o700)
        alias=self.case/'ilinux31am.LINK12';alias.symlink_to(self.scratch);self.scratch=alias
        self.assert_safe(self.run_fixture(),'SCRATCH_BINDING')
    def test_mount_error_with_no_mount_cleans_only_empty_owned_child(self):
        self.value['mount_exit']=7;self.value['preflight_after']=copy.deepcopy(self.value['preflight_before'])
        result=self.assert_safe(self.run_fixture(),'MOUNT_COMMAND');self.assertFalse(result['mount_created']);self.assertFalse(result['mount_state_uncertain']);self.assertEqual(result['cleanup'],'NOT_NEEDED');self.assertFalse((self.scratch/'preboot').exists());self.assertIsNone(result['diagnostic'])
    def test_nonzero_mount_can_still_create_mount_and_is_cleaned(self):
        self.value.update(mount_exit=7,partial_mount=True)
        result=self.assert_safe(self.run_fixture(),'MOUNT_COMMAND');self.assertTrue(result['mount_created']);self.assertEqual(result['cleanup'],'UNMOUNTED');self.assertIsNone(result['diagnostic']);self.assertFalse((self.scratch/'preboot').exists())
    def test_readonly_failure_refuses_unmount_of_unverified_rw_mount(self):
        self.value['read_only_after']=False
        result=self.assert_safe(self.run_fixture(),'NOT_READ_ONLY');self.assertTrue(result['mount_created']);self.assertFalse(result['mount_read_only_verified']);self.assertTrue(result['mount_state_uncertain']);self.assertEqual(result['cleanup'],'REFUSED');self.assertIsNone(result['diagnostic']);self.assertIsNone(result['unmount_exit']);self.assertTrue((self.scratch/'preboot').exists())
    def test_post_mount_identity_failure_retains_uncertain_state(self):
        self.value['preflight_after']['preboot_info']['VolumeUUID']=old.uuid(99)
        result=self.assert_safe(self.run_fixture());self.assertTrue(result['mount_state_uncertain']);self.assertEqual(result['cleanup'],'REFUSED');self.assertIsNone(result['diagnostic']);self.assertTrue((self.scratch/'preboot').exists())
    def test_unmount_failure_keeps_child_and_overrides_diagnostic_result(self):
        self.value['unmount_exit']=7
        self.value['preflight_final']=copy.deepcopy(self.value['preflight_after'])
        result=self.assert_safe(self.run_fixture(),'UNMOUNT_COMMAND');self.assertEqual(result['stage'],'CLEANUP');self.assertEqual(result['cleanup'],'FAILED');self.assertTrue((self.scratch/'preboot').exists())
    def test_nonzero_unmount_can_remove_mount_but_remains_refusal(self):
        self.value.update(unmount_exit=7,partial_unmount=True)
        result=self.assert_safe(self.run_fixture(),'UNMOUNT_COMMAND');self.assertEqual(result['stage'],'CLEANUP');self.assertEqual(result['cleanup'],'UNMOUNTED');self.assertFalse(result['mount_state_uncertain']);self.assertFalse((self.scratch/'preboot').exists())
    def test_cleanup_identity_change_refuses_unmount(self):
        self.value['preflight_cleanup']['preboot_info']['VolumeUUID']=old.uuid(98)
        result=self.assert_safe(self.run_fixture(),'CLEANUP_BINDING');self.assertIsNone(result['unmount_exit']);self.assertTrue(result['mount_state_uncertain']);self.assertTrue((self.scratch/'preboot').exists())
    def test_unmount_success_without_fresh_absence_is_not_cleanup_success(self):
        self.value['preflight_final']=copy.deepcopy(self.value['preflight_after'])
        result=self.assert_safe(self.run_fixture(),'UNMOUNT_NOT_OBSERVED');self.assertEqual(result['cleanup'],'REFUSED');self.assertTrue(result['mount_state_uncertain']);self.assertTrue((self.scratch/'preboot').exists())
    def test_policy_refusal_is_preserved_after_mount_and_cleanup(self):
        self.value['lab_policy']=self.value['lab_policy'].replace('(sip0): 0','(sip0): SYNTHETIC_PRIVATE_VALUE')
        result=self.assert_safe(self.run_fixture(),'DIAGNOSTIC_REFUSED');self.assertEqual(result['diagnostic']['reason'],'SEMANTIC_SIP0_MALFORMED');self.assertEqual(result['cleanup'],'UNMOUNTED')
    def test_validator_rejects_private_unknown_and_inconsistent_records(self):
        result=self.assert_safe(self.run_fixture())
        cases=[]
        d=copy.deepcopy(result);d['SYNTHETIC_PRIVATE_KEY']='SYNTHETIC_PRIVATE_VALUE';cases.append(d)
        d=copy.deepcopy(result);d['mount_created']=False;cases.append(d)
        d=copy.deepcopy(result);d['cleanup']='NOT_NEEDED';cases.append(d)
        d=copy.deepcopy(result);d['scope']='RECOVERY_CONDITIONAL_PREBOOT';cases.append(d)
        d=copy.deepcopy(result);d['diagnostic']['reason']='SYNTHETIC_PRIVATE_VALUE';cases.append(d)
        d=copy.deepcopy(result);d['stage']='CLI';cases.append(d)
        for value in cases:self.assert_safe(self.validate(value),'RESULT_FORMAT')
    def test_validator_refusal_pass_record_and_limits(self):
        result=self.assert_safe(self.run_fixture())
        result.update(status='DIAGNOSTIC_COMPLETE',stage='COMPLETE',reason='NONE')
        d=result['diagnostic'];d.update(status='INITIAL_ADMISSION_PASS',stage='INITIAL_ADMISSION',failure_kind='NONE',reason='NONE',command='NONE',command_exit=None,stdout_bytes=0,snapshot_collected=True,initial_admission_valid=True)
        r,loaded=self.validate(result);self.assertEqual(r.returncode,0);self.assertEqual(loaded,result)
        path=self.case/'oversized';path.write_bytes(b' '*8193);self.assert_safe(self.invoke('--validate-result',path),'RESULT_FORMAT')
        path=self.case/'duplicate';path.write_text('{"schema":"x","schema":"x"}');self.assert_safe(self.invoke('--validate-result',path),'RESULT_FORMAT')
    def test_validator_symlink_input_never_followed(self):
        target=self.case/'secret';target.write_text('SYNTHETIC_PRIVATE_VALUE');link=self.case/'alias';link.symlink_to(target)
        self.assert_safe(self.invoke('--validate-result',link),'RESULT_FORMAT')
    def test_kernel_source_normalization_and_snapshot_occupancy(self):
        cases=(('/dev/disk9s3',True),('/dev/rdisk9s3',True),('disk9s3',True),('com.apple.os.update-SYNTHETIC@/dev/disk9s3s1',True),('/dev/disk9s31',False),('/dev/disk9s4',False),('SYNTHETIC_PRIVATE',False))
        for source,expected in cases:
            r=subprocess.run([str(self.harness),source,'disk9s3'],capture_output=True,text=True,timeout=5);self.assertEqual(r.returncode,0);self.assertEqual(r.stderr,'');self.assertEqual(r.stdout.strip()=='true',expected)
    def test_real_mount_binding_uses_new_overlay_fd_and_closes_before_unmount(self):
        for source,expected in (('/dev/disk9s3',True),('/dev/rdisk9s3',True),('/dev/disk9s3s1',False),('/dev/disk9s4',False)):
            r=subprocess.run([str(self.overlay),str(self.scratch),source],capture_output=True,text=True,timeout=5)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stderr,'');result=json.loads(r.stdout)
            self.assertEqual(result['accepted'],expected);self.assertTrue(result['fresh_fd']);self.assertTrue(result['fresh_fd_closed']);self.assertEqual(result['read_only'],expected)
    def test_internal_invariant_fallback_never_hides_possible_mount(self):
        r=subprocess.run([str(self.harness),'__invalid','unused'],capture_output=True,text=True,timeout=5)
        self.assertEqual(r.returncode,0);self.assertEqual(r.stderr,'');value=json.loads(r.stdout)
        self.assertEqual(value['stage'],'VALIDATION');self.assertEqual(value['reason'],'RESULT_FORMAT');self.assertTrue(value['mount_attempted']);self.assertTrue(value['mount_state_uncertain']);self.assertEqual(value['cleanup'],'REFUSED')
        validated,loaded=self.validate(value);self.assertEqual(validated.returncode,0);self.assertEqual(loaded,value)
        r=subprocess.run([str(self.harness),'__invalid_complete','unused'],capture_output=True,text=True,timeout=5)
        self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['status'],'REFUSED');self.assertEqual(r.stderr,'')
    def test_frozen_sources_and_unchanged_collector_proof(self):
        proof=self.build['guard_preservation'];self.assertTrue(proof['state_marks_strip_exact']);self.assertTrue(proof['core_json_reader_byte_identical'])
        for name,digest in self.build['frozen_inputs'].items():self.assertEqual(sha((ROOT/name).read_bytes()),digest)

if __name__ == '__main__': unittest.main(verbosity=2)
