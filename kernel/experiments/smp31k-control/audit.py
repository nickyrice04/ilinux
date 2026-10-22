#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only pinned-image and original leaf assembly audit; no execution."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import control as c


def object_text(data):
    """Extract only a bounded AArch64 ELF64 relocatable's text and function."""
    c.need(type(data) is bytes and 64 <= len(data) <= 1024 * 1024, 'object_size')
    c.need(data[:7] == b'\x7fELF\x02\x01\x01', 'object_format')
    header = struct.unpack_from('<HHIQQQIHHHHHH', data, 16)
    etype, machine, version = header[:3]
    shoff, ehsize, shsize, count, names_index = header[5], header[7], header[10], header[11], header[12]
    c.need((etype, machine, version, ehsize, shsize) == (1, 183, 1, 64, 64), 'object_header')
    c.need(1 <= count <= 128 and names_index < count and shoff + count * 64 <= len(data),
           'object_sections')
    rows = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + index * 64) for index in range(count)]

    def contents(row):
        offset, size = row[4], row[5]
        c.need(offset <= len(data) and size <= len(data) - offset, 'object_section_bounds')
        return data[offset:offset + size]

    names = contents(rows[names_index])
    def string(table, offset):
        c.need(offset < len(table), 'object_string_offset')
        end = table.find(b'\0', offset)
        c.need(end >= offset, 'object_string_termination')
        try:
            return table[offset:end].decode('ascii')
        except UnicodeDecodeError:
            raise ValueError('object_string_encoding') from None

    named = [(string(names, row[0]), row) for row in rows]
    text_rows = [(index, row) for index, (name, row) in enumerate(named) if name == '.text']
    c.need(len(text_rows) == 1, 'object_text_count')
    text_index, text_row = text_rows[0]
    c.need(text_row[1] == 1 and text_row[2] == 6 and text_row[8] == 16, 'object_text_shape')
    c.need(all(not (row[2] & 4) or index == text_index for index, row in enumerate(rows)),
           'object_extra_executable_section')
    c.need(all(not (row[1] in (4, 9) and row[7] == text_index and row[5]) for row in rows),
           'object_text_relocations')
    symbols = []
    for row in rows:
        if row[1] != 2:
            continue
        c.need(row[9] == 24 and row[5] % 24 == 0 and row[6] < count, 'object_symbol_shape')
        table, strings = contents(row), contents(rows[row[6]])
        for offset in range(0, len(table), 24):
            name, info, other, section, value, size = struct.unpack_from('<IBBHQQ', table, offset)
            if info >> 4 and section == text_index:
                symbols.append((string(strings, name), info, other, value, size))
    c.need(symbols == [('smp31k_control_store', 0x12, 0, 0, 16)], 'object_function')
    return contents(text_row)


def audit(image, obj=None):
    c.verify_image_padding(image)
    if obj is not None:
        c.need(object_text(obj) == c.LEAF, 'leaf_assembly_mismatch')
    return dict(result='OFFLINE_CPU0_CONTROL_AUDIT_PASS',
        image_sha256=c.IMAGE_SHA256, shared_scratch_relative_offset=hex(c.SCRATCH_OFFSET),
        shared_scratch_bytes=c.SCRATCH_BYTES, pinned_image_scratch_zero=True,
        helper_leaf_offset=hex(c.LEAF_OFFSET), helper_leaf_bytes=len(c.LEAF),
        helper_leaf_sha256=c.LEAF_SHA256,
        compiled_object='PASS' if obj is not None else 'NOT RUN',
        compiled_object_sha256=hashlib.sha256(obj).hexdigest() if obj is not None else None,
        physical_hardware_operations=0, native_control='NOT RUN',
        cpu1_execution='NOT_TESTED', cpu1_record_visibility='NOT_TESTED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--object', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.image.read_bytes(), args.object.read_bytes() if args.object else None),
                     sort_keys=True))
