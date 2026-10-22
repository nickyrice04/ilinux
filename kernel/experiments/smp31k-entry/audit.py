#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact public boot021 cold-entry/padding audit. Data inspection only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_31k_layout_encoder',
    HERE.parent / 'smp31e-entry' / 'build_recorder.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
need, word, signed = previous.need, previous.audit.word, previous.audit.signed
IMAGE_SHA, SYMBOL_SHA = previous.audit.IMAGE_SHA, previous.audit.SYMBOL_SHA
LAYOUT = {'_text_start': 0, '_text_size': 0x70000, '_start': 0x800,
          '_rela_start': 0x84d10, '_rela_end': 0x8cd98,
          '_smp_shared_start': 0x90000, '_smp_shared_end': 0xa0000,
          '_reset_stack': 0x90a20, '_bss_start': 0x110000,
          '_bss_end': 0x389a80, '_stack_bot': 0x3c0000}
REGIONS = {'cold_stub': (0xb00, 0xc00), 'cold_record': (0x90a80, 0x90ac0),
           'control_record': (0x90b00, 0x90b40)}


def region_audit(image, named, records=()):
    """Bounded static references, not proof against computed/range accesses."""
    for start, end in REGIONS.values():
        need(image[start:end] == bytes(end-start), 'candidate_not_zero')
        need(not any(start <= value < end and kind != 'A'
                     for value, kind, _ in records), 'candidate_symbol')
    in_region = lambda target: any(start <= target < end
                                  for start, end in REGIONS.values())
    relocations = 0
    for offset in range(named['_rela_start'], named['_rela_end'], 24):
        destination, kind, addend = struct.unpack_from('<QQQ', image, offset)
        need(kind == 1027, 'unsupported_relocation')
        need(not in_region(destination) and not in_region(addend), 'candidate_relocation')
        need(not (0x800 <= destination < 0x804 or 0x800 <= addend < 0x804),
             'cold_hook_relocation')
        relocations += 1
    hits = []
    cold_refs = []
    for pc in range(named['_text_start'], named['_text_size'], 4):
        instruction = word(image, pc)
        target = None
        if instruction & 0x7c000000 == 0x14000000:
            target = pc + signed(instruction & 0x3ffffff, 26)*4
        elif (instruction & 0xff000010 == 0x54000000 or
              instruction & 0x7e000000 == 0x34000000 or
              instruction & 0x3b000000 == 0x18000000):
            target = pc + signed((instruction >> 5) & 0x7ffff, 19)*4
        elif instruction & 0x7e000000 == 0x36000000:
            target = pc + signed((instruction >> 5) & 0x3fff, 14)*4
        kind = instruction & 0x9f000000
        if kind in (0x10000000, 0x90000000):
            immediate = signed(((instruction >> 5) & 0x7ffff) << 2 |
                               ((instruction >> 29) & 3), 21)
            if kind == 0x10000000:
                target = pc + immediate
            elif pc + 4 < named['_text_size']:
                addend = previous.adjacent_add_offset(word(image, pc+4), instruction & 31)
                if addend is not None:
                    target = (pc & ~4095) + (immediate << 12) + addend
        if target is not None:
            if in_region(target):
                hits.append((pc, target))
            if target == 0x800:
                cold_refs.append(pc)
    need(not hits, 'candidate_direct_reference')
    need(not cold_refs, 'cold_entry_direct_reference')
    return {'zero_padding': True, 'symbol_check_performed': bool(records),
            'no_allocated_symbols': True if records else None,
            'relocations_checked': relocations, 'no_relative_references': True,
            'no_direct_branch_literal_adr_adjacent_adrp_add_references': True,
            'cold_entry_direct_references': 0, 'cold_hook_relocation_references': 0,
            'computed_reference_proof': False,
            'regions': {key: [hex(x) for x in value] for key, value in REGIONS.items()}}


def audit(image, symbols=None):
    need(type(image) is bytes and hashlib.sha256(image).hexdigest() == IMAGE_SHA,
         'image_digest')
    records, named = [], dict(LAYOUT)
    if symbols is not None:
        need(type(symbols) is bytes and hashlib.sha256(symbols).hexdigest() == SYMBOL_SHA,
             'symbol_digest')
        records = [(int(row[0], 16), row[1], row[2])
                   for row in (line.split() for line in symbols.decode().splitlines())
                   if len(row) == 3]
        named = {name: value for value, _, name in records}
        need(all(named.get(key) == value for key, value in LAYOUT.items()), 'layout_changed')
    need(word(image, 0x800) == 0xaa0003f3, 'cold_original_word')
    need(word(image, 0) == 0xd2800609 and word(image, 4) == 0x1400023e,
         'original_vector_changed')
    need(image[0xa00:0xc00] == bytes(0x200), 'original_vector_padding_changed')
    checked = region_audit(image, named, records)
    return {'result': 'STATIC_COLD_CANDIDATE_AUDIT_PASS', 'image_sha256': IMAGE_SHA,
            'symbol_sha256': SYMBOL_SHA if symbols is not None else None,
            'symbol_mode': 'full_symbols' if symbols is not None else 'reviewed_layout_only',
            'layout_audit': checked, 'effective_cpu1_entry': 'UNKNOWN',
            'primary_cold_entry_reuse_proven_absent': False,
            'native_execution': 'NOT RUN',
            'limits': ['No proof of the effective CPU1 reset entry or fetch/store visibility',
                       'No complete proof against computed or broad range references',
                       'Live scratch must be freshly zero; never erase unknown contents',
                       'Candidate intercepts natural late cold arrival; never resumes shared BSS',
                       'Unexpected CPU0 cold arrival loses proxy; human return bound is required']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.image.read_bytes(),
                           args.symbols.read_bytes() if args.symbols else None), sort_keys=True))
