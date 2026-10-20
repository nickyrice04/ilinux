#!/usr/bin/env python3
"""Offline review model, never imported by the live launcher.

This historical proposal covers only the *unprepared input DT* gate. The
attempt-28 integration now lives in native/boot/cpu_observe.py and launch.py,
with exact image pins, final prepared-tree validation and userspace governor.
"""
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "native/boot"))
import make_cpufreq_dt as mk
import fdt

BASE_SHA = "17c55af9eb39ea799e254335176e9748193237dce3735f59cd286a63ea0a0405"
CANDIDATE_SHA = "aa9731d1ba8246a9441a85dcbf59bf65cfe82c7a8d33439e9d2cdc40cb0ee725"


def check_input(base_blob, candidate_blob, profile):
    if profile != "cpufreq-review-only":
        raise ValueError("separate reviewed cpufreq profile required")
    if hashlib.sha256(base_blob).hexdigest() != BASE_SHA:
        raise ValueError("base digest differs from boot042")
    fdt.check_stage_b(base_blob)
    if hashlib.sha256(candidate_blob).hexdigest() != CANDIDATE_SHA:
        raise ValueError("candidate digest differs from reviewed cpufreq delta")
    return {"offline_only": True, "native_authorized": False, "base": BASE_SHA, "candidate": CANDIDATE_SHA}


def candidate_bootargs(base_args):
    tokens = base_args.split()
    if tokens.count("cpufreq.off=1") != 1:
        raise ValueError("base must disable cpufreq exactly once")
    for required in ("maxcpus=1", "nr_cpus=1", "idle=nop", "arm64.nowfxt"):
        if tokens.count(required) != 1:
            raise ValueError("single-core and idle guard missing or duplicated")
    # Historical build-review proposal only; not the attempt-28 boot arguments.
    return " ".join(t for t in tokens if t != "cpufreq.off=1")
