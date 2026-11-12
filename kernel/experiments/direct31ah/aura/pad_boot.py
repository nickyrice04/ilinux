#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline, bounded padding of the pinned Aura direct-entry Mach-O layout.

Based on the public layout/relocation contract in Aurora Silicon's
aurora-installer@2d5c44e37d04173cb7085120b34862b75a609934,
AuraStage1.swift: MachOBootObject.expandExecuteWindow(). This is an independent,
narrow Python implementation for reviewed workspace artifacts. It neither
enrolls nor executes a boot object and never queries or changes a boot policy.
"""
import argparse
import hashlib
import json
import os
import stat
import struct
from collections import Counter
from pathlib import Path

PAGE = 0x4000
SLOT = 16 << 20
ALIGN = 2 << 20
WINDOW = 128 << 20
CODE_SIZE = SLOT + ALIGN - PAGE + WINDOW
MAX_INPUT = 32 << 20
MAX_OUTPUT = 192 << 20
SEGMENT = 0x19
THREAD = 5
FIXUPS = 0x80000034
FILESET = 0x80000035
INVENTORY = ('__TEXT', '__PRELINK_TEXT', '__TEXT_EXEC', '__PRELINK_INFO', '__DATA', '__LINKEDIT')
PROTS = dict(zip(INVENTORY, (1, 1, 5, 3, 3, 1)))
ALLOWED = {SEGMENT, THREAD, FIXUPS, FILESET, 0x1b, 0x32, 2, 0xb}


def require(value, message):
    if not value:
        raise ValueError(message)


def u32(data, offset):
    require(0 <= offset <= len(data) - 4, 'truncated u32')
    return struct.unpack_from('<I', data, offset)[0]


def u64(data, offset):
    require(0 <= offset <= len(data) - 8, 'truncated u64')
    return struct.unpack_from('<Q', data, offset)[0]


def add(a, b):
    require(0 <= a < 1 << 64 and 0 <= b < 1 << 64 and a + b < 1 << 64,
            '64-bit address overflow')
    return a + b


def commands(data, offset, expected_kind):
    require(u32(data, offset) == 0xfeedfacf, 'not little-endian Mach-O64')
    require(u32(data, offset + 4) == 0x0100000c and
            u32(data, offset + 8) == 0xc0000002, 'wrong CPU type/subtype')
    require(u32(data, offset + 12) == expected_kind, 'wrong Mach-O file type')
    count, length = u32(data, offset + 16), u32(data, offset + 20)
    require(1 <= count <= 32 and 0 < length <= PAGE, 'unbounded load commands')
    pos = offset + 32
    limit = pos + length
    require(limit <= len(data), 'truncated command table')
    result = []
    for _ in range(count):
        command, size = u32(data, pos), u32(data, pos + 4)
        require(command in ALLOWED and size >= 8 and size % 8 == 0 and pos + size <= limit,
                'unknown or malformed load command')
        result.append((command, pos, size))
        pos += size
    require(pos == limit, 'command count/size disagreement')
    return result


def segments(data, cmds, logical_size):
    found = {}
    for command, pos, size in cmds:
        if command != SEGMENT:
            continue
        require(size >= 72, 'short segment')
        name = bytes(data[pos + 8:pos + 24]).split(b'\0', 1)[0].decode('ascii')
        require(name in PROTS and name not in found, 'unexpected/duplicate segment')
        vm, extent, off, backed = struct.unpack_from('<4Q', data, pos + 24)
        nsects = u32(data, pos + 64)
        require(size == 72 + 80 * nsects and nsects <= 1, 'unsupported section geometry')
        require(extent > 0 and extent % PAGE == 0 and vm % PAGE == 0 and off % PAGE == 0,
                'unaligned or empty segment')
        require(backed == extent and add(off, backed) <= logical_size, 'not fully file-backed')
        require(u32(data, pos + 56) == PROTS[name] and u32(data, pos + 60) == PROTS[name],
                'unexpected segment protection')
        if nsects:
            sec = pos + 72
            require(bytes(data[sec + 16:sec + 32]).split(b'\0', 1)[0].decode('ascii') == name,
                    'section segment disagreement')
            address, length = u64(data, sec + 32), u64(data, sec + 40)
            require(vm <= address <= add(address, length) <= add(vm, extent), 'section escapes segment')
            sec_off = u32(data, sec + 48)
            require(sec_off == off + address - vm, 'section file offset disagreement')
        found[name] = dict(command=pos, vm=vm, size=extent, off=off, sections=nsects)
    return found


def inspect(data, logical_size=None):
    logical_size = len(data) if logical_size is None else logical_size
    require(0x1c000 <= len(data) <= MAX_OUTPUT and len(data) <= logical_size <= MAX_OUTPUT,
            'invalid file extent')
    outer = commands(data, 0, 12)
    require(Counter(c for c, _, _ in outer) ==
            Counter({SEGMENT: 6, THREAD: 1, FIXUPS: 1, FILESET: 1, 0x1b: 1, 0x32: 1}),
            'unexpected outer command inventory')
    segs = segments(data, outer, logical_size)
    require(tuple(segs) == INVENTORY, 'unexpected outer segment inventory/order')
    base = segs['__TEXT']['vm']
    end = 0
    for seg in segs.values():
        require(seg['off'] == end and seg['vm'] - base == end, 'nonlinear/overlapping layout')
        end = add(end, seg['size'])
    require(end == logical_size and segs['__TEXT']['off'] == 0, 'trailing bytes or nonzero header')
    code = segs['__TEXT_EXEC']
    require(code['off'] == 0x10000 and code['sections'] == 0, 'unsupported raw image offset/sections')
    require(data[code['off'] + 0x808:code['off'] + 0x810] == b'AURALOAD', 'missing Aura load header')
    require(u64(data, code['off'] + 0x818) <= SLOT, 'Aura runtime memory exceeds slot')
    members = [(pos, size) for command, pos, size in outer if command == FILESET]
    require(len(members) == 1, 'expected one fileset member')
    pos, size = members[0]
    member_vm, member_off, nameoff = u64(data, pos + 8), u64(data, pos + 16), u32(data, pos + 24)
    require(32 <= nameoff < size and data[pos + nameoff:pos + size].rstrip(b'\0') == b'com.apple.kernel',
            'unexpected fileset identity')
    require(member_vm == segs['__PRELINK_TEXT']['vm'] and member_off == segs['__PRELINK_TEXT']['off'],
            'member does not point to header segment')
    member = commands(data, member_off, 2)
    require(Counter(c for c, _, _ in member) ==
            Counter({SEGMENT: 4, THREAD: 1, 0x1b: 1, 0x32: 1, 2: 1, 0xb: 1}),
            'unexpected member command inventory')
    inner_segs = segments(data, member, logical_size)
    require(tuple(inner_segs) == ('__TEXT', '__TEXT_EXEC', '__DATA', '__LINKEDIT'),
            'unexpected member segments')
    for name in ('__TEXT_EXEC', '__DATA', '__LINKEDIT'):
        require({k: inner_segs[name][k] for k in ('vm', 'off', 'size')} ==
                {k: segs[name][k] for k in ('vm', 'off', 'size')}, 'outer/member segment disagreement')
    require({k: inner_segs['__TEXT'][k] for k in ('vm', 'off', 'size')} ==
            {k: segs['__PRELINK_TEXT'][k] for k in ('vm', 'off', 'size')} and
            inner_segs['__TEXT']['sections'] == 0, 'member text header disagreement')
    for cmds in (outer, member):
        threads = [(p, n) for c, p, n in cmds if c == THREAD]
        require(len(threads) == 1, 'expected one thread command')
        p, n = threads[0]
        require(n == 288 and u32(data, p + 8) == 6 and u32(data, p + 12) == 68,
                'unsupported arm64 thread state')
        regs = struct.unpack_from('<34Q', data, p + 16)
        expected = [0] * 34
        expected[16], expected[32] = code['vm'], code['vm'] + 0x800
        require(tuple(expected) == regs, 'unexpected entry/vector/register state')
    all_cmds = outer + member
    for command, pos, size in all_cmds:
        if command in (2, 0xb):
            require(not any(data[pos + 8:pos + size]), 'nonempty symbol metadata')
    fixups = [(pos, size) for command, pos, size in outer if command == FIXUPS]
    require(len(fixups) == 1 and fixups[0][1] == 16, 'unexpected fixup command')
    fp = fixups[0][0]
    fixoff, fixlen = u32(data, fp + 8), u32(data, fp + 12)
    require(fixoff == segs['__LINKEDIT']['off'] and fixlen == 56, 'unexpected fixup bounds')
    # A head-only revalidation cannot inspect the sparse tail. The full input/output can.
    if fixoff + fixlen <= len(data):
        require(struct.unpack_from('<7I', data, fixoff) == (0, 28, 56, 56, 0, 1, 0),
                'unsupported chained-fixup header')
        require(struct.unpack_from('<7I', data, fixoff + 28) == (6, 0, 0, 0, 0, 0, 0),
                'nonempty chained fixups')
    return dict(base=base, code=code, segments=segs, commands=all_cmds,
                entry=code['vm'] + 0x800, logical_size=logical_size)


def plan(data):
    require(len(data) <= MAX_INPUT, 'input exceeds bounded source size')
    before = inspect(data)
    code = before['code']
    require(code['size'] <= SLOT and CODE_SIZE >= code['size'], 'already padded or oversized input')
    old_end, file_end = add(code['vm'], code['size']), add(code['off'], code['size'])
    growth = CODE_SIZE - code['size']
    require(len(data) + growth <= MAX_OUTPUT, 'expanded output exceeds bound')
    patched = bytearray(data)
    def put64(pos, value):
        struct.pack_into('<Q', patched, pos, value)
    def put32(pos, value):
        require(value <= 0xffffffff, '32-bit offset overflow')
        struct.pack_into('<I', patched, pos, value)
    for command, pos, size in before['commands']:
        if command == SEGMENT:
            vm, extent, off = u64(data, pos + 24), u64(data, pos + 32), u64(data, pos + 40)
            name = bytes(data[pos + 8:pos + 24]).split(b'\0', 1)[0].decode('ascii')
            if name == '__TEXT_EXEC':
                put64(pos + 32, CODE_SIZE)
                put64(pos + 48, CODE_SIZE)
            elif vm >= old_end:
                put64(pos + 24, add(vm, growth))
                put64(pos + 40, add(off, growth))
                if u32(data, pos + 64):
                    sec = pos + 72
                    put64(sec + 32, add(u64(data, sec + 32), growth))
                    put32(sec + 48, u32(data, sec + 48) + growth)
        elif command == FIXUPS:
            require(u32(data, pos + 8) >= file_end, 'fixups precede movable tail')
            put32(pos + 8, u32(data, pos + 8) + growth)
    head, tail = bytes(patched[:file_end]), bytes(patched[file_end:])
    after = inspect(head, len(data) + growth)
    require(after['entry'] == before['entry'], 'entry moved during padding')
    require(head[code['off']:] == data[code['off']:file_end], 'raw image changed during padding')
    return head, tail, growth, dict(schema=1, scope='OFFLINE_LAYOUT_ONLY',
        window_bytes=WINDOW, aura_slot_bytes=SLOT, alignment_bytes=ALIGN,
        original_bytes=len(data), output_bytes=len(data)+growth, padding_bytes=growth,
        expected_kcbz=0, expected_kcrz=code['off']+CODE_SIZE,
        raw_slot_sha256=hashlib.sha256(data[code['off']:file_end]).hexdigest(),
        original_sha256=hashlib.sha256(data).hexdigest(), native_tested=False,
        enrolled=False, restart_ready=False)


def read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit, 'not a bounded regular file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            result = stream.read(limit + 1)
        require(len(result) == info.st_size, 'input size changed')
        return result
    finally:
        os.close(fd)


def pad_file(source, output):
    data = read_regular(source, MAX_INPUT)
    head, tail, growth, receipt = plan(data)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    complete = False
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(head)
            stream.seek(growth, os.SEEK_CUR)
            stream.write(tail)
            stream.flush()
        os.fsync(fd)
        expanded = read_regular(output, MAX_OUTPUT)
        inspect(expanded)
        require(expanded[:len(head)] == head and expanded[-len(tail):] == tail,
                'output head/tail verification failed')
        require(not any(expanded[len(head):len(head)+growth]), 'nonzero padding')
        receipt['output_sha256'] = hashlib.sha256(expanded).hexdigest()
        complete = True
        return receipt
    finally:
        os.close(fd)
        if not complete:
            Path(output).unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(pad_file(args.input, args.output), indent=2))


if __name__ == '__main__':
    main()
