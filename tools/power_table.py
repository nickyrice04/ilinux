#!/usr/bin/env python3
"""Median SoC power per label from a labelled powermon power.jsonl (e.g. from
benchmarks/vm/vm_power_states.sh).  Usage: power_table.py power.jsonl"""
import json, statistics, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from power_summary import summarize
rows = {}
for line in open(sys.argv[1]):
    d = json.loads(line)
    rows.setdefault(d["label"], []).append(summarize(line))
cols = ["soc_W", "cpu_W", "gpu_W", "dram_W", "memctl_W", "fabric_W", "display_W"]
print("| state | n | " + " | ".join(cols) + " | soc_W per rep |")
print("|---" * (len(cols) + 3) + "|")
for label, rs in rows.items():
    med = [statistics.median(r[c] for r in rs) for c in cols]
    print(f"| {label} | {len(rs)} | " + " | ".join(f"{v:.3f}" for v in med) +
          " | " + ", ".join(f"{r['soc_W']:.2f}" for r in rs) + " |")
