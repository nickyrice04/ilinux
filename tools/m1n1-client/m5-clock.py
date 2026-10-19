#!/usr/bin/env python3
"""Set the M5's clock from the M1's over the USB byte pipe, right after connecting.

The M5's RAM root has no clock source (no RTC driver in this boot path, and no route for NTP:
the link carries SSH and the M1's HTTP proxy only), so its clock is wrong after every boot. TLS
certificates then look not yet valid or expired, and pacman, mise and Claude Code fail. Run this
once per boot, from the repository root, after connect-proxy.py is up and before any web access:

    python3 -I tools/m1n1-client/m5-clock.py

It opens one short SSH session through tools/m1n1-client/m5-ssh-config (host m5o, the Omarchy
root's desktop user, port forwarding off) and runs /usr/local/lib/ilinux/set-clock there through
its own sudo rule (VM job 045, LINK=1; it holds also when Omarchy's passwordless grant is off). The
helper says it is ready; only then does this read the
M1's clock and send it; the helper sets the M5's clock, and a second exchange reads it back, so
the result names the M5's error before the step and the residual after it, each bounded by the
measured round trip. One session at a time per port: run it before the interactive session.

Exit 0: the M5's clock is within --tolerance of the M1's. 1: it is not. 2: the session or the
exchange failed (no device, no banner, a key or host-key problem: ssh's own message is above).
3: the M5 refused (its helper or sudo rule is missing, or it rejected the time).
Python 3.9 or later, standard library only.
"""
import argparse
import os
import select
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = "sudo -n /usr/local/lib/ilinux/set-clock"


class Failed(Exception):
    """The exchange failed; carries the exit status."""
    def __init__(self, message, status=2):
        super().__init__(message)
        self.status = status


class Lines:
    """Lines from a pipe, each within a deadline: select on the descriptor, no hidden buffering."""

    def __init__(self, fd):
        self.fd, self.buf = fd, b""

    def read(self, timeout):
        end = time.monotonic() + timeout
        while b"\n" not in self.buf:
            left = end - time.monotonic()
            if left <= 0:
                raise Failed("no answer from the M5 within %.0f s" % timeout)
            ready, _, _ = select.select([self.fd], [], [], left)
            if ready:
                chunk = os.read(self.fd, 4096)
                if not chunk:
                    raise Failed("the session ended before the M5's helper answered")
                self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode("ascii", "replace").strip()


def expect(lines, word, count, timeout):
    """The next "ilinux-clock WORD N..." line's numbers; a refusal or anything else fails."""
    line = lines.read(timeout)
    parts = line.split()
    if parts[:2] in (["ilinux-clock", "refused:"], ["ilinux-clock", "failed:"]):
        raise Failed("the M5 " + line[len("ilinux-clock "):], 3)
    if (len(parts) != 2 + count or parts[:2] != ["ilinux-clock", word]
            or not all(p.isdigit() for p in parts[2:])):
        raise Failed("unexpected line from the M5: %r" % line[:120])
    return [int(p) for p in parts[2:]]


def iso(ns):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ns // 10**9)) + ".%03dZ" % (ns % 10**9 // 10**6)


def span(ns):
    s = abs(ns) / 1e9
    for unit, size in (("days", 86400), ("h", 3600), ("min", 60)):
        if s >= size:
            return "%.1f %s" % (s / size, unit)
    return "%.3f s" % s


def direction(ns):
    return "behind" if ns < 0 else "ahead of"


def exchange(proc, lines, connect_timeout, say):
    """The helper's protocol (set-clock): ready, set, read. Returns (error_before, residual, rtt1, rtt2) in ns."""
    def send(text):
        try:
            os.write(proc.stdin.fileno(), text.encode("ascii"))
        except OSError:
            raise Failed("the session closed while sending to the M5") from None

    started = time.monotonic()
    (m5_ready,) = expect(lines, "ready", 1, connect_timeout)
    m1_ready = time.time_ns()
    say("session open after %.1f s; the M5's clock read %s, %s %s the M1's" % (
        time.monotonic() - started, iso(m5_ready), span(m5_ready - m1_ready), direction(m5_ready - m1_ready)))
    sent = time.time_ns()
    send("set %d\n" % sent)
    before, after = expect(lines, "set", 2, 15)
    rtt1 = time.time_ns() - sent
    error_before = before - sent          # the M5's clock minus the M1's as it was set (to within rtt1)
    say("set: the M5 was %s %s the M1 (to within the %.1f ms round trip); its clock now reads %s" % (
        span(error_before), direction(error_before), rtt1 / 1e6, iso(after)))
    asked = time.time_ns()
    send("read\n")
    (m5_now,) = expect(lines, "now", 1, 15)
    answered = time.time_ns()
    rtt2 = answered - asked
    residual = m5_now - (asked + answered) // 2
    return error_before, residual, rtt1, rtt2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="m5o",
                        help="host in the SSH config (default m5o, the Omarchy root; m5o-port1..3 with several ports cabled)")
    parser.add_argument("--config", default="tools/m1n1-client/m5-ssh-config",
                        help="ssh config, relative to the repository root unless absolute")
    parser.add_argument("--tolerance", type=float, default=1.0,
                        help="largest residual, in seconds, that counts as set (default 1)")
    parser.add_argument("--connect-timeout", type=float, default=150.0,
                        help="seconds to wait for the session and the helper (usb-pipe alone waits up to 80)")
    parser.add_argument("--ssh", default="ssh", help=argparse.SUPPRESS)   # the offline tests' stand-in
    args = parser.parse_args(argv)

    def say(text):
        print("m5-clock: " + text, flush=True)

    config = Path(args.config)
    if not config.is_absolute():
        config = ROOT / config
    command = [args.ssh, "-F", str(config), "-o", "ClearAllForwardings=yes", "-o", "RequestTTY=no",
               args.host, HELPER]
    say("connecting: ssh -F %s %s (no port forwarding), then %s" % (args.config, args.host, HELPER))
    try:
        proc = subprocess.Popen(command, cwd=str(ROOT), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    except OSError as exc:
        say("cannot run ssh: %s" % exc)
        return 2
    status = 2
    try:
        error_before, residual, rtt1, rtt2 = exchange(proc, Lines(proc.stdout.fileno()), args.connect_timeout, say)
        ok = abs(residual) <= args.tolerance * 1e9
        say("check: the M5's clock is %.1f ms %s the M1's (round trip %.1f ms): %s" % (
            abs(residual) / 1e6, direction(residual), rtt2 / 1e6, "PASS" if ok else "FAIL"))
        status = 0 if ok else 1
    except Failed as exc:
        say(str(exc))
        if exc.status == 2:
            say("ssh's own message, if any, is above. Is the M5 running the Omarchy root built with LINK=1, "
                "and no other SSH session open on that port (one at a time)?")
        status = exc.status
    except KeyboardInterrupt:
        say("interrupted")
        status = 2
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            rc = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = proc.wait()
        if rc not in (0, None) and status == 0:
            say("ssh exited %d after a complete exchange" % rc)
    return status


if __name__ == "__main__":
    sys.exit(main())
