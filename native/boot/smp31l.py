#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31L: Normal-memory prefixes before the existing Device-memory records.

The reset destination and both CPU1 start stores are unchanged. Original code
only patches loaded RAM after exact-image, freshness and translation checks.
Any cold-entry evidence stops the campaign; there is no cold-path continuation.
"""
import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import smp31k as previous
import smp31g as vector

core = previous.core
require, Refusal = core.require, core.Refusal
CONFIRM = 'START-CPU1-J716C-31L'
RECEIPT = ROOT / 'build/native-intake/attempt31l/consumed.jsonl'
CONNECTION_RECEIPT = ROOT / 'build/native-intake/attempt31l/connection.jsonl'
LIVE_READY = True


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


connection = module('usb_connection31j', 'tools/m1n1-client/usb_connection31j.py')


candidate = module('normal_builder31l', 'kernel/experiments/smp31l-candidate/builder.py')
normal = module('normal_observer31l', 'kernel/experiments/smp31l-observer/observer.py')


def verify_recorder(image):
    previous.verify_recorder(image)
    try:
        candidate.build(image)
    except ValueError as exc:
        raise Refusal(str(exc)) from None


class Controller(previous.Controller):
    """Same CPU1 start commands, independent owned Normal record, no retries.

Prefix positivity stops, even before complete identity. Its absence is not a
failure diagnosis. No target operation is performed after any observation error.
The existing two Device recorders and all K connection/source gates remain.
"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.normal_trackers = {name: normal.Tracker() for name in normal.RECORDS}
        self.state.update(experiment='smp31l', normal_permissions={},
                          normal_publication={}, normal_observation={},
                          cpu0_normal_control={}, normal_entry_armed=False,
                          normal_reads=0, cpu1_prefix_identity_observed=False,
                          device_visibility_cause='UNKNOWN')

    def preflight(self):
        verify_recorder(self.image)
        super().preflight()
        for offset in (0xc00, 0xd00):
            require(self.read(offset, 0x100) == bytes(0x100), 'normal_code_not_fresh')
            self.clean()

    def helper_call(self, offset, *args):
        if offset == 96 and args and self.helper and any(
                self.helper + lo <= args[0] < self.helper + lo + 64
                for lo in (*normal.RECORDS.values(), normal.CONTROL_OFFSET)):
            require(len(args) == 1 and type(args[0]) is int and args[0] % 8 == 0,
                    'normal_read_alignment')
            result = self.p.call((self.helper | core.RX_ALIAS) + offset, *args)
            self.clean()
            return result
        return super().helper_call(offset, *args)

    def prepare(self):
        super().prepare()
        self.prepare_normal_records()
        self.publish_normal_prefixes()

    def prepare_normal_records(self):
        self.phase('normal_record_prepare')
        require(not self.state['start_writes_attempted'] and
                self.state['cpu0_control'].get('result') == 'CPU0_OBSERVER_CONTROL_PASS',
                'normal_prepare_preconditions')
        # Reuse the already owned, non-overlapping16KiB allocation. No new heap
        # request, remap or executable-page store is used by the CPU1 prefix.
        previous.control.layout(self.base, self.helper, self.lo, self.hi)
        self.helper = previous.control.address_integer(self.helper)
        self.fixed_probes(normal.probes(self.helper), 'normal_permissions')
        for offset in (*normal.RECORDS.values(), normal.CONTROL_OFFSET):
            self.mutate(self.i.writemem, self.helper + offset, bytes(normal.BYTES))
            # Publish initialization before startup; never clean/invalidate the
            # Normal record after a CPU1 start intent. Polls may then miss a
            # noncoherent incoming store, which is an explicit negative limit.
            self.mutate(self.p.dc_cvac, self.helper + offset, normal.BYTES)
            for at in range(0, normal.BYTES, 8):
                require(self.helper_call(96, self.helper+offset+at) == 0,
                        'normal_initialization_readback')

        def persist(report):
            self.state['cpu0_normal_control'] = report
            self.journal(dict(self.state))

        def store(value):
            require(value in (0, normal.MARKER) and not self.state['start_writes_attempted'],
                    'normal_control_store_scope')
            return self.mutate(self.p.call,
                               (self.helper | core.RX_ALIAS) + previous.control.LEAF_OFFSET,
                               self.helper + normal.CONTROL_OFFSET + 32, value)

        try:
            report = normal.cpu0_control(
                lambda off: self.helper_call(96, self.helper+normal.CONTROL_OFFSET+off),
                store, persist, lambda: self.state['start_writes_attempted'], self.clock)
        except normal.ObservationError as exc:
            raise Refusal(str(exc)) from None
        require(report['result'] == 'CPU0_NORMAL_CONTROL_PASS', 'normal_control_not_passed')
        self.mutate(self.p.dc_cvac, self.helper+normal.CONTROL_OFFSET, normal.BYTES)

    def publish_normal_prefixes(self):
        self.phase('normal_prefix_permissions')
        probes, parts = [], []
        for name, entry, code in (('vector', 0, 0xc00), ('cold', 0x800, 0xd00)):
            body, _ = candidate.program(name, self.helper)
            for end, at in (('first', code), ('last', code + len(body)-4)):
                for alias, write, fault in ((0, False, False), (vector.RW_ALIAS, True, False)):
                    probes.append(dict(name='normal_code_%s_%s_%s' % (name, end, write),
                                       address=(self.base+at)|alias, physical=self.base+at,
                                       write=write, permission_fault=fault, attr=0xff, shareability=2))
            parts.append((code, body, name+'_body'))
            parts.append((entry, struct.pack('<I', candidate.branch(entry, code)), name+'_hook'))
        self.fixed_probes(probes, 'normal_permissions')
        self.phase('normal_prefix_publish')
        expected = core.relocated_text(self.image, self.base)
        for offset, payload in ((vector.builder.CODE_START, vector.RECORDER),
                                (previous.entry.CODE_START, previous.COLD_BODY)):
            expected[offset:offset+len(payload)] = payload
        # Each prefix is verified before its hook changes. No CPU1 starts exist
        # anywhere in this stage; K already verified the pre-prefix text image.
        for offset, payload, label in parts:
            require(not self.state['start_writes_attempted'], 'normal_publish_after_start')
            alias = (self.base + offset) | vector.RW_ALIAS
            for pos in range(0, len(payload), 4):
                self.mutate(self.p.write32, alias+pos, struct.unpack_from('<I', payload, pos)[0])
            self.mutate(self.p.dc_cvac, alias, len(payload))
            self.mutate(self.p.ic_ivau, self.base+offset, len(payload))
            require(self.i.readmem(alias, len(payload)) == payload, 'normal_alias_readback')
            self.clean()
            require(self.read(offset, len(payload)) == payload, 'normal_identity_readback')
            self.clean()
            expected[offset:offset+len(payload)] = payload
            self.state['normal_publication'][label] = True
            self.journal(dict(self.state))
        for lo, hi in core.TEXT_RANGES:
            for at in range(lo, hi, 0x4000):
                size = min(0x4000, hi-at)
                require(self.read(at, size) == expected[at:at+size], 'normal_whole_text_mismatch')
                self.clean()
        for name in normal.RECORDS:
            for at in range(0, normal.BYTES, 8):
                require(self.helper_call(96, normal.record_address(self.helper, name)+at) == 0,
                        'normal_record_changed_before_start')
        self.state['normal_publication']['whole_text_verified'] = True
        self.state['normal_entry_armed'] = True
        self.journal(dict(self.state))

    def sample_normal(self):
        if not self.state['normal_entry_armed']:
            return
        for name, tracker in self.normal_trackers.items():
            def read64(address):
                self.state['normal_reads'] += 1
                return self.helper_call(96, address)
            try:
                report = tracker.sample(read64, normal.record_address(self.helper, name))
            except BaseException as exc:
                self.state['normal_observation'][name] = dict(tracker.state)
                if isinstance(exc, normal.ObservationError):
                    raise Refusal(str(exc)) from None
                raise
            old = self.state['normal_observation'].get(name, {})
            self.state['normal_observation'][name] = report
            if report['identity_status'] == 'expected_cpu1':
                self.state['cpu1_prefix_identity_observed'] = True
            if any(report.get(k) != old.get(k) for k in
                   ('highest_phase_seen', 'identity_status', 'any_record_seen', 'error')):
                self.journal(dict(self.state))
            require(not report['any_record_seen'], 'normal_%s_prefix_observed' % name)

    def sample_recorder(self):
        self.sample_normal()
        return super().sample_recorder()

    def slots(self):
        self.sample_normal()
        return super().slots()

    def wait_arrival(self):
        super().wait_arrival()
        # An unexpected complete Device-only arrival is also informative. Do
        # not let this visibility experiment progress into callback work.
        raise Refusal('device_arrival_observed_stop_without_callbacks')

def verify_sources():
    path = ROOT / 'tools/m1n1-client/attempt31l-offline.py'
    require(path.is_file() and not path.is_symlink(), 'source_intake_missing')
    intake = module('intake31l', 'tools/m1n1-client/attempt31l-offline.py')
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
        dict(experiment='smp31l', consumed=True, live_result='NOT RUN'), on_created)


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
    state = dict(schema='connection31l', phase='connection_reservation',
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
    result = dict(experiment='smp31l', result='STOP', phase='connect', linux_boot='NOT RUN')
    transport = controller = cstream = nstream = cjournal = njournal = None

    def timeout(*_):
        raise Refusal('controller_deadline')

    def persist_connection(phase=None, **fields):
        if phase is not None:
            state['phase'] = phase
        state.update(fields)
        try:
            cjournal(dict(experiment='smp31l', connection=snapshot(state),
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
            row = dict(value, experiment='smp31l', connection=snapshot(state),
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
            dict(experiment='smp31l', connection=snapshot(state), native_attempt_consumed=False))
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
        print('OFFLINE PASS: 31L source/image verified; no discovery or USB open; restart_ready=false')
        return 0
    require(args.confirm == CONFIRM, 'confirmation')
    result = live(image, args.m1n1)
    print(json.dumps(result, indent=2))
    return 0 if result['result'] == 'CPU1_ENTRY_AND_REQUESTS_PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps(dict(experiment='smp31l', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else (
                'controller_interrupted' if isinstance(exc, KeyboardInterrupt) else 'input_or_setup_failed'),
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
