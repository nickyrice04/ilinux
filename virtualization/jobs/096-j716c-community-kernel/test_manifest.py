#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""An altered caller manifest must never replace this recipe's input authority."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('manifest_prepare096',HERE/'prepare.py')
PREPARE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(PREPARE)
PIN=(HERE/'inputs.json').read_bytes()


class Manifest(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.path=self.root/'manifest.json'

    def test_only_exact_recipe_manifest_is_authority(self):
        self.path.write_bytes(PIN)
        value=PREPARE.load_pinned_manifest(self.root)
        self.assertEqual(value['kernel_commit'],'a59e709c737777495c84541c6afb6c862bb79227')
        self.assertEqual(len(value['files']),21)

    def test_same_length_altered_input_hash_refuses(self):
        changed=PIN.replace(b'eab48ef9',b'fab48ef9',1)
        self.assertEqual(len(changed),len(PIN))
        self.assertNotEqual(changed,PIN)
        self.path.write_bytes(changed)
        with self.assertRaises(ValueError):PREPARE.load_pinned_manifest(self.root)

    def test_growing_and_truncated_manifests_refuse(self):
        for changed in (PIN+b' ',PIN[:-1]):
            self.path.write_bytes(changed)
            with self.assertRaises(ValueError):PREPARE.load_pinned_manifest(self.root)

    def test_symlink_to_other_exact_manifest_refuses(self):
        target=self.root/'other.json';target.write_bytes(PIN)
        self.path.symlink_to(target)
        with self.assertRaises(ValueError):PREPARE.load_pinned_manifest(self.root)

    def test_missing_manifest_refuses(self):
        with self.assertRaises(ValueError):PREPARE.load_pinned_manifest(self.root)


if __name__=='__main__':unittest.main()
