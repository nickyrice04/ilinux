#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent strict parser for the original ordered nested 31AE profile.

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
                need(off <= secoff <= off + filesize and secsize <= off + filesize - secoff, "section outside segment")
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
    result["split_range"] = split_range(result["segments"], len(data))
    return result


def profile_arithmetic(segments: list[dict], file_bytes: int, profile: bool) -> dict:
    """Original finite model of the two stated arithmetic profiles.

    This reports checked distances in our own headers. It is not an Apple
    validator, does not determine the real Recovery profile and is not an
    acceptance oracle. Segment permissions remain a separate own-image check.
    """
    need(type(profile) is bool and type(file_bytes) is int and 0 <= file_bytes <= 1 << 64,
         "invalid arithmetic profile or finite size")
    def role(name: bytes, optional: bool = False):
        matches = [s for s in segments if s["name"] == name]
        need(len(matches) <= 1 and (optional or len(matches) == 1),
             "arithmetic role count: " + name.decode())
        if not matches:
            return None
        result = matches[0]
        for key, limit in (("offset", file_bytes), ("address", 1 << 64)):
            start, size = result[key], result["size"]
            need(type(start) is int and type(size) is int and
                 0 <= start <= limit and 0 < size <= limit - start,
                 "arithmetic role extent outside " + key)
        return result
    text = role(b"__TEXT")
    normal = role(b"__TEXT_EXEC")
    owned = role(b"__DATA_SPTM", True)
    boot = role(b"__TEXT_BOOT_EXEC", True)
    prelink = role(b"__PRELINK_INFO")
    linkedit = role(b"__LINKEDIT")
    def difference(right, left, label):
        start, stop = left["offset"], right["offset"]
        need(0 <= start <= stop <= file_bytes,
             "arithmetic " + label + " would underflow or exceed file")
        return stop - start
    selected = (owned if owned is not None else normal) if profile else prelink
    return {"profile": profile, "selected_start_role": selected["name"].decode(),
            "profile_text_exec_bytes":
                (difference(boot, normal, "boot-minus-text-exec") if boot is not None
                 else normal["size"]) if profile else None,
            "selected_start_minus_text_bytes": difference(selected, text, "selected-minus-text"),
            "linkedit_minus_prelink_bytes": difference(linkedit, prelink, "linkedit-minus-prelink"),
            "text_exec_minus_data_bytes": difference(normal, owned, "text-exec-minus-data")
                if owned is not None else None,
            "prelink_minus_boot_bytes": difference(prelink, boot, "prelink-minus-boot")
                if boot is not None else None}


def split_range(segments: list[dict], file_bytes: int) -> dict:
    """Finite original split contract, including data, executable and tail roles.

    Every subtraction has an explicit order/extent guard. This public-format
    profile checks both address spaces, not just the old normal-to-boot starts.
    It is not Apple's validator and does not establish installer acceptance.
    """
    names = (b"__TEXT", b"__DATA_SPTM", b"__TEXT_EXEC",
             b"__TEXT_BOOT_EXEC", b"__PRELINK_INFO", b"__LINKEDIT")
    selected = []
    for name in names:
        matches = [s for s in segments if s["name"] == name]
        need(len(matches) == 1, "expected one split-profile segment: " + name.decode())
        selected.append(matches[0])
    text, owned, normal, boot, prelink, linkedit = selected
    need(owned["protection"] == 3, "split data permissions")
    need(normal["protection"] == boot["protection"] == 5, "split executable permissions")
    need(text["protection"] == prelink["protection"] == linkedit["protection"] == 1,
         "split header/tail permissions")
    need(type(file_bytes) is int and 0 <= file_bytes <= 1 << 64, "invalid finite file size")
    for segment in selected:
        size = segment["size"]
        need(type(size) is int and 0 < size <= 1 << 64, "invalid split segment extent")
        for key, limit in (("offset", file_bytes), ("address", 1 << 64)):
            start = segment[key]
            need(type(start) is int and 0 <= start <= limit and size <= limit - start,
                 "split segment extent outside " + key)
    # Start-order guards retain an explicit diagnostic for the observed 31AD
    # failure: its normal-text start precedes the data start in both headers.
    for key in ("offset", "address"):
        need(owned[key] <= normal[key], "split-protection data-to-text ordering would underflow")
        need(normal[key] <= boot[key], "split-protection executable ordering would underflow")
        need(boot[key] <= prelink[key], "split-protection boot-to-prelink ordering would underflow")
        need(prelink[key] <= linkedit[key], "split-protection prelink-to-linkedit ordering would underflow")
        need(text[key] <= normal[key], "split-protection fallback-text ordering would underflow")
    adjacent = []
    for left, right in zip(selected, selected[1:]):
        row = {"from": left["name"].decode(), "to": right["name"].decode()}
        for key, label in (("offset", "file"), ("address", "virtual")):
            end = left[key] + left["size"]
            need(end <= right[key], "split-protection adjacent extents overlap in " + label)
            row[label + "_start_delta"] = right[key] - left[key]
            row[label + "_gap"] = right[key] - end
        adjacent.append(row)
    return {"data_sptm_fileoff": owned["offset"],
            "text_exec_fileoff": normal["offset"], "boot_exec_fileoff": boot["offset"],
            "prelink_info_fileoff": prelink["offset"], "linkedit_fileoff": linkedit["offset"],
            "checked_data_to_text_bytes": normal["offset"] - owned["offset"],
            "checked_text_to_boot_bytes": boot["offset"] - normal["offset"],
            "checked_boot_to_prelink_bytes": prelink["offset"] - boot["offset"],
            "checked_prelink_to_linkedit_bytes": linkedit["offset"] - prelink["offset"],
            "checked_fallback_text_to_normal_bytes": normal["offset"] - text["offset"],
            "checked_adjacent_ranges": adjacent,
            "arithmetic_profiles": {"false": profile_arithmetic(segments, file_bytes, False),
                                    "true": profile_arithmetic(segments, file_bytes, True)}}


def range_check(data: bytes) -> dict:
    """Strict finite type-2/type-12 header parsing plus checked range ordering.

    Accept either one flat header or the single-kernel nested profile. This
    entry point deliberately permits the older flat geometry, so its reversed
    executable order is rejected by the range guard itself rather than by an
    unrelated nested-header requirement.
    """
    need(0x4000 <= len(data) <= 0x30000 and len(data) % 0x4000 == 0,
         "unsupported finite image size")
    kind = struct.unpack_from("<I", data, 12)[0]
    need(kind in (2, 12), "unsupported root file type")
    root = parse(data, 0, kind)
    checked = [{"header_offset": 0, "filetype": kind, **root["split_range"]}]
    if root["entries"]:
        need(kind == 12 and len(root["entries"]) == 1, "expected one nested kernel entry")
        entry = root["entries"][0]
        need(entry["name"] == b"com.apple.kernel" and entry["offset"] == 0x4000,
             "unexpected kernel entry identifier or file offset")
        inner = parse(data, entry["offset"], 2)
        need(not inner["entries"], "nested fileset entry not supported")
        need(root["thread"] == inner["thread"], "outer/inner entry mismatch")
        checked.append({"header_offset": entry["offset"], "filetype": 2,
                        **inner["split_range"]})
    return {"status": "CHECKED_SPLIT_RANGE_PASS", "headers": checked,
            "installer_acceptance": "NOT_TESTED"}


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
    expected_names = [b"__TEXT", b"__DATA_SPTM", b"__TEXT_EXEC",
                      b"__TEXT_BOOT_EXEC", b"__PRELINK_INFO", b"__LINKEDIT"]
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
    expected = [(0x4000, 0x8000, 0xC000, 3), (0x10000, 0x14000, 0x4000, 5),
                (0x14000, 0x18000, 0x10000, 5), (0x24000, 0x28000, 0x4000, 1),
                (0x28000, 0x2C000, 0x4000, 1)]
    for seg, (delta, off, size, prot) in zip(inner["segments"][1:], expected):
        need((seg["address"], seg["offset"], seg["size"], seg["protection"]) ==
             (base + delta, off, size, prot), "payload mapping mismatch")
    pc = inner["thread"][0]
    boot = inner["segments"][3]
    need(pc == base + 0x14000 and boot["address"] <= pc < boot["address"] + boot["size"] and
         boot["protection"] == 5, "entry outside intended boot execution range")
    need(not any(data[0x8000:0x14000]), "capture/stack region must remain zero")
    need(any(data[0x14000:0x18000]) and any(data[0x18000:0x28000]), "missing original code sentinels")
    info = inner["segments"][4]["section"]
    need(info is not None and info["name"] == b"__info", "missing prelink section")
    need(info["offset"] == 0x28000, "prelink section must start at metadata segment boundary")
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
    recovered = bytes(0x4000) + data[0x8000:0x28000]
    need(metadata["_PrelinkKCID"] == hashlib.sha256(recovered).digest()[:16],
         "recovered payload/metadata binding mismatch")
    if payload is not None:
        need(type(payload) is bytes and len(payload) == 0x24000 and
             not any(payload[:0x4000]) and not any(payload[0x4000:0x10000]) and
             any(payload[0x10000:0x14000]) and any(payload[0x14000:]),
             "invalid supplied original ordered payload")
        need(data[0x8000:0x28000] == payload[0x4000:], "payload bytes changed")
        need(metadata["_PrelinkKCID"] == hashlib.sha256(payload).digest()[:16], "payload/metadata binding mismatch")
    return {"status": "STRUCTURAL_PROFILE_PASS", "image_bytes": len(data),
            "image_sha256": hashlib.sha256(data).hexdigest(), "inner_base": hex(base),
            "entry": hex(pc), "vector": hex(base + 0x14800), "record": hex(base + 0x4000),
            "fileset_entries": 1, "payload_compared": payload is not None,
            "recovered_payload_sha256": hashlib.sha256(recovered).hexdigest(),
            "checked_split_ranges": [outer["split_range"], inner["split_range"]],
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
