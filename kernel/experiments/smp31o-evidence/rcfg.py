#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded structural RCfg decoder; never interprets or executes commands.

Written from an independently supplied format description. Sequence names and
operand values are validated/consumed privately and never returned. Opcode and
flag values are opaque identifiers, including values unknown to the analyst.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
from typing import NamedTuple


HEADER_OFFSET = 0x110
MAGIC = 0x52436667
SECTION_COUNT = 5
NAME_KIND = 4
NAME_RECORD_SIZE = 66
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OPERANDS = 32
MAX_RECORDS = 65536
MAX_NAMES = 1024


class RCfgError(ValueError):
    """A fixed structural refusal reason, without input content or paths."""


class Record(NamedTuple):
    section_kind: int
    offset: int
    opcode: int
    sequence_id: int
    flags: int
    operand_count: int


def require(predicate, reason):
    if not predicate:
        raise RCfgError(reason)


def span(start, length, total, reason):
    require(0 <= start <= total and 0 <= length <= total - start, reason)
    return start, start + length


def overlaps(a, b):
    # Empty command sections occupy no bytes.
    return a[0] < a[1] and b[0] < b[1] and a[0] < b[1] and b[0] < a[1]


def _parse(payload):
    require(type(payload) is bytes, 'input_not_bytes')
    require(len(payload) <= MAX_INPUT_BYTES, 'input_too_large')
    header = span(HEADER_OFFSET, 16, len(payload), 'header_truncated')
    magic, count, directory_offset = struct.unpack_from('<IIQ', payload, HEADER_OFFSET)
    require(magic == MAGIC, 'header_magic')
    require(count == SECTION_COUNT, 'section_count')
    directory = span(directory_offset, count * 16, len(payload), 'directory_bounds')
    require(not overlaps(header, directory), 'directory_header_overlap')

    sections = {}
    occupied = [header, directory]
    for index in range(count):
        kind, length, offset = struct.unpack_from('<IIQ', payload, directory_offset + 16 * index)
        require(kind in range(SECTION_COUNT), 'section_kind')
        require(kind not in sections, 'duplicate_section_kind')
        region = span(offset, length, len(payload), 'section_bounds')
        require(not any(overlaps(region, old) for old in occupied), 'section_overlap')
        if kind == NAME_KIND:
            require(offset % 2 == 0 and length % NAME_RECORD_SIZE == 0, 'name_section_alignment')
            require(0 < length // NAME_RECORD_SIZE <= MAX_NAMES, 'name_count')
        else:
            require(offset % 4 == 0 and length % 4 == 0, 'command_section_alignment')
        sections[kind] = region
        occupied.append(region)
    require(set(sections) == set(range(SECTION_COUNT)), 'missing_section_kind')

    sequence_ids = set()
    names = set()
    start, end = sections[NAME_KIND]
    for offset in range(start, end, NAME_RECORD_SIZE):
        sequence_id, = struct.unpack_from('<H', payload, offset)
        require(sequence_id < MAX_NAMES, 'sequence_id_range')
        require(sequence_id not in sequence_ids, 'duplicate_sequence_id')
        field = payload[offset + 2:offset + NAME_RECORD_SIZE]
        terminator = field.find(b'\0')
        require(terminator > 0, 'name_termination')
        name = field[:terminator]
        require(all(32 <= value <= 126 for value in name), 'name_not_printable_ascii')
        require(not any(field[terminator:]), 'name_padding')
        require(name not in names, 'duplicate_sequence_name')
        sequence_ids.add(sequence_id)
        names.add(name)

    records = []
    for kind in range(NAME_KIND):
        offset, end = sections[kind]
        while offset < end:
            require(len(records) < MAX_RECORDS, 'record_count_limit')
            word, = struct.unpack_from('<I', payload, offset)
            operand_count = word & 0xff
            require(operand_count <= MAX_OPERANDS, 'operand_count_limit')
            record_length = 4 * (1 + operand_count)
            require(record_length <= end - offset, 'record_truncated')
            sequence_id = (word >> 18) & 0x3ff
            require(sequence_id in sequence_ids, 'unknown_sequence_id')
            records.append(Record(kind, offset, (word >> 8) & 0x3ff,
                                  sequence_id, word >> 28, operand_count))
            offset += record_length
        require(offset == end, 'section_not_consumed')
    return sections, sequence_ids, tuple(records)


def parse_records(payload):
    """Return immutable structural indices, omitting all names and operands.

    Offsets address the caller's supplied bytes only. They are not hardware
    addresses or executable commands. No branch/nesting semantics are inferred.
    """
    return _parse(payload)[2]


def decode(payload):
    """Return bounded aggregate metadata, with no raw names/operands/bytes."""
    sections, sequence_ids, records = _parse(payload)
    opcode_counts = Counter(row.opcode for row in records)
    flag_counts = Counter(row.flags for row in records)
    sequence_counts = Counter(row.sequence_id for row in records)
    section_counts = Counter(row.section_kind for row in records)
    return {
        'result': 'RCfg_STRUCTURAL_PASS',
        'format': 'rcfg-structural-v1',
        'size_bytes': len(payload),
        'sha256': hashlib.sha256(payload).hexdigest(),
        'section_count': len(sections),
        'named_sequence_count': len(sequence_ids),
        'command_count': len(records),
        'maximum_operand_count': max((row.operand_count for row in records), default=0),
        'sections': [{'kind': kind, 'size_bytes': end - start,
                      'command_count': section_counts[kind]}
                     for kind, (start, end) in sorted(sections.items())],
        'opcode_histogram': {str(key): opcode_counts[key] for key in sorted(opcode_counts)},
        'flag_histogram': {str(key): flag_counts[key] for key in sorted(flag_counts)},
        'sequence_record_counts': {str(key): sequence_counts[key] for key in sorted(sequence_ids)},
        'native_operations': 0,
        'evaluated_conditions': False,
        'firmware_emulator': False,
        'command_semantics_interpreted': False,
        'nesting_validated': False,
    }


def read_input(path):
    """Read one explicitly supplied regular file, bounded before and during IO."""
    try:
        # Reject special files before opening. O_NONBLOCK also closes the race
        # where a named pipe replaces the checked regular file before open.
        require(stat.S_ISREG(os.lstat(path).st_mode), 'input_not_regular_file')
        flags = (os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) |
                 getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode), 'input_not_regular_file')
            require(before.st_size <= MAX_INPUT_BYTES, 'input_too_large')
            payload = stream.read(MAX_INPUT_BYTES + 1)
            after = os.fstat(stream.fileno())
            require(before.st_size == after.st_size == len(payload) and
                    before.st_mtime_ns == after.st_mtime_ns, 'input_changed_during_read')
            require(len(payload) <= MAX_INPUT_BYTES, 'input_too_large')
            return payload
    except OSError:
        raise RCfgError('input_unreadable') from None


def refusal(reason):
    return {'result': 'RCfg_STRUCTURAL_REFUSAL', 'reason': reason,
            'native_operations': 0, 'evaluated_conditions': False,
            'firmware_emulator': False}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's ordinary error can echo filenames or input content.
        print(json.dumps(refusal('arguments_invalid'), sort_keys=True))
        raise SystemExit(2)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path, help='Local decoded RCfg payload')
    args = parser.parse_args(argv)
    try:
        result = decode(read_input(args.input))
    except RCfgError as exc:
        print(json.dumps(refusal(str(exc)), sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
