#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline exact-image, encoder and injected fault-prefix tests."""
import argparse
import importlib.util
from pathlib import Path
import struct
import unittest

HERE = Path(__file__).resolve().parent
def load(name):
    spec = importlib.util.spec_from_file_location('_31l_test_'+name, HERE/(name+'.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
builder, audit, model = map(load, ('builder', 'audit', 'model'))
IMAGE = SYMBOLS = None
HELPER = 0x10004000000


class PrefixTests(unittest.TestCase):
    def test_fixed_sizes_locations_destinations(self):
        for kind in builder.CODE:
            body, labels = builder.program(kind, HELPER)
            self.assertEqual(len(body), 60)
            self.assertLess(builder.CODE[kind]+len(body), builder.CODE[kind]+0x100)
            self.assertEqual(labels['first_store'], builder.CODE[kind]+20)
            self.assertEqual(labels['first_mrs'], builder.CODE[kind]+28)
            self.assertEqual(model.run(kind)['branch_destination'], builder.RESUME[kind])
    def test_hooks(self):
        self.assertEqual(builder.branch(0, 0xc00), 0x14000300)
        self.assertEqual(builder.branch(0x800, 0xd00), 0x14000140)
    def test_full_address_construction(self):
        for helper in (0x4000, 0xffffc000, 0x100000000, 0x800000000,
                       0x10004000000, (1 << 41)-0x8000):
            for kind in builder.CODE:
                with self.subTest(helper=helper, kind=kind):
                    state = model.run(kind, helper)
                    address = helper + builder.RECORD[kind]
                    self.assertEqual(state['registers'][8], address)
                    self.assertEqual(state['memory'][address], 2)
                    self.assertEqual(state['memory'][address+8], 0x40001)
                    self.assertTrue(all(address <= at < address+64 for at, _ in state['stores']))
    def test_invalid_helper_and_kind(self):
        for helper in (None, True, 0, -0x4000, 1, HELPER+8, (1 << 41)-0x4000, 1 << 64):
            with self.assertRaisesRegex(ValueError, 'normal_helper_address'):
                builder.program('vector', helper)
        for kind in (None, True, 'VECTOR', '', [], {}):
            with self.assertRaisesRegex(ValueError, 'normal_prefix_kind'):
                builder.program(kind, HELPER)
    def test_first_store_precedes_mrs(self):
        result = model.run(halt_before=7)
        self.assertEqual(result['published_phases'], [1])
        self.assertEqual(result['system_reads'], [])
    def test_first_store_fault_prevents_device_branch(self):
        result = model.run(halt_before=5)
        self.assertFalse(any(result['memory'].values()))
        self.assertFalse(result['stores'])
        self.assertIsNone(result['branch_destination'])
    def test_mrs_trap_preserves_unidentified_phase1(self):
        result = model.run(halt_before=7)
        self.assertEqual(result['memory'][HELPER+0x1000], 1)
        self.assertEqual(result['memory'][HELPER+0x1008], 0)
        self.assertIsNone(result['branch_destination'])
    def test_phase2_not_branch_proof(self):
        result = model.run(halt_before=13)
        self.assertEqual(result['memory'][HELPER+0x1000], 2)
        self.assertIsNone(result['branch_destination'])
        self.assertFalse(result['existing_recorder_executed'])
    def test_fault_before_every_instruction(self):
        for kind in builder.CODE:
            address = HELPER+builder.RECORD[kind]
            for halt in range(16):
                with self.subTest(kind=kind, halt=halt):
                    result = model.run(kind, halt_before=halt)
                    expected_phase = 0 if halt <= 5 else (1 if halt <= 12 else 2)
                    self.assertEqual(result['memory'][address], expected_phase)
                    self.assertEqual(result['memory'][address+8], 0 if halt <= 9 else 0x40001)
                    self.assertEqual(result['branch_destination'],
                                     builder.RESUME[kind] if halt == 15 else None)
                    self.assertTrue(result['incoming_x0_retained'])
                    self.assertEqual(result['lr'], result['original_lr'])
                    self.assertEqual(result['sp'], 0x70000000)
                    self.assertEqual(result['nzcv'], 0xa)
                    self.assertTrue(set(range(31))-{8, 9} <= set(result['untouched_registers']))
    def test_dirty_stores_remain_invisible_despite_dsb(self):
        result = model.run(invisible_stores=True)
        self.assertEqual(result['barriers'], 3)
        self.assertFalse(any(result['memory'].values()))
        self.assertEqual(result['private_memory'][HELPER+0x1000], 2)
        self.assertEqual(result['branch_destination'], 0xa00)
        self.assertFalse(result['hardware_visibility_proven'])
    def test_identity_low24_and_wrong_core_remain_distinct(self):
        for mpidr in (0x1234567800040001, 0x40000, 0x10200, 0xffffff):
            result = model.run(mpidr=mpidr)
            self.assertEqual(result['memory'][HELPER+0x1008], mpidr & 0xffffff)
            self.assertEqual(result['memory'][HELPER+0x1000], 2)
    def test_registers_and_canaries(self):
        result = model.run(incoming_x0=0x123abc789)
        self.assertEqual(len(result['untouched_registers']), 29)
        self.assertEqual(result['registers'][0], 0x123abc789)
        self.assertTrue(all(result['memory'][HELPER+0x1000+off] == 0 for off in range(16, 64, 8)))
    def test_all_instruction_single_bit_mutants_refused(self):
        for kind in builder.CODE:
            original, _ = builder.program(kind, HELPER)
            for bit in range(len(original)*8):
                mutant = bytearray(original)
                mutant[bit//8] ^= 1 << (bit % 8)
                with self.assertRaisesRegex(ValueError, 'exact_original'):
                    model.run(kind, body=bytes(mutant))
    def test_no_forbidden_instruction_classes(self):
        for kind in builder.CODE:
            words = struct.unpack('<15I', builder.program(kind, HELPER)[0])
            self.assertFalse(any(word & 0xfff00000 == 0xd5100000 for word in words))
            self.assertFalse(any(word & 0xfc000000 == 0x94000000 for word in words))
            self.assertNotIn(0xd65f03c0, words)
            self.assertNotIn(0xd503205f, words)
    def test_invalid_model_premises(self):
        for halt in (-1, 16, True, '7'):
            with self.assertRaisesRegex(ValueError, 'invalid_fault_index'):
                model.run(halt_before=halt)
        for value in (None, 1, 'false'):
            with self.assertRaisesRegex(ValueError, 'invalid_visibility_premise'):
                model.run(invisible_stores=value)
        for value in (-1, True, 1 << 64):
            with self.assertRaisesRegex(ValueError, 'invalid_mpidr'):
                model.run(mpidr=value)


class LayoutTests(unittest.TestCase):
    def fixture(self):
        image = bytearray(0x8cd98)
        for offset in range(0x84d10, 0x8cd98, 24):
            struct.pack_into('<QQQ', image, offset, 0x100000, 1027, 0x100000)
        return image
    def test_zero_padding_and_bounded_disclaimer(self):
        result = audit.region_audit(self.fixture())
        self.assertFalse(result['computed_reference_proof'])
        self.assertFalse(result['symbol_check_performed'])
        self.assertEqual(result['direct_references'], 0)
    def test_nonzero_padding_refused(self):
        for offset in (0xc00, 0xcff, 0xd00, 0xdff):
            image = self.fixture()
            image[offset] = 1
            with self.assertRaisesRegex(ValueError, 'normal_prefix_not_zero'):
                audit.region_audit(image)
    def test_allocated_symbol_refused(self):
        with self.assertRaisesRegex(ValueError, 'normal_prefix_symbol'):
            audit.region_audit(self.fixture(), [(0xd00, 'T', 'occupied')])
    def test_relocation_target_or_addend_refused(self):
        for target, addend in ((0xc00, 0x100000), (0x100000, 0xd00)):
            image = self.fixture()
            struct.pack_into('<QQQ', image, 0x84d10, target, 1027, addend)
            with self.assertRaisesRegex(ValueError, 'normal_prefix_relocation'):
                audit.region_audit(image)
    def test_direct_branch_and_literal_refused(self):
        for target in (0xc00, 0xd3c):
            for instruction in (builder.branch(0x2000, target),
                                0x58000000 | (((target-0x2000)//4 & 0x7ffff) << 5)):
                image = self.fixture()
                struct.pack_into('<I', image, 0x2000, instruction)
                with self.assertRaisesRegex(ValueError, 'normal_prefix_direct_reference'):
                    audit.region_audit(image)
    def test_adjacent_adrp_add_refused(self):
        image = self.fixture()
        struct.pack_into('<II', image, 0x2000, builder.audit.previous.previous.adrp(0x2000, 0xd00),
                         0x91000000 | (0xd00 << 10))
        with self.assertRaisesRegex(ValueError, 'normal_prefix_direct_reference'):
            audit.region_audit(image)
    def test_helper_region_ownership_geometry(self):
        # Published existing helper code ends at +0x210; allocation is retained16KiB.
        spans = [(0, 0x210), (0x1000, 0x1040), (0x1080, 0x10c0), (0x1100, 0x1140)]
        self.assertTrue(all(0 <= lo < hi <= 0x4000 for lo, hi in spans))
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])))
        self.assertTrue(all(start % 128 == 0 for start in (0x1000, 0x1080, 0x1100)))
    def test_exact_image_when_supplied(self):
        if IMAGE is None:
            self.skipTest('pinned image not supplied')
        result = builder.build(IMAGE, SYMBOLS)
        self.assertEqual(result['entry_audit']['symbol_mode'],
                         'full_symbols' if SYMBOLS is not None else 'reviewed_layout_only')
        self.assertFalse(result['native_deployment_ready'])
        self.assertEqual(result['native_execution'], 'NOT RUN')
    def test_exact_image_mutants_refused_when_supplied(self):
        if IMAGE is None:
            self.skipTest('pinned image not supplied')
        for offset in (0, 0x800, 0xc00, 0xd00, 0xdff, len(IMAGE)-1):
            image = bytearray(IMAGE)
            image[offset] ^= 1
            with self.assertRaisesRegex(ValueError, 'image_digest'):
                builder.build(bytes(image), SYMBOLS)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--symbols', type=Path)
    args, rest = parser.parse_known_args()
    IMAGE = args.image.read_bytes() if args.image else None
    SYMBOLS = args.symbols.read_bytes() if args.symbols else None
    unittest.main(argv=[__file__]+rest)
