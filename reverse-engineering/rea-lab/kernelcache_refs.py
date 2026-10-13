#!/usr/bin/env python3
"""Resolve selected on-disk kernel-collection references, without modifying them.

Supports only Apple's documented chained-pointer format 8, cache level 0.
Requires actual membership in the selected page's chain; a pointer-shaped
word alone is not evidence. This is file metadata analysis, not PAC signing,
target execution or runtime pointer authentication.
"""
import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "member_parser", Path(__file__).with_name("derive_member.py"))
_member = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_member)
checked, commands = _member.checked, _member.commands


def decode_word(word, base):
    if not 0 <= word < 1 << 64 or not 0 <= base < 1 << 64:
        raise ValueError("invalid word or base")
    level = (word >> 30) & 3
    if level:
        raise ValueError("other cache level needs a separately established base")
    target = base + (word & ((1 << 30) - 1))
    if target >= 1 << 64:
        raise ValueError("target overflows address space")
    return {"target": hex(target), "cache_level": level,
            "authenticated": bool(word >> 63),
            "diversity": (word >> 32) & 0xffff,
            "address_diversity": bool((word >> 48) & 1),
            "key": (word >> 49) & 3,
            "next_bytes": ((word >> 51) & 0xfff) * 4}


def walk_page(data, page_offset, page_bytes, start):
    if page_bytes not in (4096, 16384):
        raise ValueError("unsupported page size")
    checked(data, page_offset, page_bytes)
    if start == 0xffff:
        return {}
    if start & 0x8000:
        raise ValueError("multi-start pages are not implemented")
    if start % 4 or start + 8 > page_bytes:
        raise ValueError("invalid chain start")
    found = {}
    cursor = start
    while True:
        if cursor + 8 > page_bytes:
            raise ValueError("chain leaves its page")
        word = struct.unpack_from("<Q", data, page_offset + cursor)[0]
        found[cursor] = word
        step = ((word >> 51) & 0xfff) * 4
        if not step:
            return found
        if step < 8:
            raise ValueError("chain entries overlap")
        cursor += step


class Collection:
    def __init__(self, data):
        self.data = data
        header, cmds = commands(data)
        if header[3] != 12:
            raise ValueError("expected MH_FILESET")
        self.segments = []
        self.entries = {}
        fixes = []
        for cmd, record in cmds:
            if cmd == 0x19:
                if len(record) < 72:
                    raise ValueError("short segment")
                vm, size, offset, file_size = struct.unpack_from("<4Q", record, 24)
                checked(data, offset, file_size)
                if file_size > size or vm + size > 1 << 64:
                    raise ValueError("invalid segment range")
                self.segments.append((vm, size, offset, file_size))
            elif cmd == 0x80000034:
                if len(record) != 16:
                    raise ValueError("invalid chained-fixups command")
                fixes.append(struct.unpack_from("<II", record, 8))
            elif cmd == 0x80000035:
                if len(record) < 32:
                    raise ValueError("short fileset entry")
                at = struct.unpack_from("<I", record, 24)[0]
                name = _member.cstring(record, at, len(record)).decode()
                if name in self.entries:
                    raise ValueError("duplicate member")
                self.entries[name] = struct.unpack_from("<Q", record, 16)[0]
        if not self.segments or len(fixes) != 1:
            raise ValueError("missing/ambiguous segments or fixups")
        for i, a in enumerate(self.segments):
            for b in self.segments[i + 1:]:
                if max(a[0], b[0]) < min(a[0] + a[1], b[0] + b[1]):
                    raise ValueError("overlapping virtual segments")
        first = self.segments[0]
        if first[2] != 0 or first[3] < 32 + header[5]:
            raise ValueError("collection header has no established base")
        self.base = first[0]
        fixoff, fixsize = fixes[0]
        payload = checked(data, fixoff, fixsize)
        version, startoff, imports, symbols, count, _, symfmt = struct.unpack(
            "<7I", checked(payload, 0, 28))
        if version or count or symfmt:
            raise ValueError("unsupported fixup version, imports or symbols")
        if not 28 <= startoff < len(payload) or not 28 <= imports <= len(payload) or not 28 <= symbols <= len(payload):
            raise ValueError("invalid fixup offsets")
        starts = payload[startoff:]
        count = struct.unpack("<I", checked(starts, 0, 4))[0]
        if count != len(self.segments):
            raise ValueError("segment count mismatch")
        table_end = 4 + 4 * count
        checked(starts, 0, table_end)
        self.chains = {}
        record_ranges = []
        for i, segment in enumerate(self.segments):
            rel = struct.unpack_from("<I", starts, 4 + i * 4)[0]
            if not rel:
                continue
            if rel < table_end:
                raise ValueError("chain record overlaps offset table")
            size, page_size, fmt, segoff, maxptr, pages = struct.unpack(
                "<IHHQIH", checked(starts, rel, 22))
            record = checked(starts, rel, size)
            if size < 22 + pages * 2 or (size - 22) % 2:
                raise ValueError("invalid page-start array")
            if any(max(rel, a) < min(rel + size, b) for a, b in record_ranges):
                raise ValueError("overlapping chain records")
            record_ranges.append((rel, rel + size))
            if fmt != 8 or page_size not in (4096, 16384) or maxptr:
                raise ValueError("unsupported chain format")
            if segoff != segment[0] - self.base or pages * page_size > segment[3]:
                raise ValueError("chain pages disagree with segment")
            self.chains[i] = (page_size, record[22:22 + pages * 2])

    def resolve(self, address):
        matches = [(i, s) for i, s in enumerate(self.segments)
                   if s[0] <= address and address + 8 <= s[0] + s[3]]
        if len(matches) != 1 or matches[0][0] not in self.chains:
            raise ValueError("address not in a file-backed chained segment")
        index, segment = matches[0]
        size, starts = self.chains[index]
        page, inside = divmod(address - segment[0], size)
        if page >= len(starts) // 2:
            raise ValueError("address has no page-start metadata")
        start = struct.unpack_from("<H", starts, page * 2)[0]
        pageoff = segment[2] + page * size
        chain = walk_page(self.data, pageoff, size, start)
        if inside not in chain:
            raise ValueError("address is not a chained pointer")
        result = decode_word(chain[inside], self.base)
        target = int(result["target"], 16)
        if not any(s[0] <= target < s[0] + s[1] for s in self.segments):
            raise ValueError("target outside this collection")
        return dict(result, address=hex(address), carrier_offset=pageoff + inside,
                    pointer_format=8, page_size=size, page_chain_entries=len(chain),
                    chain_membership_verified=True)

    def symbols(self, name):
        # Kernel export metadata supplies identities for ordinary cross-member
        # helpers (e.g. allocation/copy); no kernel derivative is created.
        if name not in _member.ALLOWED | {"com.apple.kernel"} or name not in self.entries:
            raise ValueError("symbol member outside selected research scope")
        _, cmds = commands(self.data, self.entries[name])
        tables = [r for c, r in cmds if c == 2 and len(r) == 24]
        if len(tables) != 1:
            raise ValueError("ambiguous member symbols")
        at, count, strings, size = struct.unpack_from("<4I", tables[0], 8)
        if count > 100000:
            raise ValueError("symbol budget exceeded")
        records = checked(self.data, at, count * 16)
        names = checked(self.data, strings, size)
        result = {}
        for i in range(count):
            name_at, kind, _, _, value = struct.unpack_from("<IBBHQ", records, i * 16)
            if kind & 0xe0 or kind & 0x0e != 0x0e:
                continue
            name = _member.cstring(names, name_at, len(names)).decode()
            result.setdefault(value, []).append(name)
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("carrier", type=Path)
    p.add_argument("addresses", nargs="+", type=lambda x: int(x, 0))
    p.add_argument("--symbols-member", action="append", default=[])
    args = p.parse_args()
    data = args.carrier.read_bytes()
    collection = Collection(data)
    symbols = {}
    for member in args.symbols_member:
        for address, names in collection.symbols(member).items():
            symbols.setdefault(address, []).extend(names)
    refs = [collection.resolve(a) for a in args.addresses]
    for row in refs:
        row["exact_symbols"] = symbols.get(int(row["target"], 16), [])
    print(json.dumps({"carrier_sha256": hashlib.sha256(data).hexdigest(),
                      "references": refs,
                      "limits": ["Static reference; runtime object type not established",
                                 "No pointer authentication or target execution performed"]}, indent=2))


if __name__ == "__main__":
    main()
