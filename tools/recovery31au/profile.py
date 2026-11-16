# SPDX-License-Identifier: MIT
"""Derive the new public profile validator from unchanged original MIT source."""
import hashlib
import types

SOURCE = 'tools/recovery31aj/profile.py'
SOURCE_SHA = '3fa5fb251bee45bbf8fa352589c5fa0aba1acc64e073e318cbee175f90f68827'


def derive(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError('frozen profile source refused')
    before = data.decode('utf-8')
    old = "value['initial_payload']=='31AF'"
    new = "value['initial_payload']=='BOOT021'"
    if before.count(old) != 1:
        raise ValueError('profile selector refused')
    after = before.replace(old, new, 1)
    if after.count(new) != 1 or after.replace(new, old, 1) != before:
        raise ValueError('profile reversal refused')
    module = types.ModuleType('verified31au_profile')
    exec(compile(after, SOURCE, 'exec'), module.__dict__)
    module.SCHEMA = 'ilinux31au-recovery-profile-v1'
    module.NAMES = dict(module.NAMES, helper='ilinux31au-reader')
    return module
