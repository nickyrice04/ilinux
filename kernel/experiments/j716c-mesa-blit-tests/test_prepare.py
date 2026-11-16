#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test the isolated transform against already-held exact source, as data only."""
import argparse
import difflib
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('blit_test_transform',HERE/'prepare_test.py')
probe=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(probe)
SOURCE=None


class Transform(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'source';self.root.mkdir()
        for name in probe.PINS:
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(SOURCE/name,target)

    def test_exact_transform_preserves_source_and_driver(self):
        before={n:(self.root/n).read_bytes() for n in probe.PINS}
        original,changed,driver=probe.derive(self.root)
        self.assertNotEqual(original,changed)
        self.assertEqual(driver,before[probe.DRIVER])
        self.assertEqual(before,{n:(self.root/n).read_bytes() for n in probe.PINS})

    def test_all_existing_nonpolicy_assertions_are_retained(self):
        old,new,_=probe.derive(self.root)
        prefix=old.decode().split('static struct pipe_resource *\nmake_buffer(')[0]
        self.assertTrue(prefix)
        tail=old.decode().split(probe.OLD)[1]
        self.assertTrue(new.decode().endswith(tail))
        for required in ('AGX_G17P_BLIT_REQUIRE_ENCODE','ctx->skipped_no_program',
                         'blit took the compute path on a non-AGX2 chip',
                         'AGX3 render target compression does not follow the G17P'):
            self.assertEqual(old.count(required.encode()),new.count(required.encode()))
        self.assertIn(b'check_cpu_transfer_roundtrip(pctx)',new)
        self.assertIn(b': PIPE_TEXTURE_TRANSFER_DEFAULT',new)

    def test_test_or_driver_substitution_refuses(self):
        for name in probe.PINS:
            path=self.root/name;original=path.read_bytes();path.write_bytes(original+b' ')
            with self.assertRaises(ValueError):probe.derive(self.root)
            path.write_bytes(original)

    def test_source_leaf_symlink_refuses(self):
        path=self.root/probe.TEST;other=path.with_suffix('.held');path.rename(other);path.symlink_to(other)
        with self.assertRaises(ValueError):probe.derive(self.root)

    def test_published_patch_matches_exact_derivative(self):
        old,new,_=probe.derive(self.root)
        diff=''.join(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),
                fromfile='a/'+probe.TEST,tofile='b/'+probe.TEST))
        self.assertEqual(diff,(HERE/'test-only.patch').read_text())
        self.assertEqual(diff.count('--- a/'),1)
        self.assertNotIn('--- a/'+probe.DRIVER,diff)

    def test_cli_refuses_source_overwrite_and_existing_output(self):
        for output in (self.root/'new-test.c',self.root/probe.TEST):
            run=subprocess.run([sys.executable,'-I',str(HERE/'prepare_test.py'),
              '--source-root',str(self.root),'--output',str(output)],capture_output=True)
            self.assertNotEqual(run.returncode,0)
        outside=Path(self.temp.name)/'existing.c';outside.write_bytes(b'preserved')
        run=subprocess.run([sys.executable,'-I',str(HERE/'prepare_test.py'),
          '--source-root',str(self.root),'--output',str(outside)],capture_output=True)
        self.assertNotEqual(run.returncode,0);self.assertEqual(outside.read_bytes(),b'preserved')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    args,remaining=parser.parse_known_args();SOURCE=args.source_root
    # Exact source is required: missing fixtures are never represented as a pass.
    for name,pin in probe.PINS.items():
        if hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()!=pin:
            raise SystemExit('PINNED_SOURCE_REQUIRED')
    unittest.main(argv=[sys.argv[0]]+remaining)
