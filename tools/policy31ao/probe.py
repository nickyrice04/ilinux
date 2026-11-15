#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only desktop schema and real-C syntax check; no Recovery admission."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = 'tools/policy31an/probe.py'
BASE_SHA = '6914dbcf33ec3017efa559b20f6692f6e8569311a07b23d4a5cfc61c3856bccd'
SCANNER = 'tools/policy31ao/schema.py'
SCANNER_SHA = '5c44174da9d0965cb52340c5ffd42aa4fb37bb2db973617c0634b78b1aae6213'
ACL_GUARD = 'tools/policy31ao/acl_guard.py'
ACL_GUARD_SHA = '7b6782490dcda002006ef3b966280fa488422d7d6d17ee3c55a2684ee6da60f1'
NATIVE = 'build/policy31ao/desktop-v2/desktop-parser'
NATIVE_SHA = 'b6fbafe3c863416a1d2f442f00fa33753d50089830e6822e86a04657f826cc44'
LIMIT = 65536


def require(value):
    if not value:
        raise ValueError('observation refused')


def read_bounded(root, name, limit):
    path = Path(name)
    require(not path.is_absolute() and path.parts and '..' not in path.parts)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for i, part in enumerate(path.parts):
            child = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                            (os.O_DIRECTORY if i + 1 < len(path.parts) else 0), dir_fd=fd)
            os.close(fd)
            fd = child
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit)
        data = bytearray()
        while len(data) <= limit:
            piece = os.read(fd, min(16384, limit + 1 - len(data)))
            if not piece:
                break
            data.extend(piece)
        after = os.fstat(fd)
        require(len(data) == before.st_size and all(getattr(before, k) == getattr(after, k)
                for k in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')))
        return bytes(data)
    finally:
        os.close(fd)


def module(root, name, digest):
    blob = read_bounded(root, name, LIMIT)
    require(hashlib.sha256(blob).hexdigest() == digest)
    value = types.ModuleType('verified31ao_dependency')
    value.__file__ = str(root / name)
    exec(compile(blob, value.__file__, 'exec'), value.__dict__)
    return value


def check_native(root):
    data = read_bounded(root, NATIVE, 1024 * 1024)
    require(len(NATIVE_SHA) == 64 and hashlib.sha256(data).hexdigest() == NATIVE_SHA)
    return data


@contextlib.contextmanager
def parser_process(root):
    """Execute a verified private copy from a held directory, not its source path.

    macOS refuses descriptor-path Mach-O execution. A new mode0700 directory
    owned by this process's effective user, and a mode0500 exclusive file,
    instead bind execution to the verified bytes. fchdir pins the directory
    vnode even if a writable ancestor is renamed. Only original executable
    bytes enter scratch; no policy data, keys or diagnostics are written.
    """
    acl_guard = module(root, ACL_GUARD, ACL_GUARD_SHA)
    data = check_native(root)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    parent_fd = directory_fd = cwd_fd = -1
    name = 'policy31ao-exec-' + os.urandom(16).hex()
    process = None
    created = file_created = False
    identity = file_identity = None
    try:
        parent_fd = os.open('build', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        created = True
        directory_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        identity = os.fstat(directory_fd)
        require(identity.st_uid == os.geteuid() and stat.S_IMODE(identity.st_mode) == 0o700)
        require(acl_guard.no_extended_acl(directory_fd))
        fd = os.open('desktop-parser', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o500, dir_fd=directory_fd)
        file_created = True
        try:
            file_identity = os.fstat(fd)
            require(acl_guard.no_extended_acl(fd))
            offset = 0
            while offset < len(data):
                count = os.write(fd, data[offset:])
                require(count > 0)
                offset += count
            os.fsync(fd)
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and
                    info.st_nlink == 1 and info.st_size == len(data) and
                    stat.S_IMODE(info.st_mode) == 0o500)
        finally:
            os.close(fd)
        cwd_fd = os.open('.', os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fchdir(directory_fd)
            process = subprocess.Popen(['./desktop-parser', '--stdin'], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={'PATH': '/usr/bin:/usr/sbin:/bin:/sbin', 'LANG': 'C', 'LC_ALL': 'C'})
        finally:
            os.fchdir(cwd_fd)
            os.close(cwd_fd)
            cwd_fd = -1
        yield process
    finally:
        try:
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate()
            if file_created and directory_fd >= 0:
                current_file = os.stat('desktop-parser', dir_fd=directory_fd, follow_symlinks=False)
                require(file_identity is not None and
                        (current_file.st_dev, current_file.st_ino) ==
                        (file_identity.st_dev, file_identity.st_ino) and
                        stat.S_ISREG(current_file.st_mode))
                os.unlink('desktop-parser', dir_fd=directory_fd)
            if created and parent_fd >= 0:
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                require(identity is not None and (current.st_dev, current.st_ino) ==
                        (identity.st_dev, identity.st_ino))
                os.rmdir(name, dir_fd=parent_fd)
        finally:
            for fd in (cwd_fd, directory_fd, parent_fd, root_fd):
                if fd >= 0:
                    os.close(fd)


def unique_pairs(items):
    value = {}
    for key, item in items:
        require(key not in value)
        value[key] = item
    return value


def native_parse(root, raw):
    """Private stdin only; trusted original binary contains no host collector."""
    require(type(raw) is bytes and 0 < len(raw) <= LIMIT)
    with parser_process(root) as child:
        try:
            output, error = child.communicate(input=raw, timeout=5)
        except BaseException:
            child.kill()
            child.communicate()
            raise
        require(child.returncode == 0 and not error and len(output) <= 2048)
    value = json.loads(output, object_pairs_hook=unique_pairs)
    flags = {'read_only': True, 'admission_verified': False, 'native_ready': False,
             'policy_values_returned': False, 'identifiers_returned': False}
    booleans = ('input_within_bounds', 'old_parser_accepted', 'proposed_parser_accepted')
    lines = ('old_failure_line', 'proposed_failure_line')
    require(type(value) is dict and set(value) == set(flags) | set(booleans) | set(lines) | {'schema', 'scope'})
    require(value['schema'] == 'ilinux31ao-native-policy-parse-v1' and
            value['scope'] == 'DESKTOP_SYNTAX_ONLY')
    require(all(type(value[k]) is bool and value[k] is v for k, v in flags.items()))
    require(all(type(value[k]) is bool for k in booleans))
    require(all(type(value[k]) is int and 0 <= value[k] <= 10000 for k in lines))
    return value


def compact_shape(value):
    """Zero predicate/count entries are implicit; every observed field remains."""
    value = dict(value)
    if 'fields' in value:
        fields = value['fields']
        count_key = 'rows' if not fields or 'rows' in next(iter(fields.values())) else 'key_occurrences'
        value['unseen_catalog_fields'] = [k for k, v in fields.items() if not v[count_key]]
        value['fields'] = {k: {a: ({b: n for b, n in v.items() if n} if type(v) is dict else v)
                               for a, v in row.items()}
                           for k, row in fields.items() if row[count_key]}
    for name in ('malformed_reasons', 'group_sizes'):
        if name in value:
            value[name] = {k: v for k, v in value[name].items() if v}
    if 'expressions' in value:
        value['expressions'] = {k: {a: ({b: n for b, n in v.items() if n} if type(v) is dict else v)
                                    for a, v in row.items()}
                                for k, row in value['expressions'].items() if row['rows']}
    return value


def report(roles=None, failed_stage=None):
    roles = roles or {}
    return {'schema': 'ilinux31ao-desktop-policy-observation-v1',
            'scope': 'MACOS_DESKTOP_READ_ONLY_SYNTAX', 'roles': roles,
            'metadata_obtained': failed_stage is None and set(roles) == {'LAB', 'ORIGINAL'} and
                all(row.get('text') is not None for row in roles.values()),
            'both_proposed_parsers_accepted': set(roles) == {'LAB', 'ORIGINAL'} and
                all((row.get('native_syntax') or {}).get('proposed_parser_accepted') is True
                    for row in roles.values()),
            'failed_stage': failed_stage, 'target_consistency_rechecked': False,
            'read_only': True, 'settings_changed': False, 'native_ready': False,
            'admission_verified': False, 'policy_values_returned': False,
            'identifiers_returned': False, 'unknown_names_returned': False,
            'workspace_scratch_kind': 'VERIFIED_ORIGINAL_EXECUTABLE_ONLY_NO_POLICY_DATA',
            'Recovery_parser_installed': False}


def run_live(root=ROOT):
    root = Path(root).resolve()
    require(sys.platform == 'darwin' and os.geteuid() == 0)
    base = module(root, BASE, BASE_SHA)
    scanner = module(root, SCANNER, SCANNER_SHA)
    check_native(root)
    stager, guard, capture = base.load_runtime(root)
    backend = stager.LiveBackend()
    observed = backend.observe(guard)
    binding = stager.guard_metadata(observed, guard)
    roles = {}
    for role, group in (('LAB', guard.uuid(observed['lab']['APFSVolumeGroupID'])),
                        ('ORIGINAL', guard.uuid(observed['original']['APFSVolumeGroupID']))):
        raw, diagnostic = base.capture_policy(capture, group)
        row = {'capture': diagnostic, 'text': None, 'native_syntax': None,
               'native_failure': None, 'json': None}
        roles[role] = row
        if diagnostic['failure_reason'] == 'BPUTIL_INTERRUPTED':
            return report(roles, role + '_TEXT_INTERRUPTED')
        if raw is not None:
            row['text'] = compact_shape(scanner.scan_text(raw))
            try:
                row['native_syntax'] = native_parse(root, raw)
            except KeyboardInterrupt:
                return report(roles, role + '_NATIVE_INTERRUPTED')
            except Exception:
                row['native_failure'] = 'DESKTOP_PARSER_CHECK_FAILED'
        raw_json, json_capture = base.capture_policy(capture, group, True)
        row['json'] = {'capture': json_capture,
                       'shape': compact_shape(scanner.scan_json(raw_json)) if raw_json is not None else None}
        if json_capture['failure_reason'] == 'BPUTIL_INTERRUPTED':
            return report(roles, role + '_JSON_INTERRUPTED')
    require(stager.guard_metadata(backend.observe(guard), guard) == binding)
    check_native(root)
    value = report(roles)
    value['target_consistency_rechecked'] = True
    return value


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = Parser(prog='policy31ao-probe', description=__doc__)
    parser.add_argument('--live', action='store_true')
    try:
        args = parser.parse_args(argv)
        if not args.live:
            parser.print_help()
            return 0
        value = run_live()
    except (Exception, KeyboardInterrupt):
        value = report(failed_stage='GUARD_OR_RUNTIME')
    print(json.dumps(value, sort_keys=True))
    return 0 if value['metadata_obtained'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
