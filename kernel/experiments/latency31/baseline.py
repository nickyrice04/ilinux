#!/usr/bin/env python3
"""Bounded original CPU/STREAM reference. No sysctl, MMIO or global changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time


def run(args, timeout=45):
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=timeout).stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    p.add_argument("--cpu", type=int, default=0)
    p.add_argument("--context", choices=["native-macos", "linux-vm", "native-linux"], required=True)
    a = p.parse_args()
    if (platform.system() == "Darwin") != (a.context == "native-macos"):
        p.error("context does not match operating system")
    a.out.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[3]
    flags = ["-O3", "-march=armv8.4-a", "-pthread"]
    record = {"schema": 1, "context": a.context, "system": platform.system(),
              "release": platform.release(), "machine": platform.machine(),
              "compiler": run(["cc", "--version"]).splitlines()[0], "flags": flags,
              "page_size": os.sysconf("SC_PAGE_SIZE"), "sources": {}, "samples": [],
              "limits": "One thread. QoS is not affinity. VM is not native Linux. Clock is an ADD estimate. No energy measurement."}
    if platform.system() == "Darwin":
        record["os_build"] = run(["sw_vers", "-buildVersion"]).strip()
        record["power_source"] = "AC" if "AC Power" in run(["pmset", "-g", "batt"]) else "battery-or-unknown"
    for name in ("cpubench", "membench"):
        src = repo / "benchmarks/src" / (name + ".c")
        record["sources"][name] = hashlib.sha256(src.read_bytes()).hexdigest()
        run(["cc", *flags, str(src), "-o", str(a.out / name)], timeout=60)
    src=Path(__file__).resolve().with_name('pixels.c')
    record['sources']['pixels']=hashlib.sha256(src.read_bytes()).hexdigest()
    run(['cc',*flags,str(src),'-o',str(a.out/'pixels')],timeout=60)
    # Save compiler output privately so instruction loops can be compared.
    run(["cc", *flags, "-S", str(repo / "benchmarks/src/cpubench.c"), "-o", str(a.out / "cpubench.s")], timeout=60)
    placements = ["default", "bg"] if platform.system() == "Darwin" else ["affinity"]
    for placement in placements:
        prefix = (["taskpolicy", "-b"] if placement == "bg" else []) if platform.system() == "Darwin" else ["taskset", "-c", str(a.cpu)]
        for kernel in ("freq", "fma_asm", "intmix"):
            cmd = [str(a.out / "cpubench"), kernel, "-t", "1", "-r", "5", "-s", "0.15"]
            cmd += ["-q", placement] if platform.system() == "Darwin" else ["-c", str(a.cpu)]
            rows = [json.loads(x) for x in run(prefix + cmd).splitlines()]
            record["samples"].append({"placement": placement, "kernel": kernel, "rows": rows})
        for mib in (16, 128):
            cmd = [str(a.out / "membench"), "stream", "-t", "1", "-r", "8", "-m", str(mib)]
            rows = [json.loads(x) for x in run(prefix + cmd).splitlines()]
            record["samples"].append({"placement": placement, "kernel": "stream", "array_mib": mib, "rows": rows})
        rows=[json.loads(x) for x in run(prefix+[str(a.out/'pixels')]).splitlines()]
        record['samples'].append({'placement':placement,'kernel':'pixels','rows':rows})
        (a.out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
        time.sleep(2)
    (a.out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
