#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31C: the unchanged 31B CPU1 sequence with a machine-specific RAM gate.

Offline by default. The consumed 31B source/receipts remain frozen. No Linux,
extra core, frequency, disk, firmware or boot-policy operation is added.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import smp31b as core

CONFIRM = 'START-CPU1-J716C-31C'
RECEIPT = ROOT / 'build/native-intake/attempt31c/consumed.jsonl'
# Read-only /chosen observation on this J716c, independently consistent with
# the recorded 128 GiB inventory and earlier native boot address evidence.
# A physical address starting at 1 TiB is not a claim of 1 TiB RAM capacity.
DRAM_BASE, DRAM_SIZE = 1 << 40, 1 << 37
PHYSICAL_LIMIT = 1 << 42  # Pinned m1n1 mmu_configure(): TCR_IPS_4TB.
require = core.require
Refusal = core.Refusal


def gate(evidence, key, condition):
    evidence[key] = bool(condition)
    require(condition, 'ram_' + key)


def validate_usable(phys, size, evidence):
    gate(evidence, 'integer_fields', isinstance(phys, int) and not isinstance(phys, bool)
         and isinstance(size, int) and not isinstance(size, bool))
    gate(evidence, 'nonempty_u64', 0 <= phys < 1 << 64 and 0 < size < 1 << 64
         and phys + size <= 1 << 64)
    end = phys + size
    gate(evidence, 'address_width', end <= PHYSICAL_LIMIT)
    gate(evidence, 'within_machine_dram', DRAM_BASE <= phys < end <= DRAM_BASE + DRAM_SIZE)
    return phys, end


def read_bounds(iface, proxy, evidence):
    # Import only for live/VM fixture execution. No ProxyUtils/setup allocator.
    from m1n1.tgtypes import BootArgs_r2, BootArgs_r3
    from m1n1.adt import load_adt
    address, revision = proxy.get_bootargs_rev()
    gate(evidence, 'revision_supported', revision in (2, 3))
    evidence['bootargs_revision'] = revision
    ba = iface.readstruct(address, BootArgs_r3 if revision == 3 else BootArgs_r2)
    gate(evidence, 'revision_consistent', ba.revision == revision)
    lo, hi = validate_usable(ba.phys_base, ba.mem_size, evidence)
    # This is the same usable-memory interval m1n1 uses in dt_set_memory().
    # Validate the pointer before reading the ADT; do not broaden to all DRAM.
    addr, size = ba.devtree - ba.virt_base + ba.phys_base, ba.devtree_size
    gate(evidence, 'adt_within_usable', 0 < size <= 2 * 1024**2 and lo <= addr < addr + size <= hi)
    raw = iface.readmem(addr, size)
    gate(evidence, 'adt_read_complete', len(raw) == size)
    with contextlib.redirect_stdout(core.Discard()), contextlib.redirect_stderr(core.Discard()):
        chosen = load_adt(raw)['/chosen']
    # Missing or malformed properties stop; no fallback to a guessed aperture.
    gate(evidence, 'chosen_base_matches', getattr(chosen, 'dram_base', None) == DRAM_BASE)
    gate(evidence, 'chosen_size_matches', getattr(chosen, 'dram_size', None) == DRAM_SIZE)
    return lo, hi


class Controller(core.Controller):
    def __init__(self, iface, proxy, image, journal, *, clock=time.monotonic,
                 sleep=time.sleep, metadata=core.census.read_metadata):
        super().__init__(iface, proxy, image, journal, clock=clock, sleep=sleep,
                         metadata=metadata, bounds=self.observe_bounds)
        self.state.update(experiment='smp31c', ram_check={})

    def observe_bounds(self, iface, proxy):
        evidence = self.state['ram_check']
        try:
            lo, hi = read_bounds(iface, proxy, evidence)
            gate(evidence, 'image_within_usable', lo <= self.base < self.base + len(self.image) <= hi)
            return lo, hi
        finally:
            # Only booleans and a reviewed revision number, never raw addresses,
            # the command line, ADT, identifiers or contents of target memory.
            self.journal(dict(self.state))


def verify_sources():
    manifest = ROOT / 'native/boot/attempt31c/source-sha256.txt'
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
    require({'native/boot/smp31b.py', 'native/boot/smp31c.py',
             'tools/m1n1-client/attempt31c-supervise.py',
             'tools/m1n1-client/attempt31c-instructions.md'} <= seen, 'source_manifest_incomplete')
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
    journal(dict(experiment='smp31c', consumed=True, live_result='NOT RUN'))
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
    result = dict(experiment='smp31c', result='STOP', phase='connect', linux_boot='NOT RUN')
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
        print('OFFLINE PASS: 31C source/image/helper verified; no USB, allocation or CPU start')
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
        print(json.dumps(dict(experiment='smp31c', result='STOP',
            reason=str(exc) if isinstance(exc, Refusal) else type(exc).__name__,
            action='no retry; return to Macintosh HD')))
        raise SystemExit(1)
