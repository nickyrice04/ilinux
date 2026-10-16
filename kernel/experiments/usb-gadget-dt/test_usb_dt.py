#!/usr/bin/env python3
"""Offline tests for the USB device-mode Stage-B DT candidate (stdlib unittest).

run: python3 -I kernel/experiments/usb-gadget-dt/test_usb_dt.py -v
"""
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(ROOT / "native/boot"))
import audit_domains  # noqa: E402
import fdtedit  # noqa: E402
import make_dt  # noqa: E402

BOOT035 = ROOT / "build/native-boot035/verified"
BOOT034 = ROOT / "build/native-boot034/verified"
ADT = ROOT / "hardware/adt/adt-sanitized.json"
CANDIDATE = ROOT / "build/usb-gadget-dt/t6050-j716c-stage-b.dtb"
DELTA = HERE / "dt-delta.json"

# Expected per-port facts (sanitized ADT, translated through /arm-io ranges).
EXPECTED_PORTS = [
    {"index": 0, "port_number": 1, "core": 0x2A2280000, "irq": 1419,
     "darts": [0x2A2F00000, 0x2A2F80000], "dart_irq": 1423},
    {"index": 1, "port_number": 2, "core": 0x2AA280000, "irq": 1451,
     "darts": [0x2AAF00000, 0x2AAF80000], "dart_irq": 1455},
    {"index": 2, "port_number": 3, "core": 0x382280000, "irq": 1483,
     "darts": [0x382F00000, 0x382F80000], "dart_irq": 1487},
]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = (BOOT035 / "t6050-j716c-stage-b.dtb").read_bytes()
        cls.ports = make_dt.port_facts(make_dt.adt_nodes(ADT))

    def candidate(self):
        tree, _ = make_dt.build(self.base, self.ports)
        return tree

    def assert_rejected(self, mutate, reason):
        tree = self.candidate()
        mutate(tree)
        with self.assertRaisesRegex(ValueError, reason):
            make_dt.check(fdtedit.parse(self.base), tree, self.ports)


class RoundTrip(Base):
    def test_existing_dtbs_round_trip_byte_for_byte(self):
        for path in (BOOT035 / "t6050-j716c-stage-b.dtb", BOOT035 / "t6050-j716c.dtb",
                     BOOT034 / "t6050-j716c-stage-b.dtb"):
            if not path.exists():
                continue
            blob = path.read_bytes()
            self.assertEqual(fdtedit.encode(fdtedit.parse(blob)), blob, path)


class Candidate(Base):
    def test_base_is_boot035(self):
        self.assertEqual(hashlib.sha256(self.base).hexdigest(), make_dt.BASE_SHA256)

    def test_port_facts_from_adt(self):
        self.assertEqual(self.ports, EXPECTED_PORTS)

    def test_build_is_deterministic_and_matches_outputs(self):
        one = fdtedit.encode(self.candidate())
        self.assertEqual(one, fdtedit.encode(self.candidate()))
        if CANDIDATE.exists():
            self.assertEqual(one, CANDIDATE.read_bytes())
        if DELTA.exists():
            self.assertEqual(json.loads(DELTA.read_text())["candidate"]["sha256"],
                             hashlib.sha256(one).hexdigest())

    def test_check_accepts_the_plan(self):
        disabled = make_dt.check(fdtedit.parse(self.base), self.candidate(), self.ports)
        self.assertEqual(len(disabled), 39)
        self.assertTrue(all(label[:4] in ("atc0", "atc1", "atc2") for label in disabled))

    def test_launcher_stage_b_checker_accepts_candidate(self):
        import fdt   # native/boot/fdt.py, the reviewed checker (read-only use)
        fdt.check_stage_b(fdtedit.encode(self.candidate()))

    def test_domain_audit(self):
        before = audit_domains.audit(self.base)
        after = audit_domains.audit(fdtedit.encode(self.candidate()))
        self.assertEqual(before["dt_unclaimed"], 145)          # the boot035 notes' count
        self.assertEqual(len(before["releasable_atc0_2"]), 39)
        self.assertEqual(after["releasable_atc0_2"], [])
        self.assertEqual(after["available_atc0_2"], [])
        self.assertEqual(after["defers_forever"], [])
        self.assertEqual(after["registered"], before["registered"] - 39)
        self.assertEqual(after["claimed"], before["claimed"])

    def test_main_refuses_another_base(self):
        bad = bytearray(self.base)
        bad[-1] ^= 1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad-base.dtb"
            path.write_bytes(bytes(bad))
            with self.assertRaises(SystemExit):
                make_dt.main(["make_dt.py", str(path), str(ADT), str(path) + ".out", str(path) + ".json"])
            self.assertFalse(Path(str(path) + ".out").exists())


class Mutations(Base):
    """Each deliberate mistake must make check() fail."""

    def test_dart_keeps_power_domain(self):
        def mutate(tree):
            tree.node("/soc/iommu@2aaf80000").set("power-domains", struct.pack(">I", 0x4d))
        self.assert_rejected(mutate, "unexpected DART change")

    def test_dart_stays_disabled(self):
        self.assert_rejected(lambda t: t.node("/soc/iommu@382f00000").set("status", make_dt.DISABLED),
                             "unexpected DART change")

    def test_one_atc_domain_left_enabled(self):
        def mutate(tree):
            for path, node in tree.walk():
                if make_dt.texts(node.get("label", b"")) == ["atc1_common_dp_2"]:
                    node.delete("status")
        self.assert_rejected(mutate, "not every atc0-2 domain is disabled")

    def test_unrelated_domain_disabled(self):
        def mutate(tree):
            for path, node in tree.walk():
                if make_dt.texts(node.get("label", b"")) == ["atc3_usb"]:
                    node.set("status", make_dt.DISABLED)
        self.assert_rejected(mutate, "unplanned change")

    def test_wrong_interrupt(self):
        self.assert_rejected(lambda t: t.node("/soc/usb@2a2280000").set(
            "interrupts", make_dt.cells(0, 1420, 4)), "interrupt differs from the ADT")

    def test_swapped_stream_ids(self):
        def mutate(tree):
            node = tree.node("/soc/usb@2aa280000")
            a, s0, b, s1 = struct.unpack(">4I", node.get("iommus"))
            node.set("iommus", make_dt.cells(a, s1, b, s0))
        self.assert_rejected(mutate, "do not resolve to its DARTs")

    def test_missing_quirk(self):
        self.assert_rejected(lambda t: t.node("/soc/usb@382280000").delete("snps,dis_u2_susphy_quirk"),
                             "quirks or forbidden properties")

    def test_usb_node_with_power_domain(self):
        self.assert_rejected(lambda t: t.node("/soc/usb@2a2280000").set(
            "power-domains", struct.pack(">I", 0x4c)), "quirks or forbidden properties")

    def test_super_speed(self):
        self.assert_rejected(lambda t: t.node("/soc/usb@2a2280000").set(
            "maximum-speed", make_dt.text("super-speed")), "not a high-speed peripheral")

    def test_duplicate_phandle(self):
        def mutate(tree):
            first = tree.node("/soc/iommu@2a2f00000").get("phandle")
            tree.node("/soc/iommu@2a2f80000").set("phandle", first)
        self.assert_rejected(mutate, "duplicate phandle")

    def test_extra_node(self):
        def mutate(tree):
            extra = fdtedit.Node("usb@2b0000000")
            extra.set("compatible", make_dt.text("snps,dwc3"))
            tree.node("/soc").children.append(extra)
        self.assert_rejected(mutate, "node set differs")

    def test_other_property_changed(self):
        self.assert_rejected(lambda t: t.node("/soc/iommu@2a2f00000").set(
            "interrupts", make_dt.cells(0, 1424, 4)), "DART property value changed")

    def test_consumer_of_disabled_domain(self):
        tree = self.candidate()
        self.assertEqual(make_dt.dangling(fdtedit.flat(tree)), [])
        self.assertEqual(make_dt.dangling(fdtedit.flat(fdtedit.parse(self.base))), [])
        for path, node in tree.walk():   # point an enabled pinctrl at a disabled ATC domain
            if node.get("compatible", b"").startswith(b"apple,t6050-pinctrl") and node.has("power-domains"):
                node.set("power-domains", struct.pack(">I", 0x4c))
                break
        found = make_dt.dangling(fdtedit.flat(tree))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0][1].endswith("power-controller@150"))   # atc0_usb

    def test_reenabled_child_with_disabled_parent(self):
        # atc0_cio_usb's only parent is atc0_cio; re-enabling the child alone dangles.
        tree = self.candidate()
        for path, node in tree.walk():
            if make_dt.texts(node.get("label", b"")) == ["atc0_cio_usb"]:
                node.delete("status")
        found = make_dt.dangling(fdtedit.flat(tree))
        self.assertEqual(len(found), 1)
        self.assertEqual(make_dt.texts(fdtedit.flat(tree)[found[0][1]]["label"]), ["atc0_cio"])


if __name__ == "__main__":
    unittest.main()
