#!/usr/bin/env python3
"""Replay the selected static PMGR references and byte anchors.

This verifies stored facts against a pinned carrier. It does not independently
prove the human interpretation of instructions or runtime dispatch.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

_s = importlib.util.spec_from_file_location("refs", Path(__file__).with_name("kernelcache_refs.py"))
refs = importlib.util.module_from_spec(_s)
_s.loader.exec_module(refs)


def verify(data, references, slice_record):
    digest = hashlib.sha256(data).hexdigest()
    if digest != references["carrier_sha256"] or digest != slice_record["carrier_sha256"]:
        raise ValueError("carrier digest differs from recorded evidence")
    c = refs.Collection(data)
    symbols = {}
    for member in ("com.apple.driver.ApplePMGR", "com.apple.driver.AppleT6050PMGR"):
        for address, names in c.symbols(member).items():
            symbols.setdefault(address, []).extend(names)
    expected_table = references["references"][0]["vtable_symbol"]
    tables = [a for a, names in symbols.items() if expected_table in names]
    if len(tables) != 1:
        raise ValueError("vtable identity is not unique")
    seen = set()
    discriminators = 0
    for row in references["references"]:
        address = int(row["address"], 16)
        if address in seen or row["vtable_symbol"] != expected_table:
            raise ValueError("duplicate or foreign dispatch reference")
        seen.add(address)
        if address != tables[0] + row["address_point_bias"] + int(row["slot"], 16):
            raise ValueError("dispatch address differs from recorded slot")
        actual = c.resolve(address)
        if any(row[key] != value for key, value in actual.items()):
            raise ValueError("chained-reference fact changed")
        if row["exact_symbols"] != symbols.get(int(actual["target"], 16)):
            raise ValueError("resolved symbol differs from evidence")
        if row["callsite_diversity"] is not None:
            if row["callsite_diversity"] != actual["diversity"]:
                raise ValueError("stored call-site discriminator differs")
            discriminators += 1
    start = int(slice_record["start"], 16)
    size = int(slice_record["end_exclusive"], 16) - start
    matches = [s for s in c.segments if s[0] <= start and start + size <= s[0] + s[3]]
    if size <= 0 or len(matches) != 1:
        raise ValueError("invalid slice mapping")
    off = matches[0][2] + start - matches[0][0]
    if off != slice_record["carrier_offset"] or size != slice_record["bytes"]:
        raise ValueError("slice offset changed")
    if hashlib.sha256(data[off:off + size]).hexdigest() != slice_record["sha256"]:
        raise ValueError("slice bytes changed")
    string = slice_record["string_reference"]
    address = int(string["address"], 16)
    expected = string["value"].encode() + b"\0"
    matches = [s for s in c.segments if s[0] <= address and address + len(expected) <= s[0] + s[3]]
    if len(matches) != 1:
        raise ValueError("invalid string mapping")
    off = matches[0][2] + address - matches[0][0]
    if data[off:off + len(expected)] != expected:
        raise ValueError("property name differs")
    kernel_symbols = c.symbols("com.apple.kernel")
    for row in slice_record.get("ordinary_kernel_callees", []):
        if kernel_symbols.get(int(row["address"], 16)) != row["exact_symbols"]:
            raise ValueError("ordinary helper identity changed")
    return {"carrier_sha256": digest, "verified_static_references": len(seen),
            "stored_discriminators_consistent": discriminators,
            "supplemental_slice_bytes_verified": size,
            "property_name_verified": string["value"],
            "runtime_or_instruction_semantics_verified": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("carrier", type=Path)
    p.add_argument("findings", type=Path)
    args = p.parse_args()
    output = verify(args.carrier.read_bytes(),
                    json.loads((args.findings / "pmgr-references.json").read_text()),
                    json.loads((args.findings / "cluster-property-evidence.json").read_text()))
    print(json.dumps(output, indent=2))
