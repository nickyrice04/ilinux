#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original synthetic fixtures and negative regression cases; no hardware."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit
import capture_linux


def cell(value):
    return struct.pack(">I", value)


def adt_fixture():
    nodes = {"/arm-io/pmgr": {"clusters": {
        "hex": struct.pack("<6H", 6, 0, 6, 6, 6, 12).hex(), "len": 12}}}
    for i in range(18):
        cluster, core = divmod(i, 6)
        nodes["/cpus/cpu%d" % i] = {
            "cpu-id": i, "cluster-id": cluster,
            "cluster-type": ["M" if i < 12 else "P"],
            "reg": [{"addr": hex(cluster << 8 | core), "size": "0x0"}],
            "l2-cache-size": 8 << 20 if i < 12 else 16 << 20,
        }
    return nodes


def dt_fixture(cpus):
    tree = {"/": {"compatible": b"apple,j716c\0apple,t6050\0"},
            "/cpus": {"#address-cells": cell(2), "#size-cells": cell(0)},
            "/cpus/cpu-map": {}}
    for c in range(3):
        tree["/cpus/cpu-map/cluster%d" % c] = {}
        tree["/l2-%d" % c] = {"phandle": cell(30 + c), "cache-level": cell(2),
                               "cache-size": cell(8 << 20 if c < 2 else 16 << 20)}
        tree["/opp-%d" % c] = {"phandle": cell(40 + c), "opp-shared": b"",
                                "compatible": b"operating-points-v2\0"}
        tree["/perf-%d" % c] = {"phandle": cell(50 + c), "status": b"disabled\0",
                                 "compatible": b"apple,t6050-cluster-cpufreq\0",
                                 "#performance-domain-cells": cell(0)}
    for cpu in cpus:
        i, c, k = cpu["cpu_id"], cpu["cluster"], cpu["core"]
        tree["/cpus/cpu-map/cluster%d/core%d" % (c, k)] = {"cpu": cell(i + 1)}
        tree["/cpus/cpu@%x" % cpu["dt_mpidr"]] = {
            "device_type": b"cpu\0", "reg": struct.pack(">Q", cpu["dt_mpidr"]),
            "compatible": ("apple,sotra-" + cpu["adt_type"].lower()).encode() + b"\0",
            "phandle": cell(i + 1), "enable-method": b"spin-table\0",
            "next-level-cache": cell(30 + c), "operating-points-v2": cell(40 + c),
            "performance-domains": cell(50 + c),
            "capacity-dmips-mhz": cell(768 if c < 2 else 1024),
            "dynamic-power-coefficient": cell(550 if c < 2 else 1054),
        }
    return tree


class TopologyAudit(unittest.TestCase):
    def setUp(self):
        self.adt = adt_fixture()
        self.cpus = audit.adt_topology(self.adt)
        self.dt = dt_fixture(self.cpus)

    def rejects_adt(self, text=None):
        with self.assertRaisesRegex(audit.AuditError, text or "."):
            audit.adt_topology(self.adt)

    def rejects_dt(self, text=None):
        with self.assertRaisesRegex(audit.AuditError, text or "."):
            audit.audit_fdt(self.dt, self.cpus)

    def test_exact_two_types_three_clusters_and_no_smt(self):
        self.assertEqual([c["dt_mpidr"] for c in self.cpus[::6]],
                         [0x40000, 0x40100, 0x10200])
        self.assertEqual([c["adt_type"] for c in self.cpus], ["M"] * 12 + ["P"] * 6)
        self.assertEqual([c["die_start_bit"] for c in self.cpus], list(range(18)))
        self.assertEqual(audit.audit_fdt(self.dt, self.cpus)["structure"], "PASS")

    def test_raw_adt_reg_is_not_canonical_dt_mpidr(self):
        self.dt["/cpus/cpu@40001"]["reg"] = struct.pack(">Q", 1)
        self.rejects_dt("Aff2")

    def test_already_encoded_mpidr_in_adt_is_rejected(self):
        self.adt["/cpus/cpu1"]["reg"][0]["addr"] = "0x40001"
        self.rejects_adt("full MPIDR")

    def test_unknown_efficiency_type_never_defaults(self):
        self.adt["/cpus/cpu1"]["cluster-type"] = ["E"]
        self.rejects_adt("type mismatch")

    def test_swapped_marketing_type_detected(self):
        self.adt["/cpus/cpu12"]["cluster-type"] = ["M"]
        self.rejects_adt("type mismatch")

    def test_duplicate_cpu_id_detected(self):
        self.adt["/cpus/cpu1"]["cpu-id"] = 0
        self.rejects_adt("CPU ID")

    def test_cluster_and_raw_reg_disagreement_detected(self):
        self.adt["/cpus/cpu6"]["reg"][0]["addr"] = "0x200"
        self.rejects_adt("cluster/core mismatch")

    def test_missing_cpu_detected(self):
        del self.adt["/cpus/cpu17"]
        self.rejects_adt("18 physical")

    def test_missing_layout_does_not_fallback_to_four(self):
        del self.adt["/arm-io/pmgr"]["clusters"]
        self.rejects_adt("missing PMGR")

    def test_legacy_stride_has_four_crosscluster_collisions(self):
        self.assertEqual(audit.legacy_collisions(self.cpus), [
            {"legacy_bit": 4, "cpu_ids": [4, 6]},
            {"legacy_bit": 5, "cpu_ids": [5, 7]},
            {"legacy_bit": 8, "cpu_ids": [10, 12]},
            {"legacy_bit": 9, "cpu_ids": [11, 13]}])
        self.assertEqual(self.cpus[1]["die_start_bit"], 1)

    def test_overlapping_widths_rejected(self):
        self.adt["/arm-io/pmgr"]["clusters"]["hex"] = struct.pack(
            "<6H", 6, 0, 6, 4, 6, 8).hex()
        self.rejects_adt("overlapping")

    def test_descriptor_size_and_range_rejected(self):
        for values in ((6, 0, 6, 6, 40, 12), (6, 0, 6, 6, 6, 31)):
            with self.subTest(values=values):
                self.adt["/arm-io/pmgr"]["clusters"]["hex"] = struct.pack("<6H", *values).hex()
                self.rejects_adt("outside 32-bit")

    def test_crosscluster_cpu_map_swap_rejected(self):
        self.dt["/cpus/cpu-map/cluster0/core1"]["cpu"] = cell(7)
        self.rejects_dt("cpu-map reference")

    def test_duplicate_phandle_rejected(self):
        self.dt["/cpus/cpu@40001"]["phandle"] = cell(1)
        self.rejects_dt("duplicate/reserved")

    def test_invented_smt_rejected(self):
        self.dt["/cpus/cpu-map/cluster0/core0/thread0"] = {"cpu": cell(1)}
        self.rejects_dt("without SMT")

    def test_partial_capacity_rejected(self):
        del self.dt["/cpus/cpu@40001"]["capacity-dmips-mhz"]
        self.rejects_dt("partial capacity")

    def test_placeholder_capacity_never_certified(self):
        result = audit.audit_fdt(self.dt, self.cpus)
        self.assertEqual(result["capacity_validation"], "UNCALIBRATED")
        self.assertEqual(result["power_model_validation"], "UNCALIBRATED")
        self.assertEqual(result["runtime_online_cpu_ids"], "NOT_OBSERVED")

    def test_alternative_arbitrary_capacity_never_certified(self):
        for node in self.dt.values():
            if "capacity-dmips-mhz" in node:
                node["capacity-dmips-mhz"] = cell(999)
        self.assertEqual(audit.audit_fdt(self.dt, self.cpus)["capacity_validation"],
                         "UNCALIBRATED")

    def test_absent_capacity_is_explicit(self):
        for node in self.dt.values():
            node.pop("capacity-dmips-mhz", None)
        self.assertEqual(audit.audit_fdt(self.dt, self.cpus)["capacity_validation"], "ABSENT")

    def test_zero_and_inconsistent_capacity_rejected(self):
        for value in (0, 1024):
            with self.subTest(value=value):
                self.dt["/cpus/cpu@40001"]["capacity-dmips-mhz"] = cell(value)
                self.rejects_dt("capacity")

    def test_split_shared_opp_domain_rejected(self):
        self.dt["/cpus/cpu@40001"]["operating-points-v2"] = cell(41)
        self.rejects_dt("split operating-points")

    def test_collapsed_performance_domains_rejected(self):
        for c in self.cpus[6:12]:
            self.dt["/cpus/cpu@%x" % c["dt_mpidr"]]["performance-domains"] = cell(50)
        self.rejects_dt("distinct clusters")

    def test_wrong_l2_size_rejected(self):
        self.dt["/l2-2"]["cache-size"] = cell(8 << 20)
        self.rejects_dt("incorrect L2")

    def test_cpu_disabled_status_is_not_missing_topology(self):
        for c in self.cpus[1:]:
            self.dt["/cpus/cpu@%x" % c["dt_mpidr"]]["status"] = b"disabled\0"
        self.assertEqual(audit.audit_fdt(self.dt, self.cpus)["template_enabled_cpu_ids"], [0])

    def test_duplicate_cpu_adt_path_rejected_but_unrelated_overlays_allowed(self):
        child = {"path": "/Root/device-tree/cpus/cpu0", "values": {}}
        overlay = {"path": "/Root/device-tree/other", "values": {}}
        root = {"path": "/Root", "children": [child, overlay, copy.deepcopy(overlay)]}
        self.assertEqual(set(audit.flatten_adt(root)), {"/cpus/cpu0"})
        root["children"].append(copy.deepcopy(child))
        with self.assertRaisesRegex(audit.AuditError, "duplicate selected"):
            audit.flatten_adt(root)

    def test_real_sanitized_adt_consistent_with_synthetic_fixture(self):
        data = json.loads((audit.REPO / "hardware/adt/adt-sanitized.json").read_bytes())
        self.assertEqual(audit.adt_topology(audit.flatten_adt(data)), self.cpus)


class RuntimeCapture(unittest.TestCase):
    def write(self, root, name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else value.encode())

    def test_cpuset_parser_rejects_malformed_and_unbounded_inputs(self):
        self.assertEqual(capture_linux.cpu_list("0-5,12-17"), list(range(6)) + list(range(12, 18)))
        for bad in ("0-9999999", "5-2", "0,0", "0-3,2", "1,x", "-1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                capture_linux.cpu_list(bad)

    def test_mpidr_classification_does_not_confuse_aff2_or_aff3(self):
        self.assertEqual(capture_linux.identity(0x80040001)["macos_class"], "Performance")
        self.assertEqual(capture_linux.identity(0x80010200)["macos_class"], "Super")
        self.assertIsNone(capture_linux.identity(1))
        self.assertIsNone(capture_linux.identity(0x180040001))

    def test_runtime_fixture_is_read_only_and_one_core_not_smp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "online", "0\n")
            self.write(root, "cpu0/of_node/reg", struct.pack(">Q", 0x40000))
            self.write(root, "cpu0/cpu_capacity", "768\n")
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = capture_linux.capture(root)
            after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertTrue(result["fixture"])
            found = result["interpretation"]
            self.assertIn("all_18_cores_not_online", found["findings"])
            self.assertEqual(found["capacity_calibration"], "NOT_ESTABLISHED")
            self.assertIsNone(found["identities"]["0"]["observed_hardware_identity"])

    def test_logical_linux_id_not_assumed_to_equal_adt_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "online", "0\n")
            self.write(root, "cpu0/of_node/reg", struct.pack(">Q", 0x10200))
            result = capture_linux.capture(root)["interpretation"]
            self.assertEqual(result["identities"]["0"]["expected_identity_from_dt"]["adt_cpu_id"], 12)

    def test_hardware_identity_mismatch_does_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "online", "0\n")
            self.write(root, "cpu0/of_node/reg", struct.pack(">Q", 0x40000))
            self.write(root, "cpu0/regs/identification/mpidr_el1", "0x80010200\n")
            result = capture_linux.capture(root)["interpretation"]
            self.assertIn("hardware_and_dt_identity_mismatch_cpu0", result["findings"])

    def test_oversize_and_binary_inputs_remain_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "field"
            path.write_bytes(b"1" * 257)
            self.assertEqual(capture_linux.read_field(path)["reason"], "oversize")
            path.write_bytes(bytes(4))
            self.assertFalse(capture_linux.read_field(path, binary=True)["available"])


if __name__ == "__main__":
    unittest.main()
