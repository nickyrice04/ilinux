"""boot037 MTP input contract: the exact delta passes, every deviation fails closed."""
import gzip
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
import mtp_input as mi  # noqa: E402
import kconfig_guard  # noqa: E402
from fdt import check_stage_b, properties  # noqa: E402

BOOT036 = ROOT / "build/native-boot036/verified"
EXPERIMENT = ROOT / "kernel/experiments/mtp-input"
ADT = ROOT / "hardware/adt/adt-sanitized.json"
CANDIDATES = (ROOT / "build/native-boot037/verified/Image",
              ROOT / "virtualization/jobs/042-mtp-input/out/build/Image-mtp-input-boot036")


def cells(*values):
    return struct.pack(">%dI" % len(values), *values)


def text(*values):
    return b"".join(v.encode() + b"\0" for v in values)


# Independent oracle: written out from the ADT/README values (every address below is the
# ADT's /arm-io address plus 0x200000000), not from mtp_input.
def boot037(before, handles=(107, 108, 109, 110)):
    mtp, mbox, dock, dart = handles
    aic = before["/soc/interrupt-controller@280400000"].get("phandle", cells(0x1c))
    after = {path: dict(node) for path, node in before.items()}
    after["/soc/iommu@294800000"].pop("status", None)
    after["/soc/iommu@294800000"].update({
        "apple,dma-range": cells(0x100, 0x4000, 0x0, 0xffff0000), "phandle": cells(dart)})
    after["/aliases"]["keyboard"] = b"/soc/fifo@294b14000/input@8000/keyboard\0"
    hid = "/soc/fifo@294b14000/input@8000"
    after.update({
        "/soc/mtp@294600000": {
            "compatible": text("apple,t6050-mtp", "apple,t6050-rtk-helper-asc4", "apple,mtp",
                               "apple,rtk-helper-asc4"),
            "reg": cells(0x2, 0x94600000, 0, 0x4000, 0x2, 0x94c00000, 0, 0x100000),
            "reg-names": text("asc", "sram"), "mboxes": cells(mbox), "iommus": cells(dart, 1),
            "#helper-cells": cells(0), "phandle": cells(mtp)},
        "/soc/mbox@294608000": {
            "compatible": text("apple,t6050-asc-mailbox", "apple,asc-mailbox-v4"),
            "reg": cells(0x2, 0x94608000, 0, 0x4000), "interrupt-parent": aic,
            "interrupts": cells(0, 0x2a4, 4, 0, 0x2a5, 4, 0, 0x2a6, 4, 0, 0x2a7, 4),
            "interrupt-names": text("send-empty", "send-not-empty", "recv-empty", "recv-not-empty"),
            "#mbox-cells": cells(0), "phandle": cells(mbox)},
        "/soc/fifo@294b14000": {
            "compatible": text("apple,t6050-dockchannel", "apple,dockchannel"),
            "reg": cells(0x2, 0x94b14000, 0, 0x4000), "reg-names": text("irq"),
            "interrupt-parent": aic, "interrupts": cells(0, 0x294, 4),
            "ranges": cells(0, 0x2, 0x94b28000, 0x20000), "nonposted-mmio": b"",
            "#address-cells": cells(1), "#size-cells": cells(1), "interrupt-controller": b"",
            "#interrupt-cells": cells(2), "phandle": cells(dock)},
        hid: {
            "compatible": text("apple,t6050-dockchannel-hid", "apple,dockchannel-hid"),
            "reg": cells(0x8000, 0x4000, 0xc000, 0x4000, 0, 0x4000, 0x4000, 0x4000),
            "reg-names": text("config", "data", "rmt-config", "rmt-data"),
            "iommus": cells(dart, 1), "interrupt-parent": cells(dock),
            "interrupts": cells(2, 4, 3, 4), "interrupt-names": text("tx", "rx"),
            "apple,fifo-size": cells(0x800), "apple,helper-cpu": cells(mtp)},
        hid + "/multi-touch": {"firmware-name": b"apple/tpmtfw-j716c.bin\0"},
        hid + "/keyboard": {"hid-country-code": cells(0), "apple,keyboard-layout-id": cells(0)},
        hid + "/stm": {}, hid + "/actuator": {}, hid + "/tp_accel": {}, hid + "/tp-accel": {},
    })
    return after


def synthetic_before():
    """The nodes the rule reads, in their boot036 state, plus a few unrelated ones."""
    return {
        "/": {"compatible": b"apple,j716c\0apple,t6050\0"},
        "/aliases": {"serial0": b"/soc/serial@505200000\0"},
        "/soc": {"#address-cells": cells(2), "#size-cells": cells(2), "ranges": b""},
        "/soc/interrupt-controller@280400000": {
            "compatible": text("apple,t6050-aic3", "apple,t8122-aic3"), "phandle": cells(0x1c),
            "interrupt-controller": b"", "#interrupt-cells": cells(3)},
        "/soc/iommu@294800000": {
            "compatible": text("apple,t6050-dart", "apple,t8110-dart"),
            "reg": cells(0x2, 0x94800000, 0, 0xc000), "#iommu-cells": cells(1),
            "interrupt-parent": cells(0x1c), "interrupts": cells(0, 0x293, 4),
            "status": b"disabled\0"},
        "/soc/iommu@2a2f80000": {"phandle": cells(0x68), "#iommu-cells": cells(1)},
        "/soc/usb@2a2280000": {"dr_mode": b"peripheral\0", "iommus": cells(0x68, 1)},
        "/cpus/cpu@40000": {"device_type": b"cpu\0", "reg": struct.pack(">Q", 0x40000)},
        "/soc/power-management@288300000/power-controller@80": {
            "label": b"nub_dock_channel\0", "apple,always-on": b""},
        "/soc/serial@505200000": {"compatible": b"apple,s5l-uart\0"},
    }


CONTRACT = "MTP contract"   # the final exact comparison names every differing path


def mutations(before, after):
    """{name: (function(tree), message fragment)}: each breaks one rule of the contract."""
    hid = "/soc/fifo@294b14000/input@8000"
    dart = "/soc/iommu@294800000"
    cpu = next(p for p in before if p.startswith("/cpus/cpu@"))
    other = next(p for p in before if "phandle" in before[p] and p != "/soc/interrupt-controller@280400000")
    taken = struct.unpack(">I", before[other]["phandle"])[0]

    def drop(path):
        return lambda t: t.pop(path)

    plain = {
        "DART left disabled": lambda t: t[dart].__setitem__("status", b"disabled\0"),
        "DART status okay": lambda t: t[dart].__setitem__("status", b"okay\0"),
        "DART dma-range missing": lambda t: t[dart].pop("apple,dma-range"),
        "DART dma-range one 64 KiB short": lambda t: t[dart].__setitem__(
            "apple,dma-range", cells(0x100, 0x4000, 0, 0xfffe0000)),
        "DART dma-range from zero": lambda t: t[dart].__setitem__(
            "apple,dma-range", cells(0, 0, 0, 0xffff0000)),
        "DART register base moved by 0x8000": lambda t: t[dart].__setitem__(
            "reg", cells(0x2, 0x94808000, 0, 0xc000)),
        "DART gains power-domains": lambda t: t[dart].__setitem__("power-domains", cells(0x43)),
        "DART phandle missing": lambda t: t[dart].pop("phandle"),
        "DART phandle zero": lambda t: t[dart].__setitem__("phandle", cells(0)),
        "DART phandle all ones": lambda t: t[dart].__setitem__("phandle", cells(0xffffffff)),
        "DART phandle collides with boot036": lambda t: t[dart].__setitem__("phandle", cells(taken)),
        "mailbox phandle duplicates mtp's": lambda t: t["/soc/mbox@294608000"].__setitem__(
            "phandle", t["/soc/mtp@294600000"]["phandle"]),
        "mtp phandle collides with boot036": lambda t: t["/soc/mtp@294600000"].__setitem__(
            "phandle", cells(taken)),
        "extra node under input": lambda t: t.__setitem__(hid + "/tp_accel2", {}),
        "second mailbox": lambda t: t.__setitem__("/soc/mbox@294610000", {
            k: v for k, v in t["/soc/mbox@294608000"].items() if k != "phandle"}),
        "stream 0": lambda t: t["/soc/mtp@294600000"].__setitem__("iommus", cells(110, 0)),
        "two streams": lambda t: t["/soc/mtp@294600000"].__setitem__("iommus", cells(110, 0, 110, 1)),
        "hid on another DART": lambda t: t[hid].__setitem__("iommus", cells(0x68, 1)),
        "mailbox interrupts swapped": lambda t: t["/soc/mbox@294608000"].__setitem__(
            "interrupts", cells(0, 0x2a5, 4, 0, 0x2a4, 4, 0, 0x2a6, 4, 0, 0x2a7, 4)),
        "mailbox interrupt off by one": lambda t: t["/soc/mbox@294608000"].__setitem__(
            "interrupts", cells(0, 0x2a5, 4, 0, 0x2a6, 4, 0, 0x2a7, 4, 0, 0x2a8, 4)),
        "m3 mailbox variant": lambda t: t["/soc/mbox@294608000"].__setitem__(
            "compatible", text("apple,t6050-asc-mailbox", "apple,m3-mailbox-v2")),
        "mailbox routed to another AIC cell": lambda t: t["/soc/mbox@294608000"].__setitem__(
            "interrupt-parent", cells(0x68)),
        "dockchannel interrupt moved": lambda t: t["/soc/fifo@294b14000"].__setitem__(
            "interrupts", cells(0, 0x295, 4)),
        "dockchannel window moved": lambda t: t["/soc/fifo@294b14000"].__setitem__(
            "ranges", cells(0, 0x2, 0x94b2c000, 0x20000)),
        "fifo size 0x400": lambda t: t[hid].__setitem__("apple,fifo-size", cells(0x400)),
        "helper-cpu is the DART": lambda t: t[hid].__setitem__("apple,helper-cpu", cells(110)),
        "hid interrupts wired to the AIC": lambda t: t[hid].__setitem__(
            "interrupt-parent", t["/soc/mbox@294608000"]["interrupt-parent"]),
        "ASC window too small": lambda t: t["/soc/mtp@294600000"].__setitem__(
            "reg", cells(0x2, 0x94600000, 0, 0x4000, 0x2, 0x94c00000, 0, 0x4000)),
        "mtp compatible without the t6050 string": lambda t: t["/soc/mtp@294600000"].__setitem__(
            "compatible", text("apple,mtp", "apple,rtk-helper-asc4")),
        "hid compatible selects FIFO mode only": lambda t: t[hid].__setitem__(
            "compatible", text("apple,dockchannel-hid")),
        "status on mtp": lambda t: t["/soc/mtp@294600000"].__setitem__("status", b"disabled\0"),
        "status on hid": lambda t: t[hid].__setitem__("status", b"okay\0"),
        "power-domains on mtp": lambda t: t["/soc/mtp@294600000"].__setitem__(
            "power-domains", cells(0x43)),
        "GPIO provider reference on multi-touch": lambda t: t[hid + "/multi-touch"].__setitem__(
            "apple,reset-gpios", cells(0x4a, 3, 0)),
        "GPIO reference on keyboard": lambda t: t[hid + "/keyboard"].__setitem__(
            "apple,keyboard-gpios", cells(0x4a, 3, 0)),
        "firmware-name removed": lambda t: t[hid + "/multi-touch"].pop("firmware-name"),
        "firmware-name elsewhere": lambda t: t[hid + "/multi-touch"].__setitem__(
            "firmware-name", b"apple/other.bin\0"),
        "keyboard layout id set": lambda t: t[hid + "/keyboard"].__setitem__(
            "apple,keyboard-layout-id", cells(1)),
        "keyboard alias missing": lambda t: t["/aliases"].pop("keyboard"),
        "keyboard alias on stm": lambda t: t["/aliases"].__setitem__("keyboard", (hid + "/stm\0").encode()),
        "keyboard alias dangling": lambda t: t["/aliases"].__setitem__("keyboard", b"/soc/nope\0"),
        "extra alias": lambda t: t["/aliases"].__setitem__("touchpad", (hid + "/multi-touch\0").encode()),
        "serial alias changed": lambda t: t["/aliases"].__setitem__("serial0", b"/soc/nope\0"),
        "AIC changed": lambda t: t["/soc/interrupt-controller@280400000"].__setitem__(
            "#interrupt-cells", cells(2)),
        "CPU disabled": lambda t: t[cpu].__setitem__("status", b"disabled\0"),
        "USB core changed": lambda t: t["/soc/usb@2a2280000"].__setitem__("dr_mode", b"otg\0"),
        "other DART enabled": lambda t: t["/soc/iommu@2a2f80000"].__setitem__("status", b"okay\0"),
        "always-on domain dropped": lambda t: t[
            "/soc/power-management@288300000/power-controller@80"].pop("apple,always-on"),
    }
    cases = {name: (change, CONTRACT) for name, change in plain.items()}
    for name, needle in (("DART phandle missing", "phandle missing or invalid"),
                         ("DART phandle zero", "phandle missing or invalid"),
                         ("DART phandle all ones", "phandle missing or invalid"),
                         ("DART phandle collides with boot036", "duplicate phandle"),
                         ("mailbox phandle duplicates mtp's", "duplicate phandle"),
                         ("mtp phandle collides with boot036", "duplicate phandle")):
        cases[name] = (plain[name], needle)
    for path in mi.NEW_NODES:
        # the nodes that carry a phandle are looked up first; the rest only show in the comparison
        cases["missing " + path] = (drop(path), "phandle missing or invalid"
                                    if path in (mi.MTP, mi.MBOX, mi.DOCK) else CONTRACT)
    return cases


class DeltaRules:
    """Mixed into one test case per input tree."""
    before = None

    def refused(self, change, needle):
        after = boot037(self.before)
        change(after)
        with self.assertRaises(ValueError) as caught:
            mi.check_delta(self.before, after)
        self.assertIn(needle, str(caught.exception))

    def test_exact_delta_passes(self):
        mi.check_delta(self.before, boot037(self.before))

    def test_constants_match_the_oracle(self):
        self.assertEqual(mi.new_nodes(self.before["/soc/interrupt-controller@280400000"]["phandle"],
                                      dict(mtp=107, mbox=108, dock=109, dart=110)),
                         {p: n for p, n in boot037(self.before).items() if p in mi.NEW_NODES})
        self.assertEqual(len(mi.NEW_NODES), 10)

    def test_phandle_values_are_free(self):
        # The allocator is the tool's business; the rule only needs fresh, distinct handles.
        mi.check_delta(self.before, boot037(self.before, (0x200, 0x201, 0x202, 0x203)))
        mi.check_delta(self.before, boot037(self.before, (0x201, 0x200, 0x203, 0x202)))

    def test_mutations(self):
        for name, (change, needle) in mutations(self.before, boot037(self.before)).items():
            with self.subTest(mutation=name):
                self.refused(change, needle)

    def test_every_mutation_is_a_real_change(self):
        good = boot037(self.before)
        for name, (change, _) in mutations(self.before, good).items():
            tree = {path: dict(node) for path, node in good.items()}
            change(tree)
            self.assertNotEqual(tree, good, name)

    def test_input_must_be_boot036_state(self):
        applied = boot037(self.before)
        with self.assertRaises(ValueError):
            mi.check_delta(applied, boot037(self.before, (111, 112, 113, 114)))

    def test_input_deviations(self):
        cases = {
            "DART already enabled": lambda t: t["/soc/iommu@294800000"].pop("status"),
            "DART already has a phandle": lambda t: t["/soc/iommu@294800000"].__setitem__(
                "phandle", cells(0x77)),
            "DART has power-domains": lambda t: t["/soc/iommu@294800000"].__setitem__(
                "power-domains", cells(0x43)),
            "DART elsewhere": lambda t: t["/soc/iommu@294800000"].__setitem__(
                "reg", cells(0x2, 0x94810000, 0, 0xc000)),
            "keyboard alias present": lambda t: t["/aliases"].__setitem__("keyboard", b"/soc\0"),
            "mtp node present": lambda t: t.__setitem__("/soc/mtp@294600000", {}),
            "no AIC phandle": lambda t: t["/soc/interrupt-controller@280400000"].pop("phandle"),
        }
        for name, change in cases.items():
            before = {path: dict(node) for path, node in self.before.items()}
            change(before)
            with self.subTest(case=name), self.assertRaises(ValueError) as caught:
                mi.check_delta(before, boot037(before))
            self.assertNotIn(CONTRACT, str(caught.exception), name)


class SyntheticDeltaTests(DeltaRules, unittest.TestCase):
    def setUp(self):
        self.before = synthetic_before()


@unittest.skipUnless((BOOT036 / "t6050-j716c-stage-b.dtb").is_file(), "boot036 package not extracted in build/")
class RealDeltaTests(DeltaRules, unittest.TestCase):
    def setUp(self):
        self.before = properties((BOOT036 / "t6050-j716c-stage-b.dtb").read_bytes())

    def test_boot036_state_facts(self):
        # The one gap in what the delta tool's own check proves: the node it edits is MTP's DART.
        dart = self.before["/soc/iommu@294800000"]
        self.assertEqual(dart["status"], b"disabled\0")
        self.assertNotIn("power-domains", dart)
        domain = self.before["/soc/power-management@288300000/power-controller@80"]
        self.assertEqual(domain["label"], b"nub_dock_channel\0")
        self.assertIn("apple,always-on", domain)   # the release ladder cannot power it down

    def test_new_handles_follow_the_highest_boot036_handle(self):
        top = max(struct.unpack(">I", n["phandle"])[0] for n in self.before.values() if "phandle" in n)
        self.assertEqual(top, 106)

    @unittest.skipUnless((EXPERIMENT / "make_mtp_dt.py").is_file() and ADT.is_file()
                         and (EXPERIMENT.parent / "usb-gadget-dt/fdtedit.py").is_file(),
                         "MTP DT tool, fdtedit or the sanitized ADT not in this checkout")
    def test_tool_output_is_the_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, delta = Path(tmp) / "out.dtb", Path(tmp) / "delta.json"
            result = subprocess.run([sys.executable, "-I", str(EXPERIMENT / "make_mtp_dt.py"),
                                     str(BOOT036 / "t6050-j716c-stage-b.dtb"), str(ADT),
                                     str(out), str(delta), "--sids", "1"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            blob = out.read_bytes()
            after = properties(blob)
            mi.check_delta(self.before, after)
            check_stage_b(blob)
            handles = json.loads(delta.read_text())["phandles"]
            self.assertEqual(after, boot037(self.before, (handles["mtp"], handles["mtp_mbox"],
                                                          handles["mtp_dockchannel"], handles["mtp_dart"])))

    @unittest.skipUnless((EXPERIMENT / "mtp_adt.py").is_file() and ADT.is_file(), "ADT facts tool not present")
    def test_literals_follow_the_adt(self):
        sys.path.insert(0, str(EXPERIMENT))
        try:
            import mtp_adt
            facts = mtp_adt.facts(ADT)
        finally:
            sys.path.remove(str(EXPERIMENT))
        hi = lambda v: (v >> 32, v & 0xffffffff)  # noqa: E731
        self.assertEqual(mi.DART_REG, hi(facts["dart"]) + (0, facts["dart_window"]))
        self.assertEqual(mi.DART_IRQ, facts["dart_irq"])
        self.assertEqual(mi.DMA_RANGE, hi(facts["vm_base"]) + hi(facts["vm_size"]))
        self.assertEqual(list(mi.MAILBOX_IRQS), facts["mbox_irqs"])
        self.assertEqual(mi.FIFO_SIZE, facts["fifo_size"])
        nodes = mi.new_nodes(cells(1), dict(mtp=1, mbox=2, dock=3, dart=4))
        self.assertEqual(nodes[mi.MTP]["reg"], cells(*hi(facts["asc"]), 0, 0x4000, *hi(facts["sram"]), 0, 0x100000))
        self.assertEqual(nodes[mi.MBOX]["reg"], cells(*hi(facts["mbox"]), 0, 0x4000))
        self.assertEqual(nodes[mi.DOCK]["reg"], cells(*hi(facts["dock_irq_block"]), 0, 0x4000))
        self.assertEqual(nodes[mi.DOCK]["ranges"], cells(0, *hi(facts["dock_ranges_base"]), 0x20000))
        self.assertEqual(nodes[mi.DOCK]["interrupts"], cells(0, facts["dock_irq"], 4))
        self.assertEqual(sorted(name.replace("_", "-") for name in mi.INTERFACES if name != "tp-accel"),
                         sorted(name.replace("_", "-") for name in facts["interfaces"]))


class ConfigTests(unittest.TestCase):
    NEEDED = ["CONFIG_%s=y" % name for name in mi.CONFIG_NEEDED]
    BEFORE = "\n".join(NEEDED + ["CONFIG_USB_GADGET=y", "# CONFIG_FTRACE is not set",
                                 "CONFIG_RUSTC_VERSION=109900"]
                       + ["# CONFIG_%s is not set" % name for name in mi.CONFIG_SET])

    def after(self):
        text = self.BEFORE
        for name in mi.CONFIG_SET:
            text = text.replace("# CONFIG_%s is not set" % name, "CONFIG_%s=y" % name)
        return text + "".join("\n# CONFIG_%s is not set" % name for name in mi.CONFIG_REVEALED)

    def test_expected_delta(self):
        self.assertEqual(mi.check_config(self.BEFORE, self.after()), [])

    def test_deviations(self):
        good = self.after()
        cases = {
            "nothing changed": self.BEFORE,
            "one symbol missing": good.replace("CONFIG_HIDRAW=y", "# CONFIG_HIDRAW is not set"),
            "one symbol as a module": good.replace("CONFIG_HID_APPLE=y", "CONFIG_HID_APPLE=m"),
            "extra symbol": good + "\nCONFIG_FTRACE=y",
            "extra symbol removed": good.replace("CONFIG_USB_GADGET=y", "# CONFIG_USB_GADGET is not set"),
            "revealed symbol enabled": good.replace("# CONFIG_HID_FT260 is not set", "CONFIG_HID_FT260=y"),
            "revealed symbol missing": good.replace("\n# CONFIG_HID_CP2112 is not set", ""),
            "unexpected new symbol": good + "\n# CONFIG_HID_NEW_THING is not set",
            "symbol lost": good.replace("# CONFIG_FTRACE is not set\n", ""),
            "driver stack off": good.replace("CONFIG_APPLE_DART=y", "# CONFIG_APPLE_DART is not set"),
            "toolchain drift is not tolerated here": good.replace("RUSTC_VERSION=109900", "RUSTC_VERSION=0"),
        }
        for name, config in cases.items():
            with self.subTest(case=name), self.assertRaises(ValueError):
                mi.check_config(self.BEFORE, config)

    def test_driver_stack_off_in_both(self):
        before = self.BEFORE.replace("CONFIG_APPLE_DART=y", "# CONFIG_APPLE_DART is not set")
        after = self.after().replace("CONFIG_APPLE_DART=y", "# CONFIG_APPLE_DART is not set")
        with self.assertRaises(ValueError) as caught:
            mi.check_config(before, after)
        self.assertIn("CONFIG_APPLE_DART must be y", str(caught.exception))

    def test_contract_literals(self):
        self.assertEqual(sorted(mi.CONFIG_SET), ["APPLE_RTKIT_HELPER", "HIDRAW", "HID_APPLE", "HID_MAGICMOUSE"])
        self.assertEqual(sorted(mi.CONFIG_REVEALED), ["HID_CP2112", "HID_FT260"])
        self.assertEqual(sorted(mi.CONFIG_NEEDED), sorted([
            "APPLE_RTKIT", "APPLE_MAILBOX", "APPLE_DART", "APPLE_DOCKCHANNEL", "HID_DOCKCHANNEL", "HID",
            "INPUT", "INPUT_EVDEV", "OF", "IOMMU_DMA", "FW_LOADER", "LEDS_CLASS", "NEW_LEDS"]))
        self.assertEqual(set(mi.CONFIG_NEEDED.values()), {"y"})

    def test_toolchain_drift_when_allowed(self):
        drifted = self.after().replace("RUSTC_VERSION=109900", "RUSTC_VERSION=0")
        self.assertEqual(mi.check_config(self.BEFORE, drifted, allow_toolchain=True), ["RUSTC_VERSION"])
        with self.assertRaises(ValueError):
            mi.check_config(self.BEFORE, drifted + "\nCONFIG_FTRACE=y", allow_toolchain=True)

    @unittest.skipUnless((BOOT036 / "kernel.config").is_file(), "boot036 package not extracted in build/")
    def test_boot036_config_shape(self):
        values = kconfig_guard.parse_config((BOOT036 / "kernel.config").read_text())
        for name in mi.CONFIG_SET + mi.CONFIG_REVEALED:
            self.assertIn(values.get(name, "n"), ("n",), name)
        for name, value in mi.CONFIG_NEEDED.items():
            self.assertEqual(values.get(name), value, name)

    @unittest.skipUnless((BOOT036 / "kernel.config").is_file(), "boot036 package not extracted in build/")
    def test_real_delta(self):
        for image in CANDIDATES:
            if image.is_file():
                break
        else:
            self.skipTest("no MTP Image built (job 042 / boot037)")
        embedded = kconfig_guard.embedded_config(image.read_bytes()).decode()
        self.assertEqual(mi.check_config((BOOT036 / "kernel.config").read_text(), embedded), [])


class ImageTests(unittest.TestCase):
    def image(self, drop=None):
        markers = [m for m in mi.IMAGE_MARKERS if m != drop]
        return b"\0" * 4096 + b"\0\0".join(markers) + b"\0" * 4096

    def test_markers_pass(self):
        mi.check_image(self.image())

    def test_each_marker_is_required(self):
        for marker in mi.IMAGE_MARKERS:
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                mi.check_image(self.image(drop=marker))

    def test_prefix_of_a_longer_name_is_not_enough(self):
        # ...mtp_ring is a prefix of ...mtp_ring_size: the NUL terminator tells them apart
        image = b"dockchannel_hid.mtp_ring_size\0apple,t6050-dockchannel-hid\0Ring registered: iova " \
                b"dockchannel_hid.mtp_poll_ms\0dockchannel_hid.mtp_enable_cmd\0apple,dockchannel-hid\0"
        with self.assertRaises(ValueError):
            mi.check_image(image)

    NEW = (b"dockchannel_hid.mtp_ring\0", b"dockchannel_hid.mtp_enable_cmd\0", b"dockchannel_hid.mtp_poll_ms\0",
           b"dockchannel_hid.mtp_ring_size\0", b"apple,t6050-dockchannel-hid\0", b"Ring registered: iova ")

    def test_marker_list(self):
        self.assertEqual(set(mi.IMAGE_MARKERS), set(self.NEW) | {b"apple,dockchannel-hid\0"})

    @unittest.skipUnless((BOOT036 / "Image").is_file(), "boot036 package not extracted in build/")
    def test_boot036_image_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            mi.check_image((BOOT036 / "Image").read_bytes())
        for marker in self.NEW:
            self.assertIn(marker.rstrip(b"\0").decode(), str(caught.exception))
        self.assertNotIn("apple,dockchannel-hid", str(caught.exception))   # FIFO mode was always there

    def test_candidate_image_passes(self):
        for image in CANDIDATES:
            if image.is_file():
                mi.check_image(image.read_bytes())
                return
        self.skipTest("no MTP Image built (job 042 / boot037)")


STAGE = ROOT / "build/native-boot037/stage/export"
KEY = ROOT / "kernel/experiments/usb-gadget/authorized_keys"


@unittest.skipUnless(STAGE.is_dir() and (BOOT036 / "Image").is_file() and KEY.is_file(),
                     "boot037 stage (stage-boot037.py) or the boot036 package not in build/")
class PackagerTests(unittest.TestCase):
    """make-package.py --name ilinux-j716c-boot037 on the staged export, tampered one way at a time."""

    def package(self, tamper=None, previous=BOOT036, key=KEY):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shutil.copytree(STAGE, tmp / "out/export")
            (tmp / "rec").mkdir()
            if tamper:
                tamper(tmp / "out/export")
            cmd = [sys.executable, "-I", str(HERE / "make-package.py"), "--out", str(tmp / "out"),
                   "--destination", str(tmp / "dest"), "--name", "ilinux-j716c-boot037",
                   "--record-dir", str(tmp / "rec")]
            if previous:
                cmd += ["--previous-package", str(previous)]
            if key:
                cmd += ["--authorized-key", str(key)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode, result.stderr.strip().splitlines()[-1:] or [""]

    def refused(self, needle, **kwargs):
        code, last = self.package(**kwargs)
        self.assertNotEqual(code, 0)
        self.assertIn(needle, last[0])

    def test_staged_export_is_accepted(self):
        code, last = self.package()
        self.assertEqual((code, last), (0, [""]))

    def test_deviations(self):
        def put(name, data):
            return lambda export: (export / name).write_bytes(data() if callable(data) else data)

        def append(name):
            return lambda export: (export / name).write_bytes((export / name).read_bytes() + b"\0")

        boot036 = lambda name: (BOOT036 / name).read_bytes()  # noqa: E731

        def undriven_image():   # boot036's Image whose embedded config is boot037's
            image, config = boot036("Image"), (STAGE / "kernel.config").read_bytes()
            start = image.index(kconfig_guard.START + b"\x1f\x8b") + len(kconfig_guard.START)
            return image[:start] + gzip.compress(config, mtime=0) + image[image.index(kconfig_guard.END, start):]
        other_key = Path(tempfile.mkdtemp()) / "other.pub"
        other_key.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleExampleExampleExampleExampleExampl x\n")
        cases = {
            "boot036's Stage-B DT (no MTP nodes)": dict(
                tamper=put("t6050-j716c-stage-b.dtb", lambda: boot036("t6050-j716c-stage-b.dtb")),
                needle="phandle missing or invalid"),
            "boot036's Image with the new config": dict(
                tamper=put("Image", lambda: boot036("Image")), needle="not the config the Image was built with"),
            "an Image with the new config but no driver": dict(
                tamper=put("Image", undriven_image), needle="Image lacks the MTP ring-transport driver"),
            "boot036's Image and config": dict(
                tamper=lambda export: [(export / n).write_bytes(boot036(n)) for n in ("Image", "kernel.config")],
                needle="kernel config delta differs"),
            "initramfs changed": dict(tamper=append("initramfs-stage-b.cpio.gz"),
                                      needle="unexpected payload change: initramfs-stage-b.cpio.gz"),
            "m1n1 changed": dict(tamper=append("m1n1.bin"), needle="unexpected payload change: m1n1.bin"),
            "full DT changed": dict(tamper=append("t6050-j716c.dtb"),
                                    needle="original job-020 artifact changed: t6050-j716c.dtb"),
            "init source changed": dict(tamper=append("diag-init.c"),
                                        needle="unexpected payload change: diag-init.c"),
            "no previous package": dict(previous=None, needle="boot037 needs --previous-package"),
            "no authorized key": dict(key=None, needle="boot037 needs --previous-package"),
            "another key": dict(key=other_key, needle="authorized_keys must hold exactly the expected key"),
            "wrong previous package": dict(previous=ROOT / "build/native-boot035/verified",
                                           needle="prior digest mismatch"),
        }
        for name, case in cases.items():
            if case.get("previous", BOOT036) and not Path(case.get("previous", BOOT036)).is_dir():
                continue
            with self.subTest(case=name):
                self.refused(case.pop("needle"), **case)


if __name__ == "__main__":
    unittest.main()
