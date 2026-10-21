#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original offline cache-range coverage audit; no transport or CPU execution."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

IMAGE_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
# Public pinned boot021 instruction bindings, not Apple binary contents.
WORDS = {0x27840: 0xd50b7520, 0x27844: 0x91010000,
         0x27b20: 0xd50b7a20, 0x27b24: 0x91010000,
         0x2ce48: 0xd5033f9f, 0x2ce4c: 0xd5033fdf}
SPANS = (('recorder_body', 0xa00, 168), ('vector_hook', 0, 4),
         ('permission_and_start_helper_relative_to_aligned_allocation', 192, 176),
         ('guard_free_read32_relative_to_aligned_allocation', 384, 16))


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def range_coverage(start, length, line_bytes):
    """Model only the public helper's 64-byte stride, not cache hardware.

    The helper does not align start down. Enumerating actual touched line IDs
    exposes any missed trailing line; alignment and line size are explicit inputs.
    """
    need(type(start) is int and 0 <= start < 1 << 64, 'start')
    need(type(length) is int and 0 < length <= 4096 and start + length <= 1 << 64,
         'length')
    need(line_bytes in (32, 64, 128, 256), 'line_bytes')
    required = set(range(start // line_bytes, (start + length - 1) // line_bytes + 1))
    touched = {address // line_bytes for address in range(start, start + length, 64)}
    return dict(covered=required <= touched, operations=len(range(start, start + length, 64)),
                required_lines=len(required), touched_lines=len(touched),
                missing_lines=len(required - touched), line_bytes=line_bytes)


def audit(image):
    need(hashlib.sha256(image).hexdigest() == IMAGE_SHA, 'image_digest')
    need(all(struct.unpack_from('<I', image, offset)[0] == word
             for offset, word in WORDS.items()), 'instruction_binding')
    rows = []
    for name, start, length in SPANS:
        tests = [range_coverage(start, length, line) for line in (64, 128, 256)]
        need(all(row['covered'] for row in tests), 'fixed_span_coverage')
        rows.append(dict(name=name, length=length, relative_start_aligned64=start % 64 == 0,
                         coverage=tests))
    return dict(result='STATIC_PUBLICATION_COVERAGE_PASS', image_sha256=IMAGE_SHA,
                cache_stride_bytes=64, modeled_line_sizes=[64, 128, 256], spans=rows,
                proxy_dsb_sy_then_isb=True, hardware_operations=0,
                runtime_ctr_line_size='NOT_OBSERVED', secondary_visibility='NOT_ESTABLISHED',
                native_smp='NOT RUN')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.image.read_bytes()), sort_keys=True))
