#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded, read-only CPU sysfs capture for an already-authorized Linux boot.

No hotplug, clock changes, MMIO, debugfs, benchmarks, commands, or output files.
Absence/permission errors remain unknown. DT identities are NOT hardware reads.
--sysfs-root supports offline fixtures and labels their results accordingly.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys


CPU_ROOT = Path("/sys/devices/system/cpu")
TEXT_PATHS = (
    "online", "cpu_capacity", "topology/physical_package_id", "topology/cluster_id",
    "topology/core_id", "topology/cluster_cpus_list", "topology/core_cpus_list",
    "topology/thread_siblings_list", "regs/identification/midr_el1",
    "regs/identification/mpidr_el1", "cpufreq/related_cpus", "cpufreq/affected_cpus",
    "cpufreq/scaling_driver", "cpufreq/scaling_governor", "cpufreq/scaling_cur_freq",
    "cpufreq/cpuinfo_cur_freq", "cpufreq/cpuinfo_max_freq", "cpufreq/scaling_min_freq",
    "cpufreq/scaling_max_freq",
)
EXPECTED = {((4 if cluster < 2 else 1) << 16) | (cluster << 8) | core:
            {"adt_cpu_id": cluster * 6 + core, "cluster": cluster, "core": core,
             "adt_type": "M" if cluster < 2 else "P",
             "macos_class": "Performance" if cluster < 2 else "Super"}
            for cluster in range(3) for core in range(6)}


def read_field(path, binary=False):
    try:
        with path.open("rb") as stream:
            data = stream.read(257)
        if len(data) > 256:
            return {"available": False, "reason": "oversize"}
        if binary:
            if len(data) != 8:
                return {"available": False, "reason": "expected_64_bit_dt_reg"}
            return {"available": True, "value": struct.unpack(">Q", data)[0]}
        text = data.decode("ascii").strip()
        if not re.fullmatch(r"[A-Za-z0-9_,. +:/()=\-]*", text):
            return {"available": False, "reason": "unexpected_text_encoding"}
        return {"available": True, "value": text}
    except OSError as exc:
        return {"available": False, "errno": exc.errno}
    except UnicodeDecodeError:
        return {"available": False, "reason": "non_ascii"}


def cpu_list(text):
    if not text:
        return []
    values = set()
    for part in text.split(","):
        if not re.fullmatch(r"\d+(?:-\d+)?", part):
            raise ValueError("malformed CPU list")
        ends = [int(x) for x in part.split("-")]
        first, last = ends[0], ends[-1]
        if not 0 <= first <= last < 512:
            raise ValueError("CPU list outside bounded range")
        group = set(range(first, last + 1))
        if group & values:
            raise ValueError("duplicate CPU list entry")
        values.update(group)
    return sorted(values)


def identity(value):
    """ARM MPIDR affinity fields only, including Aff3; do not default unknowns."""
    return EXPECTED.get(value & 0xFF00FFFFFF)


def inspect_snapshot(snapshot):
    findings = []
    online = snapshot["global"]["online"]
    online_ids = cpu_list(online["value"]) if online["available"] else None
    if online_ids is None:
        findings.append("online_cpu_set_unknown")
    elif len(online_ids) != 18:
        findings.append("all_18_cores_not_online")
    mapped = set()
    by_cpu = {}
    for row in snapshot["cpus"]:
        data = row["fields"]
        dt = data["of_node/reg"]
        dt_identity = identity(dt["value"]) if dt["available"] else None
        # DT reg must be affinity-only; accepting bit31 here would mask a bug.
        if dt_identity and dt["value"] not in EXPECTED:
            dt_identity = None
        hardware = data["regs/identification/mpidr_el1"]
        hw_identity = None
        if hardware["available"]:
            try:
                raw = int(hardware["value"], 16)
                if not 0 <= raw < 1 << 64:
                    raise ValueError("MPIDR range")
                hw_identity = identity(raw)
            except ValueError:
                findings.append("invalid_hardware_mpidr_cpu%d" % row["linux_cpu"])
        if dt_identity:
            ident = dt_identity["adt_cpu_id"]
            if ident in mapped:
                findings.append("duplicate_dt_identity")
            mapped.add(ident)
        else:
            findings.append("dt_identity_unknown_cpu%d" % row["linux_cpu"])
        if hardware["available"] and hw_identity != dt_identity:
            findings.append("hardware_and_dt_identity_mismatch_cpu%d" % row["linux_cpu"])
        by_cpu[str(row["linux_cpu"])] = {
            "expected_identity_from_dt": dt_identity,
            "observed_hardware_identity": hw_identity,
        }
    if online_ids is not None and not set(online_ids).issubset(
            {r["linux_cpu"] for r in snapshot["cpus"]}):
        findings.append("online_cpu_missing_from_capture")
    return {"online_cpu_ids": online_ids, "identities": by_cpu,
            "findings": sorted(set(findings)), "capacity_calibration": "NOT_ESTABLISHED",
            "frequency_invariance": "NOT_ESTABLISHED", "performance_parity": "NOT_ESTABLISHED",
            "cache_coherency": "NOT_ESTABLISHED", "native_smp_verified": False}


def capture(root):
    snapshot = {"schema": 1, "read_only": True, "sysfs_writes": 0,
                "mmio_operations": 0, "fixture": root != CPU_ROOT,
                "global": {name: read_field(root / name)
                           for name in ("online", "possible", "present", "offline")},
                "cpus": []}
    paths = sorted((p for p in root.iterdir() if re.fullmatch(r"cpu\d+", p.name)),
                   key=lambda p: int(p.name[3:]))
    if len(paths) > 64 or any(int(p.name[3:]) >= 512 for p in paths):
        raise ValueError("CPU directories exceed capture bound")
    for path in paths:
        row = {"linux_cpu": int(path.name[3:]), "fields": {
            name: read_field(path / name) for name in TEXT_PATHS}}
        row["fields"]["of_node/reg"] = read_field(path / "of_node/reg", binary=True)
        row["cache"] = [{name: read_field(path / "cache" / ("index%d" % i) / name)
                         for name in ("level", "type", "size", "shared_cpu_list")}
                        for i in range(4)]
        snapshot["cpus"].append(row)
    snapshot["interpretation"] = inspect_snapshot(snapshot)
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sysfs-root", type=Path, default=CPU_ROOT)
    args = parser.parse_args(argv)
    if args.sysfs_root == CPU_ROOT and not sys.platform.startswith("linux"):
        parser.error("real CPU sysfs capture requires Linux; use a fixture for offline tests")
    try:
        print(json.dumps(capture(args.sysfs_root), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"read_only": True, "sysfs_writes": 0, "error": str(exc)}),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
