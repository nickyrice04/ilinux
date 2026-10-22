"""Independent fixed-leaf decode, mutation and failure-prefix contracts."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('startpair31n', Path(__file__).with_name('plan.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def decode(payload, stop_before=None):
    """Narrow independent interpreter: no sysregs, host/native code execution.

    Its only effects are Python register values and a synthetic store trace.
    It makes no prediction about the MMIO device or whether a store faults.
    """
    registers, trace, returned = [0]*31, [], False
    for offset in range(0, len(payload), 4):
        if offset == stop_before:
            break
        word, = struct.unpack_from('<I', payload, offset)
        if word & 0x7f800000 in (0x52800000, 0x72800000):
            wide = bool(word >> 31)
            rd, half, immediate = word & 31, (word >> 21) & 3, (word >> 5) & 0xffff
            if rd == 31 or not wide and half >= 2:
                raise ValueError('bad move')
            if word & 0x7f800000 == 0x52800000:
                registers[rd] = immediate << (half*16)
            else:
                registers[rd] = (registers[rd] & ~(0xffff << (half*16))) | immediate << (half*16)
            if not wide:
                registers[rd] &= 0xffffffff
        elif word & 0xffc00000 == 0xb9000000:
            rt, rn = word & 31, (word >> 5) & 31
            if rt == 31 or rn == 31:
                raise ValueError('unexpected zero/stack access')
            trace.append(('store32', registers[rn]+4*((word >> 10) & 0xfff), registers[rt] & 0xffffffff))
        elif word == 0xd5033f9f:
            trace.append(('dsb_sy',))
        elif word == 0xd65f03c0 and offset == len(payload)-4:
            returned = True
        else:
            raise ValueError('instruction outside independent allowlist')
    return trace, returned, registers[0]


class PlanTests(unittest.TestCase):
    def test_fixed_leaf_decodes_to_only_two_original_stores(self):
        trace, returned, token = decode(p.LEAF)
        self.assertEqual(trace, [('dsb_sy',), ('store32', 0x280688004, 2),
            ('dsb_sy',), ('store32', 0x280688008, 2), ('dsb_sy',)])
        self.assertTrue(returned)
        self.assertEqual(token, 0x314e)
        self.assertEqual(p.verify_leaf()['store_offsets'], [20, 28])

    def test_each_interruption_prefix_cannot_confirm_pair_return(self):
        counts = set()
        for offset in range(0, len(p.LEAF), 4):
            with self.subTest(offset=offset):
                trace, returned, token = decode(p.LEAF, offset)
                self.assertFalse(returned)
                counts.add(sum(row[0] == 'store32' for row in trace))
                # A token register can be set before RET; only an actual call
                # return plus clean diagnostics allows acknowledgment.
                self.assertEqual(p.uncertain_completion()['stores_acknowledged'], 0)
                self.assertFalse(p.uncertain_completion()['retry_authorized'])
        self.assertEqual(counts, {0, 1, 2})

    def test_every_word_mutation_rejected(self):
        for offset in range(0, len(p.LEAF), 4):
            changed = bytearray(p.LEAF)
            changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, 'leaf_changed'):
                p.verify_leaf(bytes(changed))

    def test_extent_or_type_change_rejected(self):
        for payload in (p.LEAF[:-4], p.LEAF+b'\0'*4, bytearray(p.LEAF), None):
            with self.subTest(payload_type=type(payload).__name__), self.assertRaises(ValueError):
                p.verify_leaf(payload)

    def test_full_64bit_helper_address_and_disjoint_layout(self):
        helper = 0x10000420000
        self.assertEqual(p.entry_address(helper, helper-0x4000, helper+0x8000),
                         (helper | 0xc0000000000)+0x240)
        spans = [(0, 0x210), (0x220, 0x228), (0x1000, 0x1080),
                 (0x1080, 0x1100), (0x1100, 0x1180)]
        self.assertTrue(all(p.LEAF_OFFSET+len(p.LEAF) <= lo or p.LEAF_OFFSET >= hi
                            for lo, hi in spans))

    def test_invalid_allocations_refused(self):
        h = 0x10000420000
        for args in ((True,1,2), (h+1,h,h+0x8000), (h,h+1,h+0x8000),
                     (h,h,h+0x3fff), (h,h,1<<41), (-1,0,0x8000)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                p.entry_address(*args)

    def test_integer_parser_subclasses_preserve_exact_address(self):
        class ParsedInteger(int):
            pass
        helper = 0x10000420000
        expected = (helper | 0xc0000000000)+0x240
        for values in ((helper, ParsedInteger(helper-0x4000), ParsedInteger(helper+0x8000)),
                       tuple(ParsedInteger(value) for value in
                             (helper, helper-0x4000, helper+0x8000))):
            with self.subTest(types=[type(value).__name__ for value in values]):
                self.assertEqual(p.entry_address(*values), expected)

    def test_each_address_argument_rejects_bool_float_and_string(self):
        helper = 0x10000420000
        original = (helper, helper-0x4000, helper+0x8000)
        for index in range(3):
            for value in (True, False, float(original[index]), str(original[index])):
                args = list(original)
                args[index] = value
                with self.subTest(index=index, type=type(value).__name__), self.assertRaisesRegex(
                        ValueError, '^start_pair_address_type$'):
                    p.entry_address(*args)

    def test_completion_requires_exact_token_and_clean_diagnostics(self):
        good = p.validate_completion(0x314e, 0)
        self.assertEqual(good['stores_acknowledged'], 2)
        self.assertFalse(good['completion_proves_cpu1_execution'])
        for args in ((True,0), (None,0), (0,0), (0x314e,True),
                     (0x314e,None), (0x314e,1), (0x314e,1<<32)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                p.validate_completion(*args)

    def test_uncertain_completion_does_not_grant_retry_or_cleanup(self):
        row = p.uncertain_completion()
        self.assertEqual(row['possible_completed_stores'], [0,1,2])
        self.assertFalse(row['further_target_operation_authorized'])
        self.assertFalse(row['completion_proves_cpu1_execution'])


if __name__ == '__main__':
    unittest.main()
