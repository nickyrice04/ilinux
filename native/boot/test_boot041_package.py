"""boot041 packaging: make-package.py rebuilds the package from its own verified files and
refuses every payload change except the Stage-B DT (exactly boot040's plus both DART
instances per dwc3 core), /init and its source (pinned by digest). The Image must stay
boot040's byte for byte: the Omarchy root of omarchy-root-manifest.json is pinned to it.

Needs the extracted packages in build/ (boot040 as the baseline, boot039 for an older
initramfs, boot041 itself); skipped otherwise.
"""
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "kernel/experiments/usb-gadget-dt"))
import control_channel as cc  # noqa: E402
import fdtedit  # noqa: E402
from test_boot040_package import repack  # noqa: E402

BUILD = ROOT / "build"
B39, B40, B41 = (BUILD / ("native-boot%03d/verified" % n) for n in (39, 40, 41))
KEY = ROOT / "kernel/experiments/usb-gadget/authorized_keys"
PAYLOAD = ("Image", "t6050-j716c.dtb", "initramfs.cpio.gz", "kernel.config", "t6050-j716c-stage-b.dtb",
           "initramfs-stage-b.cpio.gz", "m1n1.bin", "m1n1-build-config.h", "m1n1-LICENSE",
           "m1n1-revision.txt", "diag-init.c", "toolchain.txt")
READY = all((d / "Image").is_file() for d in (B39, B40, B41)) and KEY.is_file()


def edited_dt(change):
    """boot041's Stage-B DT re-encoded after change(tree) (fdtedit keeps every other byte)."""
    tree = fdtedit.parse((B41 / "t6050-j716c-stage-b.dtb").read_bytes())
    change(tree)
    return fdtedit.encode(tree)


@unittest.skipUnless(READY, "boot039/040/041 not extracted in build/")
class Boot041PackageTests(unittest.TestCase):
    def package(self, change=None, previous=B40, key=KEY, script=HERE / "make-package.py"):
        """Run make-package.py on boot041's verified files, changed by change(export)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            export = tmp / "out/export"
            export.mkdir(parents=True)
            for name in PAYLOAD:
                shutil.copyfile(B41 / name, export / name)
            if change:
                change(export)
            (tmp / "records").mkdir()
            args = [sys.executable, "-I", str(script), "--out", str(tmp / "out"),
                    "--destination", str(tmp / "dest"), "--name", "ilinux-j716c-boot041",
                    "--record-dir", str(tmp / "records")]
            if previous:
                args += ["--previous-package", str(previous)]
            if key:
                args += ["--authorized-key", str(key)]
            run = subprocess.run(args, capture_output=True, text=True)
            archive = tmp / "dest/ilinux-j716c-boot041.tar.gz"
            digest = hashlib.sha256(archive.read_bytes()).hexdigest() if archive.is_file() else None
            return run, digest

    def refused(self, why, **kwargs):
        run, digest = self.package(**kwargs)
        self.assertNotEqual(run.returncode, 0, run.stdout)
        self.assertIsNone(digest)
        self.assertIn(why, run.stderr)

    def test_rebuilds_byte_identically(self):
        run, digest = self.package()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(digest, (B41.parent / "SHA256SUMS").read_text().split()[0])

    def test_only_the_dt_and_init_differ_from_boot040(self):
        differ = sorted(name for name in PAYLOAD
                        if (B40 / name).read_bytes() != (B41 / name).read_bytes())
        self.assertEqual(differ, ["diag-init.c", "initramfs-stage-b.cpio.gz", "t6050-j716c-stage-b.dtb"])
        cc.check_init_only_delta((B40 / "initramfs-stage-b.cpio.gz").read_bytes(),
                                 (B41 / "initramfs-stage-b.cpio.gz").read_bytes())

    def test_rebuilds_after_init_c_moves_on(self):
        with tempfile.TemporaryDirectory() as tree:
            tree = Path(tree)
            shutil.copytree(HERE, tree / "native/boot", ignore=shutil.ignore_patterns("__pycache__", "*.md"))
            init_c = tree / "kernel/experiments/usb-gadget/init.c"
            init_c.parent.mkdir(parents=True)
            init_c.write_bytes((B41 / "diag-init.c").read_bytes() + b"/* moved on */\n")
            run, digest = self.package(script=tree / "native/boot/make-package.py")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(digest, (B41.parent / "SHA256SUMS").read_text().split()[0])

    def test_image_must_stay_boot040s(self):
        # boot039's Image (no DART patch) and a boot040 Image with one byte flipped.
        def older(export):
            shutil.copyfile(B39 / "Image", export / "Image")

        def flipped(export):
            blob = bytearray((export / "Image").read_bytes())
            blob[-1] ^= 1
            (export / "Image").write_bytes(bytes(blob))
        for name, change in (("boot039's", older), ("one byte flipped", flipped)):
            with self.subTest(image=name):
                self.refused("unexpected payload change: Image", change=change)

    def test_dt_beyond_the_two_dart_delta_is_refused(self):
        dwc3, dart0 = "/soc/usb@2a2280000", "/soc/iommu@2a2f00000"
        changes = {
            "boot040's DT (no change)": lambda export: shutil.copyfile(
                B40 / "t6050-j716c-stage-b.dtb", export / "t6050-j716c-stage-b.dtb"),
            "instance 0 keeps its power domain": lambda t: t.node(dart0).set("power-domains", struct.pack(">I", 0x4c)),
            "instance 0 still disabled": lambda t: t.node(dart0).set("status", b"disabled\0"),
            "streams swapped": lambda t: t.node(dwc3).set("iommus", struct.pack(">4I", 0x6b, 1, 0x68, 0)),
            "both streams on both instances": lambda t: t.node(dwc3).set(
                "iommus", struct.pack(">8I", 0x6b, 0, 0x6b, 1, 0x68, 0, 0x68, 1)),
            "a DMA range on instance 0": lambda t: t.node(dart0).set("apple,dma-range", bytes(16)),
            "an unrelated property": lambda t: t.node("/chosen").set("ilinux,extra", b"\0"),
        }
        for name, change in changes.items():
            with self.subTest(dt=name):
                if name.startswith("boot040"):
                    self.refused("DART instance 0 phandle missing or invalid", change=change)
                    continue

                def write(export, change=change):
                    (export / "t6050-j716c-stage-b.dtb").write_bytes(edited_dt(change))
                self.refused("DT delta differs from the boot041 two-DART contract", change=write)

    def test_other_init_source_is_refused(self):
        for name, source in (("boot040's", (B40 / "diag-init.c").read_bytes()),
                             ("one byte more", (B41 / "diag-init.c").read_bytes() + b"\n")):
            with self.subTest(source=name):
                def change(export, source=source):
                    (export / "diag-init.c").write_bytes(source)
                self.refused("diag-init.c is not the init.c boot041 was built with", change=change)

    def test_boot040_init_is_refused(self):
        # boot040's initramfs: the same gadget and DART diagnostics, none of the two-DART lines.
        def change(export):
            shutil.copyfile(B40 / "initramfs-stage-b.cpio.gz", export / "initramfs-stage-b.cpio.gz")
        self.refused("/init lacks the boot041 two-DART lines", change=change)

    def test_initramfs_beyond_init_is_refused(self):
        tree = cc.cpio_entries((B41 / "initramfs-stage-b.cpio.gz").read_bytes())
        mode, uid, gid, hosts = tree["etc/hosts"]

        def change(export):
            (export / "initramfs-stage-b.cpio.gz").write_bytes(
                repack(tree, {"etc/hosts": (mode, uid, gid, hosts + b"10.0.0.1 extra\n")}))
        self.refused("initramfs must differ in /init only", change=change)

    def test_other_payload_changes_are_refused(self):
        for name, why in (("toolchain.txt", "unexpected payload change: toolchain.txt"),
                          ("m1n1.bin", "unexpected payload change: m1n1.bin"),
                          ("kernel.config", "kernel.config is not the config the Image was built with"),
                          ("t6050-j716c.dtb", "original job-020 artifact changed: t6050-j716c.dtb"),
                          ("initramfs.cpio.gz", "original job-020 artifact changed: initramfs.cpio.gz")):
            with self.subTest(file=name):
                def change(export, name=name):
                    blob = bytearray((export / name).read_bytes())
                    blob[-1] ^= 1
                    (export / name).write_bytes(bytes(blob))
                self.refused(why, change=change)

    def test_baseline_and_flags_are_required(self):
        # boot039's Stage-B DT equals boot040's; its initramfs does not.
        self.refused("prior digest mismatch: initramfs-stage-b.cpio.gz", previous=B39)
        self.refused("boot041 needs --previous-package", previous=None)
        self.refused("boot041 needs --previous-package", key=None)

    def test_other_key_is_refused(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".pub") as other:
            other.write(KEY.read_bytes().replace(b"AAAA", b"BBBB", 1))
            other.flush()
            self.refused("authorized_keys must hold exactly the expected key", key=Path(other.name))


if __name__ == "__main__":
    unittest.main()
