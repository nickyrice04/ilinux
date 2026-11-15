#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare/check exact 31AR pages and kits; default/help are inert.

--stage is a separate future authorized lab-Data copy. --page without
--check-only is a separate bounded private page service. Neither operation
executes a native controller, mounts Preboot, or changes boot/security settings.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
INVENTORY = 'native/boot/attempt31ar-package/source-sha256.txt'
PROFILE = 'native/boot/attempt31ar-package/profile.json'
BUILD = 'native/boot/attempt31ar-package/build.json'
DELIVERY = 'native/boot/attempt31ar-package/delivery.json'
ADAPTER = 'tools/recovery31aj_portable/adapter.py'
ADAPTER_SHA = 'd47b2151e263f392e1741f913641c15dae9f244eec566e481a6520ad107a836a'
RETAINED = {
    'native/boot/attempt31ap/source-sha256.txt':
        '1e10cb95acab08adc127a84425c459745681d6c126a441523ec58e630618edf4',
    'native/boot/attempt31ap-source-page/source-sha256.txt':
        '62fad9235d127f9b436699976373bf250aae742c0be82def17291eceb523c378',
}
NATIVE = {'tools/boot-object31ar-native/' + n for n in
          ('build.py', 'controller.c', 'test_native.py', 'test_pty.py', 'README.md')}
AQ = {'tools/boot-object31aq-native/' + n for n in
      ('build.py', 'test_native.py', 'README.md')}
OWN = {'tools/recovery31ar/' + n for n in
       ('package.py', 'render.py', 'test_package.py', 'test_render.py', 'README.md')}
HANDOFF = 'tools/m1n1-client/attempt31ar-instructions.md'
EXTRA = NATIVE | AQ | OWN | {HANDOFF, PROFILE, BUILD, DELIVERY}
STATE = '/Volumes/iLinux Boot Lab - Data/private/var/db/ilinux31ar-state'


def need(value):
    if not value:
        raise ValueError('31AR package refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_name(name):
    need(type(name) is str and re.fullmatch(r'[A-Za-z0-9_./-]+', name))
    path = PurePosixPath(name)
    need(not path.is_absolute() and str(path) == name and
         all(p not in ('', '.', '..') for p in path.parts))
    return path


def read_bounded(name, root=ROOT, limit=8 * 1024 * 1024):
    root = Path(root)
    path = Path(name)
    if path.is_absolute():
        path = path.relative_to(root)
    parts = source_name(path.as_posix()).parts
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if index + 1 < len(parts):
                flags |= os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(fd)
        need(len(data) == before.st_size and
             all(getattr(before, n) == getattr(after, n) for n in
                 ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')))
        return bytes(data)
    finally:
        os.close(fd)


def parse_inventory(data):
    need(type(data) is bytes and 0 < len(data) <= 256 * 1024)
    records = {}
    for line in data.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        need(match is not None)
        digest, name = match.groups()
        source_name(name)
        need(name not in records)
        records[name] = digest
    need(0 < len(records) <= 2048)
    return records


def verified_module(name, sources, root):
    need(name in sources)
    module = types.ModuleType('verified31ar_' + Path(name).stem)
    module.__file__ = str(root / name)
    exec(compile(sources[name], module.__file__, 'exec'), module.__dict__)
    return module


def admitted(root=ROOT):
    root = Path(root).resolve()
    retained = {}
    for name, digest in RETAINED.items():
        raw = read_bounded(name, root, 256 * 1024)
        need(sha(raw) == digest)
        parsed = parse_inventory(raw)
        need(not set(parsed).intersection(retained))
        retained.update(parsed)
    need(len(retained) == 143)
    inventory = read_bounded(INVENTORY, root, 256 * 1024)
    records = parse_inventory(inventory)
    need(set(records) == set(retained) | set(RETAINED) | EXTRA)
    need(all(records[n] == v for n, v in retained.items()))
    need(all(records[n] == v for n, v in RETAINED.items()))
    sources = {}
    for name, digest in records.items():
        data = read_bounded(name, root)
        need(sha(data) == digest)
        if name not in retained:
            need(b'\0' not in data)
            data.decode('utf-8')
        sources[name] = data
    need(records[ADAPTER] == ADAPTER_SHA)
    renderer = verified_module('tools/recovery31ar/render.py', sources, root)
    value = renderer.profile.load(sources[PROFILE])
    need(renderer.profile.canonical(value) == sources[PROFILE])
    need(value['files']['candidate'] == {
        'name': 'candidate.macho', 'bytes': 153190400,
        'sha256': '1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01'})
    need(value['native_deadline_ms'] == 90000)
    delivery = json.loads(sources[DELIVERY], object_pairs_hook=renderer.profile.pairs)
    need(type(delivery) is dict and delivery['schema'] == 'ilinux31ar-delivery-v1')
    expected = {item['name']: {k: item[k] for k in ('bytes', 'sha256')}
                for item in value['files'].values()}
    expected['profile.json'] = {'bytes': len(sources[PROFILE]), 'sha256': sha(sources[PROFILE])}
    need(delivery['files'] == expected and delivery['native_ready'] is False)
    build = json.loads(sources[BUILD], object_pairs_hook=renderer.profile.pairs)
    need(build['schema'] == 'ilinux31ar-native-build-v1')
    need(build['retained_source_pins'] == retained)
    need(build['source_inputs'] == {n: records[n] for n in (
        'tools/boot-object31ar-native/build.py',
        'tools/boot-object31ar-native/controller.c',
        'tools/boot-object31aq-native/build.py')})
    need((build['binary_bytes'], build['binary_sha256']) ==
         (value['files']['helper']['bytes'], value['files']['helper']['sha256']))
    need(build['candidate_definition'] == {
        'schema': 'ilinux31aj-compiled-candidate-v1', 'target': value['target'],
        'bytes': value['files']['candidate']['bytes'],
        'sha256': value['files']['candidate']['sha256'],
        'publication_authorizes_writes': False})
    need(build['sanitized'] is False and build['host_changes'] is False and
         build['live_run'] is False and build['native_ready'] is False)
    need(read_bounded(INVENTORY, root, 256 * 1024) == inventory)
    return root, inventory, records, sources, renderer, value


def checked_output(path, root, exists=False):
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    need('..' not in path.parts and root / 'build' in path.parents)
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        need(not current.is_symlink())
    if exists:
        need(path.is_file())
    else:
        need(not path.exists())
    return path


def artifact(path, expected, root):
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    checked_output(path, root, exists=True)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = path.relative_to(root).parts
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if index + 1 < len(parts):
                flags |= os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size == expected['bytes'])
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            need(total <= expected['bytes'])
            digest.update(chunk)
        after = os.fstat(fd)
        need(total == expected['bytes'] and digest.hexdigest() == expected['sha256'])
        need(all(getattr(before, n) == getattr(after, n) for n in
                 ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')))
        return {'bytes': total, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)


def read_kit(kit, root, value):
    kit = Path(kit)
    if not kit.is_absolute():
        kit = root / kit
    need(root / 'build' in kit.parents and not kit.is_symlink() and kit.is_dir())
    expected = {item['name']: item for item in value['files'].values()}
    raw = read_bounded(PROFILE, root, 16384)
    expected['profile.json'] = {'bytes': len(raw), 'sha256': sha(raw)}
    need({p.name for p in kit.iterdir()} == set(expected))
    return {name: artifact(kit / name, item, root) for name, item in expected.items()}


def generated(renderer, value):
    return {
        'profile.json': renderer.profile.canonical(value),
        'install-paste.txt': renderer.render(value, 'install').encode(),
        'restore-paste.txt': renderer.render(value, 'restore').encode(),
        'recovery.html': renderer.page(value).encode(),
        'install.html': renderer.page(value, 'install').encode(),
        'restore.html': renderer.page(value, 'restore').encode(),
    }


def prepare(output, kit=None, root=ROOT):
    root, inventory, records, sources, renderer, value = admitted(root)
    artifacts = read_kit(kit, root, value) if kit is not None else None
    result = generated(renderer, value)
    destination = checked_output(output, root)
    need(admitted(root)[1:4] == (inventory, records, sources))
    if kit is not None:
        need(read_kit(kit, root, value) == artifacts)
    report = {
        'schema': 'ilinux31ar-preparation-v1', 'status': 'OFFLINE_PREPARATION_PASS',
        'verified_source_count': len(records), 'retained_source_count': 143,
        'source_inventory_sha256': sha(inventory),
        'profile_sha256': sha(sources[PROFILE]),
        'binary_delivery_verified': kit is not None,
        'output': {name: {'bytes': len(data), 'sha256': sha(data)}
                   for name, data in result.items()},
        'stage_run': False, 'recovery_run': False, 'controller_run': False,
        'boot_settings_changed': False, 'native_ready': False,
        'publication_authorizes_execution': False,
    }
    destination.mkdir(parents=True, mode=0o700)
    for name, data in result.items():
        with (destination / name).open('xb') as stream:
            stream.write(data)
    with (destination / 'receipt.json').open('x') as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write('\n')
    return report


def page_bytes(path, root=ROOT):
    root, inventory, records, sources, renderer, value = admitted(root)
    path = checked_output(path, root, exists=True)
    data = read_bounded(path, root, 256 * 1024)
    pages = {n: d for n, d in generated(renderer, value).items() if n.endswith('.html')}
    need(path.name in pages and data == pages[path.name])
    need(admitted(root)[1:4] == (inventory, records, sources))
    return data, {
        'schema': 'ilinux31ar-page-v1', 'status': 'EXACT_PAGE_VERIFIED',
        'page_bytes': len(data), 'page_sha256': sha(data),
        'source_inventory_sha256': sha(inventory), 'verified_source_count': len(records),
        'write_authorized': False, 'native_ready': False, 'server_started': False,
    }


def old_module(name, sources, root):
    adapter = verified_module(ADAPTER, sources, root)
    loader = adapter.SnapshotImports(root, sources)
    spec = loader.spec_from_file_location('verified31ar_' + name,
                                         root / ('tools/recovery31aj/' + name + '.py'))
    module = loader.module_from_spec(spec)
    loader.exec_module(module)
    return module


def trusted_state_parent(fd, acl, owner):
    before = os.fstat(fd)
    need(stat.S_ISDIR(before.st_mode) and before.st_uid == owner and
         not before.st_mode & 0o022 and acl.no_extended_acl(fd))
    after = os.fstat(fd)
    need(all(getattr(before, name) == getattr(after, name) for name in
             ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_ctime_ns')))


def stage(kit, root=ROOT, backend=None):
    """Reuse the complete original guarded four-file copier, with new names."""
    root, inventory, records, sources, renderer, value = admitted(root)
    read_kit(kit, root, value)
    module = old_module('stage_lab', sources, root)
    module.INVENTORY, module.PROFILE = INVENTORY, PROFILE
    state = (str(Path(backend.fixture_root) / 'lab-data/private/var/db/ilinux31ar-state')
             if backend is not None and backend.synthetic else STATE)
    module.DESTINATION, module.STATE = '31ar-kit', state
    original_guard = module.guard_metadata
    acl = verified_module('tools/policy31ao/acl_guard.py', sources, root)

    def guard_metadata(metadata, frozen):
        binding = original_guard(metadata, frozen)
        parent = frozen.secure_open(Path(state).parent, directory=True)
        try:
            trusted_state_parent(parent, acl,
                                 os.geteuid() if backend is not None and backend.synthetic else 0)
            need(module.absent_at(parent, Path(state).name))
        finally:
            os.close(parent)
        return binding

    module.guard_metadata = guard_metadata

    def current_sources(current_root, current_inventory):
        need(Path(current_root).resolve() == root and
             Path(current_inventory) == root / INVENTORY)
        current = admitted(root)
        need(current[1:4] == (inventory, records, sources))
        guard = verified_module('tools/boot-object31ag/read_selected.py', sources, root)
        return inventory, records, guard, sources[PROFILE], value

    module.checked_sources = current_sources
    report = module._stage(kit, root / INVENTORY, backend=backend, root=root)
    return dict(report, schema='ilinux31ar-lab-data-staging-v1',
                controller_run=False, preboot_mount_run=False)


def route_request(raw, original):
    first = raw.split(b'\r\n', 1)[0].split(b' ')
    original_path = first[1] if len(first) == 3 else None
    if original_path == b'/31ar':
        raw = raw.replace(b' /31ar ', b' /31aj ', 1)
    code, head = original(raw)
    if code == 200 and original_path not in (b'/', b'/31ar'):
        return 404, head
    return code, head


def page_service(path, check_only, bind, port, seconds):
    data, report = page_bytes(path)
    if check_only:
        return report
    root, _, _, sources, _, _ = admitted()
    server = old_module('serve', sources, root)
    old_request = server.request

    server.request = lambda raw: route_request(raw, old_request)
    with server.make_server(data, bind or '127.0.0.1', port or 0) as active:
        host, selected_port = active.server_address
        print(json.dumps(dict(report, status='FIXED_PAGE_SERVING', server_started=True,
                              url=f'http://{host}:{selected_port}/31ar',
                              seconds=seconds or 600), sort_keys=True), flush=True)
        server.serve(active, seconds or 600)
    return None


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = Parser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--prepare-source-page', action='store_true')
    modes.add_argument('--stage', action='store_true')
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
        if not (args.prepare or args.prepare_source_page or args.stage or args.page):
            need(args.kit is None and args.output is None and not args.check_only and
                 all(v is None for v in network))
            parser.print_help()
            return 0
        if args.prepare or args.prepare_source_page:
            need(args.output is not None and not args.check_only and
                 all(v is None for v in network))
            need((args.kit is not None) == args.prepare)
            result = prepare(args.output, args.kit)
        elif args.stage:
            need(args.kit is not None and args.output is None and not args.check_only and
                 all(v is None for v in network))
            result = stage(args.kit)
        else:
            need(args.kit is None and args.output is None)
            need(args.port is None or 0 <= args.port <= 65535)
            need(args.seconds is None or 1 <= args.seconds <= 1800)
            result = page_service(args.page, args.check_only, *network)
        if result is not None:
            print(json.dumps(result, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, UnicodeError, KeyError, TypeError):
        print('{"status":"REFUSED","native_ready":false,"boot_settings_changed":false}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
