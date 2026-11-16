#!/usr/bin/env python3
"""Pure bounded-format and fake-IOKit tests; no host framework is loaded."""

import contextlib
import ctypes
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location(
    "firmware_versions31ay", Path(__file__).with_name("read_versions.py")
)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class FakeCF:
    def __init__(self, properties):
        self.properties = properties
        self.names = {}
        self.buffers = {}
        self.released = []
        self.pointer_reads = []
        self.next_key = 100

    def CFStringCreateWithCString(self, allocator, name, encoding):
        self.next_key += 1
        self.names[self.next_key] = name
        return self.next_key

    def CFGetTypeID(self, value):
        return self.properties[value][0]

    def CFDataGetTypeID(self):
        return 1

    def CFStringGetTypeID(self):
        return 2

    def CFDataGetLength(self, value):
        return len(self.properties[value][1])

    def CFDataGetBytePtr(self, value):
        self.pointer_reads.append(value)
        self.buffers[value] = ctypes.create_string_buffer(self.properties[value][1])
        return ctypes.cast(self.buffers[value], ctypes.POINTER(ctypes.c_uint8))

    def CFStringGetLength(self, value):
        return len(self.properties[value][1].decode("utf8"))

    def CFStringGetCString(self, value, buffer, count, encoding):
        payload = self.properties[value][1] + b"\0"
        if len(payload) > count:
            return 0
        ctypes.memmove(buffer, payload, len(payload))
        return 1

    def CFRelease(self, value):
        self.released.append(value)


class FakeIO:
    def __init__(self, cf, values=None, entry=42):
        self.cf = cf
        self.entry = entry
        self.values = values if values is not None else [11, 12]
        self.paths = []
        self.keys = []
        self.released = []

    def IORegistryEntryFromPath(self, port, path):
        self.paths.append((port, path))
        return self.entry

    def IORegistryEntryCreateCFProperty(self, entry, key, allocator, options):
        self.keys.append((entry, self.cf.names[key], allocator, options))
        return self.values[len(self.keys) - 1]

    def IOObjectRelease(self, value):
        self.released.append(value)
        return 0


def fake_apis(first=(1, b"mBoot-20457.41.3\0"),
              second=(1, b"iBoot-20457.41.3\0"), **kwargs):
    cf = FakeCF({11: first, 12: second})
    return cf, FakeIO(cf, **kwargs)


class FormatTests(unittest.TestCase):
    def test_shape_metadata_never_expands_numeric_admission(self):
        for raw, field in ((b"mBoot-1.2\0\0", "numeric_version_if_nul_padding_removed"),
                           (b"mBoot-1.2~3\0", "numeric_version_with_build_suffix")):
            with self.subTest(field=field):
                self.assertEqual(reader.parse_version(raw), reader.UNKNOWN)
                shape = reader._shape("CFDATA", len(raw), raw)
                self.assertTrue(shape[field])
                self.assertFalse(shape["strict_numeric_version"])

    def test_shape_metadata_emits_no_rejected_content(self):
        raw = b"unstructured-private-looking-value\0"
        shape = reader._shape("CFDATA", len(raw), raw)
        self.assertEqual(shape["nul_count"], 1)
        self.assertNotIn(raw[:-1].decode(), json.dumps(shape))
        self.assertEqual(reader._shape("CFDATA", 130)["bounded_length"], "OUT_OF_BOUNDS")

    def test_admits_only_bounded_generic_numeric_versions(self):
        for value in (b"mBoot-20457.41.3", b"iBoot-11881.141.114\0",
                      b"mBoot-20457.60.65.0.1", b"iBoot-1.0"):
            with self.subTest(value=value):
                self.assertEqual(reader.parse_version(value), value.rstrip(b"\0").decode())

    def test_refuses_private_or_unstructured_strings(self):
        for value in (b"serial-number", b"00000000-0000-4000-8000-000000000000",
                      b"Mac17,6", b"boot-policy", b"27.2.1", b"20457.41.3",
                      b"https://example.invalid", b"mBoot-1.2;other"):
            with self.subTest(value=value):
                self.assertEqual(reader.parse_version(value), reader.UNKNOWN)

    def test_refuses_noncanonical_or_malformed_data(self):
        for value in (b"", b"mBoot-1", b"mBoot-1.", b"mBoot-01.2",
                      b"mBoot-1.02", b"mBoot--1.2", b"mBoot-1.2\n",
                      b" mBoot-1.2", b"mBoot-1.2\0\0", b"mBoot-1\0.2",
                      b"mBoot-1.2\0secret", b"mBoot-1.2\xff", b"mBoot-1.2/3",
                      b"mBoot-1.2.3.4.5.6.7.8.9", b"mBoot-12345678901.2",
                      b"mBoot-1.2" + b"0" * 129, "mBoot-1.2", None):
            with self.subTest(value=value):
                self.assertEqual(reader.parse_version(value), reader.UNKNOWN)


class ScopeTests(unittest.TestCase):
    def test_exactly_one_path_two_properties_and_releases(self):
        cf, io_api = fake_apis()
        observed = reader.read_versions((cf, io_api), platform="darwin")
        self.assertEqual(observed["status"], "OBSERVED")
        self.assertEqual(io_api.paths, [(0, b"IODeviceTree:/chosen")])
        self.assertEqual(io_api.keys, [(42, b"firmware-version", None, 0),
                                       (42, b"system-firmware-version", None, 0)])
        self.assertCountEqual(cf.released, [101, 11, 102, 12])
        self.assertEqual(io_api.released, [42])
        self.assertFalse(observed["lab_firmware_queried"])
        self.assertFalse(observed["settings_changed"])

    def test_unknown_property_cannot_be_requested(self):
        cf, io_api = fake_apis()
        self.assertEqual(reader._property_version(cf, io_api, 42, b"serial-number"),
                         reader.UNKNOWN)
        self.assertEqual(io_api.keys, [])
        self.assertEqual(cf.names, {})

    def test_unsupported_platform_loads_nothing(self):
        with mock.patch.object(reader, "load_apis", side_effect=AssertionError):
            self.assertEqual(reader.read_versions(platform="linux")["failure"],
                             "PLATFORM_UNSUPPORTED")

    def test_api_load_exception_does_not_leak_exception_text(self):
        with mock.patch.object(reader, "load_apis", side_effect=OSError("secret")):
            observed = reader.read_versions(platform="darwin")
        self.assertEqual(observed["failure"], "API_UNAVAILABLE")
        self.assertNotIn("secret", json.dumps(observed))

    def test_missing_chosen_makes_no_property_calls(self):
        cf, io_api = fake_apis(entry=0)
        self.assertEqual(reader.read_versions((cf, io_api), platform="darwin")["failure"],
                         "CHOSEN_UNAVAILABLE")
        self.assertEqual(io_api.keys, [])
        self.assertEqual(io_api.released, [])

    def test_missing_property_has_fixed_partial_result(self):
        cf, io_api = fake_apis(values=[11, None])
        observed = reader.read_versions((cf, io_api), platform="darwin")
        self.assertEqual(observed["status"], "PARTIAL")
        self.assertEqual(observed["system_firmware_version"], reader.UNKNOWN)
        self.assertCountEqual(cf.released, [101, 11, 102])
        self.assertEqual(io_api.released, [42])

    def test_cfstring_versions_are_admitted(self):
        observed = reader.read_versions(fake_apis(
            first=(2, b"mBoot-20457.41.3"), second=(2, b"iBoot-20457.41.3")
        ), platform="darwin")
        self.assertEqual(observed["status"], "OBSERVED")

    def test_cfstring_embedded_nul_never_truncates_into_valid_version(self):
        observed = reader.read_versions(fake_apis(first=(2, b"mBoot-20457.41.3\0secret")),
                                        platform="darwin")
        self.assertEqual(observed["os_firmware_version"], reader.UNKNOWN)

    def test_oversized_cfdata_never_reads_its_pointer(self):
        cf, io_api = fake_apis(first=(1, b"x" * 130))
        observed = reader.read_versions((cf, io_api), platform="darwin")
        self.assertEqual(observed["os_firmware_version"], reader.UNKNOWN)
        self.assertEqual(cf.pointer_reads, [12])
        self.assertEqual(observed["property_shapes"]["os_firmware"]["bounded_length"],
                         "OUT_OF_BOUNDS")

    def test_unsupported_cf_type_never_reads_its_pointer(self):
        cf, io_api = fake_apis(first=(7, b"mBoot-20457.41.3"))
        observed = reader.read_versions((cf, io_api), platform="darwin")
        self.assertEqual(observed["os_firmware_version"], reader.UNKNOWN)
        self.assertEqual(cf.pointer_reads, [12])
        self.assertEqual(observed["property_shapes"]["os_firmware"]["type"], "OTHER")

    def test_cfdata_shape_diagnoses_padding_without_raw_output(self):
        cf, io_api = fake_apis(first=(1, b"mBoot-1.2\0\0"))
        observed = reader.read_versions((cf, io_api), platform="darwin")
        shape = observed["property_shapes"]["os_firmware"]
        self.assertEqual(observed["os_firmware_version"], reader.UNKNOWN)
        self.assertEqual(shape["type"], "CFDATA")
        self.assertEqual(shape["nul_count"], 2)
        self.assertEqual(shape["trailing_nul_count"], 2)
        self.assertTrue(shape["numeric_version_if_nul_padding_removed"])
        self.assertNotIn("mBoot-1.2", json.dumps(observed))

    def test_invalid_strings_never_appear_in_output(self):
        raw = b"private-unexpected-content"
        observed = reader.read_versions(fake_apis(first=(1, raw)), platform="darwin")
        self.assertNotIn(raw.decode(), json.dumps(observed))

    def test_failure_releases_key_property_and_entry(self):
        cf, io_api = fake_apis()
        cf.CFGetTypeID = mock.Mock(side_effect=ValueError("private-content"))
        observed = reader.read_versions((cf, io_api), platform="darwin")
        self.assertEqual(observed["failure"], "READ_UNAVAILABLE")
        self.assertCountEqual(cf.released, [11, 101])
        self.assertEqual(io_api.released, [42])
        self.assertNotIn("private-content", json.dumps(observed))

    def test_arbitrary_cli_argument_never_queries_host(self):
        output = io.StringIO()
        with mock.patch.object(reader, "read_versions", side_effect=AssertionError), \
             contextlib.redirect_stdout(output):
            self.assertEqual(reader.main(["--serial-number"]), 2)
        self.assertEqual(json.loads(output.getvalue())["failure"], "NO_ARGUMENTS_ACCEPTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
