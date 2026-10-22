#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31H: precise reset mirrors and bounded exploratory CPU-state observations.

The frozen31G startup, recorder, power observations and deadlines are inherited
unchanged. Mirror and opaque state fields are never effective-entry or execution
claims. Native release requires source pins and VM review.
No installed file, mapping, boot policy or reset-vector register is changed.
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
import smp31g as previous

core = previous.core
require, Refusal = core.require, core.Refusal
CONFIRM = 'START-CPU1-J716C-31H'
RECEIPT = ROOT / 'build/native-intake/attempt31h/consumed.jsonl'
# Only a reviewed release with complete source closure and VM evidence may
# enable the live entrypoint. Synthetic controller tests do not satisfy this.
LIVE_READY = True


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


observer = module('rvbar_observer31h', 'kernel/experiments/smp31h-reset-format/observer.py')
cpu_state = module('cpu_state31h', 'kernel/experiments/smp31h-reset-format/cpu_state.py')


class Controller(previous.Controller):
    """31G starts with precise mirrors and four bounded CPU-state pairs.

    The observer sees the existing get_base/read64/get_exc_count calls. It
    commits a classified row only after that read's immediate guard reply is
    zero. An unexplained reset format stops before mutations. The extra state
    reads are exploratory: public m1n1 supports this access width/location, but
    t6050-specific semantics and never-started-core accessibility are unproved.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state.update(experiment='smp31h', rvbar_observation={},
                          restart_ready=False, cpu_state_permissions={},
                          cpu_state_observation={}, reset_format_gate_passed=False)
        self.cpu_state_tracker = cpu_state.Tracker()

    def preflight(self):
        original = self.p

        def journal(report):
            self.state['rvbar_observation'] = report
            self.journal(dict(self.state))

        observed = observer.ProxyObserver(original, journal=journal)
        self.state['rvbar_observation'] = observed.report()
        self.p = observed
        try:
            super().preflight()
            self.state['rvbar_observation'] = observed.finish()
            report = self.state['rvbar_observation']
            require(report['mirrors_equal'] is True and all(
                row['firmware_format_field_relation'] == 'image_base' and
                row['firmware_format_low_bits_10_1_class'] == 'zero' and
                row['firmware_format_high_bits_63_42_class'] == 'zero'
                for row in report['rows']), 'reset_format_requires_review')
            self.state['reset_format_gate_passed'] = True
            self.journal(dict(self.state))
        except BaseException as exc:
            # A census/interface error can occur outside the proxy adapter.
            # Preserve that original failure while discarding transient words.
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

    def cpu_state_persist(self, summary):
        self.state['cpu_state_observation'] = summary
        self.journal(dict(self.state))

    def prepare_cpu_state_reads(self):
        # The inherited census has bound every cpu-impl-reg base AND its
        # 0x9018 extent to exact live ADT; CPU0 and CPU1 share an active cluster.
        require(not self.state['start_writes_attempted'] and
                self.state['reset_format_gate_passed'] and
                self.state['power_binding'].get('live_adt_bound') is True,
                'cpu_state_binding_missing')
        entry = 256 if self.state['permissions']['primary_exception_level'] == 2 else 192
        for cpu, address in enumerate(cpu_state.ADDRESSES):
            self.state['cpu_state_permissions'][str(cpu)] = False
            self.journal(dict(self.state))
            par = self.p.call((self.helper | core.RX_ALIAS) + entry, address)
            self.clean()
            probe = dict(address=address, physical=address, permission_fault=False,
                         attr=0, shareability=None)
            try:
                previous.permissions.validate_probe(probe, par)
            except ValueError as exc:
                raise Refusal('cpu_state_' + str(exc)) from None
            self.state['cpu_state_permissions'][str(cpu)] = True
            self.journal(dict(self.state))

    def sample_power(self, phase):
        # Preserve PS phases. An error there prevents every additional read.
        super().sample_power(phase)
        if phase == 'before_start':
            self.prepare_cpu_state_reads()
        deadline = self.clock() + 1.0

        def read32(cpu):
            require(type(cpu) is int and cpu in (0, 1) and
                    self.state['cpu_state_permissions'].get(str(cpu)) is True,
                    'cpu_state_read_not_bound')
            address = cpu_state.ADDRESSES[cpu]
            require(self.clock() < deadline, 'cpu_state_observation_deadline')
            self.clean()
            require(self.clock() < deadline, 'cpu_state_observation_deadline')
            if phase == 'before_start':
                require(not self.state['start_writes_attempted'], 'cpu_state_baseline_after_start')
                # First access is guarded, before any secondary-start intent.
                value = self.p.read32(address)
            else:
                require(self.state['start_writes_attempted'] in (1, 2),
                        'cpu_state_sample_before_start')
                # Identical fixed 32-bit helper already published by31G.
                # Never open a global exception-guard window after CPU1 start.
                value = self.p.call((self.helper | core.RX_ALIAS) + previous.READ32_OFFSET,
                                    address)
            require(self.clock() < deadline, 'cpu_state_observation_deadline')
            self.clean()
            require(self.clock() < deadline, 'cpu_state_observation_deadline')
            return value

        fixed_refusal = None
        def checked_read(cpu):
            nonlocal fixed_refusal
            try:
                return read32(cpu)
            except Refusal as exc:
                # Only our fixed controller reasons survive; raw transport
                # exceptions are sanitized by the pure tracker.
                fixed_refusal = str(exc)
                raise
        def checked_persist(summary):
            nonlocal fixed_refusal
            try:
                self.cpu_state_persist(summary)
            except Refusal as exc:
                # An outer controller alarm may interrupt a journal syscall.
                # Preserve its fixed reason as well as the tracker's failure.
                fixed_refusal = str(exc)
                raise
        try:
            self.cpu_state_tracker.sample(phase, checked_read, checked_persist)
        except ValueError as exc:
            raise Refusal(fixed_refusal or str(exc)) from None
        finally:
            # Persist may itself have failed after receiving an earlier copy.
            # Refresh local terminal state without another journal/target call.
            self.state['cpu_state_observation'] = self.cpu_state_tracker.report()


def verify_sources():
    path = ROOT / 'tools/m1n1-client/attempt31h-offline.py'
    require(path.is_file() and not path.is_symlink(), 'source_intake_missing')
    intake = module('intake31h', 'tools/m1n1-client/attempt31h-offline.py')
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

    journal(dict(experiment='smp31h', consumed=True, live_result='NOT RUN'))
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
    result = dict(experiment='smp31h', result='STOP', phase='connect', linux_boot='NOT RUN')

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
            # This must bind31H's local class; importing31G.live would silently
            # select the frozen31G controller instead.
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
    previous.verify_recorder(image)
    source_manifest_sha = verify_sources()
    if not args.live:
        print('OFFLINE PASS: 31H source/image verified; no USB or CPU start; restart_ready=false')
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
        print(json.dumps(dict(experiment='smp31h', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else type(exc).__name__,
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
