"""Pinned-image path checks; caller supplies existing boot021 artifact."""
import argparse
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit31m', Path(__file__).with_name('audit.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
IMAGE = None


class Audit(unittest.TestCase):
    def setUp(self):
        if IMAGE is None:
            self.skipTest('pinned image not supplied')

    def test_exact_pinned_dispatch(self):
        out = m.verify_image(IMAGE)
        self.assertEqual(out['result'], 'PINNED_CIVAC_DISPATCH_AUDIT_PASS')
        self.assertEqual(out['cache_instructions_for_aligned64_bytes'], 1)
        self.assertFalse(out['temporary_exception_guard_change'])
        self.assertTrue(out['common_epilogue_restores_saved_guard'])
        self.assertTrue(out['required_runtime_got_check'])
        self.assertTrue(out['required_runtime_dispatch_table_check'])
        self.assertEqual(out['native_execution'], 'NOT RUN')

    def test_critical_word_mutants_rejected(self):
        for at in (m.CASE_TABLE_OFFSET, 0x2d460, 0x2d46c, m.EPILOGUE_OFFSET,
                   m.EPILOGUE_OFFSET+4, 0x2780c, 0x27810, m.GOT_OFFSET,
                   m.FEATURES_OFFSET+m.CYCLONE_FLAG_OFFSET):
            changed = bytearray(IMAGE)
            changed[at] ^= 1
            with self.subTest(at=hex(at)), self.assertRaisesRegex(ValueError, 'cache_path_image_digest'):
                m.verify_image(bytes(changed))

    def test_refuses_wrong_length_and_type(self):
        for image in (IMAGE[:-1], IMAGE+b'\x00', bytearray(IMAGE), None):
            with self.assertRaisesRegex(ValueError, 'cache_path_image_digest'):
                m.verify_image(image)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--image', type=Path)
    args, rest = parser.parse_known_args()
    IMAGE = args.image.read_bytes() if args.image else None
    unittest.main(argv=[__file__]+rest)
