#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Strict original ELF geometry and finite instruction-class audit."""
from __future__ import annotations
import hashlib
import struct
SIZE = 0x60000
BOOT = 0x5c000
SYSTEM = {
    0xd5033f9f, 0xd5033fdf, 0xd5034fdf,  # DSB, ISB, DAIFSet
    0xd50b7a2d,                         # DC CVAC,x13
    0xd50c7800, 0xd50c7802, 0xd50c7820, # AT S1E2R/W
    0xd5187402, 0xd5187404, 0xd51cc009, # PAR restore, VBAR_EL2
    0xd538076d, 0xd5384249,             # MMFR3, CurrentEL
    0xd5387400, 0xd5387402, 0xd5387404, 0xd5387405,
    0xd53b0020, 0xd53b4232,             # CTR, DAIF
    0xd53c100b, 0xd53c1109, 0xd53c204c, 0xd53c206e,
    0xd53c403d, 0xd53c521c, 0xd53c6010, # ELR,ESR,FAR
}
PIXEL_STORE = 0xb82b7940  # STR w0,[x10,x11,LSL#2], no writeback


def require(value, message):
    if not value:
        raise ValueError(message)


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def instruction(word, offset, base):
    """Allow only this probe's ordinary A64 classes; reject implicit SP uses.

    This proves the emitted operation classes and the sole store encoding. It
    does not replace review/tests of the address-validation control/data flow.
    """
    rd, rn = word & 31, (word >> 5) & 31
    if word == PIXEL_STORE:
        return "pixel_store"
    if word in SYSTEM:
        return "system"
    if word == 0xd65f03c0:  # RET x30, helpers have explicit LR convention
        return "return"
    if word & 0x7c000000 == 0x14000000:
        target = offset + signed(word & 0x3ffffff, 26) * 4
        require(BOOT <= target < SIZE, "direct branch outside boot code")
        return "branch"
    if word & 0xff000010 == 0x54000000:
        target = offset + signed((word >> 5) & 0x7ffff, 19) * 4
        require(BOOT <= target < SIZE, "conditional branch outside boot code")
        return "branch"
    if word & 0x7e000000 == 0x34000000:
        target = offset + signed((word >> 5) & 0x7ffff, 19) * 4
        require(BOOT <= target < SIZE, "compare branch outside boot code")
        return "branch"
    if word & 0x7e000000 == 0x36000000:
        target = offset + signed((word >> 5) & 0x3fff, 14) * 4
        require(BOOT <= target < SIZE, "test branch outside boot code")
        return "branch"
    if word & 0x9f000000 == 0x10000000:  # ADR, no ADRP/literal load
        delta = signed(((word >> 5) & 0x7ffff) << 2 | (word >> 29) & 3, 21)
        require(rd != 31 and offset + delta in (0, 0x5c800), "unapproved ADR target")
        return "address"
    if word & 0xffc00000 in (0xf9400000, 0xb9400000, 0x79400000):
        require(rn != 31, "SP-based load")
        return "load"
    if word & 0x1f000000 == 0x11000000:  # ADD/SUB immediate
        require(rn != 31 and (rd != 31 or word & (1 << 29)), "SP arithmetic")
        return "alu"
    if word & 0x1f200000 == 0x0b000000:  # shifted, never extended/SP
        return "alu"
    if word & 0x1f800000 == 0x12000000:  # logical immediate
        require(rd != 31 or (word >> 29) & 3 == 3, "SP logical destination")
        return "alu"
    if word & 0x1f800000 == 0x12800000:  # MOVZ/MOVN/MOVK
        return "alu"
    if word & 0x1f800000 == 0x13000000:  # bitfield, LSR/LSL/UBFX
        require(rd != 31 and rn != 31, "unapproved bitfield register")
        return "alu"
    if word & 0x1f000000 == 0x0a000000:  # logical shifted register
        return "alu"
    if word & 0x7fe00000 == 0x1a800000:  # conditional select, no SP
        return "alu"
    if word & 0xffe0fc00 == 0x9ac02000:  # LSLV
        return "alu"
    if word & 0xffe08000 in (0x9b000000, 0x9bc00000):  # MADD/MUL/UMULH
        return "alu"
    raise ValueError(f"unapproved instruction {word:#010x} at {offset:#x}")


def audit(data: bytes, base: int):
    require(64 <= len(data) <= 4 * 1024 * 1024, "ELF size")
    require(data[:7] == b"\x7fELF\x02\x01\x01", "ELF64 little-endian required")
    kind, machine, version, entry, po, so, flags, eh, ps, pn, ss, sn, si = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    require((kind, machine, version, entry, eh, ps, ss) == (2, 183, 1, base + BOOT, 64, 56, 64), "ELF identity")
    require(po + ps * pn <= len(data) and so + ss * sn <= len(data) and si < sn, "ELF table bounds")
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, so + i * ss) for i in range(sn)]
    names = sections[si]
    def string(offset, size, index):
        require(index < size and offset + size <= len(data), "string bounds")
        end = data.find(b"\0", offset + index, offset + size)
        require(end >= 0, "unterminated string")
        return data[offset + index:end].decode("ascii")
    allocated, symbols, functions = [], {}, []
    for s in sections:
        name, typ, sf, addr, off, size, link, info, align, entsize = s
        label = string(names[4], names[5], name)
        require(not (typ in (4, 9, 6, 11) and size), "relocation/dynamic section")
        if sf & 2 and size:
            require(typ == 1 and off + size <= len(data), "unexpected allocated section")
            allocated.append((label, addr - base, size, sf))
        if typ != 2:
            continue
        require(entsize == 24 and size % 24 == 0 and off + size <= len(data) and link < sn, "symbol bounds")
        strings = sections[link]
        for pos in range(off, off + size, 24):
            ni, sk, other, index, value, extent = struct.unpack_from("<IBBHQQ", data, pos)
            label = string(strings[4], strings[5], ni)
            require(not label or index != 0, "undefined symbol: " + label)
            if not label or label.startswith("$"):
                continue
            require(label not in symbols or symbols[label] == (value, extent), "duplicate symbol")
            symbols[label] = (value, extent)
            if sk & 15 == 2 and extent:
                functions.append((label, value - base, extent))
    require(allocated == [(".reserved", 0x4000, 0x54000, 2), (".late", 0x58000, 0x4000, 6), (".boot", BOOT, 0x4000, 6)], "section geometry")
    payload, loads = bytearray(SIZE), []
    for i in range(pn):
        typ, perm, off, va, pa, fs, ms, align = struct.unpack_from("<IIQQQQQQ", data, po + i * ps)
        if typ != 1:
            continue
        require(va == pa and fs == ms and off + fs <= len(data) and va >= base and va + ms <= base + SIZE, "load bounds")
        loads.append((va - base, ms, perm))
        payload[va - base:va - base + fs] = data[off:off + fs]
    require(loads == [(0x4000, 0x54000, 4), (0x58000, 0x4000, 5), (BOOT, 0x4000, 5)], "load geometry")
    require(not any(payload[:0x58000]), "header/reserved storage must remain zero")
    require(not any(payload[0x58004:BOOT]), "unused normal executable padding")
    for name, offset in (("native_image_base", 0), ("reserved_sptm_begin", 0x4000), ("reserved_sptm_end", 0x58000), ("native_late_park", 0x58000), ("native_entry", BOOT), ("native_vectors", 0x5c800), ("immutable_main", 0x5d000), ("native_image_end", SIZE)):
        require(symbols[name][0] == base + offset, "symbol geometry: " + name)
    for name in ("native_park", "native_fault_park", "native_late_park"):
        require(struct.unpack_from("<I", payload, symbols[name][0] - base)[0] == 0x14000000, "self-park instruction")
    covered, counts = set(), {}
    for label, offset, size in functions:
        if label == "native_late_park":
            require((offset, size) == (0x58000, 4), "late function extent")
            continue
        require(size % 4 == 0 and BOOT <= offset and offset + size <= SIZE, "function bounds: " + label)
        for pos in range(offset, offset + size, 4):
            require(pos not in covered, "overlapping functions")
            covered.add(pos)
            category = instruction(struct.unpack_from("<I", payload, pos)[0], pos, base)
            counts[category] = counts.get(category, 0) + 1
    for slot in range(16):
        pos = 0x5c800 + slot * 128
        move, branch = struct.unpack_from("<II", payload, pos)
        delta = (symbols["native_fatal"][0] - base - pos - 4) // 4
        require(move == 0xd2800011 + (slot << 5) and branch == 0x14000000 + (delta & 0x3ffffff), "vector slot instructions")
        require(not any(payload[pos + 8:pos + 128]), "vector padding")
        covered.update((pos, pos + 4))
    require(counts.get("pixel_store") == 1, "exactly one memory-store instruction required")
    require(struct.unpack_from("<I", payload, symbols["immutable_pixel_store"][0] - base)[0] == PIXEL_STORE, "named pixel store")
    for pos in range(BOOT, SIZE, 4):
        require(pos in covered or payload[pos:pos + 4] == bytes(4), "unaudited boot bytes")
    return bytes(payload), {
        "payload_bytes": SIZE, "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "symbols": {k: {"offset": v[0] - base, "bytes": v[1]} for k, v in sorted(symbols.items())},
        "load_segments": loads, "instruction_classes": counts,
        "memory_store_instruction_count": 1, "store_encoding": hex(PIXEL_STORE),
        "store_destination": "validated framebuffer; x10 row VA + x11 column *4",
        "SP_instructions": 0, "owned_image_stores": 0, "indirect_calls": 0,
        "guarded_transitions": 0, "undefined_symbols": 0, "retained_relocations": 0,
        "writable_load_segments": 0, "boot_code_bytes": len(covered) * 4,
        "complete_address_validation_proof": False,
    }
