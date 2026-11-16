#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""31AU closure, kit, fixed-page and synthetic-bootstrap integration tests.

No live backend, controller, Apple writer, mount, policy query or socket runs.
The retained AS shell fixtures intercept both controller calls while checking
genuine new-helper/project bytes as data. Missing production kit is explicit.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('package31au_tested',
                                            Path(__file__).with_name('package.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production = tool.admitted()

    def setUp(self):
        base = ROOT / 'build/31au-package-tests'
        base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=base)).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for name, data in self.production.sources.items():
            self.write(name, data)
        self.write(tool.INVENTORY, self.production.inventory)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def repin(self):
        records = self.production.legacy.parse_inventory((self.root / tool.INVENTORY).read_bytes())
        self.write(tool.INVENTORY, ''.join(tool.sha((self.root / n).read_bytes()) + '  ' + n + '\n'
                                          for n in sorted(records)).encode())

    def test_exact_closure_retains_all167_and_new_dependencies(self):
        state = tool.admitted(self.root)
        self.assertEqual(state.records, self.production.records)
        self.assertEqual(set(state.records), set(tool.frozen(self.root)[3]) |
                         {tool.OLD_INVENTORY} | tool.EXTRA)

    def test_source_only_prepare_all_pages_and_no_overwrite(self):
        report = tool.prepare('build/page', root=self.root)
        self.assertFalse(report['binary_delivery_verified'])
        self.assertFalse(report['controller_run'])
        for name in ('recovery.html', 'install.html', 'restore.html'):
            actual, checked = tool.page_bytes(self.root / 'build/page' / name, self.root)
            self.assertEqual(checked['page_sha256'], tool.sha(actual))
            self.assertFalse(checked['server_started'])
        with self.assertRaises(ValueError):
            tool.prepare('build/page', root=self.root)

    def test_changed_old_source_refuses_before_output(self):
        self.write('tools/boot-object31ar-native/controller.c', b'changed\n')
        with self.assertRaises(ValueError):
            tool.prepare('build/refused', root=self.root)
        self.assertFalse((self.root / 'build/refused').exists())

    def test_new_unknown_or_missing_source_cannot_be_repinned_in(self):
        original = (self.root / tool.INVENTORY).read_bytes()
        self.write('unreviewed.py', b'# added\n')
        self.write(tool.INVENTORY, original + (tool.sha(b'# added\n') + '  unreviewed.py\n').encode())
        with self.assertRaises(ValueError):
            tool.admitted(self.root)
        rows = self.production.legacy.parse_inventory(original)
        rows.pop('tools/boot-object31au-native/read_diagnostics.h')
        self.write(tool.INVENTORY, ''.join(v + '  ' + k + '\n' for k, v in rows.items()).encode())
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_helper_build_binding_refuses_even_if_inventory_repinned(self):
        build = json.loads((self.root / tool.BUILD).read_bytes())
        build['binary_sha256'] = '0' * 64
        self.write(tool.BUILD, json.dumps(build).encode())
        self.repin()
        with self.assertRaises(ValueError):
            tool.admitted(self.root)

    def test_old_profile_transition_or_helper_cannot_be_repinned_in(self):
        initial = self.production.sources[tool.PROFILE]
        for field in ('initial_payload', 'helper_name'):
            value = json.loads(initial)
            if field == 'initial_payload':
                value[field] = '31AF'
            else:
                value['files']['helper']['name'] = 'ilinux31aj-reader'
            self.write(tool.PROFILE, json.dumps(value).encode())
            self.repin()
            with self.assertRaises(ValueError):
                tool.admitted(self.root)

    def test_symlink_source_and_duplicate_inventory_refuse(self):
        source = self.root / 'tools/boot-object31au-native/controller.c'
        other = source.with_name('copy.c')
        source.rename(other)
        source.symlink_to(other)
        with self.assertRaises((ValueError, OSError)):
            tool.admitted(self.root)
        raw = self.production.inventory
        with self.assertRaises(ValueError):
            self.production.legacy.parse_inventory(raw + raw.splitlines(keepends=True)[0])

    def test_page_corruption_nonbuild_and_symlink_output_refuse(self):
        tool.prepare('build/page', root=self.root)
        path = self.root / 'build/page/recovery.html'
        path.write_bytes(path.read_bytes() + b' changed')
        with self.assertRaises(ValueError):
            tool.page_bytes(path, self.root)
        with self.assertRaises(ValueError):
            tool.prepare('outside-page', root=self.root)
        (self.root / 'build/alias').symlink_to(self.root / 'build/page', target_is_directory=True)
        with self.assertRaises(ValueError):
            tool.prepare('build/alias/new', root=self.root)

    def test_fixed_new_route_retains_strict_original_HTTP_parser(self):
        server = self.production.legacy.old_module('serve', self.production.sources, self.root)
        for target, expected in ((b'/', 200), (b'/31au', 200), (b'/31ar', 404),
                                 (b'/31as', 404), (b'/31aj', 404), (b'/31au/x', 404),
                                 (b'/31au?x', 404)):
            with self.subTest(target=target):
                raw = b'GET ' + target + b' HTTP/1.1\r\nHost: test\r\n\r\n'
                self.assertEqual(tool.route(raw, server.request), (expected, False))
        self.assertEqual(tool.route(b'POST /31au HTTP/1.1\r\n\r\n', server.request)[0], 405)
        self.assertEqual(tool.route(b'GET /31au HTTP/1.1\r\nBroken\r\n\r\n', server.request)[0], 400)

    def test_check_only_never_constructs_server(self):
        result = {'status': 'EXACT_PAGE_VERIFIED', 'server_started': False}
        with patch.object(tool, 'page_bytes', return_value=(b'page', result)), \
                patch.object(tool, 'admitted') as admission:
            self.assertEqual(tool.page_service('build/page', True, None, None, None), result)
            admission.assert_not_called()

    def test_kit_ancestor_symlink_and_dot_escape_refuse_before_listing(self):
        state = tool.admitted(self.root)
        build = self.root / 'build'
        build.mkdir(exist_ok=True)
        outside = self.root / 'outside-kit'
        outside.mkdir()
        (build / 'alias').symlink_to(outside, target_is_directory=True)
        with patch.object(tool.os, 'listdir', side_effect=AssertionError('must not enumerate')):
            for path in (build / 'alias', build / 'alias/sub', build / '../outside-kit'):
                with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                    tool.read_kit(path, state)

    def test_inert_and_invalid_modes_never_prepare_stage_serve_or_assemble(self):
        cases = (([], 0), (['--kit', 'build/absent'], 2),
                 (['--prepare', '--output', 'build/new'], 2),
                 (['--prepare-source-page', '--kit', 'build/absent', '--output', 'build/new'], 2),
                 (['--assemble', '--output', 'build/new'], 2),
                 (['--stage', '--kit', 'build/absent', '--seconds', '1'], 2),
                 (['--page', 'build/page', '--seconds', '1801'], 2))
        for args, expected in cases:
            with self.subTest(args=args), patch.object(tool, 'prepare') as prepare, \
                    patch.object(tool, 'stage') as stage, patch.object(tool, 'assemble') as assemble, \
                    patch.object(tool, 'page_service') as serve, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(args), expected)
                for mocked in (prepare, stage, assemble, serve):
                    mocked.assert_not_called()
        with patch.object(tool, 'admitted') as admitted, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                tool.main(['--help'])
            self.assertEqual(result.exception.code, 0)
            admitted.assert_not_called()

    def test_workspace_assemble_and_synthetic_stage_real_newkit(self):
        genuine = ROOT / 'build/ilinux-31au-kit-v2'
        if not genuine.is_dir():
            self.skipTest('Genuine new production kit absent; assembly/copy integration NOT RUN')
        source = self.root / 'build/source-kit'
        source.mkdir(parents=True)
        for path in genuine.iterdir():
            shutil.copyfile(path, source / path.name)
        helper = source / 'ilinux31au-reader'
        args = (helper, source / 'candidate.macho', source / 'm1n1-boot021.bin')
        assembled = tool.assemble('build/assembled', *args, root=self.root)
        self.assertFalse(assembled['lab_stage_run'])
        self.assertEqual(assembled['files'], tool.read_kit(source, tool.admitted(self.root)))
        with self.assertRaises(ValueError):
            tool.assemble('build/assembled', *args, root=self.root)
        frozen = self.production.legacy.verified_module('tools/recovery31aj/test_stage_lab.py',
                                                       self.production.sources, self.root)
        backend = frozen.FixtureBackend(self.root)
        base = backend.fixture_root / 'lab-data/Users/Shared/iLinuxBoot'
        base.mkdir(parents=True)
        parent = backend.fixture_root / 'lab-data/private/var/db'
        parent.mkdir(parents=True, mode=0o755)
        old = parent / 'ilinux31ar-state'
        old.mkdir(mode=0o700)
        (old / 'preserved-sentinel').write_bytes(b'old state retained')
        copied = tool.stage(self.root / 'build/assembled', self.root, backend=backend)
        self.assertEqual(copied['scope'], 'SYNTHETIC_CONTROL')
        self.assertFalse(copied['controller_run'])
        destination = base / '31au-kit'
        self.assertEqual({p.name for p in destination.iterdir()}, {p.name for p in genuine.iterdir()})
        for path in destination.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777,
                             0o700 if path.name == 'ilinux31au-reader' else 0o600)
        self.assertEqual((old / 'preserved-sentinel').read_bytes(), b'old state retained')
        destination.rename(base / 'kept-new-kit')
        new_state = parent / 'ilinux31au-state'
        for kind in ('directory', 'symlink'):
            if kind == 'directory':
                new_state.mkdir(mode=0o700)
            else:
                new_state.symlink_to(self.root / 'absent')
            with self.assertRaises((ValueError, OSError)):
                tool.stage(self.root / 'build/assembled', self.root, backend=backend)
            self.assertFalse(destination.exists())
            new_state.rmdir() if kind == 'directory' else new_state.unlink()


# Reuse the executed original AS bootstrap controls without running its old
# suite. Only namespace selectors are changed; all13 methods exercise AU boxes.
_, legacy, old, retained = tool.frozen()
name = 'tools/recovery31as/test_package.py'
raw = legacy.read_bounded(name, ROOT)
if tool.sha(raw) != retained[name]:
    raise ValueError('shell fixture source pin refused')
original = raw.decode('utf-8')
changes = (('ilinux-31ar-kit', 'ilinux-31au-kit-v2'), ('ilinux31ar', 'ilinux31au'),
           ('ilinux31aj-reader', 'ilinux31au-reader'),
           ('ilinux31as-dependency-refusal-v1', 'ilinux31au-dependency-refusal-v1'))
modified = original
counts = []
for before, after in changes:
    count = modified.count(before)
    if not count:
        raise ValueError('shell fixture selector absent')
    counts.append(count)
    modified = modified.replace(before, after)
reverse = modified
for (before, after), count in reversed(tuple(zip(changes, counts))):
    if reverse.count(after) != count:
        raise ValueError('shell fixture selector collision')
    reverse = reverse.replace(after, before)
if reverse != original:
    raise ValueError('shell fixture reversal refused')
shell_fixture = types.ModuleType('verified31au_shell_fixture')
shell_fixture.__file__ = str(ROOT / name)
exec(compile(modified, shell_fixture.__file__, 'exec'), shell_fixture.__dict__)
shell_fixture.tool = types.SimpleNamespace(REQUIRED=tool.frozen()[0].REQUIRED,
                                           render=lambda value, operation, renderer:
                                               renderer.render(value, operation))


class Shell(shell_fixture.Shell):
    @classmethod
    def setUpClass(cls):
        state = tool.admitted()
        cls.original, cls.value = state.renderer, state.profile
        cls.kit = ROOT / 'build/ilinux-31au-kit-v2'
        if not cls.kit.is_dir():
            raise unittest.SkipTest('Genuine AU kit absent; full bootstrap integration NOT RUN')
        tool.read_kit(cls.kit, state)


if __name__ == '__main__':
    unittest.main(verbosity=2)
