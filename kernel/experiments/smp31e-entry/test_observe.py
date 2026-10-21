#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('observe',Path(__file__).with_name('observe.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
TOP=0x100000a0000


class ObserveTests(unittest.TestCase):
    def test_both_partial_publication_orders(self):
        expected=[((m.MASK64,0),'no_reset_record_seen'),
                  ((m.CPU1_MPIDR,0),'mpidr_publication_seen'),
                  ((m.MASK64,TOP),'stack_publication_seen'),
                  ((m.CPU1_MPIDR,TOP),'reset_identity_seen')]
        for (mpidr,stack),stage in expected:
            self.assertEqual(m.reset_stage(mpidr,stack,0,0,TOP),stage)

    def test_final_arrival_requires_all_identity(self):
        for a,b,c in [(m.MASK64,0,0),(m.CPU1_MPIDR,0,0),
                      (m.MASK64,TOP,0),(m.CPU1_MPIDR,TOP,0)]:
            with self.assertRaisesRegex(ValueError,'arrival_identity'):
                m.reset_stage(a,b,c,1,TOP)
        self.assertEqual(m.reset_stage(m.CPU1_MPIDR,TOP,m.CPU1_MPIDR,1,TOP),'arrival_flag_seen')

    def test_spin_identity_requires_reset_publication(self):
        with self.assertRaisesRegex(ValueError,'spin_identity_before_reset'):
            m.reset_stage(m.CPU1_MPIDR,0,m.CPU1_MPIDR,0,TOP)
        self.assertEqual(m.reset_stage(m.CPU1_MPIDR,TOP,m.CPU1_MPIDR,0,TOP),'spin_identity_seen')

    def test_unknown_identity_and_malformed_values_refuse(self):
        for values in [(m.CPU1_MPIDR+1,0,0,0,TOP),
                       (m.CPU1_MPIDR,TOP+16,0,0,TOP),
                       (m.MASK64,0,0x40002,0,TOP),
                       (m.MASK64,0,0,True,TOP),(m.MASK64,0,0,0,TOP+8)]:
            with self.assertRaises(ValueError):m.reset_stage(*values)

    def test_stack_results_contain_only_booleans(self):
        base=1<<40
        words={offset:0xd1a631e0d1a631e0 for offset in m.FRAME_SLOTS}
        self.assertFalse(any(m.stack_markers(words,base).values()))
        words[-24]=base+0x974;words[-72]=base+0x32958
        result=m.stack_markers(words,base)
        self.assertTrue(result['reset_c_non_el3_frame'])
        self.assertTrue(result['init_cpu_frame'])
        self.assertTrue(all(type(value) is bool for value in result.values()))

    def test_snapshot_shape_is_exact(self):
        words={offset:0 for offset in m.FRAME_SLOTS}
        for malformed in ({},dict(words,extra=0),{**words,-24:-1}):
            with self.assertRaises(ValueError):m.stack_markers(malformed,1<<40)


if __name__=='__main__':unittest.main()
