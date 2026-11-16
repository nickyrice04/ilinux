#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconstruct source Git trees, accounting for Mesa's published EOL attributes.

Uses the original job096 Git-object method. No extraction or source execution.
Only the two explicit Mesa export-EOL patterns may normalize CRLF to LF.
"""
import hashlib
from pathlib import Path, PurePosixPath
import re
import tarfile


def obj(kind, data):
    return hashlib.sha1(kind + b' ' + str(len(data)).encode() + b'\0' + data).digest()


def verify(path, expected_tree, mesa_eol=False):
    files, directories, normalized = {}, {(): {}}, []
    total = 0
    root = None
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if not parts or member.name.startswith('/') or '..' in parts:
                raise ValueError('TREE_PATH')
            if root is None:
                root = parts[0]
            if parts[0] != root:
                raise ValueError('TREE_ROOT')
            relative = parts[1:]
            if member.isdir():
                continue
            if not relative or relative in files or len(files) >= 30000:
                raise ValueError('TREE_DUPLICATE_OR_COUNT')
            name = '/'.join(relative)
            if member.issym():
                blob = obj(b'blob', member.linkname.encode('utf-8', 'surrogateescape'))
                mode = b'120000'
            elif member.isfile() and 0 <= member.size <= 128 * 1024**2:
                stream = archive.extractfile(member)
                total += member.size
                if total > 600 * 1024**2:
                    raise ValueError('TREE_EXPANSION')
                if mesa_eol and (name.endswith('.csv') or re.fullmatch(r'src/amd/ci/vkd3d-.*\.txt', name)):
                    data = stream.read()
                    canonical = data.replace(b'\r\n', b'\n')
                    if canonical != data:
                        normalized.append({'path': name, 'export_bytes': len(data),
                                           'git_bytes': len(canonical)})
                    blob = obj(b'blob', canonical)
                else:
                    h = hashlib.sha1(b'blob ' + str(member.size).encode() + b'\0')
                    count = 0
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        count += len(block); h.update(block)
                    if count != member.size:
                        raise ValueError('TREE_TRUNCATION')
                    blob = h.digest()
                mode = b'100755' if member.mode & 0o111 else b'100644'
            else:
                raise ValueError('TREE_TYPE')
            files[relative] = (mode, blob)
    for parts, value in files.items():
        for length in range(len(parts)):
            parent = parts[:length]; directories.setdefault(parent, {})
            if length + 1 == len(parts):
                directories[parent][parts[length]] = value
            else:
                child = parts[:length + 1]
                if child in files:
                    raise ValueError('TREE_FILE_DIRECTORY_COLLISION')
                directories[parent][parts[length]] = child
    hashes = {}
    for directory in sorted(directories, key=len, reverse=True):
        rows = []
        for name, value in directories[directory].items():
            encoded = name.encode('utf-8', 'surrogateescape')
            if value and isinstance(value[0], bytes):
                mode, blob = value; key = encoded
            else:
                mode, blob, key = b'40000', hashes[value], encoded + b'/'
            rows.append((key, mode + b' ' + encoded + b'\0' + blob))
        hashes[directory] = obj(b'tree', b''.join(row for _, row in sorted(rows)))
    actual = hashes[()].hex()
    if actual != expected_tree:
        raise ValueError('SOURCE_GIT_TREE_MISMATCH')
    return {'schema': 'ilinux097-source-tree-v1', 'git_tree': actual, 'files': len(files),
            'export_eol_normalizations': normalized, 'source_bytes_modified': False,
            'source_extracted_on_host': False, 'source_executed': False}
