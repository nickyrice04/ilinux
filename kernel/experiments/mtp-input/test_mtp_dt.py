"""Offline tests for make_mtp_dt.py. Run: python3 -I test_mtp_dt.py -v

Needs the boot035 Stage-B DTB under build/ (ignored). Skips cleanly if absent.
Each negative test breaks one rule and expects check() to refuse it.
"""
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
import make_mtp_dt as M  # noqa: E402
import mtp_adt  # noqa: E402

BASE = ROOT / "build/native-boot035/verified/t6050-j716c-stage-b.dtb"
ADT = ROOT / "hardware/adt/adt-sanitized.json"


@unittest.skipUnless(BASE.exists(), "boot035 Stage-B DTB not present")
class DelTa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob = BASE.read_bytes()
        cls.facts = mtp_adt.facts(ADT)

    def fresh(self, sids=(1,)):
        base = M.fdtedit.parse(self.blob)
        tree = M.fdtedit.parse(self.blob)
        ph = M.build(tree, self.facts, sids)
        return base, tree, ph

    # ---- the plan itself -------------------------------------------------
    def test_base_digest_known(self):
        self.assertIn(hashlib.sha256(self.blob).hexdigest(), M.KNOWN_BASES)

    def test_round_trip(self):
        self.assertEqual(M.fdtedit.encode(M.fdtedit.parse(self.blob)), self.blob)

    def test_happy_path(self):
        base, tree, ph = self.fresh()
        M.check(base, tree, self.facts, ph)
        # re-parse the encoded output and check again: encode/parse symmetry
        again = M.fdtedit.parse(M.fdtedit.encode(tree))
        M.check(base, again, self.facts, ph)

    def test_wide_sid_list(self):
        base, tree, ph = self.fresh(sids=(0, 1, 2, 3, 4))
        M.check(base, tree, self.facts, ph, sids=(0, 1, 2, 3, 4))
        iommus = tree.node("/soc/mtp@294600000").get("iommus")
        self.assertEqual(len(iommus), 5 * 8)

    def test_values_follow_the_adt(self):
        _, tree, _ = self.fresh()
        mbox = tree.node("/soc/mbox@294608000").get("interrupts")
        irqs = [struct.unpack(">3I", mbox[i:i + 12])[1] for i in range(0, 48, 12)]
        self.assertEqual(irqs, [676, 677, 678, 679])
        self.assertEqual(struct.unpack(">4I", tree.node(M.DART_PATH).get("apple,dma-range")),
                         (0x100, 0x4000, 0, 0xFFFF0000))
        hid = tree.node("/soc/fifo@294b14000/input@8000")
        self.assertEqual(struct.unpack(">I", hid.get("apple,fifo-size"))[0], 0x800)
        self.assertEqual(hid.get("reg-names"), b"config\0data\0rmt-config\0rmt-data\0")

    def test_adt_remap_is_byte_pairs(self):
        self.assertEqual(self.facts["remap"], [(1, 0), (2, 0), (3, 0), (4, 0)])
        self.assertEqual(self.facts["sid"], [0])

    def test_nothing_else_changes(self):
        base, tree, _ = self.fresh()
        before, after = M.fdtedit.flat(base), M.fdtedit.flat(tree)
        for path in before:
            if path in (M.DART_PATH, "/aliases"):
                continue
            self.assertEqual(before[path], after[path], path)

    # ---- deliberate mistakes, each refused for its own reason ---------------
    def refused(self, mutate, needle=None, sids=(1,)):
        base, tree, ph = self.fresh(sids)
        mutate(tree, ph)
        with self.assertRaises(AssertionError) as cm:
            M.check(base, tree, self.facts, ph, sids)
        if needle:
            self.assertIn(needle, str(cm.exception))

    def test_dart_keeps_disabled(self):
        self.refused(lambda t, p: t.node(M.DART_PATH).set("status", b"disabled\0"), "DART property delta")

    def test_dart_range_mismatch(self):
        self.refused(lambda t, p: t.node(M.DART_PATH).set("apple,dma-range", struct.pack(">4I", 0, 0, 0, 1)),
                     "apple,dma-range")

    def test_dart_other_property_changed(self):
        self.refused(lambda t, p: t.node(M.DART_PATH).set("interrupts", struct.pack(">3I", 0, 1, 4)),
                     "DART property")

    def test_extra_node(self):
        self.refused(lambda t, p: t.node("/soc").children.append(M.new_node("junk@1", [])), "node set")

    def test_missing_node(self):
        def drop(t, p):
            t.node("/soc/fifo@294b14000/input@8000").children.pop()
        self.refused(drop, "node set")

    def test_unrelated_property_modified(self):
        self.refused(lambda t, p: t.node("/cpus").set("#address-cells", struct.pack(">I", 3)),
                     "unexpected modified nodes")

    def test_duplicate_phandle(self):
        def dup(t, p):
            t.node("/soc/mbox@294608000").set("phandle", struct.pack(">I", p["mtp"]))
        self.refused(dup, "duplicate phandle")

    def test_alias_dangling(self):
        self.refused(lambda t, p: t.node("/aliases").set("keyboard", b"/soc/nope\0"), "alias target")

    def test_mailbox_irq_order(self):
        def swap(t, p):
            n = t.node("/soc/mbox@294608000")
            v = n.get("interrupts")
            n.set("interrupts", v[12:24] + v[0:12] + v[24:])
        self.refused(swap, "mailbox interrupts")

    def test_status_on_new_node(self):
        self.refused(lambda t, p: t.node("/soc/mtp@294600000").set("status", b"disabled\0"), "status")

    def test_wrong_iommu_stream(self):
        def bad(t, p):
            n = t.node("/soc/mtp@294600000")
            n.set("iommus", struct.pack(">2I", p["mtp_dart"], 7))
        self.refused(bad, "iommus")

    def test_helper_cpu_points_elsewhere(self):
        def bad(t, p):
            t.node("/soc/fifo@294b14000/input@8000").set("apple,helper-cpu", struct.pack(">I", p["mtp_dart"]))
        self.refused(bad, "hid references")

    def test_aliases_extra_property(self):
        self.refused(lambda t, p: t.node("/aliases").set("extra", b"/soc\0"), "aliases delta")


class AdtGuards(unittest.TestCase):
    def test_rejects_changed_compatible(self):
        data = json.loads(ADT.read_text())
        # break the DockChannel compatible and expect extraction to refuse
        stack = [data]
        while stack:
            n = stack.pop()
            if n["path"].endswith("/dockchannel-mtp") and "mtp-transport" not in n["path"]:
                n["values"]["compatible"] = ["dockchannel,t9999"]
            stack.extend(n.get("children", []))
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / "adt.json"
            tmp.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                mtp_adt.facts(tmp)


if __name__ == "__main__":
    unittest.main()
