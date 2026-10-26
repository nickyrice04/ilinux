#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original positive and corrupted-image cases; no target execution required."""
import importlib.util
import copy
import plistlib
import hashlib
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


image = load("ordered31ae", "ordered.py")
validator = load("validator_ordered31ae", "validate_ordered.py")
old_image = load("unordered_control31ad", "../bootimage31ad/image.py")
old_validator = load("unordered_validator31ad", "../bootimage31ad/validate.py")
prior_image = load("ordered_control31ad", "../bootimage31ad/ordered.py")
prior_validator = load("ordered_validator31ad", "../bootimage31ad/validate_ordered.py")


def fixture():
    data = bytearray(0x24000)
    struct.pack_into("<I", data, 0x10000, 0x14000000)
    struct.pack_into("<I", data, 0x14000, 0x14000000)
    data[0x16000:0x16020] = bytes(range(32))
    return bytes(data)


def flat_fixture(kind=12, ordered=True):
    """Original synthetic flat geometry, independent of frozen 31AC files."""
    base = image.DEFAULT_BASE
    normal_off, boot_off = (0x10000, 0x14000) if ordered else (0x20000, 0x10000)
    data_off = 0x4000 if ordered else 0x4000
    commands = [image.segment("__TEXT", base, 0, 0x4000, 1),
        image.segment("__DATA_SPTM", base + data_off, data_off, 0xC000, 3),
        image.segment("__TEXT_BOOT_EXEC", base + boot_off, boot_off, 0x10000, 5),
        image.segment("__TEXT_EXEC", base + normal_off, normal_off, 0x4000, 5),
        image.thread(base + boot_off),
        image.segment("__PRELINK_INFO", base + 0x24000, 0x24000, 0x4000, 1),
        image.segment("__LINKEDIT", base + 0x28000, 0x28000, 0x4000, 1)]
    encoded = image.header(kind, commands)
    data = bytearray(0x2C000)
    data[:len(encoded)] = encoded
    return bytes(data)


def commands(blob, header=0):
    count, size = struct.unpack_from("<II", blob, header + 16)
    pos = header + 32
    rows = []
    for _ in range(count):
        kind, length = struct.unpack_from("<II", blob, pos)
        rows.append((kind, pos, length))
        pos += length
    if pos != header + 32 + size:
        raise AssertionError("test fixture load command extent")
    return rows


def segment(blob, name, header=0):
    return next(pos for kind, pos, length in commands(blob, header)
                if kind == 0x19 and bytes(blob[pos + 8:pos + 24]).rstrip(b"\0") == name)


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.payload = fixture()
        self.original, self.report = image.package(self.payload)

    def changed(self):
        return bytearray(self.original)

    def refuse(self, data, text=None, payload=None):
        with self.assertRaisesRegex(ValueError, text or "."):
            validator.validate(bytes(data), payload)

    def test_complete_profile_and_payload(self):
        r = validator.validate(self.original, self.payload)
        self.assertEqual(r["status"], "STRUCTURAL_PROFILE_PASS")
        self.assertEqual(r["native_acceptance"], "NOT_TESTED")
        self.assertFalse(r["installer_invoked"])
        self.assertEqual(self.original[0x8000:0x28000], self.payload[0x4000:])
        self.assertEqual(len(self.original), 0x30000)
        self.assertEqual(self.report["entry"], hex(image.DEFAULT_BASE + 0x14000))
        self.assertEqual(self.report["vector"], hex(image.DEFAULT_BASE + 0x14800))
        self.assertEqual(self.report["record"], hex(image.DEFAULT_BASE + 0x4000))
        self.assertEqual(self.original, image.package(self.payload)[0])
        self.assertEqual(self.report["image_sha256"], hashlib.sha256(self.original).hexdigest())
        self.assertEqual(self.report, image.package(self.payload)[1])

    def test_public_headers_have_one_embedded_original(self):
        self.assertEqual(struct.unpack_from("<I", self.original, 12)[0], 12)
        self.assertEqual(struct.unpack_from("<I", self.original, 0x4000 + 12)[0], 2)
        entry = next(pos for kind, pos, size in commands(self.original) if kind == 0x80000035)
        va, offset, nameoff, reserved = struct.unpack_from("<QQII", self.original, entry + 8)
        self.assertEqual((va, offset, nameoff, reserved), (image.DEFAULT_BASE, 0x4000, 32, 0))
        self.assertEqual(self.original[entry + nameoff:].split(b"\0", 1)[0], b"com.apple.kernel")

    def test_collection_absolute_inner_offsets(self):
        for name, offset in ((b"__TEXT", 0x4000), (b"__DATA_SPTM", 0x8000),
                             (b"__TEXT_BOOT_EXEC", 0x18000), (b"__TEXT_EXEC", 0x14000),
                             (b"__PRELINK_INFO", 0x28000), (b"__LINKEDIT", 0x2C000)):
            pos = segment(self.original, name, 0x4000)
            self.assertEqual(struct.unpack_from("<Q", self.original, pos + 40)[0], offset)
        info = segment(self.original, b"__PRELINK_INFO", 0x4000) + 72
        self.assertEqual(struct.unpack_from("<I", self.original, info + 48)[0], 0x28000)

    def test_payload_vas_remain_constant_at_multiple_bases(self):
        for base in (0x4000, 0x40400000, image.DEFAULT_BASE):
            with self.subTest(base=base):
                blob, r = image.package(self.payload, base)
                checked = validator.validate(blob, self.payload)
                self.assertEqual(checked["entry"], hex(base + 0x14000))
                self.assertEqual(r["outer_base"], hex(base - 0x4000))
                self.assertEqual(blob[0x8000:0x28000], self.payload[0x4000:])

    def test_packager_rejects_bad_base_or_payload(self):
        for base in (True, -0x4000, 0, 1, (1 << 64) - 0x4000, 1 << 64):
            with self.subTest(base=base), self.assertRaises(ValueError):
                image.package(self.payload, base)
        for payload in (b"", bytes(0x24000), self.payload[:-1], self.payload + b"x"):
            with self.assertRaises(ValueError):
                image.package(payload)
        for position in (0, 0x3FFF, 0x4000, 0x7FFF, 0xBFFF, 0xFFFF):
            payload = bytearray(self.payload); payload[position] = 1
            with self.assertRaises(ValueError):
                image.package(bytes(payload))

    def test_short_or_extended_file(self):
        self.refuse(self.original[:-1], "complete image size")
        self.refuse(self.original + b"x", "complete image size")

    def test_bad_outer_or_inner_header(self):
        for pos in (0, 4, 8, 12, 24, 28, 0x4000, 0x4004, 0x400C):
            data = self.changed(); data[pos] ^= 1
            self.refuse(data, "Mach-O header")

    def test_invalid_command_count_and_extent(self):
        for pos, value in ((16, 0), (16, 33), (20, 0x4000), (20, 0),
                           (0x4010, 0), (0x4014, 0x4000)):
            data = self.changed(); struct.pack_into("<I", data, pos, value)
            self.refuse(data)

    def test_command_lengths_are_bounded(self):
        for value in (0, 4, 9, 0x4000):
            data = self.changed(); struct.pack_into("<I", data, 36, value)
            self.refuse(data, "command length")

    def test_missing_fileset_entry(self):
        data = self.changed()
        _, pos, size = commands(data)[-1]
        count, cmdbytes = struct.unpack_from("<II", data, 16)
        struct.pack_into("<II", data, 16, count - 1, cmdbytes - size)
        data[pos:pos + size] = bytes(size)
        self.refuse(data, "exactly one fileset entry")

    def test_duplicate_fileset_entry(self):
        data = self.changed()
        _, pos, size = commands(data)[-1]
        count, cmdbytes = struct.unpack_from("<II", data, 16)
        data[pos + size:pos + 2 * size] = data[pos:pos + size]
        struct.pack_into("<II", data, 16, count + 1, cmdbytes + size)
        self.refuse(data, "exactly one fileset entry")

    def test_fileset_identifier_and_string_bounds(self):
        entry = commands(self.original)[-1][1]
        for where, value in ((entry + 24, 0), (entry + 24, 0x10000), (entry + 28, 1)):
            data = self.changed(); struct.pack_into("<I", data, where, value)
            self.refuse(data, "fileset entry string offset")
        data = self.changed(); data[entry + 32] = ord("x")
        self.refuse(data, "identifier or file offset")
        data = self.changed()
        data[entry + 32:entry + commands(self.original)[-1][2]] = b"x" * (commands(self.original)[-1][2] - 32)
        self.refuse(data, "unterminated fileset identifier")

    def test_inner_offset_and_address(self):
        entry = commands(self.original)[-1][1]
        for offset in (0, 1, 0x8000, 0x30000, (1 << 64) - 1):
            data = self.changed(); struct.pack_into("<Q", data, entry + 16, offset)
            self.refuse(data, "identifier or file offset")
        data = self.changed(); struct.pack_into("<Q", data, entry + 8, image.DEFAULT_BASE + 0x4000)
        self.refuse(data, "entry address mismatch")

    def test_segment_file_bounds_and_alignment(self):
        seg = segment(self.original, b"__TEXT_EXEC")
        for field, value in ((40, 0x30000), (48, 0x8000), (40, 1),
                             (24, (1 << 64) - 0x1000)):
            data = self.changed(); struct.pack_into("<Q", data, seg + field, value)
            self.refuse(data)

    def test_segment_overlap_and_duplicate_name(self):
        seg = segment(self.original, b"__TEXT_EXEC")
        data = self.changed(); struct.pack_into("<Q", data, seg + 40, 0xC000)
        self.refuse(data, "overlapping segments")
        data = self.changed(); data[seg + 8:seg + 24] = b"__TEXT\0".ljust(16, b"\0")
        self.refuse(data, "duplicate segment")

    def test_segment_permissions_and_nesting_agreement(self):
        seg = segment(self.original, b"__TEXT_EXEC")
        data = self.changed(); struct.pack_into("<ii", data, seg + 56, 7, 7)
        self.refuse(data, "permissions")
        seg = segment(self.original, b"__DATA_SPTM")
        data = self.changed(); struct.pack_into("<ii", data, seg + 56, 1, 1)
        self.refuse(data, "split data permissions")

    def test_thread_shape_and_reserved_registers(self):
        thread = next(pos for kind, pos, _ in commands(self.original) if kind == 5)
        data = self.changed(); struct.pack_into("<I", data, thread + 8, 0)
        self.refuse(data, "thread state")
        data = self.changed(); data[thread + 16] = 1
        self.refuse(data, "initial thread fields")

    def test_entry_outside_execute_and_outer_inner_disagreement(self):
        data = self.changed()
        for header in (0, 0x4000):
            thread = next(pos for kind, pos, _ in commands(data, header) if kind == 5)
            struct.pack_into("<Q", data, thread + 16 + 256, image.DEFAULT_BASE + 0x4000)
        self.refuse(data, "intended boot execution")
        data = self.changed()
        thread = next(pos for kind, pos, _ in commands(data) if kind == 5)
        struct.pack_into("<Q", data, thread + 16 + 256, image.DEFAULT_BASE + 0x14004)
        self.refuse(data, "outer/inner entry mismatch")

    def test_section_bounds_and_virtual_mapping(self):
        info = segment(self.original, b"__PRELINK_INFO", 0x4000) + 72
        for field, kind, value in ((48, "I", 0x30000), (40, "Q", 0x5000),
                                   (32, "Q", image.DEFAULT_BASE + 0x24004)):
            data = self.changed(); struct.pack_into("<" + kind, data, info + field, value)
            self.refuse(data)

    def test_invalid_metadata_and_binding(self):
        data = self.changed(); data[0x28000] = 0
        self.refuse(data, "prelink metadata")
        changed = bytearray(self.payload); changed[0x16000] ^= 1
        self.refuse(self.original, "payload bytes changed", bytes(changed))
        data = self.changed(); data[0x1A000] ^= 1
        self.refuse(data, "recovered payload/metadata binding mismatch", self.payload)

    def test_capture_and_code_presence(self):
        data = self.changed(); data[0x8000] = 1
        self.refuse(data, "capture/stack")
        for start, end in ((0x18000, 0x28000), (0x14000, 0x18000)):
            data = self.changed(); data[start:end] = bytes(end - start)
            self.refuse(data, "code sentinels")

    def test_unknown_fixup_command_is_refused(self):
        data = self.changed(); struct.pack_into("<I", data, 32, 0x80000034)
        self.refuse(data, "unsupported load command")

    def test_reserved_padding_remains_zero(self):
        for position, reason in ((0x3000, "header padding"), (0x7000, "header padding"),
                                 (0x2BFFF, "metadata padding"), (0x2C000, "link-edit")):
            data = self.changed(); data[position] = 1
            self.refuse(data, reason)

    def test_checked_range_is_nonnegative_for_each_header(self):
        result = validator.range_check(self.original)
        self.assertEqual(result["status"], "CHECKED_SPLIT_RANGE_PASS")
        self.assertEqual([h["header_offset"] for h in result["headers"]], [0, 0x4000])
        for row in result["headers"]:
            self.assertEqual(row["data_sptm_fileoff"], 0x8000)
            self.assertEqual(row["text_exec_fileoff"], 0x14000)
            self.assertEqual(row["boot_exec_fileoff"], 0x18000)
            self.assertEqual(row["checked_text_to_boot_bytes"], 0x4000)

    def test_old_nested_headers_parse_but_split_order_is_rejected(self):
        payload = bytearray(0x24000)
        struct.pack_into("<I", payload, 0x10000, 0x14000000)
        struct.pack_into("<I", payload, 0x20000, 0x14000000)
        prior, _ = old_image.package(bytes(payload))
        self.assertEqual(old_validator.validate(prior)["status"], "STRUCTURAL_PROFILE_PASS")
        with self.assertRaisesRegex(ValueError, "ordering would underflow"):
            validator.range_check(prior)
        self.refuse(prior, "ordering would underflow")

    def test_flat_type_two_and_twelve_checked_guard(self):
        for kind in (2, 12):
            with self.subTest(kind=kind):
                accepted = validator.range_check(flat_fixture(kind, True))
                self.assertEqual(accepted["headers"][0]["filetype"], kind)
                self.assertEqual(accepted["headers"][0]["checked_text_to_boot_bytes"], 0x4000)
                # The original flat 31AC ordering has no nested-header defect;
                # rejection must specifically reach the checked subtraction.
                with self.assertRaisesRegex(ValueError, "ordering would underflow"):
                    validator.range_check(flat_fixture(kind, False))

    def test_each_nested_header_independently_requires_ordering(self):
        for header in (0, 0x4000):
            data = self.changed()
            normal = segment(data, b"__TEXT_EXEC", header)
            boot = segment(data, b"__TEXT_BOOT_EXEC", header)
            # Exchange regions while retaining their respective sizes so both
            # resulting executable regions remain inside the file and disjoint.
            struct.pack_into("<QQQQ", data, normal + 24,
                             image.DEFAULT_BASE + 0x20000, 0x4000, 0x24000, 0x4000)
            struct.pack_into("<QQQQ", data, boot + 24,
                             image.DEFAULT_BASE + 0x10000, 0x10000, 0x14000, 0x10000)
            # Move data to the matching old location to preserve nonoverlap.
            owned = segment(data, b"__DATA_SPTM", header)
            struct.pack_into("<QQQQ", data, owned + 24,
                             image.DEFAULT_BASE + 0x4000, 0xC000, 0x8000, 0xC000)
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "ordering would underflow"):
                validator.range_check(bytes(data))

    def test_capture_zero_check_excludes_normal_executable_segment(self):
        data = bytearray(self.payload)
        data[0x11000] = 0xA5
        blob, _ = image.package(bytes(data))
        validator.validate(blob, bytes(data))
        self.assertEqual(blob[0x15000], 0xA5)
        for position in (0x8000, 0xC000, 0x13FFF):
            changed = bytearray(blob); changed[position] = 1
            self.refuse(changed, "capture/stack")

    def test_metadata_does_not_overlap_original_bytes(self):
        self.assertEqual(self.original[0x8000:0x28000], self.payload[0x4000:])
        for header in (0, 0x4000):
            boot = segment(self.original, b"__TEXT_BOOT_EXEC", header)
            info = segment(self.original, b"__PRELINK_INFO", header)
            boot_off, boot_size = struct.unpack_from("<QQ", self.original, boot + 40)
            info_off = struct.unpack_from("<Q", self.original, info + 40)[0]
            self.assertEqual(boot_off + boot_size, info_off)

    def test_malformed_finite_range_profiles(self):
        for blob in (b"", bytes(0x4000), self.original + bytes(0x4000), self.original[:-1]):
            with self.assertRaises(ValueError):
                validator.range_check(blob)
        data = bytearray(flat_fixture())
        struct.pack_into("<I", data, 12, 6)
        with self.assertRaisesRegex(ValueError, "root file type"):
            validator.range_check(bytes(data))

    def test_cli_refuses_bad_inputs_and_existing_outputs(self):
        build = image.ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="31ae-ordered-test-", dir=build) as tmp:
            root = Path(tmp)
            good = root / "payload.bin"; good.write_bytes(self.payload)
            existing = root / "existing"; existing.mkdir()
            marker = existing / "keep"; marker.write_bytes(b"untouched")
            script = Path(__file__).with_name("ordered.py")

            def run(payload, output):
                return subprocess.run([sys.executable, "-I", str(script), "--payload", str(payload),
                                       "--output", str(output)], capture_output=True, text=True)

            self.assertNotEqual(run(good, existing).returncode, 0)
            self.assertEqual(marker.read_bytes(), b"untouched")
            self.assertEqual(sorted(p.name for p in existing.iterdir()), ["keep"])
            for index, content in enumerate((b"", self.payload[:-1], bytes(0x24000))):
                bad = root / ("bad" + str(index)); bad.write_bytes(content)
                output = root / ("absent" + str(index))
                self.assertNotEqual(run(bad, output).returncode, 0)
                self.assertFalse(output.exists())
            alias = root / "symlink"; alias.symlink_to(good)
            self.assertNotEqual(run(alias, root / "no-link").returncode, 0)
            self.assertFalse((root / "no-link").exists())
            output_alias = root / "output-link"; output_alias.symlink_to(root / "new-target")
            self.assertNotEqual(run(good, output_alias).returncode, 0)
            self.assertFalse((root / "new-target").exists())
            self.assertNotEqual(run(good, root.parent.parent / "31ae-outside-build").returncode, 0)

    def test_cli_synthetic_package_and_validator(self):
        build = image.ROOT / "build"
        build.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="31ae-ordered-test-", dir=build) as tmp:
            root = Path(tmp)
            payload = root / "payload.bin"; payload.write_bytes(self.payload)
            output = root / "output"
            result = subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("ordered.py")),
                "--payload", str(payload), "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            packaged = output / "ilinux-31ae-ordered.macho"
            self.assertEqual(packaged.read_bytes(), self.original)
            checked = subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("validate_ordered.py")),
                str(packaged), "--payload", str(payload)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)


    def split_segments(self, header=0):
        return copy.deepcopy(validator.parse(self.original, header, 12 if header == 0 else 2)["segments"])

    def test_synthetic_31ad_passes_old_guard_fails_new_data_order(self):
        old_payload = bytearray(0x24000)
        struct.pack_into("<I", old_payload, 0x4000, 0x14000000)
        struct.pack_into("<I", old_payload, 0x14000, 0x14000000)
        prior, _ = prior_image.package(bytes(old_payload))
        self.assertEqual(prior_validator.validate(prior)["status"], "STRUCTURAL_PROFILE_PASS")
        self.assertEqual(prior_validator.range_check(prior)["status"], "CHECKED_SPLIT_RANGE_PASS")
        with self.assertRaisesRegex(ValueError, "data-to-text ordering would underflow"):
            validator.range_check(prior)
        self.refuse(prior, "data-to-text ordering would underflow")

    def test_each_nested_header_independently_requires_data_order(self):
        for header in (0, 0x4000):
            data = self.changed()
            owned = segment(data, b"__DATA_SPTM", header)
            normal = segment(data, b"__TEXT_EXEC", header)
            struct.pack_into("<QQQQ", data, owned + 24,
                             image.DEFAULT_BASE + 0x8000, 0xC000, 0xC000, 0xC000)
            struct.pack_into("<QQQQ", data, normal + 24,
                             image.DEFAULT_BASE + 0x4000, 0x4000, 0x8000, 0x4000)
            self.assertEqual(prior_validator.range_check(bytes(data))["status"], "CHECKED_SPLIT_RANGE_PASS")
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "data-to-text ordering"):
                validator.range_check(bytes(data))

    def test_virtual_data_order_is_independent_of_file_order(self):
        for header in (0, 0x4000):
            data = self.changed()
            owned = segment(data, b"__DATA_SPTM", header)
            normal = segment(data, b"__TEXT_EXEC", header)
            struct.pack_into("<Q", data, owned + 24, image.DEFAULT_BASE + 0x8000)
            struct.pack_into("<Q", data, normal + 24, image.DEFAULT_BASE + 0x4000)
            self.assertEqual(prior_validator.range_check(bytes(data))["status"], "CHECKED_SPLIT_RANGE_PASS")
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "data-to-text ordering"):
                validator.range_check(bytes(data))

    def test_data_command_precedes_normal_command(self):
        data = self.changed()
        for header in (0, 0x4000):
            owned = segment(data, b"__DATA_SPTM", header)
            normal = segment(data, b"__TEXT_EXEC", header)
            left, right = bytes(data[owned:owned + 72]), bytes(data[normal:normal + 72])
            data[owned:owned + 72], data[normal:normal + 72] = right, left
        self.refuse(data, "segment set/order mismatch")

    def test_checked_adjacent_extents_cover_all_roles_in_both_spaces(self):
        result = validator.range_check(self.original)
        expected = [("__TEXT", "__DATA_SPTM"), ("__DATA_SPTM", "__TEXT_EXEC"),
                    ("__TEXT_EXEC", "__TEXT_BOOT_EXEC"), ("__TEXT_BOOT_EXEC", "__PRELINK_INFO"),
                    ("__PRELINK_INFO", "__LINKEDIT")]
        for header in result["headers"]:
            rows = header["checked_adjacent_ranges"]
            self.assertEqual([(r["from"], r["to"]) for r in rows], expected)
            for row in rows:
                self.assertEqual((row["file_gap"], row["virtual_gap"]), (0, 0))
                self.assertEqual(row["file_start_delta"], row["virtual_start_delta"])

    def test_each_adjacent_full_extent_refuses_overlap(self):
        for index in range(5):
            segments = self.split_segments()
            segments[index]["size"] += 0x4000
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "adjacent extents overlap"):
                validator.split_range(segments, len(self.original))

    def test_ordered_starts_do_not_hide_file_extent_overrun(self):
        segments = self.split_segments()
        segments[1]["size"] = len(self.original)
        with self.assertRaisesRegex(ValueError, "extent outside offset"):
            validator.split_range(segments, len(self.original))
        for header in (0, 0x4000):
            data = self.changed(); owned = segment(data, b"__DATA_SPTM", header)
            struct.pack_into("<Q", data, owned + 32, 0x30000)
            struct.pack_into("<Q", data, owned + 48, 0x30000)
            self.refuse(data, "segment outside file")

    def test_virtual_full_extent_overflow_is_refused(self):
        for header in (0, 0x4000):
            data = self.changed(); boot = segment(data, b"__TEXT_BOOT_EXEC", header)
            struct.pack_into("<Q", data, boot + 24, (1 << 64) - 0x4000)
            self.refuse(data, "virtual segment overflow")
        segments = self.split_segments()
        segments[3]["address"] = (1 << 64) - 0x4000
        with self.assertRaisesRegex(ValueError, "extent outside address"):
            validator.split_range(segments, len(self.original))

    def test_file_extent_uint64_end_is_not_a_small_file_extent(self):
        data = self.changed(); normal = segment(data, b"__TEXT_EXEC")
        struct.pack_into("<Q", data, normal + 40, (1 << 64) - 0x4000)
        self.refuse(data, "segment outside file")

    def test_highest_aligned_base_with_complete_extents(self):
        base = (1 << 64) - image.IMAGE_BYTES + image.PAGE
        data, _ = image.package(self.payload, base)
        self.assertEqual(validator.validate(data, self.payload)["inner_base"], hex(base))
        with self.assertRaises(ValueError):
            image.package(self.payload, base + image.PAGE)

    def test_profile_false_and_true_report_exact_checked_arithmetic(self):
        for header, text_off in ((0, 0), (0x4000, 0x4000)):
            rows = validator.parse(self.original, header, 12 if header == 0 else 2)["split_range"]
            false, true = rows["arithmetic_profiles"]["false"], rows["arithmetic_profiles"]["true"]
            self.assertFalse(false["profile"]); self.assertTrue(true["profile"])
            self.assertEqual(false["selected_start_role"], "__PRELINK_INFO")
            self.assertEqual(true["selected_start_role"], "__DATA_SPTM")
            self.assertIsNone(false["profile_text_exec_bytes"])
            self.assertEqual(true["profile_text_exec_bytes"], 0x4000)
            self.assertEqual(false["selected_start_minus_text_bytes"], 0x28000 - text_off)
            self.assertEqual(true["selected_start_minus_text_bytes"], 0x8000 - text_off)
            for row in (false, true):
                self.assertEqual(row["linkedit_minus_prelink_bytes"], 0x4000)
                self.assertEqual(row["text_exec_minus_data_bytes"], 0xC000)
                self.assertEqual(row["prelink_minus_boot_bytes"], 0x10000)

    def test_profile_true_optional_data_uses_normal_fallback(self):
        segments = [s for s in self.split_segments() if s["name"] != b"__DATA_SPTM"]
        row = validator.profile_arithmetic(segments, len(self.original), True)
        self.assertEqual(row["selected_start_role"], "__TEXT_EXEC")
        self.assertEqual(row["selected_start_minus_text_bytes"], 0x14000)
        self.assertIsNone(row["text_exec_minus_data_bytes"])

    def test_profile_true_optional_boot_uses_normal_extent(self):
        segments = [s for s in self.split_segments() if s["name"] != b"__TEXT_BOOT_EXEC"]
        row = validator.profile_arithmetic(segments, len(self.original), True)
        self.assertEqual(row["profile_text_exec_bytes"], 0x4000)
        self.assertIsNone(row["prelink_minus_boot_bytes"])

    def test_profile_both_modes_refuse_the_observed_swapped_data(self):
        segments = self.split_segments()
        owned, normal = segments[1:3]
        owned["offset"], normal["offset"] = 0xC000, 0x8000
        for profile in (False, True):
            with self.subTest(profile=profile), self.assertRaisesRegex(ValueError, "text-exec-minus-data"):
                validator.profile_arithmetic(segments, len(self.original), profile)

    def test_profile_each_difference_rejects_underflow(self):
        for profile, left_name, right_name, reason in (
                (True, b"__TEXT_EXEC", b"__TEXT_BOOT_EXEC", "boot-minus-text-exec"),
                (False, b"__TEXT", b"__PRELINK_INFO", "selected-minus-text"),
                (False, b"__PRELINK_INFO", b"__LINKEDIT", "linkedit-minus-prelink"),
                (False, b"__DATA_SPTM", b"__TEXT_EXEC", "text-exec-minus-data"),
                (False, b"__TEXT_BOOT_EXEC", b"__PRELINK_INFO", "prelink-minus-boot")):
            segments = self.split_segments()
            left = next(s for s in segments if s["name"] == left_name)
            right = next(s for s in segments if s["name"] == right_name)
            left["offset"], right["offset"] = right["offset"], left["offset"]
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                validator.profile_arithmetic(segments, 0x40000, profile)

    def test_metadata_binds_recovered_payload_without_external_payload(self):
        data = self.changed(); data[0x1A000] ^= 1
        self.refuse(data, "recovered payload/metadata binding mismatch")
        self.assertEqual(validator.validate(self.original)["recovered_payload_sha256"],
                         hashlib.sha256(self.payload).hexdigest())

    def test_shifted_prelink_xml_cannot_hide_arbitrary_prefix_bytes(self):
        data = self.changed()
        info = segment(data, b"__PRELINK_INFO", 0x4000) + 72
        size = struct.unpack_from("<Q", data, info + 40)[0]
        metadata = bytes(data[0x28000:0x28000 + size])
        # Both headers still agree; the XML and section VA/file mapping remain
        # internally valid. The old profile admitted the unchecked prefix.
        for header in (0, 0x4000):
            section = segment(data, b"__PRELINK_INFO", header) + 72
            va = struct.unpack_from("<Q", data, section + 32)[0]
            struct.pack_into("<Q", data, section + 32, va + 16)
            struct.pack_into("<I", data, section + 48, 0x28010)
        data[0x28010:0x28010 + size] = metadata
        data[0x28000:0x28010] = b"unbounded-prefix"
        self.assertEqual(plistlib.loads(data[0x28010:0x28010 + size]),
                         plistlib.loads(metadata))
        self.refuse(data, "prelink section must start at metadata segment boundary")


    def test_metadata_binding_itself_cannot_be_mutated(self):
        data = self.changed()
        info = segment(data, b"__PRELINK_INFO", 0x4000) + 72
        size = struct.unpack_from("<Q", data, info + 40)[0]
        metadata = plistlib.loads(data[0x28000:0x28000 + size])
        metadata["_PrelinkKCID"] = bytes(16)
        encoded = plistlib.dumps(metadata, fmt=plistlib.FMT_XML)
        self.assertEqual(len(encoded), size)
        data[0x28000:0x28000 + size] = encoded
        self.refuse(data, "recovered payload/metadata binding mismatch")

    def test_supplied_payload_header_and_owned_bytes_are_checked(self):
        for position in (0, 0x3FFF, 0x4000, 0xFFFF):
            payload = bytearray(self.payload); payload[position] = 1
            self.refuse(self.original, "invalid supplied original", bytes(payload))


if __name__ == "__main__":
    unittest.main(verbosity=2)
