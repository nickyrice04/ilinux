#!/usr/bin/env python3
"""Synthetic archive intake tests; never opens USB or a real boot image."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("intake", Path(__file__).with_name("verify-two-stage.py"))
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)


class Intake(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.s1, self.s2 = self.root / "stage1.gz", self.root / "stage2.zst"
        self.s2.write_bytes(b"synthetic root")
        self.pin = dict(size=self.s2.stat().st_size, sha256=hashlib.sha256(self.s2.read_bytes()).hexdigest(),
                        image_sha256="a" * 64, entries=12, unpacked_bytes_16k=65536)
        self.archive()
        self.records()

    def archive(self, extra=""):
        data = ("\n".join("%s=%s" % item for item in self.pin.items()) + "\n" + extra).encode()
        with tarfile.open(self.s1, "w:gz") as archive:
            member = tarfile.TarInfo("etc/ilinux/stage2-pin")
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))

    def records(self):
        for path, profile, image in (("ramroot-manifest.json", "ramroot", self.s1),
                                     ("omarchy-root-manifest.json", "omarchy", self.s2)):
            value = dict(schema=1, profile=profile, size=image.stat().st_size,
                         sha256=hashlib.sha256(image.read_bytes()).hexdigest(), image_sha256="a"*64)
            if profile == "ramroot":
                value["stage2"] = self.pin.copy()
            (self.root / path).write_text(json.dumps(value))

    def verify(self):
        return intake.verify(self.s1, self.s2, self.root)

    def test_matching_pair_and_embedded_pin(self):
        result = self.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stage2"], self.pin)
        self.assertTrue(result["read_only"])

    def test_corruption_and_truncation_refused_before_tar(self):
        for content in (b"synthetic roox", b"short"):
            with self.subTest(content=content), patch.object(intake.subprocess, "run") as tar:
                self.s2.write_bytes(content)
                with self.assertRaises(ValueError):
                    self.verify()
                tar.assert_not_called()

    def test_wrong_root_in_authentic_stage_one(self):
        self.pin["sha256"] = "b"*64
        self.archive()
        self.records()
        with self.assertRaisesRegex(ValueError, "different root"):
            self.verify()

    def test_same_images_but_kernel_metadata_mismatch(self):
        path = self.root / "omarchy-root-manifest.json"
        value = json.loads(path.read_text())
        value["image_sha256"] = "c"*64
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "different kernel"):
            self.verify()

    def test_duplicate_embedded_pin_is_refused(self):
        self.archive("size=999\n")
        self.records()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.verify()

    def test_unpacked_metadata_drift_is_refused(self):
        path = self.root / "ramroot-manifest.json"
        value = json.loads(path.read_text())
        value["stage2"]["entries"] += 1
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "reviewed stage-two metadata"):
            self.verify()

    def test_symlink_is_refused(self):
        alias = self.root / "alias"
        alias.symlink_to(self.s2)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            intake.verify(self.s1, alias, self.root)

    def test_manifest_and_pin_fields_fail_closed(self):
        for value in (True, 0, -1, "13"):
            with self.subTest(value=value):
                path = self.root / "omarchy-root-manifest.json"
                manifest = json.loads(path.read_text())
                manifest["size"] = value
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, "size"):
                    self.verify()
        with self.assertRaises(ValueError):
            intake.parse_pin("size=12\nentries=1\nunpacked_bytes_16k=1\nsha256=bad\n")


if __name__ == "__main__":
    unittest.main()
