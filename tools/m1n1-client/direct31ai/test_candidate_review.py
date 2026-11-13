#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic data only. Test-scoped identities never relax the production CLI."""
import copy
import gzip
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec);sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tool = load("candidate31ai_tests", HERE / "candidate_review.py")
# Original independent MIT metadata encoder, not the upstream wrapper.
encoder = load("candidate31ai_encoder",
               REPO / "kernel/experiments/direct31ai/transport/test_extend_exec.py")
diagnostic = load("candidate31ai_test_diag",
                  REPO / "kernel/experiments/direct31ai/diagnostic/package.py")


class Candidate(unittest.TestCase):
    def setUp(self):
        self.ext = encoder.adapter
        self.image = encoder.fixtures.image_fixture()
        self.dtb = encoder.fixtures.tree_fixture()
        self.initrd = encoder.fixtures.ram.build(encoder.fixtures.elf_fixture())
        self.baseline = encoder.synthetic_baseline()
        self.payload = self.ext.inline.make_payload(self.image, self.dtb, self.initrd)
        self.raw = self.baseline + self.payload
        patches = [mock.patch.object(tool, "BASELINE", tool.sha(self.baseline)),
                   mock.patch.object(tool, "BASELINE_BYTES", len(self.baseline)),
                   mock.patch.object(tool, "RAW_BYTES", len(self.raw)),
                   mock.patch.object(tool, "RAW_SHA256", tool.sha(self.raw)),
                   mock.patch.object(self.ext.inline, "BASELINE_SHA256", tool.sha(self.baseline)),
                   mock.patch.object(self.ext.pad, "CODE_SIZE", 0x40000)]
        for patch in patches:
            patch.start();self.addCleanup(patch.stop)
        source = encoder.fixture_wrapper(self.raw)
        head, tail, growth, _ = self.ext.plan(source, self.raw, self.image, self.dtb, self.initrd)
        self.data = head + bytes(growth) + tail
        self.info = self.ext.pad.inspect(self.data)
        prefix = diagnostic.p.ROOT
        self.files = {prefix + "linux/Image": self.image,
                      prefix + "linux/t6050-j716c-diagnostic.dtb": self.dtb,
                      prefix + "diagnostic/initramfs.cpio.gz": self.initrd}
        self.directory = tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / tool.FILENAME
        self.compressed = gzip.compress(self.data, mtime=0)
        self.path.write_bytes(self.compressed)
        self.manifest = {
            "schema": tool.SCHEMA, "target": tool.TARGET.copy(),
            "delivery": "SAME_USER_LOCAL_HANDOFF_ONLY", "native_authorized": False,
            "restart_ready": False, "firmware_change_authorized": False,
            "public_binary_release": False, "glibc_public_source_closure": "INCOMPLETE",
            "upstream_aura_commit": tool.COMMIT, "baseline_aura_raw_sha256": tool.BASELINE,
            "diagnostic_manifest_sha256": "c" * 64,
            "source_sha256": {name: tool.FROZEN_PAD if name.endswith("pad_boot.py")
                              else "a" * 64 for name in tool.SOURCE_FILES},
            "candidate": {"filename": tool.FILENAME, "compressed_bytes": len(self.compressed),
                          "compressed_sha256": tool.sha(self.compressed),
                          "expanded_bytes": len(self.data), "expanded_sha256": tool.sha(self.data),
                          "raw_inline_bytes": len(self.raw), "raw_inline_sha256": tool.sha(self.raw)},
        }
        self.c = self.manifest["candidate"]

    def inspect(self, data=None, files=None):
        return tool.inspect_candidate(self.data if data is None else data, self.c,
                                      self.files if files is None else files,
                                      diagnostic, self.ext)

    def compressed_read(self, encoded):
        self.path.write_bytes(encoded)
        c = dict(self.c, compressed_bytes=len(encoded), compressed_sha256=tool.sha(encoded))
        return tool.read_candidate(self.path, c)

    def mutate(self, offset, value, width=4):
        data = bytearray(self.data)
        struct.pack_into("<I" if width == 4 else "<Q", data, offset, value)
        return bytes(data)

    def test_valid_manifest_and_candidate(self):
        self.assertEqual(tool.validate_manifest(self.manifest), self.c)
        self.assertEqual(tool.read_candidate(self.path, self.c), self.data)
        result = self.inspect()
        self.assertTrue(result["exact_diagnostic_payload_verified"])
        self.assertEqual(result["segment_count"], 6)
        self.assertEqual(result["expected_kcbz"], 0)

    def test_false_flags_are_strict_booleans(self):
        for key in ("native_authorized", "restart_ready", "firmware_change_authorized",
                    "public_binary_release"):
            for value in (True, 0, "false", None):
                with self.subTest(key=key, value=value):
                    m = copy.deepcopy(self.manifest);m[key] = value
                    with self.assertRaises(tool.Refusal):tool.validate_manifest(m)

    def test_wrong_board_refused(self):
        self.manifest["target"]["board"] = "j813"
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)

    def test_unknown_private_metadata_refused(self):
        self.manifest["serial"] = "SYNTHETIC_PRIVATE_MARKER"
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)

    def test_unknown_candidate_metadata_refused(self):
        self.c["personal_path"] = "SYNTHETIC_PRIVATE_MARKER"
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)

    def test_local_source_closure_must_not_claim_public_release(self):
        self.manifest["glibc_public_source_closure"] = "COMPLETE"
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)

    def test_wrong_baseline_or_commit_refused(self):
        for key in ("baseline_aura_raw_sha256", "upstream_aura_commit"):
            m = copy.deepcopy(self.manifest);m[key] = "0" * 64
            with self.assertRaises(tool.Refusal):tool.validate_manifest(m)

    def test_frozen_reader_cannot_be_relabelled(self):
        self.manifest["source_sha256"]["kernel/experiments/direct31ah/aura/pad_boot.py"] = "b" * 64
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)

    def test_source_inventory_is_exact(self):
        self.manifest["source_sha256"]["../unexpected.py"] = "b" * 64
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)

    def test_numeric_digest_or_boolean_length_refused(self):
        self.c["compressed_sha256"] = 10 ** 63
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)
        self.c["compressed_sha256"] = "b" * 64;self.c["expanded_bytes"] = True
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)

    def test_raw_input_pin_is_exact(self):
        self.c["raw_inline_bytes"] += 1
        with self.assertRaises(tool.Refusal):tool.validate_manifest(self.manifest)

    def test_changed_compressed_bytes_refused(self):
        self.path.write_bytes(self.compressed[:-1] + bytes([self.compressed[-1] ^ 1]))
        with self.assertRaises(tool.Refusal):tool.read_candidate(self.path, self.c)

    def test_rebound_crc_corruption_refused(self):
        data = bytearray(self.compressed);data[-8] ^= 1
        with self.assertRaises(tool.Refusal):self.compressed_read(data)

    def test_truncated_gzip_refused(self):
        with self.assertRaises(tool.Refusal):self.compressed_read(self.compressed[:-1])

    def test_hidden_concatenated_empty_member_refused(self):
        with self.assertRaises(tool.Refusal):self.compressed_read(self.compressed + gzip.compress(b""))

    def test_trailing_compressed_garbage_refused(self):
        with self.assertRaises(tool.Refusal):self.compressed_read(self.compressed + b"\0")

    def test_decompression_bound_refused_before_full_expansion(self):
        with mock.patch.object(tool, "MAX_EXPANDED", 1024):
            with self.assertRaises(tool.Refusal):tool.read_candidate(self.path, self.c)

    def test_compressed_file_bound(self):
        with mock.patch.object(tool, "MAX_COMPRESSED", 1):
            with self.assertRaises(tool.Refusal):tool.read_candidate(self.path, self.c)

    def test_expanded_hash_and_size_both_bind(self):
        for key, value in (("expanded_bytes", len(self.data) - 1), ("expanded_sha256", "b" * 64)):
            with self.subTest(key=key):
                c = dict(self.c);c[key] = value
                with self.assertRaises(tool.Refusal):tool.read_candidate(self.path, c)

    def test_symlink_input_refused(self):
        link = self.path.with_name("link.gz");link.symlink_to(self.path)
        with self.assertRaises(OSError):tool.read_candidate(link, self.c)

    def test_fifo_refused_without_blocking(self):
        pipe = self.path.with_name("fifo");os.mkfifo(pipe)
        with self.assertRaises(tool.Refusal):tool.read_candidate(pipe, self.c)

    def test_changed_raw_payload_rejected(self):
        data = bytearray(self.data);data[0x10000 + len(self.raw) - 1] ^= 1
        with self.assertRaises(tool.Refusal):self.inspect(bytes(data))

    def test_nonzero_execute_padding_rejected(self):
        data = bytearray(self.data);data[0x10000 + len(self.raw)] = 1
        with self.assertRaises(tool.Refusal):self.inspect(bytes(data))

    def test_inner_uuid_cannot_hide_different_raw_identity(self):
        pos = [pos for kind, pos, _ in self.info["commands"] if kind == 0x1b][-1]
        with self.assertRaises(ValueError):self.inspect(self.mutate(pos + 8, 0))

    def test_extra_prelink_identity_data_rejected(self):
        pos = self.info["segments"]["__PRELINK_INFO"]["off"]
        data = bytearray(self.data);data[pos:pos+5] = b"wrong"
        with self.assertRaises(ValueError):self.inspect(bytes(data))

    def test_entry_and_vector_are_fixed(self):
        pos = [pos for kind, pos, _ in self.info["commands"] if kind == 5][0]
        for register in (16, 32):
            with self.subTest(register=register):
                with self.assertRaises(ValueError):self.inspect(self.mutate(pos + 16 + register * 8, 0, 8))

    def test_boot_exec_segment_not_admitted(self):
        pos = self.info["code"]["command"]
        data = bytearray(self.data);data[pos+8:pos+24] = b"__TEXT_BOOT_EXEC\0"
        with self.assertRaises(ValueError):self.inspect(bytes(data))

    def test_exact_image_binding(self):
        files = dict(self.files);image = bytearray(self.image);image[-1] ^= 1
        files[diagnostic.p.ROOT+"linux/Image"] = bytes(image)
        with self.assertRaises(ValueError):self.inspect(files=files)

    def test_exact_initramfs_binding(self):
        files = dict(self.files);files[diagnostic.p.ROOT+"diagnostic/initramfs.cpio.gz"] += b"\0"
        with self.assertRaises(ValueError):self.inspect(files=files)

    def test_source_pin_failure_happens_before_helper_import(self):
        path = Path(self.directory.name) / "helper.py";path.write_text("raise RuntimeError('not imported')")
        with mock.patch.object(tool, "load_module") as loader:
            with self.assertRaises(tool.Refusal):tool.dependencies(path.parent, {path.name: "0" * 64})
            loader.assert_not_called()

    def test_diagnostic_manifest_digest_bound_before_dependencies(self):
        manifest_path = self.path.with_name("diagnostic.json");manifest_path.write_text("{}")
        with mock.patch.object(tool, "dependencies") as deps:
            with self.assertRaises(tool.Refusal):
                tool.review(self.manifest, self.path, manifest_path, self.path, REPO)
            deps.assert_not_called()

    def test_complete_reader_keeps_all_native_flags_false(self):
        dm = b"{}";manifest_path = self.path.with_name("diagnostic.json");manifest_path.write_bytes(dm)
        self.manifest["diagnostic_manifest_sha256"] = tool.sha(dm)
        d = mock.Mock();d.p = diagnostic.p
        d.review.return_value = {"package_sha256": "d" * 64}
        d.read_archive.return_value = (self.files, 1)
        with mock.patch.object(tool, "dependencies", return_value=(d, self.ext)):
            result = tool.review(self.manifest, self.path, manifest_path, self.path, REPO)
        self.assertEqual(result["status"], "OFFLINE_CANDIDATE_INTEGRITY_PASS")
        for key in ("extracted", "executed", "device_opened", "camera_opened", "native_authorized",
                    "native_ready", "public_binary_release", "kmutil_inspection_performed",
                    "native_execution_proven"):
            self.assertIs(result[key], False)
        d.review.assert_called_once()

    def test_duplicate_and_deep_json_refused(self):
        for data in (b'{"target":1,"target":2}', b"[" * 2000 + b"0" + b"]" * 2000):
            with self.subTest(size=len(data)):
                with self.assertRaises(tool.Refusal):tool.decode(data)


if __name__ == "__main__":
    unittest.main()
