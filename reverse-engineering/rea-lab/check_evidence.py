#!/usr/bin/env python3
"""Gate REA native dossiers against original bytes and provider body bounds.

This is a consistency check, not independent semantic verification. High-pcode
outside the reported function invalidates whole-function pseudocode inference.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(evidence, manifest, carrier, derived):
    if sha(carrier) != manifest["source_sha256"] or sha(derived) != manifest["derived_sha256"]:
        raise ValueError("artifact provenance digest mismatch")
    if evidence["subject"]["digest"]["sha256"] != sha(derived):
        raise ValueError("REA evidence describes another artifact")
    value = evidence["normalized_result"]
    body = value["procedure"]["body"]
    if not body.get("available"):
        raise ValueError("function body unavailable")
    ranges = [(int(r["start"], 16), int(r["end"], 16)) for r in body["ranges"]]
    expected = set()
    anchors = []
    for start, end in ranges:
        size = end - start + 1
        if start % 4 or size <= 0 or size % 4 or size > 1024 * 1024:
            raise ValueError("invalid bounded ARM64 body range")
        mappings = [m for m in manifest["mappings"]
                    if int(m["vmaddr"], 16) <= start and end < int(m["vmaddr"], 16) + m["bytes"]]
        if len(mappings) != 1:
            raise ValueError("body does not map uniquely to retained source bytes")
        m = mappings[0]
        offset = start - int(m["vmaddr"], 16)
        oldoff, newoff = m["source_offset"] + offset, m["derived_offset"] + offset
        old, new = carrier[oldoff:oldoff + size], derived[newoff:newoff + size]
        if len(old) != size or len(new) != size or old != new:
            raise ValueError("function bytes changed during extraction")
        addresses = set(range(start, end + 1, 4))
        if expected & addresses:
            raise ValueError("overlapping body ranges")
        expected |= addresses
        anchors.append({"start": hex(start), "end_inclusive": hex(end),
                        "carrier_offset": oldoff, "derived_offset": newoff,
                        "bytes": size, "sha256": sha(old)})
    actual = [int(line.split(":", 1)[0], 16) for line in value["assembly"]]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("assembly addresses do not cover exactly the provider body")
    operations = value.get("native_value_flow", {}).get("operations", [])
    outside = [op for op in operations if op.get("address", "").startswith("0x")
               and not any(a <= int(op["address"], 16) <= b for a, b in ranges)]
    pseudo = value.get("pseudocode", "")
    truncated = any(marker in pseudo for marker in
                    ("halt_baddata", "Truncating control flow", "Control flow encountered bad instruction"))
    warnings = []
    if truncated:
        warnings.append("bad_instruction_or_truncated_control_flow")
    if "Could not recover jumptable" in pseudo:
        warnings.append("unresolved_indirect_jump")
    if "Removing unreachable block" in pseudo:
        warnings.append("provider_removed_blocks")
    gate = "manual_review_required"
    if truncated:
        gate = "rejected_truncated_control_flow"
    if outside:
        gate = "rejected_cross_boundary"
    # Ghidra-derived membership tags are not sufficient: compare numeric PCs.
    return {
        "evidence_id": evidence["evidence_id"],
        "member": manifest["member"], "function": value["procedure"]["name"],
        "body_anchors": anchors, "assembly_instructions": len(actual),
        "original_bytes_verified": True,
        "pcode_operations": len(operations), "pcode_outside_body": len(outside),
        "outside_addresses": sorted({op["address"] for op in outside}),
        "pseudocode_gate": gate, "decompiler_warning_classes": warnings,
        "limits": ["No semantic or runtime equivalence claim",
                   "Unresolved indirect calls and collection fixups remain unknown",
                   "Whole-function pseudocode must not guide implementation after a rejected gate"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("evidence", type=Path)
    p.add_argument("derived", type=Path)
    p.add_argument("carrier", type=Path)
    args = p.parse_args()
    result = inspect(json.loads(args.evidence.read_text()),
                     json.loads(args.derived.with_suffix(args.derived.suffix + ".json").read_text()),
                     args.carrier.read_bytes(), args.derived.read_bytes())
    print(json.dumps(result, indent=2))
