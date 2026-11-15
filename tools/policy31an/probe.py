#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only policy-schema observation; returns no policy values or identifiers.

Default/help is inert. --live is a bounded current-macOS observation, not
Recovery admission. --fixture accepts only synthetic workspace fixtures.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = 'tools/recovery31am/package.py'
BASE_SHA = '1ff1528a1ec2c6913a84e4dc21da7d82cc0d065236ba696db713afa1baaa6a57'
CAPTURE = 'tools/boot-object31aj-native/schema_probe.py'
CAPTURE_SHA = '1aa2684506131f8e73d024e5c1a271699a4c782b5034aeb6a7a5c3eedfe6d7d0'
AUTH = frozenset(('auxp', 'auxi', 'auxr', 'prot', 'hrlp', 'losv'))
# lobo/love are published by Asahi's boot-policy documentation. They are
# observations only: the frozen native parser still does not accept them.
EXTRA = frozenset(('lobo', 'love'))
SUPPORTED = frozenset(('smb0', 'smb1', 'smb2', 'smb3', 'smb4', 'sip0', 'sip1',
    'sip2', 'sip3', 'coih', 'nsih', 'rpnh', 'ronh', 'spih', 'stng',
    'lpnh', 'vuid', 'kuid', 'BORD', 'CHIP', 'ECID'))
LIMIT = 65536


def require(value):
    if not value:
        raise ValueError('metadata observation refused')


def read_bounded(root, name, limit):
    """No-follow, same-descriptor read before compiling any local dependency."""
    path = Path(name)
    if path.is_absolute():
        path = path.relative_to(root)
    require(path.parts and '..' not in path.parts and '.' not in path.parts)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for i, part in enumerate(path.parts):
            child = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                            (os.O_DIRECTORY if i < len(path.parts) - 1 else 0), dir_fd=fd)
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
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(len(data) == before.st_size and
                all(getattr(before, k) == getattr(after, k) for k in fields))
        return bytes(data)
    finally:
        os.close(fd)


def pinned_module(root, name, digest):
    data = read_bounded(root, name, LIMIT)
    require(hashlib.sha256(data).hexdigest() == digest)
    module = types.ModuleType('policy31an_verified_dependency')
    module.__file__ = str(root / name)
    exec(compile(data, module.__file__, 'exec'), module.__dict__)
    return module


def value_class(value):
    if not value:
        return 'EMPTY'
    if value.lower() == b'absent':
        return 'ABSENT'
    if value.lower() in (b'0', b'1', b'true', b'false'):
        return 'BOOLEAN'
    if re.fullmatch(rb'[0-9]+', value):
        return 'DECIMAL'
    if re.fullmatch(rb'(?:0x)?[0-9a-fA-F]{16,}', value):
        return 'HEXLIKE'
    return 'OPAQUE'


def summarize(raw):
    require(type(raw) is bytes and 0 < len(raw) <= LIMIT and b'\0' not in raw)
    result = {'known_relevant_fields': {}, 'supported_tag_rows': 0,
              'other_unknown_tag_rows': 0, 'malformed_tag_rows': 0,
              'unsupported_counts': {'PROTECTED_AUX_PRESENT': 0,
                                    'PUBLISHED_EXTRA_TAG': 0, 'OTHER_TAG': 0},
              'first_unsupported_candidate': None}
    for line in raw.split(b'\n'):
        require(len(line) <= 2048)
        # Match the frozen C parser: first '(' and following ')', then ':'.
        start = line.find(b'(')
        end = line.find(b')', start + 1) if start >= 0 else -1
        if start < 0 or end < 0:
            continue
        after = line[end + 1:].strip()
        if not after.startswith(b':'):
            continue
        tags = line[start + 1:end]
        if not 0 < len(tags) < 128 or not re.fullmatch(
                rb'\s*[A-Za-z0-9]{4}\s*(?:,\s*[A-Za-z0-9]{4}\s*){0,3}', tags):
            result['malformed_tag_rows'] += 1
            continue
        value = after[1:].strip()
        kind = value_class(value)
        for item in tags.split(b','):
            tag = item.strip().decode('ascii')
            category = None
            if tag in AUTH | EXTRA:
                row = result['known_relevant_fields'].setdefault(tag,
                    {'rows': 0, 'presence_classes': [], 'syntax_classes': []})
                row['rows'] += 1
                presence = 'EMPTY' if not value else 'ABSENT' if kind == 'ABSENT' else 'PRESENT'
                if presence not in row['presence_classes']:
                    row['presence_classes'].append(presence)
                if kind not in row['syntax_classes']:
                    row['syntax_classes'].append(kind)
                if tag in EXTRA:
                    category = 'PUBLISHED_EXTRA_TAG'
                elif kind != 'ABSENT':
                    category = 'PROTECTED_AUX_PRESENT'
            elif tag in SUPPORTED:
                result['supported_tag_rows'] += 1
            else:
                result['other_unknown_tag_rows'] += 1
                category = 'OTHER_TAG'
            if category:
                result['unsupported_counts'][category] += 1
                if result['first_unsupported_candidate'] is None:
                    result['first_unsupported_candidate'] = {
                        'class': category, 'tag': tag if tag in AUTH | EXTRA else 'OTHER_TAG'}
    result['unseen_relevant_fields'] = sorted((AUTH | EXTRA) - set(result['known_relevant_fields']))
    result['classification_scope'] = 'METADATA_ONLY_NOT_NATIVE_PARSER_ADMISSION'
    result['unknown_tag_names_returned'] = False
    return result


def public_report(scope, roles=None, failed_stage=None):
    return {'schema': 'ilinux31an-policy-schema-observation-v1', 'scope': scope,
            'metadata_obtained': failed_stage is None and roles is not None and all(
                v.get('metadata') is not None for v in roles.values()) and len(roles) == 2,
            'roles': roles or {}, 'failed_stage': failed_stage, 'read_only': True,
            'policy_values_returned': False, 'identifiers_returned': False,
            'unknown_tag_names_returned': False, 'settings_changed': False,
            'parser_acceptance_changed': False, 'admission_verified': False,
            'native_ready': False, 'target_consistency_rechecked': False}


def load_runtime(root):
    package = pinned_module(root, BASE, BASE_SHA)
    _, records, _, server = package.admitted(root)
    require(records[CAPTURE] == CAPTURE_SHA)
    capture = pinned_module(root, CAPTURE, CAPTURE_SHA)
    stager = package.frozen_stager(root)
    _, _, guard, _, _ = stager.checked_sources(root, root / stager.INVENTORY)
    return stager, guard, capture


def json_shape(raw):
    require(type(raw) is bytes and 0 < len(raw) <= LIMIT and b'\0' not in raw)
    depth = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            require(depth <= 16)
        elif byte in (93, 125):
            depth -= 1
            require(depth >= 0)
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value)
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    kind = lambda v: ('OBJECT' if type(v) is dict else 'ARRAY' if type(v) is list
        else 'BOOLEAN' if type(v) is bool else 'NULL' if v is None
        else 'NUMBER' if type(v) in (int, float) else 'STRING')
    result = {'root_kind': kind(value), 'known_key_shapes': {},
              'other_key_count': 0, 'node_count': 0, 'max_depth': 0}
    def visit(item, level):
        result['node_count'] += 1
        require(result['node_count'] <= 2048 and level <= 16)
        result['max_depth'] = max(result['max_depth'], level)
        if type(item) is dict:
            for key, child in item.items():
                if key in AUTH | EXTRA | SUPPORTED:
                    shape = {'kind': kind(child),
                             'array_items': len(child) if type(child) is list else None}
                    shapes = result['known_key_shapes'].setdefault(key, [])
                    if shape not in shapes:
                        shapes.append(shape)
                else:
                    result['other_key_count'] += 1
                visit(child, level + 1)
        elif type(item) is list:
            for child in item:
                visit(child, level + 1)
    visit(value, 0)
    result['unknown_key_names_returned'] = False
    result['values_returned'] = False
    return result


def capture_policy(capture, group, json_output=False):
    argv = ['/usr/bin/bputil', '-d', '-v', group] + (['-j'] if json_output else [])
    try:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0,
            env={'PATH': '/usr/bin:/usr/sbin:/bin:/sbin', 'LANG': 'C', 'LC_ALL': 'C'})
        raw, diagnostic = capture.collect_process(child)
        return (None if diagnostic['failure_reason'] else raw), diagnostic
    except OSError:
        return None, {'failure_kind': 'READ', 'failure_reason': 'BPUTIL_EXEC_FAILURE',
                      'bputil_exit': None, 'stdout_bytes': 0}


def run_live(root=ROOT):
    root = Path(root).resolve()
    require(sys.platform == 'darwin' and os.geteuid() == 0)
    stager, guard, capture = load_runtime(root)
    backend = stager.LiveBackend()
    observed = backend.observe(guard)
    binding = stager.guard_metadata(observed, guard)
    groups = (('LAB', guard.uuid(observed['lab']['APFSVolumeGroupID'])),
              ('ORIGINAL', guard.uuid(observed['original']['APFSVolumeGroupID'])))
    roles = {}
    for role, group in groups:
        raw, diagnostic = capture_policy(capture, group)
        if diagnostic['failure_reason'] == 'BPUTIL_INTERRUPTED':
            roles[role] = {'capture': diagnostic, 'metadata': None}
            return public_report('MACOS_READ_ONLY_SCHEMA_OBSERVATION', roles,
                                 role + '_POLICY_INTERRUPTED')
        try:
            summary = summarize(raw)
        except (ValueError, UnicodeError):
            summary = None
        roles[role] = {'capture': diagnostic, 'metadata': summary}
        raw_json, json_diagnostic = capture_policy(capture, group, True)
        try:
            shape = json_shape(raw_json)
        except (ValueError, UnicodeError, RecursionError):
            shape = None
        roles[role]['json'] = {'capture': json_diagnostic, 'shape': shape}
        if json_diagnostic['failure_reason'] == 'BPUTIL_INTERRUPTED':
            return public_report('MACOS_READ_ONLY_SCHEMA_OBSERVATION', roles,
                                 role + '_JSON_INTERRUPTED')
    # Target consistency is rechecked without returning the private binding.
    require(stager.guard_metadata(backend.observe(guard), guard) == binding)
    report = public_report('MACOS_READ_ONLY_SCHEMA_OBSERVATION', roles)
    report['target_consistency_rechecked'] = True
    return report


def fixture(path, root=ROOT):
    root = Path(root).resolve()
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    require(root / 'build' in path.parents)
    value = json.loads(read_bounded(root, path, 256 * 1024))
    require(type(value) is dict and set(value) == {'schema', 'roles'} and
            value['schema'] == 'ilinux31an-synthetic-policy-fixture-v1' and
            type(value['roles']) is dict and set(value['roles']) == {'LAB', 'ORIGINAL'})
    roles = {}
    for role, text in value['roles'].items():
        require(type(text) is str)
        roles[role] = {'capture': None, 'metadata': summarize(text.encode('utf8'))}
    return public_report('SYNTHETIC_CONTROL', roles)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('arguments refused')


def main(argv=None):
    parser = Parser(prog='policy31an-probe', description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--live', action='store_true')
    modes.add_argument('--fixture', type=Path)
    try:
        args = parser.parse_args(argv)
        if not args.live and args.fixture is None:
            parser.print_help()
            return 0
        report = run_live() if args.live else fixture(args.fixture)
    except (Exception, KeyboardInterrupt):
        report = public_report('SCHEMA_OBSERVATION_REFUSED', failed_stage='GUARD_OR_FORMAT')
    print(json.dumps(report, sort_keys=True))
    return 0 if report['metadata_obtained'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
