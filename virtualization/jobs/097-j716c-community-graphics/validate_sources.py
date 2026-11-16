#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read pinned public archives as data; extract only in a Linux build VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import tarfile
import tempfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def components(name):
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or '\\' in name or '\x00' in name or
            any(x in ('', '.', '..') for x in name.rstrip('/').split('/'))):
        raise ValueError('ARCHIVE_PATH')
    return p.parts


def members_checked(members, pin):
    if len(members) != pin['member_count'] or len(members) > 30000:
        raise ValueError('ARCHIVE_COUNT')
    names, folded, total = set(), {}, 0
    for member in members:
        parts = components(member.name)
        if parts[0] != pin['prefix']:
            raise ValueError('ARCHIVE_ROOT')
        if member.name in names:
            raise ValueError('ARCHIVE_DUPLICATE')
        names.add(member.name)
        previous = folded.setdefault(member.name.casefold(), member.name)
        if previous != member.name:
            raise ValueError('ARCHIVE_CASE_COLLISION')
        if not (member.isfile() or member.isdir() or member.issym()):
            raise ValueError('ARCHIVE_TYPE')
        if not 0 <= member.size <= 100 * 1024**2:
            raise ValueError('ARCHIVE_MEMBER_SIZE')
        if member.isfile():
            total += member.size
        if member.issym():
            # Relative links may traverse inside this archive's own root only.
            link = PurePosixPath(member.linkname)
            if link.is_absolute() or '\\' in member.linkname or '\x00' in member.linkname:
                raise ValueError('ARCHIVE_LINK')
            stack = list(parts[:-1])
            for part in link.parts:
                if part == '..':
                    if len(stack) <= 1:
                        raise ValueError('ARCHIVE_LINK_ESCAPE')
                    stack.pop()
                elif part != '.':
                    stack.append(part)
    if total != pin['unpacked_bytes'] or total > 600 * 1024**2:
        raise ValueError('ARCHIVE_UNPACKED_SIZE')
    return {'members': len(members), 'unpacked_bytes': total,
            'casefold_collisions': 0}


def validate(archive, pin):
    if archive.is_symlink() or archive.stat().st_size != pin['bytes']:
        raise ValueError('ARCHIVE_FILE_SIZE')
    if digest(archive) != pin['sha256']:
        raise ValueError('ARCHIVE_HASH')
    with tarfile.open(archive, 'r:gz') as source:
        report = members_checked(source.getmembers(), pin)
        for filename, expected in pin['selected'].items():
            member = source.getmember(pin['prefix'] + '/' + filename)
            if not member.isfile() or member.size != expected['bytes']:
                raise ValueError('SELECTED_FILE')
            data = source.extractfile(member).read()
            blob = b'blob ' + str(len(data)).encode() + b'\0' + data
            if (hashlib.sha256(data).hexdigest() != expected['sha256'] or
                    hashlib.sha1(blob).hexdigest() != expected['git_blob_sha1']):
                raise ValueError('SELECTED_HASH')
    return {**report, 'sha256': pin['sha256'], 'revision': pin['revision']}


def case_sensitive(parent):
    with tempfile.TemporaryDirectory(prefix='casecheck-', dir=parent) as d:
        lower, upper = Path(d) / 'probe', Path(d) / 'PROBE'
        lower.write_bytes(b'lower')
        upper.write_bytes(b'upper')
        return (lower.stat().st_ino != upper.stat().st_ino and
                lower.read_bytes() == b'lower' and upper.read_bytes() == b'upper')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('sources', type=Path)
    parser.add_argument('--extract', type=Path)
    args = parser.parse_args()
    pins = json.loads(args.manifest.read_text())['sources']
    reports = {pin['name']: validate(args.sources / pin['filename'], pin) for pin in pins}
    if args.extract:
        if platform.system() != 'Linux' or args.extract.exists() or args.extract.is_symlink():
            raise ValueError('FRESH_LINUX_DESTINATION_REQUIRED')
        if not case_sensitive(args.extract.parent):
            raise ValueError('CASE_SENSITIVE_DESTINATION_REQUIRED')
        args.extract.mkdir(mode=0o700)
        for pin in pins:
            with tarfile.open(args.sources / pin['filename'], 'r:gz') as source:
                source.extractall(args.extract, filter='data')
    print(json.dumps({'schema': 'ilinux097-source-admission-v1', 'sources': reports,
                      'extracted': bool(args.extract), 'native_hardware_tested': False}, sort_keys=True))


if __name__ == '__main__':
    main()
