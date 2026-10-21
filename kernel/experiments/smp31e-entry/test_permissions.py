#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline malformed-PAR and exact-range tests; no target operations."""
import argparse
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('permissions', HERE / 'permissions.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
BASE = (1 << 40) + 0x200000


def good(probe):
    if probe['permission_fault']:
        return 1 | (0xf << 1)
    return ((probe['physical'] & p.PAR_PA) | probe['attr'] << 56 |
            (probe['shareability'] or 0) << 7)


class PermissionsTests(unittest.TestCase):
    def test_fixed_probe_plan(self):
        plan = p.probe_plan(BASE)
        self.assertEqual(len(plan), 16)
        self.assertEqual(len({q['name'] for q in plan}), 16)
        self.assertEqual({q['physical'] - BASE for q in plan},
                         {0x8fc, 0xa00, 0xac8, 0x90a40, 0x90a78})
        self.assertEqual(sum(q['permission_fault'] for q in plan), 3)
        for q in plan:
            self.assertTrue(p.validate_probe(q, good(q)))

    def test_regimes(self):
        self.assertEqual(p.select_regime(4), {'read_offset': 192, 'write_offset': 224})
        self.assertEqual(p.select_regime(8, p.EXPECTED_HCR),
                         {'read_offset': 256, 'write_offset': 288})
        for el, hcr in ((0, 0), (12, 0), (True, 0), (4, 1), (8, 0),
                        (8, p.EXPECTED_HCR ^ (1 << 34)),
                        (8, p.EXPECTED_HCR ^ (1 << 27)), (8, -1)):
            with self.subTest(el=el, hcr=hcr), self.assertRaises(ValueError):
                p.select_regime(el, hcr)

    def test_hcr_regime_bits_only(self):
        for bit in range(64):
            value = p.EXPECTED_HCR ^ (1 << bit)
            with self.subTest(bit=bit):
                if bit in (0, 27, 34):
                    with self.assertRaises(ValueError):
                        p.select_regime(8, value)
                else:
                    self.assertEqual(p.select_regime(8, value),
                                     {'read_offset': 256, 'write_offset': 288})
        self.assertEqual(p.select_regime(8, p.HCR_VHE_HOST),
                         {'read_offset': 256, 'write_offset': 288})

    def test_invalid_bases(self):
        for base in (True, 0, -1, BASE + 1, 1 << 41, 1 << 64, '0'):
            with self.subTest(base=base), self.assertRaises(ValueError):
                p.probe_plan(base)

    def test_invalid_par_types(self):
        for q in p.probe_plan(BASE):
            for par in (True, -1, 1 << 64, None, '0'):
                with self.subTest(q=q['name'], par=par), self.assertRaises(ValueError):
                    p.validate_probe(q, par)

    def test_translation_faults_refuse(self):
        for q in p.probe_plan(BASE):
            if not q['permission_fault']:
                with self.subTest(q=q['name']), self.assertRaises(ValueError):
                    p.validate_probe(q, 1)

    def test_wrong_physical_page_refuses(self):
        for q in p.probe_plan(BASE):
            if not q['permission_fault']:
                with self.subTest(q=q['name']), self.assertRaises(ValueError):
                    p.validate_probe(q, good(q) ^ 0x1000)

    def test_wrong_attributes_refuse(self):
        for q in p.probe_plan(BASE):
            if not q['permission_fault']:
                for attr in (0, 4, 0x44, 0xff):
                    if attr != q['attr']:
                        par = (good(q) & ((1 << 56) - 1)) | attr << 56
                        with self.subTest(q=q['name'], attr=attr), self.assertRaises(ValueError):
                            p.validate_probe(q, par)

    def test_normal_shareability_refuses(self):
        for q in p.probe_plan(BASE):
            if not q['permission_fault'] and q['shareability'] == 2:
                for sh in (0, 1, 3):
                    with self.subTest(q=q['name'], sh=sh), self.assertRaises(ValueError):
                        p.validate_probe(q, (good(q) & ~(3 << 7)) | sh << 7)

    def test_permission_fault_type(self):
        q = next(q for q in p.probe_plan(BASE) if q['permission_fault'])
        for fst in range(64):
            par = 1 | fst << 1
            if fst in (0xc, 0xd, 0xe, 0xf):
                self.assertTrue(p.validate_probe(q, par))
            else:
                with self.subTest(fst=fst), self.assertRaises(ValueError):
                    p.validate_probe(q, par)
        with self.assertRaises(ValueError):
            p.validate_probe(q, 0)

    def test_tail_binding(self):
        self.assertTrue(p.verify_helper_tail(p.HELPER_TAIL))
        self.assertEqual(len(p.HELPER_TAIL), 160)
        for n in range(len(p.HELPER_TAIL)):
            bad = bytearray(p.HELPER_TAIL)
            bad[n] ^= 1
            with self.subTest(byte=n), self.assertRaises(ValueError):
                p.verify_helper_tail(bytes(bad))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--assembled-tail', type=Path)
    args, rest = parser.parse_known_args()
    if args.assembled_tail:
        p.verify_helper_tail(args.assembled_tail.read_bytes())
    unittest.main(argv=['test_permissions.py', *rest])
