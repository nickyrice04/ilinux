#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe only preserved 31AR transaction captures; never query live policy.

No arguments and --help are inert.  --live is a fixed-path, root-only read;
--fixture accepts synthetic captures beneath this checkout's build directory.
No private string, exception, file name, hash, policy scalar or key is emitted.
"""
import argparse
import ctypes
import errno
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / 'build'
LIVE_STATE = '/Volumes/iLinux Boot Lab - Data/private/var/db/ilinux31ar-state'
PROFILE_SHA = '27e265da1fac084db457f084dcd8f52b63e5daa1629575a13de64d68f24b4ecc'
PROFILE_BYTES = 823
SCHEMA = 'ilinux31at-preserved-postcondition-v2'
SEMANTICS = frozenset(('smb0', 'smb1', 'smb2', 'smb3', 'smb4',
                       'sip0', 'sip1', 'sip3'))
BOOL_FIELDS = frozenset(('target_binding_verified', 'lab_data_bound', 'paired_1tr',
                        'selected_payload_exact', 'policy_schema_complete',
                        'metadata_bound', 'wrapper_authentication_verified',
                        'default_selection_verified', 'restoration_verified',
                        'writes_authorized', 'read_only'))
SNAPSHOT_KEYS = frozenset(('schema', 'scope', 'profile_sha256',
                         'original_security', 'original_ctrr', 'lab_security',
                         'lab_ctrr', 'selected_payload', 'original_semantics',
                         'lab_semantics', 'comparison_key_id',
                         'lab_metadata_hmac', 'original_metadata_hmac')) | BOOL_FIELDS
SHA = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)
SIP = re.compile(r'0x[0-9a-f]{16}\Z', re.ASCII)


class Refused(Exception):
    """The only public errors are our fixed stage and reason vocabulary."""
    def __init__(self, stage, reason):
        self.stage, self.reason = stage, reason


def refuse(stage, reason):
    raise Refused(stage, reason)


def no_extended_acl(fd):
    """Descriptor-only Darwin ACL check; never inspect/return principals.

    Constants/return convention follow the SDK and the qualified original
    tools/policy31ao/acl_guard.py.  An absent or valid empty ACL alone passes.
    """
    if sys.platform != 'darwin':
        refuse('FILESYSTEM', 'ACL_UNAVAILABLE')
    api = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    api.acl_get_fd_np.argtypes = [ctypes.c_int, ctypes.c_int]
    api.acl_get_fd_np.restype = ctypes.c_void_p
    api.acl_valid.argtypes = [ctypes.c_void_p]
    api.acl_valid.restype = ctypes.c_int
    api.acl_get_entry.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                  ctypes.POINTER(ctypes.c_void_p)]
    api.acl_get_entry.restype = ctypes.c_int
    api.acl_free.argtypes = [ctypes.c_void_p]
    api.acl_free.restype = ctypes.c_int
    ctypes.set_errno(0)
    acl = api.acl_get_fd_np(fd, 0x100)
    if not acl:
        if ctypes.get_errno() == errno.ENOENT:
            return True
        refuse('FILESYSTEM', 'ACL_UNAVAILABLE')
    try:
        if api.acl_valid(acl):
            refuse('FILESYSTEM', 'ACL_UNAVAILABLE')
        entry = ctypes.c_void_p()
        ctypes.set_errno(0)
        result = api.acl_get_entry(acl, 0, ctypes.byref(entry))
        error = ctypes.get_errno()
        if result == 0 and entry.value:
            return False
        if result == -1 and error == errno.EINVAL and not entry.value:
            return True
        refuse('FILESYSTEM', 'ACL_UNAVAILABLE')
    finally:
        if api.acl_free(acl):
            refuse('FILESYSTEM', 'ACL_UNAVAILABLE')


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid,
            info.st_gid, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


class HeldState:
    """Walk without symlinks, retain all FDs, verify all names again at end.

    Only known regular files are opened.  O_NONBLOCK prevents a substituted
    FIFO/device from blocking before the descriptor's type can be checked.
    """
    def __init__(self, path, owner, acl_check=no_extended_acl):
        self.path, self.owner, self.acl_check = path, owner, acl_check
        self.fds, self.names, self.records, self.absent = [], [], [], []
        self.fd = self.parent_fd = None

    def _open(self, name, flags, parent=None):
        try:
            fd = os.open(name, flags, dir_fd=parent)
        except OSError:
            refuse('FILESYSTEM', 'OPEN_REFUSED')
        self.fds.append(fd)
        return fd

    def _private(self, fd, directory=False, parent=False):
        info = os.fstat(fd)
        kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        mode = stat.S_IMODE(info.st_mode)
        proper_mode = not (mode & 0o22) if parent else mode == (0o700 if directory else 0o600)
        if (not kind or info.st_uid != self.owner or not proper_mode or
                (not directory and info.st_nlink != 1)):
            refuse('FILESYSTEM', 'OWNERSHIP_MODE_OR_TYPE')
        if not self.acl_check(fd):
            refuse('FILESYSTEM', 'ACL_PRESENT')
        return info

    def __enter__(self):
        try:
            parts = self.path.split('/')
            if (not self.path.startswith('/') or len(self.path) >= 4096 or
                    any(p in ('', '.', '..') for p in parts[1:])):
                refuse('FILESYSTEM', 'PATH_REFUSED')
            flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
            parent = self._open('/', flags | os.O_DIRECTORY)
            for name in parts[1:]:
                fd = self._open(name, flags | os.O_DIRECTORY, parent)
                self.names.append((parent, name, fd))
                parent = fd
            self.fd = parent
            self.parent_fd = self.names[-1][0]
            self._private(self.parent_fd, directory=True, parent=True)
            self._private(self.fd, directory=True)
            # Record every held directory, including ancestors.  Checking names
            # against these descriptors refuses rename/replacement races.
            self.records = [(fd, identity(os.fstat(fd))) for fd in self.fds]
            return self
        except BaseException:
            self.close()
            raise

    def read(self, name, limit, optional=False):
        if not re.fullmatch(r'[a-z][a-z0-9.-]*', name, re.ASCII):
            refuse('INTERNAL', 'FIXED_NAME_REQUIRED')
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            fd = os.open(name, flags, dir_fd=self.fd)
        except FileNotFoundError:
            if optional:
                self.absent.append(name)
                return None
            refuse('STATE', 'REQUIRED_CAPTURE_ABSENT')
        except OSError:
            refuse('FILESYSTEM', 'OPEN_REFUSED')
        self.fds.append(fd)
        info = self._private(fd)
        if info.st_size > limit:
            refuse('STATE', 'BOUNDED_READ_REFUSED')
        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(fd, min(8192, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) > limit or len(data) != info.st_size:
            refuse('STATE', 'BOUNDED_READ_REFUSED')
        if identity(os.fstat(fd)) != identity(info):
            refuse('FILESYSTEM', 'STATE_CHANGED')
        self.records.append((fd, identity(info)))
        self.names.append((self.fd, name, fd))
        return bytes(data)

    def verify(self):
        for parent, name, fd in self.names:
            try:
                named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except OSError:
                refuse('FILESYSTEM', 'STATE_CHANGED')
            if identity(named) != identity(os.fstat(fd)):
                refuse('FILESYSTEM', 'STATE_CHANGED')
        for fd, original in self.records:
            if identity(os.fstat(fd)) != original:
                refuse('FILESYSTEM', 'STATE_CHANGED')
        # Recheck ACLs on trusted parent, private state and every held file.
        self._private(self.parent_fd, directory=True, parent=True)
        self._private(self.fd, directory=True)
        for parent, unused, fd in self.names:
            if parent == self.fd:
                self._private(fd)
        for name in self.absent:
            try:
                os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            refuse('FILESYSTEM', 'STATE_CHANGED')

    def close(self):
        for fd in reversed(self.fds):
            try:
                os.close(fd)
            except OSError:
                pass
        self.fds.clear()

    def __exit__(self, *unused):
        self.close()


def strict_json(raw):
    """Match the original bounded JSON grammar before snapshot semantics."""
    if not raw or len(raw) > 65536 or b'\0' in raw:
        refuse('SNAPSHOT', 'JSON_REFUSED')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                refuse('SNAPSHOT', 'JSON_REFUSED')
            result[key] = value
        return result

    def bad_number(unused):
        refuse('SNAPSHOT', 'JSON_REFUSED')

    try:
        value = json.loads(raw.decode('ascii'), object_pairs_hook=pairs,
                           parse_float=bad_number, parse_constant=bad_number)
    except (ValueError, UnicodeError, RecursionError):
        refuse('SNAPSHOT', 'JSON_REFUSED')
    count = 0

    def ascii_string(text, limit):
        return len(text) <= limit and all(0 < ord(c) < 128 for c in text)

    def walk(node, depth):
        nonlocal count
        count += 1
        if depth > 8 or count > 512:
            refuse('SNAPSHOT', 'JSON_REFUSED')
        if type(node) is dict:
            for key, child in node.items():
                if not ascii_string(key, 79):
                    refuse('SNAPSHOT', 'JSON_REFUSED')
                walk(child, depth + 1)
        elif type(node) is str:
            if not ascii_string(node, 255):
                refuse('SNAPSHOT', 'JSON_REFUSED')
        elif type(node) is int:
            if node < 0 or len(str(node)) > 20:
                refuse('SNAPSHOT', 'JSON_REFUSED')
        elif node is not None and type(node) is not bool:
            refuse('SNAPSHOT', 'JSON_REFUSED')
    walk(value, 0)
    return value


def decode_snapshot(raw):
    """Strict v2 shape; native value/guard contracts are finite predicates.

    Separating shape from contracts lets a changed guard be named without
    printing its value.  native_parse_contract below still enforces every
    condition in the original parse_snapshot, including Boolean identity.
    """
    s = strict_json(raw)
    if type(s) is not dict or s.keys() != SNAPSHOT_KEYS:
        refuse('SNAPSHOT', 'SCHEMA_REFUSED')
    if s['schema'] != 'ilinux31aj-native-snapshot-v2':
        refuse('SNAPSHOT', 'SCHEMA_REFUSED')
    if any(type(s[k]) is not bool for k in BOOL_FIELDS):
        refuse('SNAPSHOT', 'SCHEMA_REFUSED')
    string_keys = SNAPSHOT_KEYS - BOOL_FIELDS - {'original_semantics', 'lab_semantics'}
    if any(type(s[k]) is not str for k in string_keys):
        refuse('SNAPSHOT', 'SCHEMA_REFUSED')
    if (s['scope'] not in ('RECOVERY_GUARDED_READ', 'SYNTHETIC_CONTROL') or
            not SHA.fullmatch(s['profile_sha256']) or
            s['lab_ctrr'] not in ('enabled', 'disabled', 'unknown') or
            s['selected_payload'] not in ('31AF', 'CANDIDATE', 'BOOT021', 'NONE', 'UNKNOWN')):
        refuse('SNAPSHOT', 'SCHEMA_REFUSED')
    for name in ('comparison_key_id', 'lab_metadata_hmac', 'original_metadata_hmac'):
        if s['metadata_bound']:
            if not SHA.fullmatch(s[name]):
                refuse('SNAPSHOT', 'SCHEMA_REFUSED')
        elif s[name] != 'NONE':
            refuse('SNAPSHOT', 'SCHEMA_REFUSED')
    for name in ('original_semantics', 'lab_semantics'):
        values = s[name]
        if type(values) is not dict or values.keys() != SEMANTICS:
            refuse('SNAPSHOT', 'SCHEMA_REFUSED')
        for key, value in values.items():
            if key == 'sip0':
                if type(value) is not str or (value != 'ABSENT' and not SIP.fullmatch(value)):
                    refuse('SNAPSHOT', 'SCHEMA_REFUSED')
            elif type(value) is not bool and value != 'ABSENT':
                refuse('SNAPSHOT', 'SCHEMA_REFUSED')
    return s


def predicates(s, key_id, expected_scope):
    """Exact parse_snapshot and common validate_snapshot conditions."""
    p = {
        'scope_matches': s['scope'] == expected_scope,
        'profile_matches': hmac.compare_digest(s['profile_sha256'], PROFILE_SHA),
        'target_binding_recorded': s['target_binding_verified'],
        'lab_data_binding_recorded': s['lab_data_bound'],
        'paired_recovery_recorded': s['paired_1tr'],
        'original_full_recorded': s['original_security'] == 'Full',
        'original_ctrr_enabled_recorded': s['original_ctrr'] == 'enabled',
        'lab_permissive_recorded': s['lab_security'] == 'Permissive',
        'policy_schema_complete_recorded': s['policy_schema_complete'],
        'metadata_bound': s['metadata_bound'],
        'comparison_key_matches': hmac.compare_digest(s['comparison_key_id'], key_id),
        'original_smb_contract': all(s['original_semantics'][k] is not True for k in ('smb0', 'smb1')),
        'lab_smb_contract': all(s['lab_semantics'][k] is True for k in ('smb0', 'smb1')),
        'unclaimed_verification_contract': not any(s[k] for k in (
            'wrapper_authentication_verified', 'default_selection_verified',
            'restoration_verified', 'writes_authorized')),
        'read_only_recorded': s['read_only'],
        'payload_exactness_consistent': s['selected_payload_exact'] == (
            s['selected_payload'] not in ('NONE', 'UNKNOWN')),
    }
    parse_keys = set(p) - {'scope_matches', 'profile_matches', 'metadata_bound', 'comparison_key_matches'}
    p['native_parse_contract'] = all(p[k] for k in parse_keys)
    p['native_common_contract'] = all(p.values())
    return p


def compare_captures(baseline_raw, candidate_raw, key, restored_raw=None, synthetic=False):
    """No authentication of the original captures is invented here.

    Opaque role commitments are compared, never recomputed from unavailable
    policy values.  The SHA256 key identifier binds both captures to the own
    preserved comparison key; this is not a signature over snapshot files.
    """
    if len(key) != 32:
        refuse('STATE', 'KEY_SIZE_REFUSED')
    scope = 'SYNTHETIC_CONTROL' if synthetic else 'RECOVERY_GUARDED_READ'
    key_id = hashlib.sha256(key).hexdigest()
    baseline = decode_snapshot(baseline_raw)
    candidate = decode_snapshot(candidate_raw)
    bp = predicates(baseline, key_id, scope)
    bp['initial_payload_exact'] = baseline['selected_payload_exact'] and baseline['selected_payload'] == '31AF'
    baseline_valid = bp['native_common_contract'] and bp['initial_payload_exact']

    def phase(s, name):
        p = predicates(s, key_id, scope)
        p.update({
            'baseline_initial_contract': baseline_valid,
            'original_semantics_preserved': s['original_semantics'] == baseline['original_semantics'],
            'lab_semantics_preserved': s['lab_semantics'] == baseline['lab_semantics'],
            'original_private_commitment_equal': hmac.compare_digest(s['original_metadata_hmac'], baseline['original_metadata_hmac']),
            'lab_private_commitment_equal': hmac.compare_digest(s['lab_metadata_hmac'], baseline['lab_metadata_hmac']),
            'selected_payload_exact': s['selected_payload_exact'],
            'selected_payload_matches_phase': s['selected_payload'] == ('CANDIDATE' if name == 'candidate' else 'BOOT021'),
            'lab_ctrr_matches_phase': s['lab_ctrr'] == ('enabled' if name == 'candidate' else 'disabled'),
        })
        return p

    cp = phase(candidate, 'candidate')
    result = {
        'baseline': bp,
        'baseline_initial_contract': baseline_valid,
        'candidate': cp,
        'candidate_phase_contract': all(cp.values()),
        # These are informational classes, deliberately outside cp's contract
        # conjunction: their False values must not reject a valid candidate.
        'candidate_classification': {
            'selected_payload_none_recorded': candidate['selected_payload'] == 'NONE',
            'selected_payload_unknown_recorded': candidate['selected_payload'] == 'UNKNOWN',
            'lab_ctrr_disabled_recorded': candidate['lab_ctrr'] == 'disabled',
            'lab_ctrr_unknown_recorded': candidate['lab_ctrr'] == 'unknown',
        },
        'restored_capture_present': restored_raw is not None,
    }
    if restored_raw is not None:
        rp = phase(decode_snapshot(restored_raw), 'restored')
        result['restored'] = rp
        result['restored_phase_contract'] = all(rp.values())
    return result


def observe(path, synthetic=False, acl_check=no_extended_acl):
    """Read a fixed known state set only; retain all captures and spent markers."""
    owner = os.geteuid()
    if not synthetic and (owner != 0 or sys.platform != 'darwin' or path != LIVE_STATE):
        refuse('ADMISSION', 'ROOT_FIXED_PATH_REQUIRED')
    if synthetic:
        # Pure lexical containment plus no-follow component walk.  No resolve()
        # follows a supplied symlink or opens data outside the fixture root.
        prefix = str(FIXTURE_ROOT) + '/'
        if not path.startswith(prefix) or path == str(FIXTURE_ROOT):
            refuse('ADMISSION', 'WORKSPACE_FIXTURE_REQUIRED')
    with HeldState(path, owner, acl_check) as state:
        lock = state.read('session.lock', 0)
        if lock != b'':
            refuse('STATE', 'LOCK_FORMAT_REFUSED')
        lock_fd = state.fds[-1]
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError:
            refuse('STATE', 'TRANSACTION_BUSY')
        if state.read('enrolled', 9) != b'ENROLLED\n':
            refuse('STATE', 'ENROLLMENT_REFUSED')
        profile = state.read('profile.json', PROFILE_BYTES)
        if len(profile) != PROFILE_BYTES or not hmac.compare_digest(hashlib.sha256(profile).hexdigest(), PROFILE_SHA):
            refuse('STATE', 'PROFILE_PIN_REFUSED')
        key = state.read('comparison.key', 32)
        target = state.read('target.hmac', 64)
        if not SHA.fullmatch(target.decode('ascii', errors='replace')):
            refuse('STATE', 'TARGET_COMMITMENT_FORMAT_REFUSED')
        if state.read('candidate-attempt', 6) != b'SPENT\n':
            refuse('STATE', 'ATTEMPT_MARKER_REFUSED')
        if state.read('candidate-exit', 8) != b'0\n':
            refuse('STATE', 'CANDIDATE_WRITER_NOT_ZERO')
        baseline = state.read('baseline.json', 65536)
        candidate = state.read('candidate.json', 65536)
        restored = state.read('restored.json', 65536, optional=True)
        result = compare_captures(baseline, candidate, key, restored, synthetic)
        state.verify()
    return {
        **envelope(), 'status': 'OBSERVED', 'synthetic': synthetic,
        'preserved_profile_pin_matches': True,
        'enrollment_marker_valid': True,
        'candidate_attempt_spent': True,
        'candidate_writer_zero_recorded': True,
        'target_commitment_format_valid': True,
        'target_commitment_revalidated': False,
        **result,
    }


def envelope():
    return {
        'schema': SCHEMA, 'scope': 'PRESERVED_TRANSACTION_CAPTURES_ONLY',
        'read_only': True, 'settings_changed': False, 'native_ready': False,
        'current_policy_verified': False, 'current_boot_object_verified': False,
        'firmware_acceptance_verified': False, 'rollback_verified': False,
        'private_values_returned': False, 'identifiers_returned': False,
        'state_reset': False,
    }


def main(argv=None):
    class FiniteParser(argparse.ArgumentParser):
        def error(self, unused):
            refuse('ARGUMENTS', 'OPTIONS_REFUSED')
    parser = FiniteParser(description='Read preserved transaction predicates only; default is inert.')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true', help='Read fixed preserved lab state with local root authentication; no live policy query.')
    mode.add_argument('--fixture', metavar='DIRECTORY', help='Synthetic state directory beneath this checkout/build only.')
    try:
        args = parser.parse_args(argv)
    except Refused as failure:
        print(json.dumps({**envelope(), 'status': 'REFUSED',
                          'failed_stage': failure.stage, 'failure_reason': failure.reason},
                         sort_keys=True, separators=(',', ':')))
        return 1
    if not args.live and args.fixture is None:
        print(json.dumps({**envelope(), 'status': 'INERT'}, sort_keys=True))
        return 0
    try:
        result = observe(args.fixture if args.fixture is not None else LIVE_STATE,
                         synthetic=args.fixture is not None)
    except Refused as failure:
        result = {**envelope(), 'status': 'REFUSED',
                  'failed_stage': failure.stage, 'failure_reason': failure.reason}
    except Exception:
        result = {**envelope(), 'status': 'REFUSED',
                  'failed_stage': 'OBSERVATION', 'failure_reason': 'READ_UNAVAILABLE'}
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0 if result['status'] == 'OBSERVED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
