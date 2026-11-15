#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh public-source fixtures only; no helper, kit, host query or socket."""
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
spec = importlib.util.spec_from_file_location('source_page31ap_tested', Path(__file__).with_name('prepare.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Prepare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {}
        for row in (ROOT / tool.INVENTORY).read_text().splitlines():
            digest, name = row.split('  ', 1)
            cls.records[name] = digest
        if len(cls.records) != 140:
            raise ValueError('expected frozen source closure')

    def setUp(self):
        parent = ROOT / 'build/31ap-source-page-tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='sources-', dir=parent)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for name in set(self.records) | {tool.INVENTORY}:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        self.assertFalse((self.root / 'build').exists())

    def test_fresh_sources_without_binary_or_kit_prepare_exact_reviewed_page(self):
        result = tool.prepare('build/source-page', self.root)
        self.assertEqual(result['scope'], 'SOURCE_PROFILE_PAGE_ONLY')
        self.assertFalse(result['binary_delivery_verified_on_M1'])
        self.assertFalse(result['kit_consumed'])
        self.assertFalse(result['host_queried'])
        self.assertFalse(result['server_started'])
        self.assertEqual(result['verified_source_count'], 140)
        self.assertEqual(result['output'], tool.EXPECTED)
        output = self.root / 'build/source-page'
        self.assertEqual({p.name for p in output.iterdir()}, set(tool.EXPECTED) | {'receipt.json'})
        self.assertEqual((output / 'profile.json').read_bytes(),
                         (ROOT / 'native/boot/attempt31ap/diagnostic-profile.json').read_bytes())
        package = tool.load_package(self.root)
        _, _, _, server = package.admitted(self.root)
        page, checked = server.load_page(output / 'recovery.html', self.root)
        self.assertEqual(tool.sha(page), tool.EXPECTED['recovery.html']['sha256'])
        self.assertFalse(checked['native_ready'])
        self.assertFalse(any(p.name == 'ilinux31aj-reader' for p in self.root.rglob('*')))

    def test_package_or_inventory_change_refuses_before_import(self):
        for name in (tool.PACKAGE, tool.INVENTORY):
            path = self.root / name
            original = path.read_bytes()
            path.write_text('raise RuntimeError("MUST_NOT_EXECUTE")\n')
            with self.assertRaises(ValueError):
                tool.prepare('build/source-page', self.root)
            self.assertFalse((self.root / 'build').exists())
            path.write_bytes(original)

    def test_source_or_target_profile_change_refuses(self):
        for name in ('tools/boot-object31am-native/preboot.c',
                     'native/boot/attempt31ap/diagnostic-profile.json'):
            path = self.root / name
            original = path.read_bytes()
            if name.endswith('.json'):
                value = json.loads(original)
                value['target']['model'] = 'UNSUPPORTED'
                path.write_text(json.dumps(value))
            else:
                path.write_bytes(original + b'\n/* changed */\n')
            with self.assertRaises(ValueError):
                tool.prepare('build/source-page', self.root)
            self.assertFalse((self.root / 'build').exists())
            path.write_bytes(original)

    def test_bad_destinations_and_existing_output_refused_without_overwrite(self):
        for name in ('build/new/../../outside', 'outside/new', str(self.root.parent / 'outside-new')):
            with self.subTest(name=name), self.assertRaises(ValueError):
                tool.prepare(name, self.root)
        output = self.root / 'build/existing'
        output.mkdir(parents=True)
        sentinel = output / 'preserve'
        sentinel.write_bytes(b'UNCHANGED')
        with self.assertRaises(ValueError):
            tool.prepare(output, self.root)
        self.assertEqual(sentinel.read_bytes(), b'UNCHANGED')
        self.assertEqual({p.name for p in output.iterdir()}, {'preserve'})

    def test_symlink_source_or_output_ancestor_refused(self):
        name = 'tools/recovery31ap/package.py'
        path = self.root / name
        path.unlink()
        path.symlink_to(ROOT / name)
        with self.assertRaises(OSError):
            tool.prepare('build/source-page', self.root)
        path.unlink()
        path.write_bytes((ROOT / name).read_bytes())
        outside = self.root / 'elsewhere'
        outside.mkdir()
        (self.root / 'build').symlink_to(outside)
        with self.assertRaises(ValueError):
            tool.prepare('build/source-page', self.root)
        self.assertEqual(list(outside.iterdir()), [])


class Dispatch(unittest.TestCase):
    def call(self, argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = tool.main(argv)
        return result, output.getvalue()

    def test_default_is_inert(self):
        with patch.object(tool, 'load_package') as loader, patch.object(tool, 'prepare') as prepare:
            self.assertEqual(self.call([])[0], 0)
        loader.assert_not_called()
        prepare.assert_not_called()

    def test_help_is_inert(self):
        with patch.object(tool, 'load_package') as loader, patch.object(tool, 'prepare') as prepare:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                tool.main(['--help'])
        self.assertEqual(result.exception.code, 0)
        loader.assert_not_called()
        prepare.assert_not_called()

    def test_only_explicit_prepare_output_is_supported(self):
        for argv in (['--output', 'build/out'], ['--prepare'], ['--kit', 'build/kit'],
                     ['--stage'], ['--bind', '127.0.0.1'], ['--install'], ['--serve']):
            with self.subTest(argv=argv), patch.object(tool, 'prepare') as prepare:
                self.assertEqual(self.call(argv)[0], 2)
                prepare.assert_not_called()

    def test_runtime_exception_is_fixed_refusal_without_private_text(self):
        with patch.object(tool, 'prepare', side_effect=RuntimeError('PRIVATE_SENTINEL')):
            result, text = self.call(['--prepare', '--output', 'build/out'])
        self.assertEqual(result, 2)
        self.assertNotIn('PRIVATE_SENTINEL', text)
        self.assertFalse(json.loads(text)['native_ready'])


if __name__ == '__main__':
    unittest.main()
