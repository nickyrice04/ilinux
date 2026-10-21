#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original vector-first recorder encoder; no target operations or file writes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_31f_entry_audit', HERE / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
need = audit.need
ENTRY, RESUME = 0, 4
CODE_START, CODE_END = 0xa00, 0xc00
RECORD, RECORD_END = 0x90a40, 0x90a80
ORIGINAL_MOV = 0xd2800609
branch, adrp = audit.previous.branch, audit.previous.adrp


def program():
    """Independent A64 encoding, compared with guest assembly before use."""
    instructions, labels = [], {}
    def label(name):
        labels[name] = CODE_START + len(instructions) * 4
    def emit(value):
        instructions.append(value)
    def mov(value):
        emit(0xd2800008 | value << 5)  # MOVZ X8,#value
    def jump(name, condition=None):
        emit(('branch', name, condition))
    def phase(value):
        emit(0xd5033f9f); mov(value); emit(0xf9000008); emit(0xd5033f9f)
    emit(adrp(CODE_START, RECORD))
    emit(0x91000000 | (RECORD & 4095) << 10)
    mov(1)
    label('first_store')
    emit(0xf9000008)  # Earliest RAM marker, before any MRS or identity check.
    emit(0xd5033f9f)
    label('first_mrs')
    emit(0xd53800a8)  # MRS X8,MPIDR_EL1
    emit(0xd3405d08)  # UBFX X8,X8,#0,#24
    emit(0xf9000808)
    phase(2)
    emit(0xd5384249)  # X9 is dead until the original MOV is replayed.
    emit(0xf9000409)
    phase(3)
    for level in (1, 2, 3):
        emit(0xf100013f | (level * 4) << 10)  # CMP X9,#level*4
        jump('el' + str(level), 0)
    phase(255)
    jump('replay')
    for level, mrs in [(1, 0xd5381008), (2, 0xd53c1008), (3, 0xd53e1008)]:
        label('el' + str(level))
        emit(mrs)
        jump('sctlr_done')
    label('sctlr_done')
    emit(0xf9000c08)
    phase(4)
    label('replay')
    emit(ORIGINAL_MOV)
    jump(RESUME)
    words = []
    for index, instruction in enumerate(instructions):
        if isinstance(instruction, tuple):
            _, target, condition = instruction
            target = labels[target] if isinstance(target, str) else target
            instruction = branch(CODE_START + index * 4, target, condition)
        words.append(instruction)
    need(CODE_START + 4 * len(words) <= CODE_END, 'recorder_too_large')
    return struct.pack('<' + 'I' * len(words), *words), labels


def build(image, symbols):
    checked = audit.audit(image, symbols)
    body, labels = program()
    entry = struct.pack('<I', branch(ENTRY, CODE_START))
    return ({
        'schema': 1, 'kind': 'smp31f_original_vector_first_recorder',
        'native_deployment_ready': False, 'entry_authorized': False,
        'input_image_sha256': checked['image_sha256'],
        'input_symbol_sha256': checked['symbol_sha256'],
        'source_sha256': hashlib.sha256((HERE / 'recorder.S').read_bytes()).hexdigest(),
        'entry_offset': hex(ENTRY), 'resume_offset': hex(RESUME),
        'recorder_offset': hex(CODE_START), 'recorder_bytes': len(body),
        'recorder_sha256': hashlib.sha256(body).hexdigest(),
        'entry_original_word': hex(ORIGINAL_MOV),
        'entry_branch_word': hex(struct.unpack('<I', entry)[0]),
        'record_range': [hex(RECORD), hex(RECORD_END)],
        'record_fields': {'phase': 0, 'current_el': 8, 'mpidr_low24': 16,
                          'sctlr_selected_el': 24},
        'phase_meaning': {'0': 'not_observed', '1': 'entry_marker_before_system_reads',
                          '2': 'unfiltered_identity_recorded', '3': 'current_el_recorded',
                          '4': 'register_sample_complete', '255': 'unsupported_current_el'},
        'clobbers': ['x0', 'x8', 'NZCV'], 'x9_replayed': True,
        'sp_changed': False, 'lr_changed': False,
        'ordinary_cpu1_stack_top_offset': '0x178000',
        'labels': {name: hex(value) for name, value in labels.items()},
        'layout_audit': checked['layout_audit'], 'entry_audit': checked,
        'native_execution': 'NOT RUN'}, body, entry)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.image.read_bytes(), args.symbols.read_bytes())[0], sort_keys=True))
