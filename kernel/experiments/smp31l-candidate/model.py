# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact-prefix instruction interpreter with explicit injected fault/visibility.

No firmware, cache-coherence, exception routing or CPU hardware is emulated.
"""
import importlib.util
from pathlib import Path
import struct

spec = importlib.util.spec_from_file_location('_31l_model_builder',
                                            Path(__file__).with_name('builder.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def run(kind='vector', helper=0x10004000000, *, mpidr=0x40001, halt_before=None,
        invisible_stores=False, body=None, incoming_x0=0x1234567890):
    expected, labels = builder.program(kind, helper)
    body = expected if body is None else body
    builder.need(body == expected, 'model_requires_exact_original_program')
    builder.need(halt_before is None or type(halt_before) is int and
                 0 <= halt_before <= 15, 'invalid_fault_index')
    builder.need(type(invisible_stores) is bool, 'invalid_visibility_premise')
    builder.need(type(mpidr) is int and 0 <= mpidr < 1 << 64, 'invalid_mpidr')
    regs = {i: 0x60000000+i for i in range(31)}
    regs[0] = incoming_x0
    original = dict(regs)
    address = builder.record_address(kind, helper)
    memory = {address+i: 0 for i in range(0, builder.RECORD_BYTES, 8)}
    private_memory = dict(memory)
    stores, phases, reads = [], [], []
    pc = builder.CODE[kind]
    destination = None
    barriers = 0
    for index, (ins,) in enumerate(struct.iter_unpack('<I', body)):
        pc = builder.CODE[kind]+index*4
        if halt_before == index:
            break
        if ins & 0xff800000 == 0xd2800000:
            regs[ins & 31] = ((ins >> 5) & 65535) << (((ins >> 21) & 3)*16)
        elif ins & 0xff800000 == 0xf2800000:
            shift = ((ins >> 21) & 3)*16
            register = ins & 31
            regs[register] = ((regs[register] & ~(65535 << shift)) |
                              (((ins >> 5) & 65535) << shift))
        elif ins & 0xffc00000 == 0xf9000000:
            target = regs[(ins >> 5) & 31] + ((ins >> 10) & 4095)*8
            builder.need(target in memory, 'model_store_outside_owned_record')
            value = regs[ins & 31]
            stores.append((target, value))
            private_memory[target] = value
            if not invisible_stores:
                memory[target] = value
            if target == address:
                phases.append(value)
        elif ins == 0xd5033f9f:
            barriers += 1  # Deliberately does not publish private dirty memory.
        elif ins == 0xd53800a9:
            reads.append('MPIDR_EL1')
            regs[9] = mpidr
        elif ins == 0xd3405d29:
            regs[9] &= 0xffffff
        elif ins & 0xfc000000 == 0x14000000:
            destination = pc + builder.audit.signed(ins & 0x3ffffff, 26)*4
            builder.need(destination == builder.RESUME[kind], 'model_branch_destination')
        else:
            raise ValueError('unknown_original_instruction')
    return dict(memory=memory, private_memory=private_memory, stores=stores,
                published_phases=phases, system_reads=reads, barriers=barriers,
                branch_destination=destination, pc=pc, registers=regs,
                untouched_registers=[i for i in regs if regs[i] == original[i]],
                sp=0x70000000, lr=regs[30], original_lr=original[30], nzcv=0xa,
                incoming_x0_retained=regs[0] == incoming_x0,
                existing_recorder_executed=False, native_execution='NOT RUN',
                hardware_visibility_proven=False)
