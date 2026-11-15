#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare/check the conditional read-only Preboot diagnostic; help is inert.

No live Recovery or mount operation runs here. --stage is a separate, explicitly
authorized future lab Data copy. No install, restore or native-boot mode exists.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = 'tools/recovery31al/package.py'
BASE_SHA = 'ba89f80007e7fb3482309d136a8a97c208413ac66da994db99757a33fe6a3b89'
BASE_INVENTORY = 'native/boot/attempt31al/source-sha256.txt'
BASE_INVENTORY_SHA = 'f62824f3dd91fdce6179f064d6c1582bbecace6a3b4efd884eae89969a91292c'
INVENTORY = 'native/boot/attempt31am/source-sha256.txt'
PROFILE = 'native/boot/attempt31am/diagnostic-profile.json'
CODE = {'tools/recovery31am/' + n for n in
        ('package.py', 'test_package.py', 'render.py', 'test_render.py', 'README.md')}
NATIVE = {'tools/boot-object31am-native/' + n for n in
          ('build.py', 'preboot.c', 'preboot.h', 'main.c', 'result.c',
           'test_native.py', 'README.md')}
EVIDENCE = {'native/boot/attempt31am/' + n for n in
            ('diagnostic-profile.json', 'delivery.json', 'build.json', 'findings.md',
             'metadata-shape.json')}
HANDOFF = 'tools/m1n1-client/attempt31am-instructions.md'
STAGE_SOURCE = 'tools/recovery31al/stage.py'
STAGE_DESTINATION = '31am-diagnostic'


def need(value):
    if not value:
        raise ValueError('31AM package refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bootstrap(root):
    path = root / BASE
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 65536)
    data = path.read_bytes()
    need(sha(data) == BASE_SHA)
    module = types.ModuleType('verified31al_preboot_base')
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    module.admitted(root)
    return module


def admitted(root=ROOT):
    root = Path(root).resolve()
    old = bootstrap(root)
    _, old_records, _, server = old.admitted(root)
    data = server.read_bounded(INVENTORY, root, 256 * 1024)
    # Use the already-admitted original inventory grammar, not a new parser.
    reader = old.bootstrap(root).original_adapter(root)
    records = reader.parse_inventory(data)
    need(len(old_records) == 92 and
         sha(server.read_bounded(BASE_INVENTORY, root, 256 * 1024)) == BASE_INVENTORY_SHA)
    required = set(old_records) | CODE | NATIVE | EVIDENCE | {BASE_INVENTORY, HANDOFF}
    need(set(records) == required and records[BASE_INVENTORY] == BASE_INVENTORY_SHA)
    need(all(records[n] == digest for n, digest in old_records.items()))
    sources = {}
    for name, digest in records.items():
        contents = server.read_bounded(name, root, 8 * 1024 * 1024)
        need(sha(contents) == digest)
        if name not in old_records:
            need(b'\0' not in contents)
            contents.decode('utf-8')
            if name.endswith('.json'):
                need(type(json.loads(contents)) is dict)
        sources[name] = contents
    need(server.read_bounded(INVENTORY, root, 256 * 1024) == data)
    renderer = types.ModuleType('verified31am_renderer')
    renderer.__file__ = str(root / 'tools/recovery31am/render.py')
    exec(compile(sources['tools/recovery31am/render.py'], renderer.__file__, 'exec'),
         renderer.__dict__)
    server.INVENTORY, server.PROFILE, server.renderer = INVENTORY, PROFILE, renderer
    value = renderer.profile.load(sources[PROFILE])
    need(renderer.profile.canonical(value) == sources[PROFILE])
    delivery = json.loads(sources['native/boot/attempt31am/delivery.json'])
    need(delivery['files'] == {
        'profile.json': {'bytes': len(sources[PROFILE]), 'sha256': sha(sources[PROFILE])},
        'ilinux31aj-reader': {k: value['files']['helper'][k] for k in ('bytes', 'sha256')}})
    build = json.loads(sources['native/boot/attempt31am/build.json'])
    need(build['schema'] == 'ilinux31am-native-build-v1')
    need(build['source_inputs'] == {n: records['tools/boot-object31am-native/' + n]
         for n in ('build.py', 'preboot.c', 'preboot.h', 'main.c', 'result.c')})
    need(build['frozen_inputs'] == {n: old_records[n] for n in
         ('tools/boot-object31al-native/generate.py',
          'tools/boot-object31al-native/diagnostic.c',
          'tools/boot-object31al-native/diagnostic.h')})
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
    need(build['candidate_definition'] == {
         'schema': 'ilinux31aj-compiled-candidate-v1', 'target': value['target'],
         'publication_authorizes_writes': False,
         'bytes': value['files']['candidate']['bytes'],
         'sha256': value['files']['candidate']['sha256']})
    return root, records, renderer, server


def frozen_stager(root):
    return bootstrap(Path(root).resolve()).frozen_stager(root)


def read_kit(kit, root, server):
    old = bootstrap(root)
    old.PROFILE = PROFILE  # Only the canonical profile selector changes.
    return old.read_kit(kit, root, server)


def stage_module(root, records, server):
    contents = server.read_bounded(STAGE_SOURCE, root, 65536)
    need(sha(contents) == records[STAGE_SOURCE])
    module = types.ModuleType('verified31am_two_file_stager')
    module.__file__ = str(root / STAGE_SOURCE)
    exec(compile(contents, module.__file__, 'exec'), module.__dict__)
    # Reuse the reviewed copy operation and target guards, with a new name only.
    module.DESTINATION = STAGE_DESTINATION
    return module


def stage(kit, root=ROOT):
    root, records, _, server = admitted(root)
    module = stage_module(root, records, server)
    controller = types.SimpleNamespace(admitted=admitted, read_kit=read_kit,
                                       frozen_stager=frozen_stager)
    report = module.stage_kit(kit, root, controller=controller)
    return dict(report, schema='ilinux31am-lab-data-staging-v1',
                conditional_mount_run=False)


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
    report = {'schema': 'ilinux31am-preboot-preparation-v1',
              'status': 'OFFLINE_PREPARATION_PASS',
              'source_inventory_sha256': sha(source_inventory),
              'verified_source_count': len(records),
              'output': {n: {'bytes': len(d), 'sha256': sha(d)}
                         for n, d in generated.items()},
              'conditional_read_only_mount': True, 'mount_execution': 'NOT RUN',
              'boot_settings_changed': False, 'native_ready': False,
              'publication_authorizes_execution': False}
    destination.mkdir(parents=True, mode=0o700)
    for name, contents in generated.items():
        with (destination / name).open('xb') as stream:
            stream.write(contents)
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
                result = stage(args.kit)
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
