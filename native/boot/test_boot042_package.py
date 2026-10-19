"""boot042 packaging: make-package.py rebuilds the package from its own verified files and
refuses every payload change except the three of boot042_modules.py: job 050's Image, its
kernel.config (boot041's with the keyboard path and the storage drivers as modules) and the
Stage-B DT (boot041's plus the MTP nodes on streams 0-4, the NVMe node still disabled). /init,
its source, both initramfs, m1n1 and the generic files stay boot041's byte for byte.

Needs the extracted packages in build/ (boot040 for an older baseline, boot041 as the baseline,
boot042 itself); skipped otherwise.
"""
import hashlib
import json
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
import boot042_modules as R  # noqa: E402
import fdtedit  # noqa: E402

BUILD = ROOT / "build"
B40, B41, B42 = (BUILD / ("native-boot%03d/verified" % n) for n in (40, 41, 42))
KEY = ROOT / "kernel/experiments/usb-gadget/authorized_keys"
PAYLOAD = ("Image", "t6050-j716c.dtb", "initramfs.cpio.gz", "kernel.config", "t6050-j716c-stage-b.dtb",
           "initramfs-stage-b.cpio.gz", "m1n1.bin", "m1n1-build-config.h", "m1n1-LICENSE",
           "m1n1-revision.txt", "diag-init.c", "toolchain.txt")
READY = all((d / "Image").is_file() for d in (B40, B41, B42)) and KEY.is_file()
MTP, DART, NVME = "/soc/mtp@294600000", "/soc/iommu@294800000", "/soc/nvme@45dcc0000"
NAME = "ilinux-j716c-boot042"


def edited_dt(change):
    """boot042's Stage-B DT re-encoded after change(tree) (fdtedit keeps every other byte)."""
    tree = fdtedit.parse((B42 / "t6050-j716c-stage-b.dtb").read_bytes())
    change(tree)
    return fdtedit.encode(tree)


def streams(sids):
    def change(tree):
        node = tree.node(MTP)
        handle = node.get("iommus")[:4]
        node.set("iommus", b"".join(handle + struct.pack(">I", sid) for sid in sids))
    return change


@unittest.skipUnless(READY, "boot040/041/042 not extracted in build/")
class Boot042PackageTests(unittest.TestCase):
    def package(self, change=None, previous=B41, key=KEY):
        """Run make-package.py on boot042's verified files, changed by change(export)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            export = tmp / "out/export"
            export.mkdir(parents=True)
            for name in PAYLOAD:
                shutil.copyfile(B42 / name, export / name)
            if change:
                change(export)
            (tmp / "records").mkdir()
            args = [sys.executable, "-I", str(HERE / "make-package.py"), "--out", str(tmp / "out"),
                    "--destination", str(tmp / "dest"), "--name", NAME, "--record-dir", str(tmp / "records")]
            if previous:
                args += ["--previous-package", str(previous)]
            if key:
                args += ["--authorized-key", str(key)]
            run = subprocess.run(args, capture_output=True, text=True)
            archive = tmp / "dest" / (NAME + ".tar.gz")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest() if archive.is_file() else None
            record = tmp / "records/package-manifest.json"
            manifest = json.loads(record.read_text()) if record.is_file() else None
            return run, digest, manifest

    def refused(self, why, **kwargs):
        run, digest, _ = self.package(**kwargs)
        self.assertNotEqual(run.returncode, 0, run.stdout)
        self.assertIsNone(digest)
        self.assertIn(why, run.stderr)

    def test_rebuilds_byte_identically(self):
        run, digest, manifest = self.package()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(digest, (B42.parent / "SHA256SUMS").read_text().split()[0])
        self.assertEqual(manifest, json.loads((B42 / "package-manifest.json").read_text()))

    def test_manifest_records_the_contract(self):
        manifest = json.loads((B42 / "package-manifest.json").read_text())
        self.assertEqual(manifest["package"], NAME)
        self.assertFalse(manifest["native_tested"])
        modules = manifest["modules_instead_of_built_in"]
        self.assertEqual(modules["image_as_job_050"], R.IMAGE_SHA256)
        self.assertEqual(modules["config_delta"], {k: list(v) for k, v in R.CONFIG_DELTA.items()})
        self.assertEqual(manifest["mtp_input"]["stream_ids"], [0, 1, 2, 3, 4])
        self.assertEqual(manifest["mtp_input"]["modules_loaded_over_ssh"],
                         ["apple-rtkit-helper", "apple-dockchannel", "hid-apple", "dockchannel-hid"])
        self.assertTrue(manifest["linux_patches"].endswith("job-050"))
        self.assertEqual(manifest["files"]["Image"]["sha256"], R.IMAGE_SHA256)

    def test_only_the_image_config_and_dt_differ_from_boot041(self):
        differ = sorted(name for name in PAYLOAD
                        if (B41 / name).read_bytes() != (B42 / name).read_bytes())
        self.assertEqual(differ, ["Image", "kernel.config", "t6050-j716c-stage-b.dtb"])

    def test_image_must_be_job_050s(self):
        # boot041's Image with its own config (each other's match, the boot042 delta is missing),
        # and boot042's Image with one byte flipped past the embedded config.
        def boot041s(export):
            for name in ("Image", "kernel.config"):
                shutil.copyfile(B41 / name, export / name)

        def flipped(export):
            blob = bytearray((export / "Image").read_bytes())
            blob[-1] ^= 1
            (export / "Image").write_bytes(bytes(blob))
        self.refused("kernel config differs from the boot042 contract", change=boot041s)
        self.refused("Image is not job 050's boot042 build", change=flipped)

    def test_config_change_is_refused(self):
        # A config that is not the Image's own: NVMe built in, as boot041 had it.
        def change(export):
            text = (export / "kernel.config").read_text()
            self.assertIn("CONFIG_NVME_APPLE=m\n", text)
            (export / "kernel.config").write_text(text.replace("CONFIG_NVME_APPLE=m\n", "CONFIG_NVME_APPLE=y\n"))
        self.refused("kernel.config is not the config the Image was built with", change=change)

    def test_dt_beyond_the_mtp_delta_is_refused(self):
        def nvme_on(tree):
            tree.node(NVME).set("status", b"okay\0")
        changes = {
            "boot041's DT (no change)": ("boot042 Stage-B DT: phandle missing or invalid", lambda export: shutil.copyfile(
                B41 / "t6050-j716c-stage-b.dtb", export / "t6050-j716c-stage-b.dtb")),
            "the NVMe node enabled": ("storage or cpufreq enabled: " + NVME, nvme_on),
            "boot037's stream 1 only": ("boot042 Stage-B DT: DT delta differs", streams((1,))),
            "streams 1-4": ("boot042 Stage-B DT: DT delta differs", streams((1, 2, 3, 4))),
            "streams 0-5": ("boot042 Stage-B DT: DT delta differs", streams((0, 1, 2, 3, 4, 5))),
            "the MTP DART still disabled": ("boot042 Stage-B DT: DT delta differs",
                                            lambda t: t.node(DART).set("status", b"disabled\0")),
            "an unrelated property": ("boot042 Stage-B DT: DT delta differs",
                                      lambda t: t.node("/chosen").set("ilinux,extra", b"\0")),
        }
        for name, (why, change) in changes.items():
            with self.subTest(dt=name):
                if name.startswith("boot041"):
                    self.refused(why, change=change)
                    continue

                def write(export, change=change):
                    (export / "t6050-j716c-stage-b.dtb").write_bytes(edited_dt(change))
                self.refused(why, change=write)

    def test_other_payload_changes_are_refused(self):
        for name, why in (("toolchain.txt", "unexpected payload change: toolchain.txt"),
                          ("m1n1.bin", "unexpected payload change: m1n1.bin"),
                          ("diag-init.c", "unexpected payload change: diag-init.c"),
                          ("initramfs-stage-b.cpio.gz", "unexpected payload change: initramfs-stage-b.cpio.gz"),
                          ("t6050-j716c.dtb", "original job-020 artifact changed: t6050-j716c.dtb"),
                          ("initramfs.cpio.gz", "original job-020 artifact changed: initramfs.cpio.gz")):
            with self.subTest(file=name):
                def change(export, name=name):
                    blob = bytearray((export / name).read_bytes())
                    blob[-1] ^= 1
                    (export / name).write_bytes(bytes(blob))
                self.refused(why, change=change)

    def test_baseline_and_flags_are_required(self):
        # boot040's Stage-B DT is not boot041's (boot041 added the second DART per dwc3 core).
        self.refused("prior digest mismatch: t6050-j716c-stage-b.dtb", previous=B40)
        self.refused("boot042 needs --previous-package", previous=None)
        self.refused("boot042 needs --previous-package", key=None)

    def test_other_key_is_refused(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".pub") as other:
            other.write(KEY.read_bytes().replace(b"AAAA", b"BBBB", 1))
            other.flush()
            self.refused("authorized_keys must hold exactly the expected key", key=Path(other.name))


if __name__ == "__main__":
    unittest.main()
