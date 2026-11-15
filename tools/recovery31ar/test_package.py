#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Source closure, finite page and copy-adapter controls; no live backend/socket."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('package31ar_tested', Path(__file__).with_name('package.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production = tool.admitted(ROOT)

    def setUp(self):
        base = ROOT / 'build/31ar-package-tests'
        base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=base)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for name, data in self.production[3].items():
            self.write(name, data)
        self.write(tool.INVENTORY, self.production[1])

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def repin(self):
        records = tool.parse_inventory((self.root / tool.INVENTORY).read_bytes())
        raw = ''.join(tool.sha((self.root / name).read_bytes()) + '  ' + name + '\n'
                      for name in sorted(records)).encode()
        self.write(tool.INVENTORY, raw)

    def test_all_retained_sources_and_new_closure_admit(self):
        admitted = tool.admitted(self.root)
        self.assertEqual(admitted[2], self.production[2])
        self.assertEqual(len(admitted[2]), 143 + len(tool.RETAINED) + len(tool.EXTRA))

    def test_default_help_and_bad_argument_combinations_are_inert(self):
        for args, expected in (([], 0), (['--kit', 'build/missing'], 2),
                               (['--prepare', '--output', 'build/new'], 2),
                               (['--prepare-source-page', '--kit', 'build/no',
                                 '--output', 'build/new'], 2),
                               (['--stage', '--kit', 'build/no', '--seconds', '1'], 2)):
            with self.subTest(args=args), patch.object(tool, 'stage') as stage, \
                    patch.object(tool, 'page_service') as page, \
                    patch.object(tool, 'prepare') as prepare, \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(args), expected)
                stage.assert_not_called()
                page.assert_not_called()
                prepare.assert_not_called()
        with patch.object(tool, 'admitted') as admitted, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                tool.main(['--help'])
            self.assertEqual(result.exception.code, 0)
            admitted.assert_not_called()

    def test_source_only_preparation_and_all_exact_pages_without_binary(self):
        report = tool.prepare('build/new-page', root=self.root)
        self.assertFalse(report['binary_delivery_verified'])
        self.assertFalse(report['controller_run'])
        for name in ('recovery.html', 'install.html', 'restore.html'):
            data, checked = tool.page_bytes(self.root / 'build/new-page' / name, self.root)
            self.assertEqual(checked['page_sha256'], tool.sha(data))
            self.assertFalse(checked['server_started'])

    def test_changed_source_refused_before_output_creation(self):
        self.write('tools/boot-object31ar-native/controller.c', b'changed\n')
        with self.assertRaises(ValueError):
            tool.prepare('build/refused', root=self.root)
        self.assertFalse((self.root / 'build/refused').exists())

    def test_manifest_extra_or_missing_native_source_refused(self):
        initial = (self.root / tool.INVENTORY).read_bytes()
        self.write('unreviewed.py', b'# extra\n')
        self.write(tool.INVENTORY, initial + (tool.sha(b'# extra\n') + '  unreviewed.py\n').encode())
        with self.assertRaises(ValueError):
            tool.admitted(self.root)
        records = tool.parse_inventory(initial)
        records.pop('tools/boot-object31ar-native/controller.c')
        self.write(tool.INVENTORY, ''.join(v + '  ' + k + '\n' for k, v in records.items()).encode())
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_changed_build_binding_rejected_even_with_manifest_repin(self):
        receipt = json.loads((self.root / tool.BUILD).read_bytes())
        receipt['binary_sha256'] = '0' * 64
        self.write(tool.BUILD, json.dumps(receipt).encode())
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_symlink_source_and_duplicate_inventory_refused(self):
        name = 'tools/boot-object31ar-native/controller.c'
        source = self.root / name
        other = source.with_name('copy.c')
        source.rename(other)
        source.symlink_to(other)
        with self.assertRaises((ValueError, OSError)):
            tool.admitted(self.root)
        raw = self.production[1]
        with self.assertRaises(ValueError):
            tool.parse_inventory(raw + raw.splitlines(keepends=True)[0])

    def test_page_corruption_and_nonbuild_path_rejected(self):
        tool.prepare('build/new-page', root=self.root)
        page = self.root / 'build/new-page/recovery.html'
        page.write_bytes(page.read_bytes() + b' changed')
        with self.assertRaises(ValueError):
            tool.page_bytes(page, self.root)
        self.write('recovery.html', b'not reviewed')
        with self.assertRaises(ValueError):
            tool.page_bytes(self.root / 'recovery.html', self.root)

    def test_no_overwrite_or_symlink_output(self):
        tool.prepare('build/new-page', root=self.root)
        with self.assertRaises(ValueError):
            tool.prepare('build/new-page', root=self.root)
        (self.root / 'build/alias').symlink_to(self.root / 'build/new-page', target_is_directory=True)
        with self.assertRaises(ValueError):
            tool.prepare('build/alias/sub', root=self.root)

    def test_artifact_exact_same_fd_and_symlink_refusal(self):
        content = b'original synthetic artifact'
        self.write('build/small.bin', content)
        expected = {'bytes': len(content), 'sha256': tool.sha(content)}
        self.assertEqual(tool.artifact('build/small.bin', expected, self.root), expected)
        (self.root / 'build/alias.bin').symlink_to(self.root / 'build/small.bin')
        with self.assertRaises((ValueError, OSError)):
            tool.artifact('build/alias.bin', expected, self.root)
        with self.assertRaises(ValueError):
            tool.artifact('build/small.bin', dict(expected, bytes=1), self.root)

    def test_check_only_does_not_construct_server(self):
        report = {'status': 'EXACT_PAGE_VERIFIED', 'server_started': False}
        with patch.object(tool, 'page_bytes', return_value=(b'exact', report)), \
                patch.object(tool, 'old_module') as old:
            self.assertEqual(tool.page_service('build/page', True, None, None, None), report)
            old.assert_not_called()

    def test_new_http_route_keeps_original_bounded_parser(self):
        server = tool.old_module('serve', self.production[3], self.root)
        for target, expected in ((b'/', 200), (b'/31ar', 200), (b'/31aj', 404),
                                 (b'/files/key', 404), (b'/31ar?x', 404)):
            with self.subTest(target=target):
                request = b'GET ' + target + b' HTTP/1.1\r\nHost: localhost\r\n\r\n'
                self.assertEqual(tool.route_request(request, server.request), (expected, False))
        self.assertEqual(tool.route_request(b'GET /31ar HTTP/1.1\r\nBroken\r\n\r\n',
                                           server.request)[0], 400)
        self.assertEqual(tool.route_request(b'POST /31ar HTTP/1.1\r\n\r\n',
                                           server.request)[0], 405)

    def test_stage_adapter_selects_only_new_names_and_fixed_inventory(self):
        calls = []
        module = type('SyntheticModule', (), {})()
        module.guard_metadata = lambda metadata, frozen: None
        module._stage = lambda kit, inventory, backend, root: calls.append(
            (module.DESTINATION, module.STATE, inventory, backend)) or {
                'scope': 'SYNTHETIC_CONTROL', 'native_ready': False}
        with patch.object(tool, 'read_kit', return_value={}), \
                patch.object(tool, 'old_module', return_value=module):
            result = tool.stage('build/test-only', self.root)
        self.assertEqual(calls, [('31ar-kit', tool.STATE, self.root / tool.INVENTORY, None)])
        self.assertEqual(result['schema'], 'ilinux31ar-lab-data-staging-v1')
        self.assertFalse(result['controller_run'])
        self.assertFalse(result['preboot_mount_run'])

    def test_real_four_file_copy_and_new_state_refusal_in_workspace(self):
        # Genuine retained project bytes; no fake profile or selected identity.
        kit = self.root / 'build/kit'
        kit.mkdir(parents=True)
        production_kit = ROOT / 'build/ilinux-31ar-kit'
        if not production_kit.exists():
            self.skipTest('Exact production kit unavailable; workspace copy integration NOT RUN')
        for name in ('profile.json', 'ilinux31aj-reader', 'candidate.macho', 'm1n1-boot021.bin'):
            shutil.copyfile(production_kit / name, kit / name)
        old = tool.verified_module('tools/recovery31aj/test_stage_lab.py',
                                   self.production[3], self.root)
        backend = old.FixtureBackend(self.root)
        base = backend.fixture_root / 'lab-data/Users/Shared/iLinuxBoot'
        base.mkdir(parents=True)
        state_parent = backend.fixture_root / 'lab-data/private/var/db'
        state_parent.mkdir(parents=True, mode=0o755)
        copied = tool.stage(kit, self.root, backend=backend)
        self.assertEqual(copied['scope'], 'SYNTHETIC_CONTROL')
        self.assertTrue(copied['staged'])
        destination = base / '31ar-kit'
        self.assertEqual({p.name for p in destination.iterdir()},
                         {p.name for p in kit.iterdir()})
        for path in destination.iterdir():
            role = ('helper' if path.name == 'ilinux31aj-reader' else
                    'candidate' if path.name == 'candidate.macho' else 'rollback')
            if path.name == 'profile.json':
                expected = {'bytes': path.stat().st_size,
                            'sha256': tool.sha(self.production[3][tool.PROFILE])}
            else:
                expected = self.production[5]['files'][role]
            self.assertEqual(tool.artifact(path, expected, ROOT)['sha256'],
                             expected['sha256'])
            self.assertEqual(path.stat().st_mode & 0o777,
                             0o700 if path.name == 'ilinux31aj-reader' else 0o600)
        destination.rename(base / 'kept-reviewed-kit')
        state = state_parent / 'ilinux31ar-state'
        for existing in ('directory', 'symlink'):
            with self.subTest(existing=existing):
                if existing == 'directory':
                    state.mkdir(mode=0o700)
                else:
                    state.symlink_to(self.root / 'absent')
                with self.assertRaises((ValueError, OSError)):
                    tool.stage(kit, self.root, backend=backend)
                self.assertFalse(destination.exists())
                if existing == 'directory':
                    state.rmdir()
                else:
                    state.unlink()
        state_parent.rmdir()
        with self.assertRaises((ValueError, OSError)):
            tool.stage(kit, self.root, backend=backend)
        state_parent.symlink_to(self.root / 'build')
        with self.assertRaises((ValueError, OSError)):
            tool.stage(kit, self.root, backend=backend)
        self.assertFalse(destination.exists())
        state_parent.unlink()
        state_parent.mkdir()
        backend.value['model'] = 'Mac14,2'
        with self.assertRaises((ValueError, OSError)):
            tool.stage(kit, self.root, backend=backend)
        self.assertFalse(destination.exists())

    def test_trusted_state_parent_owner_modes_and_acl_fail_closed(self):
        parent = self.root / 'build/trusted-parent'
        parent.mkdir(parents=True, mode=0o755)
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, fd)
        acl = type('SyntheticACL', (), {'no_extended_acl': lambda self, fd: True})()
        tool.trusted_state_parent(fd, acl, os.geteuid())
        with self.assertRaises(ValueError):
            tool.trusted_state_parent(fd, acl, os.geteuid() + 1)
        acl.no_extended_acl = lambda fd: False
        with self.assertRaises(ValueError):
            tool.trusted_state_parent(fd, acl, os.geteuid())
        acl.no_extended_acl = lambda fd: True
        parent.chmod(0o777)
        with self.assertRaises(ValueError):
            tool.trusted_state_parent(fd, acl, os.geteuid())


if __name__ == '__main__':
    unittest.main(verbosity=2)
