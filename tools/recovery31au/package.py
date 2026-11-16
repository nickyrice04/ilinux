#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare the new31AU kit/pages offline; stage and serving are explicit modes.

Preparation never runs a controller or queries host state. --stage is a separate
guarded lab-Data copy, with no boot/policy/mount action. No mode restarts a Mac.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import types
from typing import NamedTuple

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OLD_INVENTORY = 'native/boot/attempt31as-page/source-sha256.txt'
OLD_INVENTORY_SHA = '3bd089cc7b2a009d5bc503b7f973baac4d8c179192a31188bf4997bf24216350'
INVENTORY = 'native/boot/attempt31au-package/source-sha256.txt'
PROFILE = 'native/boot/attempt31au-package/profile.json'
BUILD = 'native/boot/attempt31au-package/build.json'
DELIVERY = 'native/boot/attempt31au-package/delivery.json'
STATE = '/Volumes/iLinux Boot Lab - Data/private/var/db/ilinux31au-state'
ADAPTER_FILES = {'tools/object31at-diagnostics/' + n for n in
                 ('build.py', 'diagnostics.c', 'diagnostics.h', 'fixture.c',
                  'test_diagnostics.py', 'README.md')}
NATIVE_FILES = {'tools/boot-object31au-native/' + n for n in
                ('build.py', 'generate.py', 'controller.c', 'read_diagnostics.h',
                 'test_native.py', 'README.md')}
OWN = {'tools/recovery31au/' + n for n in
       ('package.py', 'profile.py', 'render.py', 'test_package.py', 'test_render.py', 'README.md')}
HANDOFF = 'tools/m1n1-client/attempt31au-instructions.md'
EXTRA = ADAPTER_FILES | NATIVE_FILES | OWN | {HANDOFF, PROFILE, BUILD, DELIVERY}
BUILD_SOURCES = {'tools/boot-object31au-native/' + n for n in
                 ('build.py', 'generate.py', 'controller.c', 'read_diagnostics.h')} | {
    'tools/boot-object31aq-native/build.py', 'tools/boot-object31ar-native/controller.c',
    'tools/object31at-diagnostics/diagnostics.c', 'tools/object31at-diagnostics/diagnostics.h'}


def need(value):
    if not value:
        raise ValueError('31AU package refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Admission(NamedTuple):
    root: Path
    inventory: bytes
    records: dict
    sources: dict
    legacy: object
    renderer: object
    profile: dict
    as_module: object


def verified(name, data, root):
    module = types.ModuleType('verified31au_' + Path(name).stem)
    module.__file__ = str(root / name)
    exec(compile(data, module.__file__, 'exec'), module.__dict__)
    return module


def bootstrap_read(root, name, limit):
    """Bounded no-follow bootstrap before any frozen project code is loaded."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = name.split('/')
        need(all(p not in ('', '.', '..') for p in parts))
        for i, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if i + 1 < len(parts):
                flags |= os.O_DIRECTORY
            following = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = following
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        chunks, count = [], 0
        while count <= limit:
            block = os.read(fd, min(65536, limit + 1 - count))
            if not block:
                break
            chunks.append(block)
            count += len(block)
        after = os.fstat(fd)
        need(count == before.st_size and all(getattr(before, n) == getattr(after, n)
             for n in ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')))
        return b''.join(chunks)
    finally:
        os.close(fd)


def frozen(root=ROOT):
    """Admit all167 old inputs before executing original frozen project code."""
    root = Path(root).resolve()
    # Read this bounded public inventory with the fixed original reader. The
    # reader's own bytes are bound by the trusted167 inventory before use.
    raw = bootstrap_read(root, OLD_INVENTORY, 256 * 1024)
    need(sha(raw) == OLD_INVENTORY_SHA)
    records = {}
    import re
    for line in raw.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        need(match is not None)
        digest, name = match.groups()
        need(name not in records and not name.startswith('/') and
             all(p not in ('', '.', '..') for p in name.split('/')))
        records[name] = digest
    need(len(records) == 167)
    name = 'tools/recovery31as/package.py'
    data = bootstrap_read(root, name, 8 * 1024 * 1024)
    need(sha(data) == records[name])
    as_module = verified(name, data, root)
    legacy, old, old_inventory, old_records = as_module.admitted(root)
    need(old_inventory == raw and old_records == records)
    return as_module, legacy, old, records


def admitted(root=ROOT):
    as_module, legacy, old, retained = frozen(root)
    root = old[0]
    raw = legacy.read_bounded(INVENTORY, root, 256 * 1024)
    records = legacy.parse_inventory(raw)
    need(set(records) == set(retained) | {OLD_INVENTORY} | EXTRA)
    need(all(records[name] == digest for name, digest in retained.items()))
    need(records[OLD_INVENTORY] == OLD_INVENTORY_SHA)
    sources = {}
    for name, digest in records.items():
        data = legacy.read_bounded(name, root)
        need(sha(data) == digest)
        sources[name] = data
    profile_adapter = verified('tools/recovery31au/profile.py',
                               sources['tools/recovery31au/profile.py'], root)
    profile = profile_adapter.derive(sources[profile_adapter.SOURCE])
    value = profile.load(sources[PROFILE])
    need(profile.canonical(value) == sources[PROFILE])
    need(value['files']['candidate'] == {
        'name': 'candidate.macho', 'bytes': 153190400,
        'sha256': '1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01'})
    need(value['native_deadline_ms'] == 90000)
    render_adapter = verified('tools/recovery31au/render.py',
                              sources['tools/recovery31au/render.py'], root)
    renderer = render_adapter.derive(sources[render_adapter.SOURCE],
                                     sources[profile_adapter.SOURCE], profile,
                                     as_module, root)
    delivery = json.loads(sources[DELIVERY], object_pairs_hook=profile.pairs)
    expected = {item['name']: {k: item[k] for k in ('bytes', 'sha256')}
                for item in value['files'].values()}
    expected['profile.json'] = {'bytes': len(sources[PROFILE]), 'sha256': sha(sources[PROFILE])}
    need(type(delivery) is dict and delivery['schema'] == 'ilinux31au-delivery-v1' and
         delivery['files'] == expected and delivery['native_ready'] is False)
    build = json.loads(sources[BUILD], object_pairs_hook=profile.pairs)
    need(type(build) is dict and build['schema'] == 'ilinux31au-native-build-v1')
    need((build['binary_bytes'], build['binary_sha256']) ==
         (value['files']['helper']['bytes'], value['files']['helper']['sha256']))
    need(type(build['source_inputs']) is dict and set(build['source_inputs']) == BUILD_SOURCES)
    need(all(name in records and records[name] == digest
             for name, digest in build['source_inputs'].items()))
    need(type(build['retained_source_pins']) is dict and len(build['retained_source_pins']) == 143 and
         all(name in retained and retained[name] == digest
             for name, digest in build['retained_source_pins'].items()))
    need(build['candidate_definition'] == {
        'schema': 'ilinux31aj-compiled-candidate-v1', 'target': value['target'],
        'bytes': value['files']['candidate']['bytes'],
        'sha256': value['files']['candidate']['sha256'],
        'publication_authorizes_writes': False})
    need(build['sanitized'] is False and build['host_changes'] is False and
         build['live_run'] is False and build['native_ready'] is False)
    guard = build['guard_preservation']
    need(type(guard) is dict and guard['AU_exact_reversal'] is True and
         guard['original_recognizer_byte_identical'] is True and
         guard['initial_payload'] == 'BOOT021' and guard['initial_ctrr'] == 'disabled' and
         guard['candidate_ctrr'] == 'enabled' and guard['transport_changed'] is False)
    need(legacy.read_bounded(INVENTORY, root, 256 * 1024) == raw)
    return Admission(root, raw, records, sources, legacy, renderer, value, as_module)


def read_kit(kit, state):
    path = Path(kit)
    if not path.is_absolute():
        path = state.root / path
    need(state.root / 'build' in path.parents and '..' not in path.parts)
    expected = {item['name']: item for item in state.profile['files'].values()}
    raw = state.sources[PROFILE]
    expected['profile.json'] = {'bytes': len(raw), 'sha256': sha(raw)}

    def directory():
        fd = os.open(state.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in path.relative_to(state.root).parts:
                need(part not in ('', '.', '..'))
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY |
                                  os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            return fd
        except BaseException:
            os.close(fd)
            raise

    # Enumerate only an already held, no-follow workspace directory. Do not
    # perform even a directory listing through a caller-supplied parent link.
    fd = directory()
    try:
        before = os.fstat(fd)
        need(set(os.listdir(fd)) == set(expected))
        result = {name: state.legacy.artifact(path / name, item, state.root)
                  for name, item in expected.items()}
        current = directory()
        try:
            named = os.fstat(current)
            need((named.st_dev, named.st_ino) == (before.st_dev, before.st_ino))
        finally:
            os.close(current)
        after = os.fstat(fd)
        need(all(getattr(before, n) == getattr(after, n) for n in
                 ('st_dev', 'st_ino', 'st_mode', 'st_mtime_ns', 'st_ctime_ns')))
        need(set(os.listdir(fd)) == set(expected))
        return result
    finally:
        os.close(fd)


def generated(state):
    renderer, value = state.renderer, state.profile
    return {'profile.json': renderer.profile.canonical(value),
            'install-paste.txt': renderer.render(value, 'install').encode(),
            'restore-paste.txt': renderer.render(value, 'restore').encode(),
            'recovery.html': renderer.page(value).encode(),
            'install.html': renderer.page(value, 'install').encode(),
            'restore.html': renderer.page(value, 'restore').encode()}


def prepare(output, kit=None, root=ROOT):
    state = admitted(root)
    artifacts = read_kit(kit, state) if kit is not None else None
    destination = state.legacy.checked_output(output, state.root)
    outputs = generated(state)
    need(admitted(root)[:4] == state[:4])
    if kit is not None:
        need(read_kit(kit, state) == artifacts)
    report = {'schema': 'ilinux31au-preparation-v1', 'status': 'OFFLINE_PREPARATION_PASS',
              'verified_source_count': len(state.records), 'retained_source_count': 167,
              'source_inventory_sha256': sha(state.inventory),
              'profile_sha256': sha(state.sources[PROFILE]),
              'binary_delivery_verified': kit is not None,
              'output': {n: {'bytes': len(d), 'sha256': sha(d)} for n, d in outputs.items()},
              'stage_run': False, 'controller_run': False, 'server_started': False,
              'boot_settings_changed': False, 'native_ready': False,
              'publication_authorizes_execution': False}
    destination.mkdir(parents=True, mode=0o700)
    for name, data in outputs.items():
        with (destination / name).open('xb') as stream:
            stream.write(data)
    (destination / 'receipt.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    return report


def assemble(output, helper, candidate, rollback, root=ROOT):
    """Copy only verified project bytes into a new workspace-only four-file kit."""
    state = admitted(root)
    files = state.profile['files']
    inputs = {'helper': helper, 'candidate': candidate, 'rollback': rollback}
    for role, path in inputs.items():
        state.legacy.artifact(path, files[role], state.root)
    destination = state.legacy.checked_output(output, state.root)
    need(admitted(root)[:4] == state[:4])
    copier = state.legacy.old_module('stage_lab', state.sources, state.root)
    guard = state.legacy.verified_module('tools/boot-object31ag/read_selected.py',
                                        state.sources, state.root)
    held = {}
    try:
        for role, path in inputs.items():
            source = Path(path)
            if not source.is_absolute():
                source = state.root / source
            fd = guard.secure_open(source)
            try:
                fingerprint = copier.digest_fd(fd, files[role])
            except BaseException:
                os.close(fd)
                raise
            held[role] = (source, fd, fingerprint)
        destination.mkdir(parents=True, mode=0o700)
        for role, (source, fd, before) in held.items():
            target = destination / files[role]['name']
            os.lseek(fd, 0, os.SEEK_SET)
            with os.fdopen(os.dup(fd), 'rb') as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            target.chmod(0o700 if role == 'helper' else 0o600)
            need(copier.digest_fd(fd, files[role]) == before)
            current = guard.secure_open(source)
            try:
                need(copier.digest_fd(current, files[role]) == before)
            finally:
                os.close(current)
            state.legacy.artifact(target, files[role], state.root)
    finally:
        for _, fd, _ in held.values():
            os.close(fd)
    profile = destination / 'profile.json'
    with profile.open('xb') as stream:
        stream.write(state.sources[PROFILE])
    profile.chmod(0o600)
    need(admitted(root)[:4] == state[:4])
    return {'schema': 'ilinux31au-workspace-kit-v1', 'scope': 'WORKSPACE_ONLY',
            'files': read_kit(destination, state), 'lab_stage_run': False,
            'controller_run': False, 'boot_settings_changed': False, 'native_ready': False}


def stage(kit, root=ROOT, backend=None):
    state = admitted(root)
    read_kit(kit, state)
    original = state.sources['tools/recovery31aj/stage_lab.py'].decode('utf-8')
    old, new = "name=='ilinux31aj-reader'", "name=='ilinux31au-reader'"
    need(original.count(old) == 1)
    changed = original.replace(old, new, 1)
    need(changed.count(new) == 1 and changed.replace(new, old, 1) == original)
    derived = dict(state.sources, **{'tools/recovery31aj/stage_lab.py': changed.encode()})
    module = state.legacy.old_module('stage_lab', derived, state.root)
    module.INVENTORY, module.PROFILE = INVENTORY, PROFILE
    state_path = (str(Path(backend.fixture_root) / 'lab-data/private/var/db/ilinux31au-state')
                  if backend is not None and backend.synthetic else STATE)
    module.DESTINATION, module.STATE = '31au-kit', state_path
    old_guard = module.guard_metadata
    acl = state.legacy.verified_module('tools/policy31ao/acl_guard.py', state.sources, state.root)

    def guard_metadata(metadata, frozen_guard):
        binding = old_guard(metadata, frozen_guard)
        parent = frozen_guard.secure_open(Path(state_path).parent, directory=True)
        try:
            state.legacy.trusted_state_parent(parent, acl,
                os.geteuid() if backend is not None and backend.synthetic else 0)
            need(module.absent_at(parent, Path(state_path).name))
        finally:
            os.close(parent)
        return binding

    def current_sources(current_root, inventory):
        need(Path(current_root).resolve() == state.root and
             Path(inventory) == state.root / INVENTORY)
        need(admitted(root)[:4] == state[:4])
        guard = state.legacy.verified_module('tools/boot-object31ag/read_selected.py',
                                              state.sources, state.root)
        return state.inventory, state.records, guard, state.sources[PROFILE], state.profile

    module.guard_metadata, module.checked_sources = guard_metadata, current_sources
    report = module._stage(kit, state.root / INVENTORY, backend=backend, root=state.root)
    return dict(report, schema='ilinux31au-lab-data-staging-v1', controller_run=False,
                preboot_mount_run=False, old_transaction_reset=False)


def page_bytes(path, root=ROOT):
    state = admitted(root)
    path = state.legacy.checked_output(path, state.root, exists=True)
    actual = state.legacy.read_bounded(path, state.root, 256 * 1024)
    expected = generated(state)
    need(path.name in ('recovery.html', 'install.html', 'restore.html') and
         actual == expected[path.name])
    need(admitted(root)[:4] == state[:4])
    return actual, {'schema': 'ilinux31au-page-v1', 'status': 'EXACT_PAGE_VERIFIED',
                    'page_bytes': len(actual), 'page_sha256': sha(actual),
                    'source_inventory_sha256': sha(state.inventory),
                    'verified_source_count': len(state.records),
                    'server_started': False, 'native_ready': False}


def route(raw, original):
    first = raw.split(b'\r\n', 1)[0].split(b' ')
    path = first[1] if len(first) == 3 else None
    if path == b'/31au':
        raw = raw.replace(b' /31au ', b' /31aj ', 1)
    code, head = original(raw)
    return (404, head) if code == 200 and path not in (b'/', b'/31au') else (code, head)


def page_service(path, check_only, bind, port, seconds):
    data, report = page_bytes(path)
    if check_only:
        return report
    state = admitted()
    server = state.legacy.old_module('serve', state.sources, state.root)
    original = server.request
    server.request = lambda raw: route(raw, original)
    with server.make_server(data, bind or '127.0.0.1', port or 0) as active:
        host, selected = active.server_address
        print(json.dumps(dict(report, status='FIXED_PAGE_SERVING', server_started=True,
                              url=f'http://{host}:{selected}/31au',
                              seconds=seconds or 600), sort_keys=True), flush=True)
        server.serve(active, seconds or 600)
    return None


class Parser(argparse.ArgumentParser):
    def error(self, unused):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = Parser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--prepare-source-page', action='store_true')
    modes.add_argument('--assemble', action='store_true')
    modes.add_argument('--stage', action='store_true')
    modes.add_argument('--page', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--kit', type=Path)
    parser.add_argument('--helper', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--rollback', type=Path)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--bind')
    parser.add_argument('--port', type=int)
    parser.add_argument('--seconds', type=int)
    try:
        args = parser.parse_args(argv)
        network = (args.bind, args.port, args.seconds)
        inputs = (args.helper, args.candidate, args.rollback)
        if not any((args.prepare, args.prepare_source_page, args.assemble, args.stage, args.page)):
            need(args.output is None and args.kit is None and not args.check_only and
                 all(x is None for x in (*network, *inputs)))
            parser.print_help()
            return 0
        if args.prepare or args.prepare_source_page:
            need(args.output is not None and not args.check_only and
                 all(x is None for x in (*network, *inputs)) and
                 (args.kit is not None) == args.prepare)
            result = prepare(args.output, args.kit)
        elif args.assemble:
            need(args.output is not None and args.kit is None and not args.check_only and
                 all(x is None for x in network) and all(x is not None for x in inputs))
            result = assemble(args.output, *inputs)
        elif args.stage:
            need(args.kit is not None and args.output is None and not args.check_only and
                 all(x is None for x in (*network, *inputs)))
            result = stage(args.kit)
        else:
            need(args.output is None and args.kit is None and all(x is None for x in inputs))
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
