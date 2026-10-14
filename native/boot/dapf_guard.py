"""Pinned, RAM-only workaround for boot021's fixed AOP DAPF table entry.

The M5's AOP instance table declares DART+GAPF, no DAPF. Omit only this
nonexistent DAPF from m1n1's work list; never touch filter registers or code.
All other entries, firmware filter state and persistent boot files stay intact.
"""
from dataclasses import dataclass
import hashlib
import struct

IMAGE_SHA256 = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
TABLE_OFFSET = 0x102728
FUNCTION_START = 0x160e0
FUNCTION_END = 0x16618  # dapf_init + dapf_init_all, excluding alignment padding
ENTRIES = (('/arm-io/dart-aop', 1, 0x71218),
           ('/arm-io/dart-mtp', 1, 0x71230),
           ('/arm-io/dart-pmp', 1, 0x71248),
           ('/arm-io/dart-isp', 5, 0x71260),
           ('/arm-io/dart-isp0', 5, 0x71278))
DART, DAPF, GAPF = 0x44415254, 0x44415046, 0x47415046


def instance_types(raw, reg_count):
    if not isinstance(raw, bytes) or not raw or len(raw) % 16 or len(raw) // 16 != reg_count or reg_count > 256:
        raise ValueError('DAPF guard: malformed instance/register layout')
    return [(t, i) for t, i, _, _ in struct.iter_unpack('<4I', raw)]


def register_count(value):
    # Pinned ADT parsing retains raw bytes when parent ranges are unavailable;
    # otherwise it yields a sequence of addr/size records. Both encode 64-bit
    # address + 64-bit length here. Do not mistake byte count for range count.
    if isinstance(value, bytes) and value and len(value) % 16 == 0:
        return len(value) // 16
    if isinstance(value, (list, tuple)) and value:
        if len(value) == 2 and all(isinstance(v, int) for v in value):
            return 1  # ADT2Tuple fallback for one raw 16-byte reg property.
        if all((hasattr(v, 'addr') and hasattr(v, 'size')) or
               (isinstance(v, (list, tuple)) and len(v) == 2 and
                all(isinstance(n, int) for n in v)) for v in value):
            return len(value)
    raise ValueError('DAPF guard: unsupported register encoding')


def verify_image(image):
    if hashlib.sha256(image).hexdigest() != IMAGE_SHA256:
        raise ValueError('DAPF guard: unsupported m1n1 image')
    # These are initialized data slots whose pointers are relocated at boot.
    for n, (path, index, offset) in enumerate(ENTRIES):
        if image[offset:offset + len(path) + 1] != path.encode() + b'\0':
            raise ValueError('DAPF guard: path provenance mismatch')
        if image[TABLE_OFFSET + n * 16:TABLE_OFFSET + (n + 1) * 16] != struct.pack('<QiI', 0, index, 0):
            raise ValueError('DAPF guard: table provenance mismatch')
    if image[TABLE_OFFSET + 80:TABLE_OFFSET + 96] != struct.pack('<QiI', 0, -1, 0):
        raise ValueError('DAPF guard: sentinel provenance mismatch')


@dataclass(frozen=True)
class Plan:
    address: int
    original: bytes
    corrected: bytes


def prepare(iface, base, image, adt):
    """Read/validate only. Caller already checked chip, board and idle secondaries."""
    verify_image(image)
    code = image[FUNCTION_START:FUNCTION_END]
    if iface.readmem(base + FUNCTION_START, len(code)) != code:
        raise ValueError('DAPF guard: live code differs from pinned image')
    expected = b''.join(struct.pack('<QiI', base + off, index, 0)
                        for _, index, off in ENTRIES) + struct.pack('<QiI', 0, -1, 0)
    original = iface.readmem(base + TABLE_OFFSET, len(expected))
    if original != expected:
        raise ValueError('DAPF guard: table changed or correction already applied; use a fresh boot')
    for path, index, offset in ENTRIES:
        if iface.readmem(base + offset, len(path) + 1) != path.encode() + b'\0':
            raise ValueError('DAPF guard: live entry name differs from pinned image')
        try:
            node = adt[path]
        except KeyError:
            if path == ENTRIES[0][0]:
                raise ValueError('DAPF guard: expected AOP node absent') from None
            continue  # Same absent-node behavior as pinned dapf_init_all.
        try:
            layout = instance_types(node.instance, register_count(node.reg))
            compatible = node.compatible
        except AttributeError:
            raise ValueError('DAPF guard: required layout metadata absent') from None
        if not isinstance(compatible, (list, tuple)) or 'dart,t8110' not in compatible:
            raise ValueError('DAPF guard: unexpected DART type')
        selected = [i for i, pair in enumerate(layout) if pair == (DAPF, 0)]
        if path == ENTRIES[0][0]:
            if layout != [(DART, 0), (GAPF, 0)]:
                raise ValueError('DAPF guard: AOP layout differs from reviewed DART/GAPF case')
        elif selected != [index]:
            raise ValueError('DAPF guard: another DAPF entry needs separate review')
    # Shift intact remaining entries and their existing terminator; pad with
    # the same terminator. The entire 96-byte write stays inside dapf_entries.
    return Plan(base + TABLE_OFFSET, original, original[16:] + original[-16:])


def apply(iface, plan):
    """One bounded data write only after all other native preflight gates pass."""
    if len(plan.original) != 96 or len(plan.corrected) != 96:
        raise ValueError('DAPF guard: invalid plan size')
    if iface.readmem(plan.address, 96) != plan.original:
        raise ValueError('DAPF guard: table changed before correction')
    iface.writemem(plan.address, plan.corrected)
    if iface.readmem(plan.address, 96) != plan.corrected:
        raise ValueError('DAPF guard: RAM correction readback failed; stop and return to macOS')
