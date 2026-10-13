#!/usr/bin/env python3
"""Run explicitly selected, digest-pinned REA queries in the Linux lab.

Raw results must remain in the ignored lab output. Each CLI invocation owns
and closes its provider session. Completed outputs are never overwritten.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("artifacts", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("ids", nargs="+", help="explicit target IDs from the plan")
    args = p.parse_args()
    if sys.platform != "linux":
        p.error("run only inside the isolated Linux analysis lab")
    plan = json.loads(args.plan.read_text())["targets"]
    selected = {row["id"]: row for row in plan}
    if len(selected) != len(plan) or len(set(args.ids)) != len(args.ids):
        p.error("duplicate target IDs")
    args.output.mkdir(parents=True, exist_ok=True)
    jobs = []
    for target_id in args.ids:
        if target_id not in selected or not re.fullmatch(r"[a-z0-9-]+", target_id):
            p.error("unknown or unsafe target ID")
        row = selected[target_id]
        if Path(row["artifact"]).name != row["artifact"]:
            p.error("artifact must be a basename")
        artifact = (args.artifacts / row["artifact"]).resolve(strict=True)
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != row["sha256"]:
            p.error("artifact digest differs from plan")
        if not re.fullmatch(r"0x[0-9a-f]{1,16}", row["address"]):
            p.error("invalid address")
        outputs = [args.output / (target_id + suffix)
                   for suffix in (".json", ".stderr", ".run.json")]
        if any(path.exists() for path in outputs):
            p.error("output exists; inspect/reuse it or select a new output directory")
        jobs.append((row, artifact, outputs))
    failed = False
    for row, artifact, outputs in jobs:
        command = ["timeout", "-k", "5", "90", "rea", "function",
                   str(artifact), row["address"], "--provider", "ghidra", "--format", "json"]
        started = time.monotonic()
        print("START", row["id"], flush=True)
        with outputs[0].open("xb") as out, outputs[1].open("xb") as err:
            result = subprocess.run(command, stdout=out, stderr=err, check=False)
        record = {"id": row["id"], "artifact_sha256": row["sha256"],
                  "exit_code": result.returncode,
                  "elapsed_seconds": round(time.monotonic() - started, 3),
                  "limit_seconds": 90, "command": command,
                  "semantic_validation": "not performed by runner"}
        outputs[2].write_text(json.dumps(record, indent=2) + "\n")
        failed |= result.returncode != 0
        print("DONE", row["id"], result.returncode, flush=True)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
