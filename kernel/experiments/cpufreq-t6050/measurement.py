#!/usr/bin/env python3
"""Read-only Linux snapshot for a separately approved DVFS experiment.

Never reads /dev/mem or writes sysfs. Driver-reported frequencies are explicitly
requested state estimates, not an independent CPU clock measurement. Missing
thermal/energy telemetry is null, not zero and not evidence of safety.
"""
import argparse
import json
from pathlib import Path
import time


def read(path):
    try:
        return path.read_text().strip()
    except (OSError, UnicodeError):
        return None


def snapshot(root=Path("/")):
    cpus = root / "sys/devices/system/cpu"
    policies = {}
    for policy in sorted((cpus / "cpufreq").glob("policy[0-9]*")):
        policies[policy.name] = {name: read(policy / name) for name in (
            "scaling_driver", "scaling_governor", "scaling_cur_freq", "cpuinfo_cur_freq",
            "scaling_min_freq", "scaling_max_freq", "scaling_available_frequencies", "related_cpus")}
    thermal = {}
    for zone in sorted((root / "sys/class/thermal").glob("thermal_zone[0-9]*")):
        thermal[zone.name] = {"type": read(zone / "type"), "temp_mC": read(zone / "temp")}
    return {"schema": 1, "monotonic_ns": time.monotonic_ns(), "read_only": True,
            "frequency_semantics": "requested p-state table mapping; not measured frequency",
            "online_cpus": read(cpus / "online"), "policies": policies,
            "thermal_zones": thermal or None, "energy_joules": None,
            "power_watts": None, "uptime": read(root / "proc/uptime")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    if not 1 <= args.samples <= 30 or not 0.1 <= args.interval <= 2:
        parser.error("bounded collection requires 1..30 samples and 0.1..2 second interval")
    for i in range(args.samples):
        print(json.dumps(snapshot(), sort_keys=True), flush=True)
        if i + 1 < args.samples:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
