#!/usr/bin/env python3
"""Fixed 31C command with a separate 65-second controller-process deadline.

No USB logic here. Child success is not proof of macOS return. Output files
are exclusive; never force, erase or retry them during a native session.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/native-intake/attempt31c'


def wait_bounded(proc, seconds=65):
    try:
        return proc.wait(timeout=seconds), False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=2)
        return 124, True


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--confirm', required=True)
    a = p.parse_args()
    if a.confirm != 'START-CPU1-J716C-31C':
        p.error('requires the exact 31C confirmation')
    # Resolving a link here could replace evidence elsewhere. Refuse every
    # symlink parent and create only the fixed workspace output directory.
    for path in (ROOT / 'build', ROOT / 'build/native-intake', OUT):
        if path.is_symlink(): raise ValueError('output_symlink')
    OUT.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with open(OUT / 'supervisor-once.json', 'x') as once:
        json.dump({'experiment':'smp31c', 'consumed':True}, once)
        once.flush(); os.fsync(once.fileno())
    with open(OUT / 'controller.json', 'xb') as stdout, open(OUT / 'controller.stderr', 'xb') as stderr:
        proc = subprocess.Popen([str(ROOT / 'tools/m1n1-client/run.sh'),
            str(ROOT / 'native/boot/smp31c.py'), '--image', str(a.image.absolute()),
            '--live', '--confirm', a.confirm], stdout=stdout, stderr=stderr,
            stdin=subprocess.DEVNULL, cwd=ROOT, start_new_session=True)
        try:
            rc, expired = wait_bounded(proc)
        except BaseException:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try: proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=2)
            raise
    result = dict(experiment='smp31c', controller_exit=rc, supervisor_deadline=expired,
                  elapsed_seconds=round(time.monotonic() - start, 3),
                  action='power off M5 and return to Macintosh HD; no retry')
    with open(OUT / 'supervisor-result.json', 'x') as file:
        json.dump(result, file, indent=2)
    print(json.dumps(result, indent=2))
    return rc


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({'result':'STOP', 'reason':type(exc).__name__,
                          'action':'return to Macintosh HD; do not retry'}))
        raise SystemExit(1)
