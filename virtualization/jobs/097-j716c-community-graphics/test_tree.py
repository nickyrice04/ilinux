#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare generated original archive trees against the independent Git CLI."""
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('tree', Path(__file__).with_name('source_tree.py'))
tree = importlib.util.module_from_spec(spec); spec.loader.exec_module(tree)


class Tree(unittest.TestCase):
    def fixture(self, rows, export_crlf=False):
        temporary = tempfile.TemporaryDirectory(prefix='ilinux097-own-tree-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name); checkout = root / 'checkout'; checkout.mkdir()
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
        subprocess.run(['git', 'init', '-q', str(checkout)], check=True, env=env)
        archive = root / 'own.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            for name, data in rows.items():
                p = checkout / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
                exported = data.replace(b'\n', b'\r\n') if export_crlf else data
                member = tarfile.TarInfo('fixture/' + name); member.size = len(exported); member.mode = 0o644
                tar.addfile(member, io.BytesIO(exported))
        subprocess.run(['git', '-C', str(checkout), 'add', '.'], check=True, env=env)
        expected = subprocess.check_output(['git', '-C', str(checkout), 'write-tree'], env=env, text=True).strip()
        return archive, expected

    def test_nested_git_sort(self):
        archive, expected = self.fixture({'a.txt': b'original\n', 'a/z.txt': b'nested\n', 'a0.txt': b'end\n'})
        self.assertEqual(tree.verify(archive, expected)['git_tree'], expected)

    def test_explicit_csv_export_eol(self):
        archive, expected = self.fixture({'data/a.csv': b'a,b\n1,2\n'}, True)
        with self.assertRaises(ValueError): tree.verify(archive, expected)
        self.assertEqual(len(tree.verify(archive, expected, True)['export_eol_normalizations']), 1)

    def test_explicit_amd_export_eol(self):
        archive, expected = self.fixture({'src/amd/ci/vkd3d-own.txt': b'original\n'}, True)
        self.assertEqual(len(tree.verify(archive, expected, True)['export_eol_normalizations']), 1)

    def test_unlisted_eol_stays_exact(self):
        archive, expected = self.fixture({'src/own.c': b'int own;\n'}, True)
        with self.assertRaises(ValueError): tree.verify(archive, expected, True)


if __name__ == '__main__': unittest.main()
