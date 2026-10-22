# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import sys
import unittest
spec=importlib.util.spec_from_file_location('format_audit',Path(__file__).with_name('audit.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


class Audit(unittest.TestCase):
    def test_old_collision_reproduced_with_actual_frozen_census(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'native/boot'))
        import smp31_census as old
        base=1<<40
        self.assertEqual(old.classify(base|1,base),old.classify(base|0x801,base))
        self.assertNotEqual(a.classify(base|1,base),a.classify(base|0x801,base))
    def test_neither_input_claims_exact_entry(self):
        for word in ((1<<40)|1,(1<<40)|0x801):
            row=a.classify(word,1<<40)
            self.assertEqual(row['exact_entry_offset'],'UNKNOWN')
            self.assertEqual(row['effective_reset_route'],'UNKNOWN')
            self.assertTrue(row['legacy_page_matches_vector_page'])
    def test_every_omitted_low_bit_is_preserved(self):
        for bit in range(1,12):
            row=a.classify((1<<40)|1|(1<<bit),1<<40)
            self.assertEqual(row['unclassified_low_set_bits'],[bit])
    def test_every_high_bit_is_unclassified(self):
        for bit in range(48,64):
            row=a.classify((1<<40)|1|(1<<bit),1<<40)
            self.assertEqual(row['unclassified_high_set_bits'],[bit])
    def test_masks_cover_every_bit_without_overlap(self):
        masks=(a.PAGE_MASK,a.LOCK_MASK,a.UNKNOWN_LOW_MASK,a.UNKNOWN_HIGH_MASK)
        self.assertEqual(sum(masks),(1<<64)-1)
        for i,mask in enumerate(masks):
            for other in masks[i+1:]:self.assertEqual(mask&other,0)
    def test_different_page_is_not_hidden(self):
        self.assertFalse(a.classify((1<<40)|0x1001,1<<40)['legacy_page_matches_vector_page'])
    def test_no_absolute_address_in_report(self):
        import json
        result=json.dumps(a.classify((1<<40)|0x801,1<<40))
        self.assertNotIn(str(1<<40),result)
        self.assertEqual(a.classify((1<<40)|0x801,1<<40)['unclassified_low_set_bits'],[11])
    def test_bad_input_types_sentinels_and_alignment(self):
        for word in (None,True,-1,1<<64,0,(1<<64)-1,0xbad0bad0bad0bad0):
            with self.assertRaises(ValueError):a.classify(word,1<<40)
        for base in (0,True,-1,1,1<<48):
            with self.assertRaises(ValueError):a.classify((1<<40)|1,base)


if __name__=='__main__':unittest.main()
