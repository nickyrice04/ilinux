#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Freeze the first matched J716c package set until a replacement is reviewed.

ALPM pre-transaction hook; makes no writes, queries no package repositories,
and offers no environment-variable bypass. This is update protection, not a
watchdog guardian or proof of bootability. Not installed by the build jobs.
"""
import json
import os
import re
import stat
import sys

DT = '/sys/firmware/devicetree/base/compatible'
MAX_INPUT = 1024 * 1024
MAX_DT = 8192
PROTECTED_PACKAGE = re.compile(
    r'(?:linux(?:-.*)?|m1n1(?:-.*)?|aura(?:-.*)?|uboot(?:-.*)?|u-boot(?:-.*)?|'
    r'limine(?:-.*)?|mkinitcpio(?:-.*)?|dracut(?:-.*)?|'
    r'omarchy-(?:aurora|asahi)-firmware|asahi-firmware(?:-.*)?|asahi-scripts|'
    r'mesa(?:-.*)?|vulkan(?:-.*)?|hyprland(?:-.*)?)\Z', re.ASCII)
PATHS = ('boot/', 'usr/lib/modules/', 'usr/lib/firmware/apple/',
         'usr/lib/asahi-boot/', 'usr/lib/dri/', 'usr/share/vulkan/icd.d/',
         'usr/share/glvnd/egl_vendor.d/')
LIBS = ('usr/lib/libEGL', 'usr/lib/libGL', 'usr/lib/libgbm', 'usr/lib/libvulkan',
        'usr/lib/libgallium')
FILES = ('usr/bin/Hyprland', 'usr/bin/update-m1n1')


def board_qualified(raw):
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_DT or not raw.endswith(b'\0'):
        return False
    entries = raw[:-1].split(b'\0')
    if len(set(entries)) != len(entries) or not all(
            re.fullmatch(rb'[a-z0-9,_.+-]{1,128}', entry) for entry in entries):
        return False
    return (b'apple,j716c' in entries and b'apple,t6050' in entries and
            not any(entry.startswith(b'apple,j7') and entry != b'apple,j716c'
                    for entry in entries))


def evaluate(kind, raw, compatible):
    if kind not in ('packages', 'paths') or not isinstance(raw, bytes) or len(raw) > MAX_INPUT:
        return False, 'INVALID_HOOK_INPUT'
    try:
        text = raw.decode('ascii')
    except UnicodeDecodeError:
        return False, 'INVALID_HOOK_INPUT'
    targets = text.splitlines()
    if len(targets) > 8192:
        return False, 'INVALID_HOOK_INPUT'
    protected = False
    for name in targets:
        if not name or len(name) > 1024 or not re.fullmatch(r'[A-Za-z0-9@+_.:/-]+', name):
            return False, 'INVALID_HOOK_INPUT'
        if kind == 'packages':
            if '/' in name or not re.fullmatch(r'[a-zA-Z0-9@+_.-]+', name):
                return False, 'INVALID_HOOK_INPUT'
            protected |= PROTECTED_PACKAGE.fullmatch(name) is not None
        else:
            if name.startswith('/') or any(part in ('', '.', '..') for part in name.split('/')):
                return False, 'INVALID_HOOK_INPUT'
            protected |= (name.startswith(PATHS + LIBS) or name in FILES)
    if not protected:
        return True, 'NO_PINNED_STACK_CHANGE'
    if not board_qualified(compatible):
        return False, 'EXACT_J716C_BOARD_NOT_QUALIFIED'
    return False, 'MATCHED_STACK_FROZEN_REPLACEMENT_REQUIRES_REVIEW'


def read_compatible():
    descriptor = os.open(DT, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return b''
        return os.read(descriptor, MAX_DT + 1)
    finally:
        os.close(descriptor)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('packages', 'paths'):
        allowed, reason = False, 'INVALID_INVOCATION'
    else:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        try:
            compatible = read_compatible()
        except OSError:
            compatible = b''
        allowed, reason = evaluate(sys.argv[1], raw, compatible)
    print(json.dumps({'schema': 'ilinux-j716c-update-freeze-v1', 'allowed': allowed,
                      'reason': reason, 'settings_changed': False, 'read_only': True,
                      'native_ready': False}), file=sys.stdout if allowed else sys.stderr)
    return 0 if allowed else 1


if __name__ == '__main__':
    raise SystemExit(main())
