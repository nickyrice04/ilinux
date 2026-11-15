#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Controller integration with genuine own artifacts and synthetic OS backends.

No live Recovery, diskutil, mount, policy or Apple writer is dispatched. The
separate PTY harness exercises the same child handoff with a harmless own script.
"""
import argparse
import copy
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BINARY = OUTPUT = REFERENCE = CANDIDATE = ROLLBACK = None
SANITIZE = False


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def clone(source, destination):
    api = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    api.clonefile.argtypes = [ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]
    api.clonefile.restype = ctypes.c_int
    if api.clonefile(os.fsencode(source),os.fsencode(destination),0):
        raise OSError(ctypes.get_errno(), 'workspace clone failed')


class Controller(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if OUTPUT.exists() or ROOT/'build' not in OUTPUT.parents:
            raise ValueError('fresh workspace output required')
        OUTPUT.mkdir(parents=True,mode=0o700)
        cls.old = load('old_metadata_ar', ROOT/'tools/boot-object31aj-native/test_native.py')
        cls.aq = load('aq_for_ar_tests', ROOT/'tools/boot-object31aq-native/build.py')
        cls.before = {str(p): (sha(p),p.stat().st_size) for p in (REFERENCE,CANDIDATE,ROLLBACK)}
        cls.build = json.loads((BINARY.parent/'build-result.json').read_text())
        cls.profile = {'schema':'ilinux31aj-recovery-profile-v1',
          'target':cls.aq.CANDIDATE['target'],
          'files':{'candidate':{'name':'candidate.macho','bytes':153190400,'sha256':cls.aq.CANDIDATE['sha256']},
                   'rollback':{'name':'m1n1-boot021.bin','bytes':3932160,'sha256':cls.before[str(ROLLBACK)][0]},
                   'helper':{'name':'ilinux31aj-reader','bytes':BINARY.stat().st_size,'sha256':sha(BINARY)}},
          'native_deadline_ms':90000,'raw_policy_strategy':'ctrr_only','initial_payload':'31AF',
          'final_payload':'BOOT021','publication_authorizes_writes':False}

    @classmethod
    def tearDownClass(cls):
        for p in (REFERENCE,CANDIDATE,ROLLBACK):
            if cls.before[str(p)] != (sha(p),p.stat().st_size):
                raise AssertionError('existing own artifact changed')

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(prefix='transaction-',dir=OUTPUT)).resolve()
        self.addCleanup(shutil.rmtree,self.case)
        self.parent = self.case/'private-state-parent';self.parent.mkdir(mode=0o700)
        self.work = self.case/'ilinux31ar.ABCDEF';self.work.mkdir(mode=0o700)
        self.state = self.parent/'ilinux31ar-state'
        self.profile_path = self.work/'profile.json'
        self.profile_path.write_text(json.dumps(self.profile,sort_keys=True,indent=2)+'\n')
        for source,name in ((BINARY,'ilinux31aj-reader'),(CANDIDATE,'candidate.macho'),(ROLLBACK,'m1n1-boot021.bin')):
            clone(source,self.work/name)
        self.fixture = {'recovery':True,'root':True,'model':'Mac17,6','state_parent':str(self.parent),'phases':{}}
        self.metadata = {}
        for name,selected,ctrr in (
            ('initial',REFERENCE,'disabled'),('prewrite',REFERENCE,'disabled'),
            ('candidate',CANDIDATE,'enabled'),('before-restore',CANDIDATE,'enabled'),
            ('raw-policy',CANDIDATE,'disabled'),('restored',ROLLBACK,'disabled')):
            value = self.old.metadata(selected)
            value['apfs_list']['Containers'][0]['APFSContainerUUID'] = self.old.uuid(77)
            value['lab_policy'] = self.policy('Permissive',ctrr)
            value['original_policy'] = self.policy('Full','enabled',False)
            self.metadata[name] = value
            self.fixture['phases'][name] = str(self.case/(name+'.plist'))
        self.fixture_path = self.case/'transaction.plist'

    def policy(self, mode, ctrr, paired=True):
        value = self.old.policy(mode,ctrr,paired)
        if mode=='Permissive':
            value = value.replace('(smb0, smb1): 1','(smb0 && smb1): TRUE')
        return value+''.join('('+tag+'): '+v+'\n' for tag,v in
            {'CEPO':'0x1','SDOM':'0x1','CPRO':'1','CSEC':'1','lobo':'1','love':'26.1.0.1.2,3'}.items())

    def invoke(self, operation='install'):
        for name,value in self.metadata.items():
            Path(self.fixture['phases'].get(name,self.case/(name+'.plist'))).write_bytes(plistlib.dumps(value))
        self.fixture_path.write_bytes(plistlib.dumps(self.fixture))
        completed = subprocess.run([str(self.work/'ilinux31aj-reader'),'--transaction',operation,
            '--profile',str(self.profile_path),'--scratch',str(self.work),
            '--transaction-fixture',str(self.fixture_path)], cwd=self.work,
            capture_output=True,text=True,timeout=30)
        self.assertEqual(completed.stderr,'')
        result = json.loads(completed.stdout)
        self.assertTrue(result['synthetic'])
        for key in ('native_ready','restart_performed','default_changed','identifiers_returned','policy_values_returned'):
            self.assertFalse(result[key])
        self.assertNotIn('PRIVATE_SENTINEL',completed.stdout)
        return completed.returncode,result

    def installed(self):
        code,value = self.invoke()
        self.assertEqual((code,value['status']),(0,'INSTALL_COMPLETE'),value)
        self.assertTrue(value['candidate_verified'])
        self.assertTrue(value['cleanup_verified'])
        self.assertTrue((self.state/'candidate-attempt').exists())
        return value

    def test_complete_real_artifact_install_and_conditional_restore(self):
        self.installed()
        (self.work/'candidate.macho').unlink()
        code,result = self.invoke('restore')
        self.assertEqual((code,result['status']),(0,'RESTORE_COMPLETE'),result)
        self.assertTrue(result['rollback_verified'])
        self.assertTrue(result['cleanup_verified'])
        self.assertTrue((self.state/'ctrr-attempt').exists())
        self.assertTrue((self.state/'boot021-attempt').exists())
        self.assertEqual((self.state/'comparison.key').stat().st_size,32)
        self.assertEqual((self.state/'comparison.key').stat().st_mode&0o7777,0o600)
        self.assertEqual((self.state/'target.hmac').stat().st_size,64)

    def test_restore_already_exact_is_read_only_and_idempotent(self):
        self.installed()
        self.metadata['before-restore'] = copy.deepcopy(self.metadata['restored'])
        for _ in range(2):
            code,result = self.invoke('restore')
            self.assertEqual(code,0,result)
            self.assertFalse(result['mutation_attempted'])
            self.assertTrue(result['rollback_verified'])
        self.assertFalse((self.state/'ctrr-attempt').exists())
        self.assertFalse((self.state/'boot021-attempt').exists())

    def test_disabled_ctrr_skips_policy_writer(self):
        self.installed()
        self.metadata['before-restore'] = copy.deepcopy(self.metadata['raw-policy'])
        code,result = self.invoke('restore')
        self.assertEqual(code,0,result)
        self.assertFalse((self.state/'ctrr-attempt').exists())
        self.assertTrue((self.state/'boot021-attempt').exists())

    def test_fresh_state_is_never_adopted_or_reset(self):
        self.installed()
        original = (self.state/'comparison.key').read_bytes()
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertFalse(result['mutation_attempted'])
        self.assertEqual((self.state/'comparison.key').read_bytes(),original)

    def test_foreign_mount_is_refused_without_cleanup(self):
        for readonly in (False,True):
            self.fixture.update(foreign_mount=True,foreign_read_only=readonly)
            code,result = self.invoke()
            self.assertEqual(code,2)
            self.assertEqual(result['reason'],'FOREIGN_MOUNT')
            self.assertFalse(result['mutation_attempted'])
            self.assertFalse(self.state.exists())

    def test_rw_request_must_clear_actual_readonly_bit(self):
        self.fixture['rw_stays_readonly'] = True
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertEqual(result['stage'],'MOUNT_RW')
        self.assertFalse(result['mutation_attempted'])
        self.assertTrue(result['cleanup_verified'])

    def test_nonzero_writer_still_records_readback_and_spends_marker(self):
        self.fixture['candidate_exit'] = 71
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertEqual(result['writer_exit'],71)
        self.assertTrue((self.state/'candidate.json').exists())
        self.assertTrue((self.state/'candidate-attempt').exists())
        self.assertTrue(result['cleanup_verified'])
        # Independent rollback can inspect and restore despite candidate failure.
        self.fixture.pop('candidate_exit')
        self.assertEqual(self.invoke('restore')[0],0)

    def test_timeout_and_interruption_retain_readback_and_spent_state(self):
        for point in ('writer_timeout','writer_interrupt'):
            with self.subTest(point=point):
                # Separate transaction directories for independently spent cases.
                self.fixture['failpoint'] = point
                code,result = self.invoke()
                self.assertEqual(code,2)
                self.assertTrue(result['mutation_attempted'])
                self.assertTrue((self.state/'candidate-attempt').exists())
                self.assertTrue((self.state/'candidate.json').exists())
                self.assertTrue(result['cleanup_verified'])
                shutil.rmtree(self.state)

    def test_every_durability_failure_prevents_writer(self):
        for point in ('state_parent_sync','key_sync','profile_sync','target_sync','snapshot_sync','enrolled_sync','marker_sync'):
            with self.subTest(point=point):
                self.fixture['failpoint'] = point
                code,result = self.invoke()
                self.assertEqual(code,2)
                self.assertFalse(result['mutation_attempted'])
                self.assertTrue(self.state.exists())
                shutil.rmtree(self.state)

    def test_failed_marker_remains_spent_and_writer_cannot_retry(self):
        self.fixture['failpoint'] = 'marker_sync'
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertTrue((self.state/'candidate-attempt').exists())
        self.fixture.pop('failpoint')
        self.assertEqual(self.invoke()[0],2)

    def test_changed_original_policy_refuses_postcondition(self):
        self.metadata['candidate']['original_policy'] = self.metadata['candidate']['original_policy'].replace('(stng): 7','(stng): 8')
        # Synthetic fixture's canonical counter may differ; force a known field.
        self.metadata['candidate']['original_policy'] = self.metadata['candidate']['original_policy'].replace('(lobo): 1','(lobo): 0')
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertEqual(result['stage'],'POSTCONDITION')
        self.assertTrue((self.state/'candidate.json').exists())

    def test_prewrite_policy_change_spends_no_writer(self):
        self.metadata['prewrite']['lab_policy'] = self.metadata['prewrite']['lab_policy'].replace('(love): 26.1.0.1.2,3','(love): 26.1.0.1.2,4')
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertFalse(result['mutation_attempted'])
        self.assertFalse((self.state/'candidate-attempt').exists())

    def test_cross_visit_stable_container_change_refuses_restore(self):
        self.installed()
        self.metadata['before-restore']['apfs_list']['Containers'][0]['APFSContainerUUID'] = self.old.uuid(78)
        code,result = self.invoke('restore')
        self.assertEqual(code,2)
        self.assertEqual(result['reason'],'STATE_OR_TARGET_COMMITMENT')
        self.assertFalse(result['mutation_attempted'])

    def test_identity_changes_across_ro_rw_release_are_refused(self):
        self.metadata['prewrite']['apfs_list']['Containers'][0]['APFSContainerUUID'] = self.old.uuid(78)
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertFalse(result['mutation_attempted'])

    def test_missing_post_phase_never_falls_back_to_live_backend(self):
        self.fixture['phases'].pop('candidate')
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertEqual(result['stage'],'CLEANUP')
        self.assertFalse(result['cleanup_verified'])
        self.assertTrue((self.state/'candidate-attempt').exists())

    def test_unmount_failure_blocks_readiness(self):
        self.fixture['unmount_exit'] = 1
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertFalse(result['cleanup_verified'])
        self.assertFalse(result['candidate_verified'])

    def test_partial_mount_and_incorrect_mount_binding_refuse_writer(self):
        for settings in ({'mount_ro_exit':1,'partial_mount':True},
                         {'mount_rw_exit':1,'partial_mount':True},
                         {'failpoint':'mount_binding'}):
            with self.subTest(settings=settings):
                self.fixture.update(settings)
                code,result=self.invoke()
                self.assertEqual(code,2)
                self.assertFalse(result['mutation_attempted'])
                if self.state.exists():shutil.rmtree(self.state)
                if (self.work/'preboot').exists():(self.work/'preboot').rmdir()
                for key in settings:self.fixture.pop(key)

    def test_unavailable_post_readback_blocks_readiness_and_keeps_spent_marker(self):
        self.metadata['candidate']['lab_policy']='UNSUPPORTED_PRIVATE_SENTINEL'
        code,result=self.invoke()
        self.assertEqual(code,2)
        self.assertTrue((self.state/'candidate-attempt').exists())
        self.assertFalse((self.state/'candidate.json').exists())
        self.assertEqual(result['stage'],'READBACK')

    def test_failed_rollback_is_not_repeated_and_candidate_is_not_needed(self):
        self.installed()
        (self.work/'candidate.macho').unlink()
        self.fixture['boot021_exit']=71
        code,result=self.invoke('restore')
        self.assertEqual(code,2)
        self.assertTrue((self.state/'boot021-attempt').exists())
        self.assertTrue((self.state/'restored.json').exists())
        self.fixture.pop('boot021_exit')
        # Current fixture says candidate remains selected, so this would require
        # another raw writer and must stop on the retained spent marker.
        code,result=self.invoke('restore')
        self.assertEqual(code,2)
        self.assertFalse(result['mutation_attempted'])

    def test_restore_refuses_tampered_profile_key_and_target_commitment(self):
        self.installed()
        for name in ('profile.json','comparison.key','target.hmac'):
            path=self.state/name;before=path.read_bytes()
            changed=bytearray(before);changed[0]^=1;path.write_bytes(changed);path.chmod(0o600)
            code,result=self.invoke('restore')
            self.assertEqual(code,2)
            self.assertFalse(result['mutation_attempted'])
            path.write_bytes(before);path.chmod(0o600)

    def test_missing_unknown_ctrr_refuses_restore_without_policy_writer(self):
        self.installed()
        value=self.metadata['before-restore']['lab_policy']
        value='\n'.join(line for line in value.splitlines() if not line.startswith('Kernel CTRR Status:'))+'\n'
        self.metadata['before-restore']['lab_policy']=value
        code,result=self.invoke('restore')
        self.assertEqual(code,2)
        self.assertFalse(result['mutation_attempted'])
        self.assertFalse((self.state/'ctrr-attempt').exists())

    def test_unsafe_parent_and_existing_child_refused(self):
        self.parent.chmod(0o777)
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertFalse(result['mutation_attempted'])
        self.parent.chmod(0o700)
        (self.work/'preboot').mkdir()
        self.assertEqual(self.invoke()[0],2)

    def test_root_recovery_and_profile_self_binding_are_required(self):
        self.fixture['recovery'] = False
        self.assertEqual(self.invoke()[0],2)
        self.fixture['recovery'] = True
        value = copy.deepcopy(self.profile)
        value['files']['helper']['sha256'] = '0'*64
        self.profile_path.write_text(json.dumps(value))
        self.assertEqual(self.invoke()[0],2)

    def test_result_validator_displays_only_finite_live_records(self):
        _,result = self.invoke()
        path = self.case/'result.json'
        for good in (True,False):
            value = dict(result,synthetic=False)
            if not good:value['stage'] = 'PRIVATE_SENTINEL'
            path.write_text(json.dumps(value))
            run = subprocess.run([str(BINARY),'--validate-transaction-result',str(path),'--operation','install'],capture_output=True,text=True,timeout=5)
            self.assertEqual(run.returncode,0 if good else 2)
            self.assertNotIn('PRIVATE_SENTINEL',run.stdout)
        path.write_text(json.dumps(dict(result,synthetic=False,status='REFUSED',stage='READBACK',reason='READBACK_OR_DURABILITY')))
        self.assertEqual(subprocess.run([str(BINARY),'--validate-transaction-result',str(path),'--operation','install'],capture_output=True).returncode,0)

    def test_default_help_and_bad_cli_are_inert(self):
        for args in ([],['--help']):
            run = subprocess.run([str(BINARY),*args],capture_output=True,text=True,timeout=5)
            self.assertEqual(run.returncode,0)
            self.assertIn('Default/help is inert',run.stdout)
        for args in (['--transaction','install'],['--force'],['--transaction','install','--transaction','restore']):
            self.assertEqual(subprocess.run([str(BINARY),*args],capture_output=True).returncode,2)


def main():
    global BINARY,OUTPUT,REFERENCE,CANDIDATE,ROLLBACK,SANITIZE
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('compiled','output','reference31af','candidate','rollback'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sanitize',action='store_true')
    args,rest = p.parse_known_args()
    BINARY,OUTPUT,REFERENCE,CANDIDATE,ROLLBACK = (getattr(args,name).resolve() for name in ('compiled','output','reference31af','candidate','rollback'))
    SANITIZE = args.sanitize
    unittest.main(argv=[sys.argv[0]]+rest,verbosity=2)


if __name__ == '__main__':main()
