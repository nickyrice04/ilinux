#!/usr/bin/env python3
"""Send stage two of the two-stage boot (the Omarchy root) to the M5's stage one over the USB byte pipe.

Stage one (VM job 049, omarchy-arm64/two-stage) is a small RAM root that the launcher's ramroot
profile uploads through m1n1; it brings up job 039's USB link and waits. This sends it the Omarchy
root (job 045's image, 2.4 GB) over SSH on that link, about five times as fast as m1n1's upload.
Run it from the repository root once stage one's link is up (its panel says "WAITING FOR STAGE TWO"):

    python3 -I tools/m1n1-client/m5-stage2.py --image build/ramroot045-link/ramroot.cpio.zst

1. The image must match native/boot/omarchy-root-manifest.json: its size, then its SHA-256 (a few
   seconds on the M1). Nothing is sent otherwise.
2. One SSH session through tools/m1n1-client/m5-ssh-config, host m5s (stage one: root, this boot's
   host key in build/control/known_hosts-stage1, no port forwarding), runs
   "/usr/local/lib/ilinux/ilinux-stage2 receive SIZE SHA256". Stage one compares the offer with the
   pin it was built with and answers "ready" or "refused: <why>" before a byte is sent.
3. The image goes down the pipe; progress and the rate are printed every few seconds.
4. Stage one reports what it received and its own rate, checks the SHA-256, unpacks the root into
   RAM and soft-reboots into it; each step is printed as it comes.

Exit 0: stage one verified and unpacked stage two and is switching to it (the USB device goes away
and the Omarchy root's comes back, as in attempt 25: clear known_hosts-omarchy and use m5o).
1: stage one refused the offer or the transfer or check failed (its reason is printed; it stays up:
send again). 2: the session failed (no device, no banner, a key or host-key problem: ssh's own
message is above; or the session ended without a result). 3: the image does not match the manifest
(nothing was sent). 4: stage one could not unpack or switch (its reason is printed; it stays up).
Python 3.9 or later, standard library only.
"""
import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REMOTE = "/usr/local/lib/ilinux/ilinux-stage2"
CHUNK = 1 << 20


class Failed(Exception):
    """Carries the exit status."""
    def __init__(self, message, status):
        super().__init__(message)
        self.status = status


def commas(n):
    return format(n, ",")


def check_image(image, manifest, say, hash_image=True):
    """The manifest's (size, sha256) if the image matches it; Failed(3) otherwise."""
    try:
        record = json.loads(Path(manifest).read_text())
        size, sha = int(record["size"]), str(record["sha256"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Failed("cannot read the manifest %s: %s" % (manifest, exc), 3) from None
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha) or size <= 0:
        raise Failed("the manifest %s has no valid size and sha256" % manifest, 3)
    path = Path(image)
    if path.is_symlink() or not path.is_file():
        raise Failed("%s is missing or not a regular file" % image, 3)
    have = path.stat().st_size
    if have != size:
        raise Failed("%s has %s bytes; the manifest pins %s" % (image, commas(have), commas(size)), 3)
    if hash_image:
        say("checking the image's SHA-256 against %s (%s bytes)" % (manifest, commas(size)))
        started = time.monotonic()
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(8 * CHUNK), b""):
                digest.update(block)
        if digest.hexdigest() != sha:
            raise Failed("%s has SHA-256 %s; the manifest pins %s" % (image, digest.hexdigest(), sha), 3)
        say("image PASS: size and SHA-256 equal the manifest (%.1f s)" % (time.monotonic() - started))
    return size, sha


def reader(stream, lines):
    """Lines from ssh's stdout into the queue; None at the end."""
    for raw in iter(stream.readline, b""):
        lines.put(raw.decode("utf-8", "replace").rstrip("\n"))
    lines.put(None)


def next_line(lines, timeout):
    """The next line from the M5, None at the session's end; Failed(2) on silence."""
    try:
        return lines.get(timeout=timeout)
    except queue.Empty:
        raise Failed("no answer from stage one within %.0f s" % timeout, 2) from None


def message(line):
    """'ilinux-stage2 X' -> 'X'; anything else is passed through as is."""
    return line[len("ilinux-stage2 "):] if line.startswith("ilinux-stage2 ") else line


def session(proc, lines, image, size, sha, args, say):
    """The exchange with ilinux-stage2 receive; returns the exit status."""
    # 1. stage one's answer to the offer
    while True:
        line = next_line(lines, args.connect_timeout)
        if line is None:
            raise Failed("the session ended before stage one answered", 2)
        text = message(line)
        if text.startswith("refused: "):
            say("stage one refused: " + text[len("refused: "):])
            return 1
        if text == "ready %d %s" % (size, sha):
            break
        if line.startswith("ilinux-stage2 "):
            raise Failed("unexpected answer from stage one: %r" % line[:200], 2)
        say("M5: " + line[:200])   # something else on the session (a login banner): shown, not parsed
    say("stage one accepted the offer; sending %s bytes" % commas(size))
    # 2. the image
    started = last_t = time.monotonic()
    sent = last_sent = 0
    with open(image, "rb") as f:
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            view = memoryview(block)
            while view:
                try:
                    n = os.write(proc.stdin.fileno(), view)
                except (BrokenPipeError, OSError):
                    proc.stdin = None
                    say("the session closed after %s of %s bytes" % (commas(sent), commas(size)))
                    return finish(proc, lines, args, say, sent_all=False)
                view = view[n:]
                sent += n
            now = time.monotonic()
            if now - last_t >= args.progress:
                rate = (sent - last_sent) / (now - last_t) / 1e6
                average = sent / (now - started) / 1e6
                left = (size - sent) / (average * 1e6) if average > 0 else 0
                say("sent %s of %s MB (%.1f %%), %.1f MB/s now, %.1f MB/s average, about %.0f s left" % (
                    commas(sent // 1000000), commas(size // 1000000), 100.0 * sent / size, rate, average, left))
                last_t, last_sent = now, sent
    elapsed = time.monotonic() - started
    say("sent all %s bytes in %.1f s (%.1f MB/s as the M1 wrote them)" % (commas(sent), elapsed, sent / elapsed / 1e6))
    proc.stdin.close()
    proc.stdin = None
    return finish(proc, lines, args, say, sent_all=True)


# ilinux-stage2 receive's exit status -> this tool's: refused before the transfer (3) or the transfer or
# check failed (4) -> 1; the unpack or switch failed (5) -> 4
REMOTE_STATUS = {3: 1, 4: 1, 5: 4}


def finish(proc, lines, args, say, sent_all):
    """Stage one's report after the stream: received, verified, unpacking, switching or failed."""
    switching = False
    end = time.monotonic() + args.result_timeout
    while True:
        line = next_line(lines, max(1.0, end - time.monotonic()))
        if line is None:
            break
        text = message(line)
        say("stage one: " + text)
        switching = switching or text.startswith("switching:")
    rc = proc.wait()
    if rc == 0 and switching:
        return 0
    if switching:   # the session may drop as stage one's units stop
        say("ssh exited %d after stage one said it was switching" % rc)
        return 0
    if rc in REMOTE_STATUS:
        return REMOTE_STATUS[rc]
    raise Failed("the session ended without a result from stage one (ssh exit %d%s)" % (
        rc, "" if sent_all else ", before the whole image was sent"), 2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--image", required=True, help="stage two: the Omarchy root image (ramroot.cpio.zst)")
    parser.add_argument("--manifest", default="native/boot/omarchy-root-manifest.json",
                        help="its pin, relative to the repository root unless absolute (default: the omarchy profile's)")
    parser.add_argument("--host", default="m5s",
                        help="host in the SSH config (default m5s, stage one; m5s-port1..3 with several ports cabled)")
    parser.add_argument("--config", default="tools/m1n1-client/m5-ssh-config",
                        help="ssh config, relative to the repository root unless absolute")
    parser.add_argument("--progress", type=float, default=5.0, help="seconds between progress lines (default 5)")
    parser.add_argument("--connect-timeout", type=float, default=150.0,
                        help="seconds to wait for the session and stage one's answer (usb-pipe alone waits up to 80)")
    parser.add_argument("--result-timeout", type=float, default=1500.0,
                        help="seconds to wait for stage one's result after the last byte (default 1500)")
    parser.add_argument("--dry-run", action="store_true", help="check the image and print the command; no session")
    parser.add_argument("--ssh", default="ssh", help=argparse.SUPPRESS)   # the offline tests' stand-in
    args = parser.parse_args(argv)

    def say(text):
        print("m5-stage2: " + text, flush=True)

    def resolve(name):
        path = Path(name)
        return path if path.is_absolute() else ROOT / path

    try:
        size, sha = check_image(resolve(args.image), resolve(args.manifest), say)
    except Failed as exc:
        say(str(exc))
        return exc.status
    command = [args.ssh, "-F", str(resolve(args.config)), "-o", "ClearAllForwardings=yes", "-o", "RequestTTY=no",
               args.host, REMOTE, "receive", str(size), sha]
    say("connecting: ssh -F %s %s, then ilinux-stage2 receive %d %s..." % (args.config, args.host, size, sha[:16]))
    if args.dry_run:
        say("dry run: no session opened")
        return 0
    try:
        proc = subprocess.Popen(command, cwd=str(ROOT), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    except OSError as exc:
        say("cannot run ssh: %s" % exc)
        return 2
    lines = queue.Queue()
    threading.Thread(target=reader, args=(proc.stdout, lines), daemon=True).start()
    started = time.monotonic()
    try:
        status = session(proc, lines, resolve(args.image), size, sha, args, say)
    except Failed as exc:
        say(str(exc))
        if exc.status == 2:
            say("ssh's own message, if any, is above. Is the M5 running stage one (panel: WAITING FOR STAGE TWO), "
                "known_hosts-stage1 cleared for this boot, and no other SSH session open on that port?")
        status = exc.status
    except KeyboardInterrupt:
        say("interrupted: stage one reports a short transfer and waits for the next attempt")
        status = 2
    finally:
        if proc.stdin is not None:
            try:
                proc.stdin.close()
            except OSError:
                pass
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    say("%s after %.1f s" % ({0: "PASS: stage one is switching to stage two", 1: "REFUSED or FAILED on the M5",
                               2: "SESSION FAILED", 4: "UNPACK or SWITCH FAILED on the M5"}.get(status, "exit %d" % status),
                              time.monotonic() - started))
    return status


if __name__ == "__main__":
    sys.exit(main())
