#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31D: isolate diagnostic-UART stalls and retain pre-arrival RAM evidence.

Offline by default. Uses installed boot021; no installed-code or RVBAR edits.
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
import smp31c as previous

CONFIRM = 'START-CPU1-J716C-31D'
RECEIPT = ROOT / 'build/native-intake/attempt31d/consumed.jsonl'
require, Refusal = core.require, core.Refusal
# Two *RAM variables*, not peripheral registers. Pinned boot021 source/image
# audit resolves each load; DC CVAC publishes zeroes before any CPU1 request.
UART_BASES = ((0x110030, 0x288e28000), (0x35a4a0, 0x505200000))
PROXY_IODEV = 0x35a4a8


class Controller(previous.Controller):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state.update(experiment='smp31d', diagnostic_uart_check={},
                          entry_observation='not_sampled', arrival_samples=0)

    def preflight(self):
        super().preflight()
        # A physical UART connection would be silenced. Require direct USB,
        # as selected by the transport, and its actual active proxy device.
        active, = struct.unpack('<I', self.read(PROXY_IODEV, 4))
        check = self.state['diagnostic_uart_check']
        check['direct_usb_proxy'] = 4 <= active < 12
        require(check['direct_usb_proxy'], 'proxy_not_direct_usb')
        values = [struct.unpack('<Q', self.read(offset, 8))[0] for offset, _ in UART_BASES]
        check['bases_expected_or_zero'] = all(value in (0, expected)
            for value, (_, expected) in zip(values, UART_BASES))
        check['enabled_count'] = sum(value != 0 for value in values)
        self.journal(dict(self.state))
        require(check['bases_expected_or_zero'], 'diagnostic_uart_base_mismatch')
        require(check['enabled_count'] > 0, 'diagnostic_uarts_already_disabled')

    def prepare(self):
        super().prepare()
        self.phase('diagnostic_uart_ram_setup')
        # Never flush UARTs: a flush is itself an unbounded hardware wait.
        # Both mutations precede CPU1 start. USB and framebuffer configuration
        # stay unchanged. Do not restore until power-off, even on failure.
        for offset, _ in UART_BASES:
            self.mutate(self.p.write64, self.base + offset, 0)
            self.mutate(self.p.dc_cvac, self.base + offset, 8)
            require(self.read(offset, 8) == bytes(8), 'diagnostic_uart_readback')
        self.state['diagnostic_uart_check']['ram_zeroes_published'] = True
        self.journal(dict(self.state))

    def slots(self):
        row = super().slots()
        if not self.state['start_writes_attempted']:
            return row
        # Existing uncached SMP RAM, using the unchanged guard-free helper.
        # These are sequential reads, not an atomic multicore snapshot.
        mpidr, stack = struct.unpack('<QQ', self.read(core.OFF['reset_table'] + 16, 16))
        valid_stack = self.base + core.OFF['stack_top']
        if (mpidr, stack) == ((1 << 64) - 1, 0):
            observation = 'no_reset_record_seen'
        elif (mpidr, stack) == ((1 << 64) - 1, valid_stack):
            observation = 'stack_publication_seen'
        elif (mpidr, stack) == (0x40001, valid_stack):
            observation = 'reset_identity_seen'
        else:
            observation = 'unexpected_reset_record'
        if row[0] == 0x40001 and observation == 'reset_identity_seen':
            observation = 'spin_identity_seen' if row[1] == 0 else 'arrival_flag_seen'
        self.state['arrival_samples'] += 1
        if observation != self.state['entry_observation']:
            self.state['entry_observation'] = observation
            self.journal(dict(self.state))
        require(observation != 'unexpected_reset_record', 'cpu1_reset_record_changed')
        require(row[0] in (0, 0x40001), 'cpu1_partial_mpidr')
        return row


def verify_sources():
    manifest = ROOT / 'native/boot/attempt31d/source-sha256.txt'
    data = manifest.read_bytes()
    require(len(data) < 65536 and not manifest.is_symlink(), 'source_manifest')
    seen = set()
    for line in data.decode('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        require(match is not None, 'source_manifest_syntax')
        digest, name = match.groups()
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts and name not in seen,
                'source_manifest_path')
        path = ROOT / relative
        require(not any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(ROOT)),
                'source_symlink')
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                'source_digest_mismatch')
        seen.add(name)
    require({'native/boot/smp31b.py', 'native/boot/smp31c.py', 'native/boot/smp31d.py',
             'tools/m1n1-client/attempt31d-supervise.py',
             'tools/m1n1-client/attempt31d-instructions.md'} <= seen, 'source_manifest_incomplete')
    return hashlib.sha256(data).hexdigest()


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
    journal(dict(experiment='smp31d', consumed=True, live_result='NOT RUN'))
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
    result = dict(experiment='smp31d', result='STOP', phase='connect', linux_boot='NOT RUN')
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
    core.verify_local(image)
    source_manifest_sha = verify_sources()
    if not args.live:
        print('OFFLINE PASS: 31D source/image/helper verified; no USB, allocation or CPU start')
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
        print(json.dumps(dict(experiment='smp31d', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else type(exc).__name__,
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
