#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31I: firmware-backed readback predicate and inherited bounded observations.

This campaign adds no target operation to 31H. It separates the validated
readback comparison field from uninterpreted upper bits. Neither a matching
mirror nor the opaque core-state values establish an effective reset entry.
Consumed 31H and all earlier controllers remain unchanged.
"""
import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import smp31h as previous

startup = previous.previous  # Frozen 31G preflight; 31H's stricter gate is not called.
core = previous.core
require, Refusal = core.require, core.Refusal
observer = previous.observer
verify_recorder = startup.verify_recorder
CONFIRM = 'START-CPU1-J716C-31I'
RECEIPT = ROOT / 'build/native-intake/attempt31i/consumed.jsonl'
LIVE_READY = True


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


gate = module('readback_gate31i', 'kernel/experiments/smp31i-readback/gate.py')


class Controller(previous.Controller):
    """Reuse 31H's tested reads, starts, recorder and deadlines unchanged."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state.update(experiment='smp31i', reset_readback_decision={})

    def preflight(self):
        original = self.p
        def journal(report):
            self.state['rvbar_observation'] = report
            self.journal(dict(self.state))
        observed = observer.ProxyObserver(original, journal=journal)
        self.state['rvbar_observation'] = observed.report()
        self.p = observed
        try:
            # Explicit parent selection is intentional: no catch-and-continue
            # after 31H's refusal, no process-global patches and no second census.
            startup.Controller.preflight(self)
            report = observed.finish()
            self.state['rvbar_observation'] = report
            try:
                decision = gate.validate(report)
            except ValueError as exc:
                raise Refusal(str(exc)) from None
            self.state['reset_readback_decision'] = decision
            self.state['reset_format_gate_passed'] = True
            self.journal(dict(self.state))
        except BaseException as exc:
            try:
                observed.abort()
            except BaseException:
                pass
            self.state['rvbar_observation'] = observed.report()
            if isinstance(exc, observer.ObservationError):
                raise Refusal(str(exc)) from None
            raise
        finally:
            self.p = original


def verify_sources():
    path = ROOT / 'tools/m1n1-client/attempt31i-offline.py'
    require(path.is_file() and not path.is_symlink(), 'source_intake_missing')
    intake = module('intake31i', 'tools/m1n1-client/attempt31i-offline.py')
    try:
        _, digest = intake.source_pins(ROOT)
        return digest
    except ValueError as exc:
        raise Refusal(str(exc)) from None


def reserve(path=None):
    path = RECEIPT if path is None else path
    require(path.is_absolute() and path.is_relative_to(ROOT / 'build'), 'receipt_location')
    for parent in reversed(path.parents):
        if parent == ROOT or parent.is_relative_to(ROOT):
            require(not parent.is_symlink(), 'receipt_symlink')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    stream = os.fdopen(fd, 'w')

    def journal(state):
        stream.write(json.dumps(state, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())

    journal(dict(experiment='smp31i', consumed=True, live_result='NOT RUN'))
    dirfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)
    return stream, journal


def live(image, client):
    require(LIVE_READY, 'native_release_not_ready')
    pin = subprocess.check_output(['git', '-C', str(client), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(client), 'status', '--porcelain', '--untracked-files=no'])
    require(pin == core.census.launch.M1N1_COMMIT and not dirty, 'client_revision_or_dirty')
    stream, journal = reserve()
    transport = controller = None
    result = dict(experiment='smp31i', result='STOP', phase='connect', linux_boot='NOT RUN')

    def timeout(*_):
        raise Refusal('controller_deadline')

    old = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    start = time.monotonic()
    try:
        with contextlib.redirect_stdout(core.Discard()), contextlib.redirect_stderr(core.Discard()):
            sys.path.insert(0, str(client / 'proxyclient'))
            from m1n1.proxy import M1N1Proxy, UartInterface, Serial
            selected = core.census.launch.usb_identity.select_primary(core.census.launch.usb_identity.discover(), 'auto')
            transport = Serial(selected, UartInterface.DEFAULT_BAUD_RATE, timeout=2, write_timeout=2)
            iface = UartInterface(device=transport)
            iface.tty_enable = False
            iface.dev.timeout = 2
            iface.dev.write_timeout = 2
            # This must bind 31I's local class; importing 31H.live would silently
            # select the consumed 31H controller instead.
            controller = Controller(iface, M1N1Proxy(iface), image, journal)
            result = controller.run()
    except (Exception, KeyboardInterrupt) as exc:
        result = dict(controller.state) if controller is not None else result
        result['result'] = 'STOP'
        result['reason'] = str(exc) if isinstance(exc, Refusal) else (
            'census_precondition' if isinstance(exc, core.census.CensusRefusal) else type(exc).__name__)
    finally:
        try:
            if transport is not None:
                transport.close()
        except Exception:
            result.update(result='STOP', reason='transport_close')
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
        result['controller_elapsed_seconds'] = round(time.monotonic() - start, 3)
        journal(result)
        stream.close()
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--live', action='store_true')
    p.add_argument('--confirm')
    p.add_argument('--m1n1', type=Path, default=ROOT / 'third_party/m1n1')
    args = p.parse_args()
    require(not args.image.is_symlink() and args.image.is_file(), 'image_file')
    image = args.image.read_bytes()
    verify_recorder(image)
    source_manifest_sha = verify_sources()
    if not args.live:
        print('OFFLINE PASS: 31I source/image verified; no USB or CPU start; restart_ready=false')
        return 0
    require(args.confirm == CONFIRM, 'confirmation')
    require(LIVE_READY, 'native_release_not_ready')
    result = live(image, args.m1n1)
    result['source_manifest_sha256'] = source_manifest_sha
    print(json.dumps(result, indent=2))
    return 0 if result['result'] == 'CPU1_ENTRY_AND_REQUESTS_PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps(dict(experiment='smp31i', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else type(exc).__name__,
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
