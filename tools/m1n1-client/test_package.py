"""Offline intake regressions using synthetic payloads only."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "verify_package", Path(__file__).with_name("verify-package.py"))
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
REV = "57a9339ffd1876e78297b17d34dece8cff8fa1ba"


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("Image", "t6050-j716c.dtb", "initramfs.cpio.gz"):
            (self.root / name).write_bytes(b"synthetic fixture")
        (self.root / "m1n1-revision.txt").write_text(REV + "\n")
        self.manifest = self.root / "SHA256SUMS"
        self.manifest.write_text("".join(
            package.sha256(path) + "  " + path.name + "\n"
            for path in sorted(self.root.iterdir())))
        self.digest = package.sha256(self.manifest)

    def verify(self):
        return package.verify(self.root, REV, self.digest)

    def test_valid_receipt_does_not_authorize_boot(self):
        result = self.verify()
        self.assertEqual(len(result["files"]), 4)
        self.assertFalse(result["boot_authorized"])
        self.assertFalse(result["target_version_observed_live"])

    def test_corrupt_payload(self):
        (self.root / "Image").write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.verify()

    def test_wrong_manifest_digest(self):
        self.digest = "0" * 64
        with self.assertRaisesRegex(ValueError, "handoff digest"):
            self.verify()

    def test_wrong_target_revision(self):
        with self.assertRaisesRegex(ValueError, "target m1n1 revision"):
            package.verify(self.root, "0" * 40, self.digest)

    def test_missing_and_unlisted_files(self):
        (self.root / "extra").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "Unlisted"):
            self.verify()
        (self.root / "extra").unlink()
        (self.root / "Image").unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.verify()

    def test_symlink_rejected(self):
        (self.root / "Image").unlink()
        (self.root / "Image").symlink_to("t6050-j716c.dtb")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.verify()

    def test_traversal_rejected(self):
        self.manifest.write_text("0" * 64 + "  ../outside\n")
        self.digest = package.sha256(self.manifest)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
