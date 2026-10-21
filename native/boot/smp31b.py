#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31B: one CPU1 start and two bounded parked-loop requests. Offline by default.

No Linux, reset-vector write, installed-code patch, chainload, CPU stop, IPI,
frequency change or disk access. Live mode is called by the fixed supervisor.
"""
import argparse
import contextlib
import hashlib
import io
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
import smp31_census as census

CONFIRM = 'START-CPU1-J716C-31B'
RX_ALIAS = 0xc0000000000  # Existing m1n1 executable alias; no mapping changes.
OFF = dict(spin=0x90210, reset_table=0x90010, target=0x90a10, wfe=0x90a14,
           reset_el1=0x90a18, reset=0x90a20, stack_bottom=0x168000,
           stack_top=0x178000, primary_stack=0x3c0000, features_ptr=0x1012d0,
           features=0x7fba8, diagnostics=0x110038, timer=0x37f20)
START = (0x280688004, 0x280688008)
HELPER_WORDS = (
    0xd5033f9f, 0xd503209f, 0xd2806360, 0xd65f03c0,
    0xd5384240, 0xd65f03c0, 0xd503201f, 0xd503201f,
    0xd5380400, 0xd65f03c0, 0xd503201f, 0xd503201f,
    0xd53800a0, 0xd65f03c0, 0xd503201f, 0xd503201f,
    0xd5380000, 0xd65f03c0, 0xd503201f, 0xd503201f,
    0xd5381000, 0xd65f03c0, 0xd503201f, 0xd503201f,
    0xf9400000, 0xd65f03c0, 0xd503201f, 0xd503201f,
    0xaa1f03e2, 0xf104003f, 0x54000108, 0xb40000a1,
    0xf8408403, 0xaa030042, 0xf1000421, 0x54ffffa1,
    0xaa0203e0, 0xd65f03c0, 0x92800000, 0xd65f03c0,
    0xf9000001, 0xd5033f9f, 0xd503209f, 0xd2806360,
    0xd65f03c0, 0xd503201f, 0xd503201f, 0xd503201f,
)
HELPER = struct.pack('<48I', *HELPER_WORDS)
HELPER_SHA = 'dc046b303191b9a4fcb26a9e689fa4ec7b936dd1ae67dc5fd9b81c4edf4bf8aa'
TEXT_RANGES = ((0, 0x1000), (0x10000, 0x70000))
# Eight R_AARCH64_RELATIVE literals live inside the linked text region.
# Compare their relocated values too; do not skip bytes or reject a valid boot.
TEXT_RELOCS = {0x10f90:0x10144, 0x10f98:0x102cf8, 0x10fa0:0x101d4,
               0x12160:0x11050, 0x12168:0x11800, 0x12170:0x12000,
               0x12178:0x11090, 0x13178:0x35a700}
RECEIPT = ROOT / 'build/native-intake/attempt31b/consumed.jsonl'


class Refusal(ValueError):
    """Fixed public reason, never a raw target/transport message."""


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def verify_local(image):
    require(len(image) == 3932160, 'image_size')
    census.verify_image(image)
    require(hashlib.sha256(HELPER).hexdigest() == HELPER_SHA, 'helper_digest')
    found = {}
    for offset in range(0x84d10, 0x8cd98, 24):
        target, kind, addend = struct.unpack_from('<QQq', image, offset)
        if target < 0x70000:
            require(kind == 1027 and target not in found, 'text_relocation_kind')
            found[target] = addend
    require(found == TEXT_RELOCS, 'text_relocation_set')


def verify_sources():
    manifest = ROOT / 'native/boot/attempt31b/source-sha256.txt'
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
    require({'native/boot/smp31b.py', 'tools/m1n1-client/attempt31b-supervise.py',
             'tools/m1n1-client/attempt31b-instructions.md'} <= seen, 'source_manifest_incomplete')
    return hashlib.sha256(data).hexdigest()


def relocated_text(image, base):
    expected = bytearray(image[:0x70000])
    for offset, addend in TEXT_RELOCS.items():
        struct.pack_into('<Q', expected, offset, base + addend)
    return expected


def ram_bounds(iface, proxy):
    from m1n1.tgtypes import BootArgs_r2, BootArgs_r3
    addr, rev = proxy.get_bootargs_rev()
    require(rev in (2, 3), 'bootargs_revision')
    ba = iface.readstruct(addr, BootArgs_r3 if rev == 3 else BootArgs_r2)
    lo, hi = ba.phys_base, ba.phys_base + ba.mem_size
    require(0x800000000 <= lo < hi < 1 << 40, 'ram_bounds')
    return lo, hi


class Controller:
    def __init__(self, iface, proxy, image, journal, *, clock=time.monotonic,
                 sleep=time.sleep, metadata=census.read_metadata, bounds=ram_bounds):
        self.i, self.p, self.image, self.journal = iface, proxy, image, journal
        self.clock, self.sleep, self.metadata, self.bounds = clock, sleep, metadata, bounds
        self.used = False
        self.base = self.helper = 0
        self.helper_ready = False
        self.state = dict(experiment='smp31b', result='STOP', phase='initial',
            mutation_requests=0, start_writes_attempted=0, start_writes_acknowledged=0,
            cpu1_arrival_verified=False, requests_completed=0,
            counter_progress_verified=False, linux_boot='NOT RUN', native_linux_smp='NOT RUN')

    def phase(self, phase):
        self.state['phase'] = phase
        self.journal(dict(self.state))

    def clean(self):
        if self.helper_ready:
            # Atomic aligned read of adjacent count/guard, no read-and-clear
            # race and no global guard mutation by P_READ/REQ_MEMREAD.
            value = self.p.call((self.helper | RX_ALIAS) + 96, self.base + OFF['diagnostics'])
            require(value == 0, 'target_exception_or_guard')
        else:
            require(self.p.get_exc_count() == 0, 'target_exception')

    def mutate(self, operation, *args):
        # Persist intent BEFORE dispatch. A failed acknowledgment is not proof
        # that the operation did not execute. Never undo, retry, free or stop.
        self.state['mutation_requests'] += 1
        self.journal(dict(self.state))
        result = operation(*args)
        self.clean()
        return result

    def read(self, offset, size):
        if self.state['start_writes_attempted']:
            # REQ_MEMREAD clears exc_count and changes a GLOBAL guard. After
            # starting CPU1, use only guard-free P_CALL reads of known SMP RAM.
            require(0x90000 <= offset < offset + size <= 0x90a28, 'post_start_read_range')
            first = offset & ~7
            data = b''.join(struct.pack('<Q', self.helper_call(96, self.base + at))
                            for at in range(first, offset + size, 8))
            return data[offset - first:offset - first + size]
        data = self.i.readmem(self.base + offset, size)
        require(len(data) == size, 'short_memory_read')
        return data

    def slots(self):
        if self.state['start_writes_attempted']:
            require(struct.unpack('<Q', self.read(OFF['spin'], 8))[0] == 0x40000 and
                    self.helper_call(112, self.base + OFF['spin'] + 8, 7) == 0,
                    'primary_spin_changed')
            require(self.helper_call(112, self.base + OFF['spin'] + 128, 240) == 0,
                    'unexpected_secondary')
            return struct.unpack('<8Q', self.read(OFF['spin'] + 64, 64))
        raw = self.read(OFF['spin'], 32 * 64)
        rows = [struct.unpack_from('<8Q', raw, n * 64) for n in range(32)]
        require(rows[0] == (0x40000, 0, 0, 0, 0, 0, 0, 0), 'primary_spin_changed')
        require(all(row == (0,) * 8 for row in rows[2:]), 'unexpected_secondary')
        return rows[1]

    def fresh(self):
        require(self.slots() == (0,) * 8, 'cpu1_not_fresh')
        raw = self.read(OFF['reset_table'], 32 * 16)
        require(struct.unpack_from('<QQ', raw) ==
                (0x40000, self.base + OFF['primary_stack']), 'primary_stack_changed')
        require(all(struct.unpack_from('<QQ', raw, n * 16) == ((1 << 64) - 1, 0)
                    for n in range(1, 32)), 'reset_table_not_fresh')
        # Never read exc_guard with REQ_MEMREAD: its checksum phase temporarily
        # sets that very field, so its checksum and payload would disagree.
        for key, size in (('target', 4), ('wfe', 1), ('reset', 8), ('reset_el1', 8)):
            require(self.read(OFF[key], size) == bytes(size), 'startup_state_not_fresh')

    def preflight(self):
        self.phase('preflight')
        result = census.observe(self.i, self.p, self.image, metadata=self.metadata)
        require(all(r['locked'] and r['target_relation'] == 'vectors' and
                    r['image_offset'] == '0x0' for r in result['rows']), 'reset_mirror_mismatch')
        self.base = self.p.get_base()
        self.lo, self.hi = self.bounds(self.i, self.p)
        require(self.lo <= self.base < self.base + len(self.image) <= self.hi, 'image_outside_ram')
        expected_text = relocated_text(self.image, self.base)
        for lo, hi in TEXT_RANGES:
            for start in range(lo, hi, 0x4000):
                size = min(0x4000, hi - start)
                require(self.read(start, size) == expected_text[start:start + size], 'immutable_text_changed')
        require(self.p.read64(self.base + OFF['features_ptr']) == self.base + OFF['features'],
                'unexpected_cpu_features')
        features = self.read(OFF['features'], 20)
        expected = bytes(13) + b'\x01' + bytes(3) + b'\x01' + bytes(2)
        require(features == expected == self.image[OFF['features']:OFF['features'] + 20],
                'unsupported_cpu_features')
        self.fresh()
        self.clean()

    def helper_call(self, offset, *args):
        require(offset in (0, 16, 32, 48, 64, 80, 96, 112), 'helper_offset')
        if offset == 96:
            require(len(args) == 1 and args[0] % 8 == 0 and
                    self.base + 0x90000 <= args[0] <= self.base + 0x90a20, 'helper_read_range')
        elif offset == 112:
            require(args in ((self.base + OFF['spin'] + 8, 7),
                             (self.base + OFF['spin'] + 128, 240)), 'helper_scan_range')
        else:
            require(not args, 'helper_extra_args')
        result = self.p.call((self.helper | RX_ALIAS) + offset, *args)
        self.clean()
        return result

    def prepare(self):
        self.phase('helper_setup')
        self.helper = self.mutate(self.p.memalign, 0x4000, 0x4000)
        require(self.helper % 0x4000 == 0 and self.lo <= self.helper < self.helper + 0x4000 <= self.hi
                and (self.helper + 0x4000 <= self.base or self.helper >= self.base + len(self.image)),
                'helper_allocation_range')
        self.mutate(self.i.writemem, self.helper, HELPER)
        require(self.i.readmem(self.helper, len(HELPER)) == HELPER, 'helper_readback')
        # Each installed proxy request ends with DSB SY; ISB. Compare that
        # immutable code in preflight. Use its existing RX alias, not SPRR edits.
        self.mutate(self.p.dc_cvau, self.helper, len(HELPER))
        self.mutate(self.p.ic_ivau, self.helper | RX_ALIAS, len(HELPER))
        self.helper_ready = True
        self.clean()
        require(self.helper_call(16) in (4, 8), 'primary_exception_level')
        require(self.helper_call(32) & 0xf000 == 0, 'el3_not_supported')
        require(self.helper_call(48) & 0xffffff == 0x40000, 'primary_mpidr')
        midr = self.helper_call(64)
        require(midr >> 24 == 0x61 and (midr >> 4) & 0xfff == 0x68, 'primary_cpu_part')
        require(self.helper_call(80) & 1 == 1, 'primary_mmu_disabled')
        self.fresh()
        self.phase('cpu1_ram_setup')
        self.mutate(self.p.smp_set_wfe_mode, True)  # No alive cores => no IPI.
        require(self.read(OFF['wfe'], 1) == b'\x01', 'wfe_readback')
        self.mutate(self.p.write32, self.base + OFF['target'], 1)
        self.mutate(self.p.write64, self.base + OFF['reset'], self.base + OFF['stack_top'])
        require(self.read(OFF['target'], 4) == struct.pack('<I', 1) and
                self.read(OFF['reset'], 8) == struct.pack('<Q', self.base + OFF['stack_top']),
                'cpu1_setup_readback')
        require(self.slots() == (0,) * 8, 'cpu1_started_during_setup')

    def identity(self, row):
        require(row[0] == 0x40001, 'cpu1_mpidr')
        require(self.read(OFF['reset_table'] + 16, 16) ==
                struct.pack('<QQ', 0x40001, self.base + OFF['stack_top']), 'cpu1_stack')
        require(self.read(OFF['wfe'], 1) == b'\x01' and
                self.read(OFF['reset'], 8) == struct.pack('<Q', self.base + OFF['stack_top']),
                'park_configuration_changed')

    def wait_arrival(self):
        deadline = self.clock() + 3.0
        while self.clock() < deadline:
            row = self.slots()
            self.clean()
            require(self.clock() < deadline, 'cpu1_arrival_timeout')
            if row[1]:
                require(row[1:] == (1, 0, 0, 0, 0, 0, 0), 'unexpected_arrival_state')
                self.identity(row)
                require(self.clock() < deadline, 'cpu1_arrival_timeout')
                self.state['cpu1_arrival_verified'] = True
                return
            self.sleep(0.01)
        raise Refusal('cpu1_arrival_timeout')

    def request(self, previous):
        row = self.slots()
        self.identity(row)
        require(row[1] == previous and row[2] == 0 and row[3:7] == (0,) * 4, 'request_state')
        # Direct one-slot publication avoids the installed unbounded smp_call.
        # args remain the verified zeroes: timeout_calculate(0) only reads timer regs.
        # Publication also avoids P_WRITE64's global exception guard. Fixed
        # helper +160 stores one aligned RAM word, DSB, SEV, returns immediately.
        deadline = self.clock() + 1.0
        result = self.mutate(self.p.call, (self.helper | RX_ALIAS) + 160,
                             self.base + OFF['spin'] + 64 + 16, self.base + OFF['timer'])
        require(result == 0x31b, 'event_helper_return')
        while self.clock() < deadline:
            row = self.slots()
            self.clean()
            self.identity(row)
            require(self.clock() < deadline, 'cpu1_request_timeout')
            require(row[1] in (previous, previous + 1) and
                    row[2] in (0, self.base + OFF['timer']) and row[3:7] == (0,) * 4,
                    'request_state_changed')
            if row[1] == previous + 1 and row[2] == 0:
                require(0 < row[7] < (1 << 63), 'timer_result')
                self.state['requests_completed'] += 1
                return row[7]
            self.sleep(0.01)
        raise Refusal('cpu1_request_timeout')

    def run(self):
        require(not self.used, 'controller_already_used')
        self.used = True
        verify_local(self.image)
        self.preflight()
        self.prepare()
        self.phase('cpu1_start')
        for address in START:
            require(self.slots() == (0,) * 8 and self.read(OFF['wfe'], 1) == b'\x01' and
                    self.read(OFF['reset'], 8) == struct.pack('<Q', self.base + OFF['stack_top']) and
                    self.read(OFF['target'], 4) == struct.pack('<I', 1), 'state_changed_before_start')
            self.state['start_writes_attempted'] += 1
            self.mutate(self.p.write32, address, 2)
            self.state['start_writes_acknowledged'] += 1
        self.phase('cpu1_arrival')
        self.wait_arrival()
        self.phase('cpu1_requests')
        first = self.request(1)
        self.sleep(0.1)
        second = self.request(2)
        require(second > first, 'counter_not_progressing')
        self.state['counter_progress_verified'] = True
        # A short quiet period then read back: no third request or IPI.
        self.sleep(0.1)
        row = self.slots()
        self.identity(row)
        require(row == (0x40001, 3, 0, 0, 0, 0, 0, second), 'final_park_state')
        self.clean()
        self.state['result'] = 'CPU1_ENTRY_AND_REQUESTS_PASS'
        self.phase('complete')
        return dict(self.state)


def reserve(path=RECEIPT):
    # Never offer a reset/force flag. A consumed receipt requires M5 review.
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
    journal(dict(experiment='smp31b', consumed=True, live_result='NOT RUN'))
    dirfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)
    return stream, journal


class Discard(io.TextIOBase):
    def write(self, text):
        return len(text)


def live(image, client):
    pin = subprocess.check_output(['git', '-C', str(client), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(client), 'status', '--porcelain', '--untracked-files=no'])
    require(pin == census.launch.M1N1_COMMIT and not dirty, 'client_revision_or_dirty')
    stream, journal = reserve()
    transport = controller = None
    result = dict(experiment='smp31b', result='STOP', phase='connect', linux_boot='NOT RUN')
    def timeout(*_):
        raise Refusal('controller_deadline')
    old = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    start = time.monotonic()
    try:
        with contextlib.redirect_stdout(Discard()), contextlib.redirect_stderr(Discard()):
            sys.path.insert(0, str(client / 'proxyclient'))
            from m1n1.proxy import M1N1Proxy, UartInterface, Serial
            selected = census.launch.usb_identity.select_primary(census.launch.usb_identity.discover(), 'auto')
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
            'census_precondition' if isinstance(exc, census.CensusRefusal) else type(exc).__name__)
    finally:
        # No target cleanup: retain helper allocation, stack and WFE setting
        # until human power-off, even if the secondary arrives late.
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
    p.add_argument('--helper-check', type=Path)
    p.add_argument('--live', action='store_true')
    p.add_argument('--confirm')
    p.add_argument('--m1n1', type=Path, default=ROOT / 'third_party/m1n1')
    args = p.parse_args()
    require(not args.image.is_symlink() and args.image.is_file(), 'image_file')
    image = args.image.read_bytes()
    verify_local(image)
    source_manifest_sha = verify_sources()
    if args.helper_check:
        require(args.helper_check.read_bytes() == HELPER, 'compiled_helper_mismatch')
    if not args.live:
        print('OFFLINE PASS: boot021 and helper verified; no USB, allocation or CPU start')
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
        print(json.dumps(dict(experiment='smp31b', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else type(exc).__name__,
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
