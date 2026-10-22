#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact-image audit for two original Normal-first prefix slots; no target I/O."""
import hashlib
import importlib.util
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_31l_previous_audit',
    HERE.parent / 'smp31k-entry' / 'audit.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
need, word, signed = previous.need, previous.word, previous.signed
IMAGE_SHA, SYMBOL_SHA = previous.IMAGE_SHA, previous.SYMBOL_SHA
REGIONS = {'normal_vector_prefix': (0xc00, 0xd00),
           'normal_cold_prefix': (0xd00, 0xe00)}


def region_audit(image, records=()):
    """Direct-reference coverage is bounded; computed/range accesses not proved."""
    for start, end in REGIONS.values():
        need(image[start:end] == bytes(end-start), 'normal_prefix_not_zero')
        need(not any(start <= value < end and kind != 'A'
                     for value, kind, _ in records), 'normal_prefix_symbol')
    inside = lambda target: any(start <= target < end for start, end in REGIONS.values())
    relocations = 0
    for offset in range(0x84d10, 0x8cd98, 24):
        destination, kind, addend = struct.unpack_from('<QQQ', image, offset)
        need(kind == 1027, 'normal_prefix_relocation_type')
        need(not inside(destination) and not inside(addend), 'normal_prefix_relocation')
        relocations += 1
    references = 0
    for pc in range(0, 0x70000, 4):
        ins = word(image, pc)
        target = None
        if ins & 0x7c000000 == 0x14000000:
            target = pc + signed(ins & 0x3ffffff, 26)*4
        elif (ins & 0xff000010 == 0x54000000 or
              ins & 0x7e000000 == 0x34000000 or
              ins & 0x3b000000 == 0x18000000):
            target = pc + signed((ins >> 5) & 0x7ffff, 19)*4
        elif ins & 0x7e000000 == 0x36000000:
            target = pc + signed((ins >> 5) & 0x3fff, 14)*4
        kind = ins & 0x9f000000
        if kind in (0x10000000, 0x90000000):
            imm = signed(((ins >> 5) & 0x7ffff) << 2 | ((ins >> 29) & 3), 21)
            if kind == 0x10000000:
                target = pc + imm
            elif pc+4 < 0x70000:
                add = previous.previous.adjacent_add_offset(word(image, pc+4), ins & 31)
                if add is not None:
                    target = (pc & ~4095) + (imm << 12) + add
        if target is not None and inside(target):
            references += 1
    need(references == 0, 'normal_prefix_direct_reference')
    return dict(zero_padding=True, symbol_check_performed=bool(records),
                no_allocated_symbols=True if records else None,
                relocations_checked=relocations, direct_references=references,
                computed_reference_proof=False,
                regions={key: [hex(v) for v in pair] for key, pair in REGIONS.items()})


def audit(image, symbols=None):
    checked = previous.audit(image, symbols)
    records = []
    if symbols is not None:
        records = [(int(row[0], 16), row[1], row[2])
                   for row in (line.split() for line in symbols.decode().splitlines())
                   if len(row) == 3]
    return dict(result='STATIC_NORMAL_PREFIX_AUDIT_PASS', image_sha256=IMAGE_SHA,
                symbol_sha256=SYMBOL_SHA if symbols is not None else None,
                symbol_mode=checked['symbol_mode'], layout_audit=region_audit(image, records),
                inherited_cold_audit=checked, native_execution='NOT RUN',
                cpu1_entry_context='UNKNOWN', native_deployment_ready=False)
