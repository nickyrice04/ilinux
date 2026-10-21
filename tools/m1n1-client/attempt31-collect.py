#!/usr/bin/env python3
"""Bounded attempt-31 collector. Key verification precedes every observation.

arm starts a 600-second observation deadline, immediately at the root switch.
latency runs the image-pinned RAM-only compositor crossover; desktop reads the
existing desktop probe. This never launches Linux, changes boot policy, or
extends the deadline. Keep journals/results private under ignored build/.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
FP = r"SHA256:[A-Za-z0-9+/]{43}"


def verify_key(journal, known_hosts):
    # Both stages use the same unit name; the root's generated-key comment
    # distinguishes it from the retained stage-one event. Reject ambiguity.
    keys = set(re.findall(r"\b256 (" + FP + r") ilinux-m5-boot \(ED25519\)", journal))
    stage1 = set(re.findall(r"\b256 (" + FP + r") ilinux-m5-stage1 \(ED25519\)", journal))
    if len(keys) != 1 or keys & stage1:
        raise ValueError("need one distinct stage-two host key in this run's journal")
    rows = [line.split() for line in known_hosts.splitlines() if line and not line.startswith('#')]
    if len(rows) != 1 or len(rows[0]) != 3 or rows[0][:2] != ['m5-omarchy','ssh-ed25519']:
        raise ValueError("expected one exact m5-omarchy ed25519 known-host entry")
    raw = base64.b64decode(rows[0][2], validate=True)
    digest = 'SHA256:' + base64.b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
    if keys != {digest}:
        raise ValueError("root journal key and known-host key differ; no SSH observation")


def remaining(state, now=None):
    now = time.monotonic() if now is None else now
    start = state.get('start_monotonic')
    if state.get('attempt') != 31 or type(start) not in (int,float) or not 0 <= now-start < 600:
        raise ValueError("observation window expired or state invalid; do not re-arm")
    return 600 - (now-start)


def private_path(value):
    p=Path(value).resolve()
    p.relative_to(ROOT/'build')
    return p


def completion(text):
    # systemd --pipe also forwards ExecStopPost's output. Require its verified
    # reset after the main collector's completion; do not discard unknown text.
    lines = [s for s in text.splitlines() if s.strip()]
    if not lines or lines[-1] != 'COPY31_REFERENCE_PATH_RESTORED':
        raise ValueError('missing independent reset receipt')
    rows = [json.loads(s) for s in lines[:-1]]
    if len(rows) < 2 or rows[-1].get('event') != 'mode' or rows[-1].get('enabled') != 0:
        raise ValueError('missing independent mode-zero receipt')
    done = rows[-2]
    if (sum(r.get('event') == 'done' for r in rows) != 1
            or done.get('event') != 'done' or done.get('status') != 'COPY31_OBSERVED'
            or done.get('frequency_writes') is not False
            or done.get('modules_loaded') is not False
            or done.get('renderer_changes') != 'RAM-only A/B, reference path restored'):
        raise ValueError('missing latency completion record; keep evidence and stop')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['arm','latency','desktop'])
    parser.add_argument('--state',required=True)
    parser.add_argument('--journal')
    parser.add_argument('--output')
    args=parser.parse_args(argv)
    statepath=private_path(args.state)
    if args.mode == 'arm':
        statepath.parent.mkdir(parents=True,exist_ok=True)
        with statepath.open('x') as f:
            json.dump({'attempt':31,'start_monotonic':time.monotonic()},f)
        print('Attempt31 window armed once: 600 seconds; no USB/SSH access.')
        return 0
    if not args.journal or not args.output:
        parser.error('collection requires this run\'s --journal and private --output')
    left=remaining(json.loads(statepath.read_text()))
    required=380 if args.mode == 'latency' else 45
    if left < required:
        raise ValueError('insufficient time left for this observation; return to macOS')
    journal=private_path(args.journal)
    if journal.stat().st_size > 16*1024*1024:
        raise ValueError('journal exceeds collection bound')
    verify_key(journal.read_text(errors='replace'),(ROOT/'build/control/known_hosts-omarchy').read_text())
    out=private_path(args.output)
    err=out.with_suffix(out.suffix+'.stderr')
    ssh=['ssh','-F','tools/m1n1-client/m5-ssh-config','-o','BatchMode=yes',
         '-o','StrictHostKeyChecking=yes','-o','ClearAllForwardings=yes',
         '-o','ConnectionAttempts=1','m5o']
    if args.mode == 'latency':
        remote=('sudo -n systemd-run --unit=ilinux-desktop31 --collect --wait --pipe '
                '--property=RuntimeMaxSec=300 --property=TimeoutStopSec=40 '
                '--property=KillMode=control-group '
                +shlex.quote('--property=ExecStopPost=/usr/bin/python3 -I /usr/local/lib/ilinux-desktop31/restore.py')
                +' /usr/bin/python3 -I /usr/local/lib/ilinux-desktop31/collect.py')
        data=None
    else:
        remote='timeout --signal=TERM --kill-after=3s 40s python3 -I -'
        data=(ROOT/'tools/m1n1-client/m5-probes/inspect_desktop.py').read_bytes()
    # Exclusive outputs prevent accidentally rerunning a consumed collection.
    with out.open('xb') as stdout, err.open('xb') as stderr:
        proc=subprocess.Popen(ssh+[remote],cwd=ROOT,stdin=subprocess.PIPE if data else subprocess.DEVNULL,
                              stdout=stdout,stderr=stderr,start_new_session=True)
        try:
            proc.communicate(input=data,timeout=min(required,remaining(json.loads(statepath.read_text()))))
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL); proc.wait()
        if proc.returncode:
            raise ValueError('collection failed; keep private output and stop, no retry')
    if args.mode == 'latency':
        completion(out.read_text())
    print('Collection complete; %.0f seconds remain in the fixed observation window.' % remaining(json.loads(statepath.read_text())))
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        print('STOP: '+str(exc),file=sys.stderr); sys.exit(3)
