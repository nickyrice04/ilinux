#!/usr/bin/env python3
"""Original offline tests; input image is data, never executable host code."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('builder',HERE/'build_recorder.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def branch_target(word,pc):
    return pc+m.audit.signed(word&0x3ffffff,26)*4


class RecorderTests(unittest.TestCase):
    image_path=None
    symbols_path=None

    @classmethod
    def setUpClass(cls):
        if cls.image_path is None or cls.symbols_path is None:
            raise ValueError('Explicit --image and --symbols inputs are required; no tests are skipped')
        cls.image=cls.image_path.read_bytes()
        cls.symbols=cls.symbols_path.read_bytes()

    def test_exact_image_and_layout(self):
        before=hashlib.sha256(self.image).hexdigest()
        plan,recorder,entry=m.build(self.image,self.symbols)
        self.assertEqual(before,hashlib.sha256(self.image).hexdigest())
        self.assertEqual(plan['recorder_bytes'],204)
        self.assertFalse(plan['native_deployment_ready'])
        self.assertFalse(plan['entry_authorized'])
        self.assertEqual(plan['clobbers'],['x0','x8','NZCV'])
        self.assertFalse(plan['sp_changed']);self.assertFalse(plan['lr_changed'])
        self.assertEqual(branch_target(struct.unpack('<I',entry)[0],m.ENTRY),m.CODE_START)

    def test_exact_input_refusal(self):
        altered=bytearray(self.image);altered[0]^=1
        with self.assertRaisesRegex(ValueError,'image_digest'):
            m.build(altered,self.symbols)
        with self.assertRaisesRegex(ValueError,'symbol_digest'):
            m.build(self.image,self.symbols+b'\n')

    def test_reserved_bytes_must_be_zero(self):
        for offset in (m.CODE_START,m.CODE_END-1,m.RECORD,m.RECORD_END-1):
            altered=bytearray(self.image);altered[offset]=1
            with self.assertRaisesRegex(ValueError,'candidate_not_zero'):
                m.region_audit(altered,self.symbols)

    def test_replay_and_flag_definition_checks(self):
        for offset in (m.ENTRY,m.RESUME,0x904,0x908,0x9bc):
            altered=bytearray(self.image);altered[offset]^=1
            with self.assertRaises(ValueError):m.region_audit(altered,self.symbols)

    def test_replay_word_and_original_resume(self):
        recorder,labels=m.program()
        final_words=struct.unpack('<II',recorder[-8:])
        self.assertEqual(final_words[0],m.ORIGINAL_MOV)
        self.assertEqual(branch_target(final_words[1],m.CODE_START+len(recorder)-4),m.RESUME)
        self.assertEqual(labels['replay'],m.CODE_START+len(recorder)-8)

    def test_branches_stay_in_reserved_code_or_resume(self):
        recorder,_=m.program()
        for i in range(0,len(recorder),4):
            word=struct.unpack_from('<I',recorder,i)[0];pc=m.CODE_START+i
            if word&0xfc000000==0x14000000:
                target=branch_target(word,pc)
            elif word&0xff000010==0x54000000:
                target=pc+m.audit.signed((word>>5)&0x7ffff,19)*4
            else:continue
            self.assertTrue(target==m.RESUME or m.CODE_START<=target<m.CODE_START+len(recorder))

    def test_only_aligned_record_stores(self):
        recorder,_=m.program();offsets=set()
        for i in range(0,len(recorder),4):
            word=struct.unpack_from('<I',recorder,i)[0]
            if word&0xffc00000==0xf9000000:
                self.assertEqual((word>>5)&31,0)
                self.assertEqual(word&31,8)
                offsets.add(((word>>10)&4095)*8)
            self.assertNotEqual(word&0xfff00000,0xd5100000)  # no MSR system register
            self.assertNotEqual(word&0xfc000000,0x94000000)  # no BL/LR clobber
        self.assertEqual(offsets,{0,8,16,24})

    def test_branch_alignment_and_range_refuse(self):
        for target in (m.ENTRY+1,m.ENTRY+(1<<27),m.ENTRY-(1<<27)-4):
            with self.assertRaisesRegex(ValueError,'branch_out_of_range'):
                m.branch(m.ENTRY,target)
        with self.assertRaisesRegex(ValueError,'branch_out_of_range'):
            m.branch(m.ENTRY,m.ENTRY+(1<<20),0)
        with self.assertRaisesRegex(ValueError,'unsupported_condition'):
            m.branch(m.ENTRY,m.ENTRY,2)

    def test_output_can_only_be_ignored_owned_directory(self):
        with self.assertRaisesRegex(ValueError,'output_must_be_owned_ignored_out'):
            m.write_outputs(HERE,{},b'',b'')

    def test_all_leaf_symlinks_refuse_before_any_write(self):
        names=('recorder.bin','entry-branch.bin','plan.json')
        for blocked in names:
            with self.subTest(leaf=blocked), tempfile.TemporaryDirectory() as tmp:
                owned=Path(tmp)/'owned';directory=owned/'out'
                directory.mkdir(parents=True)
                outside=Path(tmp)/'outside.bin';outside.write_bytes(b'preserve outside')
                for name in names:(directory/name).write_bytes(b'preserve output')
                (directory/blocked).unlink()
                (directory/blocked).symlink_to(outside)
                with patch.object(m,'HERE',owned), self.assertRaisesRegex(ValueError,'output_leaf_symlink'):
                    m.write_outputs(directory,{},b'new recorder',b'new branch')
                self.assertEqual(outside.read_bytes(),b'preserve outside')
                self.assertTrue((directory/blocked).is_symlink())
                for name in names:
                    if name!=blocked:self.assertEqual((directory/name).read_bytes(),b'preserve output')
                self.assertEqual(set(p.name for p in directory.iterdir()),set(names))

    def test_hardlinks_are_replaced_without_changing_outside_inode(self):
        with tempfile.TemporaryDirectory() as tmp:
            owned=Path(tmp)/'owned';directory=owned/'out'
            directory.mkdir(parents=True)
            outside=Path(tmp)/'outside.bin';outside.write_bytes(b'preserve outside')
            expected={'recorder.bin':b'new recorder','entry-branch.bin':b'new branch',
                      'plan.json':(json.dumps({'test':True},indent=2)+'\n').encode()}
            for name in expected:os.link(outside,directory/name)
            with patch.object(m,'HERE',owned):
                m.write_outputs(directory,{'test':True},b'new recorder',b'new branch')
            self.assertEqual(outside.read_bytes(),b'preserve outside')
            for name,value in expected.items():
                path=directory/name
                self.assertEqual(path.read_bytes(),value)
                self.assertNotEqual(path.stat().st_ino,outside.stat().st_ino)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            self.assertEqual(set(p.name for p in directory.iterdir()),set(expected))

    def test_atomic_replace_failure_cleans_temporary_and_sanitizes_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            owned=Path(tmp)/'owned';directory=owned/'out'
            directory.mkdir(parents=True)
            existing=directory/'recorder.bin';existing.write_bytes(b'preserve output')
            with patch.object(m,'HERE',owned), patch.object(m.os,'replace',side_effect=OSError('raw-path-sentinel')):
                with self.assertRaisesRegex(ValueError,'^output_write_failed$'):
                    m.write_outputs(directory,{},b'new recorder',b'new branch')
            self.assertEqual(existing.read_bytes(),b'preserve output')
            self.assertEqual([p.name for p in directory.iterdir()],['recorder.bin'])

    def test_parent_resolution_error_is_sanitized(self):
        with patch.object(m.Path,'resolve',side_effect=RuntimeError('raw-path-sentinel')):
            with self.assertRaisesRegex(ValueError,'^output_write_failed$'):
                m.write_outputs(HERE/'out',{},b'',b'')

    def test_adjacent_add_accepts_both_immediate_shifts(self):
        low=0x91000000 | 0xa40 << 10
        shifted=0x91400000 | 4 << 10 | 1 << 5
        self.assertEqual(m.adjacent_add_offset(low,0),0xa40)
        self.assertEqual(m.adjacent_add_offset(shifted,1),0x4000)
        self.assertIsNone(m.adjacent_add_offset(shifted,0))
        self.assertIsNone(m.adjacent_add_offset(0xd503201f,0))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--symbols',type=Path,required=True)
    args,test_args=parser.parse_known_args()
    RecorderTests.image_path=args.image
    RecorderTests.symbols_path=args.symbols
    unittest.main(argv=[sys.argv[0],*test_args])
