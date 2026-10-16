#!/usr/bin/env python3
"""Candidate Stage-B DT: the boot035 Stage-B DT plus a USB device-mode path (DT only).

usage: python3 -I make_dt.py BASE_DTB ADT_JSON OUT_DTB DELTA_JSON

For each USB-C port (ADT usb-drd0..2) this adds a plain `snps,dwc3` node in
peripheral, high-speed mode and enables the port's two DARTs without a power
domain. It also disables every atc0-2 PMGR domain. Linux then leaves the PHY,
PMGR and DART state that m1n1's usb_phy_bringup() set up exactly as it is: no
AUTO_ENABLE write at probe, no sync_state or ladder release. check() proves that
nothing else in the boot035 Stage-B DT changes. Values come from the sanitized
ADT and are cross-checked against the DART nodes already in the base DT.
"""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fdtedit  # noqa: E402

BASE_SHA256 = "b1105bbf2c207c8c816c4b9cc0231ecc1d49543e05fe4b772bcb153019e186db"  # boot035
PORTS = (0, 1, 2)
DWC3_CORE_WINDOW = 0xcd00        # dwc3 core registers (the window Asahi's M3 DTs use)
DART_WINDOW = 0xc000
PWRSTATE = "apple,t8103-pmgr-pwrstate"
ATC_DOMAIN = re.compile(r"^atc[0-2]_")
QUIRKS = ("snps,usb2-gadget-lpm-disable", "snps,dis_u2_susphy_quirk",
          "snps,dis_u3_susphy_quirk", "snps,dis_enblslpm_quirk")
AIC_IRQ, IRQ_LEVEL_HIGH = 0, 4
DISABLED = b"disabled\0"


def cells(*values):
    return struct.pack(">%dI" % len(values), *values)


def text(value):
    return value.encode("ascii") + b"\0"


def texts(value):
    return value[:-1].decode("ascii").split("\0") if value else []


def compatible(node):
    return texts(node.get("compatible", b""))


def u32(value):
    if value is None or len(value) != 4:
        raise ValueError("expected one cell, got %r" % (value,))
    return struct.unpack(">I", value)[0]


# ------------------------------------------------------------------ sanitized ADT

def adt_nodes(path):
    tree = json.loads(Path(path).read_text())
    nodes, stack = {}, [tree]
    while stack:
        node = stack.pop()
        nodes[node["path"].replace("/Root/device-tree", "") or "/"] = node.get("values", {})
        stack.extend(node.get("children", []))
    return nodes


def words(value):
    if isinstance(value, int):
        return [value]
    return [int(x, 16) if isinstance(x, str) else x for x in value]


def arm_io_ranges(nodes):
    w = words(nodes["/arm-io"]["ranges"])
    return [(w[i] | w[i + 1] << 32, w[i + 2] | w[i + 3] << 32, w[i + 4] | w[i + 5] << 32)
            for i in range(0, len(w) - 5, 6)]


def translate(ranges, addr):
    for child, parent, size in ranges:
        if child <= addr < child + size:
            return parent + addr - child
    raise ValueError("ADT address %#x is outside the /arm-io ranges" % addr)


def adt_reg(nodes, path, index):
    entry = nodes[path]["reg"][index]
    return int(entry["addr"], 16), int(entry["size"], 16)


def port_facts(nodes):
    ranges, ports = arm_io_ranges(nodes), []
    for index in PORTS:
        drd, dart = "/arm-io/usb-drd%d" % index, "/arm-io/dart-usb%d" % index
        core, size = adt_reg(nodes, drd, 0)
        if size < DWC3_CORE_WINDOW:
            raise ValueError("%s reg[0] is smaller than the dwc3 core window" % drd)
        darts = []
        for i in (0, 1):
            addr, dsize = adt_reg(nodes, dart, i)
            if dsize != DART_WINDOW:
                raise ValueError("%s reg[%d] is not a DART register set" % (dart, i))
            darts.append(translate(ranges, addr))
        ports.append({
            "index": index,
            "port_number": nodes[drd]["port-number"],
            "core": translate(ranges, core),
            "irq": words(nodes[drd]["interrupts"])[0],     # first usb-drd interrupt: dwc3 core
            "darts": darts,
            "dart_irq": words(nodes[dart]["interrupts"])[0],
        })
    return ports


# ------------------------------------------------------------------ DT edit

def pwrstate_by_phandle(tree):
    found = {}
    for path, node in tree.walk():
        if PWRSTATE in compatible(node) and node.has("phandle"):
            found[u32(node.get("phandle"))] = (path, node)
    return found


def unit_address(name):
    _, _, unit = name.partition("@")
    return int(unit.split(",")[0], 16) if unit else None


def insert_by_address(parent, node):
    if any(child.name == node.name for child in parent.children):
        raise ValueError("%s already exists" % node.name)
    address = unit_address(node.name)
    for i, child in enumerate(parent.children):
        other = unit_address(child.name)
        if other is not None and other > address:
            parent.children.insert(i, node)
            return
    parent.children.append(node)


def build(base, ports):
    tree = fdtedit.parse(base)
    soc = tree.node("/soc")
    domains = pwrstate_by_phandle(tree)
    next_phandle = max(u32(n.get("phandle")) for _, n in tree.walk() if n.has("phandle")) + 1
    delta = {"added_nodes": [], "darts": [], "disabled_domains": []}
    for port in ports:
        dart_phandles, aic = [], None
        for addr in port["darts"]:
            path = "/soc/iommu@%x" % addr
            node = tree.node(path)
            if "apple,t8110-dart" not in compatible(node) or node.get("status") != DISABLED:
                raise ValueError("%s is not the expected disabled t8110 DART" % path)
            if node.get("reg") != cells(addr >> 32, addr & 0xFFFFFFFF, 0, DART_WINDOW):
                raise ValueError("%s reg differs from the ADT" % path)
            if node.get("interrupts") != cells(AIC_IRQ, port["dart_irq"], IRQ_LEVEL_HIGH):
                raise ValueError("%s interrupt differs from the ADT" % path)
            domain_path, domain = domains[u32(node.get("power-domains"))]
            if texts(domain.get("label")) != ["atc%d_usb" % port["index"]]:
                raise ValueError("%s is not in port %d's USB domain" % (path, port["index"]))
            aic = node.get("interrupt-parent")
            node.delete("status")
            node.delete("power-domains")
            node.set("phandle", cells(next_phandle))
            dart_phandles.append(next_phandle)
            delta["darts"].append({"path": path, "removed": ["status", "power-domains"],
                                   "phandle": next_phandle, "former_domain": domain_path})
            next_phandle += 1
        usb = fdtedit.Node("usb@%x" % port["core"])
        props = [
            ("compatible", text("snps,dwc3")),
            ("reg", cells(port["core"] >> 32, port["core"] & 0xFFFFFFFF, 0, DWC3_CORE_WINDOW)),
            ("interrupt-parent", aic),
            ("interrupts", cells(AIC_IRQ, port["irq"], IRQ_LEVEL_HIGH)),
            ("dr_mode", text("peripheral")),
            ("maximum-speed", text("high-speed")),
            ("iommus", cells(dart_phandles[0], 0, dart_phandles[1], 1)),
        ] + [(quirk, b"") for quirk in QUIRKS]
        for key, value in props:
            usb.set(key, value)
        insert_by_address(soc, usb)
        delta["added_nodes"].append({
            "path": "/soc/" + usb.name, "adt": "/arm-io/usb-drd%d" % port["index"],
            "port_number": port["port_number"], "irq": port["irq"],
            "iommus": [["/soc/iommu@%x" % port["darts"][0], 0], ["/soc/iommu@%x" % port["darts"][1], 1]],
            "properties": [key for key, _ in props]})
    for path, node in tree.walk():
        if PWRSTATE in compatible(node) and ATC_DOMAIN.match(texts(node.get("label"))[0]):
            if node.has("status"):
                raise ValueError("%s already has a status" % path)
            node.set("status", DISABLED)
            delta["disabled_domains"].append({"path": path, "label": texts(node.get("label"))[0]})
    return tree, delta


# ------------------------------------------------------------------ invariants

def check(base_tree, tree, ports):
    """Raise ValueError unless `tree` is base + exactly the planned USB delta."""
    before, after = fdtedit.flat(base_tree), fdtedit.flat(tree)
    usb_paths = {"/soc/usb@%x" % p["core"] for p in ports}
    dart_paths = {"/soc/iommu@%x" % a for p in ports for a in p["darts"]}
    if set(after) - set(before) != usb_paths or set(before) - set(after):
        raise ValueError("node set differs from the plan")
    disabled = set()
    for path in sorted(set(before) & set(after)):
        old, new = before[path], after[path]
        if old == new:
            continue
        if path in dart_paths:
            if set(old) - set(new) != {"status", "power-domains"} or set(new) - set(old) != {"phandle"}:
                raise ValueError("unexpected DART change at %s" % path)
            if any(old[k] != new[k] for k in set(old) & set(new)):
                raise ValueError("DART property value changed at %s" % path)
            continue
        label = texts(old.get("label", b"\0"))[0]
        if PWRSTATE in texts(old.get("compatible", b"")) and ATC_DOMAIN.match(label) \
                and set(new) - set(old) == {"status"} and set(old) <= set(new) \
                and new["status"] == DISABLED and all(old[k] == new[k] for k in old):
            disabled.add(label)
            continue
        raise ValueError("unplanned change at %s" % path)
    atc_labels = {texts(n["label"])[0] for n in before.values()
                  if PWRSTATE in texts(n.get("compatible", b"")) and ATC_DOMAIN.match(texts(n["label"])[0])}
    if disabled != atc_labels or not atc_labels:
        raise ValueError("not every atc0-2 domain is disabled")

    phandles = {}
    for path, node in tree.walk():
        if node.has("phandle"):
            if u32(node.get("phandle")) in phandles:
                raise ValueError("duplicate phandle at %s" % path)
            phandles[u32(node.get("phandle"))] = path
    for port in ports:
        node = after["/soc/usb@%x" % port["core"]]
        darts = ["/soc/iommu@%x" % a for a in port["darts"]]
        iommus = struct.unpack(">4I", node["iommus"])
        if [phandles.get(iommus[0]), iommus[1], phandles.get(iommus[2]), iommus[3]] != [darts[0], 0, darts[1], 1]:
            raise ValueError("iommus of usb@%x do not resolve to its DARTs" % port["core"])
        if node["interrupts"] != cells(AIC_IRQ, port["irq"], IRQ_LEVEL_HIGH):
            raise ValueError("usb@%x interrupt differs from the ADT" % port["core"])
        if node["dr_mode"] != text("peripheral") or node["maximum-speed"] != text("high-speed"):
            raise ValueError("usb@%x is not a high-speed peripheral" % port["core"])
        if any(node.get(q) != b"" for q in QUIRKS) or {"power-domains", "phys", "resets", "status"} & set(node):
            raise ValueError("usb@%x quirks or forbidden properties differ" % port["core"])

    for consumer, domain in dangling(after):
        raise ValueError("%s references disabled domain %s" % (consumer, domain))
    return sorted(disabled)


def dangling(nodes):
    """(consumer, domain) pairs where an available node points at a disabled domain.

    Such a consumer defers forever; a pwrstate child also writes AUTO_ENABLE to its
    own register before it looks its parent up and defers.
    """
    phandles = {u32(props["phandle"]): path for path, props in nodes.items() if "phandle" in props}

    def available(path):
        while True:
            if nodes.get(path, {}).get("status", b"okay\0") not in (b"okay\0", b"ok\0"):
                return False
            if path == "/":
                return True
            path = path.rsplit("/", 1)[0] or "/"
    found = []
    for path, props in sorted(nodes.items()):
        if "power-domains" in props and available(path):
            for ref in struct.unpack(">%dI" % (len(props["power-domains"]) // 4), props["power-domains"]):
                if not available(phandles[ref]):
                    found.append((path, phandles[ref]))
    return found


def sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def main(argv):
    if len(argv) != 5:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    base_path, adt_path, out_path, delta_path = map(Path, argv[1:])
    base = base_path.read_bytes()
    if sha256(base) != BASE_SHA256:
        raise SystemExit("base DTB is not the boot035 Stage-B DT")
    ports = port_facts(adt_nodes(adt_path))
    tree, delta = build(base, ports)
    disabled = check(fdtedit.parse(base), tree, ports)
    out = fdtedit.encode(tree)
    if fdtedit.encode(fdtedit.parse(out)) != out:
        raise SystemExit("candidate does not round-trip")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(out)
    delta.update({
        "base": {"file": base_path.name, "sha256": sha256(base), "bytes": len(base)},
        "candidate": {"file": out_path.name, "sha256": sha256(out), "bytes": len(out)},
        "ports": [{k: v for k, v in p.items()} for p in ports],
        "counts": {"added_nodes": len(delta["added_nodes"]), "darts": len(delta["darts"]),
                   "disabled_domains": len(disabled)},
    })
    Path(delta_path).write_text(json.dumps(delta, indent=1, sort_keys=True) + "\n")
    print("candidate %s sha256 %s (%d bytes): %d dwc3 nodes, %d DARTs enabled, %d atc domains disabled"
          % (out_path.name, sha256(out), len(out), len(delta["added_nodes"]), len(delta["darts"]), len(disabled)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
