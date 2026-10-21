import importlib.util
from pathlib import Path
import struct
import unittest

s = importlib.util.spec_from_file_location('audit', Path(__file__).with_name('audit_boot021.py'))
a = importlib.util.module_from_spec(s)
s.loader.exec_module(a)


class AuditTests(unittest.TestCase):
    def test_layout_uses_cpu1_not_cpu0(self):
        result = a.layout(dict(a.EXPECTED))
        self.assertEqual(result['spin_record_offset'], '0x90250')
        self.assertEqual(result['reset_stack_record_offset'], '0x90020')
        self.assertEqual(result['dedicated_stack_bottom_offset'], '0x168000')
        self.assertEqual(result['dedicated_stack_top_offset'], '0x178000')

    def test_changed_or_missing_symbols_refused(self):
        for name in a.EXPECTED:
            for missing in (True, False):
                symbols = dict(a.EXPECTED)
                if missing:
                    del symbols[name]
                else:
                    symbols[name] += 4
                with self.subTest(name=name, missing=missing), self.assertRaises(ValueError):
                    a.layout(symbols)

    def test_branch_forward_and_negative(self):
        self.assertEqual(a.branch_target(struct.pack('<I', 0x1400023e), 0), 0x8f8)
        self.assertEqual(a.branch_target(struct.pack('<I', 0x97ffffff), 0, link=True), -4)

    def test_wrong_opcode_alignment_and_bounds(self):
        for data, offset, link in ((b'\0' * 4, 0, False), (b'\0' * 3, 0, False),
                (b'\0' * 8, 1, False), (struct.pack('<I', 0x14000000), 0, True),
                (b'\0' * 8, -4, False)):
            with self.subTest(offset=offset, link=link), self.assertRaises(ValueError):
                a.branch_target(data, offset, link)

    def test_wrong_image_refused_before_sources(self):
        with self.assertRaisesRegex(ValueError, 'image mismatch'):
            a.audit(bytes(4), b'', {})


if __name__ == '__main__':
    unittest.main()
