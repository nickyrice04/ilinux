#!/usr/bin/env python3
"""Derive a selected ARM64 fileset member for static analysis, never execution.

Repack file offsets and member-owned symbols, preserving code/data VM addresses
and bytes. Cross-member pointers/calls and collection fixups remain unresolved.
Only the observed load-command profile is admitted; new formats fail closed.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

ALLOWED = {
    "com.apple.driver.AppleARMPlatform", "com.apple.driver.ApplePMGR",
    "com.apple.driver.AppleT6050PMGR", "com.apple.driver.AppleT6050CLPC",
    "com.apple.driver.AppleT6050SOCTuner", "com.apple.iokit.IONVMeFamily",
    # User-authorized driver-interface pass; ordinary host drivers only.
    "com.apple.AGXG17X", "com.apple.driver.AppleDCP",
    "com.apple.driver.AppleCentauriManager", "com.apple.iokit.IOBluetoothFamily",
    "com.apple.driver.AppleH16ANEInterface", "com.apple.driver.AppleH16CameraInterface",
    "com.apple.driver.AudioDMAController-T605x", "com.apple.driver.AOPAudio2",
    "com.apple.driver.AppleDockChannel", "com.apple.driver.AppleHIDTransportFIFO",
    "com.apple.driver.AppleHIDTransport", "com.apple.driver.RTBuddy",
    "com.apple.driver.AppleT8110DART",
    # Attempt 11: identified GPIO probe boundary; static ordinary driver analysis.
    "com.apple.driver.AppleGPIOICController",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(data, offset, size):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError("file range outside carrier")
    return data[offset:offset + size]


def commands(data, offset=0):
    header = struct.unpack("<8I", checked(data, offset, 32))
    if header[0] != 0xfeedfacf or header[1] != 0x100000c:
        raise ValueError("expected little-endian ARM64 Mach-O")
    if header[4] > 4096 or header[5] > 1024 * 1024:
        raise ValueError("load-command budget exceeded")
    end = offset + 32 + header[5]
    checked(data, offset, end - offset)
    cursor = offset + 32
    result = []
    for _ in range(header[4]):
        cmd, size = struct.unpack("<II", checked(data, cursor, 8))
        if size < 8 or size % 8 or cursor + size > end:
            raise ValueError("invalid load command")
        result.append((cmd, bytearray(checked(data, cursor, size))))
        cursor += size
    if cursor != end:
        raise ValueError("load-command size mismatch")
    return header, result


def cstring(data, offset, limit):
    if not 0 <= offset < limit <= len(data):
        raise ValueError("string outside table")
    end = data.find(b"\0", offset, limit)
    if end < 0:
        raise ValueError("unterminated string")
    return data[offset:end]


def derive(data, member):
    if member not in ALLOWED:
        raise ValueError("member outside research scope")
    header, outer = commands(data)
    if header[3] != 12:
        raise ValueError("expected MH_FILESET")
    matches = []
    for cmd, record in outer:
        if cmd == 0x80000035:
            if len(record) < 32:
                raise ValueError("short fileset entry")
            name_at = struct.unpack_from("<I", record, 24)[0]
            if cstring(record, name_at, len(record)).decode() == member:
                matches.append(struct.unpack_from("<Q", record, 16)[0])
    if len(matches) != 1:
        raise ValueError("expected one selected member")
    member_offset = matches[0]
    header, cmds = commands(data, member_offset)
    if header[3] != 11:
        raise ValueError("expected MH_KEXT_BUNDLE")
    output = bytearray()
    mappings = []
    linkedit = None
    symtab = None
    for cmd, record in cmds:
        if cmd == 0x19:
            if len(record) < 72:
                raise ValueError("short segment")
            name = record[8:24].split(b"\0")[0].decode()
            vm, vmsize, oldoff, size = struct.unpack_from("<4Q", record, 24)
            count = struct.unpack_from("<I", record, 64)[0]
            if len(record) != 72 + count * 80:
                raise ValueError("invalid section count")
            checked(data, oldoff, size)
            if size > vmsize:
                raise ValueError("file segment exceeds virtual segment")
            if name == "__LINKEDIT":
                if linkedit is not None or count:
                    raise ValueError("unexpected linkedit")
                linkedit = record
                continue
            newoff = (len(output) + 4095) & ~4095
            output.extend(b"\0" * (newoff - len(output)))
            source = checked(data, oldoff, size)
            output.extend(source)
            struct.pack_into("<Q", record, 40, newoff)
            for i in range(count):
                section = 72 + i * 80
                addr, length, oldsection = struct.unpack_from("<QQI", record, section + 32)
                flags = struct.unpack_from("<I", record, section + 64)[0]
                reloff, nreloc = struct.unpack_from("<II", record, section + 56)
                if nreloc or reloff:
                    raise ValueError("section relocations unsupported")
                if addr < vm or addr + length > vm + vmsize:
                    raise ValueError("section outside virtual segment")
                if flags & 0xff not in (1, 12, 18) and length:
                    if oldsection < oldoff or oldsection + length > oldoff + size:
                        raise ValueError("section outside file segment")
                    if addr - vm != oldsection - oldoff:
                        raise ValueError("section file and VM mapping disagree")
                    struct.pack_into("<I", record, section + 48, newoff + oldsection - oldoff)
            mappings.append({"segment": name, "vmaddr": hex(vm), "source_offset": oldoff,
                             "derived_offset": newoff, "bytes": size, "source_sha256": digest(source)})
        elif cmd == 2:
            if symtab is not None or len(record) != 24:
                raise ValueError("unexpected symbol table")
            symtab = record
        elif cmd not in (0xb, 0x1b, 0x2a, 0x26):
            raise ValueError(f"unsupported member load command {cmd:#x}")
        elif len(record) != {0xb: 80, 0x1b: 24, 0x2a: 16, 0x26: 16}[cmd]:
            raise ValueError("unexpected metadata command size")
    if not mappings or mappings[0]["source_offset"] != member_offset or mappings[0]["derived_offset"] != 0:
        raise ValueError("first segment must contain member header")
    if linkedit is None or symtab is None:
        raise ValueError("missing analysis metadata")
    linkstart, linksize = struct.unpack_from("<QQ", linkedit, 40)

    def metadata(offset, size):
        if offset < linkstart or offset + size > linkstart + linksize:
            raise ValueError("metadata outside member linkedit")
        return checked(data, offset, size)
    begin = (len(output) + 4095) & ~4095
    output.extend(b"\0" * (begin - len(output)))

    def append(blob):
        output.extend(b"\0" * (-len(output) % 8))
        at = len(output)
        output.extend(blob)
        return at

    oldsym, count, oldstr, strsize = struct.unpack_from("<4I", symtab, 8)
    if count > 100000:
        raise ValueError("symbol budget exceeded")
    symbols = bytearray(metadata(oldsym, count * 16))
    oldstrings = metadata(oldstr, strsize)
    strings = bytearray(b"\0")
    interned = {b"": 0}
    for i in range(count):
        if symbols[i * 16 + 4] & 0x0e == 0x0a:
            raise ValueError("N_INDR string-index rewriting unsupported")
        index = struct.unpack_from("<I", symbols, i * 16)[0]
        name = cstring(oldstrings, index, len(oldstrings))
        if name not in interned:
            interned[name] = len(strings)
            strings.extend(name + b"\0")
        struct.pack_into("<I", symbols, i * 16, interned[name])
    struct.pack_into("<4I", symtab, 8, append(symbols), count, append(strings), len(strings))
    for cmd, record in cmds:
        if cmd == 0x26:
            oldoff, size = struct.unpack_from("<II", record, 8)
            struct.pack_into("<I", record, 8, append(metadata(oldoff, size)))
        elif cmd == 0xb:
            if len(record) != 80:
                raise ValueError("unexpected dynamic symbol table")
            for field, itemsize in ((32, 8), (40, 56), (48, 4), (56, 4), (64, 8), (72, 8)):
                oldoff, count = struct.unpack_from("<II", record, field)
                if field == 40 and count:
                    raise ValueError("module tables need string-index rewriting; unsupported")
                newoff = append(metadata(oldoff, count * itemsize)) if count else 0
                struct.pack_into("<I", record, field, newoff)
    length = len(output) - begin
    struct.pack_into("<QQQ", linkedit, 32, (length + 4095) & ~4095, begin, length)
    rewritten = struct.pack("<8I", *header) + b"".join(record for _, record in cmds)
    if len(rewritten) > mappings[0]["bytes"]:
        raise ValueError("header exceeds first segment")
    output[:len(rewritten)] = rewritten
    # All original bytes outside the header must remain identical in each segment.
    for mapping in mappings:
        skip = len(rewritten) if mapping["derived_offset"] == 0 else 0
        old = checked(data, mapping["source_offset"] + skip, mapping["bytes"] - skip)
        new = checked(output, mapping["derived_offset"] + skip, mapping["bytes"] - skip)
        if old != new:
            raise ValueError("retained bytes changed")
        mapping["verified_payload_sha256"] = digest(new)
    manifest = {"source_sha256": digest(data), "member": member,
                "member_header_offset": member_offset, "derived_sha256": digest(output),
                "derived_bytes": len(output), "mappings": mappings,
                "limits": ["Static analysis derivative; not loadable or executable",
                           "Collection fixups not applied; external calls/pointers may be unresolved",
                           "Only original member symbol names retained; metadata offsets rewritten"]}
    return output, manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("carrier", type=Path)
    p.add_argument("member", choices=sorted(ALLOWED))
    p.add_argument("output", type=Path)
    args = p.parse_args()
    sidecar = args.output.with_suffix(args.output.suffix + ".json")
    if args.output.exists() or sidecar.exists():
        p.error("output or provenance sidecar already exists")
    result, manifest = derive(args.carrier.read_bytes(), args.member)
    with args.output.open("xb") as out:
        out.write(result)
    with sidecar.open("x") as out:
        out.write(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "mappings"}, indent=2))


if __name__ == "__main__":
    main()
