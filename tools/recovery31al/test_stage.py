#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Injected workspace fixtures only; no production --stage or live backend."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


stage = module('recovery31al_stage_tested', HERE / 'stage.py')
package = module('recovery31al_stage_package_fixture', HERE / 'package.py')
renderer = module('recovery31al_stage_renderer_fixture', HERE / 'render.py')
old_tests = module('recovery31al_original_stage_fixture',
                   ROOT / 'tools/recovery31aj/test_stage_lab.py')
profile_tests = module('recovery31al_original_profile_fixture',
                       ROOT / 'tools/recovery31aj/test_recovery.py')
# Load only digest-admitted original code. Constructing LiveBackend is forbidden
# throughout the tests; only its unchanged metadata guard is exercised.
frozen_stage = package.frozen_stager(ROOT)
_, _, _, server = package.bootstrap(ROOT).admitted(ROOT)
server.INVENTORY, server.PROFILE = package.INVENTORY, package.PROFILE


def sha(data):
    return hashlib.sha256(data).hexdigest()


class FixtureBackend:
    synthetic = True

    def __init__(self, root):
        self.fixture_root = root / 'targets'
        self.value = old_tests.metadata()
        self.calls = 0
        self.hook = None

    def observe(self, frozen):
        self.calls += 1
        if self.hook:
            self.hook(self.calls)
        return copy.deepcopy(self.value)


class StageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.prepared = self.root / 'build/diagnostic-kit'
        self.prepared.mkdir(parents=True)
        helper = b'SYNTHETIC ORIGINAL DIAGNOSTIC READER\n'
        self.value = profile_tests.plan()
        self.value['files']['helper'].update(bytes=len(helper), sha256=sha(helper))
        raw = renderer.profile.canonical(self.value)
        (self.prepared / 'ilinux31aj-reader').write_bytes(helper)
        (self.prepared / 'profile.json').write_bytes(raw)
        # Existing exact portable sources let checked_sources run unmodified.
        portable = (ROOT / frozen_stage.INVENTORY).read_bytes()
        self.names = [line.split('  ', 1)[1] for line in portable.decode().splitlines()]
        self.names.append(frozen_stage.INVENTORY)
        self.names += ['tools/recovery31al/stage.py', 'tools/recovery31al/test_stage.py']
        for name in self.names:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / name).read_bytes())
        self.names.append(package.PROFILE)
        destination = self.root / package.PROFILE
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        inventory = self.root / package.INVENTORY
        inventory.write_text(''.join(sha((self.root / name).read_bytes()) + '  ' + name + '\n'
                                     for name in self.names))
        self.closure = server.source_closure(self.root)
        self.controller = types.SimpleNamespace(
            admitted=self.admitted,
            frozen_stager=lambda root: frozen_stage,
            read_kit=package.read_kit)
        patch = mock.patch.object(frozen_stage, 'LiveBackend',
                                  side_effect=AssertionError('NO LIVE BACKEND'))
        patch.start()
        self.addCleanup(patch.stop)
        self.backend = FixtureBackend(self.root)
        self.base = self.backend.fixture_root / 'lab-data/Users/Shared/iLinuxBoot'
        self.base.mkdir(parents=True)
        self.destination = self.base / stage.DESTINATION

    def admitted(self, root):
        if root != self.root or server.source_closure(root) != self.closure:
            raise ValueError('synthetic source admission refused')
        return root, self.closure[1], renderer, server

    def run_stage(self):
        return stage.stage_kit(self.prepared, self.root, backend=self.backend,
                               controller=self.controller)

    def refused(self, before_query=False):
        with self.assertRaises((ValueError, OSError)):
            self.run_stage()
        self.assertFalse(self.destination.exists())
        if before_query:
            self.assertEqual(self.backend.calls, 0)

    def test_exact_two_files_private_modes_and_nonprivate_receipt(self):
        result = self.run_stage()
        self.assertEqual(result['scope'], 'SYNTHETIC_CONTROL')
        self.assertTrue(result['staged'])
        self.assertEqual({path.name for path in self.destination.iterdir()},
                         {'profile.json', 'ilinux31aj-reader'})
        self.assertEqual(self.destination.stat().st_mode & 0o7777, 0o700)
        for path in self.destination.iterdir():
            self.assertEqual(path.read_bytes(), (self.prepared / path.name).read_bytes())
            self.assertEqual(path.stat().st_mode & 0o7777,
                             0o700 if path.name == 'ilinux31aj-reader' else 0o600)
        for flag in ('boot_settings_changed', 'boot_object_installed', 'default_changed',
                     'policy_read', 'volume_created', 'native_ready'):
            self.assertIs(result[flag], False)
        encoded = json.dumps(result)
        for private in (str(self.root), frozen_stage.DATA, old_tests.uuid(11)):
            self.assertNotIn(private, encoded)
        self.assertEqual(self.backend.calls, 2)

    def test_controller_is_required_and_mutable_package_path_is_never_executed(self):
        path = self.root / 'tools/recovery31al/package.py'
        marker = self.root / 'MUST_NOT_EXECUTE'
        path.write_text('from pathlib import Path\nPath(' + repr(str(marker)) +
                        ').write_text("UNVERIFIED CODE")\nraise RuntimeError("MUST NOT RUN")\n')
        with self.assertRaises(TypeError):
            stage.stage_kit(self.prepared, self.root, backend=self.backend)
        self.assertFalse(marker.exists())
        self.assertEqual(self.backend.calls, 0)
        self.run_stage()
        self.assertFalse(marker.exists())

    def test_old_kit_and_transaction_state_are_untouched_and_not_prerequisites(self):
        for name in ('31aj-kit', '31aj-state', '31ak-kit'):
            path = self.base / name
            path.mkdir()
            (path / 'foreign.keep').write_text('KEEP')
        self.run_stage()
        for name in ('31aj-kit', '31aj-state', '31ak-kit'):
            self.assertEqual((self.base / name / 'foreign.keep').read_text(), 'KEEP')
            self.assertEqual([item.name for item in (self.base / name).iterdir()], ['foreign.keep'])

    def test_existing_destination_is_never_overwritten(self):
        self.destination.mkdir()
        sentinel = self.destination / 'sentinel'
        sentinel.write_text('KEEP')
        with self.assertRaises(ValueError):
            self.run_stage()
        self.assertEqual(sentinel.read_text(), 'KEEP')

    def test_existing_destination_symlink_is_never_followed(self):
        foreign = self.root / 'foreign'
        foreign.mkdir()
        (foreign / 'keep').write_text('KEEP')
        self.destination.symlink_to(foreign, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_stage()
        self.assertTrue(self.destination.is_symlink())
        self.assertEqual((foreign / 'keep').read_text(), 'KEEP')

    def test_helper_hash_and_git_profile_binding_fail_before_query(self):
        for name in ('ilinux31aj-reader', 'profile.json'):
            with self.subTest(name=name):
                path = self.prepared / name
                raw = path.read_bytes()
                path.write_bytes(raw + b'CHANGED')
                self.refused(before_query=True)
                path.write_bytes(raw)

    def test_extra_input_file_refused_before_target_query(self):
        (self.prepared / 'candidate.macho').write_bytes(b'NOT USED')
        self.refused(before_query=True)

    def test_symlink_input_file_refused_before_target_query(self):
        path = self.prepared / 'ilinux31aj-reader'
        raw = path.read_bytes()
        path.unlink()
        other = self.root / 'other'
        other.write_bytes(raw)
        path.symlink_to(other)
        self.refused(before_query=True)

    def test_source_outside_build_refused_before_target_query(self):
        self.prepared = self.root / 'outside-build'
        self.prepared.mkdir()
        self.refused(before_query=True)

    def test_changed_admitted_source_refused_before_target_query(self):
        (self.root / 'tools/recovery31al/stage.py').write_text('# changed\n')
        self.refused(before_query=True)

    def test_nonroot_wrong_model_platform_and_boolean_uid_refused(self):
        for key, value in (('model', 'Mac14,2'), ('euid', 501),
                           ('euid', False), ('platform', 'linux')):
            with self.subTest(key=key, value=value):
                old = self.backend.value[key]
                self.backend.value[key] = value
                self.refused()
                self.backend.value[key] = old

    def test_original_and_data_guard_constraints_remain_unchanged(self):
        for role, key, value in (
            ('original', 'VolumeName', 'Another OS'), ('original', 'MountPoint', '/wrong'),
            ('data', 'APFSVolumeGroupID', old_tests.uuid(99)),
            ('data', 'APFSContainerReference', 'disk9'),
            ('data', 'FileVault', True), ('data', 'FileVault', None),
            ('data', 'Internal', 1), ('data', 'MountPoint', '/wrong')):
            with self.subTest(role=role, key=key, value=value):
                old = self.backend.value[role][key]
                self.backend.value[role][key] = value
                self.refused()
                self.backend.value[role][key] = old

    def test_wrong_data_role_refused(self):
        self.backend.value['apfs']['Containers'][0]['Volumes'][2]['Roles'] = ['System']
        self.refused()

    def test_symbolic_base_component_refused_without_foreign_writes(self):
        real = self.base.with_name('real-base')
        self.base.rename(real)
        self.base.symlink_to(real, target_is_directory=True)
        self.refused()
        self.assertEqual(list(real.iterdir()), [])

    def test_source_changed_before_copy_refused(self):
        def hook(count):
            if count == 1:
                (self.prepared / 'ilinux31aj-reader').write_bytes(b'CHANGED')
        self.backend.hook = hook
        self.refused()

    def test_identical_source_path_replacement_refused(self):
        def hook(count):
            if count == 1:
                path = self.prepared / 'ilinux31aj-reader'
                data = path.read_bytes()
                path.rename(self.root / 'retained-original-reader')
                path.write_bytes(data)
        self.backend.hook = hook
        self.refused()

    def test_source_changed_after_copy_cleans_only_our_new_destination(self):
        def hook(count):
            if count == 2:
                (self.prepared / 'ilinux31aj-reader').write_bytes(b'CHANGED')
        self.backend.hook = hook
        self.refused()

    def test_source_closure_changed_before_copy_refused(self):
        def hook(count):
            if count == 1:
                (self.root / 'tools/recovery31al/stage.py').write_text('# changed\n')
        self.backend.hook = hook
        self.refused()

    def test_metadata_changed_after_copy_refused(self):
        def hook(count):
            if count == 2:
                self.backend.value['data']['APFSVolumeGroupID'] = old_tests.uuid(99)
        self.backend.hook = hook
        self.refused()

    def test_destination_replacement_not_confirmed_or_deleted(self):
        foreign = self.root / 'foreign'
        foreign.mkdir()
        (foreign / 'keep').write_text('KEEP')
        moved = self.base / 'retained-new-kit'
        def hook(count):
            if count == 2:
                self.destination.rename(moved)
                self.destination.symlink_to(foreign, target_is_directory=True)
        self.backend.hook = hook
        with self.assertRaises((ValueError, OSError)):
            self.run_stage()
        self.assertTrue(self.destination.is_symlink())
        self.assertEqual((foreign / 'keep').read_text(), 'KEEP')
        self.assertEqual(list(moved.iterdir()), [])

    def test_foreign_extra_destination_file_preserved_on_refusal(self):
        extra = self.destination / 'foreign.keep'
        def hook(count):
            if count == 2:
                extra.write_text('KEEP')
        self.backend.hook = hook
        with self.assertRaises(ValueError):
            self.run_stage()
        self.assertEqual(extra.read_text(), 'KEEP')
        self.assertEqual([path.name for path in self.destination.iterdir()], ['foreign.keep'])

    def test_base_replacement_preserves_replacement_and_cleans_held_destination(self):
        moved = self.base.with_name('retained-base')
        def hook(count):
            if count == 2:
                self.base.rename(moved)
                self.base.mkdir()
                (self.base / 'foreign.keep').write_text('KEEP')
        self.backend.hook = hook
        with self.assertRaises(ValueError):
            self.run_stage()
        self.assertEqual((self.base / 'foreign.keep').read_text(), 'KEEP')
        self.assertFalse((moved / stage.DESTINATION).exists())

    def test_copied_private_modes_are_verified(self):
        def hook(count):
            if count == 2:
                (self.destination / 'profile.json').chmod(0o644)
        self.backend.hook = hook
        self.refused()

    def test_partial_write_refusal_cleans_only_new_kit(self):
        with mock.patch.object(stage.os, 'write', return_value=0):
            self.refused()
        self.assertEqual({path.name for path in self.prepared.iterdir()},
                         {'profile.json', 'ilinux31aj-reader'})


if __name__ == '__main__':
    unittest.main()
