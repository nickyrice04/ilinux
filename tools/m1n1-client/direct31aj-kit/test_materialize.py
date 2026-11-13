#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Workspace-only materialization controls; no lab path, binary or live call."""
import contextlib
import copy
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('materialize31aj_test',HERE/'materialize.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

class Materialize(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name).resolve();self.folder=self.repo/'build'/'download';self.folder.mkdir(parents=True)
        self.output=self.repo/'build'/'prepared'
        self.sidecar=self.output.with_name(self.output.name+'.materialization.json')
        self.candidate=b'SYNTHETIC-CANDIDATE';self.reader=b'SYNTHETIC-READER';self.rollback=b'SYNTHETIC-ROLLBACK'
        for key,value in (('ROLLBACK_BYTES',len(self.rollback)),('ROLLBACK_SHA',tool.p.sha(self.rollback))):
            patch=mock.patch.object(tool.p,key,value);patch.start();self.addCleanup(patch.stop)
        encoded=gzip.compress(self.candidate,mtime=0)
        (self.folder/'aura-31aj-inline.macho.gz').write_bytes(encoded)
        (self.folder/'readback31aj').write_bytes(self.reader)
        (self.folder/'m1n1-boot021.bin').write_bytes(self.rollback)
        self.profile_path=self.repo/'native/boot/attempt31aj-kit/recovery-profile.json'
        self.profile_path.parent.mkdir(parents=True)
        self.reader_source=self.repo/'tools/recovery31aj/profile.py';self.reader_source.parent.mkdir(parents=True)
        source=(tool.ROOT/'tools/recovery31aj/profile.py').read_text()
        source=source.replace('ROLLBACK_BYTES = 3932160','ROLLBACK_BYTES = '+str(len(self.rollback)))
        source=source.replace('ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664',tool.p.sha(self.rollback))
        self.reader_source.write_text(source)
        self.profile=tool.module('synthetic_materializer_profile',self.reader_source)
        bodies={'candidate':self.candidate,'helper':self.reader,'rollback':self.rollback}
        self.value={'schema':self.profile.SCHEMA,'target':dict(self.profile.TARGET),
          'files':{role:{'name':name,**tool.p.metadata(bodies[role])} for role,name in self.profile.NAMES.items()},
          'initial_payload':'31AF','final_payload':'BOOT021','raw_policy_strategy':'ctrr_only',
          'native_deadline_ms':90000,'publication_authorizes_writes':False}
        self.manifest={'sources':{'tools/recovery31aj/profile.py':tool.p.sha(self.reader_source.read_bytes())},
          'candidate':{'filename':'aura-31aj-inline.macho.gz',**tool.p.metadata(encoded),
            'expanded_bytes':len(self.candidate),'expanded_sha256':tool.p.sha(self.candidate)},
          'readback':{'filename':'readback31aj',**tool.p.metadata(self.reader)}}
        self.manifest_path=self.repo/'manifest.json';self.save_profile();self.save_manifest()
        self.review_patch=mock.patch.object(tool.p,'review',return_value={'status':'OFFLINE_KIT_INTEGRITY_PASS'})
        self.review=self.review_patch.start();self.addCleanup(self.review_patch.stop)
    def save_manifest(self):self.manifest_path.write_text(json.dumps(self.manifest))
    def save_profile(self,canonical=True):
        raw=self.profile.canonical(self.value) if canonical else json.dumps(self.value).encode()
        self.profile_path.write_bytes(raw)
        self.manifest['sources'][str(self.profile_path.relative_to(self.repo))]=tool.p.sha(raw)
    def prepare(self):
        self.save_manifest()
        return tool.prepare(self.manifest_path,self.folder,self.profile_path,self.output,repo=self.repo)
    def refused(self):
        with self.assertRaises((ValueError,OSError)):self.prepare()
        self.assertFalse(self.output.exists())
    def test_exact_four_files_private_modes_and_separate_receipt(self):
        previous=os.umask(0)
        try:result=self.prepare()
        finally:os.umask(previous)
        expected={'profile.json':self.profile_path.read_bytes(),'candidate.macho':self.candidate,
                  'ilinux31aj-reader':self.reader,'m1n1-boot021.bin':self.rollback}
        self.assertEqual(set(p.name for p in self.output.iterdir()),set(expected))
        self.assertEqual(self.output.stat().st_mode&0o777,0o700)
        for name,body in expected.items():
            path=self.output/name;self.assertEqual(path.read_bytes(),body)
            self.assertEqual(path.stat().st_mode&0o777,0o700 if name=='ilinux31aj-reader' else 0o600)
        self.assertTrue(self.sidecar.is_file());self.assertEqual(json.loads(self.sidecar.read_text()),result)
        for key in ('archive_members_extracted','executed','lab_data_changed','boot_settings_changed','native_ready','writes_authorized'):
            self.assertIs(result[key],False)
        self.assertNotIn(str(self.repo),json.dumps(result))
        self.review.assert_called_once()
    def test_existing_output_preserved_before_review(self):
        self.output.mkdir();sentinel=self.output/'sentinel';sentinel.write_bytes(b'KEEP')
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(sentinel.read_bytes(),b'KEEP');self.review.assert_not_called()
    def test_existing_sibling_receipt_not_overwritten(self):
        self.sidecar.write_bytes(b'KEEP');self.refused()
        self.assertEqual(self.sidecar.read_bytes(),b'KEEP');self.review.assert_not_called()
    def test_outside_build_workspace_and_traversal_refused(self):
        for output in (self.repo/'outside',self.repo.parent/'outside-workspace',
                       self.repo/'build'/'..'/'escape'):
            self.output=output
            with self.assertRaises(ValueError):self.prepare()
        self.review.assert_not_called()
    def test_output_symlink_and_parent_symlink_refused(self):
        foreign=self.repo/'foreign';foreign.mkdir();(foreign/'sentinel').write_bytes(b'KEEP')
        link=self.repo/'build'/'link';link.symlink_to(foreign)
        for output in (link,link/'new'):
            self.output=output
            with self.assertRaises(ValueError):self.prepare()
        self.assertEqual([p.name for p in foreign.iterdir()],['sentinel']);self.review.assert_not_called()
    def test_dangling_output_symlink_refused(self):
        self.output.symlink_to(self.repo/'missing')
        with self.assertRaises(ValueError):self.prepare()
        self.assertTrue(self.output.is_symlink());self.review.assert_not_called()
    def test_unbound_or_noncanonical_profile_refused(self):
        relative=str(self.profile_path.relative_to(self.repo))
        del self.manifest['sources'][relative];self.refused()
        self.save_profile(canonical=False);self.refused()
    def test_profile_candidate_and_helper_must_match_manifest(self):
        original=copy.deepcopy(self.value)
        for role in ('candidate','helper'):
            self.value=copy.deepcopy(original);self.value['files'][role]['sha256']='0'*64
            self.save_profile();self.refused()
    def test_profile_reader_source_changed_after_review_never_executes(self):
        def change(*args):
            self.reader_source.write_text('raise AssertionError("UNTRUSTED_PROFILE_EXECUTED")\n')
            return {'status':'OFFLINE_KIT_INTEGRITY_PASS'}
        self.review.side_effect=change;self.refused()
    def test_profile_path_outside_workspace_refused(self):
        self.profile_path=self.repo.parent/'outside-profile'
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse(self.output.exists())
    def test_candidate_and_reader_rechecked_after_review(self):
        for filename in ('aura-31aj-inline.macho.gz','readback31aj'):
            path=self.folder/filename;old=path.read_bytes();path.write_bytes(b'CHANGED')
            self.refused();path.write_bytes(old)
    def test_input_symlink_refused(self):
        path=self.folder/'readback31aj';path.unlink()
        target=self.repo/'reader-copy';target.write_bytes(self.reader);path.symlink_to(target)
        self.refused()
    def test_post_review_parent_symlink_cannot_redirect_output(self):
        parent=self.repo/'build'/'parent';parent.mkdir();moved=parent.with_name('moved')
        foreign=self.repo/'foreign';foreign.mkdir();self.output=parent/'new'
        def change(*args):
            parent.rename(moved);parent.symlink_to(foreign)
            return {'status':'OFFLINE_KIT_INTEGRITY_PASS'}
        self.review.side_effect=change
        with self.assertRaises((ValueError,OSError)):self.prepare()
        self.assertEqual(list(foreign.iterdir()),[]);self.assertEqual(list(moved.iterdir()),[])
    def test_descriptor_walk_refuses_symlink_inserted_after_recheck(self):
        parent=self.repo/'build'/'parent';parent.mkdir();moved=parent.with_name('moved')
        foreign=self.repo/'foreign';foreign.mkdir();self.output=parent/'new';real_open=os.open;changed=False
        def opened(path,flags,*args,**kwargs):
            nonlocal changed
            if path=='parent' and kwargs.get('dir_fd') is not None and not changed:
                changed=True;parent.rename(moved);parent.symlink_to(foreign)
            return real_open(path,flags,*args,**kwargs)
        with mock.patch.object(tool.os,'open',side_effect=opened):
            with self.assertRaises((ValueError,OSError)):self.prepare()
        self.assertTrue(changed);self.assertEqual(list(foreign.iterdir()),[]);self.assertEqual(list(moved.iterdir()),[])
    def test_cli_refusal_suppresses_private_exception(self):
        output=io.StringIO()
        argv=['materialize.py','--manifest','SYNTHETIC_PRIVATE_PATH','--folder','.', '--profile','.', '--output','.']
        with mock.patch.object(sys,'argv',argv),mock.patch.object(tool,'prepare',side_effect=ValueError('SYNTHETIC_PRIVATE_DETAIL')),contextlib.redirect_stdout(output):
            rc=tool.main()
        self.assertEqual(rc,2);self.assertNotIn('SYNTHETIC_PRIVATE',output.getvalue())
        self.assertFalse(json.loads(output.getvalue())['native_ready'])

if __name__=='__main__':unittest.main(verbosity=2)
