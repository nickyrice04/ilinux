#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Archive boundaries, using only generated original tar metadata."""
import importlib.util
from pathlib import Path
import tarfile
import unittest

spec = importlib.util.spec_from_file_location('validator', Path(__file__).with_name('validate_sources.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class Sources(unittest.TestCase):
    def member(self, name='fixture/a', kind=tarfile.REGTYPE, link=''):
        m = tarfile.TarInfo(name); m.type = kind; m.linkname = link
        m.size = 4 if kind == tarfile.REGTYPE else 0
        return m

    def check(self, members):
        return v.members_checked(members, {'prefix': 'fixture', 'member_count': len(members),
                                          'unpacked_bytes': sum(x.size for x in members if x.isfile())})

    def test_regular(self):
        self.assertEqual(self.check([self.member()])['members'], 1)

    def test_paths(self):
        for name in ('/fixture/a', 'fixture/../x', 'fixture/./a', 'fixture//a', 'fixture\\a', 'other/a'):
            with self.subTest(name=name), self.assertRaises(ValueError): self.check([self.member(name)])

    def test_duplicate(self):
        with self.assertRaises(ValueError): self.check([self.member(), self.member()])

    def test_case_collision(self):
        with self.assertRaises(ValueError): self.check([self.member(), self.member('fixture/A')])

    def test_types(self):
        for kind in (tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), self.assertRaises(ValueError): self.check([self.member(kind=kind)])

    def test_links(self):
        self.check([self.member('fixture/d/a', tarfile.SYMTYPE, '../b')])
        for link in ('../../outside', '/etc/x', '..\\outside'):
            with self.subTest(link=link), self.assertRaises(ValueError):
                self.check([self.member(kind=tarfile.SYMTYPE, link=link)])

    def test_size(self):
        for size in (-1, 101 * 1024**2):
            m = self.member(); m.size = size
            with self.subTest(size=size), self.assertRaises(ValueError): self.check([m])


if __name__ == '__main__': unittest.main()
