#!/usr/bin/env python3
"""Candidate Stage-B DT with CPU frequency scaling allowed (DT only; offline, NOT RUN).

usage: python3 -I make_cpufreq_dt.py BASE_DTB ADT_JSON OUT_DTB DELTA_JSON [--dts OUT.dtsi]

Takes a shipped Stage-B DT (boot042's by default; only the exact reviewed boot042 digest is accepted) and
changes exactly three things, from the findings in README.md:

* the three cluster DVFS controllers ``/soc/performance-controller@21{0,1,2}e20000`` lose
  ``status = "disabled"`` (the launcher's committed guard refuses the result on purpose; the
  offline allowance model in this directory tests the proposed exception; the live launcher is unchanged);
* each controller loses the t8112 fallback compatible, preventing an old module from
  reading the unreviewed status register;
* every ``opp-level`` becomes ``table row + 2``: existing REA findings support DESIRED1 = 2 + row (native mapping unverified) for the CPU
  domains. P-states 0 and 1 have no entries in the candidate OPP table.  The ``opp-hz``
  values are checked against this Mac's own ADT voltage-states tables before any row is
  touched, so the result carries only states macOS itself uses on this unit.

Nothing else changes; check() proves it. The byte-exact DTB editor comes from
kernel/experiments/usb-gadget-dt/fdtedit.py; the ADT decode from the t6050-dt generator.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "usb-gadget-dt"))
sys.path.insert(0, str(HERE.parent / "t6050-dt"))
import fdtedit  # noqa: E402
import gen_t6050_dt  # noqa: E402

KNOWN_BASES = {
    "17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405": "boot042 Stage-B (job 050)",
}
COMPATIBLE = b"apple,t6050-cluster-cpufreq\0apple,t8112-cluster-cpufreq\0"
# cluster -> (controller path, its reg, the OPP table path); the bases are the ADT pmgr reg
# entries of size 0x12e8 at the cluster window + 0xe20000 (gen_t6050_dt.py), the tables the
# generator's opp-table-<cluster> nodes.
CONTROLLERS = {
    0: ("/soc/performance-controller@210e20000", 0x210E20000, "/opp-table-0"),
    1: ("/soc/performance-controller@211e20000", 0x211E20000, "/opp-table-1"),
    2: ("/soc/performance-controller@212e20000", 0x212E20000, "/opp-table-2"),
}
NVME = "/soc/nvme@45dcc0000"
CANDIDATE_COMPATIBLE = b"apple,t6050-cluster-cpufreq\0"
OFFSET_BASE, OFFSET_NEW = 1, 2      # opp-level = row + OFFSET: the base's convention, the new one


def u32(value):
    if value is None or len(value) != 4:
        raise ValueError("expected one cell, got %r" % (value,))
    return struct.unpack(">I", value)[0]


def u64(value):
    if value is None or len(value) != 8:
        raise ValueError("expected two cells, got %r" % (value,))
    return struct.unpack(">Q", value)[0]


def reg2(addr, size):
    return struct.pack(">QQ", addr, size)


def expected_tables(adt_json):
    """{cluster: [(hz, core_uv), ...]} from this Mac's ADT, as the generator decodes it."""
    nodes = gen_t6050_dt.load(adt_json)
    return {cluster: ops for cluster, (_table, ops) in gen_t6050_dt.dvfs_tables(nodes).items()}


def opp_children(table):
    """The OPP entries of a table node in row order (opp01, opp02, ...)."""
    rows = [n for n in table.children if n.name.startswith("opp")]
    if [n.name for n in rows] != ["opp%02d" % (i + 1) for i in range(len(rows))]:
        raise ValueError("%s: OPP entries are not opp01..opp%02d in order" % (table.name, len(rows)))
    return rows


# --------------------------------------------------------------------------- build

def build(tree, tables):
    """Apply the delta in place; return {cluster: [(hz, old level, new level), ...]}."""
    done = {}
    for cluster, (path, base, table_path) in CONTROLLERS.items():
        node = tree.node(path)
        if node.get("compatible") != COMPATIBLE:
            raise ValueError("%s: compatible is not the reviewed t6050/t8112 pair" % path)
        if node.get("reg") != reg2(base, 0x1000):
            raise ValueError("%s: reg is not <%#x 0x1000>" % (path, base))
        if node.get("#performance-domain-cells") != struct.pack(">I", 0):
            raise ValueError("%s: #performance-domain-cells is not 0" % path)
        if node.get("status") != b"disabled\0":
            raise ValueError("%s: expected status disabled in the base DT" % path)
        node.delete("status")
        node.set("compatible", CANDIDATE_COMPATIBLE)
        table = tree.node(table_path)
        if table.get("compatible") != b"operating-points-v2\0" or not table.has("opp-shared"):
            raise ValueError("%s: not a shared operating-points-v2 table" % table_path)
        rows = opp_children(table)
        if len(rows) != len(tables[cluster]):
            raise ValueError("%s: %d OPP entries, the ADT has %d rows for cluster %d"
                             % (table_path, len(rows), len(tables[cluster]), cluster))
        levels = []
        for i, (row, (hz, _uv)) in enumerate(zip(rows, tables[cluster])):
            if u64(row.get("opp-hz")) != hz:
                raise ValueError("%s/%s: opp-hz %d is not the ADT's %d Hz" % (table_path, row.name, u64(row.get("opp-hz")), hz))
            if u32(row.get("opp-level")) != i + OFFSET_BASE:
                raise ValueError("%s/%s: opp-level %d is not row + %d" % (table_path, row.name, u32(row.get("opp-level")), OFFSET_BASE))
            row.set("opp-level", struct.pack(">I", i + OFFSET_NEW))
            levels.append((hz, i + OFFSET_BASE, i + OFFSET_NEW))
        done[cluster] = levels
    return done


# --------------------------------------------------------------------------- check

def check(base, new, tables):
    """Prove the new tree differs from the base only by the planned delta."""
    before, after = fdtedit.flat(base), fdtedit.flat(new)
    if set(before) != set(after):
        raise AssertionError("node set changed: +%r -%r" % (sorted(set(after) - set(before)), sorted(set(before) - set(after))))
    planned = {path for path, _, _ in CONTROLLERS.values()}
    for cluster, (_path, _base, table_path) in CONTROLLERS.items():
        planned |= {"%s/opp%02d" % (table_path, i + 1) for i in range(len(tables[cluster]))}
    changed = {p for p in before if before[p] != after[p]}
    if changed != planned:
        raise AssertionError("unexpected modified nodes: %r" % sorted(changed ^ planned))
    for path, _base, _table in CONTROLLERS.values():
        lost = set(before[path]) - set(after[path])
        if lost != {"status"} or set(after[path]) - set(before[path]):
            raise AssertionError("%s: property delta wrong" % path)
        if after[path]["compatible"] != CANDIDATE_COMPATIBLE:
            raise AssertionError("candidate must not match the unreviewed t8112 fallback")
        for key in after[path]:
            if key != "compatible" and before[path][key] != after[path][key]:
                raise AssertionError("%s: property %s changed" % (path, key))
    for cluster, (_path, _base, table_path) in CONTROLLERS.items():
        levels = []
        for i in range(len(tables[cluster])):
            row = "%s/opp%02d" % (table_path, i + 1)
            if set(before[row]) != set(after[row]):
                raise AssertionError("%s: property set changed" % row)
            for key in after[row]:
                if key == "opp-level":
                    if (u32(before[row][key]), u32(after[row][key])) != (i + OFFSET_BASE, i + OFFSET_NEW):
                        raise AssertionError("%s: opp-level delta wrong" % row)
                elif before[row][key] != after[row][key]:
                    raise AssertionError("%s: property %s changed" % (row, key))
            levels.append(u32(after[row]["opp-level"]))
        if levels != list(range(OFFSET_NEW, OFFSET_NEW + len(tables[cluster]))) or max(levels) > 31:
            raise AssertionError("%s: levels are not %d..%d" % (table_path, OFFSET_NEW, OFFSET_NEW + len(tables[cluster]) - 1))
    # the CPUs point at the enabled controllers and at the tables of their own cluster
    handles = {u32(after[path]["phandle"]): cluster for cluster, (path, _b, _t) in CONTROLLERS.items()}
    tables_by_handle = {u32(after[table]["phandle"]): cluster for cluster, (_p, _b, table) in CONTROLLERS.items()}
    cpus = 0
    for path, props in after.items():
        if not path.startswith("/cpus/cpu@"):
            continue
        cpus += 1
        mpidr = u64(props["reg"])
        cluster = (mpidr >> 8) & 0xFF
        if handles.get(u32(props["performance-domains"])) != cluster:
            raise AssertionError("%s: performance-domains is not cluster %d's controller" % (path, cluster))
        if tables_by_handle.get(u32(props["operating-points-v2"])) != cluster:
            raise AssertionError("%s: operating-points-v2 is not cluster %d's table" % (path, cluster))
    if cpus != 18:
        raise AssertionError("expected 18 CPU nodes, found %d" % cpus)
    if after[NVME].get("status") != b"disabled\0":
        raise AssertionError("the NVMe controller must stay disabled")
    for path, _b, _t in CONTROLLERS.values():
        if "status" in after[path]:
            raise AssertionError("%s still has a status" % path)


# --------------------------------------------------------------------------- render

def render_dts(done):
    """Review text for the delta (a fragment, not a complete DTS)."""
    out = ["// SPDX-License-Identifier: GPL-2.0+ OR MIT",
           "/*",
           " * CPU frequency scaling delta for t6050 / J716c: DRAFT, generated by",
           " * kernel/experiments/cpufreq-t6050/make_cpufreq_dt.py from a shipped Stage-B DT and",
           " * hardware/adt/adt-sanitized.json.  Not booted.  Each controller below loses",
           ' * status = "disabled"; each OPP entry gets opp-level = row + 2 (macOS writes',
           " * DESIRED1 = 2 + row; native state-to-frequency mapping remains unverified).",
           " */", ""]
    for cluster, (path, base, table_path) in CONTROLLERS.items():
        out.append("&cpufreq%d {\t/* %s */" % (cluster, path))
        out.append("\t/delete-property/ status;")
        out.append('\tcompatible = "apple,t6050-cluster-cpufreq";')
        out.append("};")
        out.append("")
        out.append("&cluster%d_opp {\t/* %s */" % (cluster, table_path))
        for i, (hz, old, new) in enumerate(done[cluster]):
            out.append("\topp%02d { opp-level = <%d>; };\t/* was <%d>; %d MHz */" % (i + 1, new, old, hz // 1000000))
        out.append("};")
        out.append("")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- main

def run(base_path, adt_json):
    base_blob = Path(base_path).read_bytes()
    base_sha = hashlib.sha256(base_blob).hexdigest()
    if base_sha not in KNOWN_BASES:
        raise ValueError("base DTB is not the reviewed boot042 digest")
    tables = expected_tables(adt_json)
    tree = fdtedit.parse(base_blob)
    if fdtedit.encode(fdtedit.parse(base_blob)) != base_blob:
        raise AssertionError("fdtedit round trip failed on the base DTB")
    base_tree = fdtedit.parse(base_blob)
    done = build(tree, tables)
    new_blob = fdtedit.encode(tree)
    check(base_tree, fdtedit.parse(new_blob), tables)
    delta = {
        "base_sha256": base_sha,
        "base_known_as": KNOWN_BASES.get(base_sha, "unreviewed"),
        "out_sha256": hashlib.sha256(new_blob).hexdigest(),
        "out_size": len(new_blob),
        "controllers_enabled": [path for path, _b, _t in CONTROLLERS.values()],
        "opp_level": "row + %d (was row + %d)" % (OFFSET_NEW, OFFSET_BASE),
        "levels": {str(c): [{"opp": "opp%02d" % (i + 1), "hz": hz, "level": new} for i, (hz, _o, new) in enumerate(rows)]
                   for c, rows in done.items()},
        "nvme_status": "disabled",
    }
    return new_blob, delta, done


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("base_dtb")
    parser.add_argument("adt_json")
    parser.add_argument("out_dtb")
    parser.add_argument("delta_json")
    parser.add_argument("--dts", help="also write the review fragment")
    args = parser.parse_args(argv)
    new_blob, delta, done = run(args.base_dtb, args.adt_json)
    Path(args.out_dtb).write_bytes(new_blob)
    Path(args.delta_json).write_text(json.dumps(delta, indent=1) + "\n")
    if args.dts:
        Path(args.dts).write_text(render_dts(done))
    print("base %s (%s) -> %s (%d bytes, %s): 3 controllers enabled, %d OPP levels now row + %d; NVMe disabled"
          % (delta["base_sha256"][:16], delta["base_known_as"], delta["out_sha256"][:16], delta["out_size"],
             args.out_dtb, sum(len(r) for r in done.values()), OFFSET_NEW))
    return 0


if __name__ == "__main__":
    sys.exit(main())
