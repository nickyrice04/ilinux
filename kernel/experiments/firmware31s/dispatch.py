#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original bounded static relative-table resolver; never executes input code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import struct

U64 = 1 << 64
MAX_IMAGE = 64 * 1024 * 1024
MAX_ENTRIES = 4096


def need(value, reason):
    if not value:
        raise ValueError(reason)


def uint(value, maximum, reason):
    need(type(value) is int and 0 <= value <= maximum, reason)
    return value


def exact_dict(value, keys, reason):
    need(type(value) is dict and set(value) == set(keys), reason)


def layout_contract(layout, image_size):
    exact_dict(layout, ('schema', 'table_offset', 'entry_count', 'target_anchor',
                        'mappings', 'target_ranges', 'selectors'), 'layout_fields')
    need(type(layout['schema']) is int and layout['schema'] == 1, 'layout_schema')
    offset = uint(layout['table_offset'], U64 - 1, 'table_offset')
    count = uint(layout['entry_count'], MAX_ENTRIES, 'entry_count')
    anchor = uint(layout['target_anchor'], U64 - 1, 'target_anchor')
    need(count > 0 and offset % 4 == 0 and anchor % 4 == 0, 'table_alignment_or_count')
    need(offset <= image_size and count * 4 <= image_size - offset, 'table_extent')
    mappings = layout['mappings']
    need(type(mappings) is list and 0 < len(mappings) <= 128, 'mappings_count')
    file_spans, va_spans = [], []
    for mapping in mappings:
        exact_dict(mapping, ('file_offset', 'address', 'size'), 'mapping_fields')
        file_at = uint(mapping['file_offset'], U64 - 1, 'mapping_file_offset')
        address = uint(mapping['address'], U64 - 1, 'mapping_address')
        size = uint(mapping['size'], U64, 'mapping_size')
        need(size > 0 and size <= U64 - address, 'mapping_address_extent')
        need(file_at <= image_size and size <= image_size - file_at, 'mapping_file_extent')
        file_spans.append((file_at, file_at + size))
        va_spans.append((address, address + size))
    for spans in (file_spans, va_spans):
        spans.sort()
        need(all(left[1] <= right[0] for left, right in zip(spans, spans[1:])),
             'overlapping_mappings')
    need(any(start <= offset and offset + count * 4 <= end for start, end in file_spans),
         'table_not_in_one_mapping')
    ranges = layout['target_ranges']
    need(type(ranges) is list and 0 < len(ranges) <= 128, 'target_ranges_count')
    spans = []
    for item in ranges:
        need(type(item) is list and len(item) == 2, 'target_range_fields')
        start = uint(item[0], U64 - 1, 'target_range_start')
        end = uint(item[1], U64, 'target_range_end')
        need(start < end and start % 4 == 0 and end % 4 == 0, 'target_range_extent')
        spans.append((start, end))
    spans.sort()
    need(all(left[1] <= right[0] for left, right in zip(spans, spans[1:])),
         'overlapping_target_ranges')
    selectors = layout['selectors']
    need(type(selectors) is list and 0 < len(selectors) <= MAX_ENTRIES, 'selectors_count')
    for selector in selectors:
        uint(selector, count - 1, 'selector_bounds')
    need(len(set(selectors)) == len(selectors), 'duplicate_selector')
    return offset, count, anchor


def resolve(image, expected_sha256, layout):
    """Resolve selected signed LE32 offsets relative to an explicit code anchor.

    Layout and anchor are externally established premises, not inferred from
    adjacency. Result is static metadata, not execution or permission evidence.
    Neither image nor layout is modified; errors produce no partial result.
    Conservative mapping rules reject both file aliases and virtual overlaps.
    """
    need(type(image) is bytes and 0 < len(image) <= MAX_IMAGE, 'image_extent')
    need(type(expected_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', expected_sha256),
         'source_hash_format')
    need(hashlib.sha256(image).hexdigest() == expected_sha256, 'source_hash_mismatch')
    offset, count, anchor = layout_contract(layout, len(image))
    rows = []
    for selector in layout['selectors']:
        entry_offset = offset + selector * 4
        displacement, = struct.unpack_from('<i', image, entry_offset)
        target = anchor + displacement
        need(0 <= target <= U64 - 4, 'target_arithmetic')
        need(target % 4 == 0, 'target_alignment')
        need(any(start <= target and target + 4 <= end
                 for start, end in layout['target_ranges']), 'target_outside_allowed_ranges')
        matches = [m for m in layout['mappings']
                   if m['address'] <= target and target + 4 <= m['address'] + m['size']]
        need(len(matches) == 1, 'target_mapping')
        mapping = matches[0]
        target_file_offset = mapping['file_offset'] + target - mapping['address']
        need(target_file_offset % 4 == 0, 'target_file_alignment')
        rows.append(dict(selector=selector, entry_offset=entry_offset,
                         target=target, target_file_offset=target_file_offset))
    return dict(schema=1, result='STATIC_RESOLUTION_ONLY', source_sha256=expected_sha256,
                image_size=len(image), table_offset=offset, entry_count=count,
                target_anchor=anchor, targets=rows, hardware_operations=0,
                runtime_execution='NOT_OBSERVED', permission_state='UNKNOWN')


def read_regular(path, limit):
    need(not path.is_symlink(), 'input_symlink')
    info = path.stat()
    need(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit, 'input_extent')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    need(len(data) == info.st_size and len(data) <= limit, 'input_changed_or_oversized')
    return data


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError('arguments')


def main():
    parser = Parser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--layout', type=Path, required=True)
    args = parser.parse_args()
    image = read_regular(args.image, MAX_IMAGE)
    layout = json.loads(read_regular(args.layout, 131072))
    print(json.dumps(resolve(image, args.sha256, layout), indent=2, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        reason = str(error) if type(error) is ValueError and str(error).isidentifier() else type(error).__name__
        print(json.dumps(dict(result='STATIC_RESOLUTION_REFUSED', reason=reason,
                              hardware_operations=0)))
        raise SystemExit(1)
