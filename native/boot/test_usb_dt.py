"""boot036 USB DT contract: the exact delta passes, every deviation fails closed."""
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import usb_dt  # noqa: E402
from fdt import check_stage_b, properties  # noqa: E402

BOOT035 = HERE.parents[1] / "build/native-boot035/verified/t6050-j716c-stage-b.dtb"
DTC = HERE.parents[2] / "apple-silicon-linux-research/third_party/dtc/dtc"
MAKE_DT = HERE.parents[1] / "kernel/experiments/usb-gadget/make_stage_b_dt.py"
QUIRKS = {"snps,usb2-gadget-lpm-disable": b"", "snps,dis_u2_susphy_quirk": b"",
          "snps,dis_u3_susphy_quirk": b"", "snps,dis_enblslpm_quirk": b""}
# Independent oracle: written out from the ADT values, not from usb_dt.
DWC3 = {
    "/soc/usb@2a2280000": ((0x2, 0xa2280000), 0x58b, "/soc/iommu@2a2f80000"),
    "/soc/usb@2aa280000": ((0x2, 0xaa280000), 0x5ab, "/soc/iommu@2aaf80000"),
    "/soc/usb@382280000": ((0x3, 0x82280000), 0x5cb, "/soc/iommu@382f80000"),
}
NEW_PHANDLES = (0x68, 0x69, 0x6a)


def boot036(before):
    after = {path: dict(node) for path, node in before.items()}
    for path, node in after.items():
        label = node.get("label", b"").decode("ascii", "replace")
        if path.startswith("/soc/power-management@28") and label[:5] in ("atc0_", "atc1_", "atc2_"):
            node["status"] = b"disabled\0"
    for (path, (reg, irq, dart)), phandle in zip(sorted(DWC3.items()), NEW_PHANDLES):
        del after[dart]["status"], after[dart]["power-domains"]
        after[dart]["phandle"] = struct.pack(">I", phandle)
        after[path] = dict(QUIRKS, **{
            "compatible": b"snps,dwc3\0",
            "reg": struct.pack(">IIII", reg[0], reg[1], 0, 0xcd00),
            "interrupt-parent": struct.pack(">I", 0x1c),
            "interrupts": struct.pack(">III", 0, irq, 4),
            "dr_mode": b"peripheral\0",
            "maximum-speed": b"high-speed\0",
            "iommus": struct.pack(">II", phandle, 1),
        })
    return after


@unittest.skipUnless(BOOT035.is_file(), "boot035 package not extracted in build/")
class USBDTTests(unittest.TestCase):
    def setUp(self):
        self.before = properties(BOOT035.read_bytes())

    def test_exact_delta_passes(self):
        usb_dt.check_delta(self.before, boot036(self.before))

    def test_atc_set(self):
        domains = usb_dt.atc_domains(self.before)
        labels = sorted(self.before[p]["label"].rstrip(b"\0").decode() for p in domains)
        self.assertEqual(len(labels), 39)
        self.assertTrue(all(label[:5] in ("atc0_", "atc1_", "atc2_") for label in labels))
        for port in "012":
            self.assertIn("atc%s_usb" % port, labels)
            self.assertIn("atc%s_common" % port, labels)

    def test_amendment_text(self):
        text = usb_dt.amendment(self.before)
        self.assertEqual(text.count('status = "disabled";'), 39)
        self.assertEqual(text.count('compatible = "snps,dwc3";'), 3)
        self.assertEqual(text.count("/delete-property/ power-domains;"), 3)
        self.assertNotIn("iommu@2a2f00000", text)   # DART instance 0 stays disabled

    def mutated(self, change):
        after = boot036(self.before)
        change(after)
        with self.assertRaises(ValueError):
            usb_dt.check_delta(self.before, after)

    def test_mutations(self):
        dwc3 = "/soc/usb@2a2280000"
        dart = "/soc/iommu@2a2f80000"
        atc3 = next(p for p, n in self.before.items() if n.get("label") == b"atc3_usb\0")
        atc0 = next(p for p, n in self.before.items() if n.get("label") == b"atc0_usb\0")
        cpu = next(p for p in self.before if p.startswith("/cpus/cpu@"))
        mutations = {
            "ATC domain left enabled": lambda t: t[atc0].pop("status"),
            "ATC3 also disabled": lambda t: t[atc3].__setitem__("status", b"disabled\0"),
            "DART instance 0 enabled": lambda t: t["/soc/iommu@2a2f00000"].pop("status"),
            "DART keeps power-domains": lambda t: t[dart].__setitem__(
                "power-domains", self.before[dart]["power-domains"]),
            "DART still disabled": lambda t: t[dart].__setitem__("status", b"disabled\0"),
            "DART phandle missing": lambda t: t[dart].pop("phandle"),
            "duplicate phandle": lambda t: t[dart].__setitem__("phandle", struct.pack(">I", 0x1c)),
            "wrong IRQ": lambda t: t[dwc3].__setitem__("interrupts", struct.pack(">III", 0, 0x58c, 4)),
            "wrong reg size": lambda t: t[dwc3].__setitem__(
                "reg", struct.pack(">IIII", 2, 0xa2280000, 0, 0x100000)),
            "stream 0": lambda t: t[dwc3].__setitem__("iommus", struct.pack(">II", 0x68, 0)),
            "other port's DART": lambda t: t[dwc3].__setitem__("iommus", struct.pack(">II", 0x69, 1)),
            "missing quirk": lambda t: t[dwc3].pop("snps,dis_u2_susphy_quirk"),
            "otg mode": lambda t: t[dwc3].__setitem__("dr_mode", b"otg\0"),
            "super speed": lambda t: t[dwc3].__setitem__("maximum-speed", b"super-speed\0"),
            "Apple glue compatible": lambda t: t[dwc3].__setitem__(
                "compatible", b"apple,t6050-dwc3\0snps,dwc3\0"),
            "extra power domain": lambda t: t[dwc3].__setitem__("power-domains", b"\0\0\0\x4c"),
            "missing dwc3": lambda t: t.pop("/soc/usb@382280000"),
            "fourth dwc3": lambda t: t.__setitem__("/soc/usb@3a2280000", dict(t[dwc3])),
            "unrelated change": lambda t: t[cpu].__setitem__("status", b"disabled\0"),
        }
        for name, change in mutations.items():
            with self.subTest(mutation=name):
                self.mutated(change)

    def test_input_must_be_boot035_state(self):
        before = boot036(self.before)   # applying twice must fail
        with self.assertRaises(ValueError):
            usb_dt.check_delta(before, boot036(self.before))

    @unittest.skipUnless(DTC.is_file() or shutil.which("dtc"), "no dtc")
    def test_build_script(self):
        dtc = str(DTC) if DTC.is_file() else shutil.which("dtc")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "stage-b-036.dtb"
            result = subprocess.run([sys.executable, "-I", str(MAKE_DT), dtc, str(BOOT035), str(out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            after = properties(out.read_bytes())
            usb_dt.check_delta(self.before, after)
            check_stage_b(out.read_bytes())
            self.assertEqual(after, boot036(self.before))


if __name__ == "__main__":
    unittest.main()
