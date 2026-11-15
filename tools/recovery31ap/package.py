#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline 31AP conditional read-only kit/page; default and help are inert.

Stage and page service remain separate explicit future operations.  This
controller has no install, restoration, policy-write or native-boot mode.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = 'tools/recovery31am/package.py'
BASE_SHA = '1ff1528a1ec2c6913a84e4dc21da7d82cc0d065236ba696db713afa1baaa6a57'
BASE_INVENTORY = 'native/boot/attempt31am/source-sha256.txt'
BASE_INVENTORY_SHA = '0d080629d2cb8ae35d347431cc754ab8bd45807f8a83f17b26b03e8c78b65231'
AO_INVENTORY = 'native/boot/attempt31ao/source-sha256.txt'
AO_INVENTORY_SHA = 'bb3d962e80bbe4c265f9a5d0557f77df61a3d09648ebd48d296284aa9bda91d6'
INVENTORY = 'native/boot/attempt31ap/source-sha256.txt'
PROFILE = 'native/boot/attempt31ap/diagnostic-profile.json'
CODE = {'tools/recovery31ap/' + n for n in
        ('package.py', 'render.py', 'test_package.py', 'test_render.py', 'README.md')}
NATIVE = {'tools/boot-object31ap-native/' + n for n in
          ('build.py', 'test_native.py', 'README.md')}
EVIDENCE = {'native/boot/attempt31ap/' + n for n in
            ('diagnostic-profile.json', 'delivery.json', 'build.json', 'findings.md')}
HANDOFF = 'tools/m1n1-client/attempt31ap-instructions.md'
STAGE_DESTINATION = '31ap-diagnostic'
FROZEN_BUILD_INPUTS = (
    'tools/boot-object31al-native/diagnostic.c',
    'tools/boot-object31al-native/diagnostic.h',
    'tools/boot-object31am-native/preboot.c',
    'tools/boot-object31am-native/preboot.h',
    'tools/boot-object31am-native/main.c',
    'tools/boot-object31am-native/result.c',
    'tools/boot-object31ao-native/generate.py',
    'tools/boot-object31ao-native/extra_policy.c',
    'tools/boot-object31ao-native/extra_policy.h',
)


def need(value):
    if not value:
        raise ValueError('31AP package refused')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bootstrap(root):
    path = root / BASE
    need(path.is_file() and not path.is_symlink() and path.stat().st_size <= 65536)
    data = path.read_bytes()
    need(sha(data) == BASE_SHA)
    module = types.ModuleType('verified31am_typed_policy_base')
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    module.admitted(root)
    return module


def admitted(root=ROOT):
    root = Path(root).resolve()
    old = bootstrap(root)
    _, old_records, _, server = old.admitted(root)
    reader = old.bootstrap(root).bootstrap(root).original_adapter(root)
    need(len(old_records) == 111 and
         sha(server.read_bounded(BASE_INVENTORY, root, 256 * 1024)) == BASE_INVENTORY_SHA)
    ao_data = server.read_bounded(AO_INVENTORY, root, 256 * 1024)
    need(sha(ao_data) == AO_INVENTORY_SHA)
    ao_records = reader.parse_inventory(ao_data)
    need(len(ao_records) == 14 and not set(old_records).intersection(ao_records))
    retained = dict(old_records, **ao_records)
    data = server.read_bounded(INVENTORY, root, 256 * 1024)
    records = reader.parse_inventory(data)
    required = set(retained) | CODE | NATIVE | EVIDENCE | {
        BASE_INVENTORY, AO_INVENTORY, HANDOFF}
    need(set(records) == required and records[BASE_INVENTORY] == BASE_INVENTORY_SHA and
         records[AO_INVENTORY] == AO_INVENTORY_SHA)
    need(all(records[n] == digest for n, digest in retained.items()))
    sources = {}
    for name, digest in records.items():
        contents = server.read_bounded(name, root, 8 * 1024 * 1024)
        need(sha(contents) == digest)
        if name not in retained:
            need(b'\0' not in contents)
            contents.decode('utf-8')
            if name.endswith('.json'):
                need(type(json.loads(contents)) is dict)
        sources[name] = contents
    need(server.read_bounded(INVENTORY, root, 256 * 1024) == data and
         server.read_bounded(AO_INVENTORY, root, 256 * 1024) == ao_data)
    renderer = types.ModuleType('verified31ap_renderer')
    renderer.__file__ = str(root / 'tools/recovery31ap/render.py')
    exec(compile(sources['tools/recovery31ap/render.py'], renderer.__file__, 'exec'),
         renderer.__dict__)
    server.INVENTORY, server.PROFILE, server.renderer = INVENTORY, PROFILE, renderer
    value = renderer.profile.load(sources[PROFILE])
    need(renderer.profile.canonical(value) == sources[PROFILE])
    delivery = json.loads(sources['native/boot/attempt31ap/delivery.json'])
    need(delivery['files'] == {
        'profile.json': {'bytes': len(sources[PROFILE]), 'sha256': sha(sources[PROFILE])},
        'ilinux31aj-reader': {k: value['files']['helper'][k] for k in ('bytes', 'sha256')}})
    build = json.loads(sources['native/boot/attempt31ap/build.json'])
    need(build['schema'] == 'ilinux31ap-native-build-v1')
    need(build['source_inputs'] == {'build.py': records['tools/boot-object31ap-native/build.py']})
    need(build['frozen_inputs'] == {n: retained[n] for n in FROZEN_BUILD_INPUTS})
    need(build['retained_source_pins'] == retained and build['source_inventories'] == {
        BASE_INVENTORY: BASE_INVENTORY_SHA, AO_INVENTORY: AO_INVENTORY_SHA})
    proof = build['guard_preservation']
    baseline = proof['base_observation_proof']
    need(baseline['core_json_reader_byte_identical'] is True and
         baseline['state_marks_strip_exact'] is True and
         baseline['frozen_sources'] == {n: old_records['tools/boot-object31aj-native/' + n]
              for n in ('core.c', 'json.c', 'reader.h', 'state.c')})
    need(all(proof[n] is True for n in (
        'extension_reverses_to_frozen_observed_source',
        'stripped_reversed_source_equals_original', 'reader_header_unchanged',
        'preboot_engine_byte_identical', 'cli_result_byte_identical',
        'diagnostic_support_byte_identical')))
    need(proof['acceptance_extension'] == 'FINITE_EXTRA_CATALOG_AND_TRUE_SMB_CONJUNCTION' and
         proof['comparison_extension'] == 'PRIVATE_STRUCT_AND_TAGGED_V3_HMAC' and
         proof['native_ready'] is False)
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
    old.PROFILE = PROFILE
    return old.read_kit(kit, root, server)


def stage_module(root, records, server):
    old = bootstrap(root)
    old.STAGE_DESTINATION = STAGE_DESTINATION
    return old.stage_module(root, records, server)


def stage(kit, root=ROOT):
    root, records, _, server = admitted(root)
    module = stage_module(root, records, server)
    controller = types.SimpleNamespace(admitted=admitted, read_kit=read_kit,
                                       frozen_stager=frozen_stager)
    return dict(module.stage_kit(kit, root, controller=controller),
                schema='ilinux31ap-lab-data-staging-v1', conditional_mount_run=False)


def prepare(kit, output, root=ROOT):
    root, records, renderer, server = admitted(root)
    inventory, _ = server.source_closure(root)
    value, artifacts = read_kit(kit, root, server)
    destination = server.prepare.checked_path(output, root, exists=False)
    need(root / 'build' in destination.parents and not destination.exists())
    generated = {'profile.json': artifacts['profile.json'],
                 'diagnose-paste.txt': renderer.render(value).encode(),
                 'recovery.html': renderer.page(value).encode()}
    need(server.source_closure(root) == (inventory, records))
    need(read_kit(kit, root, server) == (value, artifacts))
    report = {'schema': 'ilinux31ap-preboot-preparation-v1',
              'status': 'OFFLINE_PREPARATION_PASS',
              'source_inventory_sha256': sha(inventory),
              'verified_source_count': len(records),
              'retained_source_count': 125,
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
