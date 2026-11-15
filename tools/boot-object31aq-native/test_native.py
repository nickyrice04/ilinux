#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fresh-key full-phase integration; original artifacts are read as data only.

No live snapshot, Recovery capability, private target-group or policy/boot write
is dispatched. Keys are newly generated own bytes in new 0600 workspace files.
"""
import argparse
import copy
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMPILED = OUTPUT = REFERENCE = CANDIDATE_PATH = ROLLBACK_PATH = None
SANITIZE = False
EXTRAS = {'CEPO': '0x1', 'SDOM': '0x1', 'CPRO': '1', 'CSEC': '1',
          'lobo': '1', 'love': '26.1.0.1.2,3'}
CANONICAL_EXTRAS = ('0x0000000000000001', '0x0000000000000001',
                    'true', 'true', 'true', '26.1.0.1.2,3')
ROLLBACK_BYTES = 3932160
ROLLBACK_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_builder():
    spec = importlib.util.spec_from_file_location('build31aq_tested', HERE / 'build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def module_from_verified(sources, name):
    module = types.ModuleType('verified_fixture31aq_' + Path(name).parent.name)
    module.__file__ = str(ROOT / name)
    exec(compile(sources[name], module.__file__, 'exec'), module.__dict__)
    return module


def verify_artifact(path, size, expected):
    """Hash an existing own build artifact without copying a large candidate."""
    if ROOT / 'build' not in path.parents or '..' in path.parts or path.is_symlink():
        raise ValueError('original workspace artifact required')
    if any(parent.is_symlink() for parent in path.parents):
        raise ValueError('original artifact alias')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size != size:
            raise ValueError('original artifact size')
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > size:
                raise ValueError('original artifact bound')
            digest.update(chunk)
        after = os.fstat(descriptor)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if total != size or digest.hexdigest() != expected or any(
                getattr(before, field) != getattr(after, field) for field in fields):
            raise ValueError('original artifact identity')
        return tuple(getattr(before, field) for field in fields)
    finally:
        os.close(descriptor)


def extra_policy(text):
    return text + ''.join('(' + tag + '): ' + value + '\n' for tag, value in EXTRAS.items())


def replace_value(text, tag, value):
    marker = '(' + tag + '): '
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if marker in line:
            lines[index] = line[:line.index(marker) + len(marker)] + value + '\n'
            return ''.join(lines)
    raise AssertionError('synthetic field absent')


class FullPhaseIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.records, sources = cls.builder.retained_sources()
        cls.old = module_from_verified(sources, 'tools/boot-object31aj-native/test_native.py')
        cls.reference_tools = module_from_verified(sources, 'tools/boot-object31ap-native/test_native.py')
        cls.build = json.loads((COMPILED.parent / 'build-result.json').read_text())
        cls.reference_before = sha(REFERENCE.read_bytes())
        cls.payload = cls.reference_tools.reference_payload(REFERENCE)
        cls.selected31af = cls.reference_tools.synthetic_selected(cls.payload)
        cls.candidate_before = verify_artifact(CANDIDATE_PATH, cls.builder.CANDIDATE['bytes'],
                                              cls.builder.CANDIDATE['sha256'])
        cls.rollback_before = verify_artifact(ROLLBACK_PATH, ROLLBACK_BYTES, ROLLBACK_SHA)
        if OUTPUT.exists() or ROOT / 'build' not in OUTPUT.parents or '..' in OUTPUT.parts:
            raise ValueError('fresh workspace test output required')
        if any(parent.is_symlink() for parent in OUTPUT.parents):
            raise ValueError('test output alias')
        OUTPUT.mkdir(parents=True, mode=0o700)
        cls.profile = {'schema': 'ilinux31aj-recovery-profile-v1',
            'target': cls.builder.CANDIDATE['target'],
            'files': {'candidate': {'name': 'candidate.macho',
                     'bytes': cls.builder.CANDIDATE['bytes'], 'sha256': cls.builder.CANDIDATE['sha256']},
                      'helper': {'name': 'ilinux31aj-reader', 'bytes': COMPILED.stat().st_size,
                                 'sha256': sha(COMPILED.read_bytes())},
                      'rollback': {'name': 'm1n1-boot021.bin', 'bytes': ROLLBACK_BYTES,
                                   'sha256': ROLLBACK_SHA}},
            'native_deadline_ms': 90000, 'raw_policy_strategy': 'ctrr_only',
            'initial_payload': '31AF', 'final_payload': 'BOOT021',
            'publication_authorizes_writes': False}
        cls.profile_path = OUTPUT / 'profile.json'
        cls.profile_path.write_text(json.dumps(cls.profile, sort_keys=True, indent=2) + '\n')

    @classmethod
    def tearDownClass(cls):
        if sha(REFERENCE.read_bytes()) != cls.reference_before:
            raise AssertionError('original31AF reference changed')
        if verify_artifact(CANDIDATE_PATH, cls.builder.CANDIDATE['bytes'],
                           cls.builder.CANDIDATE['sha256']) != cls.candidate_before:
            raise AssertionError('original candidate changed')
        if verify_artifact(ROLLBACK_PATH, ROLLBACK_BYTES, ROLLBACK_SHA) != cls.rollback_before:
            raise AssertionError('original rollback changed')

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(prefix='fresh-phase-', dir=OUTPUT)).resolve()
        self.addCleanup(shutil.rmtree, self.case)
        self.sequence = 0
        self.initial_file = self.case / 'synthetic31af.img4'
        self.initial_file.write_bytes(self.selected31af)
        self.key = self.case / 'comparison.key'
        self.generate_key(self.key)

    def generate_key(self, path):
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'wb') as target:
            completed = subprocess.run([str(COMPILED), '--generate-comparison-key',
                '--profile', str(self.profile_path)], stdout=target, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b'')
        self.assertEqual(path.stat().st_size, 32)
        self.assertEqual(path.stat().st_mode & 0o7777, 0o600)

    def invoke(self, *args, profile=None):
        completed = subprocess.run([str(COMPILED), *map(str, args), '--profile',
            str(profile or self.profile_path)], capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.stderr, '')
        self.assertNotIn('PRIVATE_SENTINEL', completed.stdout)
        return completed, json.loads(completed.stdout) if completed.stdout.startswith('{') else completed.stdout

    def save(self, value):
        self.sequence += 1
        path = self.case / ('state-' + str(self.sequence) + '.json')
        with path.open('x') as target:
            json.dump(value, target)
        path.chmod(0o600)
        return path

    def metadata(self, which='initial'):
        selected = {'initial': self.initial_file, 'candidate': CANDIDATE_PATH,
                    'restored': ROLLBACK_PATH, 'raw-policy': self.initial_file}[which]
        value = self.old.metadata(selected)
        ctrr = 'enabled' if which == 'candidate' else 'disabled'
        value['lab_policy'] = extra_policy(self.old.policy(ctrr=ctrr).replace(
            '(smb0, smb1): 1', '(smb0 && smb1): TRUE'))
        value['original_policy'] = extra_policy(self.old.policy('Full', paired=False))
        if which == 'candidate':
            value['lab_policy'] = replace_value(value['lab_policy'], 'coih', '2' * 64)
        elif which == 'restored':
            value['lab_policy'] = replace_value(value['lab_policy'], 'coih', '3' * 64)
        elif which == 'raw-policy':
            value['lab_policy'] = replace_value(value['lab_policy'], 'coih', 'absent')
        return value

    def snapshot(self, which='initial', change=None, *, bound=True, key=None):
        value = self.metadata(which)
        if change:
            change(value)
        self.sequence += 1
        fixture = self.case / ('metadata-' + str(self.sequence) + '.plist')
        fixture.write_bytes(plistlib.dumps(value))
        args = ['--snapshot-fixture', fixture]
        if bound:
            args += ['--comparison-key', key or self.key]
        completed, result = self.invoke(*args)
        if completed.returncode == 0:
            self.assertEqual(result['scope'], 'SYNTHETIC_CONTROL')
            self.assertFalse(result['writes_authorized'])
            self.assertFalse(result['wrapper_authentication_verified'])
            self.assertFalse(result['default_selection_verified'])
        return completed, result

    def phase(self, current, name, baseline=None, *, bound=True, key=None,
              profile=None, production=False):
        args = ['--validate-snapshot' if production else '--validate-fixture-snapshot',
                self.save(current), '--phase', name]
        if baseline is not None:
            args += ['--baseline', self.save(baseline)]
        if bound:
            args += ['--comparison-key', key or self.key]
        return self.invoke(*args, profile=profile)

    def initial(self):
        completed, state = self.snapshot()
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(state['selected_payload'], '31AF')
        self.assertTrue(state['selected_payload_exact'])
        completed, passed = self.phase(state, 'initial')
        self.assertEqual(completed.returncode, 0)
        self.assertTrue(passed['synthetic_control_pass'])
        return state

    def test_real_keyless_then_key_bound_initial_are_distinct(self):
        completed, unbound = self.snapshot(bound=False)
        self.assertEqual(completed.returncode, 0)
        self.assertFalse(unbound['metadata_bound'])
        completed, result = self.phase(unbound, 'initial-admission', bound=False)
        self.assertEqual(completed.returncode, 0)
        self.assertTrue(result['synthetic_control_pass'])
        self.assertEqual(self.phase(unbound, 'initial-admission')[0].returncode, 2)
        self.assertEqual(self.phase(unbound, 'initial', bound=False)[0].returncode, 2)
        bound = self.initial()
        self.assertEqual(self.phase(bound, 'initial-admission', bound=False)[0].returncode, 2)

    def test_real_31af_candidate_raw_policy_boot021_chain(self):
        baseline = self.initial()
        completed, candidate = self.snapshot('candidate')
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(candidate['selected_payload'], 'CANDIDATE')
        self.assertTrue(candidate['selected_payload_exact'])
        self.assertEqual(candidate['lab_ctrr'], 'enabled')
        self.assertEqual(self.phase(candidate, 'candidate', baseline)[0].returncode, 0)
        self.assertEqual(self.phase(candidate, 'before-restore', baseline)[0].returncode, 0)
        completed, raw = self.snapshot('raw-policy')
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(raw['selected_payload'], 'NONE')
        self.assertFalse(raw['selected_payload_exact'])
        self.assertEqual(self.phase(raw, 'raw-policy', baseline)[0].returncode, 0)
        self.assertEqual(self.phase(raw, 'candidate', baseline)[0].returncode, 2)
        completed, restored = self.snapshot('restored')
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(restored['selected_payload'], 'BOOT021')
        self.assertTrue(restored['selected_payload_exact'])
        self.assertEqual(restored['lab_ctrr'], 'disabled')
        self.assertEqual(self.phase(restored, 'restored', baseline)[0].returncode, 0)
        for current in (candidate, raw, restored):
            self.assertEqual(current['lab_metadata_hmac'], baseline['lab_metadata_hmac'])
            self.assertEqual(current['original_metadata_hmac'], baseline['original_metadata_hmac'])

    def test_independent_v3_hmac_contract_binds_qualified_catalog(self):
        state = self.initial()
        key = self.key.read_bytes()
        self.assertTrue(state['comparison_key_id'] == sha(key))
        for role, field in (('LAB', 'lab_metadata_hmac'), ('ORIGINAL', 'original_metadata_hmac')):
            parts = ['ilinux31ao-private-policy-v3', state['profile_sha256'], role,
                'rpnh', '2', 'd' * 96, 'e' * 96, 'ronh', '1', 'f' * 96,
                'spih', '1', '1' * 96, 'stng', '1', '15',
                'ilinux31ao-finite-extra-fields-v1']
            for tag, value in zip(EXTRAS, CANONICAL_EXTRAS):
                parts += [tag, '1', value]
            expected = hmac.new(key, b''.join(item.encode() + b'\0' for item in parts), hashlib.sha256).hexdigest()
            self.assertTrue(state[field] == expected)
        self.assertNotEqual(state['lab_metadata_hmac'], state['original_metadata_hmac'])

    def test_every_stable_extra_mutation_rejects_each_role_against_baseline(self):
        baseline = self.initial()
        replacements = {'CEPO': '0x2', 'SDOM': '0x2', 'CPRO': '0', 'CSEC': '0',
                        'lobo': '0', 'love': '26.1.0.1.2,4'}
        for role in ('lab_policy', 'original_policy'):
            for tag, value in replacements.items():
                with self.subTest(role=role, tag=tag):
                    completed, state = self.snapshot(change=lambda item:
                        item.update({role: replace_value(item[role], tag, value)}))
                    self.assertEqual(completed.returncode, 0)
                    self.assertEqual(self.phase(state, 'before-restore', baseline)[0].returncode, 2)

    def test_stable_extra_removal_rejects_and_canonical_forms_stay_equal(self):
        baseline = self.initial()
        for role in ('lab_policy', 'original_policy'):
            def remove(item):
                item[role] = ''.join(line for line in item[role].splitlines(keepends=True)
                                     if '(lobo):' not in line)
            completed, changed = self.snapshot(change=remove)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(self.phase(changed, 'before-restore', baseline)[0].returncode, 2)
        def canonical(item):
            for role in ('lab_policy', 'original_policy'):
                item[role] = replace_value(item[role], 'CEPO', '0x0000000000000001')
                item[role] = replace_value(item[role], 'CPRO', 'TRUE')
        completed, same = self.snapshot(change=canonical)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(self.phase(same, 'before-restore', baseline)[0].returncode, 0)

    def test_each_extra_reread_change_refuses_collection_before_phase(self):
        replacements = {'CEPO': '0x2', 'SDOM': '0x2', 'CPRO': '0', 'CSEC': '0',
                        'lobo': '0', 'love': '26.1.0.1.2,4'}
        for role in ('lab', 'original'):
            for tag, value in replacements.items():
                def change(item):
                    item[role + '_policy_after'] = replace_value(item[role + '_policy'], tag, value)
                completed, refused = self.snapshot(change=change)
                self.assertEqual(completed.returncode, 2)
                self.assertFalse(refused['writes_authorized'])

    def test_exact_true_conjunction_types_and_unknown_metadata_refuse(self):
        changes = (
            lambda text: text.replace('(smb0 && smb1): TRUE', '(smb0 && smb1): FALSE'),
            lambda text: text + '(smb0): TRUE\n',
            lambda text: replace_value(text, 'love', 'PRIVATE_SENTINEL'),
            lambda text: replace_value(text, 'CSEC', 'absent'),
            lambda text: text + '(CRPO): 1\n',
            lambda text: text + '(auxp): PRIVATE_SENTINEL\n')
        for alteration in changes:
            completed, result = self.snapshot(change=lambda item:
                item.update(lab_policy=alteration(item['lab_policy'])))
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(result['native_ready'])

    def test_wrong_new_key_profile_and_baseline_cannot_be_reused(self):
        baseline = self.initial()
        new_key = self.case / 'different-comparison.key'
        self.generate_key(new_key)
        self.assertEqual(self.phase(baseline, 'initial', key=new_key)[0].returncode, 2)
        completed, other = self.snapshot(key=new_key)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(self.phase(other, 'before-restore', baseline, key=new_key)[0].returncode, 2)
        profile = copy.deepcopy(self.profile)
        profile['native_deadline_ms'] = 30000
        path = self.case / 'different-profile.json'
        path.write_text(json.dumps(profile))
        self.assertEqual(self.phase(baseline, 'initial', profile=path)[0].returncode, 2)
        old_domain = copy.deepcopy(baseline)
        old_domain['lab_metadata_hmac'] = 'a' * 64
        self.assertEqual(self.phase(baseline, 'before-restore', old_domain)[0].returncode, 2)

    def test_keyless_bound_phases_and_production_fixture_claim_are_refused(self):
        baseline = self.initial()
        for phase in ('initial', 'candidate', 'before-restore', 'raw-policy', 'restored'):
            self.assertEqual(self.phase(baseline, phase, baseline if phase != 'initial' else None,
                                        bound=False)[0].returncode, 2)
        self.assertEqual(self.phase(baseline, 'initial', production=True)[0].returncode, 2)

    def test_pairing_original_full_and_original_ctrr_still_guard_snapshots(self):
        changes = (
            lambda item: item.update(lab_policy=item['lab_policy'].replace('Pairing: Paired', 'Pairing: Unpaired')),
            lambda item: item.update(lab_policy=item['lab_policy'].replace('one true recoveryOS', 'macOS')),
            lambda item: item.update(original_policy=extra_policy(self.old.policy())),
            lambda item: item.update(original_policy=extra_policy(self.old.policy('Full', ctrr='disabled'))))
        for change in changes:
            self.assertEqual(self.snapshot(change=change)[0].returncode, 2)

    def test_real_opaque_31af_corruption_fails_initial_identity_guard(self):
        corrupt = bytearray(self.selected31af)
        # Alter an original payload byte, preserving every surrounding length.
        at = self.selected31af.find(self.payload[:64])
        self.assertGreater(at, 0)
        corrupt[at + 64] ^= 1
        self.initial_file.write_bytes(corrupt)
        completed, state = self.snapshot()
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(state['selected_payload'], 'UNKNOWN')
        self.assertEqual(self.phase(state, 'initial')[0].returncode, 2)

    def test_raw_and_restored_ctrr_postconditions_are_explicit(self):
        baseline = self.initial()
        completed, raw = self.snapshot('raw-policy')
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(self.phase(raw, 'raw-policy', baseline)[0].returncode, 0)
        changed = dict(raw, lab_ctrr='enabled')
        self.assertEqual(self.phase(changed, 'raw-policy', baseline)[0].returncode, 2)
        completed, restored = self.snapshot('restored')
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(self.phase(restored, 'restored', baseline)[0].returncode, 0)
        self.assertEqual(self.phase(dict(restored, lab_ctrr='enabled'), 'restored', baseline)[0].returncode, 2)

    def test_intended_lpnh_coih_sip2_scope_keeps_independent_semantic_guards(self):
        baseline = self.initial()
        def rotate(item):
            for role in ('lab_policy', 'original_policy'):
                item[role] = replace_value(item[role], 'lpnh', '9' * 64)
            item['lab_policy'] = replace_value(item['lab_policy'], 'coih', '4' * 64)
            item['lab_policy'] = item['lab_policy'].replace('Kernel CTRR Status: Disabled',
                                                            'Kernel CTRR Status: Enabled')
            item['lab_policy'] = replace_value(item['lab_policy'], 'sip2', 'absent')
        completed, allowed = self.snapshot(change=rotate)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(allowed['lab_metadata_hmac'], baseline['lab_metadata_hmac'])
        self.assertEqual(self.phase(allowed, 'before-restore', baseline)[0].returncode, 0)
        completed, semantic = self.snapshot(change=lambda item:
            item.update(lab_policy=replace_value(item['lab_policy'], 'sip3', 'TRUE')))
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(self.phase(semantic, 'before-restore', baseline)[0].returncode, 2)

    def test_generated_own_key_refuses_nonempty_or_pipe_without_overwrite(self):
        existing = self.case / 'occupied.key'
        existing.write_bytes(b'KEEP')
        existing.chmod(0o600)
        with existing.open('r+b') as target:
            completed = subprocess.run([str(COMPILED), '--generate-comparison-key',
                '--profile', str(self.profile_path)], stdout=target, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(existing.read_bytes(), b'KEEP')
        self.assertEqual(completed.stderr, b'REFUSED\n')
        completed = subprocess.run([str(COMPILED), '--generate-comparison-key',
            '--profile', str(self.profile_path)], capture_output=True, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, b'')

    def test_full_default_help_inert_and_no_boot_write_mode_added(self):
        for args in ((), ('--help',)):
            completed = subprocess.run([str(COMPILED), *args], capture_output=True, text=True, timeout=5)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(completed.stderr, '')
            for mode in ('--snapshot', '--generate-comparison-key', '--validate-snapshot'):
                self.assertIn(mode, completed.stdout)
            self.assertNotIn('--preboot-diagnose', completed.stdout)
        for flag in ('--install', '--restore', '--configure-boot', '--force'):
            self.assertEqual(self.invoke(flag)[0].returncode, 2)

    def test_profile_file_verification_is_exact_and_role_restricted(self):
        helper = self.profile['files']['helper']
        completed, result = self.invoke('--verify-file', COMPILED, '--expected-bytes', helper['bytes'],
                                        '--expected-sha256', helper['sha256'])
        self.assertEqual(completed.returncode, 0)
        self.assertTrue(result['verified'])
        completed, _ = self.invoke('--verify-file', ROLLBACK_PATH, '--expected-bytes', ROLLBACK_BYTES,
                                   '--expected-sha256', ROLLBACK_SHA)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(self.invoke('--verify-file', self.initial_file, '--expected-bytes', len(self.selected31af),
                                     '--expected-sha256', sha(self.selected31af))[0].returncode, 2)

    def test_exact_143_pins_full_cli_and_qualified_pure_state_proof(self):
        self.assertEqual(len(self.records), 143)
        self.assertEqual(self.build['retained_source_pins'], self.records)
        self.assertEqual(self.build['binary_sha256'], sha(COMPILED.read_bytes()))
        self.assertEqual(self.build['source_inputs'], {'build.py': sha((HERE / 'build.py').read_bytes())})
        self.assertEqual(self.build['sanitized'], SANITIZE)
        generated = COMPILED.parent / 'sources'
        for name in ('main.c', 'core.c', 'json.c', 'reader.h'):
            self.assertEqual((generated / name).read_bytes(),
                             (ROOT / 'tools/boot-object31aj-native' / name).read_bytes())
        for key in ('original_full_cli_byte_identical', 'core_json_reader_byte_identical',
                    'diagnostic_marks_stripped', 'qualified_state_matches_31ao',
                    'stripped_reversed_source_equals_original'):
            self.assertIs(self.build['guard_preservation'][key], True)
        generator = module_from_verified({name: (ROOT / name).read_bytes()
            for name in ('tools/boot-object31ao-native/generate.py',)},
            'tools/boot-object31ao-native/generate.py')
        observed = (generated / 'state.observed.c').read_text()
        self.assertEqual(generator.frozen_generator().strip(observed), (generated / 'state.c').read_text())
        self.assertEqual(generator.frozen_generator().strip(generator.reverse(observed)),
                         (ROOT / 'tools/boot-object31aj-native/state.c').read_text())
        self.assertEqual(self.build['candidate_definition'], self.builder.CANDIDATE)

    def test_builder_refuses_reusing_existing_production_directory(self):
        before = sha(COMPILED.read_bytes())
        completed = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'build.py'),
            '--output', str(COMPILED.parent)], capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(json.loads(completed.stdout)['status'], 'REFUSED')
        self.assertEqual(sha(COMPILED.read_bytes()), before)


def main():
    global COMPILED, OUTPUT, REFERENCE, CANDIDATE_PATH, ROLLBACK_PATH, SANITIZE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiled', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference31af', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--rollback', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args, test_args = parser.parse_known_args()
    COMPILED, OUTPUT, REFERENCE = args.compiled.absolute(), args.output.absolute(), args.reference31af.absolute()
    CANDIDATE_PATH, ROLLBACK_PATH = args.candidate.absolute(), args.rollback.absolute()
    SANITIZE = args.sanitize
    if ROOT / 'build' not in COMPILED.parents or not COMPILED.is_file() or COMPILED.is_symlink():
        parser.error('workspace compiled full helper required')
    unittest.main(argv=[sys.argv[0]] + test_args, verbosity=2)


if __name__ == '__main__':
    main()
