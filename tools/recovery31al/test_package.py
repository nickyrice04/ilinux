#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline source, two-file delivery, rendering and inert-dispatch controls."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('package31al_tested', HERE / 'package.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = tool.bootstrap(ROOT).admitted(ROOT)[1]

    def setUp(self):
        build = ROOT / 'build/31al-package-tests'
        build.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=build)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.records = {}
        for name in self.old:
            self.write(name, (ROOT / name).read_bytes())
        self.write(tool.BASE_INVENTORY, (ROOT / tool.BASE_INVENTORY).read_bytes())
        for name in tool.CODE | tool.NATIVE | tool.EVIDENCE | {tool.HANDOFF}:
            data = (ROOT / name).read_bytes() if (ROOT / name).is_file() else b'# fixture\n'
            if name.endswith('.json'):
                data = b'{"scope":"SYNTHETIC_CONTROL"}\n'
            self.write(name, data)
        self.profile = json.loads((ROOT / 'native/boot/attempt31aj-kit/recovery-profile.json').read_bytes())
        self.profile['files']['helper'].update(bytes=4, sha256=tool.sha(b'TEST'))
        data = (json.dumps(self.profile, sort_keys=True, indent=2) + '\n').encode()
        self.write(tool.PROFILE, data)
        delivery = {'files': {'profile.json': {'bytes': len(data), 'sha256': tool.sha(data)},
                             'ilinux31aj-reader': {'bytes': 4, 'sha256': tool.sha(b'TEST')}}}
        self.write('native/boot/attempt31al/delivery.json', json.dumps(delivery).encode())
        receipt = {'schema': 'ilinux31al-native-build-v1',
                   'source_inputs': {n: self.records['tools/boot-object31al-native/' + n]
                        for n in ('build.py', 'generate.py', 'diagnostic.c', 'diagnostic.h', 'main.c')},
                   'guard_preservation': {'core_json_reader_byte_identical': True,
                        'state_marks_strip_exact': True,
                        'frozen_sources': {n: self.records['tools/boot-object31aj-native/' + n]
                             for n in ('core.c', 'json.c', 'reader.h', 'state.c')}},
                   'binary_bytes': 4, 'binary_sha256': tool.sha(b'TEST'),
                   'system_sdk_only': True, 'sanitized': False, 'host_changes': False,
                   'live_run': False, 'recovery_run': False, 'native_ready': False,
                   'candidate_definition': {'schema': 'ilinux31aj-compiled-candidate-v1',
                        'target': self.profile['target'], 'publication_authorizes_writes': False,
                        'bytes': self.profile['files']['candidate']['bytes'],
                        'sha256': self.profile['files']['candidate']['sha256']}}
        self.write('native/boot/attempt31al/build.json', json.dumps(receipt).encode())
        self.kit = self.root / 'build/kit'
        self.kit.mkdir(parents=True)
        (self.kit / 'profile.json').write_bytes(data)
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

    def test_actual_inert_renderer_and_two_file_preparation(self):
        _, records, renderer, server = tool.admitted(self.root)
        self.assertEqual(server.PROFILE, tool.PROFILE)
        self.assertEqual(server.INVENTORY, tool.INVENTORY)
        self.assertIs(server.renderer, renderer)
        result = tool.prepare(self.kit, 'build/pages', self.root)
        self.assertEqual(result['verified_source_count'], len(records))
        self.assertFalse(result['native_ready'])
        self.assertEqual(set(result['output']), {'profile.json', 'diagnose-paste.txt', 'recovery.html'})
        page = self.root / 'build/pages/recovery.html'
        body, checked = server.load_page(page, self.root)
        self.assertEqual(tool.sha(body), result['output']['recovery.html']['sha256'])
        self.assertFalse(checked['native_ready'])
        self.assertIn(b'--diagnose-snapshot', body)
        self.assertNotIn(b'--private-group', body)
        self.assertNotIn(b'kmutil', body)

    def test_retained_guard_edit_refuses_even_if_re_pinned(self):
        n = 'tools/boot-object31aj-native/state.c'
        self.write(n, (self.root / n).read_bytes() + b'\n/* edit */\n')
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_new_source_tamper_refuses_before_execution(self):
        path = self.root / 'tools/recovery31al/render.py'
        path.write_bytes(b'raise RuntimeError("MUST_NOT_EXECUTE")\n')
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_missing_or_arbitrary_inventory_member_refuses(self):
        name = 'tools/recovery31al/test_render.py'
        old = self.records.pop(name)
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)
        self.records[name] = old
        self.write('tools/recovery31al/extra.py', b'# extra\n')
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_new_native_source_is_bounded_text(self):
        self.write('tools/boot-object31al-native/diagnostic.c', b'\x00BINARY')
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_delivery_pin_must_equal_canonical_profile(self):
        n = 'native/boot/attempt31al/delivery.json'
        d = json.loads((self.root / n).read_bytes())
        d['files']['ilinux31aj-reader']['bytes'] += 1
        self.write(n, json.dumps(d).encode())
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_build_source_and_guard_proof_must_match_inventory(self):
        n = 'native/boot/attempt31al/build.json'
        original = (self.root / n).read_bytes()
        for change in ('source', 'proof', 'binary'):
            d = json.loads(original)
            if change == 'source':
                d['source_inputs']['main.c'] = '0' * 64
            elif change == 'proof':
                d['guard_preservation']['state_marks_strip_exact'] = False
            else:
                d['binary_bytes'] += 1
            self.write(n, json.dumps(d).encode())
            self.repin()
            with self.assertRaises(ValueError):
                tool.admitted(self.root)

    def test_profile_override_and_corrupt_helper_refuse_without_output(self):
        for name, data in (('profile.json', b'{}'), ('ilinux31aj-reader', b'FAIL')):
            old = (self.kit / name).read_bytes()
            (self.kit / name).write_bytes(data)
            with self.assertRaises(ValueError):
                tool.prepare(self.kit, 'build/pages', self.root)
            self.assertFalse((self.root / 'build/pages').exists())
            (self.kit / name).write_bytes(old)

    def test_kit_symlink_extra_and_existing_output_refuse(self):
        helper = self.kit / 'ilinux31aj-reader'
        helper.unlink()
        helper.symlink_to(self.kit / 'profile.json')
        with self.assertRaises((ValueError, OSError)):
            tool.prepare(self.kit, 'build/pages', self.root)
        helper.unlink()
        helper.write_bytes(b'TEST')
        (self.kit / 'extra').write_bytes(b'EXTRA')
        with self.assertRaises(ValueError):
            tool.prepare(self.kit, 'build/pages', self.root)
        (self.kit / 'extra').unlink()
        (self.root / 'build/pages').mkdir()
        with self.assertRaises(ValueError):
            tool.prepare(self.kit, 'build/pages', self.root)


class Dispatch(unittest.TestCase):
    def call(self, args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = tool.main(args)
        return rc, out.getvalue()

    def test_help_has_no_admission_or_stage(self):
        with mock.patch.object(tool, 'admitted') as a, mock.patch.object(tool, 'prepare') as p:
            self.assertEqual(self.call([])[0], 0)
        a.assert_not_called()
        p.assert_not_called()

    def test_no_write_boot_modes_or_mixed_options(self):
        cases = (['--install'], ['--restore'], ['--native'], ['--prepare'], ['--stage'],
                 ['--stage', '--kit', 'build/k', '--output', 'build/o'], ['--check-only'],
                 ['--page', 'build/p', '--kit', 'build/k'], ['--bind', '127.0.0.1'])
        with mock.patch.object(tool, 'admitted') as a:
            for args in cases:
                rc, output = self.call(args)
                self.assertEqual(rc, 2)
                self.assertFalse(json.loads(output)['native_ready'])
            a.assert_not_called()

    def test_check_only_forwards_without_starting_socket_here(self):
        seen = []
        server = types.SimpleNamespace(main=lambda: seen.append(sys.argv[:]) or 0)
        old = sys.argv
        with mock.patch.object(tool, 'admitted', return_value=(None, None, None, server)):
            self.assertEqual(self.call(['--page', 'build/page', '--check-only'])[0], 0)
        self.assertEqual(seen, [['serve.py', '--page', 'build/page', '--check-only']])
        self.assertIs(sys.argv, old)

    def test_private_exception_is_not_displayed(self):
        with mock.patch.object(tool, 'admitted', side_effect=ValueError('PRIVATE_MARKER')):
            rc, output = self.call(['--page', 'build/page', '--check-only'])
        self.assertEqual(rc, 2)
        self.assertNotIn('PRIVATE_MARKER', output)

    def test_stage_receives_verified_controller_without_reopening_it(self):
        contents = (b'def stage_kit(kit, root, *, controller):\n'
                    b' assert callable(controller.admitted)\n'
                    b' assert callable(controller.read_kit)\n'
                    b' assert callable(controller.frozen_stager)\n'
                    b' return {"scope":"SYNTHETIC_DISPATCH","native_ready":False}\n')
        server = types.SimpleNamespace(read_bounded=mock.Mock(return_value=contents))
        records = {'tools/recovery31al/stage.py': tool.sha(contents)}
        with mock.patch.object(tool, 'admitted', return_value=(ROOT, records, None, server)) as a:
            rc, output = self.call(['--stage', '--kit', 'build/kit'])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output)['scope'], 'SYNTHETIC_DISPATCH')
        a.assert_called_once_with()
        server.read_bounded.assert_called_once_with('tools/recovery31al/stage.py', ROOT, 65536)


if __name__ == '__main__':
    unittest.main(verbosity=2)
