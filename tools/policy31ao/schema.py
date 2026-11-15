#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original, bounded policy-output shape observation; no native admission.

This module never starts a process, reads a file, or emits input strings.  A
catalog match establishes only a public spelling, not an allowed policy value.
Case is significant.  The predicate counts deliberately overlap.
"""
import json
import re


LIMIT = 65536
LINE_LIMIT = 2048
GROUP_LIMIT = 32
DEPTH_LIMIT = 16
NODE_LIMIT = 2048
SOURCES = {
    'ASAHI': 'https://github.com/AsahiLinux/docs/blob/'
        'ae823b273477073a5419050ba826ac9be22e246a/docs/fw/boot.md',
    'APPLE_IMAGE4': 'https://github.com/apple-oss-distributions/xnu/blob/'
        'f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/EXTERNAL_HEADERS/img4/runtime.h',
    'APPLE_LOCALPOLICY': 'https://support.apple.com/en-gb/guide/security/secc745a0845/web',
}
# Source-qualified spellings only.  Generic Image4 identifiers are diagnostic
# candidates, not proof that bputil displays them, or that a LocalPolicy has them.
_ASAHI = ('vuid kuid lpnh rpnh ronh nsih coih auxp auxi auxr prot hrlp '
          'lobo love smb0 smb1 smb2 smb3 smb4 sip0 sip1 sip2 sip3').split()
_APPLE_LOCAL = ('losv spih stng BORD CHIP ECID').split()
_APPLE_IMAGE4 = ('CEPO BORD CHIP SDOM ECID CPRO CSEC EPRO ESEC IUOU RSCH CHMH '
                 'AMNM EUOU LOVE ESDM FPGT UDID FCHP TYPE STYP CLAS SPIH NSPH '
                 'STNG VUID').split()
# Qualified bputil formatter spelling from the companion static investigation:
# its JSON key is CRPO, whereas its text key is CPRO.  Keep them distinct and
# never use this spelling discrepancy to alias policy identities or values.
_FORMATTER_ONLY = ('CRPO', 'smb5')
CATALOG = tuple(sorted(set(_ASAHI + _APPLE_LOCAL + _APPLE_IMAGE4 + list(_FORMATTER_ONLY))))
CATALOG_SET = frozenset(CATALOG)
# Neither public documents nor this executable claim to enumerate all possible
# Image4 metadata.  The separate formatter flag has a narrower, pinned scope.
CATALOG_COMPLETE = False
FORMATTER_TEXT_CATALOG = tuple(sorted(('BORD CEPO CHIP CPRO CSEC ECID SDOM '
    'auxi auxp auxr coih kuid lobo love lpnh nsih ronh rpnh sip0 sip1 sip2 sip3 '
    'smb0 smb1 smb2 smb3 smb4 spih stng vuid').split()))
FORMATTER_JSON_ONLY = ('CRPO', 'smb5')
FORMATTER_CATALOG_QUALIFIED = True
FORMATTER_PROVENANCE = {
    'artifact': 'bputil',
    'bytes': 196320,
    'sha256': 'dcd2d73fbeb18d6ce3092605c151790d4a01ac9caeeb99fa23a4098e9559f545',
    'architecture': 'arm64e',
    'main_start': '0x100002da0',
    'main_end_inclusive': '0x100005373',
    'body_bytes': 9684,
    'body_sha256': '35f37c14dcc91ef5eeeb10532120f0bf278957c8b4d5efca2c92c509b0d59c7e',
    'instruction_count': 2421,
    'evidence': 'REA_GHIDRA_12_1_4_AND_LLVM_EXACT_PC_COVERAGE',
    'qualification': 'FORMATTER_BEHAVIOR_ONLY_NOT_POLICY_ADMISSION',
}
PREDICATES = ('boolean', 'uint32', 'uint64decimal', 'uint64hex',
              'uint64barehex', 'uint32barehex', 'hash96',
              'uuid128', 'printable_ascii', 'version_printable',
              'version_dotted', 'version_build', 'version_vector6',
              'version_vector6_uint32')
PRESENCE = ('ABSENT', 'EMPTY', 'PRESENT')
TEXT_REASONS = ('INPUT_TYPE', 'INPUT_BOUND', 'UTF8', 'NUL', 'LINE_BOUND',
                'MISSING_CLOSE', 'MISSING_COLON', 'EMPTY_GROUP', 'GROUP_BOUND',
                'EMPTY_TAG', 'TAG_LENGTH', 'TAG_CHAR', 'NONASCII_TAG',
                'FIRST_PAREN_LABEL', 'NESTED_GROUP')
JSON_KINDS = ('OBJECT', 'ARRAY', 'BOOLEAN', 'NULL', 'NUMBER', 'STRING')
GROUP_BUCKETS = ('1', '2', '3', '4', '5_8', '9_16', '17_32')
EXPRESSIONS = ('SMB0_AND_SMB1',)


def _version_vector6(value, width=64):
    # The qualified formatter emits six unsigned components as D.D.D.D.D,D.
    # This is shape evidence, not proof of the meaning or valid range of each
    # version component.  No component value leaves this function.
    if re.fullmatch(rb'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+,[0-9]+', value) is None:
        return False
    return all(re.fullmatch(rb'(?:0|[1-9][0-9]*)', part) is not None
               and len(part) <= 20 and int(part) <= (1 << width) - 1
               for part in re.split(rb'[.,]', value))


def _counter(keys):
    return dict.fromkeys(keys, 0)


def _field():
    return {'rows': 0, 'presence': _counter(PRESENCE),
            'predicates': _counter(PREDICATES)}


def _base(kind):
    return {'schema': 'ilinux31ao-policy-' + kind + '-shape-v1',
            'classification_scope': 'OBSERVATION_ONLY_NOT_NATIVE_ADMISSION',
            'qualified': False, 'failure_stage': None, 'failure_reason': None,
            'values_returned': False, 'identifiers_returned': False,
            'unknown_names_returned': False, 'catalog_complete': CATALOG_COMPLETE,
            'formatter_catalog_qualified': FORMATTER_CATALOG_QUALIFIED}


def scalar_predicates(value):
    """Return overlapping syntax predicates only, never a parsed scalar.

    Decimal and hexadecimal integers are canonical unsigned spellings: no
    leading decimal zeroes.  uint64hex requires a 0x/0X prefix; the separate
    barehex predicates observe unsigned hexadecimal without that prefix and
    overlap with decimal (for example, 123).  uuid128 accepts either exactly
    32 hex digits or the standard hyphenated shape.
    Version predicates are observations, not a version-parser contract.
    """
    if type(value) is not bytes or len(value) > LINE_LIMIT:
        return dict.fromkeys(PREDICATES, False)
    value = value.strip(b' \t\r')
    lower = value.lower()
    decimal = re.fullmatch(rb'(?:0|[1-9][0-9]*)', value) is not None
    hexadecimal = re.fullmatch(rb'0[xX][0-9a-fA-F]+', value) is not None
    decimal64 = decimal and len(value) <= 20 and int(value) <= (1 << 64) - 1
    hex64 = hexadecimal and len(value) <= 18 and int(value, 16) <= (1 << 64) - 1
    barehex64 = 0 < len(value) <= 16 and re.fullmatch(rb'[0-9a-fA-F]+', value) is not None
    barehex32 = barehex64 and int(value, 16) <= (1 << 32) - 1
    uint32 = ((decimal64 and int(value) <= (1 << 32) - 1) or
              (hex64 and int(value, 16) <= (1 << 32) - 1))
    printable_ascii = bool(value) and len(value) <= 256 and all(32 <= c <= 126 for c in value)
    return {
        'boolean': lower in (b'0', b'1', b'true', b'false'),
        'uint32': uint32,
        'uint64decimal': decimal64,
        'uint64hex': hex64,
        'uint64barehex': barehex64,
        'uint32barehex': barehex32,
        'hash96': re.fullmatch(rb'[0-9a-fA-F]{96}', value) is not None,
        'uuid128': re.fullmatch(rb'(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-'
                     rb'[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
                     rb'[0-9a-fA-F]{12})', value) is not None,
        'printable_ascii': printable_ascii,
        'version_printable': printable_ascii and re.fullmatch(
            rb'[0-9][0-9A-Za-z ._+()\-]*', value) is not None,
        'version_dotted': re.fullmatch(rb'[0-9]+(?:\.[0-9]+){1,4}', value) is not None,
        'version_build': re.fullmatch(rb'[0-9]+[A-Za-z][0-9]+[A-Za-z]?', value) is not None,
        'version_vector6': _version_vector6(value),
        'version_vector6_uint32': _version_vector6(value, 32),
    }


def _group(raw):
    if not raw.strip():
        return None, 'EMPTY_GROUP'
    if b'(' in raw or b')' in raw:
        return None, 'NESTED_GROUP'
    pieces = raw.split(b',')
    if len(pieces) > GROUP_LIMIT:
        return None, 'GROUP_BOUND'
    result = []
    for piece in pieces:
        piece = piece.strip(b' \t\r')
        if not piece:
            return None, 'EMPTY_TAG'
        if any(c > 127 for c in piece):
            return None, 'NONASCII_TAG'
        if len(piece) != 4:
            return None, 'TAG_LENGTH'
        if re.fullmatch(rb'[A-Za-z0-9]{4}', piece) is None:
            return None, 'TAG_CHAR'
        result.append(piece.decode('ascii'))
    return result, None


def _later_row_group(line, first_end):
    """Recognize a later terminal group only to name first-label obstruction.

    Do not attribute later tags or values to any catalog entry.  This prevents
    the observer from silently treating a different row grammar as native-safe.
    """
    cursor = first_end + 1
    for _ in range(8):
        start = line.find(b'(', cursor)
        if start < 0:
            return False
        end = line.find(b')', start + 1)
        if end < 0:
            return False
        tags, reason = _group(line[start + 1:end])
        if reason is None and tags and line[end + 1:].lstrip(b' \t\r').startswith(b':'):
            return True
        cursor = end + 1
    return False


def scan_text(raw):
    """Observe all catalog fields and bounded row/group shapes in one stream."""
    result = _base('text')
    result.update({'fields': {tag: _field() for tag in CATALOG},
                   'expressions': {name: _field() for name in EXPRESSIONS},
                   'non_tag_expression_rows': 0,
                   'tagged_rows': 0, 'untagged_lines': 0,
                   'known_tag_occurrences': 0, 'unknown_tag_occurrences': 0,
                   'unknown_tag_rows': 0, 'malformed_rows': 0,
                   'malformed_reasons': _counter(TEXT_REASONS),
                   'group_sizes': _counter(GROUP_BUCKETS),
                   'native4_compatible_rows': 0, 'native4_incompatible_rows': 0,
                   'duplicate_tag_rows': 0, 'native_first_paren_compatible': True})
    def fail(reason):
        result['failure_stage'] = 'TEXT'
        result['failure_reason'] = reason
        result['malformed_reasons'][reason] += 1
        return result
    if type(raw) is not bytes:
        return fail('INPUT_TYPE')
    if not 0 < len(raw) <= LIMIT:
        return fail('INPUT_BOUND')
    try:
        raw.decode('utf-8', 'strict')
    except UnicodeError:
        return fail('UTF8')
    if b'\0' in raw:
        return fail('NUL')
    if any(len(line) > LINE_LIMIT for line in raw.split(b'\n')):
        return fail('LINE_BOUND')
    for line in raw.split(b'\n'):
        if not line.strip():
            continue
        start = line.find(b'(')
        if start < 0:
            result['untagged_lines'] += 1
            continue
        end = line.find(b')', start + 1)
        reason = None
        tags = None
        expression = None
        if end < 0:
            reason = 'MISSING_CLOSE'
        else:
            after = line[end + 1:].lstrip(b' \t\r')
            if not after.startswith(b':'):
                reason = ('FIRST_PAREN_LABEL' if _later_row_group(line, end)
                          else 'MISSING_COLON')
            else:
                group = line[start + 1:end]
                if re.fullmatch(rb'[ \t]*smb0[ \t]*&&[ \t]*smb1[ \t]*', group) is not None:
                    expression = 'SMB0_AND_SMB1'
                else:
                    tags, reason = _group(group)
        if reason:
            result['malformed_rows'] += 1
            result['malformed_reasons'][reason] += 1
            if reason == 'FIRST_PAREN_LABEL':
                result['native_first_paren_compatible'] = False
            continue
        value = after[1:].strip(b' \t\r')
        presence = 'EMPTY' if not value else 'ABSENT' if value.lower() == b'absent' else 'PRESENT'
        predicates = scalar_predicates(value) if presence == 'PRESENT' else dict.fromkeys(PREDICATES, False)
        if expression:
            # A displayed derived result is not an independently stored 4CC.
            # Do not let it satisfy, duplicate or overwrite smb0/smb1 rows.
            result['non_tag_expression_rows'] += 1
            field = result['expressions'][expression]
            field['rows'] += 1
            field['presence'][presence] += 1
            for predicate, matches in predicates.items():
                field['predicates'][predicate] += int(matches)
            continue
        result['tagged_rows'] += 1
        size = len(tags)
        bucket = str(size) if size <= 4 else '5_8' if size <= 8 else '9_16' if size <= 16 else '17_32'
        result['group_sizes'][bucket] += 1
        result['native4_compatible_rows' if size <= 4 else 'native4_incompatible_rows'] += 1
        result['duplicate_tag_rows'] += int(len(set(tags)) != size)
        unknown = False
        for tag in tags:
            if tag not in CATALOG_SET:
                result['unknown_tag_occurrences'] += 1
                unknown = True
                continue
            result['known_tag_occurrences'] += 1
            field = result['fields'][tag]
            field['rows'] += 1
            field['presence'][presence] += 1
            for predicate, matches in predicates.items():
                field['predicates'][predicate] += int(matches)
        result['unknown_tag_rows'] += int(unknown)
    result['qualified'] = result['malformed_rows'] == 0
    if not result['qualified']:
        result['failure_stage'] = 'TEXT'
        result['failure_reason'] = 'MALFORMED_ROWS'
    return result


class _ShapeError(Exception):
    pass


class _Number:
    """Discard numeric content during JSON decoding; retain only its kind."""
    __slots__ = ()


def scan_json(raw):
    """Qualify one whole JSON document, returning fixed names and kinds only."""
    result = _base('json')
    result.update({'root_kind': None, 'node_count': 0, 'max_depth': 0,
                   'unknown_key_occurrences': 0,
                   'fields': {tag: {'key_occurrences': 0, 'kinds': _counter(JSON_KINDS)}
                              for tag in CATALOG}})
    def fail(stage, reason):
        result['failure_stage'] = stage
        result['failure_reason'] = reason
        return result
    if type(raw) is not bytes:
        return fail('ENVELOPE', 'INPUT_TYPE')
    if not 0 < len(raw) <= LIMIT:
        return fail('ENVELOPE', 'INPUT_BOUND')
    try:
        text = raw.decode('utf-8', 'strict')
    except UnicodeError:
        return fail('UTF8', 'INVALID_UTF8')
    stripped = text.strip(' \t\r\n')
    if not stripped or stripped[0] not in '[{':
        return fail('ENVELOPE', 'OBJECT_OR_ARRAY_REQUIRED')
    # Bound recursion before invoking json.loads, respecting strings/escapes.
    depth = 0
    quoted = escaped = False
    for char in stripped:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > DEPTH_LIMIT:
                return fail('DEPTH', 'DEPTH_BOUND')
        elif char in ']}':
            depth -= 1
            if depth < 0:
                return fail('SYNTAX', 'INVALID_JSON')
    def pairs(items):
        out = {}
        for key, item in items:
            if key in out:
                raise _ShapeError('DUPLICATE')
            out[key] = item
        return out
    def number(_):
        return _Number()
    def constant(_):
        raise _ShapeError('SYNTAX')
    try:
        value = json.loads(stripped, object_pairs_hook=pairs, parse_int=number,
                           parse_float=number, parse_constant=constant)
    except _ShapeError as error:
        return fail('DUPLICATE', 'DUPLICATE_KEY') if error.args == ('DUPLICATE',) else fail('SYNTAX', 'INVALID_JSON')
    except json.JSONDecodeError as error:
        return fail('ENVELOPE', 'EXTRA_DATA') if error.msg == 'Extra data' else fail('SYNTAX', 'INVALID_JSON')
    except (ValueError, OverflowError, RecursionError):
        return fail('SYNTAX', 'INVALID_JSON')
    def kind(item):
        return ('OBJECT' if type(item) is dict else 'ARRAY' if type(item) is list
                else 'BOOLEAN' if type(item) is bool else 'NULL' if item is None
                else 'NUMBER' if type(item) is _Number else 'STRING')
    def visit(item, level):
        result['node_count'] += 1
        if result['node_count'] > NODE_LIMIT:
            raise _ShapeError('NODES')
        if level > DEPTH_LIMIT:
            raise _ShapeError('DEPTH')
        result['max_depth'] = max(result['max_depth'], level)
        if type(item) is str and any(0xd800 <= ord(char) <= 0xdfff for char in item):
            raise _ShapeError('SYNTAX')
        if type(item) is dict:
            for key, child in item.items():
                if any(0xd800 <= ord(char) <= 0xdfff for char in key):
                    raise _ShapeError('SYNTAX')
                if key in CATALOG_SET:
                    row = result['fields'][key]
                    row['key_occurrences'] += 1
                    row['kinds'][kind(child)] += 1
                else:
                    result['unknown_key_occurrences'] += 1
                visit(child, level + 1)
        elif type(item) is list:
            for child in item:
                visit(child, level + 1)
    result['root_kind'] = kind(value)
    try:
        visit(value, 0)
    except _ShapeError as error:
        stage = error.args[0]
        return fail(stage, {'NODES': 'NODE_BOUND', 'DEPTH': 'DEPTH_BOUND',
                            'SYNTAX': 'UNPAIRED_SURROGATE'}[stage])
    result['qualified'] = True
    return result


# Intentional compatibility names for an enclosing collector.  Both functions
# are pure observations; neither enables the old reader to accept a policy.
summarize = scan_text
json_shape = scan_json
