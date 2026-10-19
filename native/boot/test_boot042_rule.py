"""boot042's contract (boot042_modules.py) on the real files, and the deviations it must refuse.

boot042's package is boot041's with exactly the Image, kernel.config and the Stage-B DT changed
(build/boot042/package, staged from build/native-boot041/verified and VM job 050's export). Needs those
in build/ and job 050's out/; skipped otherwise.
"""
import hashlib
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "kernel/experiments/usb-gadget-dt"))
import boot042_modules as R  # noqa: E402
import fdtedit  # noqa: E402
import kconfig_guard  # noqa: E402
from fdt import check_stage_b, properties  # noqa: E402

B41 = ROOT / "build/native-boot041/verified"
P42 = ROOT / "build/boot042/package/out/export"
PAYLOAD = ("Image", "t6050-j716c.dtb", "initramfs.cpio.gz", "kernel.config", "t6050-j716c-stage-b.dtb",
           "initramfs-stage-b.cpio.gz", "m1n1.bin", "m1n1-build-config.h", "m1n1-LICENSE",
           "m1n1-revision.txt", "diag-init.c", "toolchain.txt")
READY = (B41 / "Image").is_file() and (P42 / "Image").is_file()
MTP, DART, HID, NVME = "/soc/mtp@294600000", "/soc/iommu@294800000", "/soc/fifo@294b14000/input@8000", "/soc/nvme@45dcc0000"


def edited(change):
    tree = fdtedit.parse((P42 / "t6050-j716c-stage-b.dtb").read_bytes())
    change(tree)
    return fdtedit.encode(tree)


def iommus(tree, path, sids):
    node = tree.node(path)
    ph = node.get("iommus")[:4]
    node.set("iommus", b"".join(ph + sid.to_bytes(4, "big") for sid in sids))


@unittest.skipUnless(READY, "boot041 verified or the staged boot042 package not in build/")
class Boot042RuleTests(unittest.TestCase):
    def before(self):
        return properties((B41 / "t6050-j716c-stage-b.dtb").read_bytes())

    def test_real_files_pass(self):
        dt = (P42 / "t6050-j716c-stage-b.dtb").read_bytes()
        R.check_delta(self.before(), properties(dt))
        check_stage_b(dt)
        R.check_config((B41 / "kernel.config").read_text(), (P42 / "kernel.config").read_text())
        R.check_image((P42 / "Image").read_bytes())
        kconfig_guard.check("ilinux-j716c-boot042", (P42 / "Image").read_bytes(), (P42 / "kernel.config").read_bytes())

    def test_only_image_config_and_stage_b_dt_differ_from_boot041(self):
        differ = sorted(n for n in PAYLOAD if (B41 / n).read_bytes() != (P42 / n).read_bytes())
        self.assertEqual(differ, ["Image", "kernel.config", "t6050-j716c-stage-b.dtb"])

    def dt_refused(self, change, why):
        with self.assertRaises(ValueError) as caught:
            R.check_delta(self.before(), properties(edited(change)))
        self.assertIn(why, str(caught.exception))

    def test_dt_deviations_refused(self):
        self.dt_refused(lambda t: iommus(t, MTP, (1,)), "MTP contract")                 # boot037's stream 1 alone
        self.dt_refused(lambda t: iommus(t, HID, (0, 1, 2, 3)), "MTP contract")         # a stream missing
        self.dt_refused(lambda t: t.node(MTP).set("status", b"disabled\0"), "MTP contract")
        self.dt_refused(lambda t: t.node(DART).delete("apple,dma-range"), "MTP contract")
        self.dt_refused(lambda t: t.node("/aliases").delete("keyboard"), "MTP contract")
        self.dt_refused(lambda t: t.node("/soc/usb@2a2280000").set("iommus", b"\0\0\0\x6b\0\0\0\0"), "MTP contract")
        self.dt_refused(lambda t: t.node(NVME).delete("status"), "MTP contract")
        self.dt_refused(lambda t: t.node(MTP).set("apple,unexpected", b""), "MTP contract")

    def test_enabled_nvme_fails_the_launcher_check_too(self):
        with self.assertRaises(ValueError) as caught:
            check_stage_b(edited(lambda t: t.node(NVME).delete("status")))
        self.assertIn("storage or cpufreq enabled", str(caught.exception))

    def config_refused(self, edit, why):
        text = (P42 / "kernel.config").read_text()
        for old, new in edit:
            self.assertIn(old, text)
            text = text.replace(old, new)
        with self.assertRaises(ValueError) as caught:
            R.check_config((B41 / "kernel.config").read_text(), text)
        self.assertIn(why, str(caught.exception))

    def test_config_deviations_refused(self):
        self.config_refused([("CONFIG_NVME_APPLE=m", "CONFIG_NVME_APPLE=y")], "NVME_APPLE")
        self.config_refused([("CONFIG_APPLE_SART=m", "CONFIG_APPLE_SART=y")], "APPLE_SART")
        self.config_refused([("CONFIG_HID_DOCKCHANNEL=m", "CONFIG_HID_DOCKCHANNEL=y")], "HID_DOCKCHANNEL")
        self.config_refused([("CONFIG_HID_APPLE=m", "CONFIG_HID_APPLE=y")], "HID_APPLE")
        self.config_refused([("CONFIG_APPLE_DART=y", "CONFIG_APPLE_DART=m")], "APPLE_DART")
        self.config_refused([("CONFIG_APPLE_MAILBOX=y", "CONFIG_APPLE_MAILBOX=m")], "APPLE_MAILBOX")
        self.config_refused([("CONFIG_HIDRAW=y", "# CONFIG_HIDRAW is not set")], "HIDRAW")
        self.config_refused([("CONFIG_USB_DWC3=y", "CONFIG_USB_DWC3=m")], "USB_DWC3")
        self.config_refused([("CONFIG_MODULE_UNLOAD=y", "# CONFIG_MODULE_UNLOAD is not set")], "MODULE_UNLOAD")

    def test_image_deviations_refused(self):
        with self.assertRaises(ValueError):
            R.check_image((B41 / "Image").read_bytes())
        image = bytearray((P42 / "Image").read_bytes())
        image[4096] ^= 1
        with self.assertRaises(ValueError):
            R.check_image(bytes(image))

    def test_image_markers_checked_apart_from_the_digest(self):
        # The markers on their own (as if the pin were another build's): a storage match table or the
        # read-only patch's string in the Image, or a DART diagnostic or hidraw missing, is refused.
        image = (P42 / "Image").read_bytes()
        cases = (("still carries", image + b"apple,nvme-ans2\0"),
                 ("still carries", image + b"iLinux read-only mode"),
                 ("lacks", image.replace(b"hidraw", b"hidrax")),
                 ("lacks", image.replace(b"t8110-class DART v", b"t8110-class DART w")))
        pinned = R.IMAGE_SHA256
        try:
            for why, blob in cases:
                R.IMAGE_SHA256 = hashlib.sha256(blob).hexdigest()
                with self.assertRaises(ValueError) as caught:
                    R.check_image(blob)
                self.assertIn(why, str(caught.exception))
        finally:
            R.IMAGE_SHA256 = pinned

    def test_kept_drivers_checked_apart_from_the_delta(self):
        # A baseline that had already lost a driver boot042 keeps built in: no delta for it, still refused.
        for name in ("APPLE_DART", "APPLE_MAILBOX", "USB_CONFIGFS"):
            with self.subTest(symbol=name):
                old, new = "CONFIG_%s=y\n" % name, "CONFIG_%s=m\n" % name
                before = (B41 / "kernel.config").read_text()
                after = (P42 / "kernel.config").read_text()
                self.assertIn(old, before)
                with self.assertRaises(ValueError) as caught:
                    R.check_config(before.replace(old, new), after.replace(old, new))
                self.assertIn("%s must stay y" % name, str(caught.exception))

    def test_only_the_two_revealed_lines_may_appear(self):
        text = (P42 / "kernel.config").read_text() + "# CONFIG_ILINUX_TEST_SYMBOL is not set\n"
        with self.assertRaises(ValueError) as caught:
            R.check_config((B41 / "kernel.config").read_text(), text)
        self.assertIn("ILINUX_TEST_SYMBOL", str(caught.exception))
        for name in R.CONFIG_REVEALED:
            self.assertIn("# CONFIG_%s is not set\n" % name, (P42 / "kernel.config").read_text())

    def test_boot041_files_are_not_boot042(self):
        with self.assertRaises(ValueError):
            R.check_delta(self.before(), self.before())
        with self.assertRaises(ValueError):
            R.check_config((B41 / "kernel.config").read_text(), (B41 / "kernel.config").read_text())


if __name__ == "__main__":
    unittest.main()
