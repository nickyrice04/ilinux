#!/usr/bin/env python3
"""Run a compositor with a bounded llvmpipe worker count on available CPUs.

No affinity, resolution, graphics backend or global environment is changed.
Opt-in wrapper only; use before starting the compositor, not after its pool
has initialized. An inherited LP_NUM_THREADS value is deliberately replaced.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys


def parse_cpus(text):
    if not re.fullmatch(r'[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*', text.strip()):
        raise ValueError('invalid CPU list')
    cpus = set()
    for part in text.strip().split(','):
        ends = [int(x) for x in part.split('-')]
        lo, hi = ends[0], ends[-1]
        if lo > hi or hi > 4095:
            raise ValueError('CPU list outside bounds')
        cpus.update(range(lo, hi + 1))
    return cpus


def policy(online, allowed):
    available = sorted(online & allowed)
    if not available:
        raise ValueError('no online allowed CPUs')
    # Zero keeps synchronous rasterization on a single CPU. Reserve one CPU's
    # worth of capacity; four workers is a cap, not a measured native optimum.
    return {'available_cpus': available, 'lp_num_threads': min(4, len(available) - 1),
            'policy': 'online-affinity-cap4-v1'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report-only', action='store_true')
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    if sys.platform != 'linux':
        p.error('Linux only')
    result = policy(parse_cpus(Path('/sys/devices/system/cpu/online').read_text()),
                    set(os.sched_getaffinity(0)))
    print(json.dumps(result, sort_keys=True), file=sys.stderr, flush=True)
    if a.report_only:
        return
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command:
        p.error('a compositor command is required')
    env = os.environ.copy()
    env['LP_NUM_THREADS'] = str(result['lp_num_threads'])
    os.execvpe(command[0], command, env)


if __name__ == '__main__':
    main()
