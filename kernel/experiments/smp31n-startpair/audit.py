#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare an independently assembled original ARM64 leaf with its fixed bytes."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct

spec = importlib.util.spec_from_file_location('pair31n', Path(__file__).with_name('plan.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def audit_object(data):
    p.need(type(data) is bytes and 64 <= len(data) <= 65536, 'pair_object_extent')
    p.need(data[:6] == b'\x7fELF\x02\x01' and
           struct.unpack_from('<HH', data, 16) == (1, 183), 'pair_object_architecture')
    offset, = struct.unpack_from('<Q', data, 40)
    stride, count, strings = struct.unpack_from('<HHH', data, 58)
    p.need(stride == 64 and 0 < count <= 128 and strings < count and
           64 <= offset <= len(data)-stride*count, 'pair_object_section_table')
    rows = [struct.unpack_from('<IIQQQQIIQQ', data, offset+i*stride) for i in range(count)]
    def contents(row):
        at, size = row[4:6]
        p.need(0 <= at <= len(data)-size, 'pair_object_section_extent')
        return data[at:at+size]
    names = contents(rows[strings])
    text = []
    for index, row in enumerate(rows):
        p.need(row[0] < len(names), 'pair_object_section_name')
        name = names[row[0]:].split(b'\0', 1)[0]
        if name == b'.text':
            text.append((index, contents(row)))
    p.need(len(text) == 1, 'pair_object_text_count')
    text_index, payload = text[0]
    p.need(not any(row[1] in (4, 9) and row[7] == text_index and row[5] != 0 for row in rows),
           'pair_object_unresolved_relocations')
    result = p.verify_leaf(payload)
    result.update(result='INDEPENDENT_ASSEMBLY_MATCH', assembly_objects=1)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_object(args.object.read_bytes()), sort_keys=True))
