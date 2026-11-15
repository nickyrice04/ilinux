#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""New closure/profile/destination controls; no live backend or socket."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('package31am_tested', Path(__file__).with_name('package.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = tool.bootstrap(ROOT).admitted(ROOT)[1]

    def setUp(self):
        base = ROOT / 'build/31am-package-tests'
        base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=base)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.records = {}
        for name in self.old:
            self.write(name, (ROOT / name).read_bytes())
        self.write(tool.BASE_INVENTORY, (ROOT / tool.BASE_INVENTORY).read_bytes())
        for name in tool.CODE | tool.NATIVE | tool.EVIDENCE | {tool.HANDOFF}:
            data = (ROOT / name).read_bytes() if (ROOT / name).is_file() else b'# fixture\n'
            self.write(name, b'{}\n' if name.endswith('.json') else data)
        value = json.loads((ROOT / 'native/boot/attempt31al/diagnostic-profile.json').read_bytes())
        value['files']['helper'].update(bytes=4, sha256=tool.sha(b'TEST'))
        profile = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
        self.write(tool.PROFILE, profile)
        delivery = {'files': {'profile.json': {'bytes': len(profile), 'sha256': tool.sha(profile)},
                             'ilinux31aj-reader': {'bytes': 4, 'sha256': tool.sha(b'TEST')}}}
        self.write('native/boot/attempt31am/delivery.json', json.dumps(delivery).encode())
        build = {'schema': 'ilinux31am-native-build-v1',
                 'source_inputs': {n: self.records['tools/boot-object31am-native/' + n]
                      for n in ('build.py', 'preboot.c', 'preboot.h', 'main.c', 'result.c')},
                 'frozen_inputs': {n: self.old[n] for n in
                      ('tools/boot-object31al-native/generate.py',
                       'tools/boot-object31al-native/diagnostic.c',
                       'tools/boot-object31al-native/diagnostic.h')},
                 'guard_preservation': {'core_json_reader_byte_identical': True,
                      'state_marks_strip_exact': True,
                      'frozen_sources': {n: self.old['tools/boot-object31aj-native/' + n]
                           for n in ('core.c', 'json.c', 'reader.h', 'state.c')}},
                 'binary_bytes': 4, 'binary_sha256': tool.sha(b'TEST'),
                 'system_sdk_only': True, 'sanitized': False, 'host_changes': False,
                 'live_run': False, 'recovery_run': False, 'native_ready': False,
                 'candidate_definition': {'schema': 'ilinux31aj-compiled-candidate-v1',
                      'target': value['target'], 'publication_authorizes_writes': False,
                      'bytes': value['files']['candidate']['bytes'],
                      'sha256': value['files']['candidate']['sha256']}}
        self.write('native/boot/attempt31am/build.json', json.dumps(build).encode())
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

    def test_actual_new_renderer_prepares_and_verifies_without_live_execution(self):
        _, records, renderer, server = tool.admitted(self.root)
        self.assertEqual(len(records), 111)
        self.assertEqual(server.PROFILE, tool.PROFILE)
        self.assertIs(server.renderer, renderer)
        result = tool.prepare(self.kit, 'build/pages', self.root)
        self.assertFalse(result['publication_authorizes_execution'])
        self.assertEqual(result['mount_execution'], 'NOT RUN')
        page, checked = server.load_page(self.root / 'build/pages/recovery.html', self.root)
        self.assertEqual(tool.sha(page), result['output']['recovery.html']['sha256'])
        self.assertIn(b'--preboot-diagnose', page)
        self.assertIn(b'--validate-result', page)
        self.assertNotIn(b'--diagnose-snapshot', page)
        self.assertFalse(checked['native_ready'])

    def test_any_frozen_source_change_refuses_even_repin(self):
        name = 'tools/boot-object31al-native/generate.py'
        self.write(name, (self.root / name).read_bytes() + b'\n# changed\n')
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_missing_extra_or_binary_member_refuses(self):
        name = 'tools/recovery31am/test_render.py'
        old = self.records.pop(name)
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)
        self.records[name] = old
        self.write('tools/recovery31am/extra.py', b'# extra\n')
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)
        self.records.pop('tools/recovery31am/extra.py')
        self.write('tools/boot-object31am-native/preboot.c', b'\0BINARY')
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_unmatched_renderer_never_executes(self):
        (self.root / 'tools/recovery31am/render.py').write_text('raise RuntimeError("MUST_NOT_EXECUTE")\n')
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_build_frozen_proof_and_helper_identity_bound(self):
        name = 'native/boot/attempt31am/build.json'
        original = (self.root / name).read_bytes()
        for case in ('source', 'frozen', 'proof', 'binary'):
            value = json.loads(original)
            if case == 'source':
                value['source_inputs']['preboot.c'] = '0' * 64
            elif case == 'frozen':
                value['frozen_inputs'].pop('tools/boot-object31al-native/diagnostic.c')
            elif case == 'proof':
                value['guard_preservation']['state_marks_strip_exact'] = False
            else:
                value['binary_bytes'] += 1
            self.write(name, json.dumps(value).encode())
            self.repin()
            with self.assertRaises(ValueError):
                tool.admitted(self.root)

    def test_exact_two_file_delivery_and_canonical_profile_required(self):
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

    def test_reused_stager_changes_only_new_destination_and_keeps_guards(self):
        _, records, _, server = tool.admitted(self.root)
        stage = tool.stage_module(self.root, records, server)
        self.assertEqual(stage.DESTINATION, '31am-diagnostic')
        with self.assertRaises(TypeError):
            stage.stage_kit(self.kit, self.root)  # An admitted controller is mandatory.
        original = tool.frozen_stager(self.root)
        self.assertEqual(original.DESTINATION, '31aj-kit')
        self.assertEqual(original.STATE, '31aj-state')


class Dispatch(unittest.TestCase):
    def call(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = tool.main(args)
        return rc, output.getvalue()

    def test_default_does_not_admit_stage_or_prepare(self):
        with mock.patch.object(tool, 'admitted') as a, mock.patch.object(tool, 'stage') as s:
            self.assertEqual(self.call([])[0], 0)
        a.assert_not_called()
        s.assert_not_called()

    def test_no_mount_or_boot_execution_mode_or_mixed_options(self):
        cases = (['--mount'], ['--install'], ['--restore'], ['--native'], ['--prepare'],
                 ['--stage'], ['--page', 'build/p', '--kit', 'build/k'],
                 ['--stage', '--kit', 'build/k', '--output', 'build/o'], ['--check-only'])
        with mock.patch.object(tool, 'admitted') as a, mock.patch.object(tool, 'stage') as s:
            for args in cases:
                rc, output = self.call(args)
                self.assertEqual(rc, 2)
                self.assertFalse(json.loads(output)['native_ready'])
            a.assert_not_called()
            s.assert_not_called()

    def test_check_only_forwarding_and_private_exception_redaction(self):
        seen = []
        server = types.SimpleNamespace(main=lambda: seen.append(sys.argv[:]) or 0)
        previous = sys.argv
        with mock.patch.object(tool, 'admitted', return_value=(None, None, None, server)):
            self.assertEqual(self.call(['--page', 'build/page', '--check-only'])[0], 0)
        self.assertEqual(seen, [['serve.py', '--page', 'build/page', '--check-only']])
        self.assertIs(sys.argv, previous)
        with mock.patch.object(tool, 'admitted', side_effect=ValueError('PRIVATE_MARKER')):
            rc, output = self.call(['--page', 'build/page', '--check-only'])
        self.assertEqual(rc, 2)
        self.assertNotIn('PRIVATE_MARKER', output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
