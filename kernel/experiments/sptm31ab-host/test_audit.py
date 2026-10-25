# SPDX-License-Identifier: MIT
"""Adversarial checks against the actual linked original ELF, not a mock image."""
import struct
from audit import Elf, inspect


def run(data: bytes, base: int = 0) -> dict:
    elf = Elf(data)
    payload, report = inspect(data, base)
    rejected = 0

    def refuse(changed: bytes) -> None:
        nonlocal rejected
        try:
            inspect(changed, base)
        except (ValueError, UnicodeError, struct.error):
            rejected += 1
            return
        raise AssertionError("mutated original ELF was incorrectly admitted")

    def patch(offset: int, form: str, value: int) -> None:
        changed = bytearray(data)
        struct.pack_into(form, changed, offset, value)
        refuse(bytes(changed))

    # Header, bounds and mapping are independently required.
    refuse(data[:63])
    refuse(data[:-1])
    patch(24, "<Q", base + 0xc004)
    patch(40, "<Q", len(data) + 1)
    patch(elf.phoff + 4, "<I", 7)
    patch(elf.phoff + 32, "<Q", len(data) + 1)
    # Neither a named undefined dependency nor relocation metadata is allowed.
    patch(elf.symbol_file_offsets["host_register_cpu"] + 6, "<H", 0)
    boot_section = elf.named_sections[".boot"]
    section_index = elf.sections.index(boot_section)
    patch(elf.shoff + section_index * 64 + 4, "<I", 4)
    # Actual instructions, vector-slot destinations and non-code bytes matter.
    patch(elf.file_offset(base + 0xc000), "<I", 0xd65f03c0)  # premature return
    patch(elf.file_offset(base + 0xc800), "<I", 0xd2800031)  # wrong slot0 identity
    patch(elf.file_offset(base + 0xc804), "<I", 0x14000000)  # vector loops locally
    patch(elf.file_offset(base + 0xc808), "<I", 0xd503201f)  # extra vector instruction
    patch(elf.file_offset(base + 0xf00c), "<I", 0xd503201f)  # missing dispatch
    patch(elf.file_offset(base + 0xf008), "<I", 0xd28001d0)  # early routine uses14
    patch(elf.file_offset(base + 0x4000), "<Q", base + 0xc000 or 1)  # pointer-like data
    # Corrupt one independently resolved ADR target while retaining its opcode.
    adr = report["instruction_audit"]["adr_references"][0]
    position = elf.file_offset(base + adr["pc_offset"])
    instruction = struct.unpack_from("<I", data, position)[0]
    patch(position, "<I", instruction ^ (1 << 5))
    assert len(payload) == 0x14000 and rejected == 16
    return {"groups": 6, "mutation_refusals": rejected, "status": "PASS"}
