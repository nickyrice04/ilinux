#!/usr/bin/env python3
"""Small synthetic checks of instruction/relocation refusal boundaries."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).with_name('audit.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class AuditTests(unittest.TestCase):
    def test_bl_signed_displacement(self):
        self.assertEqual(m.bl_target(struct.pack('<I', 0x97ffffff), 0), -4)
        self.assertEqual(m.bl_target(struct.pack('<I', 0x94000002), 0), 8)
        with self.assertRaisesRegex(ValueError, 'expected_BL'):
            m.bl_target(struct.pack('<I', 0x14000002), 0)

    def test_frames_are_preindex_or_explicit_sub(self):
        self.assertEqual(m.frame_size(struct.pack('<I', 0xa9be7bfd), 0), 32)
        self.assertEqual(m.frame_size(struct.pack('<III', 0xd10083ff, 0, 0xa9007bfd), 0), 32)
        with self.assertRaisesRegex(ValueError, 'unsupported_frame'):
            m.frame_size(struct.pack('<I', 0xd503201f), 0)
        with self.assertRaisesRegex(ValueError, 'unaligned_frame'):
            m.frame_size(struct.pack('<I', 0xa9bffbfd), 0)  # 8-byte allocation violates SP alignment

    def test_relocations_reject_stack_destination_or_pointer(self):
        names = {'_rela_start': 0, '_rela_end': 24}
        for destination, addend in [(m.STACK_BOTTOM, 0), (0, m.STACK_BOTTOM)]:
            with self.assertRaisesRegex(ValueError, 'stack_relocation'):
                m.relative_relocations(struct.pack('<QQQ', destination, 1027, addend), names)
        self.assertEqual(len(m.relative_relocations(
            struct.pack('<QQQ', 16, 1027, m.STACK_TOP), names)), 1)
        with self.assertRaisesRegex(ValueError, 'unsupported_relocation'):
            m.relative_relocations(struct.pack('<QQQ', 16, 0, 32), names)

    def test_adr_into_candidate_refuses(self):
        # ADR X0, #0x94000 at PC=0. This uses only an original synthetic word.
        immediate = m.STACK_BOTTOM
        instruction = (0x10000000 | ((immediate & 3) << 29) |
                       (((immediate >> 2) & 0x7ffff) << 5))
        names = {'_text_start': 0, '_text_size': 4}
        with self.assertRaisesRegex(ValueError, 'stack_direct_address'):
            m.direct_address_references(struct.pack('<I', instruction), names)
        self.assertEqual(m.direct_address_references(struct.pack('<I', 0xd503201f), names), [])


if __name__ == '__main__':
    unittest.main()
