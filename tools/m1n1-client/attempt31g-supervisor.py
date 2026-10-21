#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the fixed 31G controller once, with an independent 65-second deadline.

This is the live launcher, not the offline intake. No USB operations exist in
this parent. Exclusive local evidence is retained even on child failure; no
retry, reconnect, target cleanup, or macOS/boot-setting operation is attempted.
The separate human 90-second return timer is still required.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CONFIRM = 'START-CPU1-J716C-31G'
DEADLINE_SECONDS = 65
TERMINATION_SECONDS = 2
ACTION = 'power off M5 and return to Macintosh HD; no retry'
FILES = ('supervisor-once.json', 'consumed.jsonl', 'controller.json',
         'controller.stderr', 'supervisor-result.json')
REQUIRED_SOURCES = frozenset({
    'native/boot/smp31g.py', 'native/boot/smp31b.py',
    'native/boot/smp31c.py', 'native/boot/smp31d.py',
    'tools/m1n1-client/attempt31g-supervisor.py',
    'tools/m1n1-client/run.sh', 'tools/m1n1-client/pin_check.py',
})


class Refusal(Exception):
    """Only fixed, non-sensitive labels reach public output."""


class DeadlineTerminationFailure(Exception):
    """The deadline fired, but child termination could not be confirmed."""


def require(ok, label):
    if not ok:
        raise Refusal(label)


def no_symlink(path):
    require(path.is_relative_to(ROOT), 'path_outside_workspace')
    for item in (path, *path.parents):
        if item == ROOT or item.is_relative_to(ROOT):
            require(not item.is_symlink(), 'workspace_symlink')


def verify_sources():
    """Do not import the controller merely to check its own digest."""
    manifest = ROOT / 'native/boot/attempt31g/source-sha256.txt'
    no_symlink(manifest)
    require(manifest.is_file() and manifest.stat().st_size <= 65536,
            'source_manifest')
    data = manifest.read_bytes()
    seen = set()
    try:
        lines = data.decode('ascii').splitlines()
    except UnicodeDecodeError:
        raise Refusal('source_manifest_syntax') from None
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        require(match is not None, 'source_manifest_syntax')
        digest, name = match.groups()
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts
                and relative.as_posix() == name and name not in seen,
                'source_manifest_path')
        path = ROOT / relative
        no_symlink(path)
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                'source_digest_mismatch')
        seen.add(name)
    require(REQUIRED_SOURCES <= seen, 'source_manifest_incomplete')
    return hashlib.sha256(data).hexdigest()


def durable_json(path, value):
    """Exclusive creation never follows or overwrites an earlier receipt."""
    no_symlink(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    dirfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def open_capture(path):
    no_symlink(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    return os.fdopen(fd, 'wb')


def signal_group(proc, sig):
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        # A child may exit between TimeoutExpired/poll and killpg. Reap it;
        # preserve the expired outcome rather than treating this as success.
        pass


def stop_child(proc):
    signal_group(proc, signal.SIGTERM)
    try:
        proc.wait(timeout=TERMINATION_SECONDS)
    except subprocess.TimeoutExpired:
        signal_group(proc, signal.SIGKILL)
        proc.wait(timeout=TERMINATION_SECONDS)


def wait_bounded(proc, seconds=DEADLINE_SECONDS):
    """seconds is injectable for offline tests, never a command-line option."""
    try:
        return proc.wait(timeout=seconds), False
    except subprocess.TimeoutExpired:
        try:
            stop_child(proc)
        except (Exception, KeyboardInterrupt):
            raise DeadlineTerminationFailure() from None
        return 124, True


def run(image):
    pins = verify_sources()
    out = ROOT / 'build/native-intake/attempt31g'
    no_symlink(out)
    out.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        path = out / name
        no_symlink(path)
        require(not path.exists(), 'attempt_already_reserved')
    start = time.monotonic()
    durable_json(out / 'supervisor-once.json', {
        'experiment': 'smp31g', 'consumed': True,
        'source_manifest_sha256': pins,
    })
    proc = None
    rc, expired, reason = None, False, 'supervisor_failure'
    supervisor_exit = 1
    try:
        with open_capture(out / 'controller.json') as stdout, \
                open_capture(out / 'controller.stderr') as stderr:
            require(verify_sources() == pins, 'sources_changed_before_spawn')
            proc = subprocess.Popen([
                str(ROOT / 'tools/m1n1-client/run.sh'),
                str(ROOT / 'native/boot/smp31g.py'), '--image', str(image.absolute()),
                '--live', '--confirm', CONFIRM,
            ], stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                cwd=ROOT, start_new_session=True)
            rc, expired = wait_bounded(proc)
            supervisor_exit = rc
            reason = 'controller_deadline' if expired else 'controller_exited'
    except (Exception, KeyboardInterrupt) as exc:
        supervisor_exit = 1
        reason = 'supervisor_interrupted' if isinstance(exc, KeyboardInterrupt) else (
            str(exc) if isinstance(exc, Refusal) else 'supervisor_failure')
        if isinstance(exc, DeadlineTerminationFailure):
            expired, supervisor_exit = True, 124
            reason = 'child_termination_unconfirmed'
        elif proc is not None and proc.poll() is None:
            try:
                stop_child(proc)
            except (Exception, KeyboardInterrupt):
                # Target state stays unknown. Never try another controller.
                reason = 'child_termination_unconfirmed'
    result = {
        'experiment': 'smp31g', 'controller_exit': rc,
        'supervisor_exit': supervisor_exit,
        'controller_started': proc is not None,
        'supervisor_deadline': expired, 'supervisor_reason': reason,
        'elapsed_seconds': round(time.monotonic() - start, 3),
        'source_manifest_sha256': pins,
        'action': ACTION,
    }
    durable_json(out / 'supervisor-result.json', result)
    print(json.dumps(result, indent=2))
    return supervisor_exit


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--confirm', required=True)
    args = parser.parse_args(argv)
    require(args.confirm == CONFIRM, 'confirmation')
    return run(args.image)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({'result': 'STOP',
                          'reason': str(exc) if isinstance(exc, Refusal)
                          else ('supervisor_interrupted' if isinstance(exc, KeyboardInterrupt)
                                else 'supervisor_failure'),
                          'action': ACTION}))
        raise SystemExit(1)
