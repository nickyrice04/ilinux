#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package the original 31AC diagnostic payload for offline format inspection.

This has no install, configure-boot, signing, USB or execution operation. A
parser accepting this image does not prove firmware acceptance. Native use is
not qualified. All pointers captured by the diagnostic remain private.
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
IMAGE_BYTES = 0x2C000
DEFAULT_BASE = 0xFFFFFE0007004000
ENTRY_OFFSET = 0x10000
ROOT = Path(__file__).resolve().parents[3]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def segment(name: str, address: int, offset: int, size: int, protection: int,
            section: bytes = b"") -> bytes:
    return struct.pack("<II16sQQQQiiII", 0x19, 72 + len(section), name.encode(),
                       address, size, offset, size, protection, protection,
                       bool(section), 0) + section


def package(payload: bytes, base: int = DEFAULT_BASE) -> tuple[bytes, dict]:
    """Keep every original payload offset; write only its reserved header page.

    The separate producer audits ELF symbols, instructions and relocations.
    This function establishes packaging geometry, not that producer's ABI or
    firmware mapping. A uniformly slid PC-relative image needs page-aligned
    placement; the actual loader must establish that placement independently.
    """
    if type(base) is not int or base < 0 or base % PAGE or base + IMAGE_BYTES > 1 << 64:
        raise ValueError("base must be aligned and image must fit uint64")
    if len(payload) != PAYLOAD_BYTES:
        raise ValueError("expected exactly the 31AC payload geometry")
    if any(payload[:ENTRY_OFFSET]):
        raise ValueError("reserved header, capture and stack must start zero")
    if not any(payload[ENTRY_OFFSET:0x20000]):
        raise ValueError("missing original entry code")
    if not any(payload[0x20000:PAYLOAD_BYTES]):
        raise ValueError("missing original late-text sentinel")

    metadata = plistlib.dumps({"_PrelinkInfoDictionary": [],
        "_PrelinkKCID": hashlib.sha256(payload).digest()[:16]}, fmt=plistlib.FMT_XML)
    if len(metadata) > PAGE:
        raise ValueError("metadata exceeds reserved page")
    info = struct.pack("<16s16sQQIIIIIIII", b"__info", b"__PRELINK_INFO",
                       base + 0x24000, len(metadata), 0x24000, 0, 0, 0, 0, 0, 0, 0)
    # Public ARM_THREAD_STATE64. Only the original entry PC is supplied.
    state = bytearray(272)
    struct.pack_into("<Q", state, 256, base + ENTRY_OFFSET)
    commands = [
        segment("__TEXT", base, 0, PAGE, 1),
        segment("__DATA_SPTM", base + PAGE, PAGE, 3 * PAGE, 3),
        segment("__TEXT_BOOT_EXEC", base + ENTRY_OFFSET, ENTRY_OFFSET, 4 * PAGE, 5),
        segment("__TEXT_EXEC", base + 0x20000, 0x20000, PAGE, 5),
        struct.pack("<IIII", 5, 288, 6, 68) + state,
        segment("__PRELINK_INFO", base + 0x24000, 0x24000, PAGE, 1, info),
        segment("__LINKEDIT", base + 0x28000, 0x28000, PAGE, 1),
    ]
    body = b"".join(commands)
    # Flat MH_FILESET follows the measured 31Y parser case; no claim that a
    # fileset-entry-free image is accepted by the actual monitor/firmware.
    header = struct.pack("<8I", 0xFEEDFACF, 0x100000C, 2, 12,
                         len(commands), len(body), 1, 0) + body
    if len(header) >= PAGE:
        raise ValueError("load commands exceed reserved header")
    image = bytearray(payload + bytes(IMAGE_BYTES - len(payload)))
    image[:len(header)] = header
    image[0x24000:0x24000 + len(metadata)] = metadata
    report = {"schema": 1, "purpose": "OFFLINE_ORIGINAL_ENTRY_DIAGNOSTIC",
        "native": "PREPARED_FOR_REVIEW", "installation_performed": False,
        "payload_sha256": sha(payload), "payload_bytes": len(payload),
        "image_sha256": sha(image), "image_bytes": len(image),
        "base": hex(base), "entry": hex(base + ENTRY_OFFSET),
        "payload_offsets_preserved": True, "chained_fixups_command": False,
        "firmware_acceptance": "NOT_TESTED", "monitor_calls": "NOT_RUN",
        "physical_secondary_execution": "NOT_RUN"}
    return bytes(image), report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT / "build" not in output.parents or output.exists():
        parser.error("output must be a new directory under the repository build/")
    if args.payload.is_symlink() or args.payload.stat().st_size != PAYLOAD_BYTES:
        parser.error("payload must be a regular, exact-size original producer output")
    image, report = package(args.payload.read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    (output / "ilinux-31ac.macho").write_bytes(image)
    (output / "packaging.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
