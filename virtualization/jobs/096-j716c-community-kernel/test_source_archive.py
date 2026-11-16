#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('source096',HERE/'source_archive.py')
source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)


def git_hash(kind,data):
    return bytes.fromhex(subprocess.check_output(['/usr/bin/git','hash-object','-t',kind,'--stdin'],input=data,cwd=ROOT).decode().strip())


class Archive(unittest.TestCase):
    def setUp(self):
        base=ROOT/'build/j716c-community-kernel/source-tests';base.mkdir(parents=True,exist_ok=True)
        self.directory=tempfile.TemporaryDirectory(dir=base);self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'fixture.tar'

    def tar(self,rows):
        with tarfile.open(self.path,'w') as tar:
            root=tarfile.TarInfo('linux-fixture');root.type=tarfile.DIRTYPE;tar.addfile(root)
            for name,data,mode in rows:
                entry=tarfile.TarInfo('linux-fixture/'+name)
                if mode=='link':entry.type=tarfile.SYMTYPE;entry.linkname=data.decode();tar.addfile(entry)
                elif mode=='device':entry.type=tarfile.CHRTYPE;tar.addfile(entry)
                else:entry.mode=mode;entry.size=len(data);tar.addfile(entry,io.BytesIO(data))

    def test_case_distinct_and_executable_and_symlink_match_git(self):
        rows=[('A',b'upper',0o644),('a',b'lower',0o644),('foo.z',b'z',0o644),
              ('foo/run',b'own executable',0o755),('link',b'foo/run','link')]
        self.tar(rows)
        subtree=git_hash('tree',b'100755 run\0'+git_hash('blob',b'own executable'))
        expected=git_hash('tree',b'100644 A\0'+git_hash('blob',b'upper')+
            b'100644 a\0'+git_hash('blob',b'lower')+b'100644 foo.z\0'+git_hash('blob',b'z')+
            b'40000 foo\0'+subtree+b'120000 link\0'+git_hash('blob',b'foo/run')).hex()
        result=source.verify(self.path,expected)
        self.assertEqual(result['files'],5);self.assertEqual(result['symlinks'],1)
        self.assertFalse(result['source_extracted_on_host'])

    def test_wrong_tree_refused(self):
        self.tar([('a',b'own',0o644)])
        with self.assertRaisesRegex(ValueError,'tree mismatch'):source.verify(self.path,'0'*40)

    def test_duplicate_refused(self):
        self.tar([('a',b'one',0o644),('a',b'two',0o644)])
        with self.assertRaisesRegex(ValueError,'duplicate'):source.verify(self.path,'0'*40)

    def test_parent_escape_refused(self):
        self.tar([('../outside',b'own',0o644)])
        with self.assertRaisesRegex(ValueError,'path refused'):source.verify(self.path,'0'*40)

    def test_special_entry_refused(self):
        self.tar([('bad',b'','device')])
        with self.assertRaisesRegex(ValueError,'special entry'):source.verify(self.path,'0'*40)

    def test_file_directory_collision_refused(self):
        self.tar([('a',b'own',0o644),('a/b',b'own',0o644)])
        with self.assertRaisesRegex(ValueError,'collision'):source.verify(self.path,'0'*40)


if __name__=='__main__':unittest.main(verbosity=2)
