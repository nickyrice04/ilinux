#!/usr/bin/env python3
"""Model of the t6050 CPU start/stop bitmap packing (patch 0002) against the sanitized ADT.

Checks that the ADT `clusters` descriptor gives 18 distinct bits equal to the `acc-cores` physical
core numbers, that the historical 4-bit stride collides, and that the validation rules in the
patch reject malformed descriptors.  Usage: python3 -I test_start_bits.py [adt-sanitized.json]
"""
import json
import struct
import sys
from pathlib import Path

DEFAULT_STRIDE = 4
MAX_CLUSTERS = 8


def layout(desc, chip_is_t6050=True):
    """Pure-Python model of smp_init_start_layout(); returns (pos[], width[]) or the default layout."""
    pos = [DEFAULT_STRIDE * i for i in range(MAX_CLUSTERS)]
    width = [DEFAULT_STRIDE] * MAX_CLUSTERS
    if not chip_is_t6050 or desc is None or len(desc) < 4 or len(desc) % 4 or len(desc) // 4 > MAX_CLUSTERS:
        return pos, width
    used = 0
    npos, nwidth = pos[:], width[:]
    for i in range(len(desc) // 4):
        w, p = struct.unpack_from("<HH", desc, 4 * i)
        if not p and i:
            p = DEFAULT_STRIDE * i
        if not w or w > 31 or p > 31 or p + w > 32:
            return pos, width
        mask = ((1 << w) - 1) << p
        if used & mask:
            return pos, width
        used |= mask
        npos[i], nwidth[i] = p, w
    return npos, nwidth


def start_bit(pos, width, cluster, core):
    if cluster < MAX_CLUSTERS and core < width[cluster]:
        return pos[cluster] + core
    return DEFAULT_STRIDE * cluster + core


def find(node, path):
    if node.get("path") == path:
        return node
    for child in node.get("children", []):
        hit = find(child, path)
        if hit:
            return hit
    return None


def main():
    adt = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[4] / "hardware/adt/adt-sanitized.json")
    pmgr = find(json.load(open(adt)), "/Root/device-tree/arm-io/pmgr")["values"]
    desc = bytes.fromhex(pmgr["clusters"]["hex"])
    pos, width = layout(desc)
    assert (pos[:3], width[:3]) == ([0, 6, 12], [6, 6, 6]), (pos, width)
    cores = [(c, k) for c in range(3) for k in range(6)]
    new = [start_bit(pos, width, c, k) for c, k in cores]
    old = [DEFAULT_STRIDE * c + k for c, k in cores]
    assert sorted(new) == list(range(18)), new
    assert len(set(old)) == 14, "the 4-bit stride must collide on 4 pairs"
    # acc-cores (live ADT, 8-byte records {u32 id, u8 0, u8 physCore, u8 coreInCluster, u8 cluster})
    acc = bytes.fromhex("0100000000000000020000000001010003000000000202000400000000030300050000000004040006000000000505000700000000060001"
                        "080000000007010109000000000802010a000000000903010b000000000a04010c000000000b05010d000000000c00020e000000000d0102"
                        "0f000000000e020210000000000f03021100000000100402120000000011050200"[:18 * 16])
    for i in range(18):
        _, _, phys, core, cluster = struct.unpack_from("<IBBBB", acc, 8 * i)
        assert start_bit(pos, width, cluster, core) == phys, (cluster, core, phys)
    # validation: overlap, too wide, zero width, odd length, wrong chip -> default layout
    for bad in (struct.pack("<HHHH", 6, 0, 6, 3), struct.pack("<HH", 33, 0), struct.pack("<HH", 0, 0), b"\x06\x00\x00", None):
        assert layout(bad) == ([DEFAULT_STRIDE * i for i in range(MAX_CLUSTERS)], [DEFAULT_STRIDE] * MAX_CLUSTERS), bad
    assert layout(desc, chip_is_t6050=False)[0][1] == 4
    # zero position on a later cluster means default stride
    assert layout(struct.pack("<HHHH", 4, 0, 4, 0))[0][1] == 4
    print("PASS: 18 distinct start bits 0..17 from the descriptor; old stride collides on bits 4,5,8,9; validation holds")


if __name__ == "__main__":
    main()
