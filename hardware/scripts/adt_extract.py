#!/usr/bin/env python3
"""Sanitized Apple Device Tree (ADT) extractor for macOS hosts.

Reads the IODeviceTree plane (read-only) via `ioreg -a -p IODeviceTree -l -w0`
or from a previously captured plist, and writes a *sanitized* view:

  - property NAMES for every node (names are structural, not sensitive)
  - property VALUES only for an explicit whitelist of hardware-description keys
    (compatible strings, reg/ranges, interrupts, clock/power gates, cpu topology...)

Anything that can identify the individual machine or user (serial numbers,
UUIDs, ECID, nonces, MAC addresses, entropy, boot hashes, console users, ...)
is never written: such keys are not in the whitelist, and a denylist acts as a
second guard in case a whitelisted name ever collides.

Usage:
  adt_extract.py --out-dir DIR [--plist FILE]

Outputs (in DIR):
  adt-sanitized.json   tree of nodes with whitelisted decoded values
  adt-nodes.tsv        one row per node: path, compatible, class, reg, irqs, gates
"""
import argparse
import json
import plistlib
import re
import struct
import subprocess
import sys

VALUE_WHITELIST = {
    "compatible", "device_type", "name", "model", "target-type", "target-sub-type",
    "platform-name", "chip-id", "board-id", "chip-epoch", "chip-revision",
    "reg", "ranges", "interrupts", "interrupt-parent", "interrupt-controller",
    "#address-cells", "#size-cells", "#interrupt-cells", "AAPL,phandle",
    "AAPL,unit-string", "clock-gates", "power-gates", "clock-ids", "clock-frequency",
    "timebase-frequency", "cpu-id", "cluster-id", "cluster-type", "cpu-impl-reg",
    "coresight-reg", "acc-impl-reg", "state", "role", "l2-cache-size",
    "i-cache-size", "d-cache-size", "cache-line-size", "cpu-uttdbg-reg",
    "segment-names", "segment-ranges", "dart-options", "page-size", "vm-base",
    "vm-size", "sid", "sids", "iommu-parent", "pcie-port-count", "max-link-speed",
    "port-number", "port-type", "lane-count", "gpu-core-count", "gpu-num-clusters",
    "num-gps", "num-cores", "ane-type", "nvme-queue-entries", "namespaces",
    "firmware-version", "system-firmware-version", "device-type",
    "AAPL,slot-name", "built-in", "manufacturer", "cluster-core-count",
    "perf-domain", "fixed-frequency-pll-index", "voltage-states", "ps-regs",
    "perf-regs", "power-domains", "num-ports", "IOObjectClass",
    # SoC-constant layout data needed to draft a Linux device tree
    "#gpio-pins", "#gpio-int-groups", "#main-cpus", "#shared-timestamps",
    "aic-iack-offset", "extint-baseaddress", "aic-numdies", "aic-numdies-per-die",
    "aic-rev", "cap0-offset", "maxnumirq-offset", "rev-offset", "aicglbcfg-offset",
    "aic-die-offset-stride", "aic-soc-offset-stride", "extintrcfg-stride",
    "intmaskset-stride", "intmaskclear-stride", "hwintmon-stride",
    "uart-version", "wdt-version", "iop-version", "soc-generation", "die-count",
    "cluster-core-id", "logical-cluster-id", "logical-cpu-id", "l2-cache-id",
    "no-aic-ipi-required", "fixed-frequency", "bus-frequency", "memory-frequency",
    "peripheral-frequency", "dart-id", "instance", "sid-count", "nvme-linear-sq",
}

# Second guard: never emit values for keys matching these patterns.
SENSITIVE = re.compile(
    r"serial|uuid|udid|nonce|seed|entropy|mac-address|macaddr|bd-addr|die-id|"
    r"bluetooth-address|wifi-address|ecid|unique|hash|manifest|crypto|apfs|"
    r"imei|meid|iccid|console|IOPlatform|IOKitDiagnostics|breadcrumb|"
    r"boot-objects-path|boot-command|bootp|token|secret|key|cert|nvram-proxy",
    re.IGNORECASE,
)

STRING_KEYS = {"compatible", "device_type", "name", "model", "target-type",
               "target-sub-type", "platform-name", "AAPL,unit-string",
               "segment-names", "role", "cluster-type", "state", "device-type",
               "AAPL,slot-name", "manufacturer", "firmware-version",
               "system-firmware-version", "ane-type"}


def run_ioreg():
    out = subprocess.run(["ioreg", "-a", "-p", "IODeviceTree", "-l", "-w0"],
                         check=True, capture_output=True).stdout
    return plistlib.loads(out)


def as_strings(b):
    return [s.decode("ascii", "replace") for s in b.split(b"\x00") if s]


def as_u32(b):
    n = len(b) // 4
    return list(struct.unpack("<%dI" % n, b[: n * 4]))


def as_u64(b):
    n = len(b) // 8
    return list(struct.unpack("<%dQ" % n, b[: n * 8]))


def decode(key, val, parent_cells):
    if not isinstance(val, (bytes, bytearray)):
        return val  # IOKit-native number/string/bool
    if key in STRING_KEYS:
        return as_strings(val)
    if key in ("reg", "ranges") and parent_cells:
        ac, sc = parent_cells
        cell_words = ac + sc if key == "reg" else None
        words = as_u32(val)
        if key == "reg" and cell_words and len(words) % cell_words == 0:
            out = []
            for i in range(0, len(words), cell_words):
                a = 0
                for j in range(ac):
                    a |= words[i + j] << (32 * j)
                s = 0
                for j in range(sc):
                    s |= words[i + ac + j] << (32 * j)
                out.append({"addr": hex(a), "size": hex(s)})
            return out
        return [hex(w) for w in words]
    if len(val) == 4:
        return as_u32(val)[0]
    if len(val) % 4 == 0 and len(val) <= 4096:
        return [hex(w) for w in as_u32(val)]
    return "<%d bytes>" % len(val)


def cells_of(props):
    def get(k, default):
        v = props.get(k)
        if isinstance(v, (bytes, bytearray)) and len(v) >= 4:
            return as_u32(v)[0]
        return default
    return (get("#address-cells", 2), get("#size-cells", 2))


def walk(node, parent_cells=None, path=""):
    name = node.get("IORegistryEntryName", "?")
    unit = node.get("AAPL,unit-string")
    me = path + "/" + name
    props = {k: v for k, v in node.items() if k != "IORegistryEntryChildren"}
    out = {"path": me, "property_names": sorted(props.keys()), "values": {}}
    for k, v in props.items():
        if k in VALUE_WHITELIST and not SENSITIVE.search(k):
            out["values"][k] = decode(k, v, parent_cells)
    my_cells = cells_of(props)
    out["children"] = [walk(c, my_cells, me)
                       for c in node.get("IORegistryEntryChildren", []) or []]
    return out


def flatten(n, rows):
    rows.append(n)
    for c in n["children"]:
        flatten(c, rows)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plist")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    root = plistlib.load(open(args.plist, "rb")) if args.plist else run_ioreg()
    tree = walk(root)
    with open(args.out_dir + "/adt-sanitized.json", "w") as f:
        json.dump(tree, f, indent=1, sort_keys=True)
    rows = flatten(tree, [])
    with open(args.out_dir + "/adt-nodes.tsv", "w") as f:
        f.write("path\tcompatible\tobject_class\treg\tinterrupts\tclock_gates\tpower_gates\n")
        for n in rows:
            v = n["values"]
            comp = ";".join(v.get("compatible", []) or [])
            reg = v.get("reg", "")
            if isinstance(reg, list) and reg and isinstance(reg[0], dict):
                reg = ",".join("%s+%s" % (r["addr"], r["size"]) for r in reg)
            irq = v.get("interrupts", "")
            irq = ",".join(map(str, irq)) if isinstance(irq, list) else str(irq)
            cg = v.get("clock-gates", "")
            pg = v.get("power-gates", "")
            cg = ",".join(map(str, cg)) if isinstance(cg, list) else str(cg)
            pg = ",".join(map(str, pg)) if isinstance(pg, list) else str(pg)
            f.write("\t".join([n["path"].replace("/Root/device-tree", ""), comp,
                               str(v.get("IOObjectClass", "")), str(reg), irq,
                               cg, pg]) + "\n")
    print("nodes:", len(rows), file=sys.stderr)


if __name__ == "__main__":
    main()
