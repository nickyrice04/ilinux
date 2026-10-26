#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original 31AF geometry/corruption tests; synthetic code is never executed."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import plistlib
import struct
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


image = load("image31af", "image.py")
validator = load("validator31af", "validate.py")


def fixture():
    data = bytearray(0x60000)
    struct.pack_into("<I", data, 0x58000, 0x14000000)
    struct.pack_into("<I", data, 0x5C000, 0x14000000)
    data[0x5C100:0x5C120] = bytes(range(32))
    return bytes(data)


def commands(blob, header=0):
    count, size = struct.unpack_from("<II", blob, header + 16)
    pos, rows = header + 32, []
    for _ in range(count):
        kind, length = struct.unpack_from("<II", blob, pos)
        rows.append((kind, pos, length))
        pos += length
    if pos != header + 32 + size:
        raise AssertionError("test command extent")
    return rows


def segment(blob, name, header=0):
    return next(pos for kind, pos, _ in commands(blob, header)
                if kind == 0x19 and bytes(blob[pos + 8:pos + 24]).rstrip(b"\0") == name)


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.payload = fixture()
        self.blob, self.report = image.package(self.payload)

    def refuse(self, data, pattern=".", payload=None):
        with self.assertRaisesRegex(ValueError, pattern):
            validator.validate(bytes(data), payload)

    def test_complete_profile_and_roundtrip(self):
        checked = validator.validate(self.blob, self.payload)
        self.assertEqual(checked["status"], "STRUCTURAL_PROFILE_PASS")
        self.assertEqual(checked["recovered_payload_sha256"], hashlib.sha256(self.payload).hexdigest())
        self.assertEqual(self.blob[0x8000:0x64000], self.payload[0x4000:])
        self.assertEqual(len(self.blob), 442368)
        self.assertEqual(image.package(self.payload), (self.blob, self.report))
        self.assertEqual(checked["entry"], hex(image.DEFAULT_BASE + 0x5C000))
        self.assertFalse(checked["own_record_or_stack"])
        self.assertFalse(checked["data_sptm_is_own_storage"])
        self.assertEqual(checked["native_acceptance"], "NOT_TESTED")
        self.assertFalse(checked["installer_invoked"])

    def test_multiple_bases_and_uint64_last_valid_base(self):
        for base in (0x4000, 0x40400000, image.DEFAULT_BASE, (1 << 64) - 0x68000):
            with self.subTest(base=base):
                blob, report = image.package(self.payload, base)
                self.assertEqual(validator.validate(blob)["inner_base"], hex(base))
                self.assertEqual(report["outer_base"], hex(base - 0x4000))
                self.assertEqual(blob[0x8000:0x64000], self.payload[0x4000:])

    def test_bad_payload_and_base(self):
        for base in (True, -0x4000, 0, 1, (1 << 64) - 0x64000, 1 << 64):
            with self.subTest(base=base), self.assertRaises(ValueError):
                image.package(self.payload, base)
        for payload in (b"", bytearray(self.payload), bytes(0x60000), self.payload[:-1], self.payload + b"x"):
            with self.assertRaises(ValueError):
                image.package(payload)
        for start, end in ((0, 0x4000), (0x58000, 0x5C000), (0x5C000, 0x60000)):
            payload = bytearray(self.payload)
            payload[start:end] = bytes(end - start)
            if start == 0:
                payload[0] = 1
            with self.subTest(start=start), self.assertRaises(ValueError):
                image.package(bytes(payload))

    def test_entire_reserved_monitor_region_is_zero_only(self):
        self.assertFalse(any(self.blob[0x8000:0x5C000]))
        for position in (0x4000, 0x7FFF, 0x27FFF, 0x57FFF):
            payload = bytearray(self.payload)
            payload[position] = 1
            with self.subTest(position=position), self.assertRaisesRegex(ValueError, "reservation"):
                image.package(bytes(payload))
            data = bytearray(self.blob)
            data[position + 0x4000] = 1
            self.refuse(data, "reservation")

    def test_header_types_entry_and_collection_absolute_offsets(self):
        self.assertEqual(struct.unpack_from("<I", self.blob, 12)[0], 12)
        self.assertEqual(struct.unpack_from("<I", self.blob, 0x400C)[0], 2)
        entry = commands(self.blob)[-1][1]
        self.assertEqual(struct.unpack_from("<QQII", self.blob, entry + 8),
                         (image.DEFAULT_BASE, 0x4000, 32, 0))
        expected = [(b"__TEXT", 0x4000), (b"__DATA_SPTM", 0x8000),
                    (b"__TEXT_EXEC", 0x5C000), (b"__TEXT_BOOT_EXEC", 0x60000),
                    (b"__PRELINK_INFO", 0x64000), (b"__LINKEDIT", 0x68000)]
        for name, offset in expected:
            pos = segment(self.blob, name, 0x4000)
            self.assertEqual(struct.unpack_from("<Q", self.blob, pos + 40)[0], offset)

    def test_size_and_header_field_mutations(self):
        self.refuse(self.blob[:-1], "complete image size")
        self.refuse(self.blob + b"x", "complete image size")
        for header in (0, 0x4000):
            for field in (0, 4, 8, 12, 24, 28):
                data = bytearray(self.blob)
                data[header + field] ^= 1
                self.refuse(data, "Mach-O header")

    def test_command_count_size_and_length_mutations(self):
        for header in (0, 0x4000):
            for field, value in ((16, 0), (16, 33), (20, 0), (20, 0x4000)):
                data = bytearray(self.blob)
                struct.pack_into("<I", data, header + field, value)
                self.refuse(data)
            for length in (0, 4, 9, 0x4000):
                data = bytearray(self.blob)
                struct.pack_into("<I", data, header + 36, length)
                self.refuse(data, "command length")
            data = bytearray(self.blob)
            struct.pack_into("<I", data, header + 32, 0x1337)
            self.refuse(data, "unsupported load command")

    def test_fileset_entry_presence_and_fields(self):
        _, pos, size = commands(self.blob)[-1]
        data = bytearray(self.blob)
        count, total = struct.unpack_from("<II", data, 16)
        struct.pack_into("<II", data, 16, count - 1, total - size)
        data[pos:pos + size] = bytes(size)
        self.refuse(data, "exactly one fileset entry")
        data = bytearray(self.blob)
        data[pos + size:pos + 2 * size] = data[pos:pos + size]
        struct.pack_into("<II", data, 16, count + 1, total + size)
        self.refuse(data, "exactly one fileset entry")
        for field, fmt, value in ((8, "Q", image.DEFAULT_BASE + 0x4000),
                                  (16, "Q", 0), (24, "I", 0), (28, "I", 1)):
            data = bytearray(self.blob)
            struct.pack_into("<" + fmt, data, pos + field, value)
            self.refuse(data)
        for at in (pos + 32, pos + size - 1):
            data = bytearray(self.blob)
            data[at] = ord("x")
            self.refuse(data)

    def test_segment_permissions_and_header_agreement(self):
        for name in (b"__TEXT", b"__DATA_SPTM", b"__TEXT_EXEC", b"__TEXT_BOOT_EXEC",
                     b"__PRELINK_INFO", b"__LINKEDIT"):
            pos = segment(self.blob, name)
            data = bytearray(self.blob)
            struct.pack_into("<ii", data, pos + 56, 7, 7)
            self.refuse(data, "permissions")
        data = bytearray(self.blob)
        pos = segment(data, b"__DATA_SPTM", 0x4000)
        struct.pack_into("<ii", data, pos + 56, 1, 1)
        self.refuse(data, "data permissions")
        data = bytearray(self.blob)
        pos = segment(data, b"__TEXT_EXEC", 0x4000)
        struct.pack_into("<Q", data, pos + 24, image.DEFAULT_BASE + 0x54000)
        self.refuse(data)

    def test_segment_bounds_alignment_and_full_extents(self):
        pos = segment(self.blob, b"__TEXT_BOOT_EXEC")
        for field, value in ((40, 0x6C000), (40, 1), (24, (1 << 64) - 0x1000),
                             (32, 0x8000), (48, 0), (48, 0x8000)):
            data = bytearray(self.blob)
            struct.pack_into("<Q", data, pos + field, value)
            self.refuse(data)
        for header in (0, 0x4000):
            data = bytearray(self.blob)
            pos = segment(data, b"__TEXT_EXEC", header)
            struct.pack_into("<Q", data, pos + 40, 0x58000)
            self.refuse(data, "overlapping segments")

    def test_segment_duplicate_unknown_and_order(self):
        pos = segment(self.blob, b"__TEXT_EXEC")
        for name in (b"__TEXT", b"__UNKNOWN"):
            data = bytearray(self.blob)
            data[pos + 8:pos + 24] = name.ljust(16, b"\0")
            self.refuse(data)
        data = bytearray(self.blob)
        a, b = segment(data, b"__TEXT_EXEC"), segment(data, b"__TEXT_BOOT_EXEC")
        data[a:a + 72], data[b:b + 72] = data[b:b + 72], data[a:a + 72]
        self.refuse(data, "segment set/order")

    def test_thread_fields_and_pc_bounds(self):
        for header in (0, 0x4000):
            pos = next(pos for kind, pos, _ in commands(self.blob, header) if kind == 5)
            for field in (8, 12, 16, 16 + 248, 16 + 264):
                data = bytearray(self.blob)
                data[pos + field] ^= 1
                self.refuse(data)
        for offset in (0x4000, 0x58000, 0x5C004, 0x60000):
            data = bytearray(self.blob)
            for header in (0, 0x4000):
                pos = next(pos for kind, pos, _ in commands(data, header) if kind == 5)
                struct.pack_into("<Q", data, pos + 272, image.DEFAULT_BASE + offset)
            self.refuse(data, "intended boot execution")

    def test_header_and_tail_padding(self):
        for position in (0x3FFF, 0x7FFF, 0x67FFF, 0x68000, 0x6BFFF):
            data = bytearray(self.blob)
            data[position] = 1
            self.refuse(data, "padding|reservation")

    def test_metadata_section_bounds_offset_and_flags(self):
        for header in (0, 0x4000):
            info = segment(self.blob, b"__PRELINK_INFO", header) + 72
            for field, fmt, value in ((32, "Q", image.DEFAULT_BASE + 0x60004),
                                      (40, "Q", 0x5000), (48, "I", 0x68000),
                                      (52, "I", 1), (56, "I", 1), (60, "I", 1),
                                      (64, "I", 1), (68, "I", 1), (72, "I", 1), (76, "I", 1)):
                data = bytearray(self.blob)
                struct.pack_into("<" + fmt, data, info + field, value)
                self.refuse(data)
        data = bytearray(self.blob)
        for header in (0, 0x4000):
            info = segment(data, b"__PRELINK_INFO", header) + 72
            struct.pack_into("<Q", data, info + 32, image.DEFAULT_BASE + 0x60008)
            struct.pack_into("<I", data, info + 48, 0x64008)
        self.refuse(data, "must start at metadata")

    def test_metadata_invalid_xml_fields_and_hash(self):
        data = bytearray(self.blob)
        data[0x64000] = 0
        self.refuse(data, "metadata")
        info = segment(self.blob, b"__PRELINK_INFO", 0x4000) + 72
        size = struct.unpack_from("<Q", self.blob, info + 40)[0]
        metadata = plistlib.loads(self.blob[0x64000:0x64000 + size])
        for mutate in (lambda d: d.update(extra=0), lambda d: d.update(_PrelinkKCID=b"x"),
                       lambda d: d.update(_PrelinkInfoDictionary=[{}]),
                       lambda d: d.update(_PrelinkKCID=bytes(16))):
            modified = dict(metadata)
            mutate(modified)
            encoded = plistlib.dumps(modified, fmt=plistlib.FMT_XML)
            data = bytearray(self.blob)
            data[0x64000:0x68000] = encoded.ljust(0x4000, b"\0")
            for header in (0, 0x4000):
                section = segment(data, b"__PRELINK_INFO", header) + 72
                struct.pack_into("<Q", data, section + 40, len(encoded))
            self.refuse(data, "metadata")

    def test_intrinsic_payload_hash_and_supplied_payload_binding(self):
        for position in (0x5C004, 0x60004, 0x63FFF):
            data = bytearray(self.blob)
            data[position] ^= 1
            self.refuse(data, "payload/metadata binding")
        other = bytearray(self.payload)
        other[0x5C004] ^= 1
        self.refuse(self.blob, "payload bytes changed", bytes(other))
        for wrong in (b"", bytearray(self.payload), bytes(0x60000), self.payload[:-1]):
            self.refuse(self.blob, "invalid supplied", wrong)

    def test_all_five_arithmetic_paths_for_both_headers(self):
        for header in (0, 0x4000):
            segments = validator.parse(self.blob, header, 12 if header == 0 else 2)["segments"]
            for profile in (False, True):
                r = validator.profile_arithmetic(segments, len(self.blob), profile)
                self.assertEqual(r["profile_text_exec_bytes"], 0x4000 if profile else None)
                self.assertEqual(r["selected_start_minus_text_bytes"],
                                 (0x8000 if profile else 0x64000) - header)
                self.assertEqual(r["linkedit_minus_prelink_bytes"], 0x4000)
                self.assertEqual(r["text_exec_minus_data_bytes"], 0x54000)
                self.assertEqual(r["prelink_minus_boot_bytes"], 0x4000)
            ranges = validator.split_range(segments, len(self.blob))
            self.assertTrue(all(r["file_gap"] == r["virtual_gap"] == 0
                                for r in ranges["checked_adjacent_ranges"]))

    def test_arithmetic_underflow_overflow_and_optional_roles(self):
        original = validator.parse(self.blob, 0, 12)["segments"]
        for profile in (False, True):
            for left, right in ((b"__DATA_SPTM", b"__TEXT_EXEC"),
                                (b"__TEXT_BOOT_EXEC", b"__PRELINK_INFO"),
                                (b"__PRELINK_INFO", b"__LINKEDIT")):
                segments = copy.deepcopy(original)
                by_name = {s["name"]: s for s in segments}
                by_name[right]["offset"] = by_name[left]["offset"] - 0x4000
                with self.subTest(profile=profile, right=right), self.assertRaises(ValueError):
                    validator.profile_arithmetic(segments, len(self.blob), profile)
        for field, value in (("offset", -1), ("address", 1 << 64), ("size", 1 << 64)):
            segments = copy.deepcopy(original)
            segments[1][field] = value
            with self.assertRaises(ValueError):
                validator.split_range(segments, len(self.blob))
        for omitted in (b"__DATA_SPTM", b"__TEXT_BOOT_EXEC"):
            segments = [s for s in original if s["name"] != omitted]
            r = validator.profile_arithmetic(segments, len(self.blob), True)
            self.assertEqual(r["profile_text_exec_bytes"], 0x4000)
            if omitted == b"__DATA_SPTM":
                self.assertEqual(r["selected_start_role"], "__TEXT_EXEC")
                self.assertIsNone(r["text_exec_minus_data_bytes"])
            else:
                self.assertIsNone(r["prelink_minus_boot_bytes"])

    def test_old_consumed_geometry_cannot_pass_new_profile(self):
        old_image = load("frozen31ae_package", "../bootimage31ae/ordered.py")
        payload = bytearray(0x24000)
        struct.pack_into("<I", payload, 0x10000, 0x14000000)
        struct.pack_into("<I", payload, 0x14000, 0x14000000)
        old, _ = old_image.package(bytes(payload))
        self.refuse(old, "complete image size")
        self.refuse(old + bytes(0x3C000), "payload mapping mismatch")

    def test_fileset_command_is_canonical_for_our_profile(self):
        _, pos, size = commands(self.blob)[-1]
        data = bytearray(self.blob)
        count, total = struct.unpack_from("<II", data, 16)
        struct.pack_into("<II", data, 16, count, total + 8)
        struct.pack_into("<I", data, pos + 4, size + 8)
        self.refuse(data, "fileset entry command size")

    def test_range_check_reports_both_headers(self):
        result = validator.range_check(self.blob)
        self.assertEqual(result["status"], "CHECKED_SPLIT_RANGE_PASS")
        self.assertEqual([h["header_offset"] for h in result["headers"]], [0, 0x4000])


if __name__ == "__main__":
    unittest.main(verbosity=2)
