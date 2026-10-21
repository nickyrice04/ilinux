#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact-derived recorder tests against synthetic state; never native calls."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('recorder_check', Path(__file__).with_name('recorder_check.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
e = r.e
IMAGE = SYMBOLS = None
PREPARED = None


class ExactRecorder(unittest.TestCase):
    def test_original_pins_and_precise_overlay(self):
        p = PREPARED
        self.assertEqual(p.original, IMAGE)
        self.assertEqual(p.derived[0x8fc:0x900], struct.pack('<I', 0x14000041))
        self.assertEqual(p.derived[:0x8fc], IMAGE[:0x8fc])
        self.assertEqual(p.derived[0x900:0xa00], IMAGE[0x900:0xa00])
        self.assertEqual(p.derived[0xacc:], IMAGE[0xacc:])
        self.assertEqual(len(p.derived), len(IMAGE))

    def test_full_symbols_mandatory_and_changed_input_refused(self):
        for image, symbols, reason in ((IMAGE, None, 'full_symbols_required'),
                                       (IMAGE[:-1], SYMBOLS, 'image_digest'),
                                       (IMAGE, SYMBOLS + b'\n', 'symbol_digest')):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(e.Refused, reason):
                    r.prepare(image, symbols)

    def test_changed_recorder_or_hook_refused(self):
        plan, code, hook = r.builder.build(IMAGE, SYMBOLS)
        bad = bytearray(code)
        bad[0] ^= 1
        for proposal, reason in (((plan, bytes(bad), hook), 'recorder_digest'),
                                ((plan, code, b'\0' * 4), 'entry_branch_binding')):
            with patch.object(r.builder, 'build', return_value=proposal):
                with self.assertRaisesRegex(e.Refused, reason):
                    r.prepare(IMAGE, SYMBOLS)

    def test_changed_overlay_layout_refused(self):
        plan, code, hook = r.builder.build(IMAGE, SYMBOLS)
        plan = dict(plan, recorder_offset='0xb00')
        with patch.object(r.builder, 'build', return_value=(plan, code, hook)):
            with self.assertRaisesRegex(e.Refused, 'overlay_binding'):
                r.prepare(IMAGE, SYMBOLS)

    def test_all_eleven_scenarios_have_explicit_outcomes(self):
        self.assertEqual(len(r.CASES), 11)
        for case, (el, mpidr, fault) in r.CASES.items():
            with self.subTest(case=case):
                row = r.run_case(PREPARED, case)
                cpu1 = mpidr & 0xffffff == e.CPU1
                expected = [] if not cpu1 else ([1, 255] if el not in (4, 8, 12)
                                               else ([1, 2] if fault else [1, 2, 3]))
                self.assertEqual(row['phase_events'], expected)
                self.assertEqual(len(row['checkpoints']), 0 if fault else 4)
                self.assertEqual(row['result'], 'MODELED_READ_FAULT_STOP' if fault
                                 else 'MODELED_REPLAY_EQUIVALENT')
                self.assertEqual(row['sctlr_reads_completed'],
                                 int(cpu1 and el in (4, 8, 12) and not fault))
                self.assertFalse(row['exception_handler_modeled'])
                self.assertFalse(row['physical_publication_modeled'])
                self.assertEqual(row['native_execution'], 'NOT RUN')

    def test_every_nzcv_pattern_preserves_before_first_use(self):
        for flags in range(16):
            for case in r.CASES:
                if r.CASES[case][2]:
                    continue
                with self.subTest(flags=flags, case=case):
                    row = r.run_case(PREPARED, case, initial_nzcv=flags)
                    self.assertTrue(row['checkpoints'][-1]['nzcv_included'])
                    self.assertTrue(row['checkpoints'][-1]['live_state_equal'])

    def test_checkpoint_liveness_masks(self):
        row = r.run_case(PREPARED, 'cpu1_el1')
        self.assertEqual([(x['checkpoint_offset'], x['x8_included'], x['nzcv_included'])
                          for x in row['checkpoints']],
                         [('0x900', False, False), ('0x904', False, False),
                          ('0x908', True, False), ('0x90c', True, True)])
        self.assertTrue(all(x['sp_lr_and_other_registers_equal'] for x in row['checkpoints']))

    def test_model_detects_wrong_replayed_mov(self):
        derived = bytearray(PREPARED.derived)
        # Last two words are the original MOV W0,'O' and B resume.
        at = r.CODE_START + r.CODE_BYTES - 8
        self.assertEqual(struct.unpack_from('<I', derived, at)[0], 0x528009e0)
        struct.pack_into('<I', derived, at, 0x52800a00)  # Synthetic wrong character.
        bad = r.Prepared(IMAGE, bytes(derived), PREPARED.plan)
        with self.assertRaisesRegex(e.Refused, 'live_state_not_equivalent'):
            r.run_case(bad, 'cpu1_el1')

    def test_bounded_steps_and_unknown_case(self):
        for limit in (0, 1, 4097, True):
            with self.subTest(limit=limit):
                with self.assertRaises(e.Refused):
                    r.run_case(PREPARED, 'cpu1_el1', max_steps=limit)
        with self.assertRaisesRegex(e.Refused, 'unknown_recorder_case'):
            r.run_case(PREPARED, 'enable_real_cpu')

    def test_sanitized_matrix_has_no_raw_synthetic_addresses(self):
        result = r.check(IMAGE, SYMBOLS)
        text = json.dumps(result)
        for value in (e.BASE, e.BASE + r.RECORD, e.BASE + e.FALLBACK_TOP,
                      0x2929292929292929):
            self.assertNotIn(str(value), text)
            self.assertNotIn(hex(value), text)
        self.assertFalse(result['entry_authorized'])
        self.assertFalse(result['native_deployment_ready'])
        self.assertFalse(result['hardware_model'])


class AddedDecoder(unittest.TestCase):
    def synthetic_word(self, word, el=4):
        image = bytearray(PREPARED.derived)
        struct.pack_into('<I', image, r.CODE_START, word)
        m = r.RecorderMachine(bytes(image), r.memory(IMAGE), el, e.CPU1)
        m.pc = e.BASE + r.CODE_START
        return m

    def test_movk_replaces_only_selected_halfword(self):
        m = self.synthetic_word(0xf2a00080)  # MOVK X0,#4,LSL#16
        m.x[0] = 0x1122334455667788
        m.step()
        self.assertEqual(m.x[0], 0x1122334400047788)
        self.assertEqual(m.trace[-1]['instruction'], 'movk')

    def test_ubfx_masks_high_mpidr_bits(self):
        m = self.synthetic_word(0xd3405d08)
        m.x[8] = 0xffffffffff040001
        m.step()
        self.assertEqual(m.x[8], e.CPU1)
        with self.assertRaisesRegex(e.Refused, 'instruction_unsupported'):
            self.synthetic_word(0xd3405908).step()  # A different width is unmodeled.

    def test_record_writes_reject_stack_mmio_and_unused_record_fields(self):
        for address in (e.BASE + e.FALLBACK_TOP - 16, e.BASE + r.RECORD + 32,
                        e.BASE + r.RECORD + 1, 0x280688000):
            m = self.synthetic_word(0xf9000008)  # STR X8,[X0]
            m.x[0], m.x[8] = address, 1
            with self.subTest(address=address):
                with self.assertRaisesRegex(e.Refused, 'record_write_not_allowlisted'):
                    m.step()
                self.assertEqual(m.memory.writes, [])

    def test_all_four_field_offsets_and_phase_values(self):
        for offset in (0, 8, 16, 24):
            m = self.synthetic_word(0xf9000008 | ((offset // 8) << 10))
            m.x[0], m.x[8] = e.BASE + r.RECORD, 1
            m.step()
            self.assertEqual(m.memory.read64(e.BASE + r.RECORD + offset), 1)
            self.assertEqual(m.record_events, [r.FIELDS[offset]])
        m = self.synthetic_word(0xf9000008)
        m.x[0], m.x[8] = e.BASE + r.RECORD, 4
        with self.assertRaisesRegex(e.Refused, 'record_phase_value'):
            m.step()

    def test_sctlr_read_level_must_match_synthetic_el(self):
        for word, level in ((0xd5381008, 4), (0xd53c1008, 8), (0xd53e1008, 12)):
            m = self.synthetic_word(word, level)
            m.step()
            self.assertEqual(m.x[8], r.SCTLR_VALUES[level])
            self.assertEqual((m.sctlr_attempts, m.sctlr_completed), (1, 1))
            wrong = self.synthetic_word(word, 8 if level == 4 else 4)
            with self.assertRaisesRegex(e.Refused, 'selected_sctlr_level_mismatch'):
                wrong.step()

    def test_no_unknown_register_or_privileged_write_support(self):
        for word in (0xd5380408, 0xd5181008, 0xffffffff):
            with self.subTest(word=hex(word)):
                with self.assertRaisesRegex(e.Refused, 'instruction_unsupported'):
                    self.synthetic_word(word).step()

    def test_fault_keeps_last_published_phase_and_never_resumes(self):
        m = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), 4, e.CPU1, True)
        r.seed(m, 10)
        original_sp, original_lr = m.sp, m.x[30]
        with self.assertRaisesRegex(e.Refused, 'modeled_sctlr_read_fault'):
            r.advance(m, 0x900, 256)
        self.assertEqual(m.memory.read64(e.BASE + r.RECORD), 2)
        self.assertEqual(m.memory.read64(e.BASE + r.RECORD + 24), 0)
        self.assertEqual((m.sp, m.x[30]), (original_sp, original_lr))
        self.assertEqual((m.sctlr_attempts, m.sctlr_completed), (1, 0))
        self.assertTrue(r.CODE_START <= m.pc - e.BASE < r.CODE_START + r.CODE_BYTES)

    def test_other_cpu_never_touches_record_even_with_fault_enabled(self):
        m = r.RecorderMachine(PREPARED.derived, r.memory(IMAGE), 4, 0x40002, True)
        r.seed(m, 10)
        r.advance(m, 0x900, 256)
        self.assertEqual(m.memory.writes, [])
        self.assertEqual(m.sctlr_attempts, 0)
        self.assertEqual(m.x[0], 79)

    def test_no_fetch_past_recorder_extent(self):
        m = self.synthetic_word(0xd503201f)
        m.pc = e.BASE + r.CODE_START + r.CODE_BYTES
        with self.assertRaisesRegex(e.Refused, 'instruction_scope'):
            m.fetch()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    IMAGE, SYMBOLS = args.image.read_bytes(), args.symbols.read_bytes()
    PREPARED = r.prepare(IMAGE, SYMBOLS)
    unittest.main(argv=['test_recorder_check.py'] + remaining)
