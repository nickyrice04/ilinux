import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

s=importlib.util.spec_from_file_location('supervisor', Path(__file__).with_name('attempt31d-supervise.py'))
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)


class SupervisorTests(unittest.TestCase):
    def test_normal_exit(self):
        proc=subprocess.Popen([sys.executable,'-I','-c','raise SystemExit(7)'], start_new_session=True)
        self.assertEqual(m.wait_bounded(proc, 5), (7, False))
    def test_stalled_child_terminated(self):
        proc=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'], start_new_session=True)
        self.assertEqual(m.wait_bounded(proc, 0.1), (124, True))
        self.assertIsNotNone(proc.poll())
    def test_sigterm_ignored_child_killed(self):
        readfd, writefd=os.pipe()
        proc=subprocess.Popen([sys.executable,'-I','-c',
            'import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
            f'os.write({writefd},b"r"); time.sleep(30)'], pass_fds=(writefd,),start_new_session=True)
        os.close(writefd)
        try:
            self.assertEqual(os.read(readfd,1),b'r')
            self.assertEqual(m.wait_bounded(proc,0.1),(124,True))
            self.assertEqual(proc.returncode,-9)
        finally:
            os.close(readfd)
            if proc.poll() is None: proc.kill(); proc.wait()


if __name__ == '__main__': unittest.main()
