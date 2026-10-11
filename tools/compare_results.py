#!/usr/bin/env python3
"""Compare two benchmark result directories (JSONL from benchmarks/src/*)
and print a Markdown parity table: candidate / reference x 100% for
higher-is-better metrics, reference / candidate x 100% for lower-is-better.

Only rows present in both runs with the same benchmark, kernel/test and
thread count are compared.  macOS QoS variants other than the given
--ref-qos are ignored so placement policy differences don't skew rows.

Usage: compare_results.py REF_DIR CAND_DIR [--ref-qos ui] [--title T]
"""
import argparse
import json
from pathlib import Path

LOWER_IS_BETTER_UNITS = {"ns", "us"}


def load(d, qos):
    rows = {}
    for name in ("cpu.jsonl", "mem.jsonl", "storage.jsonl"):
        p = Path(d) / name
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == "unsupported":
                continue
            if r.get("qos") not in (None, "none", qos):
                continue
            b = r["bench"]
            if b == "cpu":
                key = (b, r["kernel"], r.get("threads", 1))
                val, unit = r.get("aggregate_median", r.get("median")), r["unit"]
            elif b == "mem":
                t = r["test"]
                if t.startswith("stream"):
                    # medians: vCPU preemption in VMs produces impossible "best" outliers
                    key, val, unit = (b, t, r["threads"]), r["median"], r["unit"]
                elif t.startswith("latency"):
                    key = (b, "%s%s" % (t, "_dit" if r.get("dit") else ""), r["size_KiB"])
                    val, unit = r["best"], r["unit"]
                else:
                    key, val, unit = (b, t, r["MiB"]), r["median"], r["unit"]
            elif b == "storage":
                key = (b, r["test"], r["threads"])
                if r["test"].startswith("rand"):
                    val, unit = r["IOPS"], "IOPS"
                else:
                    val, unit = r["MB_per_s"], "MB/s"
            else:
                continue
            rows[key] = (val, unit)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref")
    ap.add_argument("cand")
    ap.add_argument("--ref-qos", default="ui")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    ref, cand = load(a.ref, a.ref_qos), load(a.cand, a.ref_qos)
    if a.title:
        print("### " + a.title + "\n")
    print("| bench | test | threads / size | unit | reference | candidate | parity |")
    print("|---|---|---|---|---|---|---|")
    for key in sorted(set(ref) & set(cand), key=lambda k: (k[0], k[1], k[2])):
        (rv, unit), (cv, _) = ref[key], cand[key]
        if not rv or not cv:
            continue
        par = (rv / cv if unit in LOWER_IS_BETTER_UNITS else cv / rv) * 100
        print("| %s | %s | %s | %s | %.4g | %.4g | %.1f%% |" % (key[0], key[1], key[2], unit, rv, cv, par))


if __name__ == "__main__":
    main()
