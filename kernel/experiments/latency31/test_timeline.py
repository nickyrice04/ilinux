#!/usr/bin/env python3
"""Evidence-integrity tests: changed inputs, duplicate/tampered traces, nesting."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
def load(name):
    s=importlib.util.spec_from_file_location(name,HERE/(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=load('analyze');patcher=load('apply')
input_clock=load('input_clock')


class EvidenceTests(unittest.TestCase):
    def test_overlap_clipped_union(self):
        rows=[{'tag':'monitor','start_ns':a,'end_ns':b} for a,b in [(1,4),(3,8),(9,20)]]
        self.assertEqual(a.occupied_ns(rows,2,10),7)

    def test_input_no_keycode(self):
        data=input_clock.EVENT.pack(7,50,1,30,1)
        r=input_clock.decode(data,7000060000,9)
        self.assertEqual(r['reader_delay_ns'],10000)
        self.assertNotIn('keycode',r)
        self.assertEqual(r['sequence'],9)

    def test_input_clock_domain_refusal(self):
        with self.assertRaises(ValueError):input_clock.decode(input_clock.EVENT.pack(70,0,1,30,1),3,0)

    def test_input_ignores_nonkey(self):
        self.assertIsNone(input_clock.decode(input_clock.EVENT.pack(1,0,0,0,0),2000000000,0))

    def parse(self, content):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'trace';p.write_text('id,tag,start_ns,end_ns,cpu_ns,arg0,arg1\n'+content)
            return a.read_trace(p)

    def test_nested_not_added(self):
        rows=self.parse('2,scene,110,190,75,0,0\n1,monitor,100,200,90,0,0\n')
        s=a.stats(rows)
        self.assertEqual(s['monitor']['wall_sum_ms'],.0001)
        self.assertEqual(s['scene']['wall_sum_ms'],.00008)

    def test_clock_reversal(self):
        with self.assertRaises(ValueError):self.parse('1,scene,200,100,1,0,0\n')

    def test_duplicate_id(self):
        with self.assertRaises(ValueError):self.parse('1,scene,100,200,1,0,0\n1,scene,300,400,1,0,0\n')

    def test_unrecognized_tag(self):
        with self.assertRaises(ValueError):self.parse('1,private-text,100,200,1,0,0\n')

    def test_incomplete_row(self):
        with self.assertRaises((ValueError,TypeError)):self.parse('1,scene,100\n')

    def test_empty(self):
        with self.assertRaises(ValueError):self.parse('')

    def test_ambiguous_anchor(self):
        with self.assertRaises(ValueError):patcher.once('a a','a','b')

    def test_source_refusal_before_write(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            p=root/'src/render/Renderer.cpp';p.parent.mkdir(parents=True);p.write_text('changed source')
            with self.assertRaises(ValueError):patcher.apply(root)
            self.assertEqual(p.read_text(),'changed source')
            self.assertFalse((root/'src/helpers/ILinuxTimeline.hpp').exists())


if __name__=='__main__':unittest.main()
