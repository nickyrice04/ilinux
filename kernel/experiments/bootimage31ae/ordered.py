#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package the relinked original 31AE payload in an ordered nested fileset.

No encoded code is relocated here. Only the reserved header page is replaced;
all subsequent payload bytes and payload virtual addresses are preserved.
This offline format experiment does not establish installer acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import struct

PAGE = 0x4000
PAYLOAD_BYTES = 0x24000
IMAGE_BYTES = 0x30000
ENTRY_OFFSET = 0x14000
VECTOR_OFFSET = 0x14800
RECORD_OFFSET = 0x4000
DEFAULT_BASE = 0xFFFFFE0007004000
ROOT = Path(__file__).resolve().parents[3]
IDENTIFIER = b"com.apple.kernel\0"  # Public format identifier only.


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def segment(name: str, address: int, offset: int, size: int, protection: int,
            section: bytes = b"") -> bytes:
    return struct.pack("<II16sQQQQiiII", 0x19, 72 + len(section), name.encode(),
                       address, size, offset, size, protection, protection,
                       bool(section), 0) + section


def thread(entry: int) -> bytes:
    state = bytearray(272)
    struct.pack_into("<Q", state, 256, entry)
    return struct.pack("<IIII", 5, 288, 6, 68) + state


def header(filetype: int, commands: list[bytes]) -> bytes:
    body = b"".join(commands)
    return struct.pack("<8I", 0xFEEDFACF, 0x100000C, 2, filetype,
                       len(commands), len(body), 1, 0) + body


def check_payload(payload: bytes) -> None:
    if type(payload) is not bytes or len(payload) != PAYLOAD_BYTES:
        raise ValueError("expected exact-size original ordered payload bytes")
    if any(payload[:PAGE]) or any(payload[0x4000:0x10000]):
        raise ValueError("reserved header, capture and stack must start zero")
    if not any(payload[0x10000:0x14000]) or not any(payload[0x14000:]):
        raise ValueError("missing original normal or boot executable code")


def package(payload: bytes, base: int = DEFAULT_BASE) -> tuple[bytes, dict]:
    """Prepend one page without changing any linked payload virtual address."""
    if (type(base) is not int or base < PAGE or base % PAGE or
            base - PAGE + IMAGE_BYTES > 1 << 64):
        raise ValueError("inner base must be aligned and complete image must fit uint64")
    check_payload(payload)
    outer_base = base - PAGE
    metadata = plistlib.dumps({"_PrelinkInfoDictionary": [],
        "_PrelinkKCID": hashlib.sha256(payload).digest()[:16]}, fmt=plistlib.FMT_XML)
    if len(metadata) > PAGE:
        raise ValueError("metadata exceeds page")
    info = struct.pack("<16s16sQQIIIIIIII", b"__info", b"__PRELINK_INFO",
                       base + 0x24000, len(metadata), 0x28000, 0, 0, 0, 0, 0, 0, 0)
    common = [
        segment("__DATA_SPTM", base + 0x4000, 0x8000, 0xC000, 3),
        segment("__TEXT_EXEC", base + 0x10000, 0x14000, PAGE, 5),
        segment("__TEXT_BOOT_EXEC", base + 0x14000, 0x18000, 0x10000, 5),
        thread(base + ENTRY_OFFSET),
        segment("__PRELINK_INFO", base + 0x24000, 0x28000, PAGE, 1, info),
        segment("__LINKEDIT", base + 0x28000, 0x2C000, PAGE, 1),
    ]
    inner = header(2, [segment("__TEXT", base, PAGE, PAGE, 1)] + common)
    entry_length = (32 + len(IDENTIFIER) + 7) & ~7
    entry = (struct.pack("<IIQQII", 0x80000035, entry_length, base, PAGE, 32, 0) +
             IDENTIFIER).ljust(entry_length, b"\0")
    outer = header(12, [segment("__TEXT", outer_base, 0, 2 * PAGE, 1)] + common + [entry])
    if len(outer) > PAGE or len(inner) > PAGE:
        raise ValueError("headers exceed reserved pages")
    image = bytearray(bytes(PAGE) + payload + bytes(IMAGE_BYTES - PAGE - len(payload)))
    image[:len(outer)] = outer
    image[PAGE:PAGE + len(inner)] = inner
    image[0x28000:0x28000 + len(metadata)] = metadata
    assert image[2 * PAGE:PAGE + len(payload)] == payload[PAGE:]
    report = {
        "schema": "ilinux31ae-ordered-nested-v1",
        "purpose": "OFFLINE_DATA_FIRST_STRUCTURAL_EXPERIMENT",
        "native": "NOT_QUALIFIED", "installation_performed": False,
        "image_bytes": len(image), "image_sha256": sha(image),
        "payload_bytes": len(payload), "payload_sha256": sha(payload),
        "outer_base": hex(outer_base), "inner_base": hex(base),
        "entry": hex(base + ENTRY_OFFSET), "vector": hex(base + VECTOR_OFFSET),
        "record": hex(base + RECORD_OFFSET),
        "inner_header_file_offset": PAGE, "payload_file_offset_shift": PAGE,
        "payload_virtual_offsets_preserved": True,
        "payload_bytes_after_reserved_header_preserved": True,
        "data_sptm_fileoff": 0x8000, "text_exec_fileoff": 0x14000,
        "boot_exec_fileoff": 0x18000, "prelink_info_fileoff": 0x28000,
        "linkedit_fileoff": 0x2C000,
        "checked_data_to_text_bytes": 0xC000,
        "checked_text_to_boot_bytes": 0x4000,
        "checked_boot_to_prelink_bytes": 0x10000,
        "checked_prelink_to_linkedit_bytes": 0x4000,
        "outer_type": "MH_FILESET", "inner_type": "MH_EXECUTE",
        "fileset_entries": 1, "fileset_identifier": "com.apple.kernel",
        "file_offsets": "COLLECTION_ABSOLUTE",
        "firmware_acceptance": "NOT_TESTED", "monitor_calls": "NOT_RUN",
        "physical_secondary_execution": "NOT_RUN",
    }
    return bytes(image), report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if (ROOT / "build" not in output.parents or args.output.is_symlink() or
            output.exists()):
        parser.error("output must be an absent directory beneath repository build/")
    try:
        if (args.payload.is_symlink() or not args.payload.is_file() or
                args.payload.stat().st_size != PAYLOAD_BYTES):
            parser.error("payload must be a regular, exact-size original file")
        image, report = package(args.payload.read_bytes())
        output.mkdir()
        (output / "ilinux-31ae-ordered.macho").write_bytes(image)
        (output / "packaging.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
