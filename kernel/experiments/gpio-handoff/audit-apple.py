#!/usr/bin/env python3
"""Cross-check completed driver dossiers with retained bytes and Apple LLVM.

Run on the reference host using its existing xcrun/LLVM. No target executes.
Raw disassembly goes only to the supplied ignored raw-output directory.
"""
import argparse
import importlib.util
import json
import re
import subprocess
from pathlib import Path

_spec = importlib.util.spec_from_file_location("evidence_gate", Path(__file__).resolve().parents[3]/"reverse-engineering/rea-lab/check_evidence.py")
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)
inspect = _gate.inspect


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("lab", type=Path)
    p.add_argument("summary", type=Path)
    p.add_argument("--carrier", type=Path, help="explicit read-only original carrier for a non-kernel plan")
    args = p.parse_args()
    carrier = (args.carrier or (args.lab / "artifacts/kernelcache.macho")).read_bytes()
    results = []
    plan = json.loads(args.plan.read_text())
    for row in plan["targets"]:
        target_id = row["id"]
        if not re.fullmatch(r"[a-z0-9-]+", target_id) or Path(row["artifact"]).name != row["artifact"]:
            p.error("unsafe target name")
        artifact = args.lab / row["artifact"]
        evidence_path = args.lab / (target_id + ".json")
        evidence = json.loads(evidence_path.read_text())
        manifest = json.loads(artifact.with_suffix(artifact.suffix + ".json").read_text())
        if manifest["derived_sha256"] != row["sha256"] or manifest["source_sha256"] != plan["carrier_sha256"]:
            raise ValueError("plan provenance mismatch")
        result = inspect(evidence, manifest, carrier, artifact.read_bytes())
        if evidence["normalized_result"]["procedure"]["address"] != row["address"]:
            raise ValueError("REA resolved a different function entry")
        raw = []
        words = 0
        unknown = []
        for anchor in result["body_anchors"]:
            start, end = int(anchor["start"], 16), int(anchor["end_inclusive"], 16)
            output = subprocess.check_output([
                "xcrun", "llvm-objdump", "--disassemble",
                "--start-address=" + hex(start), "--stop-address=" + hex(end + 1),
                str(artifact)], text=True)
            raw.append(output)
            seen = set()
            for line in output.splitlines():
                match = re.match(r"^([0-9a-f]+):\s+([0-9a-f]{8})\s+(.*)$", line)
                if not match:
                    continue
                address, word, instruction = int(match[1], 16), int(match[2], 16), match[3]
                if address not in range(start, end + 1, 4) or address in seen:
                    raise ValueError("LLVM returned an unexpected instruction address")
                offset = anchor["carrier_offset"] + address - start
                if word.to_bytes(4, "little") != carrier[offset:offset + 4]:
                    raise ValueError("LLVM instruction word differs from original carrier")
                seen.add(address)
                if "<unknown>" in instruction or instruction.startswith(".word"):
                    unknown.append(hex(address))
            if seen != set(range(start, end + 1, 4)):
                raise ValueError("LLVM does not cover the entire REA body")
            words += len(seen)
        evidence_path.with_suffix(".llvm.txt").write_text("\n".join(raw))
        result.update({"id": target_id, "llvm_instruction_words_verified": words,
                       "llvm_unknown_instructions": unknown})
        results.append(result)
    args.summary.write_text(json.dumps({"provider": plan["provider"],
        "carrier_sha256": plan["carrier_sha256"], "results": results,
        "limits": ["Static consistency only, not semantic or runtime equivalence",
                   "Rejected pseudocode cannot guide implementation; manual gates are not passes"]}, indent=2) + "\n")
    print(json.dumps({"functions": len(results), "instruction_words": sum(
        x["llvm_instruction_words_verified"] for x in results)}))


if __name__ == "__main__":
    main()
