"""Synthetic Mach-O boundary tests; never read a proprietary carrier.

Run: python3 -I reverse-engineering/rea-lab/test_member.py
Known parser defects intentionally fail these regression tests until fixed.
"""
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location(
    "derive_member_under_test", Path(__file__).with_name("derive_member.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def derive(data, member):
    """Match the production read_bytes input, while fixtures remain mutable."""
    return module.derive(bytes(data), member)

MEMBER = "com.apple.driver.AppleT6050PMGR"
TEXT = 0x2000
DATA = 0x5000
LINKEDIT = 0x6000
TEXT_VM = 0x100000
DATA_VM = 0x200000
LINKEDIT_VM = 0x300000
SYMBOLS = LINKEDIT
STRINGS = LINKEDIT + 0x100
STARTS = LINKEDIT + 0x240
INDIRECT = LINKEDIT + 0x280
MODULES = LINKEDIT + 0x300
UNRELATED = b"UNRELATED_CARRIER_BYTES_MUST_NOT_ESCAPE"
UNUSED_NAME = b"UNREFERENCED_STRING_MUST_NOT_ESCAPE"


def header(filetype, records, cpu=0x100000c):
    return struct.pack("<8I", 0xfeedfacf, cpu, 0xc0000002, filetype,
                       len(records), sum(map(len, records)), 0, 0)


def section(name, segment, address, length, offset, flags=0):
    return struct.pack("<16s16sQQ8I", name.encode(), segment.encode(),
                       address, length, offset, 2, 0, 0, flags, 0, 0, 0)


def segment(name, vm, vmsize, offset, size, sections=()):
    return bytearray(struct.pack("<II16s4Q4I", 0x19, 72 + 80 * len(sections),
                                 name.encode(), vm, vmsize, offset, size,
                                 7, 5, len(sections), 0) + b"".join(sections))


def entry(name=MEMBER, offset=TEXT):
    name = name.encode() + b"\0"
    size = (32 + len(name) + 7) & ~7
    return bytearray(struct.pack("<IIQQII", 0x80000035, size, TEXT_VM,
                                 offset, 32, 0) + name.ljust(size - 32, b"\0"))


class Fixture:
    """Two retained segments, one bss section, and shared-carrier noise."""

    def __init__(self):
        self.strings = b"\0" + UNUSED_NAME + b"\0_owned_func\0_owned_data\0"
        self.symbols = b"".join(
            struct.pack("<IBBHQ", self.strings.index(name), 0xf, sect, 0, address)
            for name, sect, address in [(b"_owned_func", 1, TEXT_VM + 0x400),
                                        (b"_owned_data", 2, DATA_VM)])
        self.starts = b"\x80\x08\x00"  # ULEB128 0x400, then end marker.
        self.records = [
            segment("__TEXT", TEXT_VM, 0x1000, TEXT, 0x1000,
                    [section("__text", "__TEXT", TEXT_VM + 0x400, 0x60, TEXT + 0x400)]),
            segment("__DATA", DATA_VM, 0x1000, DATA, 0x300,
                    [section("__data", "__DATA", DATA_VM, 0x80, DATA),
                     section("__bss", "__DATA", DATA_VM + 0x400, 0x100, 0, 1)]),
            segment("__LINKEDIT", LINKEDIT_VM, 0x1000, LINKEDIT, 0x400),
            bytearray(struct.pack("<6I", 2, 24, SYMBOLS, 2, STRINGS, len(self.strings))),
            bytearray(struct.pack("<20I", 0xb, 80, 0, 0, 0, 2, 2, 0,
                                  0, 0, 0, 0, 0, 0, INDIRECT, 2, 0, 0, 0, 0)),
            bytearray(struct.pack("<4I", 0x26, 16, STARTS, len(self.starts))),
            bytearray(struct.pack("<II", 0x1b, 24) + bytes(range(16))),
            bytearray(struct.pack("<IIQ", 0x2a, 16, 1)),
        ]
        self.outer = [entry()]

    def carrier(self):
        data = bytearray(0x6800)
        data[TEXT:TEXT + 0x1000] = bytes(i % 251 for i in range(0x1000))
        data[DATA:DATA + 0x300] = bytes((i * 7) % 253 for i in range(0x300))
        data[0x4500:0x4500 + len(UNRELATED)] = UNRELATED
        data[SYMBOLS:SYMBOLS + len(self.symbols)] = self.symbols
        data[STRINGS:STRINGS + len(self.strings)] = self.strings
        data[STARTS:STARTS + len(self.starts)] = self.starts
        data[INDIRECT:INDIRECT + 8] = struct.pack("<2I", 0, 1)
        # Synthetic dylib_module_64: module_name indexes the old, unused string.
        data[MODULES:MODULES + 56] = struct.pack("<12IQ", 1, *([0] * 12))
        outer = header(12, self.outer) + b"".join(self.outer)
        inner = header(11, self.records) + b"".join(self.records)
        data[:len(outer)] = outer
        data[TEXT:TEXT + len(inner)] = inner
        return data


def output_commands(data):
    """Small independent reader for assertions on generated metadata."""
    ncmd = struct.unpack_from("<I", data, 16)[0]
    cursor = 32
    found = {}
    for _ in range(ncmd):
        command, size = struct.unpack_from("<II", data, cursor)
        found.setdefault(command, []).append(data[cursor:cursor + size])
        cursor += size
    return found


class MemberBoundaries(unittest.TestCase):
    def test_payload_bytes_addresses_and_section_offsets_survive(self):
        fixture = Fixture()
        source = fixture.carrier()
        original = bytes(source)
        result, manifest = derive(source, MEMBER)
        self.assertEqual(source, original, "parser modified the source buffer")
        cmds = output_commands(result)
        rewritten_size = 32 + sum(map(len, fixture.records))
        # Verify against independently known source ranges, not only the manifest.
        self.assertEqual(result[rewritten_size:0x1000], source[TEXT + rewritten_size:TEXT + 0x1000])
        self.assertEqual(result[0x1000:0x1300], source[DATA:DATA + 0x300])
        text, data, linkedit = cmds[0x19]
        self.assertEqual(struct.unpack_from("<4Q", text, 24), (TEXT_VM, 0x1000, 0, 0x1000))
        self.assertEqual(struct.unpack_from("<4Q", data, 24), (DATA_VM, 0x1000, 0x1000, 0x300))
        self.assertEqual(struct.unpack_from("<I", text, 72 + 48)[0], 0x400)
        self.assertEqual(struct.unpack_from("<I", data, 72 + 48)[0], 0x1000)
        self.assertEqual(struct.unpack_from("<I", data, 72 + 80 + 48)[0], 0)
        self.assertEqual(struct.unpack_from("<Q", linkedit, 24)[0], LINKEDIT_VM)
        for mapping in manifest["mappings"]:
            skip = rewritten_size if mapping["derived_offset"] == 0 else 0
            start = mapping["derived_offset"] + skip
            payload = result[start:mapping["derived_offset"] + mapping["bytes"]]
            self.assertEqual(mapping["verified_payload_sha256"], hashlib.sha256(payload).hexdigest())

    def test_only_referenced_symbols_and_known_linkedit_blobs_survive(self):
        fixture = Fixture()
        result, _ = derive(fixture.carrier(), MEMBER)
        self.assertNotIn(UNRELATED, result)
        self.assertNotIn(UNUSED_NAME, result)
        cmds = output_commands(result)
        symoff, count, stroff, strsize = struct.unpack_from("<4I", cmds[2][0], 8)
        self.assertEqual(count, 2)
        strings = result[stroff:stroff + strsize]
        for index, name in enumerate((b"_owned_func", b"_owned_data")):
            si = struct.unpack_from("<I", result, symoff + index * 16)[0]
            self.assertEqual(strings[si:].split(b"\0", 1)[0], name)
            self.assertEqual(result[symoff + index * 16 + 4:symoff + (index + 1) * 16],
                             fixture.symbols[index * 16 + 4:(index + 1) * 16])
        funcoff, funcsize = struct.unpack_from("<II", cmds[0x26][0], 8)
        self.assertEqual(result[funcoff:funcoff + funcsize], fixture.starts)
        indirect, count = struct.unpack_from("<II", cmds[0xb][0], 56)
        self.assertEqual(result[indirect:indirect + count * 4], struct.pack("<2I", 0, 1))

    def test_reject_unknown_member_and_missing_or_duplicate_identity(self):
        fixture = Fixture()
        with self.assertRaises(ValueError):
            derive(fixture.carrier(), "com.example.unrelated")
        for entries in ([], [entry(), entry()]):
            with self.subTest(entries=len(entries)), self.assertRaises(ValueError):
                fixture.outer = entries
                derive(fixture.carrier(), MEMBER)

    def test_reject_wrong_architecture_type_and_truncated_referenced_ranges(self):
        source = Fixture().carrier()
        for offset, value in ((4, 0x1000007), (12, 2), (TEXT + 4, 0x1000007), (TEXT + 12, 2)):
            bad = bytearray(source)
            struct.pack_into("<I", bad, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                derive(bad, MEMBER)
        for end in (0, 31, 70, TEXT + 31, TEXT + 0x1000 - 1,
                    DATA + 0x300 - 1, SYMBOLS + 31, STRINGS + 10, STARTS + 2, INDIRECT + 7):
            with self.subTest(end=end), self.assertRaises(ValueError):
                derive(source[:end], MEMBER)

    def test_reject_unsupported_command_and_section_relocations(self):
        fixture = Fixture()
        fixture.records.append(bytearray(struct.pack("<4I", 0x80000034, 16, 0, 0)))
        with self.assertRaises(ValueError):
            derive(fixture.carrier(), MEMBER)
        for field in (72 + 56, 72 + 60):
            fixture = Fixture()
            struct.pack_into("<I", fixture.records[0], field, 1)
            with self.subTest(field=field), self.assertRaises(ValueError):
                derive(fixture.carrier(), MEMBER)

    def test_reject_bad_segment_and_section_ranges(self):
        for record, field, format_, value in (
                (0, 40, "Q", 0x9000), (0, 48, "Q", 0x2000),
                (0, 72 + 32, "Q", TEXT_VM + 0x2000),
                (0, 72 + 48, "I", TEXT - 1), (0, 64, "I", 40)):
            fixture = Fixture()
            struct.pack_into("<" + format_, fixture.records[record], field, value)
            with self.subTest(record=record, field=field), self.assertRaises(ValueError):
                derive(fixture.carrier(), MEMBER)

    def test_reject_bad_symbol_strings(self):
        fixture = Fixture()
        source = fixture.carrier()
        struct.pack_into("<I", source, SYMBOLS, len(fixture.strings))
        with self.assertRaises(ValueError):
            derive(source, MEMBER)
        source = fixture.carrier()
        source[STRINGS + len(fixture.strings) - 1] = 65
        with self.assertRaises(ValueError):
            derive(source, MEMBER)

    def test_reject_invalid_original_linkedit_ranges(self):
        for field, value in ((40, 0x9000), (48, 0x2000), (32, 0)):
            fixture = Fixture()
            struct.pack_into("<Q", fixture.records[2], field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                derive(fixture.carrier(), MEMBER)

    def test_reject_metadata_which_points_outside_member_linkedit(self):
        for kind in ("symbols", "strings", "function_starts", "indirect"):
            fixture = Fixture()
            field = {"symbols": (3, 8), "strings": (3, 16),
                     "function_starts": (5, 8), "indirect": (4, 56)}[kind]
            struct.pack_into("<I", fixture.records[field[0]], field[1], 0x4500)
            source = fixture.carrier()
            blob = {"symbols": fixture.symbols, "strings": fixture.strings,
                    "function_starts": fixture.starts, "indirect": struct.pack("<2I", 0, 1)}[kind]
            source[0x4500:0x4500 + len(blob)] = blob
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                derive(source, MEMBER)

    def test_reject_nonempty_module_table_with_unrewritten_string_indexes(self):
        fixture = Fixture()
        struct.pack_into("<II", fixture.records[4], 40, MODULES, 1)
        with self.assertRaises(ValueError):
            derive(fixture.carrier(), MEMBER)

    def test_reject_noncanonical_fixed_command_sizes(self):
        for index in (5, 6, 7):  # function starts, UUID, source version
            fixture = Fixture()
            fixture.records[index].extend(b"\0" * 8)
            struct.pack_into("<I", fixture.records[index], 4, len(fixture.records[index]))
            with self.subTest(command=index), self.assertRaises(ValueError):
                derive(fixture.carrier(), MEMBER)

    def test_reject_section_file_virtual_disagreement(self):
        fixture = Fixture()
        struct.pack_into("<Q", fixture.records[0], 72 + 32, TEXT_VM + 0x410)
        with self.assertRaises(ValueError):
            derive(fixture.carrier(), MEMBER)

    def test_reject_indirect_alias_with_unrewritten_target_string_index(self):
        fixture = Fixture()
        source = fixture.carrier()
        # N_INDR | N_EXT: n_value is another string-table index, not a VM address.
        source[SYMBOLS + 4] = 0x0b
        source[SYMBOLS + 5] = 0
        struct.pack_into("<Q", source, SYMBOLS + 8, fixture.strings.index(b"_owned_data"))
        with self.assertRaises(ValueError):
            derive(source, MEMBER)


if __name__ == "__main__":
    unittest.main()
