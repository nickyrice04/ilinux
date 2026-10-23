#!/usr/bin/env python3
"""Synthetic vectors/faults and retained sanitized ADT; no hardware operations."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("gpu31p_contract", HERE / "contract.py")
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
ADT = REPO / "hardware/adt/adt-sanitized.json"
ADT_SHA = "6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af"
# Independently specified synthetic byte vector, also checked by the C suite.
GOLDEN = bytes.fromhex("00406655443322110000ddccbbaa9988008077665544332200400000efbeadde")
SAMPLE = c.Segment(0x1122334455664000, 0x8899AABBCCDD0000,
                   0x2233445566778000, 0x4000, 0xDEADBEEF)


class CodecTests(unittest.TestCase):
    def test_golden_decode(self):
        self.assertEqual(c.decode_segments(GOLDEN), (SAMPLE,))

    def test_golden_encode(self):
        self.assertEqual(c.encode_segments([SAMPLE]), GOLDEN)

    def test_lengths(self):
        for size in list(range(32)) + [33, 1025]:
            with self.subTest(size=size), self.assertRaises(c.Refusal):
                c.decode_segments(b"\0" * size)

    def test_cell_width_types(self):
        for value in [True, False, -1, 1 << 32, "-1", "0x100000000", "1", None, 1.0, {}, []]:
            with self.subTest(value=value), self.assertRaises(c.Refusal):
                c.cell(value)

    def test_cell_order_high_bits(self):
        cells = ["0x1000000", "0x100", "0x0", "0xfffffc00",
                 "0x1000000", "0x100", "0x4000", "0xdeadbeef"]
        s = c.from_cells(cells)[0]
        self.assertEqual(s.descriptor_phys, 0x10001000000)
        self.assertEqual(s.iova, 0xFFFFFC0000000000)
        self.assertEqual(s.opaque, 0xDEADBEEF)

    def test_bad_cell_count(self):
        for cells in [[], [0] * 7, [0] * 9, [0] * 264, "0x0", {}]:
            with self.subTest(cells=type(cells).__name__), self.assertRaises(c.Refusal):
                c.from_cells(cells)

    def test_invalid_fields(self):
        for field in range(5):
            for value in [True, -1, 1 << (64 if field < 3 else 32), 1.0, None]:
                changed = list(SAMPLE)
                changed[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(c.Refusal):
                    c.encode_segments([c.Segment(*changed)])

    def test_segment_type_and_count(self):
        for value in [[], [tuple(SAMPLE)], [SAMPLE] * 33, None, True]:
            with self.assertRaises(c.Refusal):
                c.validate_segments(value)

    def test_zero_span(self):
        with self.assertRaises(c.Refusal):
            c.encode_segments([SAMPLE._replace(size=0)])

    def test_overflow_domains(self):
        for name in c.Segment._fields[:3]:
            with self.subTest(name=name), self.assertRaises(c.Refusal):
                c.encode_segments([SAMPLE._replace(**{name: c.U64 - SAMPLE.size + 1})])

    def test_last_valid_span(self):
        sample = c.Segment(c.U64 - 1, c.U64 - 1, c.U64 - 1, 1, c.U32)
        self.assertEqual(c.decode_segments(c.encode_segments([sample])), (sample,))

    def test_alignment_is_explicit_policy(self):
        self.assertEqual(c.validate_segments([SAMPLE], 16384), (SAMPLE,))
        for name in c.Segment._fields[:4]:
            s = SAMPLE._replace(**{name: getattr(SAMPLE, name) + 1})
            self.assertEqual(c.decode_segments(c.encode_segments([s])), (s,))
            with self.assertRaises(c.Refusal):
                c.validate_segments([s], 16384)
        for granule in [0, 3, -1, True, 1 << 32]:
            with self.assertRaises(c.Refusal):
                c.validate_segments([SAMPLE], granule)

    def test_overlap_each_domain_and_adjacent(self):
        second = c.Segment(*(v + SAMPLE.size for v in SAMPLE[:3]), SAMPLE.size, 1)
        self.assertEqual(len(c.validate_segments([SAMPLE, second])), 2)
        for name in c.Segment._fields[:3]:
            with self.assertRaises(c.Refusal):
                c.validate_segments([SAMPLE, second._replace(**{name: getattr(second, name) - 1})])

    def test_all_counts_roundtrip(self):
        all_segments = [c.Segment(0x10000000000 + i * 32768,
                                 0xFFFFFC0000000000 + i * 32768,
                                 0x20000000000 + i * 32768, 16384, c.U32 - i)
                        for i in range(c.MAX_SEGMENTS)]
        for count in range(1, c.MAX_SEGMENTS + 1):
            self.assertEqual(c.decode_segments(c.encode_segments(all_segments[:count])),
                             tuple(all_segments[:count]))


class ADTTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree, digest = c.read_adt(ADT)
        if digest != ADT_SHA:
            raise AssertionError("retained ADT pin mismatch")

    def setUp(self):
        self.tree = copy.deepcopy(self.__class__.tree)
        self.nodes = c.index_tree(self.tree)

    def values(self, suffix):
        return self.nodes[c.ARM + suffix]["values"]

    def test_actual_retained_contract(self):
        report = c.inspect_adt(self.tree)
        self.assertEqual(report["status"], "STRUCTURAL_PASS")
        self.assertEqual(report["role_count"], 2)
        self.assertEqual(report["hardware_operations"], 0)
        self.assertEqual(report["gpu_enablement"], "HOLD")
        self.assertEqual(report["descriptor_cpu_address_domain"], "UNQUALIFIED")
        self.assertEqual([r["descriptor_address_bits"] for r in report["roles"]], [41, 41])
        self.assertEqual([r["segment_sizes"] for r in report["roles"]],
                         [[0x4C000, 0x130000], [0x54000, 0x130000]])
        self.assertEqual(report["cross_role_iova_overlaps"], 3)

    def test_machine_identity_mismatch(self):
        for suffix, compatible in [("/sgx", ["gpu,t8132"]), ("", ["arm-io,t8142"]),
                                   ("/gfx-asc", ["iop,ascwrap-v4"])]:
            tree = copy.deepcopy(self.tree)
            c.index_tree(tree)[c.ARM + suffix]["values"]["compatible"] = compatible
            with self.assertRaises(c.Refusal):
                c.inspect_adt(tree)

    def test_role_swap_refused(self):
        self.values("/gfx-asc")["role"] = ["GFX1"]
        with self.assertRaises(c.Refusal):
            c.inspect_adt(self.tree)

    def test_same_mapper_required(self):
        self.values("/gfx1-asc")["iommu-parent"] += 1
        with self.assertRaises(c.Refusal):
            c.inspect_adt(self.tree)

    def test_phandle_renumbering_is_structural(self):
        self.values("/mapper-gfx-asc")["AAPL,phandle"] = 90000
        self.values("/gfx-asc")["iommu-parent"] = 90000
        self.values("/gfx1-asc")["iommu-parent"] = 90000
        self.assertEqual(c.inspect_adt(self.tree)["status"], "STRUCTURAL_PASS")

    def test_bool_identifier_refused(self):
        for suffix, key in [("/gfx-asc", "iop-version"), ("/mapper-gfx-asc", "AAPL,phandle"),
                            ("/gfx-asc", "interrupt-parent"), ("/gfx-asc", "iommu-parent")]:
            tree = copy.deepcopy(self.tree)
            c.index_tree(tree)[c.ARM + suffix]["values"][key] = True
            with self.assertRaises(c.Refusal):
                c.inspect_adt(tree)

    def test_parent_nub_mismatch(self):
        self.values("/gfx-asc/iop-gfx-nub")["segment-ranges"][-1] = "0xa5"
        with self.assertRaises(c.Refusal):
            c.inspect_adt(self.tree)

    def test_opaque_word_survives(self):
        for suffix in ["/gfx-asc", "/gfx-asc/iop-gfx-nub"]:
            self.values(suffix)["segment-ranges"][-1] = "0x12345678"
        report = c.inspect_adt(self.tree)
        self.assertEqual(report["roles"][0]["nonzero_opaque_words"], 2)

    def test_iova_overlap_between_roles_is_valid(self):
        # The real two roles share IOVA ranges, while each role is non-overlapping.
        report = c.inspect_adt(self.tree)
        self.assertGreater(report["cross_role_iova_overlaps"], 0)

    def test_aggregate_mmio_overlap_is_valid(self):
        sgx, asc = self.values("/sgx")["reg"][0], self.values("/gfx-asc")["reg"][0]
        self.assertLess(c.cell(sgx["addr"], 64), c.cell(asc["addr"], 64))
        self.assertGreater(c.cell(sgx["addr"], 64) + c.cell(sgx["size"], 64),
                           c.cell(asc["addr"], 64) + c.cell(asc["size"], 64))
        c.inspect_adt(self.tree)

    def test_register_and_interrupt_identity(self):
        for key in ["reg", "interrupts", "clock-gates", "power-gates", "interrupt-parent"]:
            tree = copy.deepcopy(self.tree)
            c.index_tree(tree)[c.ARM + "/sgx"]["values"][key] = []
            with self.assertRaises(c.Refusal):
                c.inspect_adt(tree)

    def test_missing_node(self):
        arm = self.nodes[c.ARM]
        arm["children"] = [n for n in arm["children"] if n["path"] != c.ARM + "/gfx1-asc"]
        with self.assertRaises(c.Refusal):
            c.inspect_adt(self.tree)

    def test_duplicate_path(self):
        self.nodes[c.ARM]["children"].append(copy.deepcopy(self.nodes[c.ARM + "/sgx"]))
        with self.assertRaises(c.Refusal):
            c.inspect_adt(self.tree)

    def test_duplicate_phandle(self):
        self.values("/gfx1-asc")["AAPL,phandle"] = self.values("/gfx-asc")["AAPL,phandle"]
        with self.assertRaises(c.Refusal):
            c.inspect_adt(self.tree)

    def test_bad_tree_shape(self):
        for field, value in [("children", {}), ("values", []), ("property_names", [True]),
                             ("path", True)]:
            tree = copy.deepcopy(self.tree)
            tree[field] = value
            with self.assertRaises(c.Refusal):
                c.inspect_adt(tree)

    def test_depth_and_cycle_bounds(self):
        tree = {"path": "/test", "values": {}, "property_names": [], "children": []}
        cur = tree
        for _ in range(65):
            child = {"path": cur["path"] + "/a", "values": {}, "property_names": [], "children": []}
            cur["children"].append(child)
            cur = child
        with self.assertRaises(c.Refusal):
            c.index_tree(tree)
        self.tree["children"].append(self.tree)
        with self.assertRaises(c.Refusal):
            c.index_tree(self.tree)

    def test_property_presence_does_not_mean_ready(self):
        report = c.inspect_adt(self.tree)
        self.assertTrue(report["property_presence_only"]["gptbat-ready"])
        self.assertEqual(report["uat_layout"], "UNKNOWN")
        self.assertEqual(report["firmware_abi"], "UNKNOWN")
        self.assertEqual(report["cpu_memory_reservations_generated"], 0)

    def test_unknown_data_is_not_emitted(self):
        # Unknown content may exist in retained metadata but must not be echoed.
        marker = "SYNTHETIC_SENTINEL_DO_NOT_ECHO"
        self.values("/sgx")["unused-test-property"] = marker
        self.nodes[c.ARM + "/sgx"]["property_names"].append("unused-test-property")
        self.assertNotIn(marker, json.dumps(c.inspect_adt(self.tree)))


class ReaderCLITests(unittest.TestCase):
    def setUp(self):
        (REPO / "build").mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="gpu31p-test-", dir=REPO / "build")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "test.json"

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", str(HERE / "contract.py"), *args],
                              capture_output=True, text=True, timeout=20)

    def test_reject_duplicate_and_nonfinite_json(self):
        for text in ['{"x":0,"x":1}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}',
                     '{"x":1e999}', '{"x":-1e999}']:
            self.path.write_text(text)
            with self.assertRaises(c.Refusal):
                c.read_adt(self.path)

    def test_bad_utf8_and_json_cli_fixed(self):
        for raw in [b"\xff", b"PRIVATE_TEST_SENTINEL", b"[]"]:
            self.path.write_bytes(raw)
            result = self.run_cli("--adt", str(self.path))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, "")
            self.assertNotIn("PRIVATE_TEST_SENTINEL", result.stdout)
            self.assertEqual(json.loads(result.stdout)["status"], "REFUSED")

    def test_argparse_never_echoes_input(self):
        for args in [("--bad-SYNTHETIC_SENTINEL",), ("--adt",), ("--live",)]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, "")
            self.assertEqual(json.loads(result.stdout),
                             {"status": "REFUSED", "reason": "ARGUMENTS", "hardware_operations": 0})

    def test_regular_file_only(self):
        self.path.write_text("{}")
        link = self.path.with_name("symlink")
        link.symlink_to(self.path)
        for path in [link, self.path.parent]:
            with self.assertRaises(c.Refusal):
                c.read_adt(path)
        fifo = self.path.with_name("pipe")
        os.mkfifo(fifo)
        with self.assertRaises(c.Refusal):
            c.read_adt(fifo)

    def test_file_size_limit(self):
        self.path.write_bytes(b"")
        with self.assertRaises(c.Refusal):
            c.read_adt(self.path)
        with self.path.open("wb") as stream:
            stream.truncate(c.MAX_FILE + 1)
        with self.assertRaises(c.Refusal):
            c.read_adt(self.path)

    def test_actual_cli(self):
        result = self.run_cli("--adt", str(ADT))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["sanitized_adt_sha256"], ADT_SHA)
        self.assertEqual(report["hardware_operations"], 0)
        self.assertNotIn(str(REPO), result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
