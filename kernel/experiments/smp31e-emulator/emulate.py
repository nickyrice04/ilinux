#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Interpret a bounded public boot021 instruction path against synthetic RAM.

This is not native execution or a model of Apple reset/cache/power hardware.
The public entry point verifies the complete image and, when supplied, the
complete symbol file before interpreting exact image words. No device API.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

IMAGE_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
SYMBOL_SHA = '751a9643a2196eda44efba4789aa789465b2b75e9546be460946d2fa4c70ac11'
MASK64 = (1 << 64) - 1
BASE = 0x10000000000  # Synthetic relocation, not an observed address.
CPU1 = 0x40001
EXPECTED = {'cpu_reset': 0x8fc, 'debug_putc': 0x9bc,
            '_cpu_reset_c': 0x328e0, 'smp_reset_stacks': 0x90010,
            '_reset_stack': 0x90a20, '_smp_shared_end': 0xa0000,
            'secondary_stacks': 0x158000}
FALLBACK_BOTTOM, FALLBACK_TOP = 0x94000, 0xa0000
DEDICATED_BOTTOM, DEDICATED_TOP = 0x168000, 0x178000
CASES = ('table_miss', 'table_hit', 'matching_zero_stack', 'el2_miss',
         'el3_shared', 'mpidr_high_bits', 'last_slot_hit', 'other_entry')


class Refused(ValueError):
    """A model boundary or invalid input, never a physical fault diagnosis."""


def need(condition, reason):
    if not condition:
        raise Refused(reason)


def integer(value, lo, hi, reason):
    need(type(value) is int and lo <= value <= hi, reason)
    return value


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def verify(image, symbol_bytes=None):
    need(len(image) == 3932160 and hashlib.sha256(image).hexdigest() == IMAGE_SHA,
         'image_digest')
    for offset, expected_word in ((0x4, 0x1400023e), (0x8fc, 0x528009e0),
                                  (0x970, 0x9400c7dc), (0x978, 0x9400c7da),
                                  (0x9bc, 0xd65f03c0), (0x328e0, 0xa9be7bfd)):
        need(struct.unpack_from('<I', image, offset)[0] == expected_word,
             'reviewed_instruction_binding')
    if symbol_bytes is None:
        return 'reviewed_layout_only'
    need(hashlib.sha256(symbol_bytes).hexdigest() == SYMBOL_SHA, 'symbol_digest')
    symbols = {}
    for line in symbol_bytes.decode('ascii').splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in EXPECTED:
            need(fields[2] not in symbols, 'duplicate_symbol')
            symbols[fields[2]] = int(fields[0], 16)
    need(symbols == EXPECTED, 'symbol_layout')
    return 'full_symbol_digest'


def logical_mask(sf, n, immr, imms):
    """A64 DecodeBitMasks immediate form; reject reserved encodings."""
    width = 64 if sf else 32
    length = ((n << 6) | ((~imms) & 63)).bit_length() - 1
    need(length >= 1 and (sf or n == 0), 'logical_immediate_reserved')
    size = 1 << length
    need(size <= width, 'logical_immediate_width')
    levels = size - 1
    s, r = imms & levels, immr & levels
    need(s != levels, 'logical_immediate_reserved')
    value = (1 << (s + 1)) - 1
    value = ((value >> r) | (value << ((size - r) % size))) & ((1 << size) - 1)
    return sum(value << shift for shift in range(0, width, size))


class Memory:
    """Only explicitly mapped synthetic bytes are readable/writable."""
    def __init__(self):
        self.regions = []
        self.writes = []

    def map(self, address, data, writable, label):
        integer(address, 0, MASK64, 'map_address')
        need(data and address + len(data) <= MASK64 + 1, 'map_extent')
        end = address + len(data)
        need(all(end <= start or address >= start + len(buf)
                 for start, buf, _, _ in self.regions), 'map_overlap')
        self.regions.append((address, bytearray(data), writable, label))

    def locate(self, address, size, write=False):
        integer(address, 0, MASK64, 'memory_address')
        integer(size, 1, 16, 'memory_size')
        need(address + size <= MASK64 + 1, 'memory_overflow')
        for start, data, writable, label in self.regions:
            if start <= address and address + size <= start + len(data):
                need(not write or writable, 'memory_readonly')
                return data, address - start, label
        raise Refused('memory_unmapped')

    def read(self, address, size):
        data, index, _ = self.locate(address, size)
        return bytes(data[index:index + size])

    def read64(self, address):
        need(address % 8 == 0, 'memory_alignment')
        return struct.unpack('<Q', self.read(address, 8))[0]

    def write(self, address, data):
        buf, index, label = self.locate(address, len(data), write=True)
        buf[index:index + len(data)] = data
        self.writes.append((address, len(data), label))


class Machine:
    """Narrow A64 decoder. Call verify() before use with retained artifacts.

    Synthetic unit tests may instantiate this class directly. The CLI and
    simulate() expose no input-verification bypass.
    """
    def __init__(self, image, memory, current_el, mpidr, base=BASE):
        integer(base, 0, MASK64 - len(image), 'image_base')
        need(base % 0x4000 == 0, 'image_base_alignment')
        integer(current_el, 4, 12, 'current_el')
        need(current_el in (4, 8, 12), 'current_el')
        integer(mpidr, 0, MASK64, 'mpidr')
        need(mpidr & 0xffffff == CPU1, 'cpu1_identity')
        self.image, self.memory, self.base = image, memory, base
        self.current_el, self.mpidr = current_el, mpidr
        self.x = [0] * 31
        self.x[29] = 0x2929292929292929  # Explicit synthetic caller FP.
        self.sp = 0
        self.pc = base + EXPECTED['cpu_reset']
        self.nzcv = 0
        self.trace = []
        self.first_store = None

    def reg(self, index, sp=False):
        return (self.sp if sp else 0) if index == 31 else self.x[index]

    def set_reg(self, index, value, width=64, sp=False):
        value &= (1 << width) - 1
        if index != 31:
            self.x[index] = value
        elif sp:
            need(value % 16 == 0, 'stack_alignment')
            self.sp = value

    def fetch(self):
        offset = self.pc - self.base
        need(offset % 4 == 0, 'instruction_alignment')
        need(0x8fc <= offset < 0x97c or offset in (0x9bc, 0x328e0),
             'instruction_scope')
        need(offset + 4 <= len(self.image), 'instruction_extent')
        return offset, struct.unpack_from('<I', self.image, offset)[0]

    def flags_sub(self, lhs, rhs, result, width):
        mask = (1 << width) - 1
        lhs, rhs, result = lhs & mask, rhs & mask, result & mask
        sign = 1 << (width - 1)
        self.nzcv = ((8 if result & sign else 0) |
                     (4 if result == 0 else 0) |
                     (2 if lhs >= rhs else 0) |
                     (1 if ((lhs ^ rhs) & (lhs ^ result) & sign) else 0))

    def step(self):
        offset, insn = self.fetch()
        next_pc = self.pc + 4
        rd, rn = insn & 31, (insn >> 5) & 31
        sf = insn >> 31
        width = 64 if sf else 32
        kind = None
        # MOVZ (only the architectural 32/64-bit immediate form).
        if insn & 0x7f800000 == 0x52800000:
            shift = ((insn >> 21) & 3) * 16
            need(shift < width, 'movz_reserved')
            self.set_reg(rd, ((insn >> 5) & 0xffff) << shift, width)
            kind = 'movz'
        elif insn & 0x7c000000 == 0x14000000:
            linked = bool(insn & 0x80000000)
            if linked:
                self.x[30] = next_pc
            next_pc = self.pc + signed(insn & 0x3ffffff, 26) * 4
            kind = 'bl' if linked else 'b'
        elif insn & 0xfffffc1f == 0xd65f0000:
            next_pc = self.reg(rn)
            kind = 'ret'
        elif insn & 0xffffffe0 in (0xd5384240, 0xd53800a0):
            current = insn & 0xffffffe0 == 0xd5384240
            self.set_reg(rd, self.current_el if current else self.mpidr)
            kind = 'mrs_currentel' if current else 'mrs_mpidr'
        elif insn & 0x1f800000 == 0x11000000:
            subtract, flags = bool(insn & (1 << 30)), bool(insn & (1 << 29))
            need(not flags or subtract, 'add_flags_unsupported')
            value = ((insn >> 10) & 0xfff) << (12 if insn & (1 << 22) else 0)
            lhs = self.reg(rn, sp=True)
            result = lhs - value if subtract else lhs + value
            if flags:
                self.flags_sub(lhs, value, result, width)
            self.set_reg(rd, result, width, sp=not flags)
            kind = 'subs_imm' if flags else ('sub_imm' if subtract else 'add_imm')
        elif insn & 0xff000010 == 0x54000000:
            condition = insn & 15
            need(condition in (0, 1), 'condition_unsupported')
            z = bool(self.nzcv & 4)
            if z == (condition == 0):
                next_pc = self.pc + signed((insn >> 5) & 0x7ffff, 19) * 4
            kind = 'b_eq' if condition == 0 else 'b_ne'
        elif insn & 0x1f800000 == 0x12000000:
            need((insn >> 29) & 3 == 0, 'logical_operation_unsupported')
            # AND-immediate destination 31 denotes SP/WSP, not XZR/WZR.
            # boot021 uses X3; leave the SP form outside this narrow model.
            need(rd != 31, 'and_sp_unsupported')
            mask = logical_mask(sf, (insn >> 22) & 1,
                                (insn >> 16) & 63, (insn >> 10) & 63)
            self.set_reg(rd, self.reg(rn) & mask, width)
            kind = 'and_imm'
        elif insn & 0x9f000000 == 0x90000000:
            imm = ((insn >> 5) & 0x7ffff) << 2 | ((insn >> 29) & 3)
            self.set_reg(rd, (self.pc & ~0xfff) + signed(imm, 21) * 4096)
            kind = 'adrp'
        elif insn & 0xff000000 == 0x58000000:
            address = self.pc + signed((insn >> 5) & 0x7ffff, 19) * 4
            self.set_reg(rd, self.memory.read64(address))
            kind = 'ldr_literal'
        elif insn & 0x7e000000 == 0x34000000:
            nonzero = bool(insn & (1 << 24))
            zero = (self.reg(rd) & ((1 << width) - 1)) == 0
            if zero != nonzero:
                next_pc = self.pc + signed((insn >> 5) & 0x7ffff, 19) * 4
            kind = 'cbnz' if nonzero else 'cbz'
        elif insn & 0xffc00000 == 0xa8c00000:
            rt2 = (insn >> 10) & 31
            need(rd != rt2 and (rn == 31 or rn not in (rd, rt2)), 'ldp_overlap')
            address = self.reg(rn, sp=True)
            need(address % 8 == 0, 'memory_alignment')
            first, second = struct.unpack('<QQ', self.memory.read(address, 16))
            self.set_reg(rd, first)
            self.set_reg(rt2, second)
            self.set_reg(rn, address + signed((insn >> 15) & 127, 7) * 8, sp=True)
            kind = 'ldp_post'
        elif insn & 0xff200000 == 0xeb000000:
            need((insn >> 22) & 3 == 0 and (insn >> 10) & 63 == 0,
                 'sub_shift_unsupported')
            lhs, rhs = self.reg(rn), self.reg((insn >> 16) & 31)
            self.flags_sub(lhs, rhs, lhs - rhs, 64)
            self.set_reg(rd, lhs - rhs)
            kind = 'subs_reg'
        elif insn & 0xffe0ffe0 == 0xaa0003e0:
            self.set_reg(rd, self.reg((insn >> 16) & 31))
            kind = 'mov_reg'
        elif insn & 0xffc00000 == 0xf9400000:
            address = self.reg(rn, sp=True) + ((insn >> 10) & 0xfff) * 8
            self.set_reg(rd, self.memory.read64(address))
            kind = 'ldr_unsigned'
        elif insn & 0xffe00c00 == 0xf8400000:
            address = self.reg(rn, sp=True) + signed((insn >> 12) & 511, 9)
            self.set_reg(rd, self.memory.read64(address))
            kind = 'ldur'
        elif insn & 0xffc00000 == 0xa9800000:
            rt2 = (insn >> 10) & 31
            need(offset == EXPECTED['_cpu_reset_c'] and
                 (rd, rt2, rn) == (29, 30, 31), 'store_scope')
            entry_sp = self.sp
            address = entry_sp + signed((insn >> 15) & 127, 7) * 8
            need(address % 16 == 0, 'stack_alignment')
            # Check the complete pair before altering RAM or SP.
            self.memory.write(address, struct.pack('<QQ', self.reg(rd), self.reg(rt2)))
            self.set_reg(rn, address, sp=True)
            self.first_store = {'entry_sp_offset': entry_sp - self.base,
                                'frame_offset': address - self.base,
                                'lr_slot_from_entry_sp': address + 8 - entry_sp,
                                'saved_lr_offset': self.reg(rt2) - self.base}
            kind = 'stp_pre_first_frame'
        elif insn == 0xd503201f:
            kind = 'nop'
        elif insn == 0xd5033f9f:
            # Only a model event: no implementation of visibility/coherency.
            kind = 'dsb_sy_model_event'
        else:
            raise Refused('instruction_unsupported')
        self.trace.append({'offset': hex(offset), 'instruction': kind})
        self.pc = next_pc

    def run(self, max_steps=256):
        integer(max_steps, 1, 4096, 'step_bound')
        for _ in range(max_steps):
            self.step()
            if self.first_store is not None:
                return self.first_store
        raise Refused('step_limit')


def synthetic_memory(image, table_entries=(), fallback_top=FALLBACK_TOP,
                     fallback_bytes=0xc000):
    """Fixture writes are model initialization, not interpreted stores."""
    integer(fallback_bytes, 8, 0xc000, 'fixture_stack_bytes')
    integer(fallback_top, 0, MASK64 - BASE, 'fixture_stack_top')
    table = bytearray(struct.pack('<QQ', MASK64, 0) * 32)
    used = set()
    for index, mpidr, stack_offset in table_entries:
        integer(index, 0, 31, 'fixture_table_index')
        integer(mpidr, 0, MASK64, 'fixture_table_mpidr')
        integer(stack_offset, 0, MASK64 - BASE, 'fixture_table_stack')
        need(index not in used, 'fixture_duplicate_index')
        used.add(index)
        struct.pack_into('<QQ', table, index * 16, mpidr,
                         BASE + stack_offset if stack_offset else 0)
    mem = Memory()
    mem.map(BASE + 0x90010, table, False, 'reset_table')
    mem.map(BASE + 0x90a20, struct.pack('<Q', BASE + fallback_top), False, 'reset_pointer')
    mem.map(BASE + FALLBACK_TOP - fallback_bytes, bytes(fallback_bytes), True,
            'fallback_stack')
    mem.map(BASE + DEDICATED_BOTTOM, bytes(DEDICATED_TOP - DEDICATED_BOTTOM), True,
            'dedicated_stack')
    mem.map(BASE + 0x9e8, image[0x9e8:0x9f0], False, 'literal_pool')
    return mem


def simulate(image, symbol_bytes=None, case='table_miss', max_steps=256,
             include_trace=False):
    symbol_validation = verify(image, symbol_bytes)
    need(case in CASES, 'unknown_case')
    el, mpidr, entries = 4, CPU1, ()
    if case == 'table_hit':
        entries = ((1, CPU1, DEDICATED_TOP),)
    elif case == 'matching_zero_stack':
        entries = ((1, CPU1, 0),)
    elif case == 'el2_miss':
        el = 8
    elif case == 'el3_shared':
        el, entries = 12, ((1, CPU1, DEDICATED_TOP),)
    elif case == 'mpidr_high_bits':
        mpidr, entries = 0x80040001, ((1, CPU1, DEDICATED_TOP),)
    elif case == 'last_slot_hit':
        entries = ((31, CPU1, DEDICATED_TOP),)
    elif case == 'other_entry':
        entries = ((1, 0x40002, DEDICATED_TOP),)
    memory = synthetic_memory(image, entries)
    machine = Machine(image, memory, el, mpidr)
    frame = machine.run(max_steps)
    result = {'result': 'MODELED_FIRST_FRAME_STORE', 'case': case,
              'image_sha256': IMAGE_SHA,
              'symbol_sha256': SYMBOL_SHA if symbol_bytes is not None else None,
              'reviewed_symbol_sha256': SYMBOL_SHA,
              'symbol_validation': symbol_validation,
              'synthetic_current_el': el, 'steps': len(machine.trace),
              'first_frame': frame, 'interpreted_stores': len(memory.writes),
              'native_execution': 'NOT RUN', 'hardware_model': False,
              'limit': 'Synthetic reset state and RAM; no hardware/cache/timing claim'}
    if include_trace:
        result['trace'] = machine.trace
    return result


def public_error(error):
    """Only our fixed refusal labels may appear in the public CLI report."""
    return str(error) if type(error) is Refused else type(error).__name__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path)
    parser.add_argument('--case', choices=CASES + ('all',), default='all')
    parser.add_argument('--max-steps', type=int, default=256)
    parser.add_argument('--trace', action='store_true')
    args = parser.parse_args()
    try:
        need(args.image.is_file() and not args.image.is_symlink(), 'image_file')
        if args.symbols is not None:
            need(args.symbols.is_file() and not args.symbols.is_symlink(), 'symbols_file')
        image = args.image.read_bytes()
        symbols = args.symbols.read_bytes() if args.symbols is not None else None
        cases = CASES if args.case == 'all' else (args.case,)
        rows = [simulate(image, symbols, case, args.max_steps, args.trace) for case in cases]
        print(json.dumps({'result': 'MODELED_ENTRY_MATRIX', 'scenarios': rows,
                          'symbol_validation': rows[0]['symbol_validation'],
                          'native_execution': 'NOT RUN', 'hardware_model': False},
                         sort_keys=True))
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({'result': 'REFUSED', 'reason': public_error(error),
                          'native_execution': 'NOT RUN'}, sort_keys=True))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
