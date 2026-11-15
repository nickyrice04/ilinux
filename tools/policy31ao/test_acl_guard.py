#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Own scratch ACL fixtures only; no system or boot metadata is queried."""
import ctypes
import errno
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('acl_guard31ao', HERE / 'acl_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class FakeAPI:
    def __init__(self, null=False, get_errno=0, valid=0, first=-1,
                 first_errno=errno.EINVAL, entry=False, free=0):
        self.null, self.get_errno, self.valid = null, get_errno, valid
        self.first, self.first_errno, self.entry, self.free = first, first_errno, entry, free
        self.freed = False

    def acl_get_fd_np(self, fd, kind):
        assert kind == 0x100
        ctypes.set_errno(self.get_errno)
        return None if self.null else 1

    def acl_valid(self, acl):
        return self.valid

    def acl_get_entry(self, acl, first, target):
        assert first == 0
        if self.entry:
            target._obj.value = 2
        ctypes.set_errno(self.first_errno)
        return self.first

    def acl_free(self, acl):
        self.freed = True
        return self.free


@unittest.skipUnless(sys.platform == 'darwin', 'Darwin descriptor API only')
class ACLTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / 'build' / 'policy31ao-acl-fixtures'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='own-', dir=parent)
        self.path = Path(self.temp.name)
        self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)

    def tearDown(self):
        os.close(self.fd)
        self.temp.cleanup()

    def test_empty_directory_and_file(self):
        self.assertTrue(guard.no_extended_acl(self.fd))
        fd = os.open('own-file', os.O_CREAT | os.O_EXCL | os.O_RDWR,
                     0o600, dir_fd=self.fd)
        try:
            self.assertTrue(guard.no_extended_acl(fd))
        finally:
            os.close(fd)

    def test_closed_descriptor_refused(self):
        fd = os.dup(self.fd)
        os.close(fd)
        with self.assertRaises(OSError):
            guard.no_extended_acl(fd)

    def test_unknown_retrieval_errors_refused(self):
        for error in (errno.EACCES, errno.EBADF, errno.EINVAL, errno.ENOTSUP, 0):
            with self.subTest(error=error), patch.object(guard, '_library', return_value=FakeAPI(null=True, get_errno=error)):
                with self.assertRaises(ValueError):
                    guard.no_extended_acl(self.fd)

    def test_allocated_empty_and_nonempty_conventions(self):
        for entry in (False, True):
            api = FakeAPI(first=0 if entry else -1, first_errno=0 if entry else errno.EINVAL, entry=entry)
            with patch.object(guard, '_library', return_value=api):
                self.assertEqual(guard.no_extended_acl(self.fd), not entry)
                self.assertTrue(api.freed)

    def test_invalid_acl_or_unknown_entry_result_refused_and_freed(self):
        for api in (FakeAPI(valid=-1), FakeAPI(first=1), FakeAPI(first=0),
                    FakeAPI(first=-1, first_errno=errno.EIO), FakeAPI(free=-1)):
            with patch.object(guard, '_library', return_value=api):
                with self.assertRaises(ValueError):
                    guard.no_extended_acl(self.fd)
                self.assertTrue(api.freed)

    def test_explicit_and_inherited_acl_refused(self):
        api = guard._library()
        declarations = {
            'acl_init': ([ctypes.c_int], ctypes.c_void_p),
            'acl_create_entry': ([ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int),
            'acl_set_tag_type': ([ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
            'acl_set_qualifier': ([ctypes.c_void_p, ctypes.c_void_p], ctypes.c_int),
            'acl_get_permset': ([ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int),
            'acl_add_perm': ([ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
            'acl_get_flagset_np': ([ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)], ctypes.c_int),
            'acl_get_flag_np': ([ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
            'acl_add_flag_np': ([ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
            'acl_set_fd_np': ([ctypes.c_int, ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
        }
        for name, (args, result) in declarations.items():
            getattr(api, name).argtypes, getattr(api, name).restype = args, result
        acl = ctypes.c_void_p(api.acl_init(1))
        self.assertTrue(acl.value)
        try:
            entry, perms, flags = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
            self.assertEqual(api.acl_create_entry(ctypes.byref(acl), ctypes.byref(entry)), 0)
            self.assertEqual(api.acl_set_tag_type(entry, 1), 0)  # ALLOW
            # Synthetic unknown principal: never a host/user UUID or identifier.
            principal = (ctypes.c_ubyte * 16)(*([1] * 16))
            self.assertEqual(api.acl_set_qualifier(entry, ctypes.cast(principal, ctypes.c_void_p)), 0)
            self.assertEqual(api.acl_get_permset(entry, ctypes.byref(perms)), 0)
            for permission in (1 << 1, 1 << 2, 1 << 3):
                self.assertEqual(api.acl_add_perm(perms, permission), 0)
            self.assertEqual(api.acl_get_flagset_np(entry, ctypes.byref(flags)), 0)
            for inheritance in (1 << 5, 1 << 6):
                self.assertEqual(api.acl_add_flag_np(flags, inheritance), 0)
            self.assertEqual(api.acl_valid(acl), 0)
            self.assertEqual(api.acl_set_fd_np(self.fd, acl, 0x100), 0)
            self.assertFalse(guard.no_extended_acl(self.fd))
            os.mkdir('own-child', 0o700, dir_fd=self.fd)
            child = os.open('own-child', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
            try:
                self.assertFalse(guard.no_extended_acl(child))
                inherited = api.acl_get_fd_np(child, 0x100)
                self.assertTrue(inherited)
                try:
                    inherited_entry, inherited_flags = ctypes.c_void_p(), ctypes.c_void_p()
                    self.assertEqual(api.acl_get_entry(inherited, 0, ctypes.byref(inherited_entry)), 0)
                    self.assertEqual(api.acl_get_flagset_np(inherited_entry, ctypes.byref(inherited_flags)), 0)
                    self.assertEqual(api.acl_get_flag_np(inherited_flags, 1 << 4), 1)
                finally:
                    self.assertEqual(api.acl_free(inherited), 0)
            finally:
                os.close(child)
            child_file = os.open('own-child-file', os.O_CREAT | os.O_EXCL | os.O_RDWR,
                                 0o600, dir_fd=self.fd)
            try:
                self.assertFalse(guard.no_extended_acl(child_file))
            finally:
                os.close(child_file)
        finally:
            self.assertEqual(api.acl_free(acl), 0)

    def test_real_allocated_empty_acl_convention(self):
        api = guard._library()
        api.acl_init.argtypes = [ctypes.c_int]
        api.acl_init.restype = ctypes.c_void_p
        acl = api.acl_init(0)
        self.assertTrue(acl)
        try:
            self.assertEqual(api.acl_valid(acl), 0)
            entry = ctypes.c_void_p()
            ctypes.set_errno(0)
            self.assertEqual(api.acl_get_entry(acl, 0, ctypes.byref(entry)), -1)
            self.assertEqual(ctypes.get_errno(), errno.EINVAL)
            self.assertFalse(entry.value)
        finally:
            self.assertEqual(api.acl_free(acl), 0)


if __name__ == '__main__':
    unittest.main()
