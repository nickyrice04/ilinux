#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Darwin descriptor-only ACL refusal; importing this module is inert.

Local SDK sys/acl.h and acl_get_entry(3) define FIRST_ENTRY=0 and success=0.
Own APFS fixtures qualify NULL/ENOENT as an absent extended ACL.  Every
nonempty ACL is refused, without inspecting or returning its principals.
"""
import ctypes
import errno
import os
import stat
import sys


ACL_TYPE_EXTENDED = 0x100
ACL_FIRST_ENTRY = 0


def _library():
    if sys.platform != 'darwin':
        raise ValueError('ACL observation refused')
    api = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    api.acl_get_fd_np.argtypes = [ctypes.c_int, ctypes.c_int]
    api.acl_get_fd_np.restype = ctypes.c_void_p
    api.acl_valid.argtypes = [ctypes.c_void_p]
    api.acl_valid.restype = ctypes.c_int
    api.acl_get_entry.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                  ctypes.POINTER(ctypes.c_void_p)]
    api.acl_get_entry.restype = ctypes.c_int
    api.acl_free.argtypes = [ctypes.c_void_p]
    api.acl_free.restype = ctypes.c_int
    return api


def no_extended_acl(fd):
    """True only for a valid held regular/directory FD with no extended entries.

    No pathname is resolved, ACL modified, or principal/value returned.  The
    caller retains responsibility for ownership, modes and descriptor lifetime.
    """
    if type(fd) is not int or fd < 0:
        raise ValueError('ACL observation refused')
    info = os.fstat(fd)
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError('ACL observation refused')
    api = _library()
    ctypes.set_errno(0)
    acl = api.acl_get_fd_np(fd, ACL_TYPE_EXTENDED)
    if not acl:
        if ctypes.get_errno() == errno.ENOENT:
            return True
        raise ValueError('ACL observation refused')
    try:
        if api.acl_valid(acl) != 0:
            raise ValueError('ACL observation refused')
        entry = ctypes.c_void_p()
        ctypes.set_errno(0)
        result = api.acl_get_entry(acl, ACL_FIRST_ENTRY, ctypes.byref(entry))
        error = ctypes.get_errno()
        if result == 0 and entry.value:
            return False
        if result == -1 and error == errno.EINVAL and not entry.value:
            return True
        raise ValueError('ACL observation refused')
    finally:
        if api.acl_free(acl) != 0:
            raise ValueError('ACL observation refused')
