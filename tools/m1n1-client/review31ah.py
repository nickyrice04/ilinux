#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only integrity review of a 31AH offline package; never extract or boot."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import zlib

SCHEMA = 'ilinux-direct31ah-offline-bundle-v1'
MAX_COMPRESSED = 512 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
MAX_FILE = 256 * 1024 * 1024
MAX_FILES = 128
TARGET = {'model': 'Mac17,6', 'board': 'j716c', 'chip_id': '0x6050'}


class Refusal(ValueError):
    pass


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise Refusal('duplicate_json_key')
        result[key] = value
    return result


def digest(stream):
    h = hashlib.sha256()
    size = 0
    while True:
        b = stream.read(1024 * 1024)
        if not b:
            return size, h.hexdigest()
        size += len(b)
        if size > MAX_TOTAL:
            raise Refusal('stream_limit')
        h.update(b)


def safe_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.+/-]{1,200}', name):
        raise Refusal('unsafe_member_name')
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '.' in p.parts or p.as_posix() != name:
        raise Refusal('unsafe_member_name')
    if not name.startswith('ilinux-direct31ah/'):
        raise Refusal('wrong_archive_root')
    return name


def validate_manifest(m):
    if not isinstance(m, dict) or m.get('schema') != SCHEMA:
        raise Refusal('manifest_schema')
    if m.get('target') != TARGET:
        raise Refusal('manifest_target')
    for key in ('native_authorized', 'restart_ready', 'firmware_change_authorized'):
        if m.get(key) is not False:
            raise Refusal('not_an_offline_review_package')
    package = m.get('package')
    if not isinstance(package, dict):
        raise Refusal('package_metadata')
    if package.get('filename') != 'ilinux-direct31ah-offline.tar.gz':
        raise Refusal('package_filename')
    if type(package.get('bytes')) is not int or not 0 < package['bytes'] <= MAX_COMPRESSED:
        raise Refusal('compressed_size')
    if not isinstance(package.get('sha256'), str) or not re.fullmatch(r'[a-f0-9]{64}', package['sha256']):
        raise Refusal('package_digest')
    files = package.get('files')
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise Refusal('member_inventory')
    total = 0
    for name, record in files.items():
        safe_name(name)
        if not isinstance(record, dict) or set(record) != {'bytes', 'sha256'}:
            raise Refusal('member_metadata')
        if type(record['bytes']) is not int or not 0 <= record['bytes'] <= MAX_FILE:
            raise Refusal('member_size')
        if not isinstance(record['sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', record['sha256']):
            raise Refusal('member_digest')
        total += record['bytes']
    if total > MAX_TOTAL:
        raise Refusal('expanded_size')
    return package


def review(manifest, archive):
    p = validate_manifest(manifest)
    archive = Path(archive)
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size != p['bytes']:
        raise Refusal('package_file')
    seen = set()
    total = 0
    decompressed = 0
    # Inspect strict USTAR headers before any metadata body can be consumed.
    # Python's ordinary tar iterator expands PAX/GNU extensions internally.
    with archive.open('rb') as stream:
        before = stream_stat(stream)
        size, sha = digest(stream)
        if size != p['bytes'] or sha != p['sha256']:
            raise Refusal('package_integrity')
        stream.seek(0)
        with gzip.GzipFile(fileobj=stream, mode='rb') as gz:
            def take(n):
                nonlocal decompressed
                if n > 1024 * 1024:
                    raise Refusal('read_limit')
                b = gz.read(n)
                decompressed += len(b)
                if decompressed > MAX_TOTAL + MAX_FILES * 1024 + 10240:
                    raise Refusal('tar_stream_limit')
                return b

            while True:
                header = take(512)
                if len(header) != 512:
                    raise Refusal('missing_tar_end')
                if header == bytes(512):
                    if take(512) != bytes(512):
                        raise Refusal('invalid_tar_end')
                    trailing = 0
                    while True:
                        b = take(1024)
                        if not b:
                            break
                        trailing += len(b)
                        if trailing > 10240 or any(b):
                            raise Refusal('data_after_tar_end')
                    break
                if header[257:265] != b'ustar\x0000':
                    raise Refusal('not_strict_ustar')
                if header[156:157] not in (b'0', b'\0'):
                    raise Refusal('nonregular_or_extension_header')
                member = tarfile.TarInfo.frombuf(header, 'ascii', 'strict')
                name = safe_name(member.name)
                if name in seen or name not in p['files'] or len(seen) >= MAX_FILES:
                    raise Refusal('unexpected_or_duplicate_member')
                if member.linkname or member.issparse():
                    raise Refusal('nonregular_member')
                expected = p['files'][name]
                if member.size != expected['bytes'] or not 0 <= member.size <= MAX_FILE:
                    raise Refusal('member_size_mismatch')
                total += member.size
                if total > MAX_TOTAL:
                    raise Refusal('expanded_size')
                h = hashlib.sha256()
                left = member.size
                while left:
                    b = take(min(left, 1024 * 1024))
                    if not b:
                        raise Refusal('truncated_member')
                    h.update(b)
                    left -= len(b)
                if h.hexdigest() != expected['sha256']:
                    raise Refusal('member_integrity')
                pad = (-member.size) % 512
                if take(pad) != bytes(pad):
                    raise Refusal('nonzero_member_padding')
                seen.add(name)
        if stream_stat(stream) != before:
            raise Refusal('package_changed_during_review')
    if seen != set(p['files']):
        raise Refusal('missing_member')
    return {'schema': 'ilinux-direct31ah-offline-review-v1',
            'status': 'OFFLINE_INTEGRITY_PASS', 'files_verified': len(seen),
            'expanded_bytes': total, 'tar_stream_bytes': decompressed, 'package_sha256': p['sha256'],
            'read_only': True, 'extracted': False, 'native_ready': False,
            'native_authorized': False, 'firmware_changed': False}


def stream_stat(stream):
    import os
    s = os.fstat(stream.fileno())
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', required=True, type=Path)
    ap.add_argument('--package', required=True, type=Path)
    args = ap.parse_args()
    if args.manifest.is_symlink() or args.manifest.stat().st_size > 128 * 1024:
        raise Refusal('manifest_file')
    m = json.loads(args.manifest.read_text(), object_pairs_hook=pairs)
    print(json.dumps(review(m, args.package), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (Refusal, OSError, EOFError, UnicodeError, json.JSONDecodeError,
            tarfile.TarError, zlib.error, RecursionError):
        print(json.dumps({'status': 'REFUSED', 'read_only': True, 'native_ready': False}))
        raise SystemExit(2)
