#!/usr/bin/env python3
"""Synthetic parser/integrity regressions; never inspect or launch an installer."""
import importlib.util
import lzma
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zlib

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('verifier', HERE / 'verify-installer.py')
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def entry(name, mode=stat.S_IFREG | 0o644, content=b''):
    name = name.encode() + b'\0'
    header = ('070707' + ''.join('%06o' % n for n in [0, 0, mode, 0, 0, 1, 0]) +
              '%011o%06o%011o' % (0, len(name), len(content)))
    return header.encode() + name + content


def archive(*items):
    return b''.join(items) + entry('TRAILER!!!')


def pbzx_chunk(content):
    return b'pbzx' + struct.pack('>QQQ', 1 << 24, 0, len(content)) + content


class ParserTests(unittest.TestCase):
    def test_zlib_bounded_and_complete(self):
        data = zlib.compress(b'example')
        self.assertEqual(verifier.inflate(data, 7), b'example')
        for candidate, limit in [(data, 6), (data[:-1], 7), (data + b'x', 7)]:
            with self.subTest(candidate=candidate, limit=limit):
                with self.assertRaises(ValueError):
                    verifier.inflate(candidate, limit)

    def test_pbzx_plain_and_xz(self):
        for content in [b'example', lzma.compress(b'example')]:
            self.assertEqual(verifier.pbzx(pbzx_chunk(content)), b'example')

    def test_pbzx_rejects_invalid_framing(self):
        valid = pbzx_chunk(b'example')
        for data in [b'', valid[:-1], valid + b'x', valid[:13]]:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    verifier.pbzx(data)

    def test_cpio_rejects_truncation_paths_and_duplicates(self):
        valid = archive(entry('./file', content=b'abc'))
        bad = [valid[:-1], archive(entry('../escape')), archive(entry('/absolute')),
               archive(entry('./file'), entry('file')), valid + b'x',
               archive(entry('a\0b'))]
        for data in bad:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    list(verifier.cpio_entries(data))

    def test_tool_failures_are_not_accepted(self):
        for result in [subprocess.CompletedProcess([], 1, 'source=Apple Installer', ''),
                       subprocess.CompletedProcess([], 0, 'something else', '')]:
            with patch.object(verifier.subprocess, 'run', return_value=result):
                with self.assertRaises(ValueError):
                    verifier.checked_tool(['fake'], 'source=Apple Installer')


class InstalledAppTests(unittest.TestCase):
    def setUp(self):
        work = HERE.parents[1] / 'build' / 'installer-verification' / 'test-tmp'
        work.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name) / 'Install macOS Tahoe.app'
        (self.app / 'Contents/SharedSupport').mkdir(parents=True)
        (self.app / 'Contents/SharedSupport/SharedSupport.dmg').write_bytes(b'fixture')
        (self.app / 'Contents/file').write_bytes(b'original')
        (self.app / 'Contents/link').symlink_to('file')
        prefix = './Applications/' + self.app.name + '/Contents'
        self.payload = archive(entry(prefix, stat.S_IFDIR | 0o755),
                               entry(prefix + '/file', content=b'original'),
                               entry(prefix + '/link', stat.S_IFLNK | 0o777, b'file'))

    def test_exact_files_and_links_pass(self):
        self.assertEqual(verifier.compare_app(self.payload, self.app),
                         {'directory': 1, 'file': 1, 'symlink': 1})

    def test_changed_file_fails(self):
        (self.app / 'Contents/file').write_bytes(b'changed!')
        with self.assertRaisesRegex(ValueError, 'file mismatch'):
            verifier.compare_app(self.payload, self.app)

    def test_changed_link_fails(self):
        link = self.app / 'Contents/link'
        link.unlink()
        link.symlink_to('SharedSupport')
        with self.assertRaisesRegex(ValueError, 'Symlink mismatch'):
            verifier.compare_app(self.payload, self.app)

    def test_unexpected_addition_fails(self):
        (self.app / 'Contents/addition').write_bytes(b'new')
        with self.assertRaisesRegex(ValueError, 'Unexpected app entries'):
            verifier.compare_app(self.payload, self.app)

    def test_replaced_file_type_fails(self):
        path = self.app / 'Contents/file'
        path.unlink()
        path.symlink_to('SharedSupport/SharedSupport.dmg')
        with self.assertRaisesRegex(ValueError, 'file mismatch'):
            verifier.compare_app(self.payload, self.app)

    def test_missing_file_fails(self):
        os.unlink(self.app / 'Contents/file')
        with self.assertRaises(FileNotFoundError):
            verifier.compare_app(self.payload, self.app)


if __name__ == '__main__':
    unittest.main()
