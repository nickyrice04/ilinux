#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Source-level regression boundary against the immutable original collector."""
import hashlib
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'direct31ah/linux/diag_init.c'

class CollectorBoundary(unittest.TestCase):
    def setUp(self):
        data=OLD.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),'53b75d25c01b03a1c92832df91c51b875f03616847cbc674cce1c539cc729761')
        self.old=data.decode();self.new=(HERE/'diag_init.c').read_text()
    def test_workloads_checks_and_deadlines_unchanged(self):
        old=self.old.split('static void camera_summary(int seconds) {')[0]
        new=self.new.split('static enum readable_result readable_cpu_result(int value) {')[0]
        new=new.replace('#include "readable.h"\n','').replace('static enum readable_scope readable_mode=READABLE_DEMO;\n','')
        self.assertEqual(new,old)
    def test_existing_json_guards_and_liveness_loop_unchanged(self):
        marker='static void camera_summary(int seconds) {'
        old=marker+self.old.split(marker)[1];new=marker+self.new.split(marker)[1]
        new=new.replace('    readable_summary(seconds);\n','')
        new=new.replace('    if(argc==2 && !strcmp(argv[1],"--display-test"))return display_test();\n','')
        new=new.replace('    readable_mode=native?READABLE_NATIVE:READABLE_VM;\n','')
        self.assertEqual(new,old)
    def test_display_mode_precedes_pid1_or_hardware_guards(self):
        main=self.new.split('int main(int argc,char **argv) {')[1]
        self.assertLess(main.index('--display-test'),main.index('getpid()!=1'))
        body=self.new.split('static int display_test(void) {')[1].split('\n}\n')[0]
        for forbidden in ('mount(','open(','sleep(','ioctl(','mmap(','log_fd=','native='):
            self.assertNotIn(forbidden,body)
        self.assertIn('SYNTHETIC_PANEL_DEMO',body)
    def test_renderer_uses_no_external_device_or_terminal_control(self):
        header=(HERE/'readable.h').read_text()
        for forbidden in ('ioctl(','mmap(','open(','system(','fork(','\x1b','\\033','\\x1b','/dev/'):
            self.assertNotIn(forbidden,header)
        self.assertIn('READABLE_COLUMNS=78',header);self.assertIn('READABLE_ROWS=35',header)

if __name__=='__main__':unittest.main(verbosity=2)
