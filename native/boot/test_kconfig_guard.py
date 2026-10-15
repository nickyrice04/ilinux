"""kernel.config provenance: a package ships the config embedded in its Image."""
import gzip
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kconfig_guard as kg  # noqa: E402

BUILD = HERE.parents[1] / "build"
PACKAGES = {"ilinux-j716c-boot021": BUILD / "native-boot-delivery-check/ilinux-j716c-boot021"}
PACKAGES.update({"ilinux-j716c-boot%03d" % n: BUILD / ("native-boot%03d/verified" % n)
                 for n in (22, 24, 25, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36)})
RUSTC_LINES = ["RUSTC_HAS_FILE_AS_C_STR", "RUSTC_HAS_FILE_WITH_NUL", "RUSTC_HAS_SPAN_FILE",
               "RUSTC_HAS_SUSPICIOUS_RUNTIME_SYMBOL_DEFINITIONS", "RUSTC_HAS_UNNECESSARY_TRANSMUTES",
               "RUSTC_LLVM_MAJOR_VERSION", "RUSTC_LLVM_VERSION", "RUSTC_VERSION"]
CONFIG = b"#\n# Linux/arm64 Kernel Configuration\n#\nCONFIG_RUSTC_VERSION=0\nCONFIG_USB_GADGET=y\n# CONFIG_FTRACE is not set\n"


def image(config, extra=b""):
    return b"\0" * 4096 + kg.START + gzip.compress(config, mtime=0) + kg.END + b"\0" * 64 + extra


class SyntheticTests(unittest.TestCase):
    def test_roundtrip(self):
        self.assertEqual(kg.embedded_config(image(CONFIG)), CONFIG)

    def test_match_passes_for_any_package(self):
        self.assertEqual(kg.check("ilinux-j716c-boot036", image(CONFIG), CONFIG), [])
        self.assertEqual(kg.check("ilinux-j716c-boot030", image(CONFIG), CONFIG), [])

    def test_toolchain_drift_only_for_listed_packages(self):
        built = CONFIG.replace(b"RUSTC_VERSION=0", b"RUSTC_VERSION=109900")
        self.assertEqual(kg.check("ilinux-j716c-boot030", image(built), CONFIG), ["RUSTC_VERSION"])
        for package in ("ilinux-j716c-boot022", "ilinux-j716c-boot036", "ilinux-j716c-boot037"):
            with self.subTest(package=package), self.assertRaises(ValueError):
                kg.check(package, image(built), CONFIG)

    def test_real_option_drift_always_fails(self):
        built = CONFIG.replace(b"# CONFIG_FTRACE is not set", b"CONFIG_FTRACE=y")
        for package in ("ilinux-j716c-boot030", "ilinux-j716c-boot036"):
            with self.subTest(package=package), self.assertRaises(ValueError):
                kg.check(package, image(built), CONFIG)

    def test_malformed_images(self):
        cases = {
            "no embedded config": b"\0" * 4096,
            "unterminated": b"\0" * 64 + kg.START + gzip.compress(CONFIG),
            "two configs": image(CONFIG, extra=kg.START + gzip.compress(CONFIG) + kg.END),
            "marker without gzip": b"\0" * 64 + kg.START + b"plain" + kg.END,
        }
        for name, blob in cases.items():
            with self.subTest(case=name), self.assertRaises(ValueError):
                kg.check("ilinux-j716c-boot036", blob, CONFIG)

    def test_formatting_only_difference_fails(self):
        with self.assertRaises(ValueError):
            kg.check("ilinux-j716c-boot036", image(CONFIG), CONFIG + b"\n")


class RealPackageTests(unittest.TestCase):
    def test_every_local_package(self):
        found = {name: path for name, path in PACKAGES.items() if (path / "Image").is_file()}
        if not found:
            self.skipTest("no extracted packages in build/")
        drifted = set()
        for name, path in sorted(found.items()):
            with self.subTest(package=name):
                lines = kg.check(name, (path / "Image").read_bytes(), (path / "kernel.config").read_bytes())
                if lines:
                    drifted.add(name)
                    self.assertEqual(lines, RUSTC_LINES)
        # The DRIFTED list is exactly the set of packages that drift, no more.
        self.assertEqual(drifted, kg.DRIFTED & set(found))


if __name__ == "__main__":
    unittest.main()
