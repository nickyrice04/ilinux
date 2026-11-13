#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile/run original C against synthetic files/CF plists; never live modes."""
import copy
import ctypes
import hashlib
import hmac
import json
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BUILD=ROOT/'build/31aj-native'
SANITIZE='--sanitize' in sys.argv
if SANITIZE:sys.argv.remove('--sanitize')

def sha(data):return hashlib.sha256(data).hexdigest()
def der(tag,data):
    n=len(data);size=(n.bit_length()+7)//8
    return bytes([tag])+(bytes([n]) if n<128 else bytes([0x80+size])+n.to_bytes(size,'big'))+data
def integer(n):
    data=n.to_bytes(max(1,(n.bit_length()+7)//8),'big')
    if data[0]&128:data=b'\0'+data
    return der(2,data)
def im4p(data,extra=b'',kind=b'krnl'):
    return der(0x30,der(0x16,b'IM4P')+der(0x16,kind)+der(0x16,b'synthetic-only')+der(4,data)+extra)
def img4(data):return der(0x30,der(0x16,b'IMG4')+data+der(0xa0,b'opaque-synthetic-manifest'))
def compress(data):
    library=ctypes.CDLL('/usr/lib/libcompression.dylib')
    library.compression_encode_buffer.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_int]
    library.compression_encode_buffer.restype=ctypes.c_size_t
    out=ctypes.create_string_buffer(len(data)*2+4096);source=ctypes.create_string_buffer(data)
    n=library.compression_encode_buffer(out,len(out),source,len(data),None,0x801)
    if not n:raise RuntimeError('synthetic compression failed')
    return out.raw[:n]

def policy(mode='Permissive',ctrr='enabled',paired=True):
    security='Security Mode: Permissive (smb0, smb1): 1' if mode=='Permissive' else 'Security Mode: Full (smb0): absent'
    coih='a'*64 if mode=='Permissive' else 'absent'
    return '\n'.join([security,'Current OS environment: one true recoveryOS','Pairing: '+('Paired' if paired else 'Unpaired'),
      'Kernel CTRR Status: '+ctrr.title(),'(smb2): absent','(smb3): absent','(smb4): absent',
      '(sip0): 0','(sip1): absent','(sip3): absent','(sip2): '+('absent' if ctrr=='enabled' else '1'),
      '(coih): '+coih,'(nsih): '+'b'*64,'(lpnh): '+'c'*64,
      '(rpnh): '+'d'*96,'(rpnh): '+'e'*96,'(ronh): '+'f'*96,'(spih): '+'1'*96,'(stng): 15'])+'\n'

def uuid(n):return f'{n:08x}-0000-0000-0000-{n:012x}' # Explicitly synthetic.
def metadata(selected):
    def vol(name,role,n):return {'Name':name,'Roles':[role],'DeviceIdentifier':f'disk3s{n}','APFSVolumeUUID':uuid(n)}
    lab=vol('iLinux Boot Lab','System',1);original=vol('Macintosh HD','System',2)
    pb=vol('Preboot','Preboot',3);data=vol('iLinux Boot Lab - Data','Data',4)
    def info(v,mount,group):return {'Internal':True,'VolumeName':v['Name'],'MountPoint':mount,'VolumeUUID':v['APFSVolumeUUID'],
         'DeviceIdentifier':v['DeviceIdentifier'],'APFSContainerReference':'disk3','APFSVolumeGroupID':uuid(group)}
    return {'recovery':True,'root':True,'model':'Mac17,6',
      'lab_info':info(lab,'/Volumes/iLinux Boot Lab',11),
      'original_info':info(original,'/Volumes/Macintosh HD',22),
      'preboot_info':info(pb,'/Volumes/Preboot',33),
      'data_info':info(data,'/Volumes/iLinux Boot Lab - Data',11),
      'apfs_list':{'Containers':[{'ContainerReference':'disk3','Volumes':[lab,original,pb,data]}]},
      'lab_policy':policy(),'original_policy':policy('Full',paired=False),'selected_file':str(selected)}

class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BUILD.mkdir(parents=True,exist_ok=True)
        cls.directory=Path(tempfile.mkdtemp(prefix='synthetic-',dir=BUILD))
        plain=bytearray(((i*17)^(i>>4))&255 for i in range(65536))
        plain[:2]=b'\x30\x80' # Exact known bytes win over a misleading DER prefix.
        cls.plain=bytes(plain)
        cls.encoded=compress(cls.plain)
        definition={'schema':'ilinux31aj-compiled-candidate-v1','target':{'model':'Mac17,6','board':'j716c','chip_id':'0x6050'},'bytes':len(cls.plain),'sha256':sha(cls.plain),'publication_authorizes_writes':False}
        definition_path=cls.directory/'definition.json';definition_path.write_text(json.dumps(definition))
        command=[sys.executable,'-I',str(HERE/'build.py'),'--output',str(cls.directory/'compiled'),'--candidate-definition',str(definition_path)]
        if SANITIZE:command.append('--sanitize')
        result=subprocess.run(command,capture_output=True,text=True,timeout=30)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        cls.binary=cls.directory/'compiled/ilinux31aj-reader';binary=cls.binary.read_bytes()
        cls.profile={'schema':'ilinux31aj-recovery-profile-v1','target':definition['target'],
          'files':{'candidate':{'name':'candidate.macho','bytes':len(cls.plain),'sha256':sha(cls.plain)},
                   'rollback':{'name':'m1n1-boot021.bin','bytes':3932160,'sha256':'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'},
                   'helper':{'name':'ilinux31aj-reader','bytes':len(binary),'sha256':sha(binary)}},
          'native_deadline_ms':90000,'raw_policy_strategy':'ctrr_only','initial_payload':'31AF','final_payload':'BOOT021','publication_authorizes_writes':False}
        cls.profile_path=cls.directory/'profile.json';cls.profile_path.write_text(json.dumps(cls.profile))
    @classmethod
    def tearDownClass(cls):shutil.rmtree(cls.directory)
    def setUp(self):
        self.scratch=Path(tempfile.mkdtemp(prefix='case-',dir=self.directory));self.addCleanup(shutil.rmtree,self.scratch)
        self.comparison_key=self.scratch/'comparison.key';self.comparison_key.write_bytes(bytes(range(32)));self.comparison_key.chmod(0o600)
    def invoke(self,*args,profile=True):
        argv=[str(self.binary),*map(str,args)]
        if profile:argv+=['--profile',str(self.profile_path)]
        result=subprocess.run(argv,capture_output=True,text=True,timeout=10)
        return result,json.loads(result.stdout) if result.stdout.startswith('{') else result.stdout
    def inspect(self,data):
        path=self.scratch/'object.bin';path.write_bytes(data)
        return self.invoke('--fixture',path)
    def snapshot(self,changes=None,bound=True):
        selected=self.scratch/'candidate.bin';selected.write_bytes(self.plain)
        value=metadata(selected)
        if changes:changes(value)
        path=self.scratch/'fixture.plist';path.write_bytes(plistlib.dumps(value))
        return self.invoke('--snapshot-fixture',path,*(['--comparison-key',self.comparison_key] if bound else []))
    def save(self,name,value):
        path=self.scratch/name;path.write_text(json.dumps(value));return path
    def phase(self,current,phase,baseline=None,synthetic=True,bound=True,key_path=None):
        args=['--validate-fixture-snapshot' if synthetic else '--validate-snapshot',self.save('state.json',current),'--phase',phase]
        if baseline is not None:args+=['--baseline',self.save('baseline.json',baseline)]
        if bound:args+=['--comparison-key',key_path or self.comparison_key]
        return self.invoke(*args)
    def states(self):
        result,state=self.snapshot();self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        base=copy.deepcopy(state);base['selected_payload']='31AF';base['lab_ctrr']='unknown'
        return state,base

    def test_default_help_only(self):
        r,text=self.invoke(profile=False);self.assertEqual(r.returncode,0);self.assertIn('Default only displays help',text)
    def test_real_stream_roundtrip_and_three_refusals(self):
        r,value=self.invoke('--codec-selftest',profile=False);self.assertEqual(r.returncode,0);self.assertEqual(value['controls'],4);self.assertEqual(r.stderr,'')
    def test_raw_exact_compiled_candidate(self):
        r,value=self.inspect(self.plain);self.assertEqual(r.returncode,0);self.assertEqual(value['payload_identity'],'CANDIDATE');self.assertFalse(value['selection_verified'])
    def test_lzfse_exact_compiled_candidate(self):
        for value in (self.encoded,img4(im4p(self.encoded,der(0x30,integer(1)+integer(len(self.plain)))))):
            with self.subTest(bytes=len(value)):
                r,identity=self.inspect(value);self.assertEqual(r.returncode,0);self.assertEqual(identity['payload_identity'],'CANDIDATE');self.assertEqual(identity['codec'],'LZFSE')
    def test_raw_lzfse_block_uses_independent_complete_framing(self):
        value=b'bvx-'+struct.pack('<I',len(self.plain))+self.plain+b'bvx$'
        r,identity=self.inspect(value);self.assertEqual(r.returncode,0);self.assertEqual(identity['payload_identity'],'CANDIDATE')
    def test_trailing_byte_concat_and_missing_footer_refused(self):
        for value in (self.encoded+b'\0',self.encoded+self.encoded,self.encoded[:-1]):
            with self.subTest(bytes=len(value)):
                r,_=self.inspect(value);self.assertEqual(r.returncode,2)
    def test_declared_decompressed_size_must_match_stream(self):
        r,_=self.inspect(im4p(self.encoded,der(0x30,integer(1)+integer(len(self.plain)+1))));self.assertEqual(r.returncode,2)
    def test_bad_frame_extent_refused(self):
        value=bytearray(self.encoded);struct.pack_into('<I',value,4,160*1024*1024+1)
        r,_=self.inspect(value);self.assertEqual(r.returncode,2)
    def test_gzip_is_explicitly_unsupported(self):
        r,_=self.inspect(b'\x1f\x8b\x08not-an-accepted-codec');self.assertEqual(r.returncode,2)
    def test_keybag_blocks_decoder_even_with_known_plaintext(self):
        r,identity=self.inspect(im4p(self.plain,der(4,b'opaque-secret-fixture')));self.assertEqual(r.returncode,0);self.assertEqual(identity['payload_identity'],'UNKNOWN');self.assertEqual(identity['codec'],'KEYBAG_BLOCKED');self.assertNotIn('secret',json.dumps(identity))
    def test_final_context_properties_are_opaque(self):
        r,identity=self.inspect(img4(im4p(self.plain,der(0xa0,b'not-DER-PRIVATE-MARKER'))));self.assertEqual(r.returncode,0);self.assertEqual(identity['payload_identity'],'CANDIDATE');self.assertFalse(identity['wrapper_authentication_verified']);self.assertNotIn('PRIVATE',json.dumps(identity))
    def test_other_printable_fourcc_does_not_erase_exact_payload_identity(self):
        r,identity=self.inspect(img4(im4p(self.plain,kind=b'bkrn')));self.assertEqual(r.returncode,0);self.assertEqual(identity['payload_identity'],'CANDIDATE');self.assertFalse(identity['wrapper_authentication_verified'])
        r,_=self.inspect(im4p(self.plain,kind=b'\x01abc'));self.assertEqual(r.returncode,2)
    def test_outer_context_order_is_strict(self):
        value=der(0x30,der(0x16,b'IMG4')+im4p(self.plain)+der(0xa1,b'first')+der(0xa0,b'second'))
        r,_=self.inspect(value);self.assertEqual(r.returncode,2)
    def test_duplicate_wrong_context_and_container_trailer_refused(self):
        for value in (im4p(self.plain,der(0xa0,b'x')*2),im4p(self.plain,der(0xa1,b'x')),img4(im4p(self.plain))+bytes(4)):
            with self.subTest(bytes=len(value)):
                r,_=self.inspect(value);self.assertEqual(r.returncode,2)
    def test_unknown_data_has_no_hash_or_paths(self):
        r,identity=self.inspect(b'SYNTHETIC_PRIVATE_MARKER');self.assertEqual(r.returncode,0);self.assertEqual(identity['payload_identity'],'UNKNOWN');self.assertNotIn('PRIVATE',json.dumps(identity));self.assertFalse(any('sha' in k or 'path' in k for k in identity))
    def test_fixture_symlink_refused(self):
        target=self.scratch/'target';target.write_bytes(self.plain);link=self.scratch/'link';link.symlink_to(target)
        r,_=self.invoke('--fixture',link);self.assertEqual(r.returncode,2)
    def test_fixture_outside_workspace_refused_without_read(self):
        r,value=self.invoke('--fixture','/synthetic-outside/no-read');self.assertEqual(r.returncode,2);self.assertNotIn('outside',json.dumps(value))
    def test_profile_candidate_tampering_refused(self):
        p=copy.deepcopy(self.profile);p['files']['candidate']['sha256']='a'*64
        r,_=self.invoke('--fixture',self.save('dummy',{}),'--profile',self.save('bad-profile.json',p),profile=False);self.assertEqual(r.returncode,2)
    def test_profile_helper_self_binding(self):
        p=copy.deepcopy(self.profile);p['files']['helper']['sha256']='a'*64
        r,_=self.invoke('--fixture',self.save('dummy',{}),'--profile',self.save('bad-profile.json',p),profile=False);self.assertEqual(r.returncode,2)
    def test_profile_unknown_authorization_or_personal_keys_refused(self):
        p=copy.deepcopy(self.profile);p['personal_uuid']='SYNTHETIC_PRIVATE_MARKER'
        r,value=self.invoke('--fixture',self.save('dummy',{}),'--profile',self.save('bad-profile.json',p),profile=False);self.assertEqual(r.returncode,2);self.assertNotIn('PRIVATE',json.dumps(value))
    def test_complete_cf_fixture_snapshot_is_synthetic(self):
        r,s=self.snapshot();self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertEqual(s['scope'],'SYNTHETIC_CONTROL');self.assertEqual(s['selected_payload'],'CANDIDATE');self.assertEqual(s['lab_semantics']['sip0'],'0x0000000000000000');self.assertFalse(s['writes_authorized']);self.assertNotIn(uuid(11),json.dumps(s))
    def test_numeric_grouped_mode_and_bare_hex_flags(self):
        r,s=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy'].replace('(sip0): 0','(sip0): abcdef10')))
        self.assertEqual(r.returncode,0);self.assertEqual(s['lab_semantics']['sip0'],'0x00000000abcdef10');self.assertTrue(s['lab_semantics']['smb0']);self.assertEqual(s['original_semantics']['smb1'],'ABSENT')
    def test_wrong_or_ordinary_recovery_refused(self):
        for change in (lambda v:v.update(recovery=False),lambda v:v.update(lab_policy=v['lab_policy'].replace('one true recoveryOS','ordinary recoveryOS'))):
            r,_=self.snapshot(change);self.assertEqual(r.returncode,2)
    def test_unpaired_or_contradictory_pair_refused(self):
        for label in ('Unpaired','Not Paired','Paired\nOther field: Unpaired'):
            r,_=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy'].replace('Pairing: Paired','Pairing: '+label)));self.assertEqual(r.returncode,2)
    def test_wrong_machine_root_or_original_mode_refused(self):
        for change in (lambda v:v.update(model='Mac14,2'),lambda v:v.update(root=False),lambda v:v.update(original_policy=policy())):
            r,_=self.snapshot(change);self.assertEqual(r.returncode,2)
    def test_shared_group_wrong_role_or_preboot_container_refused(self):
        def group(v):v['original_info']['APFSVolumeGroupID']=v['lab_info']['APFSVolumeGroupID']
        def role(v):v['apfs_list']['Containers'][0]['Volumes'][0]['Roles']=['Data']
        def container(v):v['preboot_info']['APFSContainerReference']='disk9'
        for change in (group,role,container):
            r,_=self.snapshot(change);self.assertEqual(r.returncode,2)
    def test_lab_data_binding_and_lexical_path_refused(self):
        for key,value in (('APFSVolumeGroupID',uuid(99)),('MountPoint','/Volumes/../private')):
            r,_=self.snapshot(lambda v:v['data_info'].update({key:value}));self.assertEqual(r.returncode,2)
    def test_duplicated_device_or_ambiguous_role_refused(self):
        r,_=self.snapshot(lambda v:v['apfs_list']['Containers'][0]['Volumes'].append(copy.deepcopy(v['apfs_list']['Containers'][0]['Volumes'][2])));self.assertEqual(r.returncode,2)
    def test_nonabsent_unknown_security_metadata_fixed_refusal(self):
        for key in ('auxp','prot','smb5'):
            r,s=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy']+f'({key}): '+'d'*64+'\n'));self.assertEqual(r.returncode,2);self.assertEqual(s['reason'],'unsupportedPolicyMetadata');self.assertNotIn('dddd',json.dumps(s))
    def test_duplicate_semantic_field_or_invalid_scalar_refused(self):
        for suffix in ('(sip0): 0\n','(sip0): -1\n'):
            r,_=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy']+suffix));self.assertEqual(r.returncode,2)
    def test_empty_group_components_are_not_silently_skipped(self):
        for text in ('(smb0,,smb1)','(smb0, ,smb1)','(smb0,smb1,)'):
            r,_=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy'].replace('(smb0, smb1)',text)));self.assertEqual(r.returncode,2)
    def test_selection_or_original_policy_change_during_read_refused(self):
        for field,replacement in (('lab_policy_after',policy().replace('(coih): '+'a'*64,'(coih): '+'d'*64)),
                                  ('original_policy_after',policy('Full',paired=False).replace('(sip0): 0','(sip0): 1'))):
            r,_=self.snapshot(lambda v:v.update({field:replacement}));self.assertEqual(r.returncode,2)
    def test_original_ctrr_cannot_be_disabled_even_if_mode_label_full(self):
        r,_=self.snapshot(lambda v:v.update(original_policy=policy('Full',ctrr='disabled',paired=False)));self.assertEqual(r.returncode,2)
    def test_lab_data_alias_cannot_send_persistent_baseline_to_other_mount(self):
        r,_=self.snapshot(lambda v:v['data_info'].update(MountPoint='/Volumes/iLinux Boot Lab - Data 1'));self.assertEqual(r.returncode,2)
    def test_external_or_unknown_internal_status_is_refused(self):
        for which in ('lab_info','original_info','preboot_info','data_info'):
            for value in (False,1):
                r,_=self.snapshot(lambda v:v[which].update(Internal=value));self.assertEqual(r.returncode,2)
    def test_ctrr_status_crosschecks_documented_flag(self):
        r,_=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy'].replace('(sip2): absent','(sip2): 1')));self.assertEqual(r.returncode,2)
    def test_initial_model_allows_unknown_ctrr_but_requires_31af(self):
        s,b=self.states();r,value=self.phase(b,'initial');self.assertEqual(r.returncode,0);self.assertFalse(value['phase_valid']);self.assertTrue(value['synthetic_control_pass'])
        r,_=self.phase(s,'initial');self.assertEqual(r.returncode,2)
    def test_candidate_postcondition_and_semantic_preservation(self):
        s,b=self.states();r,_=self.phase(s,'candidate',b);self.assertEqual(r.returncode,0)
        changed=copy.deepcopy(s);changed['lab_semantics']['sip3']=True
        r,_=self.phase(changed,'candidate',b);self.assertEqual(r.returncode,2)
    def test_raw_policy_allows_transient_none_only_when_disabled(self):
        s,b=self.states();s.update(selected_payload='NONE',selected_payload_exact=False,lab_ctrr='disabled')
        r,_=self.phase(s,'raw-policy',b);self.assertEqual(r.returncode,0)
        s['lab_ctrr']='unknown';r,_=self.phase(s,'raw-policy',b);self.assertEqual(r.returncode,2)
    def test_before_restore_accepts_unknown_payload_with_preserved_policy(self):
        s,b=self.states();s.update(selected_payload='UNKNOWN',selected_payload_exact=False)
        r,_=self.phase(s,'before-restore',b);self.assertEqual(r.returncode,0)
    def test_restored_requires_exact_boot021_and_disabled(self):
        s,b=self.states();s.update(selected_payload='BOOT021',selected_payload_exact=True,lab_ctrr='disabled')
        r,_=self.phase(s,'restored',b);self.assertEqual(r.returncode,0)
        s['lab_ctrr']='enabled';r,_=self.phase(s,'restored',b);self.assertEqual(r.returncode,2)
    def test_profile_or_original_semantic_drift_refused(self):
        s,b=self.states()
        for current in (dict(s,profile_sha256='a'*64),copy.deepcopy(s)):
            if current['profile_sha256']==s['profile_sha256']:current['original_semantics']['sip0']='0x0000000000000001'
            r,_=self.phase(current,'candidate',b);self.assertEqual(r.returncode,2)
    def test_production_validator_refuses_synthetic_snapshot(self):
        s,b=self.states();r,_=self.phase(s,'candidate',b,synthetic=False);self.assertEqual(r.returncode,2)
    def test_snapshot_value_refuses_unverified_fixture_and_wrong_key(self):
        s,_=self.states();path=self.save('fixture-state.json',s)
        for key in ('lab_ctrr','lab_group'):
            r,_=self.invoke('--snapshot-value',path,'--key',key);self.assertEqual(r.returncode,2)
    def test_duplicate_cli_profile_cannot_override_previous_argument(self):
        r,_=self.invoke('--fixture',self.save('file',{}),'--profile',self.profile_path);self.assertEqual(r.returncode,2)
    def test_uint64_boolean_confusion_and_json_depth_refused(self):
        s,b=self.states();s['lab_semantics']['sip0']=True
        r,_=self.phase(s,'candidate',b);self.assertEqual(r.returncode,2)
        path=self.scratch/'deep.json';path.write_text('{"x":'*20+'0'+'}'*20)
        r,_=self.invoke('--validate-fixture-snapshot',path,'--phase','initial');self.assertEqual(r.returncode,2)
    def test_snapshot_unknown_personal_key_numeric_bool_or_duplicate_json_refused(self):
        s,b=self.states()
        for changed in (dict(s,private_id='SYNTHETIC_PRIVATE_MARKER'),dict(s,writes_authorized=0)):
            r,value=self.phase(changed,'candidate',b);self.assertEqual(r.returncode,2);self.assertNotIn('PRIVATE',json.dumps(value))
        path=self.scratch/'dup.json';path.write_text('{"schema":1,"schema":2}')
        r,_=self.invoke('--validate-fixture-snapshot',path,'--phase','initial');self.assertEqual(r.returncode,2)
    def test_inconsistent_mode_and_semantic_flags_refused(self):
        s,b=self.states()
        for field in ('smb0','smb1'):
            changed=copy.deepcopy(s);changed['original_semantics'][field]=True
            r,_=self.phase(changed,'candidate',b);self.assertEqual(r.returncode,2)
        s['lab_semantics']['smb1']='ABSENT'
        r,_=self.phase(s,'candidate',b);self.assertEqual(r.returncode,2)
    def test_verify_file_is_restricted_to_profile_identities(self):
        path=self.scratch/'file';path.write_bytes(self.plain)
        r,value=self.invoke('--verify-file',path,'--expected-bytes',len(self.plain),'--expected-sha256',sha(self.plain));self.assertEqual(r.returncode,0);self.assertTrue(value['verified'])
        r,_=self.invoke('--verify-file',path,'--expected-bytes',len(self.plain),'--expected-sha256','a'*64);self.assertEqual(r.returncode,2)
    def test_metadata_commitments_match_independent_hmac_contract(self):
        r,s=self.snapshot();self.assertEqual(r.returncode,0);self.assertTrue(s['metadata_bound'])
        self.assertEqual(s['comparison_key_id'],sha(bytes(range(32))))
        for role,field in (('LAB','lab_metadata_hmac'),('ORIGINAL','original_metadata_hmac')):
            parts=['ilinux31aj-private-policy-v2',s['profile_sha256'],role,'rpnh','2','d'*96,'e'*96,'ronh','1','f'*96,'spih','1','1'*96,'stng','1','15']
            message=b''.join(p.encode()+b'\0' for p in parts)
            self.assertEqual(s[field],hmac.new(bytes(range(32)),message,hashlib.sha256).hexdigest())
        self.assertNotEqual(s['lab_metadata_hmac'],s['original_metadata_hmac'])
        for raw in ('d'*96,'e'*96,'f'*96,'1'*96):self.assertNotIn(raw,json.dumps(s))
    def test_keyless_initial_admission_is_separate_from_bound_initial(self):
        r,s=self.snapshot(bound=False);self.assertEqual(r.returncode,0);self.assertFalse(s['metadata_bound']);self.assertEqual(s['comparison_key_id'],'NONE')
        s['selected_payload']='31AF'
        r,value=self.phase(s,'initial-admission',bound=False);self.assertEqual(r.returncode,0);self.assertTrue(value['synthetic_control_pass'])
        for phase in ('initial','candidate','before-restore','raw-policy','restored'):
            r,_=self.phase(s,phase,bound=False);self.assertEqual(r.returncode,2)
        r,_=self.phase(s,'initial-admission');self.assertEqual(r.returncode,2)
        _,bound=self.states();r,_=self.phase(bound,'initial-admission',bound=False);self.assertEqual(r.returncode,2)
    def test_opaque_metadata_changes_are_refused_for_each_role(self):
        _,base=self.states()
        for role in ('lab_policy','original_policy'):
            for old,new in (('d'*96,'2'*96),('e'*96,'3'*96),('f'*96,'4'*96),('1'*96,'5'*96),('(stng): 15','(stng): 16')):
                with self.subTest(role=role,field=old[:8]):
                    r,s=self.snapshot(lambda v:v.update({role:v[role].replace(old,new)}));self.assertEqual(r.returncode,0)
                    r,_=self.phase(s,'candidate',base);self.assertEqual(r.returncode,2)
    def test_rpnh_order_is_part_of_comparison(self):
        _,base=self.states()
        def swap(v):v['lab_policy']=v['lab_policy'].replace('d'*96,'X'*96).replace('e'*96,'d'*96).replace('X'*96,'e'*96)
        r,s=self.snapshot(swap);self.assertEqual(r.returncode,0)
        r,_=self.phase(s,'candidate',base);self.assertEqual(r.returncode,2)
    def test_global_rotating_lpnh_is_not_compared_as_unchanged(self):
        r,a=self.snapshot();self.assertEqual(r.returncode,0)
        r,b=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy'].replace('c'*64,'9'*64),original_policy=v['original_policy'].replace('c'*64,'8'*64)));self.assertEqual(r.returncode,0)
        self.assertEqual(a['lab_metadata_hmac'],b['lab_metadata_hmac']);self.assertEqual(a['original_metadata_hmac'],b['original_metadata_hmac'])
    def test_opaque_metadata_schema_requires_exact_bounded_occurrences(self):
        for change in (lambda p:p.replace('(rpnh): '+'d'*96+'\n',''),lambda p:p+'(rpnh): '+'a'*96+'\n',lambda p:p+'(ronh): absent\n',lambda p:p+'(spih): absent\n',lambda p:p+'(stng): 1\n',lambda p:p.replace('(ronh): '+'f'*96,'(ronh): '+'f'*94),lambda p:p.replace('(spih): '+'1'*96,'(spih): PRIVATE-MARKER')):
            r,value=self.snapshot(lambda v:v.update(lab_policy=change(v['lab_policy'])));self.assertEqual(r.returncode,2);self.assertNotIn('PRIVATE',json.dumps(value))
    def test_stng_is_decimal_uint64_not_bare_hex(self):
        for value in ('0x10','a','-1','18446744073709551616','1_000','+1'):
            r,_=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy'].replace('(stng): 15','(stng): '+value)));self.assertEqual(r.returncode,2)
        for value in ('0','18446744073709551615','absent'):
            r,_=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy'].replace('(stng): 15','(stng): '+value)));self.assertEqual(r.returncode,0)
    def test_metadata_case_and_counter_leading_zeros_canonicalize(self):
        _,a=self.snapshot();_,b=self.snapshot(lambda v:v.update(lab_policy=v['lab_policy'].replace('d'*96,'D'*96).replace('(stng): 15','(stng): 00015')))
        self.assertEqual(a['lab_metadata_hmac'],b['lab_metadata_hmac'])
    def test_comparison_key_missing_wrong_or_unbound_cannot_validate(self):
        s,b=self.states();other=self.scratch/'other.key';other.write_bytes(b'Z'*32);other.chmod(0o600)
        for kwargs in ({'bound':False},{'key_path':other}):
            r,_=self.phase(s,'candidate',b,**kwargs);self.assertEqual(r.returncode,2)
        for field in ('comparison_key_id','lab_metadata_hmac','original_metadata_hmac'):
            changed=dict(s);changed[field]='a'*64;r,_=self.phase(changed,'candidate',b);self.assertEqual(r.returncode,2)
    def test_comparison_key_file_mode_symlink_linkcount_and_size(self):
        for mode in (0o644,0o400,0o1600):
            self.comparison_key.chmod(mode);r,_=self.snapshot();self.assertEqual(r.returncode,2)
        self.comparison_key.chmod(0o600)
        for data in (b'A'*31,b'A'*33):
            self.comparison_key.write_bytes(data);r,_=self.snapshot();self.assertEqual(r.returncode,2)
        self.comparison_key.write_bytes(bytes(range(32)))
        target=self.scratch/'target-key';self.comparison_key.rename(target);self.comparison_key.symlink_to(target)
        r,_=self.snapshot();self.assertEqual(r.returncode,2);self.comparison_key.unlink();target.rename(self.comparison_key)
        import os
        os.link(self.comparison_key,self.scratch/'hard-link');r,_=self.snapshot();self.assertEqual(r.returncode,2)
    def test_unreadable_selected_payload_preserves_guarded_restoration_state(self):
        _,base=self.states()
        r,s=self.snapshot(lambda v:v.update(selected_file=str(self.scratch/'missing-selected')));self.assertEqual(r.returncode,0);self.assertEqual(s['selected_payload'],'UNKNOWN');self.assertTrue(s['metadata_bound'])
        r,_=self.phase(s,'before-restore',base);self.assertEqual(r.returncode,0)
        r,_=self.phase(s,'candidate',base);self.assertEqual(r.returncode,2)
    def test_opaque_metadata_change_during_collection_refuses_snapshot(self):
        r,_=self.snapshot(lambda v:v.update(lab_policy_after=v['lab_policy'].replace('e'*96,'9'*96)));self.assertEqual(r.returncode,2)
    def test_generator_refuses_pipe_and_preserves_nonempty_file(self):
        r,text=self.invoke('--generate-comparison-key');self.assertEqual(r.returncode,2);self.assertEqual(text,'');self.assertEqual(r.stderr,'REFUSED\n')
        path=self.scratch/'existing-key';path.write_bytes(b'EXISTING-OWN-FIXTURE');path.chmod(0o600)
        with path.open('r+b') as stream:
            result=subprocess.run([str(self.binary),'--generate-comparison-key','--profile',str(self.profile_path)],stdout=stream,stderr=subprocess.PIPE,timeout=10)
        self.assertEqual(result.returncode,2);self.assertEqual(path.read_bytes(),b'EXISTING-OWN-FIXTURE')
    def test_generator_writes_only_own_32_random_bytes_to_new_private_file(self):
        path=self.scratch/'generated-own-key'
        with path.open('xb') as stream:
            path.chmod(0o600)
            result=subprocess.run([str(self.binary),'--generate-comparison-key','--profile',str(self.profile_path)],stdout=stream,stderr=subprocess.PIPE,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(path.stat().st_size,32);self.assertEqual(result.stderr,b'')
        # Do not print/store the generated key in any receipt or compare it with Apple data.
    def test_generator_bad_permissions_and_extra_options_do_not_write(self):
        for mode,args in ((0o644,[]),(0o600,['--comparison-key',str(self.comparison_key)])):
            path=self.scratch/f'generate-{mode}-{len(args)}'
            with path.open('xb') as stream:
                path.chmod(mode)
                result=subprocess.run([str(self.binary),'--generate-comparison-key','--profile',str(self.profile_path),*args],stdout=stream,stderr=subprocess.PIPE,timeout=10)
            self.assertEqual(result.returncode,2);self.assertEqual(path.stat().st_size,0)

if __name__=='__main__':unittest.main()
