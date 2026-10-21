#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original offline only; no hardware or client imports."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan
spec = importlib.util.spec_from_file_location('original_generator',
    plan.ROOT / 'kernel/experiments/t6050-dt/gen_t6050_dt.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class Binding(unittest.TestCase):
    def setUp(self):
        self.nodes = generator.load(plan.ROOT / 'hardware/adt/adt-sanitized.json')

    def test_exact_cpu_pair(self):
        rows = plan.allowlist(self.nodes)
        self.assertEqual([(r['cpu_id'],r['address'],r['width_bits']) for r in rows],
                         [(0,0x280600000,32),(1,0x280600008,32)])
        self.assertTrue(all(r['macos_class']=='Performance' and r['adt_cluster']==0 for r in rows))

    def mutate_record(self, offset, value):
        pm = self.nodes['/arm-io/pmgr']
        data = bytearray.fromhex(pm['devices']['hex'])
        data[48+offset] = value
        pm['devices']['hex'] = data.hex()

    def test_wrong_domain_location_refused(self):
        self.mutate_record(16,16)
        with self.assertRaisesRegex(ValueError,'binding'):plan.allowlist(self.nodes)

    def test_virtual_domain_refused(self):
        self.mutate_record(0,16)
        with self.assertRaisesRegex(ValueError,'binding'):plan.allowlist(self.nodes)

    def test_wrong_name_refused(self):
        self.mutate_record(32,ord('X'))
        with self.assertRaisesRegex(ValueError,'missing'):plan.allowlist(self.nodes)


class Decoding(unittest.TestCase):
    def test_every_nibble_pair(self):
        for desired in range(16):
            for actual in range(16):
                d=plan.fields(desired|actual<<4)
                self.assertEqual((d['desired'],d['actual']),(desired,actual))
                self.assertEqual(set(d),{'desired','actual','parent_missing','device_disabled','auto_enabled'})

    def test_sticky_gate_bits_are_not_status(self):
        self.assertEqual(plan.fields(0xff),plan.fields(0xff|0x300))

    def test_reject_bad_width_types(self):
        for word in (-1,1<<32,True,None,'0xff'):
            with self.assertRaises(ValueError):plan.fields(word)

    def test_active_domain_does_not_claim_entry(self):
        report=plan.compare([dict(phase='before_start',cpu0=0xff,cpu1=0),
                             dict(phase='after_first_start',cpu0=0xff,cpu1=0xf),
                             dict(phase='after_second_start',cpu0=0xff,cpu1=0xff)])
        self.assertTrue(report['target_actual_changed'])
        self.assertTrue(report['target_actual_equals_legacy_active'])
        self.assertEqual(report['entry_execution'],'NOT_ESTABLISHED')
        self.assertFalse(report['additional_write_authorized'])

    def test_each_prefix_valid(self):
        rows=[dict(phase=p,cpu0=0xff,cpu1=0) for p in plan.PHASES]
        for n in range(1,5):self.assertEqual(plan.compare(rows[:n])['observations'],n)

    def test_duplicate_or_reordered_phase_refused(self):
        for phase in ('final','after_second_start','unknown'):
            with self.assertRaises(ValueError):
                plan.compare([dict(phase=phase,cpu0=0xff,cpu1=0)])

    def test_size_and_shape_refused(self):
        for data in ([], [dict(phase='before_start',cpu0=0xff,cpu1=0,extra=0)],
                     [dict(phase='before_start',cpu0=0xff,cpu1=0)]*5):
            with self.assertRaises(ValueError):plan.compare(data)


if __name__ == '__main__':unittest.main()
