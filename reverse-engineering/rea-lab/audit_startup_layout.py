#!/usr/bin/env python3
"""Audit a sanitized ADT against the public m1n1 four-bit cluster formula.

The u16 count/start interpretation is a hypothesis until native validation;
raw bytes and per-CPU declared masks are independently retained as evidence.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def nodes(node):
    yield node
    for child in node.get("children", []):
        yield from nodes(child)


def audit(data):
    tree = json.loads(data)
    allnodes = list(nodes(tree))
    pmgr = [n for n in allnodes if n.get("path", "").endswith("/arm-io/pmgr")]
    if len(pmgr) != 1:
        raise ValueError("expected one PMGR node")
    raw = bytes.fromhex(pmgr[0]["values"]["clusters"]["hex"])
    if len(raw) % 4 or not raw or len(raw) > 128:
        raise ValueError("unsupported cluster table shape")
    clusters = list(struct.iter_unpack("<HH", raw))
    cpus = []
    legacy = {}
    used = set()
    for node in allnodes:
        v = node.get("values", {})
        if "function-enable_core" not in v:
            continue
        fields = bytes.fromhex(v["function-enable_core"]["hex"])
        if len(fields) != 12 or fields[4:8] != b"eroC":
            raise ValueError("unexpected Core platform-function encoding")
        phandle, selector, declared = struct.unpack("<III", fields)
        affinity = int(v["reg"][0]["addr"], 0)
        die, cluster, core = (affinity >> 11) & 15, (affinity >> 8) & 7, affinity & 255
        if die or cluster >= len(clusters):
            raise ValueError("this experiment only admits a single-die table")
        n, first = clusters[cluster]
        if not 0 < n <= 32 or core >= n or first + n > 32:
            raise ValueError("cluster or bit outside 32-bit layout")
        candidate = 1 << (first + core)
        if candidate in used:
            raise ValueError("candidate layout has duplicate masks")
        used.add(candidate)
        legacy_bit = 4 * cluster + core
        legacy.setdefault(legacy_bit, []).append(v["cpu-id"])
        cpus.append({"cpu_id": v["cpu-id"], "adt_affinity": hex(affinity),
                     "cluster": cluster, "core": core,
                     "adt_core_selector_mask": hex(declared),
                     "candidate_global_mask": hex(candidate),
                     "candidate_matches_selector": candidate == declared,
                     "legacy_bit": legacy_bit})
    if not cpus or len(cpus) != sum(n for n, _ in clusters):
        raise ValueError("CPU inventory does not cover candidate layout")
    return {"adt_sha256": hashlib.sha256(data).hexdigest(), "cluster_bytes": raw.hex(),
            "candidate_cluster_records": [{"count": n, "first_bit": first} for n, first in clusters],
            "cpus": sorted(cpus, key=lambda x: x["cpu_id"]),
            "legacy_collisions": [{"bit": b, "cpu_ids": ids} for b, ids in sorted(legacy.items()) if len(ids) > 1],
            "register_semantics_validated": False,
            "meaning": "Supports testing the existing SMP layout hypothesis; does not prove the cause of failed secondary entry"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sanitized_adt", type=Path)
    args = p.parse_args()
    print(json.dumps(audit(args.sanitized_adt.read_bytes()), indent=2))
