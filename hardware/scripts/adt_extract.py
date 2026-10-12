#!/usr/bin/env python3
"""Sanitized Apple Device Tree (ADT) extractor for macOS hosts.

Reads the IODeviceTree plane (read-only) via `ioreg -a -p IODeviceTree -l -w0`
or from a previously captured plist, and writes a *sanitized* view:

  - property NAMES for every node (names are structural, not sensitive)
  - property VALUES only for an explicit whitelist of hardware-description keys
    (compatible strings, reg/ranges, interrupts, clock/power gates, cpu topology,
    PMGR power-state/DVFS tables, SART/NVMe/DART layout...)

Anything that can identify the individual machine or user (serial numbers,
UUIDs, ECID, nonces, MAC addresses, entropy, boot hashes, console users, ...)
is never written: such keys are not in the whitelist, and a denylist acts as a
second guard in case a whitelisted name ever collides.

A leak check runs before anything is written (and standalone with
--check-only): the values of every denylisted property are collected *in
memory only* from the live tree, and the sanitized output is searched for them
in every representation it uses (strings, u32/u64 words, hex blobs).  Output
is refused if any match is found.  Pattern checks (UUID / MAC text) and a
key-whitelist check run as well.

Usage:
  adt_extract.py --out-dir DIR [--plist FILE]
  adt_extract.py --out-dir DIR --check-only      # re-check existing output

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
    # 2026-10-11 (native-enablement pass): PMGR power-state + DVFS tables.
    # Format documented in m1n1 proxyclient/m1n1/adt.py (PMGRDevices etc.).
    "devices", "ps-groups", "perf-domains", "perf-groups", "clusters",
    "acc-clusters", "soc-clusters", "clocks", "events", "device-bridges",
    "pwrgate-regs", "die-stride", "cpu-power-gate-latency-us",
    "mgpu-count-per-die", "mcx-fast-pcpu-frequency",
    # CPU start / idle platform functions: <phandle, FourCC, args...>
    "function-enable_core", "function-cpu_idle", "cpm-impl-reg",
    "cluster-power-down",
    # SART / NVMe / DART layout
    "sart-version", "sart-power-reg-offset", "power-canary-offset",
    "sart-power-managed", "nvme-secure-bar", "nvme-interrupt-idx",
    "remap", "avoid-tlbi-in-map", "exclave-sid", "flush-by-dva",
    "vm-offset", "protection-granularity",
}

# Whitelisted key prefixes (e.g. voltage-states0 ... voltage-states31-sram).
VALUE_PREFIX_WHITELIST = ("voltage-states",)

# Binary tables that must be kept complete: emitted as {"hex": "..."} with no
# size cap so that they can be decoded offline (PMGR device tables, etc.).
HEX_KEYS = {
    "devices", "ps-groups", "ps-regs", "perf-regs", "pwrgate-regs",
    "perf-domains", "perf-groups", "clusters", "acc-clusters", "soc-clusters",
    "clocks", "events", "device-bridges", "function-enable_core",
    "function-cpu_idle",
}
HEX_PREFIXES = ("voltage-states",)

# Second guard: never emit values for keys matching these patterns.
# (Only ever extended, never relaxed.)
SENSITIVE = re.compile(
    r"serial|uuid|udid|nonce|seed|entropy|mac-address|macaddr|bd-addr|die-id|"
    r"bluetooth-address|wifi-address|ecid|unique|hash|manifest|crypto|apfs|"
    r"imei|meid|iccid|console|IOPlatform|IOKitDiagnostics|breadcrumb|"
    r"boot-objects-path|boot-command|bootp|token|secret|key|cert|nvram-proxy|"
    r"random|nvram|syscfg|keybag|seal|region-info|country|housing|"
    r"cover-glass|model-number|config-number|mlb|boot-args|time-stamp",
    re.IGNORECASE,
)

STRING_KEYS = {"compatible", "device_type", "name", "model", "target-type",
               "target-sub-type", "platform-name", "AAPL,unit-string",
               "segment-names", "role", "cluster-type", "state", "device-type",
               "AAPL,slot-name", "manufacturer", "firmware-version",
               "system-firmware-version", "ane-type"}

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
MAC_RE = re.compile(r"\b[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}\b")


def whitelisted(key):
    if SENSITIVE.search(key):
        return False
    return key in VALUE_WHITELIST or key.startswith(VALUE_PREFIX_WHITELIST)


def is_hex_key(key):
    return key in HEX_KEYS or key.startswith(HEX_PREFIXES)


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
    if is_hex_key(key):
        return {"hex": bytes(val).hex(), "len": len(val)}
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
    me = path + "/" + name
    props = {k: v for k, v in node.items() if k != "IORegistryEntryChildren"}
    out = {"path": me, "property_names": sorted(props.keys()), "values": {}}
    for k, v in props.items():
        if whitelisted(k):
            out["values"][k] = decode(k, v, parent_cells)
    my_cells = cells_of(props)
    out["children"] = [walk(c, my_cells, me)
                       for c in node.get("IORegistryEntryChildren", []) or []]
    return out


# ---------------------------------------------------------------- leak check

def _to_bytes(v):
    if isinstance(v, (bytes, bytearray)):
        return bytes(v)
    if isinstance(v, str):
        return v.encode("utf-8", "replace")
    if isinstance(v, bool):
        return b""
    if isinstance(v, int):
        return struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF)
    return b""


PUBLIC_ROOT_KEYS = ("compatible", "model", "target-type", "target-sub-type",
                    "platform-name")


def public_model_strings(root):
    """Public model identifiers (e.g. "Mac17,6", "J716cAP") from the root node.
    Denylisted properties whose value is exactly one of these (e.g.
    /product/unique-model) are not secrets and are excluded from comparison."""
    pub = set()
    # The ioreg plist root is "Root"; the ADT root is its "device-tree" child.
    for c in root.get("IORegistryEntryChildren", []) or []:
        if c.get("IORegistryEntryName") == "device-tree":
            root = c
            break
    for k in PUBLIC_ROOT_KEYS:
        v = root.get(k)
        if isinstance(v, (bytes, bytearray)):
            pub.update(s for s in bytes(v).split(b"\x00") if s)
        elif isinstance(v, str):
            pub.add(v.encode())
    return pub


def collect_sensitive(node, acc, public=None):
    """Values of denylisted properties, kept in memory only."""
    if public is None:
        public = public_model_strings(node)
    for k, v in node.items():
        if k == "IORegistryEntryChildren":
            continue
        if SENSITIVE.search(k):
            b = _to_bytes(v)
            # Skip trivial values (flags, small ints, padding) that would only
            # produce false positives; identifiers are >= 6 bytes of entropy.
            core = b.strip(b"\x00")
            if len(core) >= 6 and len(set(core)) >= 4 and core not in public:
                acc.add(core)
    for c in node.get("IORegistryEntryChildren", []) or []:
        collect_sensitive(c, acc, public)
    return acc


def _value_streams(v):
    """Every byte representation the sanitized JSON uses for a value."""
    if isinstance(v, dict):
        if "hex" in v:
            yield bytes.fromhex(v["hex"])
        if "addr" in v:
            a, s = int(v["addr"], 16), int(v["size"], 16)
            yield (a.to_bytes(max(8, (a.bit_length() + 7) // 8), "little") +
                   s.to_bytes(max(8, (s.bit_length() + 7) // 8), "little"))
        return
    if isinstance(v, str):
        yield v.encode("utf-8", "replace")
        return
    if isinstance(v, bool):
        return
    if isinstance(v, int):
        yield struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF)
        return
    if isinstance(v, list):
        words = []
        for x in v:
            if isinstance(x, str) and x.startswith("0x"):
                words.append(int(x, 16))
            elif isinstance(x, int) and not isinstance(x, bool):
                words.append(x)
            else:
                for s in _value_streams(x):
                    yield s
        if words:
            yield b"".join(struct.pack("<I", w & 0xFFFFFFFF) for w in words)


def leak_check(tree, sensitive):
    problems = []

    def visit(n):
        for k, v in n["values"].items():
            if not whitelisted(k):
                problems.append("non-whitelisted value key %s at %s" % (k, n["path"]))
            text = json.dumps(v)
            if UUID_RE.search(text) or MAC_RE.search(text):
                problems.append("UUID/MAC-like text in %s at %s" % (k, n["path"]))
            for s in _value_streams(v):
                for secret in sensitive:
                    if secret in s:
                        problems.append("denylisted value found in %s at %s" % (k, n["path"]))
                        break
        for c in n["children"]:
            visit(c)
    visit(tree)
    return problems


# ---------------------------------------------------------------- output

def flatten(n, rows):
    rows.append(n)
    for c in n["children"]:
        flatten(c, rows)
    return rows


def write_outputs(tree, out_dir):
    with open(out_dir + "/adt-sanitized.json", "w") as f:
        json.dump(tree, f, indent=1, sort_keys=True)
    rows = flatten(tree, [])
    with open(out_dir + "/adt-nodes.tsv", "w") as f:
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
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plist")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--check-only", action="store_true",
                    help="leak-check the existing adt-sanitized.json in OUT_DIR")
    args = ap.parse_args()
    root = plistlib.load(open(args.plist, "rb")) if args.plist else run_ioreg()
    sensitive = collect_sensitive(root, set())
    if args.check_only:
        tree = json.load(open(args.out_dir + "/adt-sanitized.json"))
    else:
        tree = walk(root)
    problems = leak_check(tree, sensitive)
    print("leak check: %d denylisted values compared, %d problems"
          % (len(sensitive), len(problems)), file=sys.stderr)
    for p in problems[:50]:
        print("  LEAK? " + p, file=sys.stderr)
    if problems:
        print("refusing to write output" if not args.check_only else "CHECK FAILED",
              file=sys.stderr)
        sys.exit(2)
    if args.check_only:
        print("CHECK PASSED", file=sys.stderr)
        return
    n = write_outputs(tree, args.out_dir)
    print("nodes:", n, file=sys.stderr)


if __name__ == "__main__":
    main()
