#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""New closure and package controls; no live backend, mount or socket."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('package31ap_tested', Path(__file__).with_name('package.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = tool.bootstrap(ROOT).admitted(ROOT)[1]
        reader = tool.bootstrap(ROOT).bootstrap(ROOT).bootstrap(ROOT).original_adapter(ROOT)
        cls.ao = reader.parse_inventory((ROOT / tool.AO_INVENTORY).read_bytes())

    def setUp(self):
        base = ROOT / 'build/31ap-package-tests'
        base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=base)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.records = {}
        for name in self.old.keys() | self.ao.keys():
            self.write(name, (ROOT / name).read_bytes())
        for name in (tool.BASE_INVENTORY, tool.AO_INVENTORY):
            self.write(name, (ROOT / name).read_bytes())
        for name in tool.CODE | tool.NATIVE | tool.EVIDENCE | {tool.HANDOFF}:
            data = (ROOT / name).read_bytes() if (ROOT / name).is_file() else b'# fixture\n'
            self.write(name, b'{}\n' if name.endswith('.json') else data)
        value = json.loads((ROOT / 'native/boot/attempt31am/diagnostic-profile.json').read_bytes())
        value['files']['helper'].update(bytes=4, sha256=tool.sha(b'TEST'))
        profile = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
        self.write(tool.PROFILE, profile)
        delivery = {'files': {'profile.json': {'bytes': len(profile), 'sha256': tool.sha(profile)},
                             'ilinux31aj-reader': {'bytes': 4, 'sha256': tool.sha(b'TEST')}}}
        self.write('native/boot/attempt31ap/delivery.json', json.dumps(delivery).encode())
        retained = dict(self.old, **self.ao)
        proof = {'base_observation_proof': {
                     'core_json_reader_byte_identical': True, 'state_marks_strip_exact': True,
                     'frozen_sources': {n: self.old['tools/boot-object31aj-native/' + n]
                          for n in ('core.c', 'json.c', 'reader.h', 'state.c')}},
                 'acceptance_extension': 'FINITE_EXTRA_CATALOG_AND_TRUE_SMB_CONJUNCTION',
                 'comparison_extension': 'PRIVATE_STRUCT_AND_TAGGED_V3_HMAC',
                 'native_ready': False}
        for name in ('extension_reverses_to_frozen_observed_source',
                     'stripped_reversed_source_equals_original', 'reader_header_unchanged',
                     'preboot_engine_byte_identical', 'cli_result_byte_identical',
                     'diagnostic_support_byte_identical'):
            proof[name] = True
        build = {'schema': 'ilinux31ap-native-build-v1',
                 'source_inputs': {'build.py': self.records['tools/boot-object31ap-native/build.py']},
                 'frozen_inputs': {n: retained[n] for n in tool.FROZEN_BUILD_INPUTS},
                 'retained_source_pins': retained,
                 'source_inventories': {tool.BASE_INVENTORY: tool.BASE_INVENTORY_SHA,
                                        tool.AO_INVENTORY: tool.AO_INVENTORY_SHA},
                 'guard_preservation': proof,
                 'binary_bytes': 4, 'binary_sha256': tool.sha(b'TEST'),
                 'system_sdk_only': True, 'sanitized': False, 'host_changes': False,
                 'live_run': False, 'recovery_run': False, 'native_ready': False,
                 'candidate_definition': {'schema': 'ilinux31aj-compiled-candidate-v1',
                      'target': value['target'], 'publication_authorizes_writes': False,
                      'bytes': value['files']['candidate']['bytes'],
                      'sha256': value['files']['candidate']['sha256']}}
        self.write('native/boot/attempt31ap/build.json', json.dumps(build).encode())
        self.kit = self.root / 'build/kit'
        self.kit.mkdir(parents=True)
        (self.kit / 'profile.json').write_bytes(profile)
        (self.kit / 'ilinux31aj-reader').write_bytes(b'TEST')
        self.repin()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.records[name] = tool.sha(data)

    def repin(self):
        path = self.root / tool.INVENTORY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(d + '  ' + n + '\n' for n, d in sorted(self.records.items())))

    def test_offline_prepare_retains_125_and_page_verifies(self):
        _, records, renderer, server = tool.admitted(self.root)
        self.assertEqual(len(records), 140)
        self.assertTrue(all(records[n] == d for n, d in dict(self.old, **self.ao).items()))
        result = tool.prepare(self.kit, 'build/pages', self.root)
        self.assertEqual(result['retained_source_count'], 125)
        self.assertEqual(result['mount_execution'], 'NOT RUN')
        self.assertFalse(result['publication_authorizes_execution'])
        page, checked = server.load_page(self.root / 'build/pages/recovery.html', self.root)
        self.assertEqual(tool.sha(page), result['output']['recovery.html']['sha256'])
        self.assertIn(b'31AP typed-policy Preboot check', page)
        self.assertFalse(checked['native_ready'])

    def test_old_and_ao_sources_cannot_change_even_repin(self):
        for name in ('tools/boot-object31am-native/preboot.c',
                     'tools/boot-object31ao-native/extra_policy.c'):
            path = self.root / name
            original = path.read_bytes()
            self.write(name, original + b'\n/* changed */\n')
            self.repin()
            with self.assertRaises(ValueError):
                tool.admitted(self.root)
            self.write(name, original)
            self.repin()

    def test_missing_or_extra_inventory_member_refuses(self):
        name = 'tools/recovery31ap/test_render.py'
        old = self.records.pop(name)
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)
        self.records[name] = old
        self.write('tools/recovery31ap/unreviewed.py', b'# extra\n')
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_build_proof_identity_and_retained_pins_bound(self):
        name = 'native/boot/attempt31ap/build.json'
        original = (self.root / name).read_bytes()
        for case in ('source', 'frozen', 'retained', 'inventory', 'proof', 'binary'):
            value = json.loads(original)
            if case == 'source': value['source_inputs']['build.py'] = '0' * 64
            elif case == 'frozen': value['frozen_inputs'].pop(tool.FROZEN_BUILD_INPUTS[0])
            elif case == 'retained': value['retained_source_pins'].pop(next(iter(self.ao)))
            elif case == 'inventory': value['source_inventories'][tool.AO_INVENTORY] = '0' * 64
            elif case == 'proof': value['guard_preservation']['preboot_engine_byte_identical'] = False
            else: value['binary_bytes'] += 1
            self.write(name, json.dumps(value).encode())
            self.repin()
            with self.assertRaises(ValueError):
                tool.admitted(self.root)

    def test_exact_kit_profile_and_helper_required(self):
        for name, data in (('profile.json', b'{}'), ('ilinux31aj-reader', b'FAIL'), ('extra', b'EXTRA')):
            path = self.kit / name
            old = path.read_bytes() if path.exists() else None
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                tool.prepare(self.kit, 'build/pages', self.root)
            self.assertFalse((self.root / 'build/pages').exists())
            path.unlink()
            if old is not None:
                path.write_bytes(old)

    def test_unmatched_renderer_never_executes(self):
        (self.root / 'tools/recovery31ap/render.py').write_text('raise RuntimeError("MUST_NOT_EXECUTE")\n')
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_stager_changes_only_destination_and_keeps_old_state(self):
        _, records, _, server = tool.admitted(self.root)
        stage = tool.stage_module(self.root, records, server)
        self.assertEqual(stage.DESTINATION, '31ap-diagnostic')
        with self.assertRaises(TypeError):
            stage.stage_kit(self.kit, self.root)
        original = tool.frozen_stager(self.root)
        self.assertEqual(original.DESTINATION, '31aj-kit')
        self.assertEqual(original.STATE, '31aj-state')


class Dispatch(unittest.TestCase):
    def call(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = tool.main(args)
        return result, output.getvalue()

    def test_default_is_inert(self):
        with patch.object(tool, 'admitted') as admitted, patch.object(tool, 'stage') as stage:
            self.assertEqual(self.call([])[0], 0)
        admitted.assert_not_called()
        stage.assert_not_called()

    def test_no_write_or_boot_modes_or_mixed_options(self):
        for args in (['--install'], ['--restore'], ['--boot'], ['--preboot-diagnose'],
                     ['--check-only'], ['--prepare', '--kit', 'build/kit'],
                     ['--stage', '--kit', 'build/kit', '--output', 'build/out'],
                     ['--prepare', '--kit', 'build/kit', '--output', 'build/out', '--bind', '127.0.0.1']):
            with self.subTest(args=args):
                self.assertEqual(self.call(args)[0], 2)


if __name__ == '__main__':
    unittest.main()
