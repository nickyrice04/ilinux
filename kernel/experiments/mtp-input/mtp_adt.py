"""MTP (keyboard/trackpad coprocessor) facts from our sanitized ADT (stdlib only).

Reads hardware/adt/adt-sanitized.json and returns the values the device-tree delta
needs, each with the property it came from. Nothing here is guessed: if the ADT
does not carry the value, the function raises instead of inventing one.

Values that the sanitizer strips (``fifo-size`` keeps its name but not its value)
are NOT read here; the DT tool takes them from FIFO_SIZE below and the README
labels that one Observed (live IORegistry on this Mac) rather than ADT.
"""
import json
from pathlib import Path

# Observed on this Mac's live IORegistry (macOS 26.6.2 / 25G83) because the
# sanitized ADT export keeps the property name `fifo-size` but not its value.
FIFO_SIZE = 0x800

PATHS = {
    "mtp": "/arm-io/mtp",
    "dart": "/arm-io/dart-mtp",
    "dock": "/arm-io/dockchannel-mtp",
    "transport": "/arm-io/dockchannel-mtp/mtp-transport",
    "keyboard": "/arm-io/dockchannel-mtp/mtp-transport/keyboard",
}
INTERFACES = ("multi-touch", "keyboard", "stm", "actuator", "tp-accel")


def load(path):
    tree = json.loads(Path(path).read_text())
    nodes, stack = {}, [tree]
    while stack:
        node = stack.pop()
        nodes[node["path"].replace("/Root/device-tree", "") or "/"] = node
        stack.extend(node.get("children", []))
    return nodes


def words(value):
    if isinstance(value, int):
        return [value]
    return [int(x, 16) if isinstance(x, str) else x for x in value]


def prop(nodes, path, name):
    values = nodes[path].get("values", {})
    if name not in values:
        raise KeyError("%s has no exported property %s" % (path, name))
    return values[name]


def arm_io_ranges(nodes):
    w = words(prop(nodes, "/arm-io", "ranges"))
    return [(w[i] | w[i + 1] << 32, w[i + 2] | w[i + 3] << 32, w[i + 4] | w[i + 5] << 32)
            for i in range(0, len(w) - 5, 6)]


def translate(ranges, addr):
    for child, parent, size in ranges:
        if child <= addr < child + size:
            return parent + addr - child
    raise ValueError("ADT address %#x is outside the /arm-io ranges" % addr)


def reg(nodes, path, index):
    entry = prop(nodes, path, "reg")[index]
    return int(entry["addr"], 16), int(entry["size"], 16)


def facts(adt_json):
    """Return {key: value} of everything the MTP DT delta uses."""
    nodes = load(adt_json)
    rng = arm_io_ranges(nodes)
    out = {}

    # --- MTP coprocessor (ASC) -------------------------------------------------
    compat = prop(nodes, PATHS["mtp"], "compatible")
    if compat != ["iop,ascwrap-v6"]:
        raise ValueError("unexpected MTP compatible %r" % (compat,))
    asc, asc_size = reg(nodes, PATHS["mtp"], 0)
    out["asc"] = translate(rng, asc)
    out["asc_window"] = asc_size
    out["mbox"] = out["asc"] + 0x8000              # asc-mailbox-v4 sits at ASC + 0x8000
    irqs = sorted(words(prop(nodes, PATHS["mtp"], "interrupts")))
    if len(irqs) != 4 or irqs != list(range(irqs[0], irqs[0] + 4)):
        raise ValueError("MTP mailbox interrupts are not four consecutive numbers: %r" % irqs)
    out["mbox_irqs"] = irqs                        # send-empty, send-not-empty, recv-empty, recv-not-empty
    # SRAM: base of the first firmware segment (physical, high word already set)
    seg = words(prop(nodes, PATHS["mtp"], "segment-ranges"))
    out["sram"] = seg[0] | seg[1] << 32
    out["role"] = prop(nodes, PATHS["mtp"], "role")

    # --- DART ----------------------------------------------------------------------
    if prop(nodes, PATHS["dart"], "compatible") != ["dart,t8110"]:
        raise ValueError("MTP DART is not dart,t8110")
    dart, dart_size = reg(nodes, PATHS["dart"], 0)
    out["dart"] = translate(rng, dart)
    out["dart_window"] = dart_size
    out["dart_irq"] = words(prop(nodes, PATHS["dart"], "interrupts"))[0]
    base = words(prop(nodes, PATHS["dart"], "vm-base"))
    size = words(prop(nodes, PATHS["dart"], "vm-size"))
    if len(base) != 2 or len(size) != 2:
        raise ValueError("vm-base / vm-size are not 64-bit values")
    out["vm_base"] = base[0] | base[1] << 32
    out["vm_size"] = size[0] | size[1] << 32
    out["sid"] = words(prop(nodes, PATHS["dart"], "sid"))
    out["sid_count"] = words(prop(nodes, PATHS["dart"], "sid-count"))[0]
    # `remap` is read as byte pairs (from, to) by AppleT8110DART::_dartSetup.
    raw = b"".join(x.to_bytes(4, "little") for x in words(prop(nodes, PATHS["dart"], "remap")))
    out["remap"] = [(raw[i], raw[i + 1]) for i in range(0, len(raw), 2) if raw[i] or raw[i + 1]]

    # --- DockChannel -----------------------------------------------------------------
    if prop(nodes, PATHS["dock"], "compatible") != ["dockchannel,t8002"]:
        raise ValueError("unexpected DockChannel compatible")
    regs = [reg(nodes, PATHS["dock"], i) for i in range(6)]
    if any(size != 0x1000 for _, size in regs):
        raise ValueError("DockChannel register blocks are not 0x1000 bytes")
    phys = [translate(rng, addr) for addr, _ in regs]
    out["dock_regs"] = phys
    # By analogy with the Linux t8112/t6030 layout: irq=reg[1]; config/data=reg[2]/[3];
    # rmt-config/rmt-data=reg[4]/[5]; the HID child's `ranges` window starts at reg[4].
    out["dock_irq_block"] = phys[1]
    out["dock_ranges_base"] = phys[4]
    if (phys[2] - phys[4], phys[3] - phys[4], phys[5] - phys[4]) != (0x8000, 0xc000, 0x4000):
        raise ValueError("DockChannel FIFO blocks do not follow the rmt/config/data layout")
    out["dock_irq"] = words(prop(nodes, PATHS["dock"], "interrupts"))[0]

    # --- Transport ----------------------------------------------------------------------
    if prop(nodes, PATHS["transport"], "compatible") != ["aht-hibernator"]:
        raise ValueError("unexpected MTP transport compatible")
    kids = sorted(c["path"].rsplit("/", 1)[1] for c in nodes[PATHS["transport"]].get("children", []))
    if kids != sorted(INTERFACES):
        raise ValueError("unexpected transport interfaces %r" % (kids,))
    out["interfaces"] = list(INTERFACES)
    if PATHS["keyboard"] not in nodes:
        raise ValueError("no keyboard node (m1n1 dt_set_ipd needs this exact path)")
    out["fifo_size"] = FIFO_SIZE
    return out
