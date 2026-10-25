# SPDX-License-Identifier: MIT
"""Bounded ELF and exact original AArch64 instruction audit; never executes code."""
from __future__ import annotations
import struct

IMAGE_BYTES = 0x14000
GENTER = 0x00201420
GEOMETRY = {"host_capture": 0x4000, "host_stack_bottom": 0x8000,
            "host_stack_top": 0xc000, "host_entry": 0xc000,
            "host_vectors": 0xc800, "host_fixups_complete": 0xf000,
            "host_register_cpu": 0x10000, "host_register_exception_return": 0x10018}
PHASES = {"captured": 1, "vectors_parked": 2, "fatal_exception": 3, "unsupported_el": 0x80}
RECORD = {"magic": 0x00, "version": 0x08, "phase": 0x10, "current_el": 0x18,
          "daif": 0x20, "incoming_sp": 0x28, "x0": 0x30, "x1": 0x38, "x2": 0x40,
          "owned_sp": 0x48, "vector_base": 0x50, "hcr_el2": 0x58, "hcr_present": 0x60,
          "fault_slot": 0x68, "fault_el": 0x70, "fault_esr": 0x78,
          "fault_elr": 0x80, "fault_far": 0x88, "fault_spsr": 0x90,
          "fault_sp": 0x98, "fault_daif": 0xa0}


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


class Elf:
    def __init__(self, data: bytes):
        self.data = data
        need(len(data) <= 2 * 1024 * 1024, "ELF exceeds original-artifact bound")
        header = struct.unpack("<16sHHIQQQIHHHHHH", self.span(0, 64))
        ident, kind, machine, version, self.entry, phoff, shoff, _, ehsize, phsize, phnum, shsize, shnum, names = header
        need(ident[:7] == b"\x7fELF\x02\x01\x01" and kind == 2 and machine == 183 and version == 1,
             "expected little-endian AArch64 ELF64 executable")
        need(ehsize == 64 and phsize == 56 and shsize == 64 and 0 < phnum <= 16 and
             0 < shnum <= 64 and names < shnum, "unsupported ELF tables")
        self.programs = [struct.unpack("<IIQQQQQQ", self.span(phoff + i * 56, 56)) for i in range(phnum)]
        self.sections = [struct.unpack("<IIQQQQIIQQ", self.span(shoff + i * 64, 64)) for i in range(shnum)]
        self.phoff, self.shoff = phoff, shoff
        string_section = self.sections[names]
        need(string_section[1] == 3, "section-name table is not strings")
        strings = self.span(string_section[4], string_section[5])
        self.named_sections = {}
        self.symbols = {}
        self.symbol_file_offsets = {}
        for index, section in enumerate(self.sections):
            name, kind, flags, address, offset, size, link, _, _, entsize = section
            label = self.string(strings, name)
            if label:
                need(label not in self.named_sections, "duplicate section name")
                self.named_sections[label] = section
            if kind != 8:
                self.span(offset, size)
            need(not (kind in (4, 9) and size), "runtime or unresolved relocation section")
            need(kind not in (6, 11), "dynamic linking metadata is forbidden")
            if flags & 2 and size:
                need(label in (".data", ".boot", ".text") and kind == 1,
                     "unexpected allocated section")
            if kind != 2:
                continue
            need(entsize == 24 and size % 24 == 0 and link < shnum and self.sections[link][1] == 3,
                 "invalid symbol table")
            table = self.sections[link]
            symbol_names = self.span(table[4], table[5])
            for position in range(offset, offset + size, 24):
                name, info, _, target, value, extent = struct.unpack("<IBBHQQ", self.span(position, 24))
                label = self.string(symbol_names, name)
                need(not (target == 0 and label), "undefined symbol")
                if label and not label.startswith("$"):
                    need(label not in self.symbols, "duplicate named symbol")
                    self.symbols[label] = {"value": value, "size": extent, "type": info & 15,
                                           "binding": info >> 4, "section": target}
                    self.symbol_file_offsets[label] = position

    def span(self, offset: int, size: int) -> bytes:
        need(0 <= offset <= len(self.data) and 0 <= size <= len(self.data) - offset,
             "ELF span outside file")
        return self.data[offset:offset + size]

    @staticmethod
    def string(table: bytes, offset: int) -> str:
        need(0 <= offset < len(table), "string offset outside table")
        end = table.find(b"\0", offset)
        need(end >= 0, "unterminated ELF string")
        return table[offset:end].decode("ascii")

    def file_offset(self, address: int, size: int = 4) -> int:
        matches = [p[2] + address - p[3] for p in self.programs
                   if p[0] == 1 and p[3] <= address and size <= p[5] - (address - p[3])]
        need(len(matches) == 1, "address is not in exactly one file-backed segment")
        return matches[0]


def mrs_key(op0: int, op1: int, crn: int, crm: int, op2: int) -> int:
    return 0xd5200000 | op0 << 19 | op1 << 16 | crn << 12 | crm << 8 | op2 << 5


MRS = {mrs_key(3, 0, 4, 2, 2): "CurrentEL", mrs_key(3, 3, 4, 2, 1): "DAIF",
       mrs_key(3, 4, 1, 1, 0): "HCR_EL2"}
for level, op1 in ((1, 0), (2, 4)):
    for label, crn, crm, op2 in (("ESR", 5, 2, 0), ("ELR", 4, 0, 1),
                                ("FAR", 6, 0, 0), ("SPSR", 4, 0, 0)):
        MRS[mrs_key(3, op1, crn, crm, op2)] = f"{label}_EL{level}"


def inspect_code(payload: bytes, symbols: dict, base: int) -> dict:
    coverage = bytearray(IMAGE_BYTES)
    relative = []
    reads = []
    transports = {"host_fixups_complete": 15, "host_register_cpu": 14,
                  "host_register_exception_return": 18}
    for name, selector in transports.items():
        symbol = symbols[name]
        offset = symbol["value"] - base
        words = (0xa9bf7bfd, 0x910003fd, 0xd2800010 | selector << 5,
                 GENTER, 0xa8c17bfd, 0xd65f03c0)
        need(symbol["size"] == 24 and payload[offset:offset + 24] == struct.pack("<6I", *words),
             "transport body or argument-preservation shape changed")
        coverage[offset:offset + 24] = b"\1" * 24
    vectors = symbols["host_vectors"]["value"] - base
    need(symbols["host_vectors"]["size"] == 2048 and vectors % 2048 == 0, "vector geometry")
    fatal = symbols["host_fatal_vector"]["value"] - base
    for slot in range(16):
        pc = vectors + slot * 128
        first, branch = struct.unpack_from("<II", payload, pc)
        need(first == 0xd2800011 | slot << 5, "vector slot identity changed")
        need(branch & 0xfc000000 == 0x14000000 and pc + 4 + signed(branch & 0x3ffffff, 26) * 4 == fatal,
             "vector does not branch to owned fatal recorder")
        need(not any(payload[pc + 8:pc + 128]), "unexpected vector-slot instructions")
        coverage[pc:pc + 8] = b"\1" * 8
    instruction_count = 0
    for name in ("host_entry", "host_fatal_vector"):
        start = symbols[name]["value"] - base
        size = symbols[name]["size"]
        need(size > 0 and size % 4 == 0 and 0xc000 <= start < start + size <= 0xf000,
             "capture function boundary outside boot code")
        need(not any(coverage[start:start + size]), "function overlap")
        coverage[start:start + size] = b"\1" * size
        for pc in range(start, start + size, 4):
            word = struct.unpack_from("<I", payload, pc)[0]
            instruction_count += 1
            if word & 0x9f000000 == 0x10000000:  # ADR, deliberately no ADRP/literal loads
                imm = ((word >> 5) & 0x7ffff) << 2 | ((word >> 29) & 3)
                target = pc + signed(imm, 21)
                rd = word & 31
                need((rd, target) in ((6, 0x4000), (16, 0x4000), (7, 0xc000), (7, 0xc800)),
                     "unexpected PC-relative data reference")
                relative.append({"pc_offset": pc, "target_offset": target, "register": rd})
            elif word & 0xfc000000 == 0x14000000:
                target = pc + signed(word & 0x3ffffff, 26) * 4
                need(start <= target < start + size, "capture branch escapes its function")
            elif word & 0xff000010 == 0x54000000:
                target = pc + signed((word >> 5) & 0x7ffff, 19) * 4
                need(word & 15 in (0, 1) and start <= target < start + size,
                     "unexpected conditional capture branch")
            elif word & 0xff800000 in (0xd2800000, 0xf2800000):
                rd, immediate, shift = word & 31, (word >> 5) & 0xffff, (word >> 21) & 3
                need(rd in (7, 17) and (immediate, shift) in (
                    (0x5053, 0), (0x4d54, 1), (0x3133, 2), (0x4241, 3),
                    (1, 0), (2, 0), (3, 0), (0x80, 0)), "unexpected immediate constant")
            elif word & 0xffc00000 == 0xf9000000:  # STR unsigned64
                rn, rt, offset = (word >> 5) & 31, word & 31, ((word >> 10) & 0xfff) * 8
                need((rn == 6 and rt in (2, 3, 4, 5, 7)) or (rn == 16 and rt == 17),
                     "store base is not the owned record")
                need(offset in RECORD.values(), "store outside declared diagnostic fields")
            elif word & 0xffc00000 == 0xa9000000:  # STP signed-offset64
                rn, rt, rt2 = (word >> 5) & 31, word & 31, (word >> 10) & 31
                offset = signed((word >> 15) & 127, 7) * 8
                need(rn == 6 and (((rt, rt2) == (31, 31) and 0 <= offset <= 240 and offset % 16 == 0)
                                  or ((rt, rt2) == (0, 1) and offset == 0x30)), "unexpected pair store")
            elif word & 0xffc003ff == 0xf100007f or word & 0xffc003ff == 0xf100023f:
                need((word >> 10) & 0xfff in (4, 8), "unexpected EL comparison")
            elif word & 0xffffffe0 in MRS:
                need(word & 31 in (3, 4, 7, 17), "unexpected MRS destination")
                reads.append({"pc_offset": pc, "register": MRS[word & 0xffffffe0]})
            else:
                need(word in (0x910003e5, 0x910000ff, 0x910003f1,  # incomingSP/ownedSP/faultSP
                              0xd5034fdf, 0xd50041bf,  # DAIFSet15 / SPSel1
                              0xd518c007, 0xd51cc007,  # explicit VBAR banks
                              0xd5033f9f, 0xd5033fdf),  # DSB SY / ISB
                     f"unapproved original instruction at0x{pc:x}:0x{word:08x}")
    need(len(relative) == 4, "expected capture/fault/stack/vector address references")
    need(all(used or byte == 0 for used, byte in zip(coverage, payload)),
         "unaccounted nonzero data/instructions or absolute pointer material")
    return {"capture_instruction_count": instruction_count, "adr_references": relative,
            "system_reads": reads, "vector_slots": 16, "transports": transports,
            "entry_calls_transport": False, "runtime_pointer_fixups": False}


def inspect(data: bytes, base: int = 0) -> tuple[bytes, dict]:
    need(base >= 0 and base % 0x4000 == 0 and base <= (1 << 64) - IMAGE_BYTES,
         "unsupported image base")
    elf = Elf(data)
    need(elf.entry == base + 0xc000, "ELF entry changed")
    expected = [(0x4000, 0x8000, 6), (0xc000, 0x4000, 5), (0x10000, 0x4000, 5)]
    need(len(elf.programs) == 3 and all(p[0] == 1 for p in elf.programs), "unexpected program headers")
    payload = bytearray(IMAGE_BYTES)
    for p, (offset, size, flags) in zip(elf.programs, expected):
        kind, actual_flags, file_offset, va, pa, file_size, memory_size, alignment = p
        need((va, pa, file_size, memory_size, actual_flags) == (base + offset, base + offset, size, size, flags),
             "segment placement, size or permissions changed")
        need(alignment == 0x4000 and file_offset % alignment == va % alignment,
             "segment page geometry changed")
        payload[offset:offset + size] = elf.span(file_offset, size)
    for label, offset, size, flags in ((".data", 0x4000, 0x8000, 3),
                                       (".boot", 0xc000, 0x4000, 6),
                                       (".text", 0x10000, 0x4000, 6)):
        need(label in elf.named_sections, "missing allocated section")
        section = elf.named_sections[label]
        need((section[2], section[3], section[5]) == (flags, base + offset, size),
             "section placement or permissions changed")
    for name, offset in GEOMETRY.items():
        need(name in elf.symbols and elf.symbols[name]["value"] == base + offset, "symbol geometry: " + name)
    for name in ("host_park", "host_fatal_vector", "host_fault_park"):
        need(name in elf.symbols and base + 0xc000 <= elf.symbols[name]["value"] < base + 0xf000,
             "missing bounded diagnostic symbol: " + name)
    need(not any(payload[:0xc000]), "header/owned initial storage is not all zero")
    instruction_audit = inspect_code(bytes(payload), elf.symbols, base)
    symbols = {name: {"offset": value["value"] - base, "size": value["size"]}
               for name, value in elf.symbols.items() if name.startswith("host_") and
               base <= value["value"] <= base + IMAGE_BYTES}
    return bytes(payload), {"link_base": base, "image_bytes": IMAGE_BYTES, "entry_offset": 0xc000,
        "segments": [{"offset": off, "bytes": size, "flags": flags} for off, size, flags in expected],
        "symbols": symbols, "record_fields": RECORD, "record_magic": 0x424131334d545053,
        "record_version": 1, "phases": PHASES, "instruction_audit": instruction_audit,
        "relocation_sections": 0, "undefined_symbols": [], "native": "NOT_DEPLOYABLE"}
