#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31F fixed vector/body probes; original pure tests, no target operations."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('permissions31f_checks', HERE / 'permissions.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
BASE = (1 << 40) + 0x200000


def good(probe):
    if probe['permission_fault']:
        return 1 | (0xf << 1)
    return ((probe['physical'] & p.previous.PAR_PA) | probe['attr'] << 56 |
            (probe['shareability'] or 0) << 7)


class VectorPermissions(unittest.TestCase):
    def test_all_sixteen_precise_named_probes(self):
        plan = p.probe_plan(BASE)
        self.assertEqual(len(plan), 16)
        self.assertEqual(len({row['name'] for row in plan}), 16)
        self.assertEqual({row['physical'] - BASE for row in plan},
                         {0, 0xa00, 0xaa4, 0x90a40, 0x90a78})
        self.assertEqual(sum(row['permission_fault'] for row in plan), 3)
        for row in plan:
            self.assertTrue(p.validate_probe(row, good(row)))

    def test_hook_and_last_word_are_bound_to_builder(self):
        spec = importlib.util.spec_from_file_location('permissions31f_builder', HERE / 'builder.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        body, _ = builder.program()
        for row in p.probe_plan(BASE):
            if row['name'].startswith('hook_'):
                self.assertEqual(row['physical'], BASE + builder.ENTRY)
            elif row['name'].startswith('stub_last_'):
                self.assertEqual(row['physical'], BASE + builder.CODE_START + len(body) - 4)

    def test_wrapper_changes_only_hook_and_last_word_offsets(self):
        original = p.previous.probe_plan(BASE)
        actual = p.probe_plan(BASE)
        for old, new in zip(original, actual):
            expected = dict(old)
            if old['name'].startswith(('hook_', 'stub_last_')):
                offset = 0 if old['name'].startswith('hook_') else 0xaa4
                delta = old['physical'] - (BASE + offset)
                expected['address'] -= delta
                expected['physical'] -= delta
            self.assertEqual(new, expected)
        self.assertEqual(original, p.previous.probe_plan(BASE))

    def test_existing_alias_and_identity_permissions_are_distinct(self):
        for row in p.probe_plan(BASE):
            alias = '_alias_' in row['name']
            self.assertEqual(row['address'], row['physical'] |
                             (p.previous.RW_ALIAS if alias else 0))
            if row['name'].startswith(('hook_', 'stub_')):
                self.assertEqual(row['attr'], 0xff)
                self.assertEqual(row['shareability'], 2)
                self.assertEqual(row['permission_fault'], row['name'].endswith('identity_write'))
            else:
                self.assertEqual(row['attr'], 0)
                self.assertIsNone(row['shareability'])
                self.assertFalse(row['permission_fault'])

    def test_regimes_exact_and_invalid_states(self):
        self.assertEqual(p.select_regime(4), {'read_offset':192, 'write_offset':224})
        self.assertEqual(p.select_regime(8, p.previous.HCR_VHE_HOST),
                         {'read_offset':256, 'write_offset':288})
        for el, hcr in ((0,0),(12,0),(True,0),(4,1),(8,0),
                        (8,p.previous.HCR_VHE_HOST|1),(8,-1)):
            with self.assertRaises(ValueError):
                p.select_regime(el,hcr)

    def test_only_hcr_regime_bits_decide_el2_translation(self):
        original = p.previous.EXPECTED_HCR
        for bit in range(64):
            if bit in (0,27,34):
                with self.assertRaises(ValueError):
                    p.select_regime(8, original ^ (1 << bit))
            else:
                self.assertEqual(p.select_regime(8, original ^ (1 << bit)),
                                 {'read_offset':256, 'write_offset':288})

    def test_invalid_bases_and_par_types(self):
        for base in (True,0,-1,BASE+1,1 << 41,1 << 64,'0'):
            with self.assertRaises(ValueError):
                p.probe_plan(base)
        for row in p.probe_plan(BASE):
            for value in (True,-1,1 << 64,None,'0'):
                with self.assertRaises(ValueError):
                    p.validate_probe(row,value)

    def test_translation_fault_and_wrong_physical_page_refused(self):
        for row in p.probe_plan(BASE):
            if not row['permission_fault']:
                for value in (1, good(row) ^ 0x1000):
                    with self.assertRaises(ValueError):
                        p.validate_probe(row,value)

    def test_wrong_memory_attributes_and_shareability_refused(self):
        for row in p.probe_plan(BASE):
            if row['permission_fault']:
                continue
            for attribute in (0,4,0x44,0xff):
                if attribute != row['attr']:
                    value = (good(row) & ((1 << 56)-1)) | attribute << 56
                    with self.assertRaises(ValueError):
                        p.validate_probe(row,value)
            if row['shareability'] == 2:
                for shared in (0,1,3):
                    with self.assertRaises(ValueError):
                        p.validate_probe(row,(good(row)&~(3 << 7)) | shared << 7)

    def test_only_permission_faults_accept_identity_write_denial(self):
        for row in p.probe_plan(BASE):
            if not row['permission_fault']:
                continue
            for fault in range(64):
                value = 1 | fault << 1
                if fault in (0xc,0xd,0xe,0xf):
                    self.assertTrue(p.validate_probe(row,value))
                else:
                    with self.assertRaises(ValueError):
                        p.validate_probe(row,value)
            with self.assertRaises(ValueError):
                p.validate_probe(row,0)

    def test_frozen_helper_bytes_and_no_wrapper_mutation(self):
        self.assertIs(p.HELPER_TAIL,p.previous.HELPER_TAIL)
        self.assertTrue(p.verify_helper_tail(p.HELPER_TAIL))
        self.assertEqual(len(p.HELPER_TAIL),160)
        for offset in range(len(p.HELPER_TAIL)):
            changed = bytearray(p.HELPER_TAIL)
            changed[offset] ^= 1
            with self.assertRaises(ValueError):
                p.verify_helper_tail(bytes(changed))


if __name__ == '__main__':
    unittest.main()
