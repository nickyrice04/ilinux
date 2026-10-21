#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original finite range model, no hardware/cache emulation or native code."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('publication31g',Path(__file__).with_name('audit.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class Coverage(unittest.TestCase):
    def test_all_current_spans_cover_every_modeled_line(self):
        for _,offset,size in a.SPANS:
            for line in (64,128,256):
                with self.subTest(offset=offset,size=size,line=line):
                    self.assertTrue(a.range_coverage(offset,size,line)['covered'])

    def test_unaligned_crossing_can_miss_last_line(self):
        r=a.range_coverage(63,2,64)
        self.assertFalse(r['covered']);self.assertEqual(r['missing_lines'],1)

    def test_stride64_cannot_prove_32byte_line_coverage(self):
        self.assertFalse(a.range_coverage(0,168,32)['covered'])

    def test_realistic_128byte_line_is_covered_with_redundant_operations(self):
        r=a.range_coverage(0xa00,168,128)
        self.assertEqual((r['operations'],r['required_lines']), (3,2))

    def test_addresses_above_one_tib_preserve_coverage(self):
        for _,offset,size in a.SPANS:
            self.assertEqual(a.range_coverage(offset,size,128),
                             a.range_coverage((1<<40)+offset,size,128))

    def test_every_small_span_matches_independent_byte_enumeration(self):
        for start in range(128):
            for length in range(1,193):
                needed={p//64 for p in range(start,start+length)}
                touched={p//64 for p in range(start,start+length,64)}
                self.assertEqual(a.range_coverage(start,length,64)['covered'],needed<=touched)

    def test_invalid_ranges_rejected(self):
        for args in [(-1,4,64),(0,0,64),(0,4097,64),(1<<64,4,64),((1<<64)-1,2,64),(0,4,3),(True,4,64)]:
            with self.subTest(args=args),self.assertRaises(ValueError):a.range_coverage(*args)

    def test_wrong_image_is_refused(self):
        with self.assertRaisesRegex(ValueError,'image_digest'):a.audit(b'not the pinned image')

if __name__=='__main__':unittest.main()
