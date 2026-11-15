#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare the exact reviewed 31AP page from public sources, without a kit.

Default/help are inert. This tool performs workspace-only preparation; it does
not verify binary delivery on M1, stage files on M5, serve a page or query a host.
The unchanged Recovery block verifies the actual staged helper and profile.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = 'tools/recovery31ap/package.py'
PACKAGE_SHA = '6d1810d68da296fbac71bd7e7552697a683c2d49ece5088678496873b6002b9a'
INVENTORY = 'native/boot/attempt31ap/source-sha256.txt'
INVENTORY_SHA = '1e10cb95acab08adc127a84425c459745681d6c126a441523ec58e630618edf4'
EXPECTED = {
    'profile.json': {'bytes': 823, 'sha256': 'c64b596fd0d2e7003098eda79fa3a7f9841e13de79d2ce430d2b49f15d2bc747'},
    'diagnose-paste.txt': {'bytes': 5615, 'sha256': 'd9a47b93fc65ac78aa7a2b0e662bb6f2ce568584c74cf07575735f6247631bd7'},
    'recovery.html': {'bytes': 8357, 'sha256': 'fff051694d5cecd389e9fcc26204189277c0c83ba66f619429acc631558ff466'},
}


def require(value):
    if not value:
        raise ValueError('source-only page refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned_read(root, name, digest, limit):
    path = Path(name)
    require(not path.is_absolute() and path.parts and '..' not in path.parts)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for index, part in enumerate(path.parts):
            child = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                            (os.O_DIRECTORY if index + 1 < len(path.parts) else 0), dir_fd=fd)
            os.close(fd)
            fd = child
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        data = bytearray()
        while len(data) <= limit:
            piece = os.read(fd, min(16384, limit + 1 - len(data)))
            if not piece:
                break
            data.extend(piece)
        after = os.fstat(fd)
        require(len(data) == before.st_size and
                all(getattr(before, key) == getattr(after, key)
                    for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')) and
                sha(data) == digest)
        return bytes(data)
    finally:
        os.close(fd)


def load_package(root):
    data = pinned_read(root, PACKAGE, PACKAGE_SHA, 65536)
    pinned_read(root, INVENTORY, INVENTORY_SHA, 256 * 1024)
    package = types.ModuleType('verified31ap_source_only_page')
    package.__file__ = str(root / PACKAGE)
    exec(compile(data, package.__file__, 'exec'), package.__dict__)
    return package


def prepare(output, root=ROOT):
    root = Path(root).resolve()
    package = load_package(root)
    admitted_root, records, renderer, server = package.admitted(root)
    require(admitted_root == root and len(records) == 140)
    inventory, closure = server.source_closure(root)
    require(sha(inventory) == INVENTORY_SHA and closure == records)
    profile = server.read_bounded(package.PROFILE, root, 16384)
    require(sha(profile) == records[package.PROFILE])
    value = renderer.profile.load(profile)
    require(renderer.profile.canonical(value) == profile)
    generated = {'profile.json': profile,
                 'diagnose-paste.txt': renderer.render(value).encode('utf-8'),
                 'recovery.html': renderer.page(value).encode('utf-8')}
    outputs = {name: {'bytes': len(data), 'sha256': sha(data)}
               for name, data in generated.items()}
    require(outputs == EXPECTED)
    destination = server.prepare.checked_path(output, root, exists=False)
    require(root / 'build' in destination.parents and not destination.exists())
    require(server.source_closure(root) == (inventory, records))
    require(server.read_bounded(package.PROFILE, root, 16384) == profile)
    pinned_read(root, PACKAGE, PACKAGE_SHA, 65536)
    pinned_read(root, INVENTORY, INVENTORY_SHA, 256 * 1024)
    report = {'schema': 'ilinux31ap-source-profile-page-v1',
              'scope': 'SOURCE_PROFILE_PAGE_ONLY', 'status': 'OFFLINE_PREPARATION_PASS',
              'source_inventory_sha256': INVENTORY_SHA, 'verified_source_count': len(records),
              'output': outputs, 'kit_consumed': False,
              'binary_delivery_verified_on_M1': False,
              'staged': False, 'server_started': False, 'host_queried': False,
              'boot_settings_changed': False, 'native_ready': False,
              'publication_authorizes_execution': False}
    destination.mkdir(parents=True, mode=0o700)
    for name, data in generated.items():
        with (destination / name).open('xb') as stream:
            stream.write(data)
    with (destination / 'receipt.json').open('x') as stream:
        stream.write(json.dumps(report, sort_keys=True, indent=2) + '\n')
    return report


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--output', type=Path)
    try:
        args = parser.parse_args(argv)
        if not args.prepare:
            require(args.output is None)
            parser.print_help()
            return 0
        require(args.output is not None)
        result = prepare(args.output)
    except (Exception, KeyboardInterrupt):
        print('{"status":"REFUSED","native_ready":false,"staged":false,"server_started":false}')
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
