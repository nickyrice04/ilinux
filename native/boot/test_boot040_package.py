"""boot040 packaging: make-package.py rebuilds the package from its own verified files and
refuses every payload change except the Image (which must carry the DART fault-report
patch), /init and its source, which is pinned by digest.

Needs the extracted packages in build/ (boot039 as the baseline, boot038 for a CDC init,
boot040 itself); skipped otherwise.
"""
import gzip
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import control_channel as cc  # noqa: E402

BUILD = ROOT / "build"
B38, B39, B40 = (BUILD / ("native-boot%03d/verified" % n) for n in (38, 39, 40))
KEY = ROOT / "kernel/experiments/usb-gadget/authorized_keys"
PAYLOAD = ("Image", "t6050-j716c.dtb", "initramfs.cpio.gz", "kernel.config", "t6050-j716c-stage-b.dtb",
           "initramfs-stage-b.cpio.gz", "m1n1.bin", "m1n1-build-config.h", "m1n1-LICENSE",
           "m1n1-revision.txt", "diag-init.c", "toolchain.txt")
READY = all((d / "Image").is_file() for d in (B38, B39, B40)) and KEY.is_file()


def repack(tree, replace):
    """A newc cpio.gz of tree (cpio_entries form) with entries replaced, as job 041 packs it."""
    entries = dict(tree, **replace)
    out = bytearray()
    for i, name in enumerate(sorted(entries) + ["TRAILER!!!"]):
        mode, uid, gid, data = entries.get(name, (0, 0, 0, b""))
        raw = (("./" + name) if name != "TRAILER!!!" else name).encode() + b"\0"
        fields = (i + 1, mode, uid, gid, 1, 1760486400, len(data), 0, 0, 0, 0, len(raw), 0)
        out += b"070701" + b"".join(b"%08X" % v for v in fields) + raw
        out += b"\0" * (-len(out) % 4) + data
        out += b"\0" * (-len(out) % 4)
    return gzip.compress(bytes(out), mtime=0)


@unittest.skipUnless(READY, "boot038/039/040 not extracted in build/")
class Boot040PackageTests(unittest.TestCase):
    def package(self, change=None, previous=B39, key=KEY, extra=(), script=HERE / "make-package.py"):
        """Run make-package.py on boot040's verified files, changed by change(export)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            export = tmp / "out/export"
            export.mkdir(parents=True)
            for name in PAYLOAD:
                shutil.copyfile(B40 / name, export / name)
            if change:
                change(export)
            (tmp / "records").mkdir()
            args = [sys.executable, "-I", str(script), "--out", str(tmp / "out"),
                    "--destination", str(tmp / "dest"), "--name", "ilinux-j716c-boot040",
                    "--record-dir", str(tmp / "records")]
            if previous:
                args += ["--previous-package", str(previous)]
            if key:
                args += ["--authorized-key", str(key)]
            run = subprocess.run(args + list(extra), capture_output=True, text=True)
            archive = tmp / "dest/ilinux-j716c-boot040.tar.gz"
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
        published = (B40.parent / "SHA256SUMS").read_text().split()[0]
        self.assertEqual(digest, published)

    def test_rebuilds_after_init_c_moves_on(self):
        # The packager in a copy of the tree whose usb-gadget/init.c is no longer boot040's.
        with tempfile.TemporaryDirectory() as tree:
            tree = Path(tree)
            shutil.copytree(HERE, tree / "native/boot", ignore=shutil.ignore_patterns("__pycache__", "*.md"))
            init_c = tree / "kernel/experiments/usb-gadget/init.c"
            init_c.parent.mkdir(parents=True)
            init_c.write_bytes((B40 / "diag-init.c").read_bytes() + b"/* moved on */\n")
            run, digest = self.package(script=tree / "native/boot/make-package.py")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(digest, (B40.parent / "SHA256SUMS").read_text().split()[0])

    def test_other_init_source_is_refused(self):
        for name, source in (("boot039's", (B39 / "diag-init.c").read_bytes()),
                             ("one byte more", (B40 / "diag-init.c").read_bytes() + b"\n")):
            with self.subTest(source=name):
                def change(export, source=source):
                    (export / "diag-init.c").write_bytes(source)
                self.refused("diag-init.c is not the init.c boot040 was built with", change=change)

    def test_unpatched_image_is_refused(self):
        # boot039's Image: same config, no DART fault-report patch.
        def change(export):
            shutil.copyfile(B39 / "Image", export / "Image")
        self.refused("Image lacks the boot040 DART fault-report patch", change=change)

    def test_boot039_init_is_refused(self):
        # boot039's initramfs: the same gadget, an /init without the DART diagnostics.
        def change(export):
            shutil.copyfile(B39 / "initramfs-stage-b.cpio.gz", export / "initramfs-stage-b.cpio.gz")
        self.refused("/init lacks the boot040 DART diagnostics", change=change)

    def test_other_payload_changes_are_refused(self):
        # The DT and kernel.config meet earlier checks (embedded config, check_stage_b) first, so
        # for them any refusal will do; the Image is allowed to differ from boot039 and is pinned
        # instead; the others reach the job-020 originals or the baseline comparison.
        for name, why in (("toolchain.txt", "unexpected payload change: toolchain.txt"),
                          ("m1n1.bin", "unexpected payload change: m1n1.bin"),
                          ("kernel.config", ""), ("Image", "Image is not the boot040 Image job 041 built"),
                          ("t6050-j716c-stage-b.dtb", ""), ("t6050-j716c.dtb", ""),
                          ("initramfs.cpio.gz", "original job-020 artifact changed: initramfs.cpio.gz")):
            with self.subTest(file=name):
                def change(export, name=name):
                    blob = bytearray((export / name).read_bytes())
                    blob[-1] ^= 1
                    (export / name).write_bytes(bytes(blob))
                run, digest = self.package(change=change)
                self.assertNotEqual(run.returncode, 0)
                self.assertIsNone(digest)
                self.assertIn(why, run.stderr)

    def test_initramfs_beyond_init_is_refused(self):
        tree = cc.cpio_entries((B40 / "initramfs-stage-b.cpio.gz").read_bytes())
        mode, uid, gid, hosts = tree["etc/hosts"]

        def change(export):
            (export / "initramfs-stage-b.cpio.gz").write_bytes(
                repack(tree, {"etc/hosts": (mode, uid, gid, hosts + b"10.0.0.1 extra\n")}))
        self.refused("initramfs must differ in /init only", change=change)

    def test_cdc_init_is_refused(self):
        # boot038's initramfs: boot036's apart from an ACM + ECM /init.
        def change(export):
            shutil.copyfile(B38 / "initramfs-stage-b.cpio.gz", export / "initramfs-stage-b.cpio.gz")
        self.refused("/init does not set up functions/gser.GS0", change=change)

    def test_baseline_and_flags_are_required(self):
        self.refused("prior digest mismatch: initramfs-stage-b.cpio.gz", previous=B38)
        self.refused("boot040 needs --previous-package", previous=None)
        self.refused("boot040 needs --previous-package", key=None)

    def test_other_key_is_refused(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".pub") as other:
            other.write(KEY.read_bytes().replace(b"AAAA", b"BBBB", 1))
            other.flush()
            self.refused("authorized_keys must hold exactly the expected key", key=Path(other.name))


if __name__ == "__main__":
    unittest.main()
