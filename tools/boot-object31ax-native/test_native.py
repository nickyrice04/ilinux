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
import re
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


def compress_own(plain):
    api=ctypes.CDLL('/usr/lib/libcompression.dylib')
    api.compression_encode_buffer.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_int]
    api.compression_encode_buffer.restype=ctypes.c_size_t
    source=ctypes.create_string_buffer(plain);output=ctypes.create_string_buffer(len(plain)*2+4096)
    n=api.compression_encode_buffer(output,len(output),source,len(plain),None,0x801)
    if not n:raise AssertionError('own candidate encoding failed')
    return ctypes.string_at(output,n)


def der(tag,body):
    n=len(body);width=max(1,(n.bit_length()+7)//8)
    return bytes([tag])+(bytes([n]) if n<128 else bytes([128+width])+n.to_bytes(width,'big'))+body


def integer(n):
    value=n.to_bytes(max(1,(n.bit_length()+7)//8),'big')
    if value[0]&128:value=b'\0'+value
    return der(2,value)


class Controller(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if OUTPUT.exists() or ROOT/'build' not in OUTPUT.parents:
            raise ValueError('fresh workspace output required')
        OUTPUT.mkdir(parents=True,mode=0o700)
        cls.old = load('old_metadata_ar', ROOT/'tools/boot-object31aj-native/test_native.py')
        cls.aq = load('aq_for_ar_tests', ROOT/'tools/boot-object31aq-native/build.py')
        cls.artifacts=(CANDIDATE,ROLLBACK)+((REFERENCE,) if REFERENCE is not None else ())
        cls.before = {str(p): (sha(p),p.stat().st_size) for p in cls.artifacts}
        cls.build = json.loads((BINARY.parent/'build-result.json').read_text())
        cls.profile = {'schema':'ilinux31ax-recovery-profile-v1',
          'target':cls.aq.CANDIDATE['target'],
          'files':{'candidate':{'name':'candidate.macho','bytes':153190400,'sha256':cls.aq.CANDIDATE['sha256']},
                   'rollback':{'name':'m1n1-boot021.bin','bytes':3932160,'sha256':cls.before[str(ROLLBACK)][0]},
                   'helper':{'name':'ilinux31ax-reader','bytes':BINARY.stat().st_size,'sha256':sha(BINARY)}},
          'native_deadline_ms':90000,'raw_policy_strategy':'reconstruct_lab_then_boot021_rescue','initial_payload':'BOOT021',
          'final_payload':'BOOT021','publication_authorizes_writes':False}
        if (CANDIDATE.stat().st_size,sha(CANDIDATE))!=(153190400,cls.aq.CANDIDATE['sha256']):
            raise ValueError('exact genuine own candidate required')
        cls.carriers=OUTPUT/'own-codec-fixtures';cls.carriers.mkdir(mode=0o700)
        encoded=compress_own(CANDIDATE.read_bytes())
        compression=der(0x30,integer(1)+integer(153190400))
        inner=der(0x30,der(0x16,b'IM4P')+der(0x16,b'krnl')+der(0x16,b'OWN-AW-GENERATED')+der(4,encoded)+compression)
        (cls.carriers/'candidate_img4_lzfse.bin').write_bytes(der(0x30,der(0x16,b'IMG4')+inner+der(0xa0,b'OWN')))
        (cls.carriers/'candidate_lzfse_with_trailer.bin').write_bytes(encoded+b'\0')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'carriers'):shutil.rmtree(cls.carriers)
        for p in cls.artifacts:
            if cls.before[str(p)] != (sha(p),p.stat().st_size):
                raise AssertionError('existing own artifact changed')

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(prefix='transaction-',dir=OUTPUT)).resolve()
        self.addCleanup(shutil.rmtree,self.case)
        self.parent = self.case/'private-state-parent';self.parent.mkdir(mode=0o700)
        self.work = self.case/'ilinux31ax.ABCDEF';self.work.mkdir(mode=0o700)
        self.state = self.parent/'ilinux31ax-state'
        self.profile_path = self.work/'profile.json'
        self.profile_path.write_text(json.dumps(self.profile,sort_keys=True,indent=2)+'\n')
        for source,name in ((BINARY,'ilinux31ax-reader'),(CANDIDATE,'candidate.macho'),(ROLLBACK,'m1n1-boot021.bin')):
            clone(source,self.work/name)
        self.fixture = {'recovery':True,'root':True,'model':'Mac17,6','state_parent':str(self.parent),'phases':{}}
        self.metadata = {}
        for name,selected,ctrr in (
            ('initial',ROLLBACK,'disabled'),('prewrite',ROLLBACK,'disabled'),
            ('reset',ROLLBACK,'enabled'),('candidate-prewrite',ROLLBACK,'enabled'),
            ('candidate',CANDIDATE,'enabled'),('before-restore',CANDIDATE,'enabled'),
            ('raw-policy',CANDIDATE,'disabled'),('restored',ROLLBACK,'disabled')):
            value = self.old.metadata(selected)
            value['apfs_list']['Containers'][0]['APFSContainerUUID'] = self.old.uuid(77)
            value['lab_policy'] = self.policy('Permissive',ctrr)
            value['original_policy'] = self.policy('Full','enabled',False)
            if name in ('reset','candidate-prewrite'):
                value['lab_policy']='\n'.join('(coih): absent' if line.startswith('(coih):') else line for line in value['lab_policy'].splitlines())+'\n'
            self.metadata[name] = value
            self.fixture['phases'][name] = str(self.case/(name+'.plist'))
        self.fixture_path = self.case/'transaction.plist'

    def policy(self, mode, ctrr, paired=True):
        value = self.old.policy(mode,ctrr,paired)
        if mode=='Permissive':
            value = value.replace('(smb0, smb1): 1','(smb0 && smb1): TRUE')
        value='\n'.join(line for line in value.splitlines() if not line.startswith('(lpnh):'))+'\n'
        value+='(lpnh): '+'c'*96+'\n(lpnh): '+'2'*96+'\n'
        value+=''.join('('+tag+'): '+v+'\n' for tag,v in
            {'CEPO':'0x1','SDOM':'0x1','CPRO':'1','CSEC':'1','lobo':'1','love':'26.1.0.1.2,3',
             'BORD':'0x1','CHIP':'0x6050','ECID':'0x1',
             'vuid':self.old.uuid(11 if mode=='Permissive' else 22),
             'kuid':self.old.uuid(88 if mode=='Permissive' else 99),
             'auxp':'absent','auxi':'absent','auxr':'absent'}.items())
        return value

    def invoke(self, operation='install'):
        for name,value in self.metadata.items():
            Path(self.fixture['phases'].get(name,self.case/(name+'.plist'))).write_bytes(plistlib.dumps(value))
        self.fixture_path.write_bytes(plistlib.dumps(self.fixture))
        completed = subprocess.run([str(self.work/'ilinux31ax-reader'),'--transaction',operation,
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
                self.assertTrue((self.state/'reset-attempt').exists())
                self.assertTrue((self.state/'reset.json').exists())
                self.assertTrue(result['cleanup_verified'])
                shutil.rmtree(self.state)

    def test_every_durability_failure_prevents_writer(self):
        for point in ('state_parent_sync','key_sync','profile_sync','target_sync','snapshot_sync','anchor_sync','enrolled_sync','reset_marker_sync'):
            with self.subTest(point=point):
                self.fixture['failpoint'] = point
                code,result = self.invoke()
                self.assertEqual(code,2)
                self.assertFalse(result['mutation_attempted'])
                self.assertTrue(self.state.exists())
                shutil.rmtree(self.state)

    def test_failed_marker_remains_spent_and_writer_cannot_retry(self):
        self.fixture['failpoint'] = 'reset_marker_sync'
        code,result = self.invoke()
        self.assertEqual(code,2)
        self.assertTrue((self.state/'reset-attempt').exists())
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

    def test_initial_is_exact_boot021_disabled_and_old_namespace_is_untouched(self):
        old=self.parent/'ilinux31ar-state';old.mkdir(mode=0o700)
        sentinel=old/'consumed';sentinel.write_bytes(b'OLD_SPENT_STATE');sentinel.chmod(0o600)
        self.installed()
        self.assertEqual(sentinel.read_bytes(),b'OLD_SPENT_STATE')
        self.assertEqual(set(p.name for p in old.iterdir()),{'consumed'})

    def test_enabled_initial_boot021_is_refused_before_state(self):
        self.metadata['initial']['selected_file']=str(ROLLBACK)
        self.metadata['initial']['lab_policy']=self.policy('Permissive','enabled')
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'ADMISSION'))
        self.assertFalse(result['mutation_attempted'])
        self.assertFalse(self.state.exists())

    def test_legacy_initial31af_is_refused_before_state(self):
        if REFERENCE is None:self.skipTest('optional own legacy31AF negative fixture not supplied')
        self.metadata['initial']['selected_file']=str(REFERENCE)
        self.metadata['initial']['lab_policy']=self.policy('Permissive','disabled')
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'ADMISSION'))
        self.assertFalse(result['mutation_attempted'])
        self.assertFalse(self.state.exists())

    def test_failed_candidate_has_saved_finite_readback_and_candidate_free_restore(self):
        unsupported=self.case/'unknown-object.bin';unsupported.write_bytes(b'owned unrecognized carrier')
        self.metadata['candidate']['selected_file']=str(unsupported)
        self.metadata['candidate']['lab_policy']=self.policy('Permissive','disabled')
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        d=result['diagnostics']
        self.assertTrue(d['available'])
        self.assertTrue(d['read_succeeded'])
        self.assertEqual(d['object_stage'],'UNCOMPRESSED_UNMATCHED')
        self.assertTrue(d['preservation_contract'])
        self.assertFalse(d['selected_payload_matches_phase'])
        self.assertFalse(d['lab_ctrr_matches_phase'])
        self.assertTrue(d['lab_ctrr_disabled'])
        self.assertEqual(json.loads((self.state/'candidate-diagnostic.json').read_text()),d)
        self.assertEqual((self.state/'candidate-diagnostic.json').stat().st_mode&0o7777,0o600)
        (self.work/'candidate.macho').unlink()
        self.assertEqual(self.invoke('restore')[0],0)

    def test_selected_read_refusal_is_distinct_from_recognition_failure(self):
        self.metadata['candidate']['selected_file']=str(self.case/'missing-carrier')
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        d=result['diagnostics']
        self.assertTrue(d['reference_present'])
        self.assertTrue(d['read_attempted'])
        self.assertFalse(d['read_succeeded'])
        self.assertEqual(d['object_stage'],'READ_REFUSED')
        self.assertFalse(d['known_exact'])
        self.assertTrue((self.state/'candidate-diagnostic.json').exists())

    def test_missing_reference_is_distinct_from_read_refusal(self):
        self.metadata['candidate']['lab_policy']=self.policy('Permissive','disabled').replace('(coih): '+'a'*64,'(coih): absent')
        # The original fixture uses a canonical synthetic hash, discover it
        # from the fixture policy line rather than hardcoding a private value.
        lines=self.metadata['candidate']['lab_policy'].splitlines()
        self.metadata['candidate']['lab_policy']='\n'.join('(coih): absent' if '(coih):' in line else line for line in lines)+'\n'
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        d=result['diagnostics']
        self.assertFalse(d['reference_present'])
        self.assertFalse(d['read_attempted'])
        self.assertEqual(d['object_stage'],'NO_REFERENCE')

    def test_same_process_reference_comparison_changes_and_preserves_no_values(self):
        # The standard metadata fixtures reuse the same COIH/NSIH, so equality
        # is independent of changing the owned fixture file's contents.
        for phase in ('reset','candidate-prewrite'):
            self.metadata[phase]['lab_policy']=self.policy('Permissive','enabled')
        _,result=self.invoke()
        self.assertTrue(result['diagnostics']['selection_comparison_available'])
        self.assertFalse(result['diagnostics']['selected_reference_changed'])
        self.assertNotIn('reference_commitment',json.dumps(result))
        self.assertNotIn('selection_before',json.dumps(result))

    def test_changed_selected_reference_is_compared_without_changing_admission(self):
        policy=self.metadata['candidate']['lab_policy']
        def changed(match):
            value=match.group(2)
            return match.group(1)+('a' if value[0]!='a' else 'b')+value[1:]
        changed_policy,count=re.subn(r'(\(coih\): )([0-9a-fA-F]+)',changed,policy)
        self.assertEqual(count,1)
        self.metadata['candidate']['lab_policy']=changed_policy
        code,result=self.invoke()
        self.assertEqual(code,0,result)
        d=result['diagnostics']
        self.assertTrue(d['selection_comparison_available'])
        self.assertTrue(d['selected_reference_changed'])
        self.assertTrue(d['phase_contract'])
        text=json.dumps(result)+(self.state/'candidate-diagnostic.json').read_text()
        self.assertNotIn('reference_commitment',text)
        self.assertNotIn(changed_policy,text)

    def test_owned_compressed_candidate_uses_same_recognizer(self):
        carrier=self.carriers/'candidate_img4_lzfse.bin'
        self.assertTrue(carrier.is_file(),'genuine own codec fixture required')
        self.metadata['candidate']['selected_file']=str(carrier)
        code,result=self.invoke()
        self.assertEqual(code,0,result)
        d=result['diagnostics']
        self.assertEqual((d['object_stage'],d['object_container'],d['object_codec']),('KNOWN_MATCHED','IMG4','LZFSE'))
        self.assertTrue(d['candidate_exact'])

    def test_damaged_own_compressed_carrier_refuses_with_finite_frame_reason(self):
        carrier=self.carriers/'candidate_lzfse_with_trailer.bin'
        self.assertTrue(carrier.is_file(),'genuine own damaged codec fixture required')
        self.metadata['candidate']['selected_file']=str(carrier)
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assertEqual(result['diagnostics']['object_stage'],'LZFSE_FRAME_REJECTED')
        self.assertFalse(result['candidate_verified'])

    def test_diagnostic_durability_failure_refuses_and_spends_reset(self):
        self.fixture['failpoint']='diagnostic_sync'
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'READBACK'))
        self.assertTrue(result['mutation_attempted'])
        self.assertTrue((self.state/'reset-attempt').exists())
        self.assertTrue((self.state/'reset-diagnostic.json').exists())
        self.fixture.pop('failpoint')
        self.assertEqual(self.invoke()[0],2)
        self.assertEqual(self.invoke('restore')[0],0)

    def test_result_validator_refuses_unknown_or_contradictory_diagnostics(self):
        _,result=self.invoke()
        original=dict(result,synthetic=False)
        path=self.case/'result.json'
        mutations=[('object_stage','PRIVATE_SENTINEL'),('object_identity','PRIVATE_SENTINEL'),
                   ('read_succeeded',False),('known_exact',False),('candidate_exact',False),
                   ('phase_contract',False),('selection_comparison_available',False)]
        for key,value in mutations:
            with self.subTest(key=key):
                bad=copy.deepcopy(original);bad['diagnostics'][key]=value
                if key=='selection_comparison_available':bad['diagnostics']['selected_reference_changed']=True
                path.write_text(json.dumps(bad))
                run=subprocess.run([str(BINARY),'--validate-transaction-result',str(path),'--operation','install'],capture_output=True,text=True)
                self.assertEqual(run.returncode,2)
                self.assertNotIn('PRIVATE_SENTINEL',run.stdout)

    def validate_finite(self, result, operation='install'):
        path=self.case/'finite-result.json';path.write_text(json.dumps(result))
        run=subprocess.run([str(BINARY),'--validate-transaction-result',str(path),'--operation',operation],
                           capture_output=True,text=True,timeout=5)
        self.assertEqual(run.stderr,'')
        return run.returncode

    def test_known_result_rejects_blocked_codec_or_unclassified_container(self):
        _,result=self.invoke();original=dict(result,synthetic=False)
        self.assertEqual(self.validate_finite(original),0)
        for codec in ('KEYBAG_BLOCKED','GZIP_UNSUPPORTED'):
            with self.subTest(codec=codec):
                bad=copy.deepcopy(original);bad['diagnostics']['object_codec']=codec
                self.assertEqual(self.validate_finite(bad),2)
                # Exact independent-review counterexample changed both fields.
                bad['diagnostics']['object_container']='UNCLASSIFIED'
                self.assertEqual(self.validate_finite(bad),2)
        bad=copy.deepcopy(original);bad['diagnostics']['object_container']='UNCLASSIFIED'
        self.assertEqual(self.validate_finite(bad),2)

    def test_failure_stage_category_completion_relations_are_enforced(self):
        _,result=self.invoke();base=dict(result,synthetic=False,status='REFUSED',stage='POSTCONDITION',
                                        reason='POLICY_OR_OBJECT',candidate_verified=False)
        base['diagnostics']=dict(base['diagnostics'],known_exact=False,candidate_exact=False,
            object_identity='UNKNOWN',selected_payload_matches_phase=False,phase_contract=False)
        # Finite hypothetical display fixtures follow the pinned AT adapter's
        # distinct branches. They are not additional runtime observations.
        cases=[
            ('INPUT_BOUND_REJECTED','UNCLASSIFIED','NONE',False),
            ('DER_FRAMING_REJECTED','UNCLASSIFIED','NONE',False),
            ('KEYBAG_BLOCKED','IM4P','KEYBAG_BLOCKED',True),
            ('COMPRESSED_BOUND_REJECTED','RAW','LZFSE',False),
            ('LZFSE_FRAME_REJECTED','IMG4','LZFSE',False),
            ('DECLARED_SIZE_MISMATCH','IM4P','LZFSE',False),
            ('DECODE_REJECTED','RAW','LZFSE',False),
            ('DECODED_UNMATCHED','IMG4','LZFSE',True),
            ('UNCOMPRESSED_DECLARATION_REJECTED','IM4P','NONE',False),
            ('GZIP_UNSUPPORTED','RAW','GZIP_UNSUPPORTED',False),
            ('UNCOMPRESSED_BOUND_REJECTED','RAW','NONE',False),
            ('UNCOMPRESSED_UNMATCHED','RAW','NONE',True),
        ]
        for stage,container,codec,completed in cases:
            with self.subTest(stage=stage):
                good=copy.deepcopy(base);good['diagnostics'].update(object_stage=stage,
                    object_container=container,object_codec=codec,recognizer_completed=completed,
                    decode_reason='DECODE_RETURN_ZERO' if stage=='DECODE_REJECTED' else
                        'DECODED' if codec=='LZFSE' and completed else 'NOT_APPLICABLE')
                self.assertEqual(self.validate_finite(good),0)
                bad=copy.deepcopy(good);bad['diagnostics']['recognizer_completed']=not completed
                self.assertEqual(self.validate_finite(bad),2)
                bad=copy.deepcopy(good);bad['diagnostics']['object_codec']='NONE' if codec!='NONE' else 'LZFSE'
                self.assertEqual(self.validate_finite(bad),2)
        # Framing/declaration/keybag failures cannot claim arbitrary raw carriers.
        for stage,codec,completed in [('DER_FRAMING_REJECTED','NONE',False),
                                      ('KEYBAG_BLOCKED','KEYBAG_BLOCKED',True),
                                      ('DECLARED_SIZE_MISMATCH','LZFSE',False),
                                      ('UNCOMPRESSED_DECLARATION_REJECTED','NONE',False)]:
            bad=copy.deepcopy(base);bad['diagnostics'].update(object_stage=stage,
                object_container='RAW',object_codec=codec,recognizer_completed=completed)
            self.assertEqual(self.validate_finite(bad),2)

    def test_refused_diagnostic_phase_is_bound_to_operation(self):
        _,result=self.invoke()
        candidate=dict(result,synthetic=False,status='REFUSED',stage='WRITER',reason='NONZERO_OR_INTERRUPTED',
                       writer_exit=71,candidate_verified=False)
        self.assertEqual(self.validate_finite(candidate,'install'),0)
        # A candidate-phase refusal must not be displayed as a restore result.
        restore_candidate=copy.deepcopy(candidate);restore_candidate['operation']='restore'
        self.assertEqual(self.validate_finite(restore_candidate,'restore'),2)
        raw=copy.deepcopy(restore_candidate);raw['diagnostics'].update(phase='raw-policy',
            lab_ctrr_enabled=False,lab_ctrr_disabled=True)
        raw['policy_transition'].update(reset_attempted=False,fresh_lab_baseline_ready=False,
            rescue_anchor_durable=True,transition_class='CLOSED_TYPED_OBSERVATION')
        self.assertEqual(self.validate_finite(raw,'restore'),0)
        # The inverse must reject even when no *_verified success flag is true.
        install_raw=copy.deepcopy(raw);install_raw['operation']='install'
        self.assertEqual(self.validate_finite(install_raw,'install'),2)

    def test_runtime_positive_negative_controls_precede_install_writer(self):
        for point,key in (('codec_positive','positive_exact'),('codec_negative','negative_refused')):
            with self.subTest(point=point):
                self.fixture['failpoint']=point
                code,result=self.invoke()
                self.assertEqual((code,result['stage'],result['reason']),(2,'CODEC','CAPABILITY_FAILED'))
                self.assertFalse(result['mutation_attempted'])
                self.assertFalse(result['candidate_verified'])
                self.assertTrue(result['cleanup_verified'])
                self.assertFalse(self.state.exists())
                self.assertFalse((self.work/'preboot').exists())
                cap=result['codec_capability']
                self.assertTrue(cap['attempted'])
                self.assertFalse(cap[key])
                self.assertFalse(cap['passed'])
                self.assertEqual(self.validate_finite(dict(result,synthetic=False)),0)
        self.fixture.pop('failpoint')

    def test_codec_failure_does_not_prevent_candidate_independent_raw_restore(self):
        self.installed()
        (self.work/'candidate.macho').unlink()
        invalid=self.case/'framed-invalid-lzvn'
        invalid.write_bytes(b'bvxn'+(16).to_bytes(4,'little')+(3).to_bytes(4,'little')+b'\0\0\0bvx$')
        for phase in ('before-restore','raw-policy'):
            self.metadata[phase]['selected_file']=str(invalid)
        self.fixture['failpoint']='codec_positive'
        code,result=self.invoke('restore')
        self.assertEqual((code,result['status']),(0,'RESTORE_COMPLETE'),result)
        self.assertFalse(result['codec_capability']['passed'])
        self.assertTrue(result['rollback_verified'])
        self.assertTrue(result['cleanup_verified'])
        self.assertTrue((self.state/'ctrr-attempt').exists())
        self.assertTrue((self.state/'boot021-attempt').exists())
        self.assertEqual(self.validate_finite(dict(result,synthetic=False),'restore'),0)

    def test_prior_aw_au_and_ar_state_are_never_touched(self):
        sentinels=[]
        for name in ('ilinux31aw-state','ilinux31au-state','ilinux31ar-state'):
            directory=self.parent/name;directory.mkdir(mode=0o700)
            file=directory/'spent';file.write_bytes(b'OLD_CONSUMED_STATE');file.chmod(0o600)
            sentinels.append((directory,file))
        self.installed()
        for directory,file in sentinels:
            self.assertEqual(file.read_bytes(),b'OLD_CONSUMED_STATE')
            self.assertEqual(set(p.name for p in directory.iterdir()),{'spent'})

    def test_exact_compressed_candidate_still_requires_enabled_ctrr(self):
        self.metadata['candidate']['selected_file']=str(self.carriers/'candidate_img4_lzfse.bin')
        self.metadata['candidate']['lab_policy']=self.policy('Permissive','disabled')
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assertTrue(result['diagnostics']['candidate_exact'])
        self.assertEqual(result['diagnostics']['decode_reason'],'DECODED')
        self.assertFalse(result['diagnostics']['lab_ctrr_matches_phase'])
        self.assertFalse(result['candidate_verified'])
        self.assertEqual(self.invoke('restore')[0],0)

    def test_buffer_failure_subreasons_are_finite_and_same_read(self):
        invalid=self.case/'invalid-lzvn'
        invalid.write_bytes(b'bvxn'+(16).to_bytes(4,'little')+(3).to_bytes(4,'little')+b'\0\0\0bvx$')
        self.metadata['candidate']['selected_file']=str(invalid)
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assertEqual(result['diagnostics']['object_stage'],'DECODE_REJECTED')
        self.assertEqual(result['diagnostics']['decode_reason'],'DECODE_RETURN_ZERO')
        self.assertEqual(json.loads((self.state/'candidate-diagnostic.json').read_text()),result['diagnostics'])
        self.assertEqual(self.validate_finite(dict(result,synthetic=False)),0)

    def test_capability_and_decode_display_relations_refuse_contradictions(self):
        _,result=self.invoke();base=dict(result,synthetic=False)
        self.assertTrue(base['codec_capability']['passed'])
        for key,value in (('attempted',False),('positive_exact',False),('negative_refused',False),
                          ('passed',False),('reason','PRIVATE_SENTINEL')):
            bad=copy.deepcopy(base);bad['codec_capability'][key]=value
            self.assertEqual(self.validate_finite(bad),2)
        for reason in ('DECODED','DECODE_RETURN_ZERO','PRIVATE_SENTINEL'):
            bad=copy.deepcopy(base);bad['diagnostics']['decode_reason']=reason
            self.assertEqual(self.validate_finite(bad),2)
        bad=copy.deepcopy(base);bad['codec_capability']['extra']=True
        self.assertEqual(self.validate_finite(bad),2)
        bad=copy.deepcopy(base);bad['diagnostics']['extra']=True
        self.assertEqual(self.validate_finite(bad),2)

    def test_new_builder_proves_safety_bodies_and_reversible_derivation(self):
        self.assertEqual(len(self.build['guard_preservation']['unchanged_aw_safety_bodies']),21)
        self.assertTrue(self.build['guard_preservation']['legacy_writer_argv_body_identical'])
        self.assertFalse(self.build['guard_preservation']['reset_uses_ctrr_disable_option'])
        self.assertEqual(len(self.build['frozen_aw_inputs']),14)
        self.assertEqual(len(self.build['retained_source_pins']),190)

    def test_standalone_codec_capability_dispatch_is_pure_and_bounded(self):
        before=set(self.case.rglob('*'))
        run=subprocess.run([str(BINARY),'--codec-capability'],capture_output=True,text=True,timeout=5)
        self.assertEqual((run.returncode,run.stderr),(0,''))
        value=json.loads(run.stdout)
        self.assertEqual(value,{'schema':'ilinux31ax-codec-capability-v1','attempted':True,
            'positive_exact':True,'negative_refused':True,'passed':True,'reason':'PASS',
            'read_only':True,'host_queries':False,'native_ready':False})
        self.assertEqual(set(self.case.rglob('*')),before)
        run=subprocess.run([str(BINARY),'--codec-capability','--transaction','install'],capture_output=True,text=True,timeout=5)
        self.assertEqual(run.returncode,2)

    def test_canonical_negative_one_refusal_and_malformed_numeric_tokens(self):
        self.fixture['failpoint']='codec_positive'
        _,result=self.invoke();result['synthetic']=False
        self.assertEqual(result['writer_exit'],-1)
        self.assertEqual(self.validate_finite(result),0)
        path=self.case/'numeric-result.json'
        original=json.dumps(result)
        self.assertEqual(original.count('"writer_exit": -1'),1)
        for token in ('-0','-01','-2','-10','+1','1.0','1e0','-1.0','-1e0','01','- 1'):
            with self.subTest(token=token):
                path.write_text(original.replace('"writer_exit": -1','"writer_exit": '+token))
                run=subprocess.run([str(BINARY),'--validate-transaction-result',str(path),'--operation','install'],capture_output=True,text=True,timeout=5)
                self.assertEqual(run.returncode,2)

    def test_negative_profile_unsigned_fields_still_refuse(self):
        for names in (('files','candidate','bytes'),('files','helper','bytes'),('native_deadline_ms',)):
            with self.subTest(field=names):
                value=copy.deepcopy(self.profile);current=value
                for name in names[:-1]:current=current[name]
                current[names[-1]]=-1
                self.profile_path.write_text(json.dumps(value))
                code,result=self.invoke()
                self.assertEqual((code,result['stage']),(2,'PREFLIGHT'))
                self.assertFalse(result['mutation_attempted'])
                self.assertFalse(result['codec_capability']['attempted'])
                self.assertFalse(self.state.exists())

    def test_multiple_capability_failures_preserve_positive_first_display(self):
        self.fixture['failpoint']='codec_positive'
        _,result=self.invoke();result['synthetic']=False
        result['codec_capability']['negative_refused']=False
        self.assertEqual(self.validate_finite(result),0)
        result['codec_capability']['reason']='NEGATIVE_CONTROL_FAILED'
        self.assertEqual(self.validate_finite(result),2)

    def test_formerly_rejected_apple_control_completes_selected_read(self):
        plain=bytearray(1048576);state=0x19671234
        for index in range(len(plain)):
            state^=(state<<13)&0xffffffff;state^=state>>17;state^=(state<<5)&0xffffffff
            plain[index]=state&255
        encoded=compress_own(bytes(plain))
        self.assertEqual(len(encoded),1059159)
        carrier=self.case/'owned-original-stream-counterexample';carrier.write_bytes(encoded)
        self.metadata['candidate']['selected_file']=str(carrier)
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        d=result['diagnostics']
        self.assertTrue(d['recognizer_completed'])
        self.assertEqual((d['object_stage'],d['decode_reason']),('DECODED_UNMATCHED','DECODED'))
        self.assertFalse(d['known_exact'])
        self.assertFalse(result['candidate_verified'])

    def change_tag(self,phase,tag,value,role='lab_policy'):
        pattern=r'(\('+re.escape(tag)+r'\): )[^\n]+'
        changed,count=re.subn(pattern,lambda m:m.group(1)+value,self.metadata[phase][role],count=1)
        self.assertEqual(count,1)
        self.metadata[phase][role]=changed

    def rescue_from_reset(self):
        self.metadata['before-restore']=copy.deepcopy(self.metadata['reset'])
        self.metadata['raw-policy']=copy.deepcopy(self.metadata['reset'])
        policy=self.metadata['raw-policy']['lab_policy'].replace('Kernel CTRR Status: Enabled','Kernel CTRR Status: Disabled')
        policy=re.sub(r'(\(sip2\): )[^\n]+',r'\g<1>1',policy)
        self.metadata['raw-policy']['lab_policy']=policy

    def assert_no_candidate(self):
        self.assertFalse((self.state/'candidate-attempt').exists())
        self.assertFalse((self.state/'reset-ready').exists())

    def test_reset_fresh_baseline_and_empty_reference_are_durable(self):
        result=self.installed();transition=result['policy_transition']
        self.assertTrue(transition['pre_anchor_bound'])
        self.assertTrue(transition['reset_attempted'])
        self.assertTrue(transition['fresh_lab_baseline_ready'])
        self.assertEqual(transition['transition_class'],'STRICT_RESET_ADMITTED')
        for name in ('pre-reset.json','pre-policy-anchor.json','reset-attempt','reset.json','candidate-baseline.json','reset-ready'):
            self.assertTrue((self.state/name).is_file())
        d=json.loads((self.state/'reset-diagnostic.json').read_text())
        self.assertEqual((d['phase'],d['object_stage']),('reset','NO_REFERENCE'))
        self.assertTrue(d['selection_comparison_available'])
        self.assertTrue(d['phase_contract'])
        self.assertEqual(self.validate_finite(dict(result,synthetic=False)),0)

    def test_failed_new_baseline_still_has_independent_functional_rescue(self):
        self.fixture['failpoint']='new_baseline_sync'
        code,result=self.invoke();self.assertEqual((code,result['stage']),(2,'BASELINE'))
        self.assert_no_candidate()
        self.assertEqual(result['diagnostics']['object_stage'],'NO_REFERENCE')
        self.assertEqual(self.validate_finite(dict(result,synthetic=False)),0)
        self.fixture.pop('failpoint');self.rescue_from_reset();(self.work/'candidate.macho').unlink()
        code,result=self.invoke('restore')
        self.assertEqual((code,result['status']),(0,'RESTORE_COMPLETE'),result)
        self.assertEqual(result['policy_transition']['rollback_scope'],'FUNCTIONAL_BOOT021_CTRR_DISABLED')
        self.assertFalse(result['policy_transition']['old_lab_metadata_restored'])
        self.assertTrue(result['policy_transition']['rescue_anchor_durable'])
        self.assertEqual(self.validate_finite(dict(result,synthetic=False),'restore'),0)

    def test_first_reset_readback_failure_does_not_require_new_baseline_for_rescue(self):
        valid=copy.deepcopy(self.metadata['reset'])
        self.metadata['reset']['lab_policy']='UNREADABLE_SYNTHETIC_CONTROL'
        code,result=self.invoke();self.assertEqual((code,result['stage']),(2,'READBACK'))
        self.assert_no_candidate();self.assertTrue((self.state/'enrolled').exists())
        self.metadata['reset']=valid;self.rescue_from_reset();(self.work/'candidate.macho').unlink()
        code,result=self.invoke('restore');self.assertEqual((code,result['status']),(0,'RESTORE_COMPLETE'),result)

    def test_unqualified_private_reissuance_blocks_candidate_but_allows_functional_rescue(self):
        self.change_tag('reset','rpnh','9'*96)
        code,result=self.invoke();self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assert_no_candidate();self.assertTrue(result['policy_transition']['lab_private_changed'])
        self.assertEqual(result['policy_transition']['transition_class'],'UNQUALIFIED_TRANSITION')
        self.rescue_from_reset();self.change_tag('restored','rpnh','9'*96)
        (self.work/'candidate.macho').unlink()
        code,result=self.invoke('restore');self.assertEqual((code,result['status']),(0,'RESTORE_COMPLETE'),result)
        self.assertEqual(result['policy_transition']['transition_class'],'UNQUALIFIED_TRANSITION')
        self.assertFalse(result['policy_transition']['old_lab_metadata_restored'])
        self.assertEqual(self.validate_finite(dict(result,synthetic=False),'restore'),0)
        self.assertEqual(self.invoke()[0],2)
        self.assertFalse((self.state/'candidate-attempt').exists())

    def test_reset_nsih_drift_never_becomes_candidate_baseline(self):
        self.change_tag('reset','nsih','8'*64)
        code,result=self.invoke();self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assert_no_candidate();self.assertTrue(result['policy_transition']['lab_manifest_changed'])
        self.rescue_from_reset();self.change_tag('restored','nsih','8'*64)
        code,result=self.invoke('restore');self.assertEqual((code,result['status']),(0,'RESTORE_COMPLETE'),result)
        self.assertFalse(result['policy_transition']['fresh_lab_baseline_ready'])

    def test_reset_can_clear_only_nondowngrade_default_representations(self):
        for phase in ('reset','candidate-prewrite','candidate','before-restore','raw-policy','restored'):
            self.change_tag(phase,'sip0','absent')
            self.change_tag(phase,'sip1','0')
            self.change_tag(phase,'smb2','0')
        self.installed();self.assertEqual(self.invoke('restore')[0],0)

    def test_preexisting_other_lab_downgrade_refuses_before_reset(self):
        self.change_tag('initial','sip1','1')
        code,result=self.invoke();self.assertEqual((code,result['stage']),(2,'ADMISSION'))
        self.assertFalse(result['mutation_attempted']);self.assertFalse(self.state.exists())

    def test_protected_original_identity_and_private_changes_block_rescue(self):
        self.change_tag('reset','nsih','7'*64,'original_policy')
        code,result=self.invoke();self.assertEqual(code,2);self.assert_no_candidate()
        self.assertTrue(result['policy_transition']['protected_identity_changed'])
        self.rescue_from_reset();code,result=self.invoke('restore')
        self.assertEqual((code,result['stage']),(2,'RESTORE_ADMISSION'))
        self.assertFalse(result['mutation_attempted'])

    def test_changed_lab_kuid_or_unsafe_aux_is_not_a_rescue_exception(self):
        self.change_tag('reset','kuid',self.old.uuid(999))
        code,result=self.invoke();self.assertEqual(code,2);self.assert_no_candidate()
        self.rescue_from_reset();code,result=self.invoke('restore')
        self.assertEqual((code,result['stage']),(2,'RESTORE_ADMISSION'))
        self.assertFalse(result['mutation_attempted'])

    def test_unsafe_aux_refuses_reset_readback_and_persistent_rescue(self):
        self.change_tag('reset','auxp','1')
        code,result=self.invoke();self.assertEqual((code,result['stage']),(2,'READBACK'));self.assert_no_candidate()
        self.rescue_from_reset();code,result=self.invoke('restore')
        self.assertEqual((code,result['stage']),(2,'RESTORE_ADMISSION'));self.assertFalse(result['mutation_attempted'])

    def test_existing_pre_anchor_content_cannot_be_rebased(self):
        self.installed();path=self.state/'pre-reset.json';original=path.read_bytes()
        mutations=[('original_metadata_hmac','0'*64),('lab_metadata_hmac','0'*64),('original_semantics',None)]
        for key,value in mutations:
            record=json.loads(original)
            if value is None:record[key]['smb2']=False
            else:record[key]=value
            path.write_text(json.dumps(record));path.chmod(0o600)
            code,result=self.invoke('restore')
            self.assertEqual((code,result['stage']),(2,'ENROLLMENT'))
            self.assertFalse(result['mutation_attempted'])
            path.write_bytes(original);path.chmod(0o600)

    def test_rescue_minus_c_may_not_change_custom_object_reference(self):
        self.installed()
        self.change_tag('raw-policy','coih','3'*64)
        code,result=self.invoke('restore')
        self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assertFalse((self.state/'boot021-attempt').exists())
        self.assertTrue(result['diagnostics']['selected_reference_changed'])

    def test_current_rescue_metadata_is_frozen_across_raw_and_future_invocation(self):
        self.installed();self.change_tag('restored','rpnh','9'*96)
        code,result=self.invoke('restore');self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assertTrue((self.state/'boot021-attempt').exists())
        self.metadata['before-restore']=copy.deepcopy(self.metadata['restored'])
        code,result=self.invoke('restore')
        self.assertEqual((code,result['stage']),(2,'RESTORE_ADMISSION'))
        self.assertFalse(result['mutation_attempted']);self.assertFalse(result['rollback_verified'])

    def test_absent_manifest_rescue_accepts_only_preknown_raw_manifest(self):
        self.change_tag('reset','nsih','absent')
        code,result=self.invoke();self.assertEqual(code,2);self.assert_no_candidate()
        self.rescue_from_reset();code,result=self.invoke('restore')
        self.assertEqual((code,result['status']),(0,'RESTORE_COMPLETE'),result)
        self.assertEqual(result['policy_transition']['transition_class'],'UNQUALIFIED_TRANSITION')
        self.assertEqual(self.validate_finite(dict(result,synthetic=False),'restore'),0)

    def test_absent_manifest_rescue_refuses_unrelated_raw_manifest(self):
        self.change_tag('reset','nsih','absent');self.assertEqual(self.invoke()[0],2)
        self.rescue_from_reset();self.change_tag('restored','nsih','4'*64)
        code,result=self.invoke('restore');self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assertFalse(result['rollback_verified'])

    def test_rescue_anchor_snapshot_durability_precedes_all_rescue_writers(self):
        self.installed();self.fixture['failpoint']='snapshot_sync'
        code,result=self.invoke('restore');self.assertEqual((code,result['stage']),(2,'RESCUE_ANCHOR'))
        self.assertFalse(result['mutation_attempted']);self.assertFalse((self.state/'ctrr-attempt').exists())

    def test_rescue_anchor_contract_durability_precedes_all_rescue_writers(self):
        self.installed();self.fixture['failpoint']='rescue_contract_sync'
        code,result=self.invoke('restore');self.assertEqual((code,result['stage']),(2,'RESCUE_ANCHOR'))
        self.assertFalse(result['mutation_attempted']);self.assertFalse((self.state/'ctrr-attempt').exists())

    def test_rescue_anchor_ready_durability_precedes_all_rescue_writers(self):
        self.installed();self.fixture['failpoint']='rescue_ready_sync'
        code,result=self.invoke('restore');self.assertEqual((code,result['stage']),(2,'RESCUE_ANCHOR'))
        self.assertFalse(result['mutation_attempted']);self.assertFalse((self.state/'ctrr-attempt').exists())

    def test_partial_rescue_anchor_cannot_be_bypassed_by_readonly_noop(self):
        self.installed();path=self.state/'rescue-anchor.json';path.write_bytes(b'PARTIAL');path.chmod(0o600)
        self.metadata['before-restore']=copy.deepcopy(self.metadata['restored'])
        code,result=self.invoke('restore');self.assertEqual((code,result['stage']),(2,'RESCUE_ANCHOR'))
        self.assertFalse(result['mutation_attempted']);self.assertFalse(result['rollback_verified'])
        self.assertEqual(path.read_bytes(),b'PARTIAL')

    def test_nonzero_reset_writer_is_spent_and_does_not_install_candidate(self):
        self.fixture['reset_exit']=71
        code,result=self.invoke();self.assertEqual((code,result['stage'],result['writer_exit']),(2,'WRITER',71))
        self.assert_no_candidate();self.assertTrue((self.state/'reset.json').exists())
        self.fixture.pop('reset_exit');self.rescue_from_reset();self.assertEqual(self.invoke('restore')[0],0)

    def test_unexpected_candidate_as_reset_selection_is_not_admitted(self):
        self.metadata['reset']['lab_policy']=self.policy('Permissive','enabled')
        self.metadata['reset']['selected_file']=str(CANDIDATE)
        code,result=self.invoke();self.assertEqual((code,result['stage']),(2,'POSTCONDITION'))
        self.assert_no_candidate();self.assertTrue(result['diagnostics']['candidate_exact'])

    def test_functional_result_cannot_claim_old_metadata_or_fresh_candidate_state(self):
        self.installed();_,result=self.invoke('restore');base=dict(result,synthetic=False)
        self.assertEqual(self.validate_finite(base,'restore'),0)
        for key,value in (('old_lab_metadata_restored',True),('fresh_lab_baseline_ready',True),
                          ('rollback_scope','EXACT_OLD_POLICY'),('rescue_anchor_durable',False)):
            bad=copy.deepcopy(base);bad['policy_transition'][key]=value
            self.assertEqual(self.validate_finite(bad,'restore'),2)

    def test_global_typed_lpnh_rotation_does_not_rebase_stable_anchors(self):
        for index,phase in enumerate(self.metadata):
            for role in ('lab_policy','original_policy'):
                self.change_tag(phase,'lpnh',format(index+3,'x')*96,role)
        self.installed();self.assertEqual(self.invoke('restore')[0],0)

    def test_inconsistent_lpnh_within_one_guarded_read_is_refused(self):
        value=self.metadata['initial']['lab_policy'].replace('(lpnh): '+'c'*96,'(lpnh): '+'9'*96)
        self.metadata['initial']['lab_policy_after']=value
        code,result=self.invoke()
        self.assertEqual((code,result['stage']),(2,'ADMISSION'))
        self.assertFalse(result['mutation_attempted']);self.assertFalse(self.state.exists())


def main():
    global BINARY,OUTPUT,REFERENCE,CANDIDATE,ROLLBACK,SANITIZE
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('compiled','output','candidate','rollback'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reference31af',type=Path)
    p.add_argument('--sanitize',action='store_true')
    args,rest = p.parse_known_args()
    BINARY,OUTPUT,CANDIDATE,ROLLBACK = (getattr(args,name).resolve() for name in ('compiled','output','candidate','rollback'))
    REFERENCE=args.reference31af.resolve() if args.reference31af is not None else None
    SANITIZE = args.sanitize
    unittest.main(argv=[sys.argv[0]]+rest,verbosity=2)


if __name__ == '__main__':main()
