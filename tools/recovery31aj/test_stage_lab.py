# SPDX-License-Identifier: MIT
"""Only injected workspace fixtures; never --stage, LiveBackend or /Volumes.

Small synthetic rollback bytes replace only the in-memory profile module's two
immutable rollback constants. Real profile/candidate/boot021 pins remain unchanged.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sp=importlib.util.spec_from_file_location('stage_lab_tested',HERE/'stage_lab.py')
s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s)


def sha(data):return hashlib.sha256(data).hexdigest()
def uuid(n):return f'{n:08x}-0000-0000-0000-{n:012x}' # Synthetic only.


def metadata():
    def volume(name,role,n):return {'Name':name,'Roles':[role],'DeviceIdentifier':f'disk3s{n}','APFSVolumeUUID':uuid(n)}
    lab=volume('iLinux Boot Lab','System',1);original=volume('Macintosh HD','System',2)
    data=volume('iLinux Boot Lab - Data','Data',3);preboot=volume('Preboot','Preboot',4)
    def info(v,mount,group):return {'Internal':True,'VolumeName':v['Name'],'MountPoint':mount,
      'APFSContainerReference':'disk3','VolumeUUID':v['APFSVolumeUUID'],
      'APFSVolumeGroupID':uuid(group),'DeviceIdentifier':v['DeviceIdentifier']}
    d=info(data,s.DATA,11);d['FileVault']=False
    return {'platform':'darwin','euid':0,'model':'Mac17,6','lab':info(lab,s.LAB,11),
      'data':d,'original':info(original,'/',22),
      'apfs':{'Containers':[{'ContainerReference':'disk3','Volumes':[lab,original,data,preboot]}]}}


class FixtureBackend:
    synthetic=True
    def __init__(self,root):self.fixture_root=root/'targets';self.value=metadata();self.calls=0;self.hook=None
    def observe(self,frozen):
        self.calls+=1
        if self.hook:self.hook(self.calls)
        return copy.deepcopy(self.value)


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        raw=b'SYNTHETIC-RAW-021';self.raw=raw
        for key,value in (('ROLLBACK_BYTES',len(raw)),('ROLLBACK_SHA',sha(raw))):
            p=patch.object(s.profile,key,value);p.start();self.addCleanup(p.stop)
        self.source=self.root/'build/prepared';self.source.mkdir(parents=True)
        files={}
        for role,name in s.profile.NAMES.items():
            data=raw if role=='rollback' else ('SYNTHETIC-'+role).encode()
            (self.source/name).write_bytes(data);files[role]={'name':name,'bytes':len(data),'sha256':sha(data)}
        self.profile={'schema':s.profile.SCHEMA,'target':dict(s.profile.TARGET),'files':files,
          'initial_payload':'31AF','final_payload':'BOOT021','raw_policy_strategy':'ctrr_only',
          'native_deadline_ms':90000,'publication_authorizes_writes':False}
        rawprofile=s.profile.canonical(self.profile);(self.source/'profile.json').write_bytes(rawprofile)
        (self.root/s.PROFILE).parent.mkdir(parents=True);(self.root/s.PROFILE).write_bytes(rawprofile)
        names=['tools/recovery31aj/'+name for name in ('profile.py','model.py','render.py','prepare.py','test_recovery.py','README.md','stage_lab.py','test_stage_lab.py')]+[s.GUARD]
        for name in names:
            f=self.root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((ROOT/name).read_bytes())
        self.pinned=names+[s.PROFILE];self.inventory=self.root/s.INVENTORY;self.repin()
        self.backend=FixtureBackend(self.root)
        self.base=self.backend.fixture_root/'lab-data/Users/Shared/iLinuxBoot';self.base.mkdir(parents=True)
        self.dest=self.base/s.DESTINATION
    def repin(self):
        self.inventory.write_text(''.join(sha((self.root/n).read_bytes())+'  '+n+'\n' for n in self.pinned))
    def stage(self):return s._stage(self.source,self.inventory,backend=self.backend,root=self.root)
    def refused(self,before_queries=False):
        with self.assertRaises((ValueError,OSError)):
            self.stage()
        self.assertFalse(self.dest.exists())
        if before_queries:self.assertEqual(self.backend.calls,0)
    def test_exact_four_new_files_and_private_modes(self):
        r=self.stage();self.assertEqual(r['scope'],'SYNTHETIC_CONTROL');self.assertTrue(r['staged'])
        self.assertEqual(set(p.name for p in self.dest.iterdir()),set(p.name for p in self.source.iterdir()))
        self.assertEqual(self.dest.stat().st_mode&0o777,0o700)
        for p in self.dest.iterdir():
            self.assertEqual(p.read_bytes(),(self.source/p.name).read_bytes())
            self.assertEqual(p.stat().st_mode&0o777,0o700 if p.name=='ilinux31aj-reader' else 0o600)
        encoded=json.dumps(r)
        for private in (uuid(11),str(self.root),s.DATA):self.assertNotIn(private,encoded)
        for key in ('boot_settings_changed','policy_read','boot_object_installed','default_changed','volume_created','native_ready'):self.assertIs(r[key],False)
    def test_default_and_help_have_no_live_calls(self):
        with patch.object(s,'_stage') as stage,contextlib.redirect_stdout(io.StringIO()):self.assertEqual(s.main([]),0)
        stage.assert_not_called()
        with patch.object(s,'_stage') as stage,contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as e:s.main(['--help'])
        self.assertEqual(e.exception.code,0);stage.assert_not_called()
    def test_bad_source_hash_before_target_query(self):
        (self.source/'candidate.macho').write_bytes(b'BAD');self.refused(True)
    def test_profile_must_match_reviewed_git_source(self):
        p=copy.deepcopy(self.profile);p['native_deadline_ms']=30000
        (self.source/'profile.json').write_bytes(s.profile.canonical(p));self.refused(True)
    def test_unreviewed_or_changed_source_inventory_refused(self):
        (self.root/'tools/recovery31aj/stage_lab.py').write_text('# changed\n');self.refused(True)
    def test_arbitrary_inventory_path_refused(self):
        other=self.root/'other-inventory';other.write_bytes(self.inventory.read_bytes())
        self.inventory=other;self.refused(True)
    def test_missing_stage_source_pin_refused(self):
        self.pinned.remove('tools/recovery31aj/test_stage_lab.py');self.repin();self.refused(True)
    def test_unknown_extra_source_file_refused(self):
        (self.source/'extra').touch();self.refused(True)
    def test_symlink_source_refused_before_query(self):
        f=self.source/'candidate.macho';data=f.read_bytes();f.unlink()
        other=self.root/'other';other.write_bytes(data);f.symlink_to(other);self.refused(True)
    def test_source_directory_outside_build_refused(self):
        self.source=self.root/'outside';self.source.mkdir();self.refused(True)
    def test_wrong_machine_or_nonroot_refused(self):
        for key,value in (('model','Mac14,2'),('euid',501),('euid',False),('platform','linux')):
            with self.subTest(key=key):
                old=self.backend.value[key];self.backend.value[key]=value;self.refused();self.backend.value[key]=old
    def test_wrong_current_installation_refused(self):
        self.backend.value['original']['VolumeName']='Another OS';self.refused()
    def test_external_internal_numeric_or_filevault_unknown_refused(self):
        for key,value in (('Internal',False),('Internal',1),('FileVault',True),('FileVault',None)):
            with self.subTest(key=key,value=value):
                old=self.backend.value['data'].get(key);self.backend.value['data'][key]=value;self.refused();self.backend.value['data'][key]=old
    def test_wrong_data_group_container_mount_or_role_refused(self):
        def group(v):v['data']['APFSVolumeGroupID']=uuid(99)
        def container(v):v['data']['APFSContainerReference']='disk9'
        def mount(v):v['data']['MountPoint']='/wrong'
        def role(v):v['apfs']['Containers'][0]['Volumes'][2]['Roles']=['System']
        for change in (group,container,mount,role):
            with self.subTest(change=change.__name__):
                old=copy.deepcopy(self.backend.value);change(self.backend.value);self.refused();self.backend.value=old
    def test_original_lab_shared_group_refused(self):
        self.backend.value['original']['APFSVolumeGroupID']=self.backend.value['lab']['APFSVolumeGroupID'];self.refused()
    def test_existing_destination_never_overwritten(self):
        self.dest.mkdir();sentinel=self.dest/'sentinel';sentinel.write_text('KEEP')
        with self.assertRaises(ValueError):self.stage()
        self.assertEqual(sentinel.read_text(),'KEEP')
    def test_existing_state_even_symlink_refused(self):
        (self.base/s.STATE).symlink_to(self.root/'missing');self.refused()
    def test_symlink_base_component_refused(self):
        original=self.base;renamed=original.with_name('elsewhere');original.rename(renamed);original.symlink_to(renamed)
        self.refused();self.assertEqual(list(renamed.iterdir()),[])
    def test_source_changed_after_initial_hash_before_copy_refused(self):
        def hook(n):
            if n==1:(self.source/'candidate.macho').write_bytes(b'CHANGED')
        self.backend.hook=hook;self.refused()
    def test_source_changed_after_copy_cleans_only_new_destination(self):
        def hook(n):
            if n==2:(self.source/'candidate.macho').write_bytes(b'CHANGED')
        self.backend.hook=hook;self.refused()
    def test_target_binding_change_after_copy_refused(self):
        def hook(n):
            if n==2:self.backend.value['data']['APFSVolumeGroupID']=uuid(99)
        self.backend.hook=hook;self.refused()
    def test_source_profile_pin_missing_refused(self):
        self.pinned.remove(s.PROFILE);self.repin();self.refused(True)
    def test_destination_swapped_after_copy_is_not_confirmed_or_removed(self):
        foreign=self.root/'foreign-kit';foreign.mkdir();sentinel=foreign/'sentinel';sentinel.write_text('KEEP')
        moved=self.base/'moved-created-kit'
        def hook(n):
            if n==2:self.dest.rename(moved);self.dest.symlink_to(foreign)
        self.backend.hook=hook
        with self.assertRaises((ValueError,OSError)):self.stage()
        self.assertTrue(self.dest.is_symlink());self.assertEqual(sentinel.read_text(),'KEEP')
        self.assertEqual(list(moved.iterdir()),[])
    def test_extra_destination_file_refuses_and_preserves_foreign_file(self):
        extra=self.dest/'foreign.txt'
        def hook(n):
            if n==2:extra.write_text('KEEP')
        self.backend.hook=hook
        with self.assertRaises((ValueError,OSError)):self.stage()
        self.assertEqual(extra.read_text(),'KEEP');self.assertEqual([p.name for p in self.dest.iterdir()],['foreign.txt'])
    def test_base_path_replaced_after_copy_refuses_and_preserves_replacement(self):
        moved=self.base.with_name('moved-original-base')
        def hook(n):
            if n==2:
                self.base.rename(moved);self.base.mkdir();(self.base/'sentinel').write_text('KEEP')
        self.backend.hook=hook
        with self.assertRaises((ValueError,OSError)):self.stage()
        self.assertEqual((self.base/'sentinel').read_text(),'KEEP')
        self.assertFalse((moved/s.DESTINATION).exists())


if __name__=='__main__':unittest.main(verbosity=2)
