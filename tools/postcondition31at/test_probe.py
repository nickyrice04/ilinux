#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic files only.  No live observer, policy query or boot writer."""
import contextlib
import copy
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('postcondition31at', HERE / 'probe.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
BUILD = ROOT / 'build/postcondition31at-fixtures'
KEY = bytes(range(32))  # Synthetic own data, never a real comparison key.
KEY_ID = hashlib.sha256(KEY).hexdigest()
PRIVATE_SENTINEL = 'a' * 64


def encode(value):
    return json.dumps(value, separators=(',', ':')).encode('ascii')


def snapshot(selected='CANDIDATE', ctrr='enabled'):
    original = {k: 'ABSENT' for k in p.SEMANTICS}
    lab = dict(original)
    lab.update(smb0=True, smb1=True)
    return {
        'schema': 'ilinux31aj-native-snapshot-v2', 'scope': 'SYNTHETIC_CONTROL',
        'profile_sha256': p.PROFILE_SHA, 'target_binding_verified': True,
        'lab_data_bound': True, 'paired_1tr': True, 'original_security': 'Full',
        'original_ctrr': 'enabled', 'lab_security': 'Permissive', 'lab_ctrr': ctrr,
        'selected_payload': selected, 'selected_payload_exact': True,
        'policy_schema_complete': True, 'original_semantics': original,
        'lab_semantics': lab, 'metadata_bound': True, 'comparison_key_id': KEY_ID,
        'lab_metadata_hmac': PRIVATE_SENTINEL, 'original_metadata_hmac': 'b' * 64,
        'wrapper_authentication_verified': False, 'default_selection_verified': False,
        'restoration_verified': False, 'writes_authorized': False, 'read_only': True,
    }


def compare(base=None, candidate=None, restored=None, key=KEY):
    return p.compare_captures(encode(base if base is not None else snapshot('31AF')),
                              encode(candidate if candidate is not None else snapshot()),
                              key, encode(restored) if restored is not None else None,
                              synthetic=True)


class PredicateTests(unittest.TestCase):
    def test_good_candidate_and_restored_capture(self):
        r = compare(restored=snapshot('BOOT021', 'disabled'))
        self.assertTrue(r['baseline_initial_contract'])
        self.assertTrue(r['candidate_phase_contract'])
        self.assertTrue(r['restored_phase_contract'])

    def test_every_boolean_guard(self):
        positive = ('target_binding_verified', 'lab_data_bound', 'paired_1tr',
                    'policy_schema_complete', 'read_only')
        negative = ('wrapper_authentication_verified', 'default_selection_verified',
                    'restoration_verified', 'writes_authorized')
        for key in positive + negative:
            with self.subTest(key=key):
                s = snapshot()
                s[key] = key in negative
                r = compare(candidate=s)
                self.assertFalse(r['candidate']['native_parse_contract'])
                self.assertFalse(r['candidate_phase_contract'])

    def test_scope_profile_key_and_metadata_binding(self):
        cases = (
            ('scope', 'RECOVERY_GUARDED_READ', 'scope_matches'),
            ('profile_sha256', 'c' * 64, 'profile_matches'),
            ('comparison_key_id', 'c' * 64, 'comparison_key_matches'),
        )
        for field, value, predicate in cases:
            with self.subTest(field=field):
                s = snapshot()
                s[field] = value
                r = compare(candidate=s)
                self.assertFalse(r['candidate'][predicate])
                self.assertFalse(r['candidate_phase_contract'])
        s = snapshot()
        s.update(metadata_bound=False, comparison_key_id='NONE',
                 lab_metadata_hmac='NONE', original_metadata_hmac='NONE')
        self.assertFalse(compare(candidate=s)['candidate']['metadata_bound'])
        self.assertFalse(compare(candidate=s)['candidate_phase_contract'])

    def test_security_and_ctrr_guards(self):
        for field, value, predicate in (
                ('original_security', 'Reduced', 'original_full_recorded'),
                ('original_ctrr', 'disabled', 'original_ctrr_enabled_recorded'),
                ('lab_security', 'Full', 'lab_permissive_recorded')):
            with self.subTest(field=field):
                s = snapshot()
                s[field] = value
                r = compare(candidate=s)
                self.assertFalse(r['candidate'][predicate])
                self.assertFalse(r['candidate_phase_contract'])
        for ctrr in ('disabled', 'unknown'):
            r = compare(candidate=snapshot(ctrr=ctrr))
            self.assertFalse(r['candidate']['lab_ctrr_matches_phase'])
            self.assertFalse(r['candidate_phase_contract'])

    def test_each_role_semantic_and_private_commitment(self):
        for role in ('original', 'lab'):
            for key in p.SEMANTICS:
                with self.subTest(role=role, key=key):
                    s = snapshot()
                    s[role + '_semantics'][key] = '0x0000000000000001' if key == 'sip0' else False
                    r = compare(candidate=s)
                    self.assertFalse(r['candidate'][role + '_semantics_preserved'])
                    self.assertFalse(r['candidate_phase_contract'])
            s = snapshot()
            s[role + '_metadata_hmac'] = 'c' * 64
            r = compare(candidate=s)
            self.assertFalse(r['candidate'][role + '_private_commitment_equal'])
            self.assertFalse(r['candidate_phase_contract'])

    def test_exactness_and_selected_phase(self):
        for selected in ('31AF', 'BOOT021', 'NONE', 'UNKNOWN'):
            with self.subTest(selected=selected):
                s = snapshot(selected)
                s['selected_payload_exact'] = selected not in ('NONE', 'UNKNOWN')
                r = compare(candidate=s)
                self.assertFalse(r['candidate']['selected_payload_matches_phase'])
                self.assertFalse(r['candidate_phase_contract'])
        s = snapshot()
        s['selected_payload_exact'] = False
        r = compare(candidate=s)
        self.assertFalse(r['candidate']['payload_exactness_consistent'])
        self.assertFalse(r['candidate']['selected_payload_exact'])
        self.assertFalse(r['candidate_phase_contract'])

    def test_informational_classes_never_join_phase_contract(self):
        good = compare()
        self.assertTrue(good['candidate_phase_contract'])
        self.assertFalse(any(good['candidate_classification'].values()))
        for selected in ('NONE', 'UNKNOWN'):
            for ctrr in ('disabled', 'unknown'):
                with self.subTest(selected=selected, ctrr=ctrr):
                    s = snapshot(selected, ctrr)
                    s['selected_payload_exact'] = False
                    r = compare(candidate=s)
                    classes = r['candidate_classification']
                    self.assertEqual(classes['selected_payload_none_recorded'], selected == 'NONE')
                    self.assertEqual(classes['selected_payload_unknown_recorded'], selected == 'UNKNOWN')
                    self.assertEqual(classes['lab_ctrr_disabled_recorded'], ctrr == 'disabled')
                    self.assertEqual(classes['lab_ctrr_unknown_recorded'], ctrr == 'unknown')
                    self.assertFalse(r['candidate_phase_contract'])

    def test_baseline_phase_and_key_are_required(self):
        for field, value in (('selected_payload', 'BOOT021'),
                             ('scope', 'RECOVERY_GUARDED_READ'),
                             ('profile_sha256', 'c' * 64),
                             ('comparison_key_id', 'c' * 64)):
            with self.subTest(field=field):
                b = snapshot('31AF')
                b[field] = value
                r = compare(base=b)
                self.assertFalse(r['baseline_initial_contract'])
                self.assertFalse(r['candidate_phase_contract'])
        self.assertFalse(compare(key=bytes(reversed(KEY)))['candidate_phase_contract'])
        with self.assertRaises(p.Refused):
            compare(key=b'x' * 31)

    def test_native_smb_parse_contracts(self):
        for role in ('original', 'lab'):
            for name in ('smb0', 'smb1'):
                with self.subTest(role=role, name=name):
                    s = snapshot()
                    s[role + '_semantics'][name] = role == 'original'
                    r = compare(candidate=s)
                    self.assertFalse(r['candidate'][role + '_smb_contract'])
                    self.assertFalse(r['candidate']['native_parse_contract'])

    def test_restored_optional_and_not_current_verification(self):
        r = compare()
        self.assertFalse(r['restored_capture_present'])
        self.assertNotIn('restored_phase_contract', r)
        r = compare(restored=snapshot('BOOT021', 'enabled'))
        self.assertFalse(r['restored_phase_contract'])
        for name in ('current_policy_verified', 'current_boot_object_verified',
                     'firmware_acceptance_verified', 'rollback_verified', 'native_ready'):
            self.assertFalse(p.envelope()[name])

    def test_only_fixed_output_booleans_no_private_values(self):
        text = json.dumps(compare())
        for forbidden in (PRIVATE_SENTINEL, KEY_ID, p.PROFILE_SHA, 'ABSENT', '31AF', 'CANDIDATE'):
            self.assertNotIn(forbidden, text)
        def check(node):
            if type(node) is dict:
                for value in node.values():
                    check(value)
            else:
                self.assertIs(type(node), bool)
        check(compare(restored=snapshot('BOOT021', 'disabled')))


class SchemaTests(unittest.TestCase):
    def test_duplicate_decoded_keys_and_unknown_keys_refused(self):
        raw = encode(snapshot())
        for bad in (raw[:-1] + b',"read_only":true}',
                    raw[:-1] + b',"read_\\u006fnly":true}',
                    raw[:-1] + b',"new_private_value":"DO_NOT_RETURN"}'):
            with self.subTest(kind=bad[-40:]):
                with self.assertRaises(p.Refused):
                    p.decode_snapshot(bad)

    def test_missing_fields_and_wrong_types(self):
        for key in snapshot():
            s = snapshot()
            del s[key]
            with self.subTest(key=key), self.assertRaises(p.Refused):
                p.decode_snapshot(encode(s))
        for key in p.BOOL_FIELDS:
            s = snapshot()
            s[key] = 1
            with self.subTest(key=key), self.assertRaises(p.Refused):
                p.decode_snapshot(encode(s))

    def test_semantics_exact_type_and_canonical_sip0(self):
        for value in (True, False, 1, '0x1', '0x000000000000000A', '0000000000000001', 'absent'):
            s = snapshot()
            s['lab_semantics']['sip0'] = value
            with self.subTest(value=value), self.assertRaises(p.Refused):
                p.decode_snapshot(encode(s))
        for key in ('smb2', 'sip1'):
            s = snapshot()
            s['lab_semantics'][key] = 'false'
            with self.assertRaises(p.Refused):
                p.decode_snapshot(encode(s))
        s = snapshot()
        s['lab_semantics']['extra'] = False
        with self.assertRaises(p.Refused):
            p.decode_snapshot(encode(s))

    def test_snapshot_hash_and_enums(self):
        for key, value in (('scope', 'OTHER'), ('lab_ctrr', 'ON'),
                           ('selected_payload', 'MACHO'),
                           ('profile_sha256', 'a' * 63),
                           ('comparison_key_id', 'A' * 64),
                           ('lab_metadata_hmac', 'g' * 64)):
            s = snapshot()
            s[key] = value
            with self.subTest(key=key), self.assertRaises(p.Refused):
                p.decode_snapshot(encode(s))

    def test_original_json_grammar_bounds(self):
        for raw in (b'', b'{}\0', b'[]', b'{"a":[]}', b'{"a":1.0}',
                    b'{"a":-1}', b'{"a":NaN}', b'{"a":01}',
                    b'{"a":123456789012345678901}', b'{"a":"\\u0000"}',
                    b'{"a":"\\u0080"}', '{"a":"é"}'.encode(),
                    b'{"' + b'a' * 80 + b'":true}', b'"' + b'a' * 256 + b'"',
                    b'{"x":' * 9 + b'true' + b'}' * 9,
                    encode({str(i): True for i in range(512)}), b' ' * 65537):
            with self.subTest(size=len(raw)), self.assertRaises(p.Refused):
                p.strict_json(raw)


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        BUILD.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='synthetic-', dir=BUILD))
        self.root.chmod(0o700)
        self.state = self.root / 'state'
        self.state.mkdir(mode=0o700)
        self.profile = (ROOT / 'native/boot/attempt31ar-package/profile.json').read_bytes()
        self.files = {
            'session.lock': b'', 'enrolled': b'ENROLLED\n', 'profile.json': self.profile,
            'comparison.key': KEY, 'target.hmac': b'd' * 64,
            'candidate-attempt': b'SPENT\n', 'candidate-exit': b'0\n',
            'baseline.json': encode(snapshot('31AF')), 'candidate.json': encode(snapshot()),
        }
        for name, data in self.files.items():
            self.write(name, data)

    def tearDown(self):
        shutil.rmtree(self.root)

    def write(self, name, data):
        path = self.state / name
        path.write_bytes(data)
        path.chmod(0o600)

    def observe(self, acl_check=p.no_extended_acl):
        return p.observe(str(self.state), synthetic=True, acl_check=acl_check)

    def test_real_fixture_acl_and_secure_read_no_content_mutation(self):
        if sys.platform != 'darwin':
            self.skipTest('Darwin descriptor ACL integration')
        before = {name: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                  for name in self.files for path in (self.state / name,)}
        result = self.observe()
        self.assertEqual(result['status'], 'OBSERVED')
        self.assertTrue(result['candidate_phase_contract'])
        after = {name: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                 for name in self.files for path in (self.state / name,)}
        self.assertEqual(before, after)

    def test_each_required_state_file_absence_refuses(self):
        for name, data in self.files.items():
            with self.subTest(name=name):
                (self.state / name).unlink()
                with self.assertRaises(p.Refused):
                    self.observe(acl_check=lambda fd: True)
                self.write(name, data)

    def test_profile_key_and_markers_corrupt(self):
        for name, data in (('profile.json', self.profile + b' '),
                           ('comparison.key', b'x' * 31),
                           ('target.hmac', b'q' * 64), ('enrolled', b'WRONG\n'),
                           ('candidate-attempt', b'FRESH\n'), ('candidate-exit', b'1\n'),
                           ('session.lock', b'x')):
            with self.subTest(name=name):
                self.write(name, data)
                with self.assertRaises(p.Refused):
                    self.observe(acl_check=lambda fd: True)
                self.write(name, self.files[name])

    def test_private_modes_and_hardlinks_refused(self):
        for name in ('comparison.key', 'candidate.json', 'profile.json'):
            path = self.state / name
            for mode in (0o644, 0o400, 0o660, 0o1600):
                with self.subTest(name=name, mode=mode):
                    path.chmod(mode)
                    with self.assertRaises(p.Refused):
                        self.observe(acl_check=lambda fd: True)
            path.chmod(0o600)
            other = self.root / 'linked'
            os.link(path, other)
            with self.assertRaises(p.Refused):
                self.observe(acl_check=lambda fd: True)
            other.unlink()
        self.state.chmod(0o755)
        with self.assertRaises(p.Refused):
            self.observe(acl_check=lambda fd: True)
        self.state.chmod(0o700)
        self.root.chmod(0o722)
        with self.assertRaises(p.Refused):
            self.observe(acl_check=lambda fd: True)

    def test_acl_present_and_acl_unavailable_refuse(self):
        with self.assertRaises(p.Refused):
            self.observe(acl_check=lambda fd: False)
        def unavailable(fd):
            raise p.Refused('FILESYSTEM', 'ACL_UNAVAILABLE')
        with self.assertRaises(p.Refused):
            self.observe(acl_check=unavailable)

    def test_symlink_at_file_state_and_ancestor_refuses(self):
        path = self.state / 'candidate.json'
        outside = self.root / 'other'
        outside.write_bytes(self.files['candidate.json'])
        outside.chmod(0o600)
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaises(p.Refused):
            self.observe(acl_check=lambda fd: True)
        path.unlink()
        self.write('candidate.json', self.files['candidate.json'])
        link = self.root / 'alias'
        link.symlink_to(self.state, target_is_directory=True)
        with self.assertRaises(p.Refused):
            p.observe(str(link), True, acl_check=lambda fd: True)
        link.unlink()
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(p.Refused):
            p.observe(str(link / 'state'), True, acl_check=lambda fd: True)

    def test_fifo_does_not_block(self):
        path = self.state / 'candidate.json'
        path.unlink()
        os.mkfifo(path, 0o600)
        with self.assertRaises(p.Refused):
            self.observe(acl_check=lambda fd: True)

    def test_busy_controller_lock_refuses(self):
        with (self.state / 'session.lock').open('rb') as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(p.Refused) as failure:
                self.observe(acl_check=lambda fd: True)
            self.assertEqual(failure.exception.reason, 'TRANSACTION_BUSY')

    def test_replacement_and_in_place_change_refuse(self):
        with p.HeldState(str(self.state), os.geteuid(), lambda fd: True) as held:
            held.read('candidate.json', 65536)
            path = self.state / 'candidate.json'
            path.unlink()
            self.write('candidate.json', self.files['candidate.json'])
            with self.assertRaises(p.Refused):
                held.verify()
        with p.HeldState(str(self.state), os.geteuid(), lambda fd: True) as held:
            held.read('candidate.json', 65536)
            self.write('candidate.json', self.files['candidate.json'] + b' ')
            with self.assertRaises(p.Refused):
                held.verify()

    def test_optional_restored_absence_appearance_and_bad_capture(self):
        self.assertFalse(self.observe(acl_check=lambda fd: True)['restored_capture_present'])
        with p.HeldState(str(self.state), os.geteuid(), lambda fd: True) as held:
            self.assertIsNone(held.read('restored.json', 65536, optional=True))
            self.write('restored.json', encode(snapshot('BOOT021', 'disabled')))
            with self.assertRaises(p.Refused):
                held.verify()
        self.assertTrue(self.observe(acl_check=lambda fd: True)['restored_phase_contract'])
        self.write('restored.json', b'{}')
        with self.assertRaises(p.Refused):
            self.observe(acl_check=lambda fd: True)

    def test_oversize_and_wrong_owner_refuse(self):
        self.write('candidate.json', b' ' * 65537)
        with self.assertRaises(p.Refused):
            self.observe(acl_check=lambda fd: True)
        with self.assertRaises(p.Refused):
            with p.HeldState(str(self.state), os.geteuid() + 1, lambda fd: True):
                pass

    def test_fixture_containment_and_root_admission(self):
        for path in ('relative/state', str(ROOT / 'tools/state'), str(BUILD / '../..'),
                     str(self.root / '../state'), str(self.state) + '/'):
            with self.subTest(path=path), self.assertRaises(p.Refused):
                p.observe(path, True, acl_check=lambda fd: True)
        with self.assertRaises(p.Refused):
            p.observe(str(self.state), False, acl_check=lambda fd: True)


class InertTests(unittest.TestCase):
    def test_no_arguments_and_help_never_observe(self):
        with mock.patch.object(p, 'observe', side_effect=AssertionError('must not read')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(p.main([]), 0)
            self.assertEqual(json.loads(out.getvalue())['status'], 'INERT')
            self.assertEqual(json.loads(out.getvalue())['schema'],
                             'ilinux31at-preserved-postcondition-v2')
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as code:
                p.main(['--help'])
            self.assertEqual(code.exception.code, 0)

    def test_unknown_arguments_refuse_without_echo_or_read(self):
        with mock.patch.object(p, 'observe', side_effect=AssertionError('must not read')):
            with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(p.main(['--private-value=SECRET_DO_NOT_RETURN']), 1)
        self.assertNotIn('SECRET', out.getvalue())
        self.assertEqual(err.getvalue(), '')
        self.assertEqual(json.loads(out.getvalue())['failure_reason'], 'OPTIONS_REFUSED')

    def test_failure_does_not_serialize_exception_or_path(self):
        for exc in (OSError('SECRET_PATH_VALUE'), ValueError('SECRET_POLICY_VALUE'),
                    p.Refused('STATE', 'REQUIRED_CAPTURE_ABSENT')):
            with mock.patch.object(p, 'observe', side_effect=exc):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(p.main(['--live']), 1)
            result = out.getvalue()
            self.assertNotIn('SECRET', result)
            self.assertNotIn(p.LIVE_STATE, result)
            self.assertEqual(json.loads(result)['status'], 'REFUSED')


class NativeDifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != 'darwin':
            raise unittest.SkipTest('Original native pure validator needs macOS SDK')
        BUILD.mkdir(parents=True, exist_ok=True)
        cls.directory = Path(tempfile.mkdtemp(prefix='native-oracle-', dir=BUILD))
        cls.sources = ROOT / 'build/boot-object31ar-native/production-v2/sources'
        pins = {
            'state.c': 'bee973746052f6562a9d2d4817bb5014abb6994a7629944e75b7265f9e76d036',
            'core.c': '2e9882eae113e24ba2023fa2843fe8447f3da4ec7e022591d5ca46d987bfcdd8',
            'json.c': 'a06a21280546f02c3ec330b346b95c9a55872e3712198f18bdee7e8e9bdb240f',
            'reader.h': 'bfa3bfe2af667e4b54db1913c80a35d9da4e343cddbc182464d08be674fcbf99',
            'extra_policy.c': 'c721bf59aa262a2b06f69536f5712d5a847dd48793ed33213350bb8270ef669e',
            'extra_policy.h': '1c3f275e3564489c95d60580734dc445beb86b6bc9e0b049ea88017e71e9fb1f',
        }
        for name, digest in pins.items():
            if hashlib.sha256((cls.sources / name).read_bytes()).hexdigest() != digest:
                raise AssertionError('Frozen qualified source pin differs')
        cls.binary = cls.directory / 'fixture-validator'
        command = ['/usr/bin/xcrun', 'clang', '-std=c11', '-O2', '-Wno-deprecated-declarations',
                   '-I', str(cls.sources), '-DWORKSPACE_ROOT="' + str(ROOT) + '"',
                   str(HERE / 'native_fixture.c'),
                   *(str(cls.sources / name) for name in ('state.c', 'core.c', 'json.c', 'extra_policy.c')),
                   '-framework', 'CoreFoundation', '-lcompression', '-o', str(cls.binary)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError('Pure fixture validator compile failed: ' + result.stderr)
        cls.key = cls.directory / 'comparison.key'
        cls.key.write_bytes(KEY)
        cls.key.chmod(0o600)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'directory'):
            shutil.rmtree(cls.directory)

    def assert_agreement(self, base, candidate):
        bp, cp = self.directory / 'baseline.json', self.directory / 'candidate.json'
        bp.write_bytes(encode(base))
        cp.write_bytes(encode(candidate))
        bp.chmod(0o600)
        cp.chmod(0o600)
        result = subprocess.run([str(self.binary), str(bp), str(cp), str(self.key)],
                                capture_output=True, text=True, timeout=5)
        self.assertIn(result.stdout, ('ACCEPTED\n', 'REFUSED\n'))
        self.assertIn(result.returncode, (0, 1))
        try:
            accepted = compare(base, candidate)['candidate_phase_contract']
        except p.Refused:
            accepted = False
        self.assertEqual(accepted, result.returncode == 0)

    def test_exact_native_contract_differential(self):
        self.assert_agreement(snapshot('31AF'), snapshot())
        mutations = [(k, not v) for k, v in snapshot().items() if type(v) is bool]
        mutations += [
            ('scope', 'RECOVERY_GUARDED_READ'), ('profile_sha256', 'c' * 64),
            ('comparison_key_id', 'c' * 64), ('original_security', 'Reduced'),
            ('original_ctrr', 'disabled'), ('lab_security', 'Full'),
            ('lab_ctrr', 'disabled'), ('lab_ctrr', 'unknown'),
            ('lab_metadata_hmac', 'c' * 64), ('original_metadata_hmac', 'c' * 64),
            ('selected_payload', '31AF'), ('selected_payload', 'BOOT021'),
            ('selected_payload', 'UNKNOWN'), ('selected_payload', 'NONE'),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                s = snapshot()
                s[field] = value
                self.assert_agreement(snapshot('31AF'), s)
        for role in ('original', 'lab'):
            for key in p.SEMANTICS:
                with self.subTest(role=role, key=key):
                    s = snapshot()
                    s[role + '_semantics'][key] = '0x0000000000000001' if key == 'sip0' else False
                    self.assert_agreement(snapshot('31AF'), s)
        for field, value in mutations:
            with self.subTest(baseline_field=field):
                b = snapshot('31AF')
                b[field] = value
                self.assert_agreement(b, snapshot())


if __name__ == '__main__':
    unittest.main()
