#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Portable closure and dispatch controls; workspace fixtures, no live calls."""
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
spec = importlib.util.spec_from_file_location('portable31aj_tested', HERE / 'adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Portable(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'build/31aj-portable-tests'
        base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='synthetic-', dir=base)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        original_bytes = (ROOT / adapter.OLD_INVENTORY).read_bytes()
        original = adapter.parse_inventory(original_bytes)
        self.assertEqual(original.pop(adapter.PRODUCER_FILE), adapter.PRODUCER_SHA)
        self.records = dict(original)
        for name in original:
            self.write(name, (ROOT / name).read_bytes())
        self.write(adapter.OLD_INVENTORY, original_bytes)
        for name in adapter.ADAPTER_FILES:
            self.write(name, (ROOT / name).read_bytes())
        self.write('native/boot/attempt31aj-portable/README.md', b'Original portable test fixture.\n')
        self.write('native/boot/attempt31aj-portable/control.json', b'{"scope":"SYNTHETIC_CONTROL"}\n')
        self.pin()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.records[name] = sha(data)
        return path

    def pin(self):
        path = self.root / adapter.INVENTORY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(value + '  ' + name + '\n'
                               for name, value in sorted(self.records.items())))

    def test_complete_portable_closure_uses_no_producer_executable(self):
        self.assertFalse((self.root / adapter.PRODUCER_FILE).exists())
        real_read = adapter.read_bounded
        def read(root, name, *args):
            self.assertNotEqual(name, adapter.PRODUCER_FILE)
            return real_read(root, name, *args)
        with mock.patch.object(adapter, 'read_bounded', side_effect=read):
            root, data, records, sources = adapter.snapshot(self.root)
        self.assertEqual(root, self.root)
        self.assertEqual(records, self.records)
        self.assertEqual(set(sources), set(records))

    def test_original_inventory_and_all_56_sources_are_immutable(self):
        path = self.root / adapter.OLD_INVENTORY
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            adapter.snapshot(self.root)

    def test_changed_original_digest_cannot_be_repinned(self):
        self.write('tools/recovery31aj/stage_lab.py', b'raise RuntimeError("UNVERIFIED")\n')
        self.pin()
        with self.assertRaises(ValueError):
            adapter.snapshot(self.root)

    def test_missing_original_or_new_adapter_source_refused(self):
        for name in ('tools/recovery31aj/profile.py', 'tools/recovery31aj_portable/test_adapter.py'):
            expected = self.records.pop(name)
            self.pin()
            with self.assertRaises(ValueError):
                adapter.snapshot(self.root)
            self.records[name] = expected

    def test_changed_source_bytes_refused_without_execution(self):
        (self.root / 'tools/recovery31aj/serve.py').write_bytes(b'UNVERIFIED\n')
        with self.assertRaises(ValueError):
            adapter.load_original('page', self.root)

    def test_producer_entry_even_if_present_is_refused(self):
        self.records[adapter.PRODUCER_FILE] = adapter.PRODUCER_SHA
        self.pin()
        with self.assertRaises(ValueError):
            adapter.snapshot(self.root)

    def test_unknown_output_or_code_addition_refused(self):
        for name in ('build/test-readable-host', 'virtualization/jobs/097-direct31aj-readable/out/other',
                     'tools/recovery31aj_portable/unreviewed.py',
                     'native/boot/attempt31aj-portable/out/other.json',
                     'native/boot/attempt31aj-portable/payload.bin'):
            self.records[name] = 'a' * 64
            self.pin()
            with self.assertRaises(ValueError):
                adapter.snapshot(self.root)
            self.records.pop(name)

    def test_new_records_must_be_text_or_json_objects(self):
        name = 'native/boot/attempt31aj-portable/control.json'
        for body in (b'\0', b'[1,2,3]', b'not-json', b'{"x":"\xff"}'):
            self.write(name, body)
            self.pin()
            with self.assertRaises((ValueError, UnicodeError)):
                adapter.snapshot(self.root)

    def test_inventory_cannot_include_itself(self):
        self.records[adapter.INVENTORY] = 'a' * 64
        self.pin()
        with self.assertRaises(ValueError):
            adapter.snapshot(self.root)

    def test_inventory_duplicate_traversal_and_absolute_paths_refused(self):
        cases = [b'a' * 64 + b'  ../outside\n', b'a' * 64 + b'  /absolute\n',
                 b'a' * 64 + b'  a/./b\n', b'a' * 64 + b'  one\n' + b'b' * 64 + b'  one\n']
        for data in cases:
            with self.assertRaises(ValueError):
                adapter.parse_inventory(data)

    def test_file_and_directory_symlinks_refused(self):
        file = self.root / 'tools/recovery31aj/profile.py'
        other = file.with_name('other.py')
        file.rename(other)
        file.symlink_to(other)
        with self.assertRaises((ValueError, OSError)):
            adapter.snapshot(self.root)
        file.unlink()
        other.rename(file)
        directory = file.parent
        moved = directory.with_name('moved')
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            adapter.snapshot(self.root)

    def test_inventory_swap_after_collection_refused(self):
        real_read = adapter.read_bounded
        calls = 0
        def read(root, name, *args):
            nonlocal calls
            body = real_read(root, name, *args)
            if name == adapter.INVENTORY:
                calls += 1
                if calls == 2:
                    return body + b'\n'
            return body
        with mock.patch.object(adapter, 'read_bounded', side_effect=read):
            with self.assertRaises(ValueError):
                adapter.snapshot(self.root)

    def test_fixed_original_module_keeps_target_guards(self):
        stage = adapter.load_original('stage', self.root)
        self.assertEqual(stage.INVENTORY, adapter.INVENTORY)
        self.assertEqual(stage.LAB, '/Volumes/iLinux Boot Lab')
        self.assertEqual(stage.DATA, '/Volumes/iLinux Boot Lab - Data')
        self.assertEqual(stage.DESTINATION, '31aj-kit')
        self.assertEqual(stage.STATE, '31aj-state')
        self.assertEqual(stage.PROFILE, 'native/boot/attempt31aj-kit/recovery-profile.json')
        self.assertEqual(stage.GUARD_SHA, '0728fae7dd30fd2ef14dacdf9e25028614f239c254c8fc40c3f8866fde32dc47')
        page = adapter.load_original('page', self.root)
        self.assertEqual(page.INVENTORY, adapter.INVENTORY)
        self.assertEqual(page.PROFILE, stage.PROFILE)
        self.assertEqual(page.PAGE_LIMIT, 256 * 1024)
        self.assertEqual(page.CLIENT_SECONDS, 1.0)

    def test_dependency_loader_executes_verified_snapshot_not_changed_file(self):
        captured = adapter.snapshot(self.root)
        (self.root / 'tools/recovery31aj/profile.py').write_text('raise RuntimeError("UNVERIFIED")\n')
        (self.root / 'tools/recovery31aj/stage_lab.py').write_text('raise RuntimeError("UNVERIFIED")\n')
        with mock.patch.object(adapter, 'snapshot', return_value=captured):
            stage = adapter.load_original('stage', self.root)
        self.assertEqual(stage.profile.TARGET['model'], 'Mac17,6')
        self.assertEqual(stage.INVENTORY, adapter.INVENTORY)

    def test_original_server_checks_actual_portable_closure_and_page_without_socket(self):
        page_module = adapter.load_original('page', self.root)
        value = page_module.profile.load((self.root / page_module.PROFILE).read_bytes())
        expected = page_module.renderer.page(value).encode()
        page = self.root / 'build/portable-control/recovery.html'
        page.parent.mkdir(parents=True)
        page.write_bytes(expected)
        result, report = page_module.load_page(page, self.root)
        self.assertEqual(result, expected)
        self.assertEqual(report['verified_source_count'], len(self.records))
        self.assertFalse(report['write_authorized'])
        self.assertFalse(report['native_ready'])

    def test_original_stager_source_admission_uses_new_path_without_target_query(self):
        stage = adapter.load_original('stage', self.root)
        with mock.patch.object(stage, 'LiveBackend', side_effect=AssertionError('NO LIVE BACKEND')):
            source, hashes, guard, raw, value = stage.checked_sources(
                self.root, self.root / adapter.INVENTORY)
            self.assertEqual(hashes, self.records)
            self.assertEqual(value['target']['model'], 'Mac17,6')
            self.assertEqual(guard.LAB_NAME, 'iLinux Boot Lab')
            with self.assertRaises(ValueError):
                stage.checked_sources(self.root, self.root / adapter.OLD_INVENTORY)

    def test_loader_refuses_any_unverified_local_dependency(self):
        root, _, _, sources = adapter.snapshot(self.root)
        loader = adapter.SnapshotImports(root, sources)
        for path in (root / 'tools/recovery31aj/unknown.py', root.parent / 'outside.py'):
            with self.assertRaises(ValueError):
                loader.spec_from_file_location('unknown', path)

    def test_default_help_has_no_loader_or_write_calls(self):
        for args in ([], ['--help']):
            with mock.patch.object(adapter, 'load_original') as load, contextlib.redirect_stdout(io.StringIO()):
                if args:
                    with self.assertRaises(SystemExit) as stopped:
                        adapter.main(args)
                    self.assertEqual(stopped.exception.code, 0)
                else:
                    self.assertEqual(adapter.main(args), 0)
                load.assert_not_called()

    def test_explicit_stage_dispatch_keeps_fixed_inventory_and_only_prepared_argument(self):
        calls = []
        module = types.SimpleNamespace(main=lambda args: calls.append(args) or 0)
        with mock.patch.object(adapter, 'load_original', return_value=module) as load:
            rc = adapter.main(['--stage', '--prepared', 'build/SYNTHETIC-PREPARED'])
        self.assertEqual(rc, 0)
        load.assert_called_once_with('stage', adapter.ROOT)
        self.assertEqual(calls, [['--stage', '--prepared', 'build/SYNTHETIC-PREPARED',
                                 '--inventory', str(adapter.ROOT / adapter.INVENTORY)]])

    def test_stage_requires_explicit_flag_and_no_page_overrides(self):
        invalid = [['--prepared', 'build/SYNTHETIC'], ['--stage'],
                   ['--stage', '--prepared', 'build/SYNTHETIC', '--check-only'],
                   ['--stage', '--prepared', 'build/SYNTHETIC', '--bind', '127.0.0.1'],
                   ['--stage', '--prepared', 'build/SYNTHETIC', '--inventory', 'other'],
                   ['--stage', '--prepared', 'build/SYNTHETIC', '--root', '/other'],
                   ['--stage', '--page', 'build/other']]
        for args in invalid:
            with mock.patch.object(adapter, 'load_original') as load, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(adapter.main(args), 2)
                load.assert_not_called()

    def test_page_check_only_dispatch_opens_no_socket(self):
        calls = []
        module = types.SimpleNamespace(main=lambda: calls.append(list(sys.argv)) or 0)
        before = sys.argv
        with mock.patch.object(adapter, 'load_original', return_value=module) as load:
            rc = adapter.main(['--page', 'build/SYNTHETIC.html', '--check-only'])
        self.assertEqual(rc, 0)
        load.assert_called_once_with('page', adapter.ROOT)
        self.assertEqual(calls, [['serve.py', '--page', 'build/SYNTHETIC.html', '--check-only']])
        self.assertIs(sys.argv, before)

    def test_future_server_dispatch_preserves_explicit_network_bounds(self):
        calls = []
        module = types.SimpleNamespace(main=lambda: calls.append(list(sys.argv)) or 0)
        with mock.patch.object(adapter, 'load_original', return_value=module):
            rc = adapter.main(['--page', 'build/SYNTHETIC.html', '--bind', '127.0.0.1',
                               '--port', '0', '--seconds', '1'])
        self.assertEqual(rc, 0)
        self.assertEqual(calls[0][-6:], ['--bind', '127.0.0.1', '--port', '0', '--seconds', '1'])

    def test_loader_refusal_is_fixed_and_suppresses_private_path(self):
        output = io.StringIO()
        with mock.patch.object(adapter, 'load_original', side_effect=OSError('PRIVATE-PATH')), contextlib.redirect_stdout(output):
            self.assertEqual(adapter.main(['--page', 'build/SYNTHETIC.html', '--check-only']), 2)
        self.assertNotIn('PRIVATE-PATH', output.getvalue())
        result = json.loads(output.getvalue())
        self.assertFalse(result['native_ready'])
        self.assertFalse(result['boot_settings_changed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
