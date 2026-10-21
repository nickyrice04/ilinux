#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only t6050/J716c topology audit; never authorizes a target operation.

Original project code. Inputs are the sanitized ADT and a retained Linux DTB.
No imports from vendor code, subprocesses, device access, or output files.
The existing original native/boot/fdt.py handles bounded FDT decoding.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys


REPO = Path(__file__).resolve().parents[3]
AFF2 = {"M": 4, "P": 1}
NAMES = {"M": "Performance", "P": "Super"}
EXPECTED_TYPES = {0: "M", 1: "M", 2: "P"}


class AuditError(ValueError):
    """The input does not establish the required topology invariant."""


def require(condition, reason):
    if not condition:
        raise AuditError(reason)


def integer(value, label):
    require(type(value) is int, label + " must be an integer")
    return value


def flatten_adt(root):
    """Select CPU/PMGR nodes; unrelated IORegistry overlays may repeat paths."""
    nodes = {}
    count = 0
    pending = [root]
    while pending:
        node = pending.pop()
        require(isinstance(node, dict), "invalid ADT node")
        path = node.get("path", "")
        require(isinstance(path, str) and (path == "/Root" or
                path == "/Root/device-tree" or path.startswith("/Root/device-tree/")),
                "unexpected sanitized ADT path")
        path = (path.removeprefix("/Root/device-tree") or "/")
        values = node.get("values", {})
        require(isinstance(values, dict), "invalid ADT values")
        if re.fullmatch(r"/cpus/cpu\d+", path) or path == "/arm-io/pmgr":
            require(path not in nodes, "duplicate selected ADT path")
            nodes[path] = values
        count += 1
        require(count <= 16384, "excessive ADT nodes")
        children = node.get("children", [])
        require(isinstance(children, list), "invalid ADT children")
        pending.extend(children)
    return nodes


def decode_layout(value):
    """Reject missing/malformed packing; never substitute four-bit stride."""
    require(isinstance(value, dict), "missing PMGR clusters descriptor")
    try:
        data = bytes.fromhex(value["hex"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditError("invalid PMGR clusters encoding") from exc
    require(value.get("len") == len(data) == 12,
            "expected three PMGR width/position pairs")
    pairs = list(struct.iter_unpack("<HH", data))
    used = 0
    for width, position in pairs:
        require(0 < width <= 32 and position + width <= 32,
                "PMGR cluster field outside 32-bit register")
        mask = ((1 << width) - 1) << position
        require(not used & mask, "overlapping PMGR cluster fields")
        used |= mask
    require(pairs == [(6, 0), (6, 6), (6, 12)],
            "PMGR descriptor does not match observed J716c three-by-six layout")
    return pairs


def adt_topology(nodes):
    paths = [p for p in nodes if re.fullmatch(r"/cpus/cpu\d+", p)]
    require(len(paths) == 18, "expected 18 physical CPUs")
    layout = decode_layout(nodes.get("/arm-io/pmgr", {}).get("clusters"))
    result = []
    ids, regs, mpidrs, die_bits = set(), set(), set(), set()
    for path in paths:
        value = nodes[path]
        cpu = integer(value.get("cpu-id"), "cpu-id")
        cluster = integer(value.get("cluster-id"), "cluster-id")
        require(cpu in range(18) and cpu not in ids, "duplicate/invalid CPU ID")
        require(path == "/cpus/cpu%d" % cpu, "CPU path/id mismatch")
        require(cluster in EXPECTED_TYPES, "unexpected CPU cluster")
        ctype = value.get("cluster-type")
        require(ctype == [EXPECTED_TYPES[cluster]], "CPU cluster/type mismatch")
        ctype = ctype[0]
        ranges = value.get("reg")
        require(isinstance(ranges, list) and len(ranges) == 1 and
                isinstance(ranges[0], dict), "invalid ADT CPU reg")
        try:
            reg = int(ranges[0]["addr"], 16)
        except (KeyError, TypeError, ValueError) as exc:
            raise AuditError("invalid ADT CPU reg encoding") from exc
        require(0 <= reg <= 0xFFFF, "ADT CPU reg must not be a full MPIDR")
        core = reg & 0xFF
        require(reg >> 8 == cluster and core < 6, "ADT reg/cluster/core mismatch")
        require(cpu == cluster * 6 + core, "CPU ID does not match observed layout")
        require(reg not in regs, "duplicate ADT reg")
        mpidr = (AFF2[ctype] << 16) | reg
        width, position = layout[cluster]
        require(core < width, "CPU outside PMGR cluster width")
        die_bit = position + core
        require(mpidr not in mpidrs and die_bit not in die_bits,
                "duplicate MPIDR/start bit")
        l2 = integer(value.get("l2-cache-size"), "l2-cache-size")
        require(l2 == (8 << 20 if ctype == "M" else 16 << 20),
                "unexpected cluster L2 size")
        ids.add(cpu)
        regs.add(reg)
        mpidrs.add(mpidr)
        die_bits.add(die_bit)
        result.append({"cpu_id": cpu, "cluster": cluster, "core": core,
                       "adt_type": ctype, "macos_class": NAMES[ctype],
                       "adt_reg": reg, "dt_mpidr": mpidr, "l2_bytes": l2,
                       "die_start_bit": die_bit, "cluster_start_bit": core})
    require(ids == set(range(18)), "incomplete CPU IDs")
    return sorted(result, key=lambda row: row["cpu_id"])


def u32(blob, label):
    require(isinstance(blob, bytes) and len(blob) == 4, label + " needs one cell")
    return struct.unpack(">I", blob)[0]


def strings(blob, label):
    require(isinstance(blob, bytes) and blob.endswith(b"\0"),
            label + " needs a terminated string")
    try:
        return blob[:-1].decode("ascii").split("\0")
    except UnicodeDecodeError as exc:
        raise AuditError("non-ASCII " + label) from exc


def audit_fdt(tree, cpus):
    """Validate full template structure; report status separately from facts."""
    compatible = strings(tree.get("/", {}).get("compatible"), "board compatible")
    require("apple,j716c" in compatible and "apple,t6050" in compatible,
            "expected t6050/J716c DT")
    parent = tree.get("/cpus", {})
    require(u32(parent.get("#address-cells"), "CPU address cells") == 2 and
            u32(parent.get("#size-cells"), "CPU size cells") == 0,
            "unexpected CPU cell layout")
    by_handle = {}
    for path, node in tree.items():
        if "phandle" in node:
            handle = u32(node["phandle"], "phandle")
            require(handle not in (0, 0xFFFFFFFF) and handle not in by_handle,
                    "duplicate/reserved phandle")
            by_handle[handle] = (path, node)
    cpu_nodes = {p: v for p, v in tree.items()
                 if p.startswith("/cpus/") and v.get("device_type") == b"cpu\0"}
    require(len(cpu_nodes) == 18, "DT must retain all 18 CPU descriptions")
    require(set(cpu_nodes) == {"/cpus/cpu@%x" % c["dt_mpidr"] for c in cpus},
            "DT CPU names omit Aff2 or mismatch canonical MPIDR")
    expected_map = {"/cpus/cpu-map"}
    expected_map.update("/cpus/cpu-map/cluster%d" % i for i in range(3))
    expected_map.update("/cpus/cpu-map/cluster%d/core%d" % (i, j)
                        for i in range(3) for j in range(6))
    require({p for p in tree if p.startswith("/cpus/cpu-map")} == expected_map,
            "cpu-map must contain three six-core clusters without SMT threads")
    shared = {name: {} for name in
              ("next-level-cache", "operating-points-v2", "performance-domains")}
    capacities, power, enabled = {}, {}, []
    for cpu in cpus:
        ident, cluster = cpu["cpu_id"], cpu["cluster"]
        path = "/cpus/cpu@%x" % cpu["dt_mpidr"]
        node = cpu_nodes[path]
        require(node.get("reg") == struct.pack(">Q", cpu["dt_mpidr"]),
                "DT reg must include core-type Aff2; raw ADT reg is insufficient")
        require(strings(node.get("compatible"), "CPU compatible") ==
                ["apple,sotra-" + cpu["adt_type"].lower()], "wrong CPU compatible")
        require(node.get("enable-method") == b"spin-table\0",
                "unexpected CPU enable-method")
        status = node.get("status", b"okay\0")
        require(status in (b"okay\0", b"ok\0", b"disabled\0"), "unknown CPU status")
        if status != b"disabled\0":
            enabled.append(ident)
        leaf = tree["/cpus/cpu-map/cluster%d/core%d" % (cluster, cpu["core"])]
        require(u32(leaf.get("cpu"), "cpu-map reference") ==
                u32(node.get("phandle"), "CPU phandle"),
                "cpu-map reference mismatches cluster/core")
        for key, groups in shared.items():
            handle = u32(node.get(key), key)
            require(handle in by_handle, "unresolved " + key)
            prior = groups.setdefault(cluster, handle)
            require(prior == handle, "cluster has split " + key)
        if "capacity-dmips-mhz" in node:
            capacity = u32(node["capacity-dmips-mhz"], "capacity-dmips-mhz")
            require(capacity > 0, "zero capacity")
            capacities[ident] = capacity
        if "dynamic-power-coefficient" in node:
            coefficient = u32(node["dynamic-power-coefficient"], "power coefficient")
            require(coefficient > 0, "zero power coefficient")
            power[ident] = coefficient
    require(len(capacities) in (0, 18), "partial capacity data would lose asymmetry")
    require(len(power) in (0, 18), "partial dynamic power model")
    for values, label in ((capacities, "capacity"), (power, "power coefficient")):
        for ctype in AFF2:
            require(len({values[c["cpu_id"]] for c in cpus
                         if c["adt_type"] == ctype and c["cpu_id"] in values}) <= 1,
                    "inconsistent " + label + " within one core type")
    controller_status = {}
    for key, groups in shared.items():
        require(len(set(groups.values())) == 3, "distinct clusters share " + key)
        for cluster, handle in groups.items():
            _, node = by_handle[handle]
            if key == "next-level-cache":
                require(u32(node.get("cache-level"), "L2 level") == 2 and
                        u32(node.get("cache-size"), "L2 size") ==
                        (8 << 20 if cluster < 2 else 16 << 20), "incorrect L2")
            elif key == "operating-points-v2":
                require(node.get("opp-shared") == b"", "missing shared cluster OPPs")
                require(node.get("compatible") == b"operating-points-v2\0",
                        "wrong OPP table compatible")
            else:
                require(u32(node.get("#performance-domain-cells"), "domain cells") == 0,
                        "unexpected performance domain arguments")
                require("apple,t6050-cluster-cpufreq" in
                        strings(node.get("compatible"), "cpufreq compatible"),
                        "wrong cluster cpufreq compatible")
                controller_status[str(cluster)] = strings(
                    node.get("status", b"okay\0"), "controller status")[0]
    return {"structure": "PASS", "template_enabled_cpu_ids": enabled,
            "cluster_cpufreq_status": controller_status,
            "capacity_validation": "UNCALIBRATED" if capacities else "ABSENT",
            "capacity_dmips_mhz_by_type": {
                t: capacities[c["cpu_id"]] for t in AFF2 for c in cpus
                if c["adt_type"] == t and c["cpu_id"] in capacities},
            "power_model_validation": "UNCALIBRATED" if power else "ABSENT",
            "dynamic_power_coefficient_by_type": {
                t: power[c["cpu_id"]] for t in AFF2 for c in cpus
                if c["adt_type"] == t and c["cpu_id"] in power},
            "runtime_online_cpu_ids": "NOT_OBSERVED"}


def legacy_collisions(cpus):
    groups = {}
    for cpu in cpus:
        bit = 4 * cpu["cluster"] + cpu["core"]
        groups.setdefault(bit, []).append(cpu["cpu_id"])
    return [{"legacy_bit": bit, "cpu_ids": ids}
            for bit, ids in sorted(groups.items()) if len(ids) > 1]


def read_bounded(path, limit):
    with path.open("rb") as stream:
        blob = stream.read(limit + 1)
    require(len(blob) <= limit, "input exceeds audit size bound")
    return blob


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adt", type=Path, default=REPO / "hardware/adt/adt-sanitized.json")
    parser.add_argument("--dtb", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    try:
        adt = read_bounded(args.adt, 16 << 20)
        cpus = adt_topology(flatten_adt(json.loads(adt)))
        report = {"schema": 1, "read_only": True, "hardware_operations": 0,
                  "scope": "t6050-j716c-offline-topology", "adt_sha256":
                  hashlib.sha256(adt).hexdigest(), "cpu_count": len(cpus),
                  "core_counts": {NAMES[t]: sum(c["adt_type"] == t for c in cpus)
                                  for t in AFF2}, "cpus": cpus,
                  "legacy_four_bit_stride_collisions": legacy_collisions(cpus),
                  "dtbs": [], "native_smp_verified": False,
                  "restart_authorized": False}
        if args.dtb:
            # This is original project code, not the external m1n1 Python client.
            sys.path.insert(0, str(REPO / "native/boot"))
            import fdt
            for path in args.dtb:
                blob = read_bounded(path, 4 << 20)
                item = audit_fdt(fdt.properties(blob), cpus)
                item["sha256"] = hashlib.sha256(blob).hexdigest()
                item["bytes"] = len(blob)
                report["dtbs"].append(item)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (AuditError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"schema": 1, "read_only": True, "hardware_operations": 0,
                          "structure": "FAIL", "error": str(exc),
                          "restart_authorized": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
