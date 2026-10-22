#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31M: paired cached and cache-maintained observations of owned Normal RAM.

The reset destination and both CPU1 start stores are unchanged. Original code
only patches loaded RAM after exact-image, freshness and translation checks.
Only CPU0 issues cache maintenance. Any entry evidence stops without callbacks.
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
import smp31l as previous
import smp31g as vector

core = previous.core
require, Refusal = core.require, core.Refusal
CONFIRM = 'START-CPU1-J716C-31M'
RECEIPT = ROOT / 'build/native-intake/attempt31m/consumed.jsonl'
CONNECTION_RECEIPT = ROOT / 'build/native-intake/attempt31m/connection.jsonl'
LIVE_READY = True


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


connection = module('usb_connection31j', 'tools/m1n1-client/usb_connection31j.py')


observer = module('paired_observer31m', 'kernel/experiments/smp31m-observer/observer.py')
audit = module('cache_dispatch_audit31m', 'kernel/experiments/smp31m-observer/audit.py')
normal = previous.normal
CONTROL_BYTES = 128
CONTROL_MARKER = 0x314d435055304f4b


def verify_recorder(image):
    previous.verify_recorder(image)
    try:
        audit.verify_image(image)
    except ValueError as exc:
        raise Refusal(str(exc)) from None


class Controller(previous.Controller):
    """Same two CPU1 starts; CPU0-owned cache observation, no CPU1 new ops."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qualification = None
        self.paired_trackers = {}
        self.state.update(experiment='smp31m', requests_planned=0,
            cache_qualification={}, cache_permissions={}, cache_publication={},
            cpu0_cache_control={}, paired_observation={}, cache_records_frozen=False,
            cpu0_post_start_record_stores=0, cache_visibility_cause='UNKNOWN',
            cache_maintenance_intents=0, cache_maintenance_attempted=0,
            cache_maintenance_acknowledged=0)

    def preflight(self):
        super().preflight()
        at = audit.CASE_TABLE_OFFSET
        require(self.read(at, 2) == self.image[at:at+2],
                'cache_dispatch_table_binding')
        self.clean()
        # The frozen cache helper consults its features variable through this
        # relocation. Bind that indirection too; otherwise the independently
        # checked non-Cyclone path would not cover the live cache operation.
        require(self.read(audit.GOT_OFFSET, 8) ==
                struct.pack('<Q', self.base+audit.FEATURE_POINTER_OFFSET),
                'cache_features_got_binding')
        self.clean()
        self.state['cache_publication']['features_got_verified'] = True

    def helper_call(self, offset, *args):
        if offset == 96 and args and self.helper and any(
                self.helper + lo <= args[0] < self.helper + lo + CONTROL_BYTES
                for lo in (*normal.RECORDS.values(), normal.CONTROL_OFFSET)):
            require(len(args) == 1 and type(args[0]) is int and args[0] % 8 == 0,
                    'cache_read_alignment')
            # The second half is checked only before any CPU1 start intent.
            if any(self.helper + lo + 64 <= args[0] < self.helper + lo + CONTROL_BYTES
                   for lo in (*normal.RECORDS.values(), normal.CONTROL_OFFSET)):
                require(not self.state['start_writes_attempted'], 'cache_padding_read_after_start')
            result = self.p.call((self.helper | core.RX_ALIAS) + offset, *args)
            self.clean()
            return result
        return super().helper_call(offset, *args)

    def prepare_normal_records(self):
        super().prepare_normal_records()
        self.prepare_cache_observer()

    def prepare_cache_observer(self):
        self.phase('cache_observer_qualification')
        require(not self.state['start_writes_attempted'] and
                self.state['cpu0_normal_control'].get('result') == 'CPU0_NORMAL_CONTROL_PASS',
                'cache_prepare_preconditions')
        previous.previous.control.layout(self.base, self.helper, self.lo, self.hi)
        leaf = self.helper + observer.CTR_LEAF_OFFSET
        probes = [dict(name='cache_ctr_leaf', address=leaf | core.RX_ALIAS,
                       physical=leaf, write=False, permission_fault=False,
                       attr=0xff, shareability=2)]
        for name, offset in (*normal.RECORDS.items(), ('control', normal.CONTROL_OFFSET)):
            for end, at in (('first', offset), ('last', offset + CONTROL_BYTES - 8)):
                for write in (False, True):
                    probes.append(dict(name='cache_%s_%s_%s' % (name, end, write),
                        address=self.helper+at, physical=self.helper+at, write=write,
                        permission_fault=False, attr=0xff, shareability=2))
        self.fixed_probes(probes, 'cache_permissions')
        self.mutate(self.i.writemem, leaf, observer.CTR_LEAF)
        require(self.i.readmem(leaf, len(observer.CTR_LEAF)) == observer.CTR_LEAF,
                'cache_ctr_leaf_readback')
        self.clean()
        self.mutate(self.p.dc_cvau, leaf, len(observer.CTR_LEAF))
        self.mutate(self.p.ic_ivau, leaf | core.RX_ALIAS, len(observer.CTR_LEAF))
        level = self.helper_call(16)
        hcr = self.p.call((self.helper | core.RX_ALIAS) + 320)
        self.clean()
        ctr = self.p.call(leaf | core.RX_ALIAS)
        self.clean()
        try:
            self.qualification = observer.qualify(self.helper, level, hcr, ctr)
        except ValueError as exc:
            raise Refusal(str(exc)) from None
        self.state['cache_qualification'] = self.qualification.public()
        self.state['cache_publication']['ctr_leaf_verified'] = True
        self.phase('cache_owned_granule_prepare')
        for name, offset in (*normal.RECORDS.items(), ('control', normal.CONTROL_OFFSET)):
            require(not self.state['start_writes_attempted'], 'cache_initialize_after_start')
            self.mutate(self.i.writemem, self.helper+offset, bytes(CONTROL_BYTES))
            self.mutate(self.p.dc_cvac, self.helper+offset, CONTROL_BYTES)
            for at in range(0, CONTROL_BYTES, 8):
                require(self.helper_call(96, self.helper+offset+at) == 0,
                        'cache_granule_initialization_readback')
            self.state['cache_publication'][name+'_granule_clean'] = True
            self.journal(dict(self.state))
        self.prepare_cache_control()
        # These records have not been CPU0-written since their complete clean.
        # Publishing the CPU1 prefix changes disjoint code, not these granules.
        self.state['cache_records_frozen'] = True
        self.paired_trackers = {name: observer.PairedTracker(
            self.qualification, name, initialized_clean=True, cpu0_stores_frozen=True)
            for name in normal.RECORDS}
        self.journal(dict(self.state))

    def cache_maintain(self, address, size, *, control=False, before_dispatch=None):
        require(self.qualification is not None and type(address) is int and size == 64,
                'cache_maintenance_unqualified')
        require(type(self.p.P_DC_CIVAC) is int and self.p.P_DC_CIVAC == 0x30a,
                'cache_opcode_binding')
        if control:
            require(not self.state['start_writes_attempted'] and
                    address == self.helper+normal.CONTROL_OFFSET and callable(before_dispatch),
                    'cache_control_maintenance_scope')
        else:
            require(self.state['cache_records_frozen'] is True and
                    self.state['cpu0_post_start_record_stores'] == 0 and
                    address in tuple(self.helper+v for v in normal.RECORDS.values()),
                    'cache_maintenance_record_scope')
        self.state['cache_maintenance_intents'] += 1
        self.journal(dict(self.state))
        self.state['cache_maintenance_attempted'] += 1
        # Unlike the convenience wrapper, request retains the reply's value.
        # The frozen target opcode does no guard change and its common epilogue
        # provides DSB SY and ISB before the successful reply.
        def dispatch():
            if control:
                before_dispatch()  # Recheck after the mutation-intent journal.
            return self.p.request(self.p.P_DC_CIVAC, address, size)
        value = self.mutate(dispatch)
        require(type(value) is int and value == 0, 'cache_maintenance_return')
        self.state['cache_maintenance_acknowledged'] += 1
        self.journal(dict(self.state))
        return value

    def prepare_cache_control(self):
        self.phase('cpu0_cache_control')
        report = dict(result='NOT RUN', reads_attempted=0, reads_completed=0,
            stores_attempted=0, stores_acknowledged=0, maintenance_attempted=0,
            maintenance_acknowledged=0, marker_observed=False, canaries_preserved=False,
            original_restored=False, cpu1_visibility='NOT_TESTED', error=None)
        self.state['cpu0_cache_control'] = report
        start = self.clock()
        def budget():
            require(not self.state['start_writes_attempted'], 'cache_control_after_start')
            elapsed = self.clock()-start
            require(0 <= elapsed < 2.0, 'cache_control_deadline')
        def persist():
            self.journal(dict(self.state))
        def read(expected):
            for at in range(0, CONTROL_BYTES, 8):
                budget()
                report['reads_attempted'] += 1
                persist()
                budget()
                value = self.helper_call(96, self.helper+normal.CONTROL_OFFSET+at)
                report['reads_completed'] += 1
                budget()
                require(type(value) is int and value == (expected if at == 32 else 0),
                        'cache_control_readback')
        def store(value):
            budget()
            report['stores_attempted'] += 1
            persist()
            budget()
            def dispatch():
                budget()  # self.mutate journals before invoking this callback.
                return self.p.call(
                    (self.helper | core.RX_ALIAS)+previous.previous.control.LEAF_OFFSET,
                    self.helper+normal.CONTROL_OFFSET+32, value)
            result = self.mutate(dispatch)
            require(type(result) is int and result == 0x314b, 'cache_control_store_return')
            report['stores_acknowledged'] += 1
            budget()
        def maintain():
            budget()
            report['maintenance_attempted'] += 1
            persist()
            budget()
            self.cache_maintain(self.helper+normal.CONTROL_OFFSET, 64, control=True,
                                before_dispatch=budget)
            report['maintenance_acknowledged'] += 1
            budget()
        try:
            read(0)
            store(CONTROL_MARKER)
            maintain()
            read(CONTROL_MARKER)
            report['marker_observed'] = True
            store(0)
            maintain()
            read(0)
            report.update(result='CPU0_CACHE_CONTROL_PASS', canaries_preserved=True,
                          original_restored=True)
            persist()
        except BaseException:
            report.update(result='STOP', error='cpu0_cache_control_incomplete')
            raise

    def sample_normal(self):
        if not self.state['normal_entry_armed']:
            return
        if not self.state['start_writes_attempted']:
            return super().sample_normal()
        require(self.qualification is not None and self.state['cache_records_frozen'] and
                self.state['cpu0_cache_control'].get('result') == 'CPU0_CACHE_CONTROL_PASS',
                'cache_observer_not_ready')
        for name, tracker in self.paired_trackers.items():
            def read64(address):
                self.state['normal_reads'] += 1
                return self.helper_call(96, address)
            def journal(report):
                self.state['paired_observation'][name] = report
                self.journal(dict(self.state))
            try:
                report = tracker.sample(read64, self.cache_maintain, journal)
            except observer.ObservationError as exc:
                self.state['paired_observation'][name] = dict(tracker.state)
                raise Refusal(str(exc)) from None
            except BaseException:
                self.state['paired_observation'][name] = dict(tracker.state)
                raise
            self.state['paired_observation'][name] = report
            if report['identity_status'] == 'expected_cpu1':
                self.state['cpu1_prefix_identity_observed'] = True
            require(not report['any_record_seen'], 'paired_%s_prefix_observed' % name)


def verify_sources():
    path = ROOT / 'tools/m1n1-client/attempt31m-offline.py'
    require(path.is_file() and not path.is_symlink(), 'source_intake_missing')
    intake = module('intake31m', 'tools/m1n1-client/attempt31m-offline.py')
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
        dict(experiment='smp31m', consumed=True, live_result='NOT RUN'), on_created)


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
    state = dict(schema='connection31m', phase='connection_reservation',
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
    result = dict(experiment='smp31m', result='STOP', phase='connect', linux_boot='NOT RUN')
    transport = controller = cstream = nstream = cjournal = njournal = None

    def timeout(*_):
        raise Refusal('controller_deadline')

    def persist_connection(phase=None, **fields):
        if phase is not None:
            state['phase'] = phase
        state.update(fields)
        try:
            cjournal(dict(experiment='smp31m', connection=snapshot(state),
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
            row = dict(value, experiment='smp31m', connection=snapshot(state),
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
            dict(experiment='smp31m', connection=snapshot(state), native_attempt_consumed=False))
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
        print('OFFLINE PASS: 31M source/image verified; no discovery or USB open; restart_ready=false')
        return 0
    require(args.confirm == CONFIRM, 'confirmation')
    result = live(image, args.m1n1)
    print(json.dumps(result, indent=2))
    return 0 if result['result'] == 'CPU1_ENTRY_AND_REQUESTS_PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps(dict(experiment='smp31m', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else (
                'controller_interrupted' if isinstance(exc, KeyboardInterrupt) else 'input_or_setup_failed'),
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
