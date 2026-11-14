#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare or check a read-only Recovery diagnostic. Default/help is inert.

No install, restoration, native boot or policy-write mode exists. --stage is a
separate future authorized lab Data copy; preparing pages never calls it.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = 'tools/recovery31ak/package.py'
BASE_SHA = '249010da9471fd8067845de20d973d286afae9908afd5746e334ad5b403588a4'
BASE_INVENTORY = 'native/boot/attempt31ak/source-sha256.txt'
BASE_INVENTORY_SHA = 'f795b4329bfc8b75c0ec9dfa54ef5f1703ed67d3847bf2e061dc1c5067763115'
INVENTORY = 'native/boot/attempt31al/source-sha256.txt'
PROFILE = 'native/boot/attempt31al/diagnostic-profile.json'
# Explicit source names: build products and arbitrary extra modules are excluded.
CODE = {'tools/recovery31al/' + n for n in
        ('package.py', 'test_package.py', 'render.py', 'test_render.py',
         'stage.py', 'test_stage.py', 'README.md')}
NATIVE = {'tools/boot-object31al-native/' + n for n in
          ('main.c', 'diagnostic.c', 'diagnostic.h', 'build.py', 'generate.py',
           'test_native.py', 'README.md')}
EVIDENCE = {'native/boot/attempt31al/' + n for n in
            ('diagnostic-profile.json', 'delivery.json', 'build.json', 'findings.md')}
HANDOFF = 'tools/m1n1-client/attempt31al-instructions.md'


def need(value):
    if not value:
        raise ValueError('31AL diagnostic refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bootstrap(root):
    """Admit the frozen 31AK dependency closure before any new local import."""
    path = root / BASE
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 65536)
    data = path.read_bytes()
    need(sha(data) == BASE_SHA)
    module = types.ModuleType('verified31ak_diagnostic_base')
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    module.admitted(root)
    return module


def admitted(root=ROOT):
    root = Path(root).resolve()
    old = bootstrap(root)
    _, old_records, _, server = old.admitted(root)
    reader = old.original_adapter(root)
    old_inventory = reader.read_bounded(root, BASE_INVENTORY, 256 * 1024)
    need(sha(old_inventory) == BASE_INVENTORY_SHA and len(old_records) == 72)
    data = reader.read_bounded(root, INVENTORY, 256 * 1024)
    records = reader.parse_inventory(data)
    required = set(old_records) | CODE | NATIVE | EVIDENCE | {BASE_INVENTORY, HANDOFF}
    need(set(records) == required and records[BASE_INVENTORY] == BASE_INVENTORY_SHA)
    need(all(records[n] == d for n, d in old_records.items()))
    sources = {}
    for name, digest in records.items():
        contents = reader.read_bounded(root, name)
        need(sha(contents) == digest)
        if name not in old_records:
            need(b'\0' not in contents)
            contents.decode('utf-8')
            if name.endswith('.json'):
                need(type(json.loads(contents)) is dict)
        sources[name] = contents
    need(reader.read_bounded(root, INVENTORY, 256 * 1024) == data)
    renderer = types.ModuleType('verified31al_renderer')
    renderer.__file__ = str(root / 'tools/recovery31al/render.py')
    exec(compile(sources['tools/recovery31al/render.py'], renderer.__file__, 'exec'),
         renderer.__dict__)
    server.INVENTORY, server.PROFILE, server.renderer = INVENTORY, PROFILE, renderer
    value = renderer.profile.load(sources[PROFILE])
    need(renderer.profile.canonical(value) == sources[PROFILE])
    delivery = json.loads(sources['native/boot/attempt31al/delivery.json'])
    need(delivery['files'] == {
        'profile.json': {'bytes': len(sources[PROFILE]), 'sha256': sha(sources[PROFILE])},
        'ilinux31aj-reader': {k: value['files']['helper'][k] for k in ('bytes', 'sha256')}})
    build = json.loads(sources['native/boot/attempt31al/build.json'])
    need(build['schema'] == 'ilinux31al-native-build-v1')
    need(build['source_inputs'] == {n: records['tools/boot-object31al-native/' + n]
         for n in ('build.py', 'generate.py', 'diagnostic.c', 'diagnostic.h', 'main.c')})
    proof = build['guard_preservation']
    need(proof['core_json_reader_byte_identical'] is True and
         proof['state_marks_strip_exact'] is True and
         proof['frozen_sources'] == {n: old_records['tools/boot-object31aj-native/' + n]
              for n in ('core.c', 'json.c', 'reader.h', 'state.c')})
    need((build['binary_bytes'], build['binary_sha256']) ==
         (value['files']['helper']['bytes'], value['files']['helper']['sha256']))
    need(build['system_sdk_only'] is True and build['sanitized'] is False and
         build['host_changes'] is False and build['live_run'] is False and
         build['recovery_run'] is False and build['native_ready'] is False)
    definition = build['candidate_definition']
    need(definition == {'schema': 'ilinux31aj-compiled-candidate-v1',
         'target': value['target'], 'publication_authorizes_writes': False,
         'bytes': value['files']['candidate']['bytes'],
         'sha256': value['files']['candidate']['sha256']})
    return root, records, renderer, server


def frozen_stager(root):
    old = bootstrap(Path(root).resolve())
    return old.original_adapter(Path(root).resolve()).load_original('stage', root)


def read_kit(kit, root, server):
    """Only the diagnostic helper and canonical public profile are consumed."""
    profile_data = server.read_bounded(PROFILE, root, 16384)
    value = server.profile.load(profile_data)
    need(server.profile.canonical(value) == profile_data)
    kit = Path(kit)
    if not kit.is_absolute():
        kit = root / kit
    need(not kit.is_symlink() and kit.is_dir())
    need({p.name for p in kit.iterdir()} == {'profile.json', 'ilinux31aj-reader'})
    data = {'profile.json': server.read_bounded(kit / 'profile.json', root, 16384),
            'ilinux31aj-reader': server.read_bounded(kit / 'ilinux31aj-reader', root,
                                                  8 * 1024 * 1024)}
    need(data['profile.json'] == profile_data)
    helper = value['files']['helper']
    need(len(data['ilinux31aj-reader']) == helper['bytes'] and
         sha(data['ilinux31aj-reader']) == helper['sha256'])
    return value, data


def prepare(kit, output, root=ROOT):
    root, records, renderer, server = admitted(root)
    source_inventory, _ = server.source_closure(root)
    value, artifacts = read_kit(kit, root, server)
    destination = server.prepare.checked_path(output, root, exists=False)
    need(root / 'build' in destination.parents and not destination.exists())
    generated = {'profile.json': artifacts['profile.json'],
                 'diagnose-paste.txt': renderer.render(value).encode(),
                 'recovery.html': renderer.page(value).encode()}
    need(server.source_closure(root) == (source_inventory, records))
    need(read_kit(kit, root, server) == (value, artifacts))
    report = {'schema': 'ilinux31al-diagnostic-preparation-v1',
              'status': 'OFFLINE_PREPARATION_PASS',
              'source_inventory_sha256': sha(source_inventory),
              'verified_source_count': len(records),
              'output': {n: {'bytes': len(d), 'sha256': sha(d)}
                         for n, d in generated.items()},
              'read_only_diagnostic_only': True, 'native_ready': False,
              'boot_settings_changed': False, 'writes_authorized': False,
              'live_recovery_diagnosis': 'NOT RUN'}
    destination.mkdir(parents=True, mode=0o700)
    for name, data in generated.items():
        with (destination / name).open('xb') as stream:
            stream.write(data)
    (destination / 'receipt.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    return report


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = Parser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare', action='store_true')
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
        if not args.prepare and not args.stage and args.page is None:
            need(args.kit is None and args.output is None and not args.check_only
                 and all(v is None for v in network))
            parser.print_help()
            return 0
        if args.prepare or args.stage:
            need(args.kit is not None and not args.check_only and all(v is None for v in network))
            if args.prepare:
                need(args.output is not None)
                result = prepare(args.kit, args.output)
            else:
                need(args.output is None)
                root, records, _, server = admitted()
                contents = server.read_bounded('tools/recovery31al/stage.py', root, 65536)
                need(sha(contents) == records['tools/recovery31al/stage.py'])
                module = types.ModuleType('verified31al_stage')
                module.__file__ = str(root / 'tools/recovery31al/stage.py')
                exec(compile(contents, module.__file__, 'exec'), module.__dict__)
                controller = types.SimpleNamespace(admitted=admitted, read_kit=read_kit,
                                                   frozen_stager=frozen_stager)
                result = module.stage_kit(args.kit, root, controller=controller)
            print(json.dumps(result, sort_keys=True))
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
    except (ValueError, OSError, UnicodeError, KeyError, TypeError):
        print('{"status":"REFUSED","native_ready":false,"boot_settings_changed":false}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
