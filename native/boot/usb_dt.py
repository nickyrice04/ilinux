"""boot036 Stage-B DT contract: dwc3 peripheral cores for the USB control channel.

The delta from the boot035 Stage-B DT, and nothing else:

* One `snps,dwc3` node per usb-drd port (ADT usb-drd0..2 = ports 1..3):
  peripheral only, high speed (m1n1 parks the PIPE mux on the dummy PHY), the
  four quirks that keep the USB2 PHY out of suspend (no Linux PHY driver can
  bring it back), and DMA through that port's second USB DART with stream 1.
  That is the DART instance and stream m1n1's own USB gadget uses on this Mac
  (third_party/m1n1/src/usb.c usb_dart_init: instance 1, SID = ADT
  dart-usbN/mapper-usbN reg = 1).
* Those three DARTs enabled, without `power-domains`, each with a new phandle.
* Every PMGR power-controller of ATC ports 0-2 (label atc0_* .. atc2_*, 39
  nodes) disabled. Linux then never probes them, so it neither arms
  AUTO_ENABLE nor releases them through the boot034 ladder: the PHY and power
  state of the three ports stay exactly as m1n1 left them.

No MMIO, transport writes or ADT access happen here.
"""
import re
import struct

AIC = "/soc/interrupt-controller@280400000"
PMGR = ("/soc/power-management@280600000", "/soc/power-management@288300000")
ATC_LABEL = re.compile(r"atc[012]_")
ATC_COUNT = 39
# (dwc3 node, core base, AIC IRQ, DART instance 1) from the ADT: usb-drdN reg[0]
# and interrupts[0], dart-usbN reg[1], both translated through /arm-io ranges.
PORTS = (
    ("/soc/usb@2a2280000", 0x2a2280000, 0x58b, "/soc/iommu@2a2f80000"),
    ("/soc/usb@2aa280000", 0x2aa280000, 0x5ab, "/soc/iommu@2aaf80000"),
    ("/soc/usb@382280000", 0x382280000, 0x5cb, "/soc/iommu@382f80000"),
)
CORE_SIZE = 0xcd00   # dwc3 core window (xHCI, global, device, OTG); Apple glue follows
SID = 1
QUIRKS = ("snps,usb2-gadget-lpm-disable", "snps,dis_u2_susphy_quirk",
          "snps,dis_u3_susphy_quirk", "snps,dis_enblslpm_quirk")


def _label(node):
    return node.get("label", b"").rstrip(b"\0").decode("ascii", "replace")


def atc_domains(tree):
    found = sorted(path for path in tree
                   if path.rsplit("/", 1)[0] in PMGR and ATC_LABEL.match(_label(tree[path])))
    if len(found) != ATC_COUNT:
        raise ValueError("expected %d ATC 0-2 power domains, found %d" % (ATC_COUNT, len(found)))
    return found


def dwc3_node(base, irq, dart_phandle, aic_phandle):
    node = {
        "compatible": b"snps,dwc3\0",
        "reg": struct.pack(">IIII", base >> 32, base & 0xffffffff, 0, CORE_SIZE),
        "interrupt-parent": aic_phandle,
        "interrupts": struct.pack(">III", 0, irq, 4),
        "dr_mode": b"peripheral\0",
        "maximum-speed": b"high-speed\0",
        "iommus": struct.pack(">II", dart_phandle, SID),
    }
    node.update({quirk: b"" for quirk in QUIRKS})
    return node


def amendment(tree):
    """DTS text appended to the decompiled boot035 Stage-B DT to make boot036's."""
    lines = ["", "/* boot036 USB control channel: native/boot/usb_dt.py */"]
    lines += ['&{%s} { status = "disabled"; };' % path for path in atc_domains(tree)]
    lines += ["&{%s} { /delete-property/ power-domains; /delete-property/ status; };" % dart
              for _, _, _, dart in PORTS]
    lines.append("&{/soc} {")
    for dwc3, base, irq, dart in PORTS:
        lines += [
            "\t%s {" % dwc3.rsplit("/", 1)[1],
            '\t\tcompatible = "snps,dwc3";',
            "\t\treg = <0x%x 0x%x 0x0 0x%x>;" % (base >> 32, base & 0xffffffff, CORE_SIZE),
            "\t\tinterrupt-parent = <&{%s}>;" % AIC,
            "\t\tinterrupts = <0x0 0x%x 0x4>;" % irq,
            '\t\tdr_mode = "peripheral";',
            '\t\tmaximum-speed = "high-speed";',
        ]
        lines += ["\t\t%s;" % quirk for quirk in QUIRKS]
        lines += ["\t\tiommus = <&{%s} 0x%x>;" % (dart, SID), "\t};"]
    lines.append("};")
    return "\n".join(lines) + "\n"


def check_delta(before, after):
    """Raise unless `after` is exactly `before` (boot035 Stage-B) plus the boot036 delta."""
    expected = {path: dict(node) for path, node in before.items()}
    for path in atc_domains(before):
        if "status" in expected[path] or "apple,always-on" in expected[path]:
            raise ValueError("ATC domain not in its boot035 state: " + path)
        expected[path]["status"] = b"disabled\0"
    used = {struct.unpack(">I", node["phandle"])[0]
            for node in after.values() if len(node.get("phandle", b"")) == 4}
    if sum(len(node.get("phandle", b"")) == 4 for node in after.values()) != len(used):
        raise ValueError("duplicate phandle in boot036 DT")
    aic = before.get(AIC, {}).get("phandle")
    if aic is None or len(aic) != 4:
        raise ValueError("AIC phandle missing")
    for dwc3, base, irq, dart in PORTS:
        node = expected.get(dart)
        if (node is None or node.get("status") != b"disabled\0" or "phandle" in node
                or "power-domains" not in node or dwc3 in before):
            raise ValueError("DART or dwc3 node not in its boot035 state: " + dart)
        del node["status"], node["power-domains"]
        phandle = after.get(dart, {}).get("phandle", b"")
        if len(phandle) != 4 or struct.unpack(">I", phandle)[0] in (0, 0xffffffff):
            raise ValueError("DART phandle missing or invalid: " + dart)
        node["phandle"] = phandle
        expected[dwc3] = dwc3_node(base, irq, struct.unpack(">I", phandle)[0], aic)
    if expected != after:
        differ = sorted(path for path in set(expected) | set(after)
                        if expected.get(path) != after.get(path))
        raise ValueError("DT delta differs from the boot036 USB contract: " + ", ".join(differ[:6]))
