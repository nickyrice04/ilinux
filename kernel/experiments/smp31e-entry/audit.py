#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Static boot021 entry/prologue audit. Parses bytes; no instruction execution."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

IMAGE_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
SYMBOL_SHA = '751a9643a2196eda44efba4789aa789465b2b75e9546be460946d2fa4c70ac11'
STACK_BOTTOM = 0x94000
STACK_TOP = 0xa0000


def need(ok, why):
    if not ok: raise ValueError(why)


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def word(image, offset):
    return struct.unpack_from('<I', image, offset)[0]


def bl_target(image, offset):
    value = word(image, offset)
    need(value >> 26 == 0b100101, 'expected_BL')
    return offset + signed(value & 0x3ffffff, 26) * 4


def frame_size(image, entry):
    # STP X29,X30,[SP,#negative]! or SUB SP,SP,#imm + STP X29,X30,[SP].
    first = word(image, entry)
    if first & 0xffc07fff == 0xa9807bfd:
        size = -signed((first >> 15) & 127, 7) * 8
    else:
        need(first & 0xffc003ff == 0xd10003ff, 'unsupported_frame_prologue')
        size = (first >> 10) & 0xfff
        need(word(image, entry + 8) == 0xa9007bfd, 'frame_pair_not_found')
    need(size > 0 and size % 16 == 0, 'unaligned_frame')
    return size


def relative_relocations(image, named):
    """Decode public ELF64 RELA records carried in the flat boot image."""
    start, end = named['_rela_start'], named['_rela_end']
    need((end - start) % 24 == 0, 'bad_rela_size')
    records = [struct.unpack_from('<QQQ', image, offset)
               for offset in range(start, end, 24)]
    need(all(kind == 1027 for _, kind, _ in records), 'unsupported_relocation')
    need(not any(STACK_BOTTOM <= target < STACK_TOP or
                 STACK_BOTTOM <= addend < STACK_TOP
                 for target, _, addend in records), 'stack_relocation_reference')
    return records


def direct_address_references(image, named):
    """Conservatively scan ADR/ADRP encodings; this is not a CFG proof.

    ADRP is checked at page granularity. There are no such candidate hits,
    including literal data that may happen to decode as these instructions.
    Computed addresses and broad range operations are outside this check.
    """
    hits = []
    for offset in range(named['_text_start'], named['_text_size'], 4):
        instruction = word(image, offset)
        kind = instruction & 0x9f000000
        if kind not in (0x10000000, 0x90000000):
            continue
        immediate = signed(((instruction >> 5) & 0x7ffff) << 2 |
                           ((instruction >> 29) & 3), 21)
        address = (offset + immediate if kind == 0x10000000 else
                   (offset & ~0xfff) + (immediate << 12))
        if STACK_BOTTOM <= address < STACK_TOP:
            hits.append((offset, address))
    need(not hits, 'stack_direct_address_reference')
    return hits


def direct_calls(image, start, end):
    return {bl_target(image, offset) for offset in range(start, end, 4)
            if word(image, offset) >> 26 == 0b100101}


def conditional_stack_audit(image, named, relocations):
    """Bound the reviewed ordinary path, not all hardware exception paths.

    The bound relies on CPU1 entering with MMU off, the known MIDR entry,
    original UART iodev callbacks, no exceptions, and WFE/no-dispatch parking.
    Those conditions have not been measured on CPU1. No live approval follows.
    """
    frames = {
        'reset_c': (0x328e0, 32), 'init_cpu': (0x14fe0, 48),
        'debug_printf': (0x37ca0, 672), 'vsnprintf': (0x388e0, 96),
        'fmtint': (0x38560, 64), 'console_write': (0x1d420, 112),
        'console_helper': (0x1cde0, 48),
        'uart_write_wrapper': (0x348e0, 32),
        'dock_write_wrapper': (0x1a440, 32),
        # These two have an initial CBZ before the frame allocation.
        'uart_write': (0x348a4, 32), 'dock_write': (0x1a404, 32),
        'uart_putchar': (0x34834, 32), 'uart_puts': (0x34860, 32),
        'secondary_entry': (0x30d40, 48),
    }
    for label, (entry, expected) in frames.items():
        need(frame_size(image, entry) == expected, 'path_frame_' + label)
    need(direct_calls(image, named['debug_printf'], 0x37d40) ==
         {named['vsnprintf'], named['iodev_console_write']}, 'printf_call_set')
    need(direct_calls(image, named['vsnprintf'], 0x39340) ==
         {named['fmtint'], named['fmtstr']}, 'format_call_set')
    need(not direct_calls(image, named['fmtint'], named['vsnprintf']), 'fmtint_not_leaf')
    need(not direct_calls(image, named['fmtstr'], named['fmtint']), 'fmtstr_not_leaf')
    # The known CPU1 part has no part-specific init callback in this image.
    row = 0x1017d8
    need(word(image, row) == 0x68 and struct.unpack_from('<Q', image, row+16)[0] == 0,
         'known_midr_init_value')
    need(not any(target == row+16 for target, _, _ in relocations),
         'known_midr_init_relocation')
    need(any(target == row+24 and addend == named['features_m4']
             for target, _, addend in relocations), 'known_midr_features')
    return {
        'ordinary_path_max_bytes': 32+48+672+112+48+32+32,
        'formatting_path_max_bytes': 32+48+672+96+64,
        'review_allowance_bytes': 2048,
        'complete_hardware_bound': False,
        'conditions': ['CPU1 MMU off and known part 0x68',
                       'Original UART/dock iodev callbacks and UART RAM bases zero',
                       'No exceptions, recursive output, or arbitrary target dispatch',
                       'WFE parking; no deep WFI, reset, or Linux continuation'],
        'device_memory_review': {
            'build_flags': ['-mstrict-align', '-mgeneral-regs-only'],
            'formatting_leaf_calls': ['fmtint', 'fmtstr'],
            'formatting_memcpy_calls': 0,
            'complete_dynamic_alignment_proof': False,
            'notes': ['Public source uses byte accesses for formatting buffers/strings',
                      'Varargs and len storage have natural alignment under AAPCS64',
                      'The MMU-on console path can reach memcpy and is excluded',
                      'No live Device-memory stack approval from this conditional audit']
        },
    }


def audit(image, symbols):
    need(hashlib.sha256(image).hexdigest() == IMAGE_SHA, 'image_digest')
    need(hashlib.sha256(symbols).hexdigest() == SYMBOL_SHA, 'symbol_digest')
    records = [(int(v,16), kind, name) for v, kind, name in
               (line.split() for line in symbols.decode().splitlines() if len(line.split()) == 3)]
    named = {name: offset for offset, _, name in records}
    need(named['_smp_shared_start'] == 0x90000 and named['_smp_shared_end'] == 0xa0000,
         'shared_boundaries')
    need(named['_reset_stack'] == 0x90a20, 'last_shared_object')
    need(not any(0x90a28 <= value < 0xa0000 for value, _, _ in records), 'padding_symbol')
    need(image[0x90a28:0xa0000] == bytes(0xf5d8), 'padding_not_zero')
    relocations = relative_relocations(image, named)
    address_hits = direct_address_references(image, named)
    stack_audit = conditional_stack_audit(image, named, relocations)
    need(bl_target(image, 0x970) == 0x328e0 and bl_target(image,0x978) == 0x328e0,
         'reset_C_call')
    frames = {name: frame_size(image, entry) for name, entry in
              [('reset_c',0x328e0),('uart_puts',0x34860),('init_cpu',0x14fe0),
               ('debug_printf',0x37ca0),('vsnprintf',0x388e0),('secondary_entry',0x30d40)]}
    need(frames == {'reset_c':32,'uart_puts':32,'init_cpu':48,
                    'debug_printf':672,'vsnprintf':96,'secondary_entry':48}, 'frame_sizes')
    calls = [(0x32920,0x34860),(0x32930,0x34860),(0x32940,0x37ca0),
             (0x32950,0x37ca0),(0x32954,0x14fe0),(0x32968,0x37ca0),
             (0x3296c,0x1a500),(0x15020,0x37ca0),(0x15060,0x37ca0)]
    need(all(bl_target(image, site) == callee for site, callee in calls),'call_sites')
    # Exact linked stores: MPIDR from X20 to [reset_table + index*16],
    # then stack top to that record +8, then DSB SY. No source-order assumption.
    need([word(image,p) for p in (0x30da0,0x30da8,0x30dac)] ==
         [0xf8236854,0xf9000480,0xd5033f9f], 'reset_publication_instructions')
    return {'result':'STATIC_ENTRY_AUDIT_PASS','image_sha256':IMAGE_SHA,
        'symbol_sha256':SYMBOL_SHA,'frame_bytes':frames,
        'reset_publication_order':['mpidr','stack','dsb_sy'],
        'shared_padding':{'start_offset':'0x90a28','end_offset':'0xa0000','zero_bytes':0xf5d8},
        'candidate_stack':{'bottom_offset':hex(STACK_BOTTOM),'top_offset':hex(STACK_TOP),
                           'bytes':STACK_TOP-STACK_BOTTOM,'native_deployment_ready':False,
                           'reset_record_expected_stack_offset':'0x178000',
                           'relocations_checked':len(relocations),
                           'adr_adrp_references':address_hits},
        'conditional_stack_audit':stack_audit,
        'call_return_offsets':[hex(site+4) for site,_ in calls],
        'native_execution':'NOT RUN',
        'limits':['Static source/image facts, not a reset emulator',
                  'Conditional path bound does not cover unexpected CPU1 MMU state or exceptions',
                  'No symbols/relocations/ADR references does not rule out computed range accesses',
                  'Shared Device-memory stack changes runtime layout; live use remains HOLD']}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image',type=Path,required=True)
    p.add_argument('--symbols',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(audit(a.image.read_bytes(),a.symbols.read_bytes()),indent=2))
