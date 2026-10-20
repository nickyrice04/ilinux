#!/usr/bin/env python3
"""Verified size/hash and exact regular-file set, then extract only into RAM.

Imported source is sent as the SSH command; the reviewed bundle arrives on
stdin. No tar.extract, links, paths, devices, permissions, or owner restoration.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

NAMES = {'ilinux_mem29.ko', 'memory29', 'collect.py', 'assets.json'}
LIMIT = 2 * 1024 * 1024


def validate(data, size, digest):
    if not 0 < size <= LIMIT or len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('bundle size/hash differs')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        for member in archive:
            if member.name not in NAMES or member.name in files or not member.isreg() or not 0 < member.size <= LIMIT:
                raise ValueError('unexpected bundle member')
            if sum(map(len, files.values())) + member.size > LIMIT:
                raise ValueError('expanded bundle exceeds bound')
            files[member.name] = archive.extractfile(member).read()
    if set(files) != NAMES:
        raise ValueError('bundle member set differs')
    manifest = json.loads(files['assets.json'])
    if manifest.get('attempt') != 29 or set(manifest.get('sha256', {})) != NAMES - {'assets.json'}:
        raise ValueError('wrong bundle manifest')
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256(files[name]).hexdigest() != expected:
            raise ValueError('bundle asset hash differs')
    return files


def main():
    size, digest = int(sys.argv[1]), sys.argv[2]
    if not 0 < size <= LIMIT:
        raise ValueError('bundle outside size bound')
    files = validate(sys.stdin.buffer.read(size + 1), size, digest)
    # /run must really be tmpfs; never write any native persistent filesystem.
    mounts = [s.split() for s in Path('/proc/mounts').read_text().splitlines()]
    if not any(len(s) > 2 and s[1:3] == ['/run','tmpfs'] for s in mounts):
        raise ValueError('/run is not tmpfs')
    dest = Path('/run/ilinux-memory29')
    dest.mkdir(mode=0o700)  # existing dir refuses retries, including partial runs
    for name, data in files.items():
        with (dest/name).open('xb') as f:
            f.write(data)
        (dest/name).chmod(0o700 if name == 'memory29' else 0o600)
    os.execv('/usr/bin/python3', ['python3','-I',str(dest/'collect.py')])


if __name__ == '__main__':
    main()
