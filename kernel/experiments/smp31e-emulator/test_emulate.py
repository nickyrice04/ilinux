#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit tests and required exact-retained-image regressions; no native calls."""
import argparse
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('entry_emulator', Path(__file__).with_name('emulate.py'))
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
IMAGE = SYMBOLS = None


def machine(**kwargs):
    mem = e.synthetic_memory(IMAGE, **kwargs)
    return e.Machine(IMAGE, mem, 4, e.CPU1)


class RetainedImage(unittest.TestCase):
    def test_all_eight_production_paths(self):
        expected = {
            'table_miss': (e.FALLBACK_TOP, 0x974, 186),
            'table_hit': (e.DEDICATED_TOP, 0x974, 35),
            'matching_zero_stack': (e.FALLBACK_TOP, 0x974, 36),
            'el2_miss': (e.FALLBACK_TOP, 0x974, 186),
            'el3_shared': (e.FALLBACK_TOP, 0x97c, 20),
            'mpidr_high_bits': (e.DEDICATED_TOP, 0x974, 35),
            'last_slot_hit': (e.DEDICATED_TOP, 0x974, 185),
            'other_entry': (e.FALLBACK_TOP, 0x974, 186),
        }
        for case, (top, lr, steps) in expected.items():
            with self.subTest(case=case):
                r = e.simulate(IMAGE, SYMBOLS, case, include_trace=True)
                self.assertEqual(r['first_frame'], {
                    'entry_sp_offset': top, 'frame_offset': top - 32,
                    'lr_slot_from_entry_sp': -24, 'saved_lr_offset': lr})
                self.assertEqual(r['steps'], steps)
                self.assertEqual(r['interpreted_stores'], 1)
                self.assertEqual(r['trace'][-1]['instruction'], 'stp_pre_first_frame')
                self.assertEqual(r['trace'][-1]['offset'], '0x328e0')
                self.assertEqual(r['native_execution'], 'NOT RUN')
                self.assertFalse(r['hardware_model'])

    def test_production_store_has_exact_bytes_and_canary_boundary(self):
        m = machine()
        r = m.run()
        address = e.BASE + e.FALLBACK_TOP - 32
        self.assertEqual(m.memory.read(address, 16),
                         struct.pack('<QQ', 0x2929292929292929, e.BASE + 0x974))
        self.assertEqual(m.memory.read(address - 16, 16), bytes(16))
        self.assertEqual(m.memory.read(address + 16, 16), bytes(16))
        self.assertEqual(r['lr_slot_from_entry_sp'], -24)
        self.assertEqual(m.pc - e.BASE, 0x328e4)
        with self.assertRaisesRegex(e.Refused, 'instruction_scope'):
            m.step()  # The C body is outside the implemented model.

    def test_corrupted_inputs_refused_before_interpretation(self):
        image = bytearray(IMAGE)
        image[0x900] ^= 1
        for bad_image, bad_symbols, reason in (
                (bytes(image), SYMBOLS, 'image_digest'),
                (IMAGE[:-1], SYMBOLS, 'image_digest'),
                (IMAGE, (SYMBOLS or b'') + b'\n', 'symbol_digest')):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(e.Refused, reason):
                    e.simulate(bad_image, bad_symbols)

    def test_unknown_case_refused(self):
        with self.assertRaisesRegex(e.Refused, 'unknown_case'):
            e.simulate(IMAGE, SYMBOLS, 'native')

    def test_absent_symbols_report_reviewed_layout_only(self):
        r = e.simulate(IMAGE)
        self.assertEqual(r['symbol_validation'], 'reviewed_layout_only')
        self.assertIsNone(r['symbol_sha256'])
        self.assertEqual(r['reviewed_symbol_sha256'], e.SYMBOL_SHA)
        if SYMBOLS is not None:
            self.assertEqual(e.simulate(IMAGE, SYMBOLS)['symbol_validation'],
                             'full_symbol_digest')

    def test_step_bound_and_exact_limit(self):
        for limit in (0, 4097, True, 1.5):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(e.Refused, 'step_bound'):
                    machine().run(limit)
        with self.assertRaisesRegex(e.Refused, 'step_limit'):
            machine().run(185)
        self.assertEqual(machine().run(186)['saved_lr_offset'], 0x974)
        self.assertEqual(machine().run(4096)['saved_lr_offset'], 0x974)

    def test_bad_identity_and_exception_level_refused(self):
        for mpidr in (0, 0x40000, 0x40002, -1, 1 << 64, True):
            with self.subTest(mpidr=mpidr):
                with self.assertRaises(e.Refused):
                    e.Machine(IMAGE, e.synthetic_memory(IMAGE), 4, mpidr)
        with self.assertRaisesRegex(e.Refused, 'cpu1_identity'):
            e.Machine(IMAGE, e.synthetic_memory(IMAGE), 4, 0x140001)
        for el in (0, 1, 5, 16, 4.0, True):
            with self.subTest(el=el):
                with self.assertRaisesRegex(e.Refused, 'current_el'):
                    e.Machine(IMAGE, e.synthetic_memory(IMAGE), el, e.CPU1)

    def test_unmapped_stack_refused_without_store(self):
        for top in (0, e.FALLBACK_BOTTOM, e.FALLBACK_TOP + 16, 0x700000):
            m = machine(fallback_top=top)
            with self.subTest(top=top):
                with self.assertRaisesRegex(e.Refused, 'memory_unmapped'):
                    m.run()
                self.assertEqual(m.memory.writes, [])

    def test_misaligned_stack_refused(self):
        m = machine(fallback_top=e.FALLBACK_TOP - 8)
        with self.assertRaisesRegex(e.Refused, 'stack_alignment'):
            m.run()
        self.assertEqual(m.memory.writes, [])

    def test_first_pair_store_is_atomic_at_model_boundary(self):
        m = machine(fallback_bytes=16)
        with self.assertRaisesRegex(e.Refused, 'memory_unmapped'):
            m.run()
        self.assertEqual(m.sp, e.BASE + e.FALLBACK_TOP)
        self.assertEqual(m.memory.writes, [])
        self.assertEqual(m.memory.read(e.BASE + e.FALLBACK_TOP - 16, 16), bytes(16))

    def test_table_stack_is_not_trusted_or_mapped_automatically(self):
        m = machine(table_entries=((1, e.CPU1, 0x180000),))
        with self.assertRaisesRegex(e.Refused, 'memory_unmapped'):
            m.run()
        self.assertEqual(m.memory.writes, [])

    def test_table_geometry_refused(self):
        for entries in (((32, e.CPU1, 0),), ((-1, e.CPU1, 0),),
                        ((1, e.CPU1, 0), (1, e.CPU1, 0)),
                        ((1, 1 << 64, 0),), ((1, e.CPU1, -1),)):
            with self.subTest(entries=entries):
                with self.assertRaises(e.Refused):
                    e.synthetic_memory(IMAGE, entries)


class DecoderAndMemory(unittest.TestCase):
    def test_public_error_omits_paths_bytes_and_external_messages(self):
        errors = (OSError('PRIVATE_INPUT_PATH'),
                  UnicodeDecodeError('ascii', b'PRIVATE_INPUT_BYTES\xff', 0, 1,
                                     'PRIVATE_INPUT_REASON'),
                  ValueError('PRIVATE_INPUT_VALUE'))
        for error in errors:
            with self.subTest(error=type(error).__name__):
                self.assertEqual(e.public_error(error), type(error).__name__)
                self.assertNotIn('PRIVATE_INPUT', e.public_error(error))
        self.assertEqual(e.public_error(e.Refused('image_digest')), 'image_digest')

    def with_word(self, word):
        image = bytearray(IMAGE)
        struct.pack_into('<I', image, 0x8fc, word)
        # Intentional synthetic decoder-only input, not simulate() bypass.
        return e.Machine(bytes(image), e.synthetic_memory(IMAGE), 4, e.CPU1)

    def test_unknown_instruction_and_sysreg_refuse(self):
        for word in (0, 0xffffffff, 0xd5380408, 0xd4000002):
            with self.subTest(word=hex(word)):
                with self.assertRaisesRegex(e.Refused, 'instruction_unsupported'):
                    self.with_word(word).step()

    def test_and_immediate_sp_destination_is_refused(self):
        m = self.with_word(0x927cec1f)  # AND SP,X0,#-16, outside pinned path.
        m.x[0], m.sp = e.MASK64, e.BASE + e.FALLBACK_TOP
        with self.assertRaisesRegex(e.Refused, 'and_sp_unsupported'):
            m.step()
        self.assertEqual(m.sp, e.BASE + e.FALLBACK_TOP)
        self.assertEqual(m.trace, [])

    def test_and_immediate_wsp_destination_is_refused(self):
        m = self.with_word(0x121c6c1f)  # AND WSP,W0,#-16, outside pinned path.
        m.x[0], m.sp = e.MASK64, e.BASE + e.FALLBACK_TOP
        with self.assertRaisesRegex(e.Refused, 'and_sp_unsupported'):
            m.step()
        self.assertEqual(m.sp, e.BASE + e.FALLBACK_TOP)
        self.assertEqual(m.trace, [])

    def test_only_explicit_nop_barrier_are_events(self):
        for word, name in ((0xd503201f, 'nop'), (0xd5033f9f, 'dsb_sy_model_event')):
            m = self.with_word(word)
            m.step()
            self.assertEqual(m.trace[-1]['instruction'], name)
            self.assertEqual(m.memory.writes, [])
        with self.assertRaisesRegex(e.Refused, 'instruction_unsupported'):
            self.with_word(0xd503205f).step()  # WFE cannot be faked as NOP.

    def test_no_instruction_fetch_outside_scope(self):
        m = machine()
        for offset in (0x8fb, 0x97c, 0x9c0, 0x328e4, -4):
            m.pc = e.BASE + offset
            with self.subTest(offset=offset):
                with self.assertRaises(e.Refused):
                    m.fetch()

    def test_sub_flags(self):
        m = machine()
        for lhs, rhs, result, flags in ((1, 1, 0, 6), (0, 1, -1, 8),
                                        (2, 1, 1, 2),
                                        (1 << 63, 1, (1 << 63) - 1, 3)):
            m.flags_sub(lhs, rhs, result, 64)
            self.assertEqual(m.nzcv, flags)

    def test_logical_immediate_masks_and_reserved(self):
        self.assertEqual(e.logical_mask(1, 1, 0, 23), 0xffffff)
        self.assertEqual(e.logical_mask(1, 1, 1, 0), 1 << 63)
        self.assertEqual(e.logical_mask(0, 0, 0, 7), 0xff)
        self.assertEqual(e.logical_mask(1, 0, 0, 39), 0x00ff00ff00ff00ff)
        for fields in ((0, 1, 0, 0), (1, 1, 0, 63), (0, 0, 0, 63)):
            with self.assertRaises(e.Refused):
                e.logical_mask(*fields)

    def test_zero_register_and_word_write(self):
        m = machine()
        m.set_reg(0, e.MASK64, width=32)
        self.assertEqual(m.reg(0), 0xffffffff)
        m.set_reg(31, e.MASK64)
        self.assertEqual(m.reg(31), 0)
        self.assertEqual(m.sp, 0)

    def test_memory_permissions_bounds_overflow(self):
        mem = e.Memory()
        mem.map(0x100, bytes(16), False, 'readonly')
        for addr, size in ((0xff, 8), (0x108, 16), (e.MASK64, 8)):
            with self.subTest(addr=addr):
                with self.assertRaises(e.Refused):
                    mem.read(addr, size)
        with self.assertRaisesRegex(e.Refused, 'memory_readonly'):
            mem.write(0x100, b'12345678')
        with self.assertRaisesRegex(e.Refused, 'map_overlap'):
            mem.map(0x108, bytes(8), True, 'overlap')
        with self.assertRaisesRegex(e.Refused, 'memory_alignment'):
            mem.read64(0x101)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path)
    args, remaining = parser.parse_known_args()
    IMAGE = args.image.read_bytes()
    SYMBOLS = args.symbols.read_bytes() if args.symbols is not None else None
    e.verify(IMAGE, SYMBOLS)
    unittest.main(argv=['test_emulate.py'] + remaining)
