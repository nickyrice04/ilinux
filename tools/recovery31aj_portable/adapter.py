#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Route the frozen 31AJ stager/server to one portable source inventory.

Default is help. This adapter introduces no target, policy or artifact override.
All original source bytes and the complete portable closure are verified before
loading original code. Dependency imports execute the same verified snapshots.
Only the original module's INVENTORY selector changes after loading.
"""
import argparse
import builtins
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
INVENTORY = 'native/boot/attempt31aj-portable/source-sha256.txt'
OLD_INVENTORY = 'native/boot/attempt31aj-kit/source-sha256.txt'
OLD_INVENTORY_SHA = 'ae825d028e613bdb67ef67a4ca4a29480b3387035db3cdce5f2a42c1914be969'
PRODUCER_FILE = 'virtualization/jobs/097-direct31aj-readable/out/test-readable-host'
PRODUCER_SHA = 'f829b0db80fceef5eccabb3498414831e75db6a6dd9618c52b67c71263b64d2a'
ADAPTER_FILES = {'tools/recovery31aj_portable/adapter.py',
                 'tools/recovery31aj_portable/test_adapter.py'}
OPTIONAL_HANDOFF = 'tools/m1n1-client/attempt31aj-portable-instructions.md'
MODULES = {'tools/recovery31aj/' + name + '.py'
           for name in ('profile', 'render', 'prepare', 'stage_lab', 'serve')}
MAX_FILE = 8 * 1024 * 1024


def require(ok):
    if not ok:
        raise ValueError('portable source admission refused')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_name(name):
    require(type(name) is str and re.fullmatch(r'[A-Za-z0-9_./-]+', name))
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name and
            all(part not in ('.', '..', '') for part in path.parts))
    return path


def read_bounded(root, name, limit=MAX_FILE):
    """Same-fd bounded read; every path component is opened without following."""
    parts = source_name(name).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if index < len(parts) - 1:
                flags |= os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        pieces = []
        total = 0
        while True:
            data = os.read(fd, min(65536, limit + 1 - total))
            if not data:
                break
            pieces.append(data)
            total += len(data)
            require(total <= limit)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(total == before.st_size and
                all(getattr(before, key) == getattr(after, key) for key in fields))
        return b''.join(pieces)
    finally:
        os.close(fd)


def parse_inventory(data):
    require(type(data) is bytes and 0 < len(data) <= 256 * 1024)
    lines = data.decode('ascii').splitlines()
    require(0 < len(lines) <= 2048)
    records = {}
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        require(match is not None)
        expected, name = match.groups()
        source_name(name)
        require(name not in records)
        records[name] = expected
    return records


def allowed_addition(name):
    if name in ADAPTER_FILES or name in (OLD_INVENTORY, OPTIONAL_HANDOFF):
        return True
    path = PurePosixPath(name)
    prefix = 'native/boot/attempt31aj-portable/'
    return (name.startswith(prefix) and name != INVENTORY and
            path.suffix in ('.md', '.json', '.txt') and
            not {'out', 'build', '__pycache__'} & set(path.parts))


def snapshot(root=ROOT):
    """Retain all 56 published inputs, omitting only the pinned producer output."""
    root = Path(root).resolve()
    old_bytes = read_bounded(root, OLD_INVENTORY, 256 * 1024)
    require(digest(old_bytes) == OLD_INVENTORY_SHA)
    original = parse_inventory(old_bytes)
    require(len(original) == 57 and original.pop(PRODUCER_FILE, None) == PRODUCER_SHA)
    inventory = read_bounded(root, INVENTORY, 256 * 1024)
    records = parse_inventory(inventory)
    require(PRODUCER_FILE not in records and INVENTORY not in records)
    require(set(original) | ADAPTER_FILES | {OLD_INVENTORY} <= set(records))
    require(all(records[name] == expected for name, expected in original.items()))
    require(records[OLD_INVENTORY] == OLD_INVENTORY_SHA)
    require(all(name in original or allowed_addition(name) for name in records))
    sources = {}
    for name, expected in records.items():
        data = read_bounded(root, name)
        require(digest(data) == expected)
        if name not in original:
            require(b'\0' not in data)
            data.decode('utf-8')
            if name.endswith('.json'):
                require(type(json.loads(data)) is dict)
        sources[name] = data
    require(read_bounded(root, INVENTORY, 256 * 1024) == inventory and
            read_bounded(root, OLD_INVENTORY, 256 * 1024) == old_bytes)
    return root, inventory, records, sources


class SnapshotImports:
    """The frozen importlib-based local loaders see only verified source bytes.

    This proxy is private to the original modules' globals. It does not replace
    any process-wide import hook or stdlib module. Ordinary stdlib imports use
    Python's unchanged import implementation; invoke the CLI with Python -I.
    """
    def __init__(self, root, sources):
        self.root = root
        self.sources = sources
        self.util = self
        self.builtins = dict(vars(builtins), __import__=self.import_module)

    def import_module(self, name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'importlib.util' and level == 0:
            return self if not fromlist else self.util
        return builtins.__import__(name, globals, locals, fromlist, level)

    def spec_from_file_location(self, name, path):
        path = Path(path).absolute()
        relative = path.relative_to(self.root).as_posix()
        require(relative in MODULES and relative in self.sources)
        return types.SimpleNamespace(name=name, path=path, relative=relative, loader=self)

    def module_from_spec(self, spec):
        module = types.ModuleType(spec.name)
        module.__file__ = str(spec.path)
        module.__builtins__ = self.builtins
        module.__verified_spec__ = spec
        return module

    def exec_module(self, module):
        spec = module.__verified_spec__
        exec(compile(self.sources[spec.relative], str(spec.path), 'exec'), module.__dict__)


def load_original(operation, root=ROOT):
    require(operation in ('stage', 'page'))
    root, inventory, records, sources = snapshot(root)
    loader = SnapshotImports(root, sources)
    name = 'stage_lab' if operation == 'stage' else 'serve'
    spec = loader.spec_from_file_location('portable31aj_' + name,
                                         root / ('tools/recovery31aj/' + name + '.py'))
    module = loader.module_from_spec(spec)
    loader.exec_module(module)
    require(module.INVENTORY == OLD_INVENTORY and module.ROOT == root)
    module.INVENTORY = INVENTORY
    return module


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = SafeParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument('--stage', action='store_true', help='Explicit authorized fixed lab-Data copy')
    operation.add_argument('--page', type=Path, help='Exact reviewed page under workspace build/')
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--check-only', action='store_true', help='Page verification without sockets')
    parser.add_argument('--bind', default=None)
    parser.add_argument('--port', type=int, default=None)
    parser.add_argument('--seconds', type=int, default=None)
    try:
        args = parser.parse_args(argv)
        if not args.stage and args.page is None:
            require(args.prepared is None and not args.check_only and args.bind is None and
                    args.port is None and args.seconds is None)
            parser.print_help()
            return 0
        if args.stage:
            require(args.prepared is not None and not args.check_only and args.bind is None and
                    args.port is None and args.seconds is None)
            module = load_original('stage', ROOT)
            return module.main(['--stage', '--prepared', str(args.prepared),
                                '--inventory', str(ROOT / INVENTORY)])
        require(args.prepared is None)
        module = load_original('page', ROOT)
        forwarded = ['serve.py', '--page', str(args.page)]
        if args.check_only:
            forwarded.append('--check-only')
        for option, value in (('--bind', args.bind), ('--port', args.port), ('--seconds', args.seconds)):
            if value is not None:
                forwarded.extend((option, str(value)))
        previous = sys.argv
        try:
            sys.argv = forwarded
            return module.main()
        finally:
            sys.argv = previous
    except (ValueError, OSError, UnicodeError, KeyError):
        print('{"status":"REFUSED","native_ready":false,"boot_settings_changed":false}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
