#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pinned public boot021 vector-entry audit. Data inspection only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous = load('_31f_frozen_layout', HERE.parent / 'smp31e-entry' / 'build_recorder.py')
need, word, signed = previous.need, previous.audit.word, previous.audit.signed
IMAGE_SHA = previous.audit.IMAGE_SHA
SYMBOL_SHA = previous.audit.SYMBOL_SHA
SOURCE_SHA = '91de75024c12f034a046171e88c8be9377bb09e4bfe95bf1ac5ba3cdd1e423ea'
SOURCE_COMMIT = '57a9339ffd1876e78297b17d34dece8cff8fa1ba'


def audit(image, symbols, source=None):
    result = previous.audit.audit(image, symbols)
    layout = previous.region_audit(image, symbols)
    records = [line.split() for line in symbols.decode().splitlines()]
    named = {row[2]: int(row[0], 16) for row in records if len(row) == 3}
    need(named['_vectors_start'] == 0 and named['cpu_reset'] == 0x8fc,
         'vector_symbols_changed')
    need(word(image, 0) == 0xd2800609 and word(image, 4) == 0x1400023e,
         'vector_dispatch_changed')
    need(word(image, 0x8fc) == 0x528009e0 and
         previous.audit.bl_target(image, 0x900) == named['debug_putc'] and
         word(image, named['debug_putc']) == 0xd65f03c0 and
         [word(image, pc) for pc in (0x904, 0x908)] == [0xd5384248, 0xf100311f],
         'dead_register_definition_changed')
    if source is not None:
        need(hashlib.sha256(source).hexdigest() == SOURCE_SHA, 'public_source_digest')
    return {
        'result': 'STATIC_VECTOR_ENTRY_AUDIT_PASS',
        'image_sha256': IMAGE_SHA, 'symbol_sha256': SYMBOL_SHA,
        'public_source_commit': SOURCE_COMMIT, 'public_start_source_sha256': SOURCE_SHA,
        'public_source_checked': source is not None,
        'layout_audit': layout, 'reset_entry': '0x0', 'reset_dispatch': '0x4',
        'reset_dispatch_target': '0x8fc', 'instructions_before_old_hook': 2,
        'entry_slot_also_sync_exception_vector': True,
        'first_definition': {'x0': '0x8fc', 'x8': '0x904', 'NZCV': '0x908'},
        'x9_original_assignment_replayed': 'MOV X9,#48',
        'computed_reference_proof': False,
        'frozen_full_layout_audit_passed': result['result'] == 'STATIC_ENTRY_AUDIT_PASS',
        'native_execution': 'NOT RUN',
        'limits': ['No proof of effective reset-vector target from mirror reads',
                   'No proof of instruction-cache visibility on an offline secondary',
                   'Vector zero is also a synchronous exception slot',
                   'Static references cannot rule out computed or broad-range accesses']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.image.read_bytes(), args.symbols.read_bytes(),
                           args.source.read_bytes() if args.source else None), sort_keys=True))
