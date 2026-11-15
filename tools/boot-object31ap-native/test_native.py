#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused 31AP integration using real core/collector and original 31AF bytes.

All metadata and manifest surroundings are explicitly synthetic. Fixture mode
simulates mounts using ordinary workspace directories, never host mount calls.
No live Recovery, security, disk or policy command is dispatched by these tests.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMPILED = OUTPUT = REFERENCE = None
SANITIZE = False
REFERENCE_BYTES = 442368
REFERENCE_SHA = '166bea74bf515473057dfd29dc89127d04768945a451e497cc80a9fc53d4951b'
EXTRAS = {'CEPO': '0x1', 'SDOM': '0x1', 'CPRO': '1', 'CSEC': '1',
          'lobo': '1', 'love': '26.1.0.1.2,3'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_builder():
    spec = importlib.util.spec_from_file_location('builder31ap_tested', HERE / 'build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def der(tag, data):
    length = len(data)
    size = (length.bit_length() + 7) // 8
    return bytes([tag]) + (bytes([length]) if length < 128 else
            bytes([128 + size]) + length.to_bytes(size, 'big')) + data


def children(raw):
    """Bounded synthetic/reference envelope reader; no decompression needed."""
    def take(offset, limit):
        if offset + 2 > limit:
            raise ValueError('reference framing')
        tag, first = raw[offset:offset + 2]
        start = offset + 2
        length = first
        if first & 128:
            count = first & 127
            if not 0 < count <= 4 or start + count > limit or raw[start] == 0:
                raise ValueError('reference framing')
            length = int.from_bytes(raw[start:start + count], 'big')
            start += count
            if length < 128:
                raise ValueError('reference framing')
        end = start + length
        if end > limit:
            raise ValueError('reference framing')
        return tag, start, end
    tag, start, end = take(0, len(raw))
    if tag != 0x30 or end != len(raw):
        raise ValueError('reference framing')
    result = []
    while start < end:
        if len(result) >= 8:
            raise ValueError('reference field count')
        tag, value, following = take(start, end)
        result.append((tag, raw[value:following], raw[start:following]))
        start = following
    return result


def reference_payload(path):
    absolute = path.absolute()
    if ROOT / 'build' not in absolute.parents or '..' in absolute.parts or absolute.is_symlink():
        raise ValueError('workspace original reference required')
    if any(parent.is_symlink() for parent in absolute.parents):
        raise ValueError('reference alias')
    if not 0 < absolute.stat().st_size <= 1024 * 1024:
        raise ValueError('reference bound')
    raw = absolute.read_bytes()
    if len(raw) == REFERENCE_BYTES and sha(raw) == REFERENCE_SHA:
        return raw
    fields = children(raw)
    if fields[0][:2] == (0x16, b'IMG4'):
        if len(fields) < 2 or fields[1][0] != 0x30:
            raise ValueError('reference IMG4')
        fields = children(fields[1][2])
    if len(fields) < 4 or fields[0][:2] != (0x16, b'IM4P') or fields[3][0] != 4:
        raise ValueError('reference IM4P')
    payload = fields[3][1]
    if len(payload) != REFERENCE_BYTES or sha(payload) != REFERENCE_SHA:
        raise ValueError('reference original identity')
    return payload


def synthetic_selected(payload, *, duplicate_inner=False):
    # New original fixture bytes, not an Apple manifest or copied host object.
    description = b'synthetic-reference-selected-object'.ljust(39, b'-')
    inner = der(0xa0, b'I' * 300)
    body = der(0x30, der(0x16, b'IM4P') + der(0x16, b'bkrn') +
               der(0x16, description) + der(4, payload) + inner +
               (inner if duplicate_inner else b''))
    return der(0x30, der(0x16, b'IMG4') + body + der(0xa0, b'O' * 2680))


def add_extras(text, extras=EXTRAS):
    return text + ''.join('(' + tag + '): ' + value + '\n' for tag, value in extras.items())


def change_value(text, tag, value):
    marker = '(' + tag + '): '
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if marker in line:
            lines[index] = line[:line.index(marker) + len(marker)] + value + '\n'
            return ''.join(lines)
    raise AssertionError('synthetic field missing')


class RecoveryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builder = load_builder()
        cls.records, sources = builder.retained_sources()
        cls.old = types.ModuleType('verified_original_fixture_factory31ap')
        name = 'tools/boot-object31aj-native/test_native.py'
        cls.old.__file__ = str(ROOT / name)
        exec(compile(sources[name], cls.old.__file__, 'exec'), cls.old.__dict__)
        cls.reference_before = sha(REFERENCE.read_bytes())
        cls.payload = reference_payload(REFERENCE)
        cls.selected_bytes = synthetic_selected(cls.payload)
        if len(cls.selected_bytes) != 445430:
            raise ValueError('synthetic observed-envelope shape mismatch')
        if OUTPUT.exists() or ROOT / 'build' not in OUTPUT.parents or '..' in OUTPUT.parts:
            raise ValueError('fresh workspace test output required')
        OUTPUT.mkdir(parents=True, mode=0o700)
        cls.build = json.loads((COMPILED.parent / 'build-result.json').read_text())
        candidate = cls.build['candidate_definition']
        cls.profile = {'schema': 'ilinux31aj-recovery-profile-v1', 'target': candidate['target'],
            'files': {'candidate': {'name': 'candidate.macho', 'bytes': candidate['bytes'],
                                   'sha256': candidate['sha256']},
                      'helper': {'name': 'ilinux31aj-reader', 'bytes': COMPILED.stat().st_size,
                                 'sha256': sha(COMPILED.read_bytes())},
                      'rollback': {'name': 'm1n1-boot021.bin', 'bytes': 3932160,
                         'sha256': 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'}},
            'native_deadline_ms': 90000, 'raw_policy_strategy': 'ctrr_only',
            'initial_payload': '31AF', 'final_payload': 'BOOT021',
            'publication_authorizes_writes': False}
        cls.profile_path = OUTPUT / 'profile.json'
        cls.profile_path.write_text(json.dumps(cls.profile))

    @classmethod
    def tearDownClass(cls):
        if sha(REFERENCE.read_bytes()) != cls.reference_before:
            raise AssertionError('immutable original reference changed')

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(prefix='case-', dir=OUTPUT)).resolve()
        self.addCleanup(shutil.rmtree, self.case)
        self.scratch = self.case / 'ilinux31am.ABC123'
        self.scratch.mkdir(mode=0o700)
        self.selected = self.case / 'selected.bin'
        self.selected.write_bytes(self.selected_bytes)
        self.value = self.old.metadata(self.selected)
        self.value['lab_policy'] = add_extras(self.old.policy(ctrr='disabled').replace(
            '(smb0, smb1): 1', '(smb0 && smb1): TRUE'))
        self.value['original_policy'] = add_extras(self.old.policy('Full', paired=False))
        before = copy.deepcopy(self.value)
        before['preboot_info']['MountPoint'] = ''
        before['kernel_mounted'] = False
        after = copy.deepcopy(self.value)
        after['preboot_info']['MountPoint'] = str(self.scratch / 'preboot')
        after['kernel_mounted'] = True
        self.value['preboot_info']['MountPoint'] = str(self.scratch / 'preboot')
        self.value.update(preflight_before=before, preflight_before_again=copy.deepcopy(before),
            preflight_after=after, preflight_cleanup=copy.deepcopy(after),
            preflight_final=copy.deepcopy(before))

    def invoke(self, *args, profile=True):
        command = [str(COMPILED), *map(str, args)]
        if profile:
            command += ['--profile', str(self.profile_path)]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.stderr, '')
        self.assertNotIn('PRIVATE_SENTINEL', completed.stdout)
        return completed, json.loads(completed.stdout) if completed.stdout.startswith('{') else completed.stdout

    def fixture(self):
        path = self.case / 'fixture.plist'
        path.write_bytes(plistlib.dumps(self.value))
        completed, result = self.invoke('--diagnose-fixture', path, '--scratch', self.scratch)
        self.assertEqual(result['scope'], 'SYNTHETIC_CONTROL')
        for key in ('preboot_write_requested', 'boot_object_installed', 'security_settings_changed',
                    'native_ready', 'identifiers_returned', 'policy_values_returned'):
            self.assertIs(result[key], False)
        if result['diagnostic']:
            self.assertEqual(result['diagnostic']['command'], 'NONE')
            self.assertIs(result['diagnostic']['read_only'], True)
        return completed, result

    def assert_pass(self):
        completed, result = self.fixture()
        self.assertEqual(completed.returncode, 0, result)
        self.assertEqual((result['status'], result['stage'], result['reason']),
                         ('DIAGNOSTIC_COMPLETE', 'COMPLETE', 'NONE'))
        diagnostic = result['diagnostic']
        self.assertTrue(diagnostic['snapshot_collected'])
        self.assertTrue(diagnostic['initial_admission_valid'])
        self.assertEqual(diagnostic['status'], 'INITIAL_ADMISSION_PASS')
        self.assertFalse(result['mount_state_uncertain'])
        return result

    def assert_refused(self, stage=None, reason=None):
        completed, result = self.fixture()
        self.assertEqual(completed.returncode, 2, result)
        self.assertEqual(result['status'], 'REFUSED')
        if stage is not None:
            self.assertEqual(result['diagnostic']['stage'], stage, result)
        if reason is not None:
            self.assertEqual(result['diagnostic']['reason'], reason, result)
        return result

    def already_mounted(self):
        for phase in ('preflight_before', 'preflight_before_again'):
            self.value[phase]['preboot_info']['MountPoint'] = '/Volumes/Preboot'
            self.value[phase]['kernel_mounted'] = True
        self.value['preboot_info']['MountPoint'] = '/Volumes/Preboot'

    def test_unmounted_full_collection_admission_and_cleanup_pass(self):
        result = self.assert_pass()
        self.assertEqual(result['initial_state'], 'UNMOUNTED_EMPTY')
        self.assertTrue(result['mount_attempted'])
        self.assertTrue(result['mount_created'])
        self.assertTrue(result['mount_read_only_verified'])
        self.assertEqual(result['cleanup'], 'UNMOUNTED')
        self.assertEqual((result['mount_exit'], result['unmount_exit']), (0, 0))
        self.assertFalse((self.scratch / 'preboot').exists())

    def test_existing_mount_full_admission_pass_without_mount_operation(self):
        self.already_mounted()
        result = self.assert_pass()
        self.assertEqual(result['initial_state'], 'MOUNTED_VALID')
        self.assertFalse(result['mount_attempted'])
        self.assertEqual(result['cleanup'], 'NOT_NEEDED')
        self.assertIsNone(result['unmount_exit'])

    def test_renderer_derived_scratch_basename_reaches_full_admission(self):
        path = ROOT / 'tools/recovery31ap/render.py'
        spec = importlib.util.spec_from_file_location('renderer31ap_cross_boundary', path)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        block = renderer.render(copy.deepcopy(self.profile))
        templates = re.findall(r'/usr/bin/mktemp -d (/private/tmp/[A-Za-z0-9_.]+)', block)
        self.assertEqual(len(templates), 1)
        self.assertTrue(templates[0].endswith('.XXXXXX'))
        basename = Path(templates[0]).name.replace('XXXXXX', 'DER123')
        previous = str(self.scratch / 'preboot')
        self.scratch.rmdir()
        self.scratch = self.case / basename
        self.scratch.mkdir(mode=0o700)
        for item in (self.value, *(self.value[phase] for phase in
                    ('preflight_before', 'preflight_before_again', 'preflight_after',
                     'preflight_cleanup', 'preflight_final'))):
            if item['preboot_info']['MountPoint'] == previous:
                item['preboot_info']['MountPoint'] = str(self.scratch / 'preboot')
        result = self.assert_pass()
        self.assertEqual(result['cleanup'], 'UNMOUNTED')

    def test_synthetic_shape_and_original_reference_are_exact(self):
        self.assertEqual(len(self.selected_bytes), 445430)
        self.assertEqual(len(self.payload), REFERENCE_BYTES)
        self.assertEqual(sha(self.payload), REFERENCE_SHA)
        outer = children(self.selected_bytes)
        inner = children(outer[1][2])
        self.assertEqual((len(inner[2][1]), len(inner[4][1]), len(outer[2][1])), (39, 300, 2680))
        self.assertEqual(sha(REFERENCE.read_bytes()), self.reference_before)

    def test_new_fields_and_conjunction_fail_as_such_not_old_unknowns(self):
        self.value['lab_policy'] = change_value(self.value['lab_policy'], 'love', 'PRIVATE_SENTINEL')
        result = self.assert_refused('LAB_POLICY')
        self.assertEqual(result['cleanup'], 'UNMOUNTED')
        self.assertFalse(result['diagnostic']['snapshot_collected'])
        self.assertNotEqual(result['diagnostic']['reason'], 'UNSUPPORTED_METADATA')

    def test_new_field_types_absence_duplicates_and_unknown_are_guarded(self):
        original = self.value['lab_policy']
        bad = [('CEPO', '1'), ('SDOM', '0x10000000000000000'), ('CPRO', '2'),
               ('CSEC', 'absent'), ('lobo', '0x1'), ('love', '1.2.3.4.5,4294967296')]
        for tag, value in bad:
            with self.subTest(tag=tag):
                self.value['lab_policy'] = change_value(original, tag, value)
                self.assert_refused('LAB_POLICY')
        for tag in EXTRAS:
            self.value['lab_policy'] = original + '(' + tag + '): ' + EXTRAS[tag] + '\n'
            self.assert_refused('LAB_POLICY')
        self.value['lab_policy'] = original + '(CRPO): 1\n'
        self.assert_refused('LAB_POLICY', 'UNSUPPORTED_METADATA')

    def test_true_conjunction_duplicates_and_false_are_refused(self):
        original = self.value['lab_policy']
        for extra in ('(smb0): TRUE\n', '(smb1): TRUE\n'):
            self.value['lab_policy'] = original + extra
            self.assert_refused('LAB_POLICY')
        self.value['lab_policy'] = original.replace('(smb0 && smb1): TRUE', '(smb0 && smb1): FALSE')
        self.assert_refused('LAB_POLICY')

    def test_each_role_extra_change_detected_by_real_collection_reread(self):
        alternatives = {'CEPO': '0x2', 'SDOM': '0x2', 'CPRO': '0', 'CSEC': '0',
                        'lobo': '0', 'love': '26.1.0.1.2,4'}
        for role in ('lab', 'original'):
            for tag, value in alternatives.items():
                with self.subTest(role=role, tag=tag):
                    key = role + '_policy_after'
                    self.value[key] = change_value(self.value[role + '_policy'], tag, value)
                    result = self.assert_refused('POLICY_COMPARISON', 'POLICY_CHANGED')
                    self.assertEqual(result['cleanup'], 'UNMOUNTED')
                    self.value.pop(key)

    def test_optional_presence_change_detected_and_canonical_forms_stable(self):
        base = self.value['lab_policy']
        self.value['lab_policy_after'] = ''.join(line for line in base.splitlines(keepends=True)
                                                if '(lobo):' not in line)
        self.assert_refused('POLICY_COMPARISON', 'POLICY_CHANGED')
        self.value['lab_policy_after'] = change_value(base, 'CEPO', '0x0000000000000001')
        self.value['lab_policy_after'] = change_value(self.value['lab_policy_after'], 'CPRO', 'TRUE')
        self.assert_pass()

    def test_pairing_full_security_and_original_ctrr_guards_reached(self):
        original_lab = self.value['lab_policy']
        self.value['lab_policy'] = original_lab.replace('Pairing: Paired', 'Pairing: Unpaired')
        self.assert_refused('RECOVERY_PAIRING', 'NOT_PAIRED')
        self.value['lab_policy'] = original_lab
        original = self.value['original_policy']
        self.value['original_policy'] = add_extras(self.old.policy())
        self.assert_refused('SECURITY_GUARDS', 'ORIGINAL_SECURITY_GUARD')
        self.value['original_policy'] = add_extras(self.old.policy('Full', ctrr='disabled', paired=False))
        self.assert_refused('SECURITY_GUARDS', 'ORIGINAL_CTRR_GUARD')
        self.value['original_policy'] = original
        self.value['lab_policy'] = original_lab.replace('one true recoveryOS', 'macOS')
        self.assert_refused('RECOVERY_PAIRING', 'NOT_ONE_TRUE_RECOVERY')

    def test_existing_auxiliary_refusal_and_private_metadata_comparison_preserved(self):
        original = self.value['lab_policy']
        self.value['lab_policy'] = original + '(auxp): PRIVATE_SENTINEL\n'
        self.assert_refused('LAB_POLICY', 'UNSUPPORTED_METADATA')
        self.value['lab_policy'] = original
        self.value['lab_policy_after'] = change_value(original, 'stng', '16')
        self.assert_refused('POLICY_COMPARISON', 'POLICY_CHANGED')

    def test_selected_payload_corruption_and_envelope_errors_fail_final_admission(self):
        corrupt = bytearray(self.payload)
        corrupt[64] ^= 1
        for selected in (synthetic_selected(bytes(corrupt)),
                         synthetic_selected(self.payload, duplicate_inner=True),
                         self.selected_bytes + b'\0'):
            with self.subTest(bytes=len(selected)):
                self.selected.write_bytes(selected)
                result = self.assert_refused('INITIAL_ADMISSION', 'INITIAL_ADMISSION_GUARD')
                self.assertTrue(result['diagnostic']['snapshot_collected'])
                self.assertEqual(result['cleanup'], 'UNMOUNTED')

    def test_selected_missing_or_symlink_never_gains_admission(self):
        alias = self.case / 'selected-alias.bin'
        alias.symlink_to(self.selected)
        for path in (alias, self.case / 'missing.bin'):
            self.value['selected_file'] = str(path)
            result = self.assert_refused('INITIAL_ADMISSION', 'INITIAL_ADMISSION_GUARD')
            self.assertTrue(result['diagnostic']['snapshot_collected'])

    def test_cleanup_failure_overrides_genuine_initial_admission_pass(self):
        self.value['unmount_exit'] = 7
        self.value['preflight_final'] = copy.deepcopy(self.value['preflight_after'])
        completed, result = self.fixture()
        self.assertEqual(completed.returncode, 2)
        self.assertTrue(result['diagnostic']['initial_admission_valid'])
        self.assertEqual((result['stage'], result['reason'], result['cleanup']),
                         ('CLEANUP', 'UNMOUNT_COMMAND', 'FAILED'))
        self.assertTrue((self.scratch / 'preboot').exists())

    def test_preparation_identity_change_stops_before_collection(self):
        info = self.value['preflight_before_again']
        changed = self.old.uuid(77)
        info['preboot_info']['VolumeUUID'] = changed
        info['apfs_list']['Containers'][0]['Volumes'][2]['APFSVolumeUUID'] = changed
        completed, result = self.fixture()
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(result['reason'], 'IDENTITY_CHANGED')
        self.assertFalse(result['mount_attempted'])
        self.assertIsNone(result['diagnostic'])

    def test_actual_pass_record_roundtrips_unchanged_strict_validator(self):
        result = self.assert_pass()
        path = self.case / 'result.json'
        path.write_text(json.dumps(result))
        completed, checked = self.invoke('--validate-result', path)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(checked, result)
        for modified in (dict(result, PRIVATE_SENTINEL='PRIVATE_SENTINEL'),
                         dict(result, mount_state_uncertain=True),
                         dict(result, scope='RECOVERY_CONDITIONAL_PREBOOT')):
            path.write_text(json.dumps(modified))
            completed, refused = self.invoke('--validate-result', path)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(refused['reason'], 'RESULT_FORMAT')

    def test_profile_binding_and_inert_no_write_cli_remain(self):
        for args in ((), ('--help',)):
            completed, text = self.invoke(*args, profile=False)
            self.assertEqual(completed.returncode, 0)
            self.assertIn('inert', text)
        for flag in ('--install', '--restore', '--repair', '--force'):
            completed, refused = self.invoke(flag, profile=False)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(refused['reason'], 'ARGUMENTS')
        bad = copy.deepcopy(self.profile)
        bad['files']['helper']['sha256'] = 'a' * 64
        path = self.case / 'bad-profile.json'
        path.write_text(json.dumps(bad))
        completed, refused = self.invoke('--diagnose-fixture', self.case / 'never-read',
                                        '--scratch', self.scratch, '--profile', path, profile=False)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(refused['reason'], 'PROFILE_BINDING')

    def test_retained125_pins_proofs_candidate_and_compiler_receipt(self):
        self.assertEqual(self.build['schema'], 'ilinux31ap-native-build-v1')
        self.assertEqual(self.build['retained_source_pins'], self.records)
        self.assertEqual(len(self.records), 125)
        self.assertEqual(self.build['binary_sha256'], sha(COMPILED.read_bytes()))
        self.assertEqual(self.build['sanitized'], SANITIZE)
        self.assertEqual(self.build['candidate_definition']['bytes'], 153190400)
        self.assertEqual(self.build['candidate_definition']['sha256'],
                         '1ea24f0de4aa7d3e82c70a1b35f815791a48342db1a060100226b84dca7d7d01')
        self.assertEqual(self.build['source_inputs'], {'build.py': sha((HERE / 'build.py').read_bytes())})
        proof = self.build['guard_preservation']
        for key in ('preboot_engine_byte_identical', 'cli_result_byte_identical',
                    'diagnostic_support_byte_identical',
                    'extension_reverses_to_frozen_observed_source',
                    'stripped_reversed_source_equals_original'):
            self.assertIs(proof[key], True)
        for name, expected in self.build['frozen_inputs'].items():
            self.assertEqual(sha((ROOT / name).read_bytes()), expected)
            if not name.endswith('generate.py'):
                self.assertEqual((COMPILED.parent / 'sources' / Path(name).name).read_bytes(),
                                 (ROOT / name).read_bytes())
        generator_name = 'tools/boot-object31ao-native/generate.py'
        generator = types.ModuleType('verified_schema_reversal31ap')
        generator.__file__ = str(ROOT / generator_name)
        exec(compile((ROOT / generator_name).read_bytes(), generator.__file__, 'exec'), generator.__dict__)
        state = (COMPILED.parent / 'sources/state.c').read_text()
        self.assertEqual(generator.frozen_generator().strip(generator.reverse(state)),
                         (ROOT / 'tools/boot-object31aj-native/state.c').read_text())

    def test_build_input_refusals_are_private_and_never_rebuild_existing_output(self):
        builder = load_builder()
        with mock.patch.object(builder, 'read_source', return_value=b'PRIVATE_SENTINEL'):
            with self.assertRaises(ValueError):
                builder.retained_sources()
        before = sha(COMPILED.read_bytes())
        completed = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'build.py'),
            '--output', str(COMPILED.parent), '--candidate-definition', 'PRIVATE_SENTINEL'],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn('PRIVATE_SENTINEL', completed.stdout + completed.stderr)
        self.assertEqual(before, sha(COMPILED.read_bytes()))


def main():
    global COMPILED, OUTPUT, REFERENCE, SANITIZE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiled', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference31af', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args, test_args = parser.parse_known_args()
    COMPILED, OUTPUT, REFERENCE = args.compiled.absolute(), args.output.absolute(), args.reference31af.absolute()
    SANITIZE = args.sanitize
    if ROOT / 'build' not in COMPILED.parents or not COMPILED.is_file() or COMPILED.is_symlink():
        parser.error('workspace compiled companion required')
    unittest.main(argv=[sys.argv[0]] + test_args, verbosity=2)


if __name__ == '__main__':
    main()
