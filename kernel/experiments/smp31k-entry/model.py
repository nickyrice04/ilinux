#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded synthetic execution of the original tripwire's exact instruction set.

This is a software fault-injection oracle, not an Apple CPU/firmware emulator.
No instruction runs on a target. Visibility, traps and asynchronous exceptions
are injected unknowns, never assumed to match physical hardware.
"""
import importlib.util
from pathlib import Path
import struct
spec = importlib.util.spec_from_file_location('_31k_model_builder',
                                             Path(__file__).with_name('builder.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def run(*, mpidr=0x40001, current_el=8, halt_before=None, invisible_stores=False,
        body=None, incoming_x0=0x1234567890):
    expected, labels = builder.program()
    if body is None:
        body = expected
    builder.need(body == expected, 'model_requires_exact_original_program')
    builder.need(halt_before is None or type(halt_before) is int and
                 0 <= halt_before <= len(body)//4, 'invalid_fault_index')
    regs = {index: 0x60000000+index for index in range(31)}
    regs[0] = incoming_x0
    saved_lr, sp = regs[30], 0x70000000
    memory = {offset: 0 for offset in range(builder.RECORD, builder.RECORD_END, 8)}
    stores, system_reads, phases = [], [], []
    terminal = False
    pc = builder.CODE_START
    for index, (ins,) in enumerate(struct.iter_unpack('<I', body)):
        if halt_before == index:
            break
        pc = builder.CODE_START+index*4
        if index == 0:
            imm = builder.audit.signed(((ins >> 5) & 0x7ffff) << 2 |
                                       ((ins >> 29) & 3), 21)
            regs[0] = (pc & ~4095)+(imm << 12)
        elif index == 1:
            regs[0] += (ins >> 10) & 4095
        elif ins & 0xff80001f == 0xd2800008:
            regs[8] = (ins >> 5) & 65535
        elif ins in (0xf9000008, 0xf9000808, 0xf9000409):
            address = regs[0]+((ins >> 10) & 4095)*8
            builder.need(address in memory, 'model_store_outside_owned_record')
            value = regs[ins & 31]
            stores.append((address, value))
            if not invisible_stores:
                memory[address] = value
            if address == builder.RECORD:
                phases.append(value)
        elif ins == 0xd5033f9f:
            pass
        elif ins == 0xd53800a8:
            system_reads.append('MPIDR_EL1')
            regs[8] = mpidr
        elif ins == 0xd3405d08:
            regs[8] &= 0xffffff
        elif ins == 0xd5384249:
            system_reads.append('CurrentEL')
            regs[9] = current_el
        elif ins == 0x14000000:
            terminal = True
            break
        else:
            raise ValueError('unknown_original_instruction')
    return dict(memory=memory, stores=stores, system_reads=system_reads,
                published_phases=phases, terminal_spin_selected=terminal,
                pc=pc, sp=sp, lr=regs[30], original_lr=saved_lr,
                x0=regs[0], untouched_registers=[index for index in range(31)
                    if index not in (0, 8, 9) and regs[index] == 0x60000000+index],
                bss_reached=False, native_execution='NOT RUN',
                hardware_visibility_proven=False)
