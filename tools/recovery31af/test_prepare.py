#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic review-closure and output-refusal checks; no Recovery commands."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("prepare31af", HERE / "prepare.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ilinux31af-prepare-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.output = self.root / "build" / "reviewed-pages"
        self.security = "tools/m1n1-client/recovery-preflight.sh"
        self.manifest = {"schema": "ilinux-native31af-delivery-v1",
            "candidate": "ilinux-31af.macho", "candidate_bytes": 442368,
            "candidate_sha256": "1" * 64,
            "candidate_url": "https://example.invalid/ilinux-31af.macho",
            "files": {"ilinux-31af.macho": {"bytes": 442368, "sha256": "1" * 64}}}
        for name, data in ((prepare.MANIFEST, json.dumps(self.manifest).encode()),
                           (prepare.RENDERER, (HERE / "write_render.py").read_bytes()),
                           ("tools/recovery31af/prepare.py", (HERE / "prepare.py").read_bytes()),
                           (self.security, b"original synthetic policy guard\n")):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.names = sorted(prepare.REQUIRED | {self.security})
        self.repin()

    def repin(self):
        inventory = "".join(hashlib.sha256((self.root / name).read_bytes()).hexdigest() +
                            "  " + name + "\n" for name in self.names)
        (self.root / prepare.PINS).write_text(inventory)

    def write_manifest(self):
        (self.root / prepare.MANIFEST).write_text(json.dumps(self.manifest))
        self.repin()

    def refuse(self, pattern=".", output=None):
        destination = output or self.output
        with mock.patch.object(prepare, "load_renderer") as load:
            with self.assertRaisesRegex(ValueError, pattern):
                prepare.prepare(destination, self.root)
            load.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_reviewed_manifest_renders_complete_independent_blocks(self):
        report = prepare.prepare(self.output, self.root)
        self.assertEqual(sorted(p.name for p in self.output.iterdir()),
            ["install-paste.txt", "profile.json", "recovery.html", "render.json", "rollback-paste.txt"])
        for phase in ("install", "rollback"):
            block = (self.output / (phase + "-paste.txt")).read_text()
            self.assertIn("base_guard", block)
            self.assertIn("</dev/tty", block)
            self.assertIn("ILINUX31AF_" + phase.upper() + "_END\n", block)
            self.assertEqual(block.count("/usr/bin/kmutil configure-boot"), 1)
        self.assertNotIn("--raw", (self.output / "install-paste.txt").read_text())
        self.assertIn("--raw --entry-point 2048 --lowest-virtual-address 0",
                      (self.output / "rollback-paste.txt").read_text())
        self.assertEqual(json.loads((self.output / "profile.json").read_text()),
                         prepare.profile_from_manifest((self.root / prepare.MANIFEST).read_bytes()))
        self.assertEqual(json.loads((self.output / "render.json").read_text()), report)
        for name, digest in report["files"].items():
            content = (self.output / name).read_bytes()
            self.assertEqual(digest, {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        self.assertEqual(report["verified_source_files"], 4)
        self.assertFalse(report["network_used"])
        self.assertEqual(report["execution"], "NOT_RUN")

    def test_security_pin_failure_precedes_renderer_and_output(self):
        (self.root / self.security).write_text("changed security guard\n")
        self.refuse("source SHA-256 mismatch")

    def test_renderer_pin_failure_precedes_import(self):
        (self.root / prepare.RENDERER).write_text("raise AssertionError('must never import')\n")
        self.refuse("source SHA-256 mismatch")

    def test_manifest_pin_failure_is_refused(self):
        (self.root / prepare.MANIFEST).write_text("{}")
        self.refuse("source SHA-256 mismatch")

    def test_inventory_rejects_missing_required_duplicate_self_and_bad_lines(self):
        good = (self.root / prepare.PINS).read_text()
        for bad in ("", good + good.splitlines()[0] + "\n",
                    "0" * 64 + "  " + prepare.PINS + "\n", "invalid\n",
                    "\n".join(line for line in good.splitlines() if prepare.MANIFEST not in line) + "\n"):
            with self.subTest(inventory=bad):
                (self.root / prepare.PINS).write_text(bad)
                self.refuse()

    def test_source_traversal_and_symlink_are_refused(self):
        good = (self.root / prepare.PINS).read_text()
        for name in ("../outside", "/outside", "tools/../outside", "tools//outside", "./outside"):
            (self.root / prepare.PINS).write_text(good + "0" * 64 + "  " + name + "\n")
            self.refuse("unsafe source path")
        (self.root / prepare.PINS).write_text(good)
        security = self.root / self.security
        security.unlink()
        security.symlink_to(self.root / prepare.MANIFEST)
        self.refuse("source symlink")

    def test_manifest_candidate_binding_and_schema_are_required(self):
        self.manifest["files"]["ilinux-31af.macho"]["sha256"] = "2" * 64
        self.write_manifest()
        self.refuse("candidate disagrees")
        self.manifest["schema"] = "ilinux-native31ad-delivery-v1"
        self.write_manifest()
        self.refuse("31AF delivery manifest")

    def test_manifest_duplicate_keys_are_refused(self):
        (self.root / prepare.MANIFEST).write_text('{"schema":"one","schema":"two"}')
        self.repin()
        self.refuse("duplicate manifest key")

    def test_invalid_candidate_profile_creates_no_output(self):
        self.manifest["candidate_url"] = "https://user:secret@example.invalid/image"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "credentials"):
            prepare.prepare(self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_output_outside_build_existing_and_symlink_paths_are_refused(self):
        for path in (self.root / "outside", self.root / "build",
                     self.root / "build" / ".." / "outside"):
            with self.subTest(path=path):
                self.refuse("output", path)
        self.output.mkdir(parents=True)
        (self.output / "keep").write_bytes(b"untouched")
        with self.assertRaisesRegex(ValueError, "absent directory"):
            prepare.prepare(self.output, self.root)
        self.assertEqual((self.output / "keep").read_bytes(), b"untouched")
        alias = self.root / "build" / "alias"
        alias.symlink_to(self.root / "elsewhere")
        with self.assertRaisesRegex(ValueError, "symlinks"):
            prepare.prepare(alias / "pages", self.root)
        self.assertFalse((self.root / "elsewhere").exists())

    def test_relative_output_uses_repository_root(self):
        prepare.prepare(Path("build/relative-pages"), self.root)
        self.assertTrue((self.root / "build/relative-pages/render.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
