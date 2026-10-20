"""Offline tests for make_cpufreq_dt.py: the exact delta, and every refusal of a base that is not the
reviewed shape.  Uses boot042's shipped Stage-B DT when job 050's export or the verified package is
there (skips otherwise), and synthetic edits of it for the refusals.  Nothing runs on hardware."""
import hashlib
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "native/boot"))
import make_cpufreq_dt as mk  # noqa: E402  (puts fdtedit and the generator on the path)
import fdt  # noqa: E402
import fdtedit  # noqa: E402

ADT = ROOT / "hardware/adt/adt-sanitized.json"
BASES = [p for p in (ROOT / "virtualization/jobs/050-boot042-keyboard/out/export/t6050-j716c-stage-b.dtb",
                     ROOT / "build/native-boot042/verified/t6050-j716c-stage-b.dtb") if p.is_file()]
BOOT042_SHA = "17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405"
C0, C2 = mk.CONTROLLERS[0][0], mk.CONTROLLERS[2][0]


def edited(blob, change):
    tree = fdtedit.parse(blob)
    change(tree)
    return fdtedit.encode(tree)


@unittest.skipUnless(BASES, "boot042's Stage-B DT is not extracted (job 050 export or build/)")
class RealBaseTests(unittest.TestCase):
    def tempdir(self):
        temp = __import__("tempfile").TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    @classmethod
    def setUpClass(cls):
        cls.base = BASES[0].read_bytes()
        cls.tables = mk.expected_tables(str(ADT))

    def test_base_is_boot042(self):
        self.assertEqual(hashlib.sha256(self.base).hexdigest(), BOOT042_SHA)
        fdt.check_stage_b(self.base)   # the committed launcher accepts the base

    def test_delta_and_determinism(self):
        tmp = self.tempdir()
        tmp_base = tmp / "base.dtb"
        tmp_base.write_bytes(self.base)
        blob1, delta, done = mk.run(str(tmp_base), str(ADT))
        blob2, _, _ = mk.run(str(tmp_base), str(ADT))
        self.assertEqual(blob1, blob2)
        self.assertEqual(delta["base_known_as"], "boot042 Stage-B (job 050)")
        self.assertEqual(sorted(len(v) for v in done.values()), [15, 15, 20])
        tree = fdt.properties(blob1)
        for path, _b, _t in mk.CONTROLLERS.values():
            self.assertNotIn("status", tree[path])
            self.assertEqual(tree[path]["compatible"], mk.CANDIDATE_COMPATIBLE)
        self.assertEqual(tree[mk.NVME]["status"], b"disabled\0")
        levels = [struct.unpack(">I", tree["/opp-table-2/opp%02d" % (i + 1)]["opp-level"])[0] for i in range(20)]
        self.assertEqual(levels, list(range(2, 22)))
        self.assertEqual(struct.unpack(">Q", tree["/opp-table-2/opp20"]["opp-hz"])[0], 4608000000)
        self.assertEqual(struct.unpack(">Q", tree["/opp-table-0/opp05"]["opp-hz"])[0], 2652000000)
        # the committed launcher refuses the result, by design, at the first enabled controller
        with self.assertRaises(ValueError) as caught:
            fdt.check_stage_b(blob1)
        self.assertEqual(str(caught.exception), "storage or cpufreq enabled: " + C0)
        # everything the committed guard checks besides the controllers still holds
        tree_edit = fdtedit.parse(blob1)
        for path, _b, _t in mk.CONTROLLERS.values():
            tree_edit.node(path).set("status", b"disabled\0")
        fdt.check_stage_b(fdtedit.encode(tree_edit))

    def test_unknown_base_refused(self):
        tmp = self.tempdir()
        path = tmp / "altered.dtb"
        path.write_bytes(edited(self.base, lambda t: t.node("/").set("model", b"changed\0")))
        with self.assertRaisesRegex(ValueError, "reviewed boot042 digest"):
            mk.run(path, ADT)

    def test_refusals(self):
        tmp = self.tempdir()

        def refused(name, change, message):
            path = tmp / (name + ".dtb")
            path.write_bytes(edited(self.base, change))
            with self.subTest(case=name), self.assertRaises((ValueError, AssertionError)) as caught:
                mk.build(fdtedit.parse(path.read_bytes()), self.tables)
            self.assertIn(message, str(caught.exception))

        refused("controller already enabled", lambda t: t.node(C0).delete("status"), "expected status disabled")
        refused("controller okay", lambda t: t.node(C0).set("status", b"okay\0"), "expected status disabled")
        refused("another compatible", lambda t: t.node(C2).set("compatible", b"apple,t8112-cluster-cpufreq\0"),
                "compatible is not the reviewed")
        refused("another reg", lambda t: t.node(C2).set("reg", struct.pack(">QQ", 0x212E20000, 0x2000)), "reg is not")
        refused("opp-level off", lambda t: t.node("/opp-table-0/opp03").set("opp-level", struct.pack(">I", 7)),
                "opp-level 7 is not row + 1")
        refused("opp-hz not the ADT's", lambda t: t.node("/opp-table-2/opp20").set("opp-hz", struct.pack(">Q", 4700000000)),
                "is not the ADT's")
        refused("a row missing", lambda t: t.node("/opp-table-1").children.pop(), "15 rows")

        def extra(t):
            node = fdtedit.Node("opp21")
            node.props = [["opp-hz", struct.pack(">Q", 4800000000), None], ["opp-level", struct.pack(">I", 21), None]]
            t.node("/opp-table-2").children.append(node)
        refused("a row added", extra, "21 OPP entries")
        refused("table not shared", lambda t: t.node("/opp-table-0").delete("opp-shared"), "not a shared")


class RenderTests(unittest.TestCase):
    def test_fragment_names_every_change(self):
        done = {c: [(1000000000 * (i + 1), i + 1, i + 2) for i in range(n)] for c, n in ((0, 15), (1, 15), (2, 20))}
        text = mk.render_dts(done)
        self.assertEqual(text.count("/delete-property/ status;"), 3)
        self.assertEqual(text.count("opp-level = <"), 50)
        self.assertIn("opp20 { opp-level = <21>; };", text)


if __name__ == "__main__":
    unittest.main()
