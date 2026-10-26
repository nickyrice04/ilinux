#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit one conditional BootKC reserved-range relation from explicit inputs.

No image is generated, executed or installed. No Apple bytes or machine state
are read. The caller must supply the applicable affine materialized image
extent; the tool does not establish that the running firmware uses this model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

U64_LIMIT = 1 << 64
ALIGNMENT = 0x4000
PROPERTY_NAMES = frozenset(("kclo", "kcep", "kcrf", "kcrz", "kcsf", "kcsz",
                            "kcxf", "kcxz", "kcbf", "kcbz", "kcwf", "kcwz",
                            "kclf", "kclz"))


def unsigned(value, name):
    if type(value) is not int or not 0 <= value < U64_LIMIT:
        raise ValueError(name + " must be an unsigned64-bit integer")
    return value


def properties_from_text(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate property key")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def audit(properties, *, image_bytes, load_base, expected_reserved_offset,
          expected_reserved_bytes):
    """Evaluate RS=load_base+kcrz, RSsize=kcsz under the stated contract only."""
    if not isinstance(properties, dict) or set(properties) != PROPERTY_NAMES:
        raise ValueError("properties must contain exactly the fourteen supported keys")
    for key in PROPERTY_NAMES:
        unsigned(properties[key], key)
    for name, value in (("image_bytes", image_bytes), ("load_base", load_base),
                        ("expected_reserved_offset", expected_reserved_offset),
                        ("expected_reserved_bytes", expected_reserved_bytes)):
        unsigned(value, name)
        if value % ALIGNMENT:
            raise ValueError(name + " must be16KiB aligned")
    if not image_bytes or not expected_reserved_bytes:
        raise ValueError("image and expected reservation sizes must be nonzero")
    image_end = load_base + image_bytes
    expected_end = expected_reserved_offset + expected_reserved_bytes
    if image_end >= U64_LIMIT or expected_end >= U64_LIMIT:
        raise ValueError("supplied image or expected reservation extent overflows64 bits")
    if expected_end > image_bytes:
        raise ValueError("expected reservation lies outside the supplied image extent")

    relative_start, size = properties["kcrz"], properties["kcsz"]
    relative_end = relative_start + size
    start, end = load_base + relative_start, load_base + relative_end
    issues = []
    if not size:
        issues.append("reserved_size_zero")
    if relative_start % ALIGNMENT or size % ALIGNMENT:
        issues.append("reserved_range_not_16k_aligned")
    overflow = relative_end >= U64_LIMIT or start >= U64_LIMIT or end >= U64_LIMIT
    if overflow:
        issues.append("producer_reserved_range_overflows_u64")
    if relative_start != expected_reserved_offset:
        issues.append("reserved_start_differs_from_declared_segment")
    if size != expected_reserved_bytes:
        issues.append("reserved_size_differs_from_declared_segment")
    if relative_start >= image_bytes or relative_end > image_bytes:
        issues.append("reserved_range_exceeds_materialized_image")

    canonical = json.dumps(properties, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": "ilinux-entry31ag-reserved-range-audit-v1",
        "status": "CONDITIONAL_INCONSISTENCY" if issues else "CONDITIONAL_CONSISTENCY",
        "contract": "BootKC-rs base=explicit_affine_load_base+kcrz; bytes=kcsz",
        "contract_alignment_bytes": ALIGNMENT,
        "premise": "Caller-supplied affine materialized image extent and declared reserved segment; actual firmware mode/binding not verified",
        "properties_canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "supplied_image": {"load_base": load_base, "bytes": image_bytes, "end": image_end},
        "declared_reserved": {"offset": expected_reserved_offset,
                              "bytes": expected_reserved_bytes, "end_offset": expected_end},
        "conditional_producer_reserved": {"offset": relative_start, "bytes": size,
                                          "end_offset": None if relative_end >= U64_LIMIT else relative_end,
                                          "base": None if start >= U64_LIMIT else start,
                                          "end": None if end >= U64_LIMIT else end},
        "issues": issues,
        "kcsf_semantics_applied": False,
        "other_regions_audited": False,
        "native_binding_verified": False,
        "native_failure_cause_proven": False,
        "image_acceptance_proven": False,
        "new_native_boot_ready": False,
    }


def number(text):
    try:
        return int(text, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected an integer (decimal or0x prefix)") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--properties", type=Path, required=True,
                        help="JSON object containing exactly fourteen integer properties")
    parser.add_argument("--image-bytes", type=number, required=True,
                        help="explicit applicable materialized affine image extent, not inferred from a file")
    parser.add_argument("--load-base", type=number, required=True)
    parser.add_argument("--reserved-offset", type=number, required=True)
    parser.add_argument("--reserved-bytes", type=number, required=True)
    args = parser.parse_args()
    p = args.properties
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 65536:
        parser.error("properties must be a regular JSON file no larger than64KiB")
    try:
        result = audit(properties_from_text(p.read_text()), image_bytes=args.image_bytes,
                       load_base=args.load_base, expected_reserved_offset=args.reserved_offset,
                       expected_reserved_bytes=args.reserved_bytes)
    except (ValueError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    # Successful evaluation is not unconditional image acceptance. A finite
    # inconsistency is a report result, not a parser/runtime exception.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
