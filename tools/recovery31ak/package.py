#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare/verify the new Recovery workflow; no staging or boot operation.

The candidate, native reader and transaction profile remain the reviewed 31AJ
bytes. Only the renderer is replaced. Default invocation displays help. Serving
requires --page; --check-only validates it without creating a socket.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
INVENTORY = 'native/boot/attempt31ak/source-sha256.txt'
BASE_INVENTORY = 'native/boot/attempt31aj-portable/source-sha256.txt'
BASE_INVENTORY_SHA = '92b7612fe86ad7fc58dca09ac94b09160d00e1733365e139f077f1e37b5ec92f'
BASE_ADAPTER = 'tools/recovery31aj_portable/adapter.py'
BASE_ADAPTER_SHA = 'd47b2151e263f392e1741f913641c15dae9f244eec566e481a6520ad107a836a'
PROFILE = 'native/boot/attempt31aj-kit/recovery-profile.json'
CODE = {'tools/recovery31ak/' + name for name in
        ('package.py', 'test_package.py', 'render.py', 'test_paths.py', 'README.md')}
HANDOFF = 'tools/m1n1-client/attempt31ak-instructions.md'


def need(value):
    if not value:
        raise ValueError('31AK package refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def original_adapter(root):
    path = root / BASE_ADAPTER
    need(not path.is_symlink() and path.is_file() and path.stat().st_size <= 65536)
    data = path.read_bytes()
    need(sha(data) == BASE_ADAPTER_SHA)
    module = types.ModuleType('verified31aj_portable')
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


def extra_source(name):
    if name in CODE or name in (BASE_INVENTORY, HANDOFF):
        return True
    path = PurePosixPath(name)
    return (name.startswith('native/boot/attempt31ak/') and name != INVENTORY and
            path.suffix in ('.md', '.json', '.txt') and
            not {'out', 'build', '__pycache__'} & set(path.parts))


def admitted(root=ROOT):
    root = Path(root).resolve()
    base = original_adapter(root)
    _, old_bytes, old_records, _ = base.snapshot(root)
    need(len(old_records) == 62 and sha(old_bytes) == BASE_INVENTORY_SHA)
    inventory = base.read_bounded(root, INVENTORY, 256 * 1024)
    records = base.parse_inventory(inventory)
    need(set(old_records) | CODE | {BASE_INVENTORY} <= set(records))
    need(records[BASE_INVENTORY] == BASE_INVENTORY_SHA)
    need(all(records[name] == digest for name, digest in old_records.items()))
    need(INVENTORY not in records and
         all(name in old_records or extra_source(name) for name in records))
    sources = {}
    for name, digest in records.items():
        data = base.read_bounded(root, name)
        need(sha(data) == digest)
        if name not in old_records:
            need(b'\0' not in data)
            data.decode('utf-8')
            if name.endswith('.json'):
                need(type(json.loads(data)) is dict)
        sources[name] = data
    need(base.read_bounded(root, INVENTORY, 256 * 1024) == inventory)
    renderer = types.ModuleType('verified31ak_renderer')
    renderer.__file__ = str(root / 'tools/recovery31ak/render.py')
    exec(compile(sources['tools/recovery31ak/render.py'], renderer.__file__, 'exec'),
         renderer.__dict__)
    # Every original dependency is still loaded from verified memory snapshots.
    server = base.load_original('page', root)
    server.INVENTORY = INVENTORY
    server.renderer = renderer
    server.prepare.renderer = renderer
    return root, records, renderer, server


def prepare(kit, output, root=ROOT):
    root, records, _, server = admitted(root)
    result = server.prepare.prepare(PROFILE, kit, INVENTORY, output, root=root)
    need(result['verified_source_count'] == len(records))
    # The original receipt schema is retained; this wrapper labels the new scope.
    return {'schema': 'ilinux31ak-workflow-preparation-v1',
            'status': 'OFFLINE_PREPARATION_PASS',
            'unchanged_31aj_candidate_helper_profile': True,
            'preparation': result, 'native_ready': False,
            'boot_settings_changed': False, 'writes_authorized': False}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = Parser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--page', type=Path)
    parser.add_argument('--kit', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--bind')
    parser.add_argument('--port', type=int)
    parser.add_argument('--seconds', type=int)
    try:
        args = parser.parse_args(argv)
        network = (args.bind, args.port, args.seconds)
        if not args.prepare and args.page is None:
            need(args.kit is None and args.output is None and not args.check_only
                 and all(value is None for value in network))
            parser.print_help()
            return 0
        if args.prepare:
            need(args.kit is not None and args.output is not None and
                 not args.check_only and all(value is None for value in network))
            print(json.dumps(prepare(args.kit, args.output), sort_keys=True))
            return 0
        need(args.kit is None and args.output is None)
        _, _, _, server = admitted()
        forwarded = ['serve.py', '--page', str(args.page)]
        if args.check_only:
            forwarded.append('--check-only')
        for option, value in zip(('--bind', '--port', '--seconds'), network):
            if value is not None:
                forwarded.extend((option, str(value)))
        previous = sys.argv
        try:
            sys.argv = forwarded
            return server.main()
        finally:
            sys.argv = previous
    except (ValueError, OSError, UnicodeError, KeyError):
        print('{"status":"REFUSED","native_ready":false,"boot_settings_changed":false}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
