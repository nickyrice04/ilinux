#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline original/patched instruction equivalence for the proposed recorder.

The original full image and symbol pins are mandatory. Only the independently
assembled, fixed recorder proposal is overlaid in an in-memory copy. No input
is executed by the host and no output binary, device or transport is opened.
"""
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


e = load('_recorder_entry_model', HERE / 'emulate.py')
builder = load('_recorder_builder', HERE.parent / 'smp31e-entry' / 'build_recorder.py')
CODE_START, CODE_BYTES = 0xa00, 204
RECORD, RECORD_BYTES = 0x90a40, 64
RECORDER_SHA = '9fa1f68b849a7049481cb1a83e645ccd43ca61a0d5df11d6bf7ca76dffd00335'
HOOK = 0x14000041
FIELDS = {0: 'phase', 8: 'current_el', 16: 'mpidr_low24', 24: 'sctlr_selected_el'}
SCTLR_MRS = {0xd5381000: 4, 0xd53c1000: 8, 0xd53e1000: 12}
# Deliberately synthetic, different values. Never read from this Mac.
SCTLR_VALUES = {4: 0x1005, 8: 0x2001, 12: 0x3000}
CHECKPOINTS = ((0x900, False, False), (0x904, False, False),
               (0x908, True, False), (0x90c, True, True))
CASES = {
    'cpu1_el1': (4, e.CPU1, False),
    'cpu1_el2': (8, e.CPU1, False),
    'cpu1_el3': (12, e.CPU1, False),
    'cpu1_unsupported_el0': (0, e.CPU1, False),
    'cpu1_unsupported_reserved_el': (16, e.CPU1, False),
    'other_cpu_filtered': (4, 0x40002, False),
    'zero_mpidr_filtered': (8, 0, False),
    'cpu1_high_mpidr_flags': (4, 0x80040001, False),
    'cpu1_el1_sctlr_fault': (4, e.CPU1, True),
    'cpu1_el2_sctlr_fault': (8, e.CPU1, True),
    'cpu1_el3_sctlr_fault': (12, e.CPU1, True),
}


class Prepared:
    def __init__(self, original, derived, plan):
        self.original, self.derived, self.plan = original, derived, plan


def prepare(image, symbols):
    e.need(symbols is not None, 'full_symbols_required')
    e.verify(image, symbols)
    plan, recorder, entry = builder.build(image, symbols)
    e.need(len(recorder) == CODE_BYTES and
           hashlib.sha256(recorder).hexdigest() == RECORDER_SHA, 'recorder_digest')
    e.need(entry == struct.pack('<I', HOOK), 'entry_branch_binding')
    e.need(plan['entry_offset'] == '0x8fc' and plan['resume_offset'] == '0x900' and
           plan['recorder_offset'] == hex(CODE_START) and
           plan['record_range'] == [hex(RECORD), hex(RECORD + RECORD_BYTES)],
           'overlay_binding')
    e.need(image[CODE_START:CODE_START + CODE_BYTES] == bytes(CODE_BYTES),
           'overlay_nonzero')
    derived = bytearray(image)
    derived[0x8fc:0x900] = entry
    derived[CODE_START:CODE_START + CODE_BYTES] = recorder
    # Independently constrain every changed byte to the two fixed intervals.
    e.need(derived[:0x8fc] == image[:0x8fc] and
           derived[0x900:CODE_START] == image[0x900:CODE_START] and
           derived[CODE_START + CODE_BYTES:] == image[CODE_START + CODE_BYTES:],
           'overlay_changed_other_bytes')
    return Prepared(image, bytes(derived), plan)


def memory(image):
    mem = e.synthetic_memory(image)
    mem.map(e.BASE + RECORD, bytes(32) + bytes([0xa5]) * 32, True,
            'original_recorder_fields')
    return mem


class RecorderMachine(e.Machine):
    """Additional exact recorder instruction forms; no generic device model."""
    def __init__(self, image, mem, current_el, mpidr, fault=False):
        # Base model's public CPU1-only entry contract is unchanged. This
        # separate model explicitly tests the recorder's filtering paths.
        super().__init__(image, mem, 4, e.CPU1)
        e.integer(current_el, 0, 16, 'synthetic_current_el')
        e.need(current_el in (0, 4, 8, 12, 16), 'synthetic_current_el')
        e.integer(mpidr, 0, e.MASK64, 'synthetic_mpidr')
        e.need(type(fault) is bool, 'synthetic_fault')
        self.current_el, self.mpidr, self.fault = current_el, mpidr, fault
        self.sctlr_attempts = 0
        self.sctlr_completed = 0
        self.phase_events = []
        self.record_events = []

    def fetch(self):
        offset = self.pc - self.base
        if CODE_START <= offset < CODE_START + CODE_BYTES:
            e.need(offset % 4 == 0 and offset + 4 <= len(self.image), 'recorder_fetch')
            return offset, struct.unpack_from('<I', self.image, offset)[0]
        return super().fetch()

    def step(self):
        offset, insn = self.fetch()
        in_recorder = CODE_START <= offset < CODE_START + CODE_BYTES
        rd, rn = insn & 31, (insn >> 5) & 31
        kind = None
        if insn & 0x7f800000 == 0x72800000:  # MOVK
            e.need(in_recorder, 'recorder_instruction_scope')
            width = 64 if insn >> 31 else 32
            shift = ((insn >> 21) & 3) * 16
            e.need(shift < width, 'movk_reserved')
            value = ((self.reg(rd) & ~(0xffff << shift)) |
                     (((insn >> 5) & 0xffff) << shift))
            self.set_reg(rd, value, width)
            kind = 'movk'
        elif insn & 0xfffffc00 == 0xd3405c00:  # UBFX Xd,Xn,#0,#24
            e.need(in_recorder, 'recorder_instruction_scope')
            self.set_reg(rd, self.reg(rn) & 0xffffff)
            kind = 'ubfx_low24'
        elif insn & 0xffc00000 == 0xf9000000:  # STR Xt,[Xn,#imm12*8]
            e.need(in_recorder and rn != 31, 'recorder_store_scope')
            address = self.reg(rn) + ((insn >> 10) & 0xfff) * 8
            field = address - (self.base + RECORD)
            e.need(field in FIELDS, 'record_write_not_allowlisted')
            value = self.reg(rd)
            if field == 0:
                e.need(value in (1, 2, 3, 255), 'record_phase_value')
            self.memory.write(address, struct.pack('<Q', value))
            self.record_events.append(FIELDS[field])
            if field == 0:
                self.phase_events.append(value)
            kind = 'str_recorder_field'
        elif insn & 0xffffffe0 in SCTLR_MRS:
            e.need(in_recorder, 'recorder_instruction_scope')
            level = SCTLR_MRS[insn & 0xffffffe0]
            e.need(level == self.current_el, 'selected_sctlr_level_mismatch')
            self.sctlr_attempts += 1
            if self.fault:
                # End at this synthetic fault; no exception-vector semantics
                # or return-to-original-path behavior is assumed.
                raise e.Refused('modeled_sctlr_read_fault')
            self.set_reg(rd, SCTLR_VALUES[level])
            self.sctlr_completed += 1
            kind = 'mrs_selected_sctlr'
        if kind is None:
            super().step()
        else:
            self.trace.append({'offset': hex(offset), 'instruction': kind})
            self.pc += 4


def seed(machine, nzcv):
    e.integer(nzcv, 0, 15, 'synthetic_nzcv')
    machine.x = [((index + 1) * 0x0101010101010101) & e.MASK64
                 for index in range(31)]
    machine.sp = e.BASE + e.FALLBACK_TOP
    machine.nzcv = nzcv


def advance(machine, stop, max_steps):
    e.integer(max_steps, 1, 4096, 'step_bound')
    while machine.pc != e.BASE + stop:
        e.need(len(machine.trace) < max_steps, 'step_limit')
        machine.step()


def equivalent(original, patched, include_x8, include_flags):
    indices = [i for i in range(31) if include_x8 or i != 8]
    return (all(original.x[i] == patched.x[i] for i in indices) and
            original.sp == patched.sp and
            (not include_flags or original.nzcv == patched.nzcv))


def run_case(prepared, case, max_steps=256, initial_nzcv=10):
    e.need(case in CASES, 'unknown_recorder_case')
    current_el, mpidr, fault = CASES[case]
    # Original path can be modeled with the same synthetic values even when
    # they would fail the stricter CPU1-only public entry model's intake.
    original = RecorderMachine(prepared.original, memory(prepared.original),
                               current_el, mpidr, False)
    patched = RecorderMachine(prepared.derived, memory(prepared.derived),
                              current_el, mpidr, fault)
    seed(original, initial_nzcv)
    seed(patched, initial_nzcv)
    checkpoints, refusal = [], None
    for stop, x8_live, flags_live in CHECKPOINTS:
        advance(original, stop, max_steps)
        try:
            advance(patched, stop, max_steps)
        except e.Refused as error:
            if str(error) != 'modeled_sctlr_read_fault' or not fault:
                raise
            refusal = 'modeled_sctlr_read_fault'
            break
        same = equivalent(original, patched, x8_live, flags_live)
        e.need(same, 'live_state_not_equivalent')
        checkpoints.append({'checkpoint_offset': hex(stop), 'live_state_equal': same,
                            'x8_included': x8_live, 'nzcv_included': flags_live,
                            'sp_lr_and_other_registers_equal': True})
    record = {field: patched.memory.read64(e.BASE + RECORD + offset)
              for offset, field in FIELDS.items()}
    cpu1 = mpidr & 0xffffff == e.CPU1
    known_el = current_el in SCTLR_VALUES
    expected_phase = 0 if not cpu1 else (255 if not known_el else (2 if fault else 3))
    expected_events = [] if not cpu1 else ([1, 255] if not known_el else
                                         ([1, 2] if fault else [1, 2, 3]))
    e.need(record['phase'] == expected_phase and patched.phase_events == expected_events,
           'record_phase_progression')
    e.need(record['mpidr_low24'] == (e.CPU1 if cpu1 else 0), 'record_mpidr')
    e.need(record['current_el'] == (current_el if cpu1 else 0), 'record_current_el')
    expected_sctlr = SCTLR_VALUES[current_el] if cpu1 and known_el and not fault else 0
    e.need(record['sctlr_selected_el'] == expected_sctlr, 'record_sctlr')
    e.need(patched.memory.read(e.BASE + RECORD + 32, 16) == bytes([0xa5]) * 16 and
           patched.memory.read(e.BASE + RECORD + 48, 16) == bytes([0xa5]) * 16,
           'record_canary_changed')
    expected_reads = 1 if cpu1 and known_el else 0
    e.need(patched.sctlr_attempts == expected_reads and
           patched.sctlr_completed == (expected_reads if not fault else 0),
           'sctlr_read_count')
    e.need(bool(refusal) == fault, 'fault_outcome')
    e.need(all(label == 'original_recorder_fields'
               for _, _, label in patched.memory.writes), 'nonrecord_write')
    return {'case': case,
            'result': 'MODELED_READ_FAULT_STOP' if fault else 'MODELED_REPLAY_EQUIVALENT',
            'checkpoints': checkpoints, 'phase_events': patched.phase_events,
            'record_write_fields': patched.record_events,
            'record_values_match_synthetic_inputs': True,
            'record_tail_canaries_intact': True,
            'sctlr_reads_attempted': patched.sctlr_attempts,
            'sctlr_reads_completed': patched.sctlr_completed,
            'interpreted_steps': len(patched.trace), 'instruction_budget': max_steps,
            'exception_handler_modeled': False, 'physical_publication_modeled': False,
            'native_execution': 'NOT RUN'}


def check(image, symbols):
    prepared = prepare(image, symbols)
    return {'result': 'OFFLINE_RECORDER_EQUIVALENCE_PASS_NATIVE_HOLD',
            'original_image_sha256': e.IMAGE_SHA,
            'symbol_sha256': e.SYMBOL_SHA,
            'derived_image_sha256': hashlib.sha256(prepared.derived).hexdigest(),
            'recorder_sha256': RECORDER_SHA, 'recorder_bytes': CODE_BYTES,
            'scenarios': [run_case(prepared, case) for case in CASES],
            'native_execution': 'NOT RUN', 'native_deployment_ready': False,
            'entry_authorized': False, 'hardware_model': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path, required=True)
    args = parser.parse_args()
    try:
        for path in (args.image, args.symbols):
            e.need(path.is_file() and not path.is_symlink(), 'input_file')
        print(json.dumps(check(args.image.read_bytes(), args.symbols.read_bytes()),
                         sort_keys=True))
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({'result': 'OFFLINE_RECORDER_REFUSED_NATIVE_HOLD',
                          'reason': e.public_error(error), 'native_deployment_ready': False,
                          'native_execution': 'NOT RUN'}, sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
