#!/usr/bin/env python3
"""Attempt31A: two RVBAR reads, no CPU start or Linux launch.

Default is offline. Uses the installed, pinned boot021 image. Never loads
ProxyUtils, allocates target memory, writes hardware, patches code, changes
boot policy, or emits the raw ADT. Exception counters are read/cleared by the
existing proxy diagnostics. No inference of effective reset entry from a mirror.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import signal
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import launch

IMAGE_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
CONFIRM = 'CENSUS-J716C-SMP-31A'
# Generated boot021 symbol table, verified against original linked image.
OFF = dict(mpidr=0x90000, index=0x90008, info=0x1171e8,
           start_base=0x1173e8, initialized=0x1173f0)
class CensusRefusal(ValueError):
    """Only fixed, non-identifying gate messages may use this exception."""


RVBAR = (0x210050000, 0x210150000)
MASK = ((1 << 48) - 1) & ~0xfff


def verify_image(image):
    if hashlib.sha256(image).hexdigest() != IMAGE_SHA:
        raise CensusRefusal('boot021 image digest mismatch')


def validate_topology(compatible, cpus, clusters):
    if 'J716cAP' not in compatible or clusters != [6, 6 | (6 << 16), 6 | (12 << 16)]:
        raise CensusRefusal('board/cluster description mismatch')
    if len(cpus) != 18:
        raise CensusRefusal('CPU count differs from this machine')
    by_id = {c['id']: c for c in cpus}
    if set(by_id) != set(range(18)):
        raise CensusRefusal('CPU IDs duplicate or incomplete')
    for i in range(18):
        c = by_id[i]
        cluster, core = divmod(i, 6)
        expected = 0x210050000 + cluster * 0x1000000 + core * 0x100000
        if (c['reg'] != (cluster << 8 | core) or c['impl'] != (expected, 0x9018)
                or c['kind'] != ('M' if i < 12 else 'P')
                or c['state'] != ('running' if i == 0 else 'waiting')):
            raise CensusRefusal('CPU topology/state differs from reviewed ADT')


def read_metadata(iface, proxy):
    # Import only in the live path. No setup module or target heap utilities.
    from m1n1.tgtypes import BootArgs_r2, BootArgs_r3
    from m1n1.adt import load_adt
    address, revision = proxy.get_bootargs_rev()
    if revision not in (2, 3):
        raise CensusRefusal('unreviewed boot-args revision')
    ba = iface.readstruct(address, BootArgs_r3 if revision == 3 else BootArgs_r2)
    size = ba.devtree_size
    addr = ba.devtree - ba.virt_base + ba.phys_base
    if not 0 < size <= 2 * 1024**2 or not ba.phys_base <= addr < addr + size <= ba.phys_base + ba.mem_size:
        raise CensusRefusal('ADT outside bounded RAM')
    # The pinned parser prints raw property bytes on a decoding error. Keep
    # those diagnostics in transient memory, never the public census stream.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        root = load_adt(iface.readmem(addr, size))
    cpus = []
    for node in root['/cpus']:
        cpus.append(dict(id=node.cpu_id, reg=node.reg, impl=tuple(node.cpu_impl_reg),
                         state=node.state, kind=node.cluster_type))
    validate_topology(root.compatible, cpus, list(root['/arm-io/pmgr'].clusters))


def classify(value, base):
    target = value & MASK
    relation = ('vectors' if target == base else
                'within-image' if base <= target < base + 0x3c0000 else 'outside-image')
    return {'locked': bool(value & 1), 'target_relation': relation,
            # Keep the signed distance even outside the image: discarding it
            # would lose whether the two cores name the same external page.
            'image_offset': hex(target - base),
            'mirror_only': True}


def observe(iface, proxy, image, metadata=read_metadata):
    verify_image(image)
    proxy.nop()
    if proxy.get_chipid() != 0x6050:
        raise CensusRefusal('target is not t6050')
    base = proxy.get_base()
    if base <= 0 or base % 0x4000:
        raise CensusRefusal('unaligned image base')
    # Only immutable text is compared. Relocated data are checked separately.
    for lo, hi in ((0, 0x1000), (0x30000, 0x32000)):
        if iface.readmem(base + lo, hi - lo) != image[lo:hi]:
            raise CensusRefusal('live boot021 startup/SMP text differs')
    launch.ensure_no_secondaries(proxy)
    metadata(iface, proxy)
    if (proxy.read32(base + OFF['index']) != 0 or
        proxy.read64(base + OFF['mpidr']) & 0xffffff != 0x40000 or
        iface.readmem(base + OFF['initialized'], 1) != b'\x01' or
        proxy.read64(base + OFF['start_base']) != 0x280688000):
        raise CensusRefusal('installed SMP state differs')
    info = iface.readmem(base + OFF['info'], 32 * 16)
    for i in range(32):
        valid, die, cluster, core, impl = struct.unpack_from('<4B4xQ', info, i * 16)
        if i >= 18:
            if (valid, die, cluster, core, impl) != (0, 0, 0, 0, 0):
                raise CensusRefusal('unexpected extra CPU record')
        elif (valid, die, cluster, core, impl) != (1, 0, i // 6, i % 6,
                0x210050000 + (i // 6) * 0x1000000 + (i % 6) * 0x100000):
            raise CensusRefusal('SMP record differs from ADT')
    if proxy.get_exc_count():
        raise CensusRefusal('pre-existing exception; no MMIO reads')
    rows = []
    for cpu, address in enumerate(RVBAR):
        value = proxy.read64(address)  # P_READ64 uses the existing GUARD_MARK.
        if proxy.get_exc_count():
            raise CensusRefusal('RVBAR read trapped; no further reads or retry')
        if value in (0, 0xffffffffffffffff, 0xbad0bad0bad0bad0):
            raise CensusRefusal('RVBAR value invalid; no further reads')
        rows.append({'cpu_id': cpu, **classify(value, base)})
    launch.ensure_no_secondaries(proxy)
    return {'experiment': 'smp31a', 'read_only_hardware': True,
            'cpu_starts': 0, 'mmio_reads': 2, 'rows': rows,
            'result': 'CENSUS_COMPLETE_REVIEW_REQUIRED',
            'native_smp': 'NOT RUN', 'linux_boot': 'NOT RUN'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--live', action='store_true')
    p.add_argument('--device', default='auto')
    p.add_argument('--confirm')
    p.add_argument('--m1n1', type=Path, default=ROOT / 'third_party/m1n1')
    a = p.parse_args()
    if a.image.is_symlink() or not a.image.is_file() or a.image.stat().st_size != 3932160:
        raise CensusRefusal('invalid image file')
    image = a.image.read_bytes()
    verify_image(image)
    if not a.live:
        print('OFFLINE PASS: boot021 verified; no USB opened; no CPU start')
        return
    if a.confirm != CONFIRM:
        p.error('requires --confirm ' + CONFIRM)
    pin = subprocess.check_output(['git', '-C', str(a.m1n1), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(a.m1n1), 'status', '--porcelain', '--untracked-files=no'])
    if pin != launch.M1N1_COMMIT or dirty:
        raise CensusRefusal('client must be clean pinned m1n1')
    sys.path.insert(0, str(a.m1n1 / 'proxyclient'))
    from m1n1.proxy import M1N1Proxy, UartInterface, Serial
    selected = launch.usb_identity.select_primary(launch.usb_identity.discover(), a.device)
    def timeout(*_):
        raise TimeoutError('bounded census expired')
    old = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    transport = None
    try:
        transport = Serial(selected, UartInterface.DEFAULT_BAUD_RATE)
        iface = UartInterface(device=transport)
        iface.tty_enable = False
        iface.dev.timeout = 5
        result = observe(iface, M1N1Proxy(iface), image)
    finally:
        try:
            if transport is not None:
                transport.close()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        # No raw exception message: USB paths/ADT objects can contain identifiers.
        reason = str(exc) if isinstance(exc, CensusRefusal) else type(exc).__name__
        print('STOP smp31a: ' + reason + '; no retry; return to Macintosh HD', file=sys.stderr)
        raise SystemExit(130 if isinstance(exc, KeyboardInterrupt) else 1)
