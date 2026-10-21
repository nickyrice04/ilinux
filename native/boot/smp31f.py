#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31F: bounded early CPU1 recorder and conditional parked-loop requests.

Offline by default. Uses loaded boot021 RAM; no boot-object, security, mapping or RVBAR edits.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import smp31b as core
import smp31d as previous
import importlib.util

CONFIRM = 'START-CPU1-J716C-31F'
RECEIPT = ROOT / 'build/native-intake/attempt31f/consumed.jsonl'
require, Refusal = core.require, core.Refusal
# Two *RAM variables*, not peripheral registers. Pinned boot021 source/image
# audit resolves each load; DC CVAC publishes zeroes before any CPU1 request.
UART_BASES = ((0x110030, 0x288e28000), (0x35a4a0, 0x505200000))
PROXY_IODEV = 0x35a4a8


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


builder = module('recorder31f', 'kernel/experiments/smp31f-entry/builder.py')
observation = module('observation31f', 'kernel/experiments/smp31e-entry/observe.py')
telemetry = module('telemetry31f', 'kernel/experiments/smp31f-entry/telemetry.py')
# Permissions query helpers and pure PAR decoders are independently reviewed.
permissions = module('permissions31f', 'kernel/experiments/smp31f-entry/permissions.py')
RW_ALIAS = 0xa0000000000
RECORDER, _ = builder.program()
BRANCH = struct.pack('<I', builder.branch(builder.ENTRY, builder.CODE_START))
RECORDER_BYTES = 168
RECORDER_SHA = '52f9d1b312725cdc9261e0fbf1c31991e9078a663827734b9ba54c9d171106bc'
REQUESTS = 8
START_HELPER = struct.pack('<4I', 0xb9000001, 0xd5033f9f, 0xd28063c0, 0xd65f03c0)
HELPER_EXTENSION = permissions.HELPER_TAIL + START_HELPER


def verify_recorder(image):
    core.verify_local(image)
    require(hashlib.sha256(RECORDER).hexdigest() == RECORDER_SHA and len(RECORDER) == RECORDER_BYTES,
            'recorder_encoding_changed')
    require(image[builder.ENTRY:builder.ENTRY + 4] == struct.pack('<I', builder.ORIGINAL_MOV),
            'entry_original_word')
    require(image[builder.CODE_START:builder.CODE_END] == bytes(builder.CODE_END-builder.CODE_START),
            'recorder_padding_changed')
    require(image[builder.RECORD:builder.RECORD_END] == bytes(builder.RECORD_END-builder.RECORD),
            'record_padding_changed')


class Controller(previous.Controller):
    """Exactly one CPU1 transition, earlier telemetry and conditional requests.

    The installed image/file is never edited. Only fixed owned RAM spans may
    change, through already configured mappings. No permission-register write,
    remap, reset-vector change, retry, Linux handoff or additional core exists.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state.update(experiment='smp31f', cpu_topology={}, permissions={}, recorder_publication={},
                          recorder_observation={}, recorder_reads=0,
                          requests_planned=REQUESTS, request_roundtrips_ms=[],
                          park_verified=False)
        self.recorder_tracker = telemetry.Tracker()

    def clean(self):
        if not self.helper_ready:
            return super().clean()
        value = self.p.call((self.helper | core.RX_ALIAS) + 96,
                            self.base + core.OFF['diagnostics'])
        if value:
            self.state['exception_count_nonzero'] = bool(value & 0xffffffff)
            self.state['exception_guard_nonzero'] = bool(value >> 32)
            self.journal(dict(self.state))
        require(value == 0, 'target_exception_or_guard')

    def preflight(self):
        verify_recorder(self.image)
        super().preflight()
        # The inherited census has just validated all18 ADT and runtime CPU
        # records against this board. Marketing labels follow the separately
        # observed macOS perflevel inventory, not a guessed P/E translation.
        self.state['cpu_topology'] = {
            'validated_by_exact_adt_and_runtime_census': True,
            'physical_and_logical_cores': 18,
            'clusters': [{'id':0,'adt_type':'M','macos_name':'Performance','cores':6},
                         {'id':1,'adt_type':'M','macos_name':'Performance','cores':6},
                         {'id':2,'adt_type':'P','macos_name':'Super','cores':6}],
            'boot_cpu':0,'target_cpu':1,'target_cluster':0,
            'target_macos_type':'Performance','same_cluster_as_boot_cpu':True,
            'linux_scheduler_capacity_calibrated':False,
            'all_core_linux_operation':'NOT RUN'}
        self.journal(dict(self.state))
        require(self.read(builder.RECORD, builder.RECORD_END-builder.RECORD) ==
                bytes(builder.RECORD_END-builder.RECORD), 'recorder_not_fresh')

    def helper_call(self, offset, *args):
        if offset == 96 and args and self.base + builder.RECORD <= args[0] < self.base + builder.RECORD_END:
            require(len(args) == 1 and args[0] % 8 == 0, 'recorder_read_alignment')
            value = self.p.call((self.helper | core.RX_ALIAS) + offset, *args)
            self.clean()
            return value
        return super().helper_call(offset, *args)

    def sample_recorder(self):
        def read64(address):
            self.state['recorder_reads'] += 1
            return self.helper_call(96, address)
        try:
            summary = self.recorder_tracker.sample(read64, self.base)
        except (KeyboardInterrupt, SystemExit):
            self.state['recorder_observation'] = self.recorder_tracker.report()
            self.journal(dict(self.state))
            raise
        old = self.state['recorder_observation']
        self.state['recorder_observation'] = summary
        fields = ('state', 'highest_phase_seen', 'complete', 'error', 'exception_level',
                  'mmu_enabled', 'data_cache_enabled', 'instruction_cache_enabled')
        if any(summary.get(key) != old.get(key) for key in fields):
            self.journal(dict(self.state))
        require(summary['error'] is None, summary['error'] or 'recorder_error')
        return summary

    def slots(self):
        if not self.state['start_writes_attempted']:
            return core.Controller.slots(self)
        # Acquire the flag BEFORE the identity words it validates. No guarded
        # memory RPC after start; preserve shared exception evidence throughout.
        flag = struct.unpack('<Q', self.read(core.OFF['spin'] + 72, 8))[0]
        require(struct.unpack('<Q', self.read(core.OFF['spin'], 8))[0] == 0x40000 and
                self.helper_call(112, self.base + core.OFF['spin'] + 8, 7) == 0,
                'primary_spin_changed')
        require(self.helper_call(112, self.base + core.OFF['spin'] + 128, 240) == 0,
                'unexpected_secondary')
        mpidr, = struct.unpack('<Q', self.read(core.OFF['spin'] + 64, 8))
        rest = struct.unpack('<6Q', self.read(core.OFF['spin'] + 80, 48))
        reset_mpidr, stack = struct.unpack('<QQ', self.read(core.OFF['reset_table'] + 16, 16))
        try:
            stage = observation.reset_stage(reset_mpidr, stack, mpidr, flag,
                                            self.base + core.OFF['stack_top'])
        except ValueError as exc:
            raise Refusal(str(exc)) from None
        self.state['arrival_samples'] += 1
        if stage != self.state['entry_observation']:
            self.state['entry_observation'] = stage
            self.journal(dict(self.state))
        return (mpidr, flag, *rest)

    def prepare(self):
        super().prepare()
        self.phase('recorder_permissions')
        self.check_permissions()
        self.phase('recorder_publish')
        self.publish_recorder()

    def check_permissions(self):
        require(not self.state['start_writes_attempted'], 'queries_after_start')
        permissions.verify_helper_tail(permissions.HELPER_TAIL)
        self.clean()
        self.mutate(self.i.writemem, self.helper + 192, HELPER_EXTENSION)
        require(self.i.readmem(self.helper + 192, len(HELPER_EXTENSION)) == HELPER_EXTENSION,
                'permission_helper_readback')
        self.clean()
        self.mutate(self.p.dc_cvau, self.helper + 192, len(HELPER_EXTENSION))
        self.mutate(self.p.ic_ivau, (self.helper | core.RX_ALIAS) + 192, len(HELPER_EXTENSION))
        current_el = self.helper_call(16)
        hcr = self.p.call((self.helper | core.RX_ALIAS) + 320)
        self.clean()
        checks = self.state['permissions']
        checks['primary_exception_level'] = current_el // 4 if current_el in (4,8) else None
        try:
            regime = permissions.select_regime(current_el, hcr)
            checks['regime_verified'] = True
            self.journal(dict(self.state))
            for probe in permissions.probe_plan(self.base):
                entry = regime['write_offset' if probe['write'] else 'read_offset']
                par = self.p.call((self.helper | core.RX_ALIAS) + entry, probe['address'])
                self.clean()
                checks[probe['name']] = False
                permissions.validate_probe(probe, par)
                checks[probe['name']] = True
            checks['passed'] = True
        except ValueError as exc:
            self.journal(dict(self.state))
            raise Refusal(str(exc)) from None
        self.journal(dict(self.state))

    def publish_recorder(self):
        require(self.state['permissions'].get('passed') is True, 'permissions_not_verified')
        self.clean()
        require(self.slots() == (0,) * 8 and
                self.read(builder.RECORD, 64) == bytes(64), 'recorder_state_not_fresh')
        # Publish the entire body before replacing its single-word entry hook.
        # Guarded code writes are allowed only BEFORE the first startup intent.
        for offset, payload, label in ((builder.CODE_START, RECORDER, 'body'),
                                       (builder.ENTRY, BRANCH, 'hook')):
            require(not self.state['start_writes_attempted'], 'code_write_after_start')
            alias = (self.base + offset) | RW_ALIAS
            self.clean()
            for pos in range(0, len(payload), 4):
                word, = struct.unpack_from('<I', payload, pos)
                self.mutate(self.p.write32, alias + pos, word)
            # Clean the write alias to PoC. Each pinned proxy dispatch supplies
            # DSB SY + ISB; invalidate the identity instruction-fetch alias next.
            self.mutate(self.p.dc_cvac, alias, len(payload))
            self.mutate(self.p.ic_ivau, self.base + offset, len(payload))
            require(self.i.readmem(alias, len(payload)) == payload, 'recorder_alias_readback')
            self.clean()
            require(self.read(offset, len(payload)) == payload, 'recorder_identity_readback')
            self.clean()
            self.state['recorder_publication'][label + '_verified'] = True
            self.journal(dict(self.state))
        # Recheck the WHOLE immutable text after applying only the two reviewed
        # deltas. This catches adjacent corruption and wrong-address stores.
        expected = core.relocated_text(self.image, self.base)
        expected[builder.CODE_START:builder.CODE_START+len(RECORDER)] = RECORDER
        expected[builder.ENTRY:builder.ENTRY+4] = BRANCH
        for lo, hi in core.TEXT_RANGES:
            for at in range(lo, hi, 0x4000):
                size = min(0x4000, hi-at)
                require(self.read(at, size) == expected[at:at+size], 'published_text_mismatch')
                self.clean()
        require(self.read(builder.RECORD, 64) == bytes(64), 'record_changed_before_start')
        self.clean()
        self.state['recorder_publication']['whole_text_verified'] = True
        self.journal(dict(self.state))

    def wait_arrival(self):
        deadline = self.clock() + 3.0
        while self.clock() < deadline:
            self.sample_recorder()
            row = self.slots()
            self.clean()
            require(self.clock() < deadline, 'cpu1_arrival_timeout')
            if row[1]:
                require(row[1:] == (1, 0, 0, 0, 0, 0, 0), 'unexpected_arrival_state')
                self.identity(row)
                require(self.clock() < deadline, 'cpu1_arrival_timeout')
                self.state['cpu1_arrival_verified'] = True
                summary = self.sample_recorder()
                require(self.clock() < deadline, 'cpu1_arrival_timeout')
                require(summary['complete'], 'arrival_without_complete_recorder')
                return
            self.sleep(0.02)
        raise Refusal('cpu1_arrival_timeout')

    def run(self):
        require(not self.used, 'controller_already_used')
        self.used = True
        self.preflight()
        self.prepare()
        self.phase('cpu1_start')
        for address in core.START:
            if self.state['start_writes_attempted']:
                self.sample_recorder()
            row = self.slots()
            if row != (0,) * 8 and self.state['start_writes_attempted']:
                # Retain the most informative unexpected early-entry outcome,
                # then stop; never blindly issue the second start in that state.
                raise Refusal('cpu1_state_changed_before_second_start')
            require(not self.state['start_writes_attempted'] or
                    self.state['recorder_observation']['highest_phase_seen'] == 0,
                    'recorder_changed_before_second_start')
            require(row == (0,) * 8 and self.read(core.OFF['wfe'], 1) == b'\x01' and
                    self.read(core.OFF['reset'], 8) == struct.pack('<Q', self.base + core.OFF['stack_top']) and
                    self.read(core.OFF['target'], 4) == struct.pack('<I', 1), 'state_changed_before_start')
            self.state['start_writes_attempted'] += 1
            # P_WRITE32 temporarily changes a GLOBAL exception guard. CPU1
            # could fault inside that window. The fixed original helper does
            # the identical aligned32-bit MMIO store without changing guards.
            require(address in core.START, 'startup_address')
            result = self.mutate(self.p.call, (self.helper | core.RX_ALIAS) + 352, address, 2)
            require(result == 0x31e, 'startup_helper_return')
            self.state['start_writes_acknowledged'] += 1
        self.phase('cpu1_arrival')
        self.wait_arrival()
        self.phase('cpu1_requests')
        previous_timer = 0
        for number in range(1, REQUESTS + 1):
            start = self.clock()
            value = self.request(number)
            self.state['request_roundtrips_ms'].append(round((self.clock()-start)*1000, 3))
            require(value > previous_timer, 'counter_not_progressing')
            previous_timer = value
            self.sample_recorder()
            self.journal(dict(self.state))
            self.sleep(0.02)
        self.state['counter_progress_verified'] = True
        self.phase('cpu1_park')
        self.sleep(0.1)
        row = self.slots()
        self.identity(row)
        require(row == (0x40001, REQUESTS+1, 0, 0, 0, 0, 0, previous_timer), 'final_park_state')
        self.clean()
        self.sample_recorder()
        self.state.update(result='CPU1_ENTRY_AND_REQUESTS_PASS', park_verified=True)
        self.phase('complete')
        return dict(self.state)


def verify_sources():
    intake = module('intake31f', 'tools/m1n1-client/attempt31f-offline.py')
    try:
        _, digest = intake.source_pins(ROOT)
        return digest
    except ValueError as exc:
        raise Refusal(str(exc)) from None


def reserve(path=RECEIPT):
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
    journal(dict(experiment='smp31f', consumed=True, live_result='NOT RUN'))
    dirfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)
    return stream, journal


def live(image, client):
    pin = subprocess.check_output(['git', '-C', str(client), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(client), 'status', '--porcelain', '--untracked-files=no'])
    require(pin == core.census.launch.M1N1_COMMIT and not dirty, 'client_revision_or_dirty')
    stream, journal = reserve()
    transport = controller = None
    result = dict(experiment='smp31f', result='STOP', phase='connect', linux_boot='NOT RUN')
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
        print('OFFLINE PASS: 31F source/image/helper verified; no USB, allocation or CPU start')
        return 0
    require(args.confirm == CONFIRM, 'confirmation')
    result = live(image, args.m1n1)
    result['source_manifest_sha256'] = source_manifest_sha
    print(json.dumps(result, indent=2))
    return 0 if result['result'] == 'CPU1_ENTRY_AND_REQUESTS_PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps(dict(experiment='smp31f', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else type(exc).__name__,
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
