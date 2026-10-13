#!/usr/bin/env python3
"""Build a synthetic, non-loadable AArch64 ELF for three Airship functions.

Original bounded parser, based on Apple's public dyld-cache field layouts.
Only selected function instructions are copied. This never executes a target.
ELF contains no entry point or program headers, and is not a recovered library.
"""

import argparse
import hashlib
import json
import pathlib
import struct

CACHE = pathlib.Path("/System/Volumes/Preboot/Cryptexes/OS/System/DriverKit/System/Library/dyld/dyld_shared_cache_arm64e")
SOURCE_SHA256 = "c0cb9e3f489efe860ec67122bd51b93c816eac5ff4f48884375f0c908fea536d"
IMAGE = "/System/DriverKit/System/Library/PrivateFrameworks/AirshipDK.framework/AirshipDK"
IMAGE_VM = 0x180226000
TARGETS = (
    ("__ZN4ashp15ring_index_pairItEC2Et", 0x18023000c, 136),
    ("__ZN4ashp15ring_index_pairItE18advance_head_indexEt", 0x180237ef8, 196),
    ("__ZN4ashp15ring_index_pairItE18advance_tail_indexEt", 0x180237fbc, 192),
)
MAX_CACHE = 64 * 1024 * 1024


class Reader:
    def __init__(self, file):
        self.file = file
        self.size = file.seek(0, 2)
        if self.size < 512 or self.size > MAX_CACHE:
            raise ValueError("unsupported cache size")

    def read(self, offset, size):
        if offset < 0 or size < 0 or size > self.size - offset or size > 4 * 1024 * 1024:
            raise ValueError("read outside permitted cache range")
        self.file.seek(offset)
        data = self.file.read(size)
        if len(data) != size:
            raise ValueError("truncated cache")
        return data

    def cstring(self, offset, limit=512):
        raw = self.read(offset, min(limit, self.size - offset))
        end = raw.find(b"\0")
        if end < 0:
            raise ValueError("unterminated cache string")
        return raw[:end].decode("ascii")


def function_starts(data, base):
    starts = []
    offset = 0
    while offset < len(data):
        delta = 0
        shift = 0
        while True:
            if offset == len(data) or shift >= 64:
                raise ValueError("truncated/overflowing function-start integer")
            byte = data[offset]
            offset += 1
            delta |= (byte & 127) << shift
            shift += 7
            if not byte & 128:
                break
        if delta == 0:
            if any(data[offset:]):
                raise ValueError("nonzero padding after function-start terminator")
            return starts
        base += delta
        if base >= 1 << 64:
            raise ValueError("function-start address overflow")
        starts.append(base)
    raise ValueError("missing function-start terminator")


def extract_ranges(file, expected_sha256=SOURCE_SHA256):
    reader = Reader(file)
    digest = hashlib.sha256()
    file.seek(0)
    while True:
        chunk = file.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    if digest.hexdigest() != expected_sha256:
        raise ValueError("source cache SHA-256 mismatch")
    header = reader.read(0, 512)
    if not header[:16].startswith(b"dyld_v1") or b"arm64e" not in header[:16]:
        raise ValueError("not the supported ARM64e cache")
    mapping_offset, mapping_count = struct.unpack_from("<II", header, 16)
    image_offset, image_count = struct.unpack_from("<II", header, 448)
    if not 0 < mapping_count <= 64 or not 0 < image_count <= 4096 or mapping_offset < 512:
        raise ValueError("invalid cache tables")
    maps = [struct.unpack("<QQQII", reader.read(mapping_offset + 32 * i, 32))
            for i in range(mapping_count)]

    def file_offset(address, size):
        offsets = [offset + address - start for start, length, offset, _, _ in maps
                   if start <= address and size <= length - (address - start)]
        if len(offsets) != 1:
            raise ValueError("unmapped or ambiguous virtual range")
        return offsets[0]

    images = []
    for i in range(image_count):
        entry = reader.read(image_offset + i * 32, 32)
        address = struct.unpack_from("<Q", entry)[0]
        path_offset = struct.unpack_from("<I", entry, 24)[0]
        if reader.cstring(path_offset) == IMAGE:
            images.append(address)
    if images != [IMAGE_VM]:
        raise ValueError("missing, duplicated or moved Airship image")
    image_file = file_offset(IMAGE_VM, 32)
    mh = struct.unpack("<8I", reader.read(image_file, 32))
    if mh[0] != 0xfeedfacf or mh[1] != 0x100000c or mh[2] & 0xffffff != 2 or mh[3] != 6:
        raise ValueError("unexpected cached Mach-O architecture/type")
    if not 0 < mh[4] <= 128 or mh[5] > 32768:
        raise ValueError("invalid Mach-O commands")
    commands = reader.read(image_file + 32, mh[5])
    offset = 0
    text_sections = []
    starts = None
    for _ in range(mh[4]):
        if offset + 8 > len(commands):
            raise ValueError("truncated Mach-O command")
        cmd, size = struct.unpack_from("<II", commands, offset)
        if size < 8 or size > len(commands) - offset:
            raise ValueError("invalid Mach-O command size")
        if cmd == 0x19:
            if size < 72:
                raise ValueError("short segment command")
            count = struct.unpack_from("<I", commands, offset + 64)[0]
            if count > (size - 72) // 80:
                raise ValueError("section array outside command")
            for i in range(count):
                section = commands[offset + 72 + i * 80:offset + 152 + i * 80]
                if section[:16].split(b"\0")[0] == b"__text":
                    text_sections.append(struct.unpack_from("<QQI", section, 32))
        if cmd == 0x26:
            if size != 16 or starts is not None:
                raise ValueError("invalid/duplicate function-start table")
            start_offset, start_size = struct.unpack_from("<II", commands, offset + 8)
            starts = function_starts(reader.read(start_offset, start_size), IMAGE_VM)
        offset += size
    if offset != len(commands) or len(text_sections) != 1 or starts is None:
        raise ValueError("incomplete image layout")
    text_address, text_size, text_offset = text_sections[0]
    if file_offset(text_address, text_size) != text_offset:
        raise ValueError("text section/cache mapping mismatch")
    result = []
    for name, address, length in TARGETS:
        if address not in starts:
            raise ValueError("selected function lacks a start record")
        index = starts.index(address)
        if index + 1 == len(starts) or starts[index + 1] - address != length:
            raise ValueError("selected function interval changed")
        if address < text_address or length > text_size - (address - text_address):
            raise ValueError("selected function outside text")
        source_offset = file_offset(address, length)
        data = reader.read(source_offset, length)
        result.append({"symbol": name, "address": address, "source_offset": source_offset,
                       "data": data, "sha256": hashlib.sha256(data).hexdigest()})
    return result


def make_elf(functions):
    """No PT_LOAD segments or e_entry: a static-analysis container only."""
    if len(functions) != len(TARGETS):
        raise ValueError("analysis carrier must contain exactly three selected functions")
    blob = bytearray(64)
    sections = [(0,) * 10]
    section_names = bytearray(b"\0")
    symbols = bytearray(24)  # ELF STN_UNDEF
    symbol_names = bytearray(b"\0")

    def add_section(name, kind, flags, address, data, alignment, link=0, info=0, entry_size=0):
        name_offset = len(section_names)
        section_names.extend(name.encode("ascii") + b"\0")
        blob.extend(b"\0" * (-len(blob) % alignment))
        offset = len(blob)
        blob.extend(data)
        sections.append((name_offset, kind, flags, address, offset, len(data),
                         link, info, alignment, entry_size))

    for index, (function, expected) in enumerate(zip(functions, TARGETS), 1):
        name, address, length = expected
        if function["symbol"] != name or function["address"] != address or len(function["data"]) != length:
            raise ValueError("unexpected function in analysis carrier")
        add_section(f".text.target{index}", 1, 6, address, function["data"], 4)
        name_offset = len(symbol_names)
        symbol_names.extend(name.encode("ascii") + b"\0")
        symbols.extend(struct.pack("<IBBHQQ", name_offset, 0x12, 0, index, address, length))
    add_section(".symtab", 2, 0, 0, symbols, 8, link=5, info=1, entry_size=24)
    add_section(".strtab", 3, 0, 0, symbol_names, 1)
    # The section-name table includes its own name.
    shstr_name_offset = len(section_names)
    section_names.extend(b".shstrtab\0")
    shstr_offset = len(blob)
    blob.extend(section_names)
    sections.append((shstr_name_offset, 3, 0, 0, shstr_offset, len(section_names), 0, 0, 1, 0))
    blob.extend(b"\0" * (-len(blob) % 8))
    shoff = len(blob)
    for section in sections:
        blob.extend(struct.pack("<IIQQQQIIQQ", *section))
    header = struct.pack("<16sHHIQQQIHHHHHH", b"\x7fELF\x02\x01\x01" + bytes(9),
                         2, 183, 1, 0, 0, shoff, 0, 64, 0, 0, 64, len(sections), 6)
    blob[:64] = header
    return bytes(blob)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=pathlib.Path, default=CACHE)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    manifest_path = args.output.with_suffix(args.output.suffix + ".json")
    if args.output.exists() or manifest_path.exists():
        parser.error("output already exists")
    with args.cache.open("rb") as file:
        functions = extract_ranges(file)
    data = make_elf(functions)
    manifest = {
        "format_version": 1, "kind": "synthetic_nonloadable_static_analysis_carrier",
        "source_sha256": SOURCE_SHA256,
        "derived_sha256": hashlib.sha256(data).hexdigest(),
        "member": "AirshipDK:selected-ring-functions",
        "source": {"path": str(args.cache), "sha256": SOURCE_SHA256, "image": IMAGE},
        "output": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                   "elf_machine": "AArch64", "program_headers": 0, "entry_point": 0},
        "limitations": ["Not an original Mach-O, recovered library or runnable executable",
                        "External branch targets are absent; cross-function analysis is incomplete",
                        "No data, shared strings, relocations or authenticated pointer fixups copied",
                        "No target function has been executed; names/bounds do not establish semantics"],
        "functions": [{"symbol": f["symbol"], "address": hex(f["address"]),
                       "source_offset": f["source_offset"], "bytes": len(f["data"]),
                       "sha256": f["sha256"], "bounds": "LC_FUNCTION_STARTS"} for f in functions],
    }
    shoff = struct.unpack_from("<Q", data, 40)[0]
    manifest["mappings"] = []
    for index, function in enumerate(functions, 1):
        section = struct.unpack_from("<IIQQQQIIQQ", data, shoff + index * 64)
        if section[3] != function["address"] or data[section[4]:section[4] + section[5]] != function["data"]:
            raise ValueError("generated ELF/source mapping mismatch")
        manifest["mappings"].append({"vmaddr": hex(section[3]),
                                     "source_offset": function["source_offset"],
                                     "derived_offset": section[4], "bytes": section[5]})
    with args.output.open("xb") as file:
        file.write(data)
    with manifest_path.open("x") as file:
        json.dump(manifest, file, indent=2, sort_keys=True)
        file.write("\n")
    print(f"Created analysis-only carrier: {len(data)} bytes, 524 target bytes; no target execution")


if __name__ == "__main__":
    main()
