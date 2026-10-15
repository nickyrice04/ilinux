#!/usr/bin/env python3
"""Candidate Stage-B DT with the MTP input path (DT only; offline, NOT RUN).

usage: python3 -I make_mtp_dt.py BASE_DTB ADT_JSON OUT_DTB DELTA_JSON [--sids 1] [--dts OUT.dtsi]

Adds, from our own sanitized ADT (see mtp_adt.py):

* ``mtp@294600000`` (RTKit helper), ``mbox@294608000`` (ASC mailbox v4),
* ``fifo@294b14000`` (DockChannel, ``irq`` block + FIFO window) with its HID
  child ``input@8000`` and the interface nodes multi-touch/keyboard/stm/actuator/
  tp_accel/tp-accel,
* ``apple,dma-range`` and ``status`` on the DART node the base DT already carries,
* the ``keyboard`` alias m1n1's dt_set_ipd() resolves.

Nothing else changes; check() proves it. The base is the boot035 Stage-B DT by
default (sha256 below); boot036's differs only in USB nodes and is accepted too.
The byte-exact DTB editor comes from kernel/experiments/usb-gadget-dt/fdtedit.py.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "usb-gadget-dt"))
import mtp_adt  # noqa: E402

try:
    import fdtedit  # noqa: E402
except ImportError as e:  # pragma: no cover
    raise SystemExit("needs kernel/experiments/usb-gadget-dt/fdtedit.py (%s)" % e)

KNOWN_BASES = {
    "b1105bbf2c207c8c816c4b9cc0231ecc1d49543e05fe4b772bcb153019e186db": "boot035 Stage-B",
}
AIC_IRQ, IRQ_LEVEL_HIGH = 0, 4
DART_PATH = "/soc/iommu@294800000"
NEW_NODES = (
    "/soc/mtp@294600000",
    "/soc/mbox@294608000",
    "/soc/fifo@294b14000",
    "/soc/fifo@294b14000/input@8000",
    "/soc/fifo@294b14000/input@8000/multi-touch",
    "/soc/fifo@294b14000/input@8000/keyboard",
    "/soc/fifo@294b14000/input@8000/stm",
    "/soc/fifo@294b14000/input@8000/actuator",
    "/soc/fifo@294b14000/input@8000/tp_accel",
    "/soc/fifo@294b14000/input@8000/tp-accel",
)
FIRMWARE_NAME = "apple/tpmtfw-j716c.bin"


def cells(*values):
    return struct.pack(">%dI" % len(values), *values)


def text(value):
    return value.encode("ascii") + b"\0"


def texts(*values):
    return b"".join(text(v) for v in values)


def u64cells(value):
    return cells(value >> 32, value & 0xFFFFFFFF)


def reg2(addr, size):
    return u64cells(addr) + u64cells(size)


def u32(value):
    if value is None or len(value) != 4:
        raise ValueError("expected one cell, got %r" % (value,))
    return struct.unpack(">I", value)[0]


def new_node(name, props, children=()):
    node = fdtedit.Node(name)
    for key, value in props:
        node.props.append([key, value, None])
    node.children.extend(children)
    return node


def find_aic(tree):
    for path, node in tree.walk():
        comp = node.get("compatible")
        if comp and b"apple,t6050-aic3" in comp:
            return path, node
    raise ValueError("no AIC node in the base DT")


def max_phandle(tree):
    best = 0
    for _, node in tree.walk():
        for key in ("phandle", "linux,phandle"):
            value = node.get(key)
            if value is not None:
                best = max(best, u32(value))
    return best


# --------------------------------------------------------------------------- build

def build(tree, f, sids=(1,)):
    """Apply the delta in place; return {label: phandle} of allocated handles."""
    soc = tree.node("/soc")
    _, aic = find_aic(tree)
    aic_ph = u32(aic.get("phandle"))
    nxt = max_phandle(tree) + 1
    ph = {}
    for label in ("mtp", "mtp_mbox", "mtp_dockchannel"):
        ph[label] = nxt
        nxt += 1

    # --- existing DART: enable, add the IOVA window, give it a phandle ---------------
    dart = tree.node(DART_PATH)
    reg = dart.get("reg")
    if reg is None or struct.unpack(">4I", reg) != (f["dart"] >> 32, f["dart"] & 0xFFFFFFFF,
                                                    0, f["dart_window"]):
        raise ValueError("base DART reg does not match the ADT (%s)" % hex(f["dart"]))
    if u32(dart.get("interrupts")[4:8]) != f["dart_irq"]:
        raise ValueError("base DART interrupt does not match the ADT")
    if dart.has("power-domains"):
        raise ValueError("MTP DART unexpectedly has power-domains in the base DT")
    if dart.get("phandle") is None:
        dart.set("phandle", cells(nxt))
        ph["mtp_dart"] = nxt
        nxt += 1
    else:
        ph["mtp_dart"] = u32(dart.get("phandle"))
    dart.set("apple,dma-range", u64cells(f["vm_base"]) + u64cells(f["vm_size"]))
    if dart.has("status"):
        dart.delete("status")

    iommus = b"".join(cells(ph["mtp_dart"], s) for s in sids)
    irq = lambda n: cells(AIC_IRQ, n, IRQ_LEVEL_HIGH)  # noqa: E731

    mtp = new_node("mtp@%x" % f["asc"], [
        ("compatible", texts("apple,t6050-mtp", "apple,t6050-rtk-helper-asc4",
                             "apple,mtp", "apple,rtk-helper-asc4")),
        ("reg", reg2(f["asc"], 0x4000) + reg2(f["sram"], 0x100000)),
        ("reg-names", texts("asc", "sram")),
        ("mboxes", cells(ph["mtp_mbox"])),
        ("iommus", iommus),
        ("#helper-cells", cells(0)),
        ("phandle", cells(ph["mtp"])),
    ])
    mbox = new_node("mbox@%x" % f["mbox"], [
        ("compatible", texts("apple,t6050-asc-mailbox", "apple,asc-mailbox-v4")),
        ("reg", reg2(f["mbox"], 0x4000)),
        ("interrupt-parent", cells(aic_ph)),
        ("interrupts", b"".join(irq(n) for n in f["mbox_irqs"])),
        ("interrupt-names", texts("send-empty", "send-not-empty", "recv-empty", "recv-not-empty")),
        ("#mbox-cells", cells(0)),
        ("phandle", cells(ph["mtp_mbox"])),
    ])
    iface = lambda name, props=(): new_node(name, list(props))  # noqa: E731
    hid = new_node("input@8000", [
        ("compatible", texts("apple,t6050-dockchannel-hid", "apple,dockchannel-hid")),
        ("reg", cells(0x8000, 0x4000, 0xC000, 0x4000, 0x0, 0x4000, 0x4000, 0x4000)),
        ("reg-names", texts("config", "data", "rmt-config", "rmt-data")),
        ("iommus", iommus),
        ("interrupt-parent", cells(ph["mtp_dockchannel"])),
        ("interrupts", cells(2, IRQ_LEVEL_HIGH, 3, IRQ_LEVEL_HIGH)),
        ("interrupt-names", texts("tx", "rx")),
        ("apple,fifo-size", cells(f["fifo_size"])),
        ("apple,helper-cpu", cells(ph["mtp"])),
    ], children=[
        iface("multi-touch", [("firmware-name", text(FIRMWARE_NAME))]),
        # hid-country-code / apple,keyboard-layout-id are overwritten by m1n1 from
        # kblang-calibration through the `keyboard` alias.
        iface("keyboard", [("hid-country-code", cells(0)), ("apple,keyboard-layout-id", cells(0))]),
        iface("stm"),
        iface("actuator"),
        # The ADT names the interface "tp-accel"; the FIFO-era firmware announced
        # "tp_accel". Carry both spellings so the name lookup works either way.
        iface("tp_accel"),
        iface("tp-accel"),
    ])
    dock = new_node("fifo@%x" % f["dock_irq_block"], [
        ("compatible", texts("apple,t6050-dockchannel", "apple,dockchannel")),
        ("reg", reg2(f["dock_irq_block"], 0x4000)),
        ("reg-names", texts("irq")),
        ("interrupt-parent", cells(aic_ph)),
        ("interrupts", irq(f["dock_irq"])),
        ("ranges", cells(0, f["dock_ranges_base"] >> 32, f["dock_ranges_base"] & 0xFFFFFFFF, 0x20000)),
        ("nonposted-mmio", b""),
        ("#address-cells", cells(1)),
        ("#size-cells", cells(1)),
        ("interrupt-controller", b""),
        ("#interrupt-cells", cells(2)),
        ("phandle", cells(ph["mtp_dockchannel"])),
    ], children=[hid])
    soc.children.extend([mtp, mbox, dock])

    keyboard_path = "/soc/%s/%s/keyboard" % (dock.name, hid.name)
    aliases = tree.node("/aliases")
    aliases.set("keyboard", text(keyboard_path))
    return ph


# --------------------------------------------------------------------------- check

def check(base, new, f, ph, sids=(1,)):
    """Prove the new tree differs from the base only by the planned delta."""
    before, after = fdtedit.flat(base), fdtedit.flat(new)
    added = sorted(set(after) - set(before))
    if added != sorted(NEW_NODES):
        raise AssertionError("node set changed unexpectedly: %r" % (added,))
    removed = set(before) - set(after)
    if removed:
        raise AssertionError("nodes removed: %r" % sorted(removed))
    changed = {p for p in before if before[p] != after[p]}
    if changed != {DART_PATH, "/aliases"}:
        raise AssertionError("unexpected modified nodes: %r" % sorted(changed))
    d_before, d_after = before[DART_PATH], after[DART_PATH]
    gained = set(d_after) - set(d_before)
    lost = set(d_before) - set(d_after)
    allowed_gain = {"apple,dma-range"} | ({"phandle"} if "phandle" not in d_before else set())
    if gained != allowed_gain or lost != {"status"}:
        raise AssertionError("DART property delta wrong: +%r -%r" % (gained, lost))
    for key in set(d_before) & set(d_after):
        if d_before[key] != d_after[key]:
            raise AssertionError("DART property %s changed" % key)
    if d_before["status"] != b"disabled\0":
        raise AssertionError("base DART status was not disabled")
    if set(after["/aliases"]) - set(before["/aliases"]) != {"keyboard"}:
        raise AssertionError("aliases delta wrong")

    # phandles unique, references resolve
    seen = {}
    for path, props in after.items():
        for key in ("phandle", "linux,phandle"):
            if key in props:
                v = u32(props[key])
                if v in seen:
                    raise AssertionError("duplicate phandle %d: %s and %s" % (v, seen[v], path))
                seen[v] = path
    want = {
        ph["mtp"]: "/soc/mtp@294600000",
        ph["mtp_mbox"]: "/soc/mbox@294608000",
        ph["mtp_dockchannel"]: "/soc/fifo@294b14000",
        ph["mtp_dart"]: DART_PATH,
    }
    for value, path in want.items():
        if seen.get(value) != path:
            raise AssertionError("phandle %d is not %s" % (value, path))
    if struct.unpack(">%dI" % (2 * len(sids)), after["/soc/mtp@294600000"]["iommus"]) != \
            tuple(x for s in sids for x in (ph["mtp_dart"], s)):
        raise AssertionError("mtp iommus wrong")
    if u32(after["/soc/mtp@294600000"]["mboxes"]) != ph["mtp_mbox"]:
        raise AssertionError("mtp mboxes wrong")
    hid = after["/soc/fifo@294b14000/input@8000"]
    if u32(hid["apple,helper-cpu"]) != ph["mtp"] or u32(hid["interrupt-parent"]) != ph["mtp_dockchannel"]:
        raise AssertionError("hid references wrong")
    # the alias must resolve to a node that exists
    alias = after["/aliases"]["keyboard"][:-1].decode()
    if alias not in after:
        raise AssertionError("keyboard alias target missing: %s" % alias)
    # facts that must match the ADT exactly
    mbox = after["/soc/mbox@294608000"]
    expect_irq = b"".join(cells(AIC_IRQ, n, IRQ_LEVEL_HIGH) for n in f["mbox_irqs"])
    if mbox["interrupts"] != expect_irq:
        raise AssertionError("mailbox interrupts do not match the ADT")
    dart_range = after[DART_PATH]["apple,dma-range"]
    if struct.unpack(">4I", dart_range) != (f["vm_base"] >> 32, f["vm_base"] & 0xFFFFFFFF,
                                           f["vm_size"] >> 32, f["vm_size"] & 0xFFFFFFFF):
        raise AssertionError("apple,dma-range does not match vm-base/vm-size")
    if "status" in after["/soc/mtp@294600000"] or "status" in hid:
        raise AssertionError("new nodes must not carry a status")


# --------------------------------------------------------------------------- render

def render_dts(f, ph, sids):
    """Review text for the delta (a fragment, not a complete DTS)."""
    iommus = ", ".join("<&mtp_dart %d>" % s for s in sids)
    irqs = ",\n\t\t\t".join("<AIC_IRQ %d IRQ_TYPE_LEVEL_HIGH>" % n for n in f["mbox_irqs"])
    return """\
// SPDX-License-Identifier: GPL-2.0+ OR MIT
/*
 * MTP keyboard/trackpad nodes for t6050 / J716c: DRAFT, generated by
 * kernel/experiments/mtp-input/make_mtp_dt.py from hardware/adt/adt-sanitized.json.
 * Not booted. The nodes below go under /soc; mtp_dart is the DART node the
 * Stage-B DT already has (iommu@294800000), which gains only the two properties
 * shown and loses `status = "disabled"`.
 */
&mtp_dart {{
	/* ADT dart-mtp vm-base 0x{vm_base:x}, vm-size 0x{vm_size:x} */
	apple,dma-range = <0x{base_hi:x} 0x{base_lo:x} 0x{size_hi:x} 0x{size_lo:x}>;
}};

/ {{
	aliases {{
		keyboard = &keyboard;
	}};

	soc {{
		mtp: mtp@{asc:x} {{
			compatible = "apple,t6050-mtp", "apple,t6050-rtk-helper-asc4",
				     "apple,mtp", "apple,rtk-helper-asc4";
			reg = <0x{asc_hi:x} 0x{asc_lo:x} 0x0 0x4000>,
			      <0x{sram_hi:x} 0x{sram_lo:x} 0x0 0x100000>;
			reg-names = "asc", "sram";
			mboxes = <&mtp_mbox>;
			iommus = {iommus};
			#helper-cells = <0>;
		}};

		mtp_mbox: mbox@{mbox:x} {{
			compatible = "apple,t6050-asc-mailbox", "apple,asc-mailbox-v4";
			reg = <0x{mbox_hi:x} 0x{mbox_lo:x} 0x0 0x4000>;
			interrupt-parent = <&aic>;
			interrupts = {irqs};
			interrupt-names = "send-empty", "send-not-empty",
					  "recv-empty", "recv-not-empty";
			#mbox-cells = <0>;
		}};

		mtp_dockchannel: fifo@{irq_block:x} {{
			compatible = "apple,t6050-dockchannel", "apple,dockchannel";
			reg = <0x{irq_hi:x} 0x{irq_lo:x} 0x0 0x4000>;
			reg-names = "irq";
			interrupt-parent = <&aic>;
			interrupts = <AIC_IRQ {dock_irq} IRQ_TYPE_LEVEL_HIGH>;
			ranges = <0 0x{rb_hi:x} 0x{rb_lo:x} 0x20000>;
			nonposted-mmio;
			#address-cells = <1>;
			#size-cells = <1>;
			interrupt-controller;
			#interrupt-cells = <2>;

			mtp_hid: input@8000 {{
				compatible = "apple,t6050-dockchannel-hid",
					     "apple,dockchannel-hid";
				reg = <0x8000 0x4000>, <0xc000 0x4000>,
				      <0x0000 0x4000>, <0x4000 0x4000>;
				reg-names = "config", "data", "rmt-config", "rmt-data";
				iommus = {iommus};
				interrupt-parent = <&mtp_dockchannel>;
				interrupts = <2 IRQ_TYPE_LEVEL_HIGH>, <3 IRQ_TYPE_LEVEL_HIGH>;
				interrupt-names = "tx", "rx";
				apple,fifo-size = <0x{fifo:x}>;
				apple,helper-cpu = <&mtp>;

				multi-touch {{
					firmware-name = "{fw}";
				}};

				keyboard: keyboard {{
					/* overwritten by m1n1 from kblang-calibration */
					hid-country-code = <0>;
					apple,keyboard-layout-id = <0>;
				}};

				stm {{ }};
				actuator {{ }};
				tp_accel {{ }};
				tp-accel {{ }};
			}};
		}};
	}};
}};
""".format(vm_base=f["vm_base"], vm_size=f["vm_size"],
           base_hi=f["vm_base"] >> 32, base_lo=f["vm_base"] & 0xFFFFFFFF,
           size_hi=f["vm_size"] >> 32, size_lo=f["vm_size"] & 0xFFFFFFFF,
           asc=f["asc"], asc_hi=f["asc"] >> 32, asc_lo=f["asc"] & 0xFFFFFFFF,
           sram_hi=f["sram"] >> 32, sram_lo=f["sram"] & 0xFFFFFFFF,
           mbox=f["mbox"], mbox_hi=f["mbox"] >> 32, mbox_lo=f["mbox"] & 0xFFFFFFFF,
           irq_block=f["dock_irq_block"], irq_hi=f["dock_irq_block"] >> 32,
           irq_lo=f["dock_irq_block"] & 0xFFFFFFFF, dock_irq=f["dock_irq"],
           rb_hi=f["dock_ranges_base"] >> 32, rb_lo=f["dock_ranges_base"] & 0xFFFFFFFF,
           fifo=f["fifo_size"], fw=FIRMWARE_NAME, iommus=iommus, irqs=irqs)


# --------------------------------------------------------------------------- main

def describe(tree, paths):
    out = {}
    for path in paths:
        node = tree.node(path)
        out[path] = {k: v.hex() for k, v, _ in node.props}
    return out


def run(base_path, adt_json, sids):
    base_blob = Path(base_path).read_bytes()
    base_sha = hashlib.sha256(base_blob).hexdigest()
    facts = mtp_adt.facts(adt_json)
    tree = fdtedit.parse(base_blob)
    if fdtedit.encode(fdtedit.parse(base_blob)) != base_blob:
        raise AssertionError("fdtedit round trip failed on the base DTB")
    base_tree = fdtedit.parse(base_blob)
    ph = build(tree, facts, sids)
    check(base_tree, tree, facts, ph, sids)
    return base_sha, facts, ph, fdtedit.encode(tree), tree


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("base_dtb")
    ap.add_argument("adt_json")
    ap.add_argument("out_dtb")
    ap.add_argument("delta_json")
    ap.add_argument("--sids", default="1", help="comma separated DART stream ids (default 1)")
    ap.add_argument("--dts", help="also write the review fragment here")
    args = ap.parse_args()
    sids = tuple(int(x) for x in args.sids.split(","))
    base_sha, facts, ph, blob, tree = run(args.base_dtb, args.adt_json, sids)
    Path(args.out_dtb).write_bytes(blob)
    delta = {
        "base": {"sha256": base_sha, "known": KNOWN_BASES.get(base_sha, "UNKNOWN base (checked structurally)")},
        "out": {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)},
        "sids": list(sids),
        "adt_facts": {k: (hex(v) if isinstance(v, int) else v) for k, v in facts.items()},
        "phandles": ph,
        "added_nodes": describe(tree, NEW_NODES),
        "dart_after": describe(tree, [DART_PATH])[DART_PATH],
        "aliases_keyboard": tree.node("/aliases").get("keyboard")[:-1].decode(),
        "labels": {
            "addresses/irqs/dma-range": "Confirmed (ADT)",
            "fifo-size 0x800": "Observed (live IORegistry; stripped from sanitized ADT)",
            "iommus <dart 1> for mtp/hid": "Likely (Asahi M2/M3 convention; macOS aliases SIDs 1-4 to 0)",
            "SRAM window 1 MiB at first firmware segment": "Likely",
            "DART register base +0 of the 0xc000 ADT region": "Likely (m1n1 dart_init_adt uses reg[0])",
        },
    }
    Path(args.delta_json).write_text(json.dumps(delta, indent=2) + "\n")
    if args.dts:
        Path(args.dts).write_text(render_dts(facts, ph, sids))
    print(json.dumps({"base": delta["base"], "out": delta["out"], "phandles": ph}, indent=2))


if __name__ == "__main__":
    main()
