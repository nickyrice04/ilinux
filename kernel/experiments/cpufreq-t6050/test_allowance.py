#!/usr/bin/env python3
"""Mutate the candidate to test the separate offline allowance model."""
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import allowance_model as gate
import make_cpufreq_dt as mk
import fdt
import fdtedit

BASE = ROOT / "build/native-boot042/verified/t6050-j716c-stage-b.dtb"


@unittest.skipUnless(BASE.exists(), "requires extracted boot042 input")
class AllowanceTests(unittest.TestCase):
    def setUp(self):
        self.base = BASE.read_bytes()
        self.candidate, _, _ = mk.run(BASE, ROOT / "hardware/adt/adt-sanitized.json")

    def test_exact_candidate_is_offline_only(self):
        result = gate.check_input(self.base, self.candidate, "cpufreq-review-only")
        self.assertTrue(result["offline_only"])
        self.assertFalse(result["native_authorized"])
        with self.assertRaisesRegex(ValueError, "storage or cpufreq enabled"):
            fdt.check_stage_b(self.candidate)

    def test_profiles_fail_closed(self):
        for profile in (None, "", "omarchy", "storage", "cpufreq"):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                gate.check_input(self.base, self.candidate, profile)

    def test_foreign_base(self):
        with self.assertRaisesRegex(ValueError, "base digest"):
            gate.check_input(self.base + b"\0", self.candidate, "cpufreq-review-only")

    def test_mutation_refusals(self):
        for path, prop, val in (
            (mk.NVME, "status", b"okay\0"),
            ("/soc/performance-controller@210e20000", "compatible", mk.COMPATIBLE),
            ("/soc/performance-controller@211e20000", "status", b"disabled\0"),
            ("/opp-table-0/opp01", "opp-level", b"\0\0\0\1"),
            ("/opp-table-0/opp01", "opp-hz", b"\0" * 8),
            ("/", "compatible", b"apple,foreign\0"),
        ):
            with self.subTest(path=path, prop=prop):
                tree = fdtedit.parse(self.candidate)
                tree.node(path).set(prop, val)
                with self.assertRaisesRegex(ValueError, "candidate digest"):
                    gate.check_input(self.base, fdtedit.encode(tree), "cpufreq-review-only")

    def test_args_change_only_cpufreq(self):
        args = "ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt clk_ignore_unused"
        self.assertEqual(gate.candidate_bootargs(args), args.replace("cpufreq.off=1 ", ""))
        for bad in (args.replace("nr_cpus=1", "nr_cpus=18"), args + " cpufreq.off=1", args.replace("idle=nop ", "")):
            with self.subTest(args=bad), self.assertRaises(ValueError):
                gate.candidate_bootargs(bad)


if __name__ == "__main__":
    unittest.main()
