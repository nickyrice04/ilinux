#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original geometry tests; no Apple software or executable payload required."""
import importlib.util
from pathlib import Path
import plistlib
import struct
import sys
import unittest

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("image31ab", Path(__file__).with_name("image.py"))
image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image)


def fixture():
    data = bytearray(image.PAYLOAD_BYTES)
    # Original synthetic branch-to-self markers, not a functioning entry host.
    struct.pack_into("<I", data, 0xc000, 0x14000000)
    struct.pack_into("<I", data, 0x10000, 0x14000000)
    return bytes(data)


def commands(blob):
    count, size = struct.unpack_from("<II", blob, 16)
    pos = 32
    rows = []
    for _ in range(count):
        kind, length = struct.unpack_from("<II", blob, pos)
        assert length >= 8 and length % 8 == 0
        rows.append((kind, blob[pos:pos + length]))
        pos += length
    assert pos == 32 + size
    return rows


class ImageTests(unittest.TestCase):
    def test_exact_payload_offsets(self):
        original = fixture()
        blob, report = image.package(original)
        self.assertEqual(len(blob), 0x1c000)
        self.assertEqual(blob[0x4000:0x14000], original[0x4000:])
        self.assertEqual(report["image_sha256"], image.sha(blob))
        self.assertEqual(report["firmware_acceptance"], "NOT_TESTED")

    def test_nonoverlapping_segments_and_permissions(self):
        blob, _ = image.package(fixture())
        regions = []
        for kind, body in commands(blob):
            if kind != 0x19:
                continue
            (_, _, name, va, size, off, count, maxprot, prot, _, _) = struct.unpack_from("<II16sQQQQiiII", body)
            self.assertEqual(va, image.DEFAULT_BASE + off)
            self.assertEqual(size, count)
            self.assertEqual(maxprot, prot)
            self.assertNotEqual(prot & 6, 6)  # Never writable and executable.
            self.assertEqual(off % image.PAGE, 0)
            self.assertLessEqual(off + size, len(blob))
            regions.append((off, off + size, name.rstrip(b"\0")))
        self.assertEqual([r[0] for r in regions], [0,0x4000,0xc000,0x10000,0x14000,0x18000])
        for a, b in zip(regions, regions[1:]):
            self.assertEqual(a[1], b[0])

    def test_entry_maps_to_boot_code(self):
        blob, _ = image.package(fixture())
        thread = [body for kind, body in commands(blob) if kind == 5]
        self.assertEqual(len(thread), 1)
        self.assertEqual(struct.unpack_from("<Q", thread[0], 16 + 256)[0], image.DEFAULT_BASE + 0xc000)
        self.assertEqual(struct.unpack_from("<I", blob, 0xc000)[0], 0x14000000)

    def test_no_pointer_fixup_commands(self):
        blob, _ = image.package(fixture())
        kinds = [kind for kind, _ in commands(blob)]
        self.assertNotIn(0x80000034, kinds)
        self.assertNotIn(0x80000022, kinds)
        self.assertEqual(kinds.count(0x19), 6)

    def test_metadata_is_original_and_deterministic(self):
        blob, _ = image.package(fixture())
        data = blob[0x14000:0x18000].rstrip(b"\0")
        plist = plistlib.loads(data)
        self.assertEqual(set(plist), {"_PrelinkKCID", "_PrelinkInfoDictionary"})
        self.assertEqual(plist["_PrelinkInfoDictionary"], [])
        self.assertEqual(blob, image.package(fixture())[0])

    def test_rejects_geometry_or_nonzero_storage(self):
        for n in (0, 0x13fff, 0x14001):
            with self.assertRaises(ValueError): image.package(bytes(n))
        for position in (0, 0x3fff, 0x4000, 0x7fff, 0x8000, 0xbfff):
            data = bytearray(fixture()); data[position] = 1
            with self.assertRaises(ValueError): image.package(bytes(data))

    def test_rejects_absent_code(self):
        for lo, hi in ((0xc000, 0x10000), (0x10000, 0x14000)):
            data = bytearray(fixture()); data[lo:hi] = bytes(hi-lo)
            with self.assertRaises(ValueError): image.package(bytes(data))

    def test_slide_and_overflow(self):
        original = fixture()
        for base in (0, 0x40000000, image.DEFAULT_BASE):
            blob, report = image.package(original, base)
            self.assertEqual(report["entry"], hex(base + 0xc000))
            self.assertEqual(blob[0x4000:0x14000], original[0x4000:])
        for base in (True, -0x4000, 1, (1 << 64)-0x4000, 1 << 64):
            with self.assertRaises(ValueError): image.package(original, base)


if __name__ == "__main__":
    unittest.main(verbosity=2)
