#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31J: classify bounded host discovery before consuming the native campaign.

All target behavior is inherited unchanged from 31I. Connection progress has
its own exclusive journal. Only a verified primary permits client import,
native reservation and one serial open; no connection retry follows that open.
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
import smp31i as previous

core = previous.core
require, Refusal = core.require, core.Refusal
verify_recorder = previous.verify_recorder
CONFIRM = 'START-CPU1-J716C-31J'
RECEIPT = ROOT / 'build/native-intake/attempt31j/consumed.jsonl'
CONNECTION_RECEIPT = ROOT / 'build/native-intake/attempt31j/connection.jsonl'
LIVE_READY = True


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


connection = module('usb_connection31j', 'tools/m1n1-client/usb_connection31j.py')


class Controller(previous.Controller):
    """Change the campaign label only; every target method remains inherited."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state['experiment'] = 'smp31j'


def verify_sources():
    path = ROOT / 'tools/m1n1-client/attempt31j-offline.py'
    require(path.is_file() and not path.is_symlink(), 'source_intake_missing')
    intake = module('intake31j', 'tools/m1n1-client/attempt31j-offline.py')
    try:
        _, digest = intake.source_pins(ROOT)
        return digest
    except ValueError as exc:
        raise Refusal(str(exc)) from None


def reserve_journal(path, initial, on_created=None):
    """Create one durable receipt; never remove it even if initialization fails."""
    require(path.is_absolute() and path.is_relative_to(ROOT / 'build'), 'receipt_location')
    for parent in reversed(path.parents):
        if parent == ROOT or parent.is_relative_to(ROOT):
            require(not parent.is_symlink(), 'receipt_symlink')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    stream = None
    try:
        if on_created is not None:
            on_created()  # Local state only: reservation exists from this point.
        stream = os.fdopen(fd, 'w')

        def journal(state):
            stream.write(json.dumps(state, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

        journal(initial)
        dirfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        return stream, journal
    except BaseException:
        try:
            if stream is not None:
                stream.close()
            else:
                os.close(fd)
        except BaseException:
            pass  # Preserve the original reservation failure or outer deadline.
        raise


def reserve(on_created=None):
    return reserve_journal(RECEIPT,
        dict(experiment='smp31j', consumed=True, live_result='NOT RUN'), on_created)


def load_client(client):
    # Called only after successful host-only discovery. Never import setup.
    sys.path.insert(0, str(client / 'proxyclient'))
    from m1n1.proxy import M1N1Proxy, UartInterface, Serial
    return Serial, UartInterface, M1N1Proxy


def snapshot(value):
    return json.loads(json.dumps(value))


def verify_client(client):
    pin = subprocess.check_output(['git', '-C', str(client), 'rev-parse', 'HEAD'],
                                  text=True, timeout=5).strip()
    dirty = subprocess.check_output(['git', '-C', str(client), 'status', '--porcelain',
                                     '--untracked-files=all'], timeout=5)
    require(pin == core.census.launch.M1N1_COMMIT and not dirty, 'client_revision_or_dirty')


def live(image, client):
    require(LIVE_READY, 'native_release_not_ready')
    # Direct callers must pass the same immutable-input gates as the CLI.
    verify_recorder(image)
    pins = verify_sources()
    verify_client(client)
    state = dict(schema='connection31j', phase='connection_reservation',
        discovery_started=False, discovery_completed=False, discovery_observation={},
        discovery_scope='cached_registry_only', source_recheck_passed=False,
        client_import_attempted=False, client_import_returned=False,
        native_reservation_attempted=False, native_attempt_consumed=False,
        serial_open_attempted=False, serial_open_returned=False,
        uart_init_attempted=False, uart_init_returned=False,
        proxy_init_attempted=False, proxy_init_returned=False,
        controller_construction_attempted=False, controller_constructed=False,
        transport_close_attempted=False, transport_closed=False,
        connection_journal_failed=False, native_journal_failed=False)
    result = dict(experiment='smp31j', result='STOP', phase='connect', linux_boot='NOT RUN')
    transport = controller = cstream = nstream = cjournal = njournal = None

    def timeout(*_):
        raise Refusal('controller_deadline')

    def persist_connection(phase=None, **fields):
        if phase is not None:
            state['phase'] = phase
        state.update(fields)
        try:
            cjournal(dict(experiment='smp31j', connection=snapshot(state),
                native_attempt_consumed=state['native_attempt_consumed']))
        except BaseException:
            state['connection_journal_failed'] = True
            raise

    def progress(report):
        # Retain the last prefix even if its following disk write is interrupted.
        state['discovery_observation'] = snapshot(report)
        persist_connection('discovery')

    def consumed():
        state['native_attempt_consumed'] = True

    def native_journal(value):
        try:
            row = dict(value, experiment='smp31j', connection=snapshot(state),
                       native_attempt_consumed=state['native_attempt_consumed'])
            njournal(row)
        except Refusal:
            state['native_journal_failed'] = True
            raise
        except (Exception, KeyboardInterrupt) as exc:
            state['native_journal_failed'] = True
            if isinstance(exc, KeyboardInterrupt):
                raise
            raise Refusal('native_journal_failed') from None

    start = time.monotonic()
    old = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    try:
        cstream, cjournal = reserve_journal(CONNECTION_RECEIPT,
            dict(experiment='smp31j', connection=snapshot(state), native_attempt_consumed=False))
        with contextlib.redirect_stdout(core.Discard()), contextlib.redirect_stderr(core.Discard()):
            persist_connection('discovery', discovery_started=True)
            try:
                selected, report = connection.discover_primary(progress=progress)
            except connection.ConnectionRefusal as exc:
                state['discovery_observation'] = snapshot(exc.report)
                causes = getattr(exc, 'interruptions', (getattr(exc, 'callback_exception', None),))
                for cause in causes:
                    if isinstance(cause, (Refusal, KeyboardInterrupt)):
                        raise cause from None
                raise
            state['discovery_observation'] = snapshot(report)
            require(report.get('ready') is True, 'primary_discovery_not_ready')
            persist_connection('discovery_complete', discovery_completed=True)
            persist_connection('source_recheck')
            require(verify_sources() == pins, 'sources_changed_during_discovery')
            persist_connection('client_pin_recheck', source_recheck_passed=True)
            verify_client(client)
            persist_connection('client_import', client_import_attempted=True)
            Serial, UartInterface, M1N1Proxy = load_client(client)
            persist_connection('client_import_complete', client_import_returned=True)
            persist_connection('native_reservation', native_reservation_attempted=True)
            nstream, njournal = reserve(on_created=consumed)
            persist_connection('serial_open', serial_open_attempted=True)
            transport = Serial(selected, UartInterface.DEFAULT_BAUD_RATE, timeout=2, write_timeout=2)
            persist_connection('serial_open_returned', serial_open_returned=True)
            persist_connection('uart_init', uart_init_attempted=True)
            iface = UartInterface(device=transport)
            persist_connection('uart_init_returned', uart_init_returned=True)
            iface.tty_enable = False
            iface.dev.timeout = 2
            iface.dev.write_timeout = 2
            persist_connection('proxy_init', proxy_init_attempted=True)
            proxy = M1N1Proxy(iface)
            persist_connection('proxy_init_returned', proxy_init_returned=True)
            persist_connection('controller_construction', controller_construction_attempted=True)
            controller = Controller(iface, proxy, image, native_journal)
            persist_connection('controller_run', controller_constructed=True)
            result = controller.run()
            persist_connection('controller_finished')
    except (Exception, KeyboardInterrupt) as exc:
        result = dict(controller.state) if controller is not None else result
        result['result'] = 'STOP'
        if controller is None:
            result['phase'] = state['phase']
        if isinstance(exc, Refusal):
            reason = str(exc)
        elif isinstance(exc, connection.ConnectionRefusal):
            reason = exc.reason
        elif isinstance(exc, KeyboardInterrupt):
            reason = 'controller_interrupted'
        elif isinstance(exc, core.census.CensusRefusal):
            reason = 'census_precondition'
        elif isinstance(exc, FileExistsError) and state['phase'] == 'native_reservation':
            reason = 'native_receipt_already_exists'
        elif isinstance(exc, FileExistsError) and state['phase'] == 'connection_reservation':
            reason = 'connection_receipt_already_exists'
        elif state['connection_journal_failed']:
            reason = 'connection_journal_failed'
        else:
            reason = state['phase'] + '_failed'
        result['reason'] = reason
        if reason == 'controller_deadline':
            result['controller_deadline_observed'] = True
    finally:
        def finalization_failure(exc, fallback):
            if isinstance(exc, Refusal) and str(exc) == 'controller_deadline':
                label = 'controller_deadline'
                result['controller_deadline_observed'] = True
            elif isinstance(exc, KeyboardInterrupt):
                label = 'controller_interrupted'
                result['controller_interruption_observed'] = True
            else:
                label = fallback
            result['result'] = 'STOP'
            result.setdefault('finalization_error', label)
            result.setdefault('reason', label)

        if transport is not None:
            state['transport_close_attempted'] = True
            try:
                transport.close()
                state['transport_closed'] = True
            except (Exception, KeyboardInterrupt) as exc:
                result['transport_close_error'] = 'transport_close_failed'
                finalization_failure(exc, 'transport_close_failed')
        result.update(connection=snapshot(state), native_attempt_consumed=state['native_attempt_consumed'],
            source_manifest_sha256=pins, controller_elapsed_seconds=round(time.monotonic() - start, 3))
        # A failed Serial constructor may have opened a device before raising.
        # Only a never-attempted open establishes a zero count.
        if not state['serial_open_attempted']:
            result['device_opens'] = 0
        for label, journal in (('native', njournal), ('connection', cjournal)):
            if journal is not None:
                try:
                    journal(result)
                except (Exception, KeyboardInterrupt) as exc:
                    state[label + '_journal_failed'] = True
                    result.update(result='STOP', connection=snapshot(state))
                    finalization_failure(exc, label + '_journal_failed')
        for stream in (nstream, cstream):
            if stream is not None:
                try:
                    stream.close()
                except (Exception, KeyboardInterrupt) as exc:
                    finalization_failure(exc, 'journal_close_failed')
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refusal('arguments')


def main():
    p = Parser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--live', action='store_true')
    p.add_argument('--confirm')
    p.add_argument('--m1n1', type=Path, default=ROOT / 'third_party/m1n1')
    args = p.parse_args()
    require(not args.image.is_symlink() and args.image.is_file(), 'image_file')
    image = args.image.read_bytes()
    if not args.live:
        verify_recorder(image)
        verify_sources()
        print('OFFLINE PASS: 31J source/image verified; no discovery or USB open; restart_ready=false')
        return 0
    require(args.confirm == CONFIRM, 'confirmation')
    result = live(image, args.m1n1)
    print(json.dumps(result, indent=2))
    return 0 if result['result'] == 'CPU1_ENTRY_AND_REQUESTS_PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps(dict(experiment='smp31j', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else (
                'controller_interrupted' if isinstance(exc, KeyboardInterrupt) else 'input_or_setup_failed'),
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
