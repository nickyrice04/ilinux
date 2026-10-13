"""Synthetic fixtures only: malformed metadata must not become an asserted reference."""
import importlib.util
import struct
import unittest
from pathlib import Path

_s = importlib.util.spec_from_file_location("refs", Path(__file__).with_name("kernelcache_refs.py"))
refs = importlib.util.module_from_spec(_s)
_s.loader.exec_module(refs)
BASE = 0xfffffe0007004000


def fixture():
    segments = []
    for i, name in enumerate((b"__TEXT", b"__DATA_CONST")):
        segments.append(struct.pack("<II16sQQQQiiII", 0x19, 72, name,
                                   BASE + i * 4096, 4096, i * 4096, 4096, 3, 3, 0, 0))
    start = struct.pack("<III", 2, 0, 12)
    start += struct.pack("<IHHQIH H", 24, 4096, 8, 4096, 0, 1, 0x20)
    payload = struct.pack("<7I", 0, 28, 28 + len(start), 28 + len(start), 0, 1, 0) + start
    commands = b"".join(segments) + struct.pack("<IIII", 0x80000034, 16, 8192, len(payload))
    data = bytearray(struct.pack("<8I", 0xfeedfacf, 0x100000c, 2, 12, 3, len(commands), 0, 0) + commands)
    data.extend(bytes(8192 - len(data)))
    data.extend(payload)
    struct.pack_into("<Q", data, 0x1020, (1 << 63) | (2 << 51) | (0x70b5 << 32) | 0x80)
    struct.pack_into("<Q", data, 0x1028, 0x90)
    return data


class ReferenceTests(unittest.TestCase):
    def test_authenticated_reference(self):
        r = refs.Collection(fixture()).resolve(BASE + 0x1020)
        self.assertEqual(r["target"], hex(BASE + 0x80))
        self.assertEqual(r["diversity"], 0x70b5)
        self.assertTrue(r["authenticated"])
        self.assertEqual(r["page_chain_entries"], 2)

    def test_plain_reference(self):
        r = refs.Collection(fixture()).resolve(BASE + 0x1028)
        self.assertEqual(r["target"], hex(BASE + 0x90))
        self.assertFalse(r["authenticated"])

    def test_pointer_shaped_nonmember_rejected(self):
        data = fixture()
        struct.pack_into("<Q", data, 0x1080, 0x90)
        with self.assertRaisesRegex(ValueError, "not a chained"):
            refs.Collection(data).resolve(BASE + 0x1080)

    def test_unknown_cache_base(self):
        for level in (1, 2, 3):
            with self.subTest(level=level), self.assertRaisesRegex(ValueError, "cache level"):
                refs.decode_word(level << 30, BASE)

    def test_address_overflow(self):
        with self.assertRaisesRegex(ValueError, "overflows"):
            refs.decode_word(32, (1 << 64) - 16)

    def test_outside_target(self):
        data = fixture()
        struct.pack_into("<Q", data, 0x1028, 0x3000)
        with self.assertRaisesRegex(ValueError, "target outside"):
            refs.Collection(data).resolve(BASE + 0x1028)

    def test_chain_crossing_page(self):
        data = fixture()
        struct.pack_into("<Q", data, 0x1028, 0x800 << 51)
        with self.assertRaisesRegex(ValueError, "leaves its page"):
            refs.Collection(data).resolve(BASE + 0x1020)

    def test_overlapping_chain_words(self):
        data = fixture()
        struct.pack_into("<Q", data, 0x1028, 1 << 51)
        with self.assertRaisesRegex(ValueError, "entries overlap"):
            refs.Collection(data).resolve(BASE + 0x1020)

    def test_unsupported_format(self):
        data = fixture()
        struct.pack_into("<H", data, 8192 + 28 + 12 + 6, 7)
        with self.assertRaisesRegex(ValueError, "unsupported chain"):
            refs.Collection(data)

    def test_unknown_version_and_imports(self):
        for off in (0, 16, 24):
            data = fixture()
            struct.pack_into("<I", data, 8192 + off, 1)
            with self.subTest(off=off), self.assertRaises(ValueError):
                refs.Collection(data)

    def test_truncated_header_and_metadata(self):
        data = fixture()
        for end in (0, 31, 150, 8192, len(data) - 1):
            with self.subTest(end=end), self.assertRaises(ValueError):
                refs.Collection(data[:end])

    def test_segment_mismatch(self):
        data = fixture()
        struct.pack_into("<Q", data, 8192 + 28 + 12 + 8, 0x2000)
        with self.assertRaisesRegex(ValueError, "disagree"):
            refs.Collection(data)

    def test_overlapping_segments(self):
        data = fixture()
        struct.pack_into("<Q", data, 32 + 72 + 24, BASE)
        with self.assertRaisesRegex(ValueError, "overlapping virtual"):
            refs.Collection(data)

    def test_multi_start_rejected(self):
        data = fixture()
        struct.pack_into("<H", data, 8192 + 28 + 12 + 22, 0x8001)
        with self.assertRaisesRegex(ValueError, "multi-start"):
            refs.Collection(data).resolve(BASE + 0x1020)

    def test_empty_page(self):
        data = fixture()
        struct.pack_into("<H", data, 8192 + 28 + 12 + 22, 0xffff)
        with self.assertRaisesRegex(ValueError, "not a chained"):
            refs.Collection(data).resolve(BASE + 0x1020)

    def test_slot_not_backed(self):
        c = refs.Collection(fixture())
        for slot in (BASE, BASE + 0x2000, BASE + 0x1ffc, BASE - 4):
            with self.subTest(slot=slot), self.assertRaises(ValueError):
                c.resolve(slot)

    def test_odd_page_start(self):
        data = fixture()
        struct.pack_into("<H", data, 8192 + 28 + 12 + 22, 0x21)
        with self.assertRaisesRegex(ValueError, "chain start"):
            refs.Collection(data).resolve(BASE + 0x1020)


if __name__ == "__main__":
    unittest.main()
