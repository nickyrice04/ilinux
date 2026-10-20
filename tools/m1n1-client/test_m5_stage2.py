#!/usr/bin/env python3
"""Offline tests of m5-stage2.py (the M1's sender for the two-stage boot, VM job 049).

A stand-in for ssh records its arguments and plays stage one's ilinux-stage2 receive (the real one
needs Linux, root and systemd; VM job 049's run-qemu.sh runs it over the real USB pipe): it answers the
offer, reads the image, counts and hashes it as stage one does and answers as stage one would, or
refuses, fails a step, stays silent or drops the session, as each case asks. Also: the tool's own
check of the image against the manifest (nothing is sent on a mismatch), the dry run, and
m5-ssh-config's m5s entries as ssh itself reads them (ssh -G).
    python3 -I tools/m1n1-client/test_m5_stage2.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOL = HERE / "m5-stage2.py"
CONFIG = HERE / "m5-ssh-config"

# The stand-in for ssh: argv to a file, then stage one as FAKE_MODE says.
FAKE_SSH = r'''#!@PYTHON@
import hashlib, os, sys, time
open(os.environ["FAKE_SSH_ARGV"], "w").write("\n".join(sys.argv[1:]))
mode = os.environ.get("FAKE_MODE", "ok")
pin_size, pin_sha = int(os.environ["FAKE_PIN_SIZE"]), os.environ["FAKE_PIN_SHA"]
size, sha = int(sys.argv[-2]), sys.argv[-1]
def say(text):
    sys.stdout.write("ilinux-stage2 " + text + "\n"); sys.stdout.flush()
if mode == "unreachable":
    sys.stderr.write("usb-pipe: no matching interface in 80 s\n"); sys.exit(255)
if mode == "silent":
    time.sleep(30); sys.exit(255)
if (size, sha) != (pin_size, pin_sha):
    say("refused: the M1 offers %d bytes, but this stage one is pinned to %d bytes" % (size, pin_size)); sys.exit(3)
if mode == "busy":
    say("refused: busy: another transfer or the switch to stage two is running"); sys.exit(3)
sys.stdout.write("Welcome banner line\n"); sys.stdout.flush()
say("ready %d %s" % (pin_size, pin_sha))
got, h = 0, hashlib.sha256()
limit = 1 << 20 if mode == "drop" else pin_size + 1
while got < limit:
    block = sys.stdin.buffer.read(min(1 << 16, limit - got))
    if not block:
        break
    got += len(block); h.update(block)
    time.sleep(float(os.environ.get("FAKE_DELAY", "0")))   # a slow link, so progress lines appear
open(os.environ["FAKE_SSH_ARGV"] + ".received", "w").write("%d %s" % (got, h.hexdigest()))
if mode == "drop":
    sys.exit(255)          # the link went away mid-transfer: no result
if got != pin_size:
    say("failed: the transfer ended after %d of %d bytes" % (got, pin_size)); sys.exit(4)
say("received %d bytes in 0.1 s (99.0 MB/s)" % got)
if h.hexdigest() != pin_sha or mode == "badsha":
    say("failed: SHA-256 %s of the received image differs from the pin %s" % (h.hexdigest(), pin_sha)); sys.exit(4)
say("verified " + pin_sha)
say("queued: verified (0.1 s at 99.0 MB/s); unpacking next")
say("unpacking: unpacking %d bytes into RAM (/run/nextroot, about 10.3 GiB)" % pin_size)
if mode == "unpackfail":
    say("failed: unpacking failed: bsdtar: Write failed"); sys.exit(5)
say("switching: soft-reboot into stage two: 215,472 entries, 10.3 GiB, unpacked in 10.6 s")
sys.exit(0)
'''


class Stage2Tool(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="m5-stage2-test-"))
        self.image = self.tmp / "ramroot.cpio.zst"
        data = b"\x28\xb5\x2f\xfd" + os.urandom(3 * 1024 * 1024 + 123)
        self.image.write_bytes(data)
        self.size, self.sha = len(data), hashlib.sha256(data).hexdigest()
        self.manifest = self.tmp / "manifest.json"
        self.manifest.write_text(json.dumps({"size": self.size, "sha256": self.sha}))
        self.argv = self.tmp / "argv"
        self.ssh = self.tmp / "ssh"
        self.ssh.write_text(FAKE_SSH.replace("@PYTHON@", sys.executable))
        self.ssh.chmod(0o755)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_tool(self, mode="ok", pin=None, extra=(), timeout=60, delay=0.0):
        env = dict(os.environ, FAKE_SSH_ARGV=str(self.argv), FAKE_MODE=mode, FAKE_DELAY=str(delay),
                   FAKE_PIN_SIZE=str((pin or (self.size, self.sha))[0]), FAKE_PIN_SHA=(pin or (self.size, self.sha))[1])
        args = [sys.executable, "-I", str(TOOL), "--image", str(self.image), "--manifest", str(self.manifest),
                "--ssh", str(self.ssh), "--progress", "0.01"] + list(extra)
        return subprocess.run(args, env=env, capture_output=True, text=True, timeout=timeout)

    def received(self):
        path = Path(str(self.argv) + ".received")
        return path.read_text().split() if path.exists() else None

    def test_success_sends_exactly_the_image_and_reports_the_switch(self):
        r = self.run_tool(delay=0.005)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.received(), [str(self.size), self.sha])
        out = r.stdout
        self.assertIn("image PASS: size and SHA-256 equal the manifest", out)
        self.assertIn("stage one accepted the offer; sending %s bytes" % format(self.size, ","), out)
        self.assertIn("m5-stage2: M5: Welcome banner line", out)     # unknown lines are shown, not parsed
        self.assertIn("sent all %s bytes" % format(self.size, ","), out)
        self.assertIn("stage one: verified " + self.sha, out)
        self.assertIn("stage one: switching: soft-reboot into stage two", out)
        self.assertIn("PASS: stage one is switching to stage two", out)
        self.assertRegex(out, r"sent [0-9,]+ of [0-9,]+ MB \([0-9.]+ %\), [0-9.]+ MB/s now")

    def test_command_line(self):
        self.run_tool()
        argv = self.argv.read_text().split("\n")
        self.assertEqual(argv[0:2], ["-F", str(CONFIG)])
        self.assertEqual(argv[2:6], ["-o", "ClearAllForwardings=yes", "-o", "RequestTTY=no"])
        self.assertEqual(argv[6:], ["m5s", "/usr/local/lib/ilinux/ilinux-stage2", "receive", str(self.size), self.sha])

    def test_host_option(self):
        self.run_tool(extra=("--host", "m5s-port2"))
        self.assertEqual(self.argv.read_text().split("\n")[6], "m5s-port2")

    def test_stage_one_pinned_to_another_image_refuses_before_any_byte(self):
        r = self.run_tool(pin=(self.size + 1, "0" * 64))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("stage one refused: the M1 offers", r.stdout)
        self.assertNotIn("sending", r.stdout)
        self.assertIsNone(self.received())

    def test_busy_refusal(self):
        r = self.run_tool(mode="busy")
        self.assertEqual(r.returncode, 1)
        self.assertIn("stage one refused: busy", r.stdout)

    def test_sha_failure_on_the_m5_is_exit_1(self):
        r = self.run_tool(mode="badsha")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("stage one: failed: SHA-256", r.stdout)
        self.assertIn("REFUSED or FAILED on the M5", r.stdout)

    def test_unpack_failure_on_the_m5_is_exit_4(self):
        r = self.run_tool(mode="unpackfail")
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertIn("stage one: failed: unpacking failed", r.stdout)

    def test_session_dropped_mid_transfer_is_exit_2(self):
        r = self.run_tool(mode="drop")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("SESSION FAILED", r.stdout)

    def test_unreachable_is_exit_2_with_ssh_message(self):
        r = self.run_tool(mode="unreachable")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no matching interface", r.stderr)
        self.assertIn("the session ended before stage one answered", r.stdout)

    def test_silence_times_out(self):
        r = self.run_tool(mode="silent", extra=("--connect-timeout", "1"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no answer from stage one within 1 s", r.stdout)

    def test_image_size_mismatch_sends_nothing(self):
        with self.image.open("ab") as f:
            f.write(b"x")
        r = self.run_tool()
        self.assertEqual(r.returncode, 3)
        self.assertIn("the manifest pins", r.stdout)
        self.assertFalse(self.argv.exists())

    def test_image_content_mismatch_sends_nothing(self):
        data = bytearray(self.image.read_bytes())
        data[len(data) // 2] ^= 0xFF
        self.image.write_bytes(bytes(data))
        r = self.run_tool()
        self.assertEqual(r.returncode, 3)
        self.assertIn("has SHA-256", r.stdout)
        self.assertFalse(self.argv.exists())

    def test_bad_manifest(self):
        self.manifest.write_text("{}")
        r = self.run_tool()
        self.assertEqual(r.returncode, 3)
        self.assertIn("cannot read the manifest", r.stdout)

    def test_dry_run_opens_no_session(self):
        r = self.run_tool(extra=("--dry-run",))
        self.assertEqual(r.returncode, 0)
        self.assertIn("dry run: no session opened", r.stdout)
        self.assertFalse(self.argv.exists())

    def test_symlinked_image_is_refused(self):
        link = self.tmp / "link.zst"
        link.symlink_to(self.image)
        env = dict(os.environ, FAKE_SSH_ARGV=str(self.argv), FAKE_PIN_SIZE=str(self.size), FAKE_PIN_SHA=self.sha)
        r = subprocess.run([sys.executable, "-I", str(TOOL), "--image", str(link), "--manifest", str(self.manifest),
                            "--ssh", str(self.ssh)], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 3)
        self.assertFalse(self.argv.exists())


@unittest.skipUnless(shutil.which("ssh"), "no ssh client")
class SshConfig(unittest.TestCase):
    def options(self, host):
        r = subprocess.run(["ssh", "-G", "-F", str(CONFIG), host], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(r.returncode, 0, r.stderr)
        opts = {}
        for line in r.stdout.splitlines():
            key, _, value = line.partition(" ")
            opts.setdefault(key, []).append(value)
        return opts

    def test_m5s_is_stage_one(self):
        o = self.options("m5s")
        self.assertEqual(o["user"], ["root"])
        self.assertEqual(o["hostkeyalias"], ["m5-stage1"])
        self.assertEqual(o["userknownhostsfile"], ["build/control/known_hosts-stage1"])
        self.assertEqual(o["stricthostkeychecking"], ["accept-new"])
        self.assertEqual(o["identityfile"], ["build/control/m1-control"])
        self.assertEqual(o["clearallforwardings"], ["yes"])
        self.assertNotIn("remoteforward", o)
        self.assertEqual(o["proxycommand"], ["build/control/usb-pipe --log build/native-intake/usb-pipe.log"])

    def test_m5s_ports(self):
        for n in (1, 2, 3):
            o = self.options("m5s-port%d" % n)
            self.assertEqual(o["proxycommand"], ["build/control/usb-pipe --port %d --log build/native-intake/usb-pipe.log" % n])
            self.assertEqual(o["hostkeyalias"], ["m5-stage1"])

    def test_m5o_unchanged(self):
        o = self.options("m5o")
        self.assertEqual(o["user"], ["omarchy"])
        self.assertEqual(o["hostkeyalias"], ["m5-omarchy"])
        self.assertIn("remoteforward", o)


if __name__ == "__main__":
    unittest.main(verbosity=2)
