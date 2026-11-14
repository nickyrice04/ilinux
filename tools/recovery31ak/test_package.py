#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Workspace-only admission/dispatch controls; no live backend or sockets."""
import contextlib
import hashlib
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
spec = importlib.util.spec_from_file_location('package31ak_tested', HERE / 'package.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Admission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tool.original_adapter(ROOT)
        cls.original = cls.base.snapshot(ROOT)[2]

    def setUp(self):
        build = ROOT / 'build/31ak-package-tests'
        build.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=build)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.records = dict(self.original)
        for name in self.original:
            self.write(name, (ROOT / name).read_bytes())
        self.write(tool.BASE_INVENTORY, (ROOT / tool.BASE_INVENTORY).read_bytes())
        for name in tool.CODE:
            self.write(name, b'# original synthetic fixture, never live\n')
        self.write('tools/recovery31ak/render.py',
                   b'def render(value, operation): return "SYNTHETIC_"+operation+"\\n"\n'
                   b'def page(value): return "<textarea readonly>SYNTHETIC</textarea>"\n')
        self.repin()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.records[name] = sha(data)

    def repin(self):
        path = self.root / tool.INVENTORY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(digest + '  ' + name + '\n'
                               for name, digest in sorted(self.records.items())))

    def test_retained_originals_and_only_renderer_inventory_replacement(self):
        root, records, renderer, server = tool.admitted(self.root)
        self.assertEqual(root, self.root)
        self.assertTrue(set(self.original) <= set(records))
        self.assertEqual(server.INVENTORY, tool.INVENTORY)
        self.assertIs(server.renderer, renderer)
        self.assertIs(server.prepare.renderer, renderer)
        self.assertEqual(server.PROFILE, tool.PROFILE)
        self.assertEqual(renderer.render({}, 'install'), 'SYNTHETIC_install\n')
        self.assertEqual(server.profile.TARGET, {'model': 'Mac17,6', 'board': 'j716c', 'chip_id': '0x6050'})

    def test_changed_original_source_refuses(self):
        path = self.root / 'tools/recovery31aj/render.py'
        path.write_bytes(path.read_bytes() + b'\n# changed\n')
        self.records['tools/recovery31aj/render.py'] = sha(path.read_bytes())
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_missing_retained_pin_refuses(self):
        self.records.pop('tools/recovery31aj/render.py')
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_changed_base_inventory_refuses(self):
        path = self.root / tool.BASE_INVENTORY
        path.write_bytes(path.read_bytes() + b'\n')
        self.records[tool.BASE_INVENTORY] = sha(path.read_bytes())
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_adapter_symlink_refuses_even_same_bytes(self):
        path = self.root / tool.BASE_ADAPTER
        other = path.with_name('same.py')
        path.rename(other)
        path.symlink_to(other)
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_missing_new_renderer_or_tests_refuses(self):
        for name in ('tools/recovery31ak/render.py', 'tools/recovery31ak/test_paths.py'):
            saved = self.records.pop(name)
            self.repin()
            with self.assertRaises(ValueError):
                tool.admitted(self.root)
            self.records[name] = saved

    def test_unmatched_new_source_never_executes(self):
        marker = self.root / 'must-not-exist'
        name = 'tools/recovery31ak/render.py'
        (self.root / name).write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("BAD")\n')
        with self.assertRaises(ValueError):
            tool.admitted(self.root)
        self.assertFalse(marker.exists())

    def test_producer_output_and_unreviewed_extra_code_refuse(self):
        for name in ('virtualization/jobs/097-direct31aj-readable/out/test-readable-host',
                     'tools/recovery31ak/extra.py'):
            self.write(name, b'UNREVIEWED\n')
            self.repin()
            with self.assertRaises(ValueError):
                tool.admitted(self.root)
            self.records.pop(name)

    def test_public_evidence_allowed_but_binary_and_nonobject_refuse(self):
        name = 'native/boot/attempt31ak/fixture.json'
        self.write(name, b'{"scope":"SYNTHETIC"}\n')
        self.repin()
        tool.admitted(self.root)
        for data in (b'[]\n', b'{"hidden":"\x00"}\n'):
            self.write(name, data)
            self.repin()
            with self.assertRaises((ValueError, UnicodeError)):
                tool.admitted(self.root)

    def test_prepare_routes_fixed_profile_and_inventory(self):
        prepare_call = mock.Mock(return_value={'verified_source_count': 7})
        server = types.SimpleNamespace(prepare=types.SimpleNamespace(prepare=prepare_call))
        with mock.patch.object(tool, 'admitted', return_value=(self.root, dict.fromkeys(range(7)), None, server)):
            result = tool.prepare('build/owned-kit', 'build/new-output', self.root)
        prepare_call.assert_called_once_with(tool.PROFILE, 'build/owned-kit', tool.INVENTORY,
                                             'build/new-output', root=self.root)
        self.assertEqual(result['status'], 'OFFLINE_PREPARATION_PASS')
        self.assertFalse(result['native_ready'])
        self.assertFalse(result['boot_settings_changed'])


class Dispatch(unittest.TestCase):
    def call(self, args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = tool.main(args)
        return rc, out.getvalue()

    def test_default_help_does_not_load_or_act(self):
        with mock.patch.object(tool, 'admitted') as admission, mock.patch.object(tool, 'prepare') as prepare:
            rc, _ = self.call([])
        self.assertEqual(rc, 0)
        admission.assert_not_called()
        prepare.assert_not_called()

    def test_bad_mixed_or_write_options_refuse_before_load(self):
        cases = (['--stage'], ['--prepare'], ['--check-only'], ['--bind', '127.0.0.1'],
                 ['--prepare', '--kit', 'build/kit', '--output', 'build/new', '--page', 'build/page'],
                 ['--page', 'build/page', '--kit', 'build/kit'])
        with mock.patch.object(tool, 'admitted') as admission, mock.patch.object(tool, 'prepare') as prepare:
            for args in cases:
                rc, output = self.call(args)
                self.assertEqual(rc, 2)
                self.assertFalse(json.loads(output)['native_ready'])
            admission.assert_not_called()
            prepare.assert_not_called()

    def test_page_check_passes_only_reviewed_server_options(self):
        observed = []
        server = types.SimpleNamespace(main=lambda: observed.append(list(sys.argv)) or 0)
        previous = sys.argv
        with mock.patch.object(tool, 'admitted', return_value=(None, None, None, server)):
            rc, _ = self.call(['--page', 'build/page', '--check-only'])
        self.assertEqual(rc, 0)
        self.assertEqual(observed, [['serve.py', '--page', 'build/page', '--check-only']])
        self.assertIs(sys.argv, previous)

    def test_refusal_hides_private_exception_details(self):
        with mock.patch.object(tool, 'admitted', side_effect=ValueError('SYNTHETIC_PRIVATE_DETAIL')):
            rc, output = self.call(['--page', 'build/page', '--check-only'])
        self.assertEqual(rc, 2)
        self.assertNotIn('SYNTHETIC_PRIVATE_DETAIL', output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
