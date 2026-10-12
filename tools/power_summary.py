#!/usr/bin/env python3
"""Summarize powermon output (benchmarks/bin/powermon JSON lines) into
non-overlapping top-level SoC blocks.  Per-core / SRAM / DTL channels are
sub-components of "CPU Energy" and "GPU" is part of "GPU Energy", so only
the top-level channels are summed.
Usage: power_summary.py FILE.jsonl [label] ...   (or '-' for stdin)"""
import json, sys
TOP = ["CPU Energy", "GPU Energy", "ANE", "DRAM", "AMCC", "DCS", "FAB",
       "DISP", "DISPEXT", "AFR", "ISP", "AVE", "MSR"]
def summarize(line):
    d = json.loads(line)
    w = {k: d.get("avgW:" + k, 0.0) for k in TOP}
    out = {"seconds": d.get("seconds"), "cpu_W": w["CPU Energy"], "gpu_W": w["GPU Energy"],
           "ane_W": w["ANE"], "dram_W": w["DRAM"], "memctl_W": w["AMCC"] + w["DCS"],
           "fabric_W": w["FAB"], "display_W": w["DISP"] + w["DISPEXT"],
           "media_W": w["AFR"] + w["ISP"] + w["AVE"] + w["MSR"]}
    out["soc_W"] = round(sum(w.values()), 3)
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}
if __name__ == "__main__":
    args = sys.argv[1:] or ["-"]
    for i, path in enumerate(args):
        src = sys.stdin if path == "-" else open(path)
        for line in src:
            if line.startswith('{"bench":"power"'):
                print(json.dumps({"file": path, **summarize(line)}))
