#!/usr/bin/env python3
"""Offline tests of m5-clock.py (the M1) against the M5's set-clock helper (VM job 045, LINK=1).

A stand-in for ssh runs the real helper with bash, with a fake `date` that keeps the "M5's clock"
as an offset in a file, so the whole exchange runs here: the clock really moves, the readback
really checks it. Also: the helper's refusals, the tool's exits for a missing helper, a refusal,
garbage and silence, and m5-ssh-config's m5o entries as ssh itself reads them (ssh -G).
    python3 -I tools/m1n1-client/test_m5_clock.py
The VM job runs the same tool and helper over the real USB pipe (job 045, LINK=1, stage 4).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOL = HERE / "m5-clock.py"
CONFIG = HERE / "m5-ssh-config"
HELPER = ROOT / "virtualization/jobs/045-omarchy-installer-root/link-overlay/usr/local/lib/ilinux/set-clock"
DAY = 86400 * 10**9

FAKE_DATE = r'''#!%(python)s
import os, sys, time
state = os.environ["FAKE_CLOCK_FILE"]
def offset():
    try:
        return int(open(state).read())
    except FileNotFoundError:
        return 0
args = sys.argv[1:]
if args == ["+%%s%%N"]:
    print(time.time_ns() + offset())
elif args[:2] == ["-u", "-s"] and args[2].startswith("@"):
    s, _, frac = args[2][1:].partition(".")
    target = int(s) * 10**9 + int((frac + "000000000")[:9])
    if os.environ.get("FAKE_CLOCK_STUCK") != "1":
        open(state, "w").write(str(target - time.time_ns()))
    with open(os.environ["FAKE_CLOCK_FILE"] + ".sets", "a") as f:
        f.write(args[2] + "\n")
elif args[:2] == ["-u", "-d"]:
    print(time.strftime("%%Y-%%m-%%dT%%H:%%M:%%SZ", time.gmtime(int(args[2][1:].split(".")[0]))))
else:
    sys.exit("fake date: unexpected arguments %%r" %% args)
'''

# The stand-ins for ssh. Each records its arguments, then plays the M5.
SSH_HELPER = r'''#!%(python)s
import os, sys
open(os.environ["FAKE_SSH_ARGV"], "w").write("\n".join(sys.argv[1:]))
os.environ["PATH"] = os.environ["FAKE_BIN"] + ":/usr/bin:/bin"
os.execv("/bin/bash", ["bash", os.environ["FAKE_HELPER"]])
'''
SSH_NO_HELPER = r'''#!%(python)s
import os, sys
open(os.environ["FAKE_SSH_ARGV"], "w").write("\n".join(sys.argv[1:]))
sys.stderr.write("sudo: a password is required\n")
sys.exit(1)
'''
SSH_REFUSES = r'''#!%(python)s
import os, sys, time
open(os.environ["FAKE_SSH_ARGV"], "w").write("\n".join(sys.argv[1:]))
print("ilinux-clock ready %%d" %% time.time_ns(), flush=True)
sys.stdin.readline()
print("ilinux-clock refused: a test refusal", flush=True)
'''
SSH_GARBAGE = r'''#!%(python)s
import os, sys
open(os.environ["FAKE_SSH_ARGV"], "w").write("\n".join(sys.argv[1:]))
print("SSH-2.0-not-the-helper", flush=True)
'''
SSH_SILENT = r'''#!%(python)s
import os, sys, time
open(os.environ["FAKE_SSH_ARGV"], "w").write("\n".join(sys.argv[1:]))
time.sleep(5)
'''


class ClockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="m5-clock-test-"))
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.write(self.bin / "date", FAKE_DATE)
        self.write(self.bin / "logger", "#!/bin/sh\nexit 0\n")
        self.clock = self.tmp / "clock"
        self.env = dict(os.environ, FAKE_CLOCK_FILE=str(self.clock), FAKE_BIN=str(self.bin),
                        FAKE_HELPER=str(HELPER), FAKE_SSH_ARGV=str(self.tmp / "argv"))
        self.env.pop("FAKE_CLOCK_STUCK", None)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, path, text):
        path.write_text(text % {"python": sys.executable} if "%(python)s" in text else text)
        path.chmod(0o755)

    def offset(self):
        return int(self.clock.read_text()) if self.clock.exists() else 0

    def run_tool(self, ssh_text, *extra, offset=0):
        ssh = self.tmp / "ssh"
        self.write(ssh, ssh_text)
        self.clock.write_text(str(offset))
        out = subprocess.run([sys.executable, "-I", str(TOOL), "--ssh", str(ssh), "--config", "/dev/null",
                              *extra], env=self.env, capture_output=True, text=True, timeout=60)
        return out.returncode, out.stdout + out.stderr

    def helper(self, text, offset=0):
        self.clock.write_text(str(offset))
        env = dict(self.env, PATH=str(self.bin) + ":/usr/bin:/bin")
        out = subprocess.run(["/bin/bash", str(HELPER)], input=text, env=env, capture_output=True,
                             text=True, timeout=60)
        return out.returncode, out.stdout

    # ---- the whole exchange against the real helper -------------------------------------------------
    def test_sets_a_clock_three_days_behind(self):
        rc, out = self.run_tool(SSH_HELPER, offset=-3 * DAY)
        self.assertEqual(rc, 0, out)
        self.assertIn("3.0 days behind", out)
        self.assertIn("PASS", out)
        self.assertLess(abs(self.offset()), 5 * 10**8, out)   # the fake M5 clock now agrees with the M1's
        self.assertEqual(len((self.tmp / "clock.sets").read_text().splitlines()), 1)

    def test_sets_a_clock_that_is_ahead(self):
        rc, out = self.run_tool(SSH_HELPER, offset=90 * 60 * 10**9)
        self.assertEqual(rc, 0, out)
        self.assertIn("1.5 h ahead of", out)
        self.assertLess(abs(self.offset()), 5 * 10**8, out)

    def test_ssh_command_line(self):
        rc, out = self.run_tool(SSH_HELPER, "--host", "m5o-port2")
        self.assertEqual(rc, 0, out)
        argv = (self.tmp / "argv").read_text().split("\n")
        self.assertEqual(argv[:2], ["-F", "/dev/null"])
        self.assertIn("ClearAllForwardings=yes", argv)   # no proxy forward during the clock step
        self.assertIn("RequestTTY=no", argv)
        self.assertEqual(argv[-2:], ["m5o-port2", "sudo -n /usr/local/lib/ilinux/set-clock"])

    def test_a_clock_that_does_not_move_fails_the_check(self):
        self.env["FAKE_CLOCK_STUCK"] = "1"
        rc, out = self.run_tool(SSH_HELPER, offset=-3 * DAY)
        self.assertEqual(rc, 1, out)
        self.assertIn("FAIL", out)

    # ---- the tool's other exits ------------------------------------------------------------------------
    def test_no_helper_on_the_m5(self):
        rc, out = self.run_tool(SSH_NO_HELPER)
        self.assertEqual(rc, 2, out)
        self.assertIn("ended before the M5's helper answered", out)
        self.assertIn("a password is required", out)

    def test_the_m5_refuses(self):
        rc, out = self.run_tool(SSH_REFUSES)
        self.assertEqual(rc, 3, out)
        self.assertIn("refused: a test refusal", out)

    def test_garbage_from_the_m5(self):
        rc, out = self.run_tool(SSH_GARBAGE)
        self.assertEqual(rc, 2, out)
        self.assertIn("unexpected line", out)

    def test_silence_times_out(self):
        t0 = time.monotonic()
        rc, out = self.run_tool(SSH_SILENT, "--connect-timeout", "1")
        self.assertEqual(rc, 2, out)
        self.assertIn("no answer from the M5 within 1 s", out)
        self.assertLess(time.monotonic() - t0, 30)

    # ---- the helper refuses anything but one plausible time ------------------------------------------
    def test_helper_refusals(self):
        now = time.time_ns()
        for text in ("set 123\n", "set abcdefghijklmnopqrs\n", "set %d extra\n" % now, "hello\n", "",
                     "set 1000000000000000000\n",       # 2001: before 2025
                     "set 4200000000000000000\n",       # 2103: after 2099
                     "set -%d\n" % now, "set %d\n" % (now * 10)):
            with self.subTest(text=text):
                rc, out = self.helper(text, offset=-DAY)
                self.assertEqual(rc, 2, out)
                self.assertRegex(out.splitlines()[0], r"^ilinux-clock ready [0-9]{19}$")
                self.assertIn("ilinux-clock refused:", out)
                self.assertEqual(self.offset(), -DAY)   # the clock was not touched
                self.assertFalse((self.tmp / "clock.sets").exists())

    def test_helper_protocol(self):
        rc, out = self.helper("set %d\nread\n" % time.time_ns(), offset=-DAY)
        self.assertEqual(rc, 0, out)
        lines = out.splitlines()
        self.assertRegex(lines[1], r"^ilinux-clock set [0-9]{19} [0-9]{19}$")
        self.assertRegex(lines[2], r"^ilinux-clock now [0-9]{19}$")
        self.assertLess(abs(self.offset()), 5 * 10**8)


@unittest.skipUnless(shutil.which("ssh"), "no ssh client here")
class ConfigTests(unittest.TestCase):
    def config(self, host):
        out = subprocess.run(["ssh", "-G", "-F", str(CONFIG), host], capture_output=True, text=True, cwd=ROOT,
                             timeout=30, check=True).stdout
        return {line.split(" ", 1)[0]: line.split(" ", 1)[1] for line in out.splitlines() if " " in line}

    def test_omarchy_root_entry(self):
        c = self.config("m5o")
        self.assertEqual(c["user"], "omarchy")
        self.assertEqual(c["hostkeyalias"], "m5-omarchy")
        self.assertEqual(c["userknownhostsfile"], "build/control/known_hosts-omarchy")
        self.assertEqual(c["stricthostkeychecking"], "accept-new")
        self.assertEqual(c["identityfile"], "build/control/m1-control")
        self.assertEqual(c["proxycommand"], "build/control/usb-pipe --log build/native-intake/usb-pipe.log")
        self.assertEqual(c["remoteforward"], "[127.0.0.1]:3128 [127.0.0.1]:3128")   # as ssh -G prints it
        self.assertEqual(c["forwardagent"], "no")

    def test_omarchy_root_ports(self):
        for n in (1, 2, 3):
            c = self.config("m5o-port%d" % n)
            self.assertEqual(c["user"], "omarchy")
            self.assertEqual(c["proxycommand"], "build/control/usb-pipe --port %d --log build/native-intake/usb-pipe.log" % n)

    def test_job039_entries_unchanged(self):
        c = self.config("m5")
        self.assertEqual(c["user"], "root")
        self.assertEqual(c["userknownhostsfile"], "build/control/known_hosts")
        self.assertNotIn("hostkeyalias", c)


if __name__ == "__main__":
    unittest.main(verbosity=2)
