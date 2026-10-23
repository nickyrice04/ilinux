#!/usr/bin/env python3
"""Offline GPU ADT contract. No target, device, firmware, or MMIO operations."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys
from typing import NamedTuple

MAX_FILE = 8 * 1024 * 1024
MAX_SEGMENTS = 32
U64 = (1 << 64) - 1
U32 = (1 << 32) - 1
ROOT = "/Root/device-tree"
ARM = ROOT + "/arm-io"
LAYOUT = struct.Struct("<QQQII")
CONTRACT_PATHS = {ROOT, ARM, ARM + "/sgx", ARM + "/aic", ARM + "/mapper-gfx-asc",
                  ARM + "/gfx-asc", ARM + "/gfx-asc/iop-gfx-nub",
                  ARM + "/gfx1-asc", ARM + "/gfx1-asc/iop-gfx1-nub"}


class Refusal(ValueError):
    """Messages are fixed labels, never interpolated input."""


class Segment(NamedTuple):
    descriptor_phys: int
    iova: int
    remap: int
    size: int
    opaque: int


def require(condition, label):
    if not condition:
        raise Refusal(label)


def uint(value, bits):
    require(type(value) is int and 0 <= value < (1 << bits), "INTEGER")
    return value


def cell(value, bits=32):
    if type(value) is str:
        require(re.fullmatch(r"0x[0-9a-fA-F]{1,16}", value) is not None, "CELL")
        value = int(value, 16)
    return uint(value, bits)


def validate_segments(segments, granule=1):
    require(type(segments) in (tuple, list) and 0 < len(segments) <= MAX_SEGMENTS,
            "SEGMENT_COUNT")
    uint(granule, 32)
    require(granule != 0 and not granule & (granule - 1), "GRANULE")
    for s in segments:
        require(type(s) is Segment, "SEGMENT_TYPE")
        for value in s[:3]:
            uint(value, 64)
        uint(s.size, 32)
        uint(s.opaque, 32)
        require(s.size > 0, "SPAN")
        require(all(base <= U64 - s.size for base in s[:3]), "SPAN")
        require(all(value % granule == 0 for value in s[:4]), "ALIGNMENT")
    for i, a in enumerate(segments):
        for b in segments[i + 1:]:
            for domain in range(3):
                require(not (a[domain] < b[domain] + b.size and
                             b[domain] < a[domain] + a.size), "OVERLAP")
    return tuple(segments)


def decode_segments(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_SEGMENTS * LAYOUT.size and
            len(raw) % LAYOUT.size == 0, "SEGMENT_LENGTH")
    return validate_segments([Segment(*item) for item in LAYOUT.iter_unpack(raw)])


def encode_segments(segments):
    return b"".join(LAYOUT.pack(*s) for s in validate_segments(segments))


def from_cells(cells):
    require(type(cells) is list and 0 < len(cells) <= MAX_SEGMENTS * 8 and
            len(cells) % 8 == 0, "CELL_COUNT")
    raw = b"".join(struct.pack("<I", cell(value)) for value in cells)
    return decode_segments(raw)


def index_tree(tree):
    index, handles, seen = {}, {}, set()
    pending = [(tree, 0, None)]
    while pending:
        node, depth, parent = pending.pop()
        require(type(node) is dict and depth <= 64 and len(seen) < 8192, "TREE_BOUND")
        require(id(node) not in seen, "TREE_CYCLE")
        seen.add(id(node))
        path = node.get("path")
        require(type(path) is str and 0 < len(path) <= 512 and path.startswith("/"), "NODE_PATH")
        # This retained IOKit tree contains duplicate paths for unrelated PCI
        # services. They do not describe GPU resources. Never select a duplicate
        # contract path or silently overwrite one of its descriptors.
        require(path not in CONTRACT_PATHS or path not in index, "DUPLICATE_PATH")
        if parent is not None:
            require(path.rsplit("/", 1)[0] == parent, "NODE_PARENT")
        values, names, children = node.get("values"), node.get("property_names"), node.get("children")
        require(type(values) is dict and len(values) <= 1024 and
                type(names) is list and len(names) <= 2048 and
                type(children) is list and len(children) <= 8192, "NODE_SHAPE")
        require(all(type(name) is str and len(name) <= 256 for name in names), "PROPERTY_NAME")
        require(len(set(names)) == len(names), "DUPLICATE_PROPERTY")
        require(set(values).issubset(names), "PROPERTY_LIST")
        if path in CONTRACT_PATHS and "AAPL,phandle" in values:
            handle = uint(values["AAPL,phandle"], 32)
            require(handle > 0 and handle not in handles, "PHANDLE")
            handles[handle] = path
        if path not in index:
            index[path] = node
        pending.extend((child, depth + 1, path) for child in children)
    return index


def inspect_adt(tree):
    """Validate this observed machine's structural contract; emit no raw values.

    Acceptance is NOT boot readiness. In particular, retained descriptor_phys is
    a named field, not an established CPU PA, and sanitized property presence is
    not proof that UAT/GPTBAT was initialized.
    """
    nodes = index_tree(tree)

    def get(path):
        require(path in nodes, "MISSING_NODE")
        return nodes[path]["values"]

    def equal(values, name, expected):
        require(values.get(name) == expected, "IDENTITY")

    def numeric_list(values, name, expected):
        value = values.get(name)
        require(type(value) is list and len(value) == len(expected), "RESOURCE_COUNT")
        require([cell(item) for item in value] == expected, "RESOURCE_IDENTITY")

    def registers(values, expected):
        regs = values.get("reg")
        require(type(regs) is list and len(regs) == len(expected), "REGISTER_COUNT")
        actual = []
        for item in regs:
            require(type(item) is dict and set(item) == {"addr", "size"}, "REGISTER_SHAPE")
            base, size = cell(item["addr"], 64), cell(item["size"], 64)
            require(size > 0 and base <= U64 - size, "REGISTER_SPAN")
            actual.append((base, size))
        require(actual == expected, "REGISTER_IDENTITY")

    equal(get(ROOT), "compatible", ["J716cAP", "Mac17,6", "AppleARM"])
    equal(get(ARM), "compatible", ["arm-io,t6050"])
    gpu = get(ARM + "/sgx")
    equal(gpu, "compatible", ["gpu,t6050"])
    registers(gpu, [(0x2100000000, 0x3FDC000), (0x2100D00000, 0x177000)])
    numeric_list(gpu, "interrupts", [0x990, 0x991, 0x992, 0x993, 0x1C2, 0xAF6, 0x99F, 0x9A1])
    for name in ("clock-gates", "power-gates"):
        numeric_list(gpu, name, [0x268, 0x267])
    aic = get(ARM + "/aic")
    equal(aic, "compatible", ["aic,3"])
    aic_handle = uint(aic.get("AAPL,phandle"), 32)
    require(uint(gpu.get("interrupt-parent"), 32) == aic_handle, "IRQ_PARENT")
    mapper = get(ARM + "/mapper-gfx-asc")
    equal(mapper, "compatible", ["iommu-mapper,gfx"])
    mapper_handle = uint(mapper.get("AAPL,phandle"), 32)
    profiles = (
        ("GFX", "gfx-asc", "iop-gfx-nub", 614,
         [(0x2102600000, 0x88000), (0x2102050000, 8)], [0xAEE, 0xAED, 0xAF0, 0xAEF]),
        ("GFX1", "gfx1-asc", "iop-gfx1-nub", 657,
         [(0x2102E00000, 0x88000), (0x2102850000, 0x60000)], [0xAF2, 0xAF1, 0xAF4, 0xAF3]),
    )
    role_reports, per_role = [], []
    for role, name, nub_name, gate, regs, irqs in profiles:
        asc = get(ARM + "/" + name)
        nub = get(ARM + "/" + name + "/" + nub_name)
        equal(asc, "compatible", ["iop,ascwrap-v6"])
        equal(asc, "role", [role])
        require(uint(asc.get("iop-version"), 32) == 1, "IOP_VERSION")
        equal(nub, "compatible", ["iop-nub,rtbuddy-v2"])
        require(uint(asc.get("iommu-parent"), 32) == mapper_handle, "MAPPER_PARENT")
        require(uint(asc.get("interrupt-parent"), 32) == aic_handle, "IRQ_PARENT")
        for gate_name in ("clock-gates", "power-gates"):
            require(uint(asc.get(gate_name), 32) == gate, "POWER_IDENTITY")
        registers(asc, regs)
        numeric_list(asc, "interrupts", irqs)
        for record in (asc, nub):
            equal(record, "segment-names", ["__TEXT;__DATA"])
        segments = from_cells(asc.get("segment-ranges"))
        require(len(segments) == 2, "ROLE_SEGMENT_COUNT")
        validate_segments(segments, 16384)
        require(segments == from_cells(nub.get("segment-ranges")), "NUB_DISAGREEMENT")
        raw = encode_segments(segments)
        require(decode_segments(raw) == segments, "ROUNDTRIP")
        per_role.append(segments)
        role_reports.append({
            "role": role, "segment_count": 2, "descriptor_bytes": len(raw),
            "descriptor_sha256": hashlib.sha256(raw).hexdigest(),
            "segment_sizes": [s.size for s in segments],
            "descriptor_address_bits": max(s.descriptor_phys.bit_length() for s in segments),
            "nonzero_high_descriptor_words": sum(s.descriptor_phys > U32 for s in segments),
            "nonzero_opaque_words": sum(s.opaque != 0 for s in segments),
            "parent_nub_equal": True, "alignment_policy_bytes": 16384,
        })
    cross_overlap = sum(a.iova < b.iova + b.size and b.iova < a.iova + a.size
                        for a in per_role[0] for b in per_role[1])
    names = nodes[ARM + "/sgx"]["property_names"]
    return {
        "schema": "ilinux-gpu31p-contract-v1", "status": "STRUCTURAL_PASS",
        "identity": "J716C_T6050_DUAL_ASC", "hardware_operations": 0,
        "native_validation": "NOT_RUN", "gpu_enablement": "HOLD",
        "descriptor_cpu_address_domain": "UNQUALIFIED",
        "uat_layout": "UNKNOWN", "firmware_abi": "UNKNOWN",
        "cpu_memory_reservations_generated": 0, "mmio_writes_generated": 0,
        "indexed_path_count": len(nodes), "contract_node_count": len(CONTRACT_PATHS),
        "role_count": 2, "shared_mapper": True,
        "cross_role_iova_overlaps": cross_overlap, "roles": role_reports,
        "property_presence_only": {name: name in names for name in (
            "gptbat-ready", "ttbat-phys-addr-base", "agx-address-space-mgmt-mode")},
    }


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def reject_constant(_value):
    raise Refusal("NONFINITE_JSON")


def finite_float(value):
    number = float(value)
    require(math.isfinite(number), "NONFINITE_JSON")
    return number


def read_adt(path):
    """Bounded regular-file input with no symlink or special-device traversal."""
    before = os.lstat(path)
    require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_FILE, "INPUT_FILE")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and
                (before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino), "INPUT_FILE")
        raw = stream.read(MAX_FILE + 1)
        require(0 < len(raw) <= MAX_FILE, "INPUT_SIZE")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs,
                      parse_constant=reject_constant, parse_float=finite_float)
    return data, hashlib.sha256(raw).hexdigest()


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise Refusal("ARGUMENTS")


def main(argv=None):
    try:
        parser = Parser(description="Offline sanitized ADT GPU contract; no device operations")
        parser.add_argument("--adt", type=Path, required=True)
        args = parser.parse_args(argv)
        data, digest = read_adt(args.adt)
        result = inspect_adt(data)
        result["sanitized_adt_sha256"] = digest
    except Refusal as error:
        result = {"status": "REFUSED", "reason": str(error), "hardware_operations": 0}
    except (OSError, UnicodeError, ValueError, RecursionError, OverflowError):
        result = {"status": "REFUSED", "reason": "INPUT", "hardware_operations": 0}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "STRUCTURAL_PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
