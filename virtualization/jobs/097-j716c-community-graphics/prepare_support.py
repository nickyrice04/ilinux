#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Authenticate support packages with the qualified temporary compiler keyring.

Reuse job075's data-only package checks/extraction rules and job096's exact
selected-signer qualification. No system keyring or package installation.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def main():
    job, source, keyring, target, output = map(Path, sys.argv[1:])
    if target.exists():
        raise ValueError('FRESH_SUPPORT_PREFIX_REQUIRED')
    prepare = module('prepare', job / 'kernel-prepare.py')
    old = module('isolate', job / 'support/isolate-toolchain.py')
    space = module('space', job / 'support/package-space.py')
    packages = json.loads((job / 'support/packages.json').read_text())['packages']
    verified = []
    for row in packages:
        for suffix, size, digest in (('', 'size', 'sha256'), ('.sig', 'signature_size', 'signature_sha256')):
            p = source / (row['filename'] + suffix)
            if p.is_symlink() or p.stat().st_size != row[size] or prepare.digest(p) != row[digest]:
                raise ValueError('SUPPORT_PACKAGE_PIN')
        space.check_package_info(row, source)
        verified.append({'name': row['name'], **prepare.signature(keyring,
                        source / (row['filename'] + '.sig'), source / row['filename'], True)})
    target.mkdir(mode=0o700)
    for row in packages:
        with tarfile.open(source / row['filename'], 'r:xz') as archive:
            members = archive.getmembers()
            if len(members) > 40000:
                raise ValueError('SUPPORT_ARCHIVE_COUNT')
            admitted = [m for m in members if old.allowed_member(m)]
            if sum(m.size for m in admitted if m.isfile()) > row['installed_size']:
                raise ValueError('SUPPORT_INSTALLED_SIZE')
            archive.extractall(target, members=admitted, filter='data')
    relocated = []
    for directory in (target / 'usr/lib/pkgconfig', target / 'usr/share/pkgconfig'):
        for path in sorted(directory.glob('*.pc')):
            if path.is_symlink() or path.stat().st_size > 128 * 1024:
                raise ValueError('SUPPORT_PKGCONFIG_TYPE')
            before = path.read_text(); after = old.relocate_pc(before, target)
            if before != after:
                path.write_text(after)
                relocated.append({'file': path.name, 'before_sha256': hashlib.sha256(before.encode()).hexdigest(),
                                  'after_sha256': hashlib.sha256(after.encode()).hexdigest()})
    output.write_text(json.dumps({'schema': 'ilinux097-support-prefix-v1', 'signatures': verified,
                                 'relocated': relocated, 'package_installations': 0,
                                 'system_keyring_changes': False}, indent=2) + '\n')


if __name__ == '__main__':
    main()
