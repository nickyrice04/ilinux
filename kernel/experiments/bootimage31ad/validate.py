#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent strict parser for the original nested 31AD control profile.

Only workspace bytes are read. This is not Apple's validator or an acceptance
oracle; a matching result checks our stated nested-image/entry geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import struct


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse(data: bytes, start: int, filetype: int) -> dict:
    need(0 <= start <= len(data) - 32, "header outside file")
    magic, cpu, sub, kind, ncmd, cmdbytes, flags, reserved = struct.unpack_from("<8I", data, start)
    need((magic, cpu, sub, kind, flags, reserved) ==
         (0xFEEDFACF, 0x100000C, 2, filetype, 1, 0), "unexpected Mach-O header profile")
    need(0 < ncmd <= 32 and 0 < cmdbytes <= 0x4000 - 32, "invalid command extent")
    end = start + 32 + cmdbytes
    need(end <= start + 0x4000 and end <= len(data), "command table outside header page")
    pos = start + 32
    result = {"segments": [], "entries": [], "thread": []}
    for _ in range(ncmd):
        need(pos + 8 <= end, "truncated command header")
        command, size = struct.unpack_from("<II", data, pos)
        need(size >= 8 and size % 8 == 0 and pos + size <= end, "invalid command length")
        if command == 0x19:
            need(size >= 72, "short segment")
            name, va, vmsize, off, filesize, maximum, initial, sections, segflags = struct.unpack_from(
                "<16sQQQQiiII", data, pos + 8)
            name = name.rstrip(b"\0")
            need(size == 72 + 80 * sections and sections <= 1, "segment section count mismatch")
            need(vmsize > 0 and filesize == vmsize, "unsupported zero-fill or segment size")
            need(off <= len(data) and filesize <= len(data) - off, "segment outside file")
            need(va + vmsize <= 1 << 64, "virtual segment overflow")
            need(va % 0x4000 == off % 0x4000 == vmsize % 0x4000 == 0, "unaligned segment")
            need(initial == maximum and initial in (1, 3, 5) and segflags == 0, "unexpected segment permissions")
            section = None
            if sections:
                secname, secseg, secva, secsize, secoff, align, reloff, nreloc, secflags, r1, r2, r3 = struct.unpack_from(
                    "<16s16sQQIIIIIIII", data, pos + 72)
                need(secseg.rstrip(b"\0") == name, "section segment mismatch")
                need(off <= secoff and secsize <= off + filesize - secoff, "section outside segment")
                need(secva == va + secoff - off and secsize > 0, "section address mismatch")
                need((align, reloff, nreloc, secflags, r1, r2, r3) == (0, 0, 0, 0, 0, 0, 0), "unsupported section fields")
                section = {"name": secname.rstrip(b"\0"), "offset": secoff, "size": secsize}
            result["segments"].append({"name": name, "address": va, "size": vmsize,
                                       "offset": off, "protection": initial, "section": section})
        elif command == 5:
            need(size == 288 and struct.unpack_from("<II", data, pos + 8) == (6, 68), "bad thread state")
            state = bytearray(data[pos + 16:pos + size])
            pc = struct.unpack_from("<Q", state, 256)[0]
            state[256:264] = bytes(8)
            need(not any(state), "unexpected initial thread fields")
            result["thread"].append(pc)
        elif command == 0x80000035:
            need(size >= 40, "short fileset entry")
            vm, offset, nameoff, entry_reserved = struct.unpack_from("<QQII", data, pos + 8)
            need(32 <= nameoff < size and entry_reserved == 0, "invalid fileset entry string offset")
            string = data[pos + nameoff:pos + size]
            need(b"\0" in string, "unterminated fileset identifier")
            name, padding = string.split(b"\0", 1)
            need(name and not any(padding), "invalid fileset identifier padding")
            result["entries"].append({"address": vm, "offset": offset, "name": name})
        else:
            raise ValueError("unsupported load command")
        pos += size
    need(pos == end, "command count/size mismatch")
    need(not any(data[end:start + 0x4000]), "nonzero reserved header padding")
    names = [s["name"] for s in result["segments"]]
    need(len(names) == len(set(names)), "duplicate segment name")
    need(len(result["thread"]) == 1, "expected one thread state")
    for key in ("offset", "address"):
        ordered = sorted(result["segments"], key=lambda s: s[key])
        for left, right in zip(ordered, ordered[1:]):
            need(left[key] + left["size"] <= right[key], "overlapping segments")
    return result


def validate(data: bytes, payload: bytes | None = None) -> dict:
    need(len(data) == 0x30000, "unexpected complete image size")
    outer = parse(data, 0, 12)
    need(len(outer["entries"]) == 1, "expected exactly one fileset entry")
    entry = outer["entries"][0]
    need(entry["name"] == b"com.apple.kernel" and entry["offset"] == 0x4000,
         "unexpected kernel entry identifier or file offset")
    inner = parse(data, entry["offset"], 2)
    need(not inner["entries"], "nested fileset entry not supported")
    need(outer["thread"] == inner["thread"], "outer/inner entry mismatch")
    expected_names = [b"__TEXT", b"__DATA_SPTM", b"__TEXT_BOOT_EXEC",
                      b"__TEXT_EXEC", b"__PRELINK_INFO", b"__LINKEDIT"]
    need([s["name"] for s in outer["segments"]] == expected_names and
         [s["name"] for s in inner["segments"]] == expected_names, "segment set/order mismatch")
    outer_text, inner_text = outer["segments"][0], inner["segments"][0]
    need(outer_text["section"] is None and inner_text["section"] is None, "unexpected header section")
    base = inner_text["address"]
    need(base >= 0x4000 and entry["address"] == base, "kernel entry address mismatch")
    need((outer_text["address"], outer_text["offset"], outer_text["size"], outer_text["protection"]) ==
         (base - 0x4000, 0, 0x8000, 1), "outer header mapping mismatch")
    need((inner_text["offset"], inner_text["size"], inner_text["protection"]) ==
         (0x4000, 0x4000, 1), "inner header mapping mismatch")
    need(outer["segments"][1:] == inner["segments"][1:], "outer/inner segment descriptions disagree")
    expected = [(0x4000, 0x8000, 0xC000, 3), (0x10000, 0x14000, 0x10000, 5),
                (0x20000, 0x24000, 0x4000, 5), (0x24000, 0x28000, 0x4000, 1),
                (0x28000, 0x2C000, 0x4000, 1)]
    for seg, (delta, off, size, prot) in zip(inner["segments"][1:], expected):
        need((seg["address"], seg["offset"], seg["size"], seg["protection"]) ==
             (base + delta, off, size, prot), "payload mapping mismatch")
    pc = inner["thread"][0]
    boot = inner["segments"][2]
    need(pc == base + 0x10000 and boot["address"] <= pc < boot["address"] + boot["size"] and
         boot["protection"] == 5, "entry outside intended boot execution range")
    need(not any(data[0x8000:0x14000]), "capture/stack region must remain zero")
    need(any(data[0x14000:0x24000]) and any(data[0x24000:0x28000]), "missing original code sentinels")
    info = inner["segments"][4]["section"]
    need(info is not None and info["name"] == b"__info", "missing prelink section")
    need(all(s["section"] is None for s in inner["segments"] if s["name"] != b"__PRELINK_INFO"),
         "unexpected section")
    try:
        metadata = plistlib.loads(data[info["offset"]:info["offset"] + info["size"]])
    except Exception as exc:
        raise ValueError("invalid prelink metadata") from exc
    need(type(metadata) is dict and set(metadata) == {"_PrelinkKCID", "_PrelinkInfoDictionary"}, "metadata fields mismatch")
    need(metadata["_PrelinkInfoDictionary"] == [] and type(metadata["_PrelinkKCID"]) is bytes and
         len(metadata["_PrelinkKCID"]) == 16, "metadata profile mismatch")
    need(not any(data[info["offset"] + info["size"]:0x2C000]), "nonzero metadata padding")
    need(not any(data[0x2C000:]), "nonzero link-edit reservation")
    if payload is not None:
        need(len(payload) == 0x24000 and not any(payload[:0x10000]), "invalid supplied original payload")
        need(data[0x8000:0x28000] == payload[0x4000:], "payload bytes changed")
        need(metadata["_PrelinkKCID"] == hashlib.sha256(payload).digest()[:16], "payload/metadata binding mismatch")
    return {"status": "STRUCTURAL_PROFILE_PASS", "image_bytes": len(data),
            "image_sha256": hashlib.sha256(data).hexdigest(), "inner_base": hex(base),
            "entry": hex(pc), "fileset_entries": 1, "payload_compared": payload is not None,
            "native_acceptance": "NOT_TESTED", "installer_invoked": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--payload", type=Path)
    args = parser.parse_args()
    try:
        need(args.image.is_file() and not args.image.is_symlink(), "image must be a regular file")
        need(args.image.stat().st_size == 0x30000, "unexpected complete image size")
        if args.payload:
            need(args.payload.is_file() and not args.payload.is_symlink() and
                 args.payload.stat().st_size == 0x24000, "payload must be a regular exact-size file")
        payload = args.payload.read_bytes() if args.payload else None
        print(json.dumps(validate(args.image.read_bytes(), payload), sort_keys=True))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
