#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Harmless PTY qualification of the production interactive-child primitive.

This builds a separate test-only main, never broadens the production CLI, and
runs only a fixed own shell fragment. No disk, policy, Recovery or boot command.
"""
import argparse
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import time
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BUILD=OUTPUT=None

HARNESS=r'''#define main original_controller_main
#define AR_TEST_EARLY_EXIT early_exit
static int early_exit;
#include "controller.c"
#include <sys/ioctl.h>
#undef main
int main(int argc,char **argv){
 if(argc!=2)return 2;
 if(!strcmp(argv[1],"sources")){
  char normalized[80];const char *valid[]={"/dev/disk3s1","/dev/disk3s1s1","snapshot@/dev/disk3s1s2s1","/dev/rdisk9s2"};
  const char *invalid[]={"disk3","/dev/disk3s","/dev/disk3s1s1s1s1","/dev/disk3s-1","/dev/disk3s1junk"};
  for(unsigned i=0;i<4;i++)if(!source_device_ar(valid[i],normalized))return 10;
  for(unsigned i=0;i<5;i++)if(source_device_ar(invalid[i],normalized))return 11;
  puts("SOURCE_GRAMMAR_PASS");return 0;
 }
 int tty=open("/dev/tty",O_RDWR);if(tty<0)return 3;
 struct termios before,after;if(tcgetattr(tty,&before))return 4;pid_t group=tcgetpgrp(tty);
 bool timeout=!strcmp(argv[1],"timeout"),interrupt=!strcmp(argv[1],"interrupt"),quick=!strcmp(argv[1],"quick");
 early_exit=!strcmp(argv[1],"early");
 signal(SIGINT,stop_handler);signal(SIGTERM,stop_handler);
 const char *const args[]={"/bin/sh","-c",quick?"exit 17":"printf 'OWN_PROMPT\\n'; stty -echo; IFS= read -r own; printf 'OWN_READ_OK\\n'; sleep 10",NULL};
 int rc=interactive_child(args,timeout?350:interrupt?5000:quick||early_exit?2000:1200);
 int pending=-1;bool restored=tcgetpgrp(tty)==group&&!tcgetattr(tty,&after)&&!memcmp(&before,&after,sizeof(before))&&
  !ioctl(tty,FIONREAD,&pending)&&pending==0;close(tty);
 printf("PTY_RESULT %d %d\\n",rc,restored?1:0);fflush(stdout);return restored?0:5;
}
'''


class PtyControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if OUTPUT.exists() or ROOT/'build' not in OUTPUT.parents:raise ValueError('fresh workspace output')
        OUTPUT.mkdir(parents=True,mode=0o700)
        source=BUILD/'sources'
        harness=OUTPUT/'pty-harness.c';harness.write_text(HARNESS)
        cls.binary=OUTPUT/'pty-harness'
        receipt=json.loads((BUILD/'build-result.json').read_text())
        candidate=receipt['candidate_definition']
        command=['/usr/bin/xcrun','clang','-std=c11','-O1','-Wall','-Wextra','-Werror',
                 '-Wno-deprecated-declarations','-arch','arm64','-mmacosx-version-min=13.0',
                 '-DWORKSPACE_ROOT='+json.dumps(str(ROOT)),
                 '-DCANDIDATE_BYTES='+str(candidate['bytes']),
                 '-DCANDIDATE_SHA256='+json.dumps(candidate['sha256']),'-I',str(source),
                 str(harness),str(source/'core.c'),str(source/'json.c'),str(source/'extra_policy.c'),
                 '-framework','CoreFoundation','-lcompression','-o',str(cls.binary)]
        subprocess.run(command,check=True,timeout=60,capture_output=True)

    def run_case(self,kind,expected):
        child,fd=pty.fork()
        if not child:
            os.execv(self.binary,[str(self.binary),kind])
        transcript=bytearray();sent=False;queued=False;interrupted=False;deadline=time.monotonic()+8;status=None
        try:
            while time.monotonic()<deadline:
                ready,_,_=select.select([fd],[],[],0.1)
                if ready:
                    try:piece=os.read(fd,4096)
                    except OSError:piece=b''
                    if piece:transcript.extend(piece)
                if b'OWN_PROMPT' in transcript and not sent:
                    os.write(fd,b'own-input\n');sent=True
                if kind in ('timeout','interrupt') and b'OWN_READ_OK' in transcript and not queued:
                    os.write(fd,b'queued-dummy-input\n');queued=True
                if kind=='interrupt' and b'OWN_READ_OK' in transcript and not interrupted:
                    os.kill(child,signal.SIGTERM);interrupted=True
                got,raw=os.waitpid(child,os.WNOHANG)
                if got:
                    status=raw
                    for _ in range(4):
                        try:piece=os.read(fd,4096)
                        except OSError:break
                        if not piece:break
                        transcript.extend(piece)
                    break
            self.assertIsNotNone(status,bytes(transcript))
            self.assertEqual(os.waitstatus_to_exitcode(status),0,bytes(transcript))
            self.assertIn(('PTY_RESULT '+str(expected)+' 1').encode(),transcript)
            if kind not in ('early','quick'):self.assertTrue(sent)
        finally:
            if status is None:
                os.kill(child,signal.SIGKILL);os.waitpid(child,0)
            os.close(fd)

    def test_foreground_auth_input_and_echo_restored_after_timeout(self):self.run_case('timeout',124)
    def test_foreground_and_echo_restored_after_parent_interruption(self):self.run_case('interrupt',130)
    def test_immediate_nonzero_child_exit_restores_foreground(self):self.run_case('quick',17)
    def test_pre_gate_child_exit_cannot_kill_parent_with_sigpipe(self):self.run_case('early',19)
    def test_system_snapshot_source_grammar_and_negative_controls(self):
        run=subprocess.run([str(self.binary),'sources'],capture_output=True,text=True,timeout=5)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(run.stdout,'SOURCE_GRAMMAR_PASS\n')


def main():
    global BUILD,OUTPUT
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a,rest=p.parse_known_args();BUILD=a.build.resolve();OUTPUT=a.output.resolve()
    unittest.main(argv=[sys.argv[0]]+rest,verbosity=2)


if __name__=='__main__':main()
