"""boot037 MTP input contract: Stage-B DT delta, kernel config delta, Image provenance.

boot037 is boot036 plus the keyboard/trackpad input path of the MTP coprocessor
(kernel/experiments/mtp-input; labelled findings in its README). Three exact
deltas against boot036, and nothing else:

* Stage-B DT: ten new nodes under /soc (the RTKit helper `mtp`, its mailbox, the
  DockChannel `fifo` with its HID child `input@8000` and six interface nodes);
  the MTP DART node (iommu@294800000) enabled, with a phandle and its IOVA
  window as apple,dma-range; the `keyboard` alias m1n1's dt_set_ipd() resolves.
  Addresses, interrupts and windows are the sanitized ADT's through the /arm-io
  ranges (+0x200000000). `apple,fifo-size` is Observed on the live IORegistry
  (the sanitizer strips its value) and stream id 1 is Likely (Asahi M2/M3
  convention; macOS aliases streams 1-4 to 0) until the E1 probe reports. Another
  stream id is another contract: change SIDS and say why.
* kernel.config: HIDRAW, HID_APPLE, HID_MAGICMOUSE and APPLE_RTKIT_HELPER from n
  to y. Kconfig then lists two symbols HIDRAW makes visible as "is not set"
  (HID_CP2112, HID_FT260); nothing else changes.
* Image: the ring-transport driver (patches/0002) is linked in, so its module
  parameters, compatible string and log format are in the Image. That is
  provenance, not correctness: it cannot say what the driver does.

No node may carry an `apple,*-gpios` property: the driver defers its probe until
a GPIO provider answers and t6050 has none. This module only decides whether
a DT, config or Image is the contract; no MMIO, transport write or ADT access.
"""
import struct

from kconfig_guard import TOOLCHAIN, config_delta, parse_config

AIC = "/soc/interrupt-controller@280400000"
DART = "/soc/iommu@294800000"
MTP = "/soc/mtp@294600000"
MBOX = "/soc/mbox@294608000"
DOCK = "/soc/fifo@294b14000"
HID = DOCK + "/input@8000"
KEYBOARD = HID + "/keyboard"
INTERFACES = ("multi-touch", "keyboard", "stm", "actuator", "tp_accel", "tp-accel")
NEW_NODES = (MTP, MBOX, DOCK, HID) + tuple(HID + "/" + name for name in INTERFACES)
PHANDLES = (("mtp", MTP), ("mbox", MBOX), ("dock", DOCK), ("dart", DART))

SIDS = (1,)                          # Likely; the E1 probe (mtp_probe.py) decides
DART_REG = (0x2, 0x94800000, 0x0, 0xc000)     # ADT dart-mtp reg[0] + 0x200000000
DART_IRQ = 0x293                              # ADT dart-mtp interrupts[0]
DMA_RANGE = (0x100, 0x4000, 0x0, 0xffff0000)  # ADT vm-base 0x10000004000, vm-size 0xffff0000
MAILBOX_IRQS = (0x2a4, 0x2a5, 0x2a6, 0x2a7)   # send-empty, send-not-empty, recv-empty, recv-not-empty
FIFO_SIZE = 0x800                             # Observed (live IORegistry), not in the sanitized ADT
FIRMWARE_NAME = "apple/tpmtfw-j716c.bin"      # read only when something opens the trackpad

CONFIG_SET = ("APPLE_RTKIT_HELPER", "HID_APPLE", "HID_MAGICMOUSE", "HIDRAW")
CONFIG_REVEALED = ("HID_CP2112", "HID_FT260")
# The driver stack the delta sits on (kernel/experiments/mtp-input/check_config.py).
CONFIG_NEEDED = {name: "y" for name in (
    "APPLE_RTKIT", "APPLE_MAILBOX", "APPLE_DART", "APPLE_DOCKCHANNEL", "HID_DOCKCHANNEL", "HID",
    "INPUT", "INPUT_EVDEV", "OF", "IOMMU_DMA", "FW_LOADER", "LEDS_CLASS", "NEW_LEDS")}
# Built-in parameters are named <module>.<parameter>; all of these are absent from boot036's Image.
IMAGE_MARKERS = (b"dockchannel_hid.mtp_ring\0", b"dockchannel_hid.mtp_enable_cmd\0",
                 b"dockchannel_hid.mtp_poll_ms\0", b"dockchannel_hid.mtp_ring_size\0",
                 b"apple,t6050-dockchannel-hid\0", b"Ring registered: iova ",
                 b"apple,dockchannel-hid\0")


def cells(*values):
    return struct.pack(">%dI" % len(values), *values)


def strings(*values):
    return b"".join(value.encode("ascii") + b"\0" for value in values)


def _phandle(node):
    value = node.get("phandle", b"")
    if len(value) != 4 or struct.unpack(">I", value)[0] in (0, 0xffffffff):
        return None
    return struct.unpack(">I", value)[0]


def new_nodes(aic, handle):
    """The exact property dict of every new node. `aic` is the AIC phandle (bytes), `handle`
    maps mtp, mbox, dock and dart to their phandle values."""
    iommus = b"".join(cells(handle["dart"], sid) for sid in SIDS)
    nodes = {
        MTP: {
            "compatible": strings("apple,t6050-mtp", "apple,t6050-rtk-helper-asc4",
                                  "apple,mtp", "apple,rtk-helper-asc4"),
            "reg": cells(0x2, 0x94600000, 0x0, 0x4000, 0x2, 0x94c00000, 0x0, 0x100000),
            "reg-names": strings("asc", "sram"),
            "mboxes": cells(handle["mbox"]),
            "iommus": iommus,
            "#helper-cells": cells(0),
            "phandle": cells(handle["mtp"]),
        },
        MBOX: {
            "compatible": strings("apple,t6050-asc-mailbox", "apple,asc-mailbox-v4"),
            "reg": cells(0x2, 0x94608000, 0x0, 0x4000),
            "interrupt-parent": aic,
            "interrupts": b"".join(cells(0, irq, 4) for irq in MAILBOX_IRQS),
            "interrupt-names": strings("send-empty", "send-not-empty", "recv-empty", "recv-not-empty"),
            "#mbox-cells": cells(0),
            "phandle": cells(handle["mbox"]),
        },
        DOCK: {
            "compatible": strings("apple,t6050-dockchannel", "apple,dockchannel"),
            "reg": cells(0x2, 0x94b14000, 0x0, 0x4000),
            "reg-names": strings("irq"),
            "interrupt-parent": aic,
            "interrupts": cells(0, 0x294, 4),
            "ranges": cells(0, 0x2, 0x94b28000, 0x20000),
            "nonposted-mmio": b"",
            "#address-cells": cells(1),
            "#size-cells": cells(1),
            "interrupt-controller": b"",
            "#interrupt-cells": cells(2),
            "phandle": cells(handle["dock"]),
        },
        HID: {
            "compatible": strings("apple,t6050-dockchannel-hid", "apple,dockchannel-hid"),
            "reg": cells(0x8000, 0x4000, 0xc000, 0x4000, 0x0, 0x4000, 0x4000, 0x4000),
            "reg-names": strings("config", "data", "rmt-config", "rmt-data"),
            "iommus": iommus,
            "interrupt-parent": cells(handle["dock"]),
            "interrupts": cells(2, 4, 3, 4),
            "interrupt-names": strings("tx", "rx"),
            "apple,fifo-size": cells(FIFO_SIZE),
            "apple,helper-cpu": cells(handle["mtp"]),
        },
    }
    for name in INTERFACES:
        nodes[HID + "/" + name] = {}
    nodes[HID + "/multi-touch"]["firmware-name"] = strings(FIRMWARE_NAME)
    # m1n1 overwrites both from the ADT's kblang-calibration through the `keyboard` alias.
    nodes[KEYBOARD]["hid-country-code"] = cells(0)
    nodes[KEYBOARD]["apple,keyboard-layout-id"] = cells(0)
    return nodes


def check_delta(before, after):
    """Raise unless `after` is exactly `before` (boot036 Stage-B) plus the boot037 DT delta."""
    if _phandle(before.get(AIC, {})) is None:
        raise ValueError("AIC phandle missing")
    aic = before[AIC]["phandle"]
    dart = before.get(DART)
    if dart is None or dart.get("reg") != cells(*DART_REG) or dart.get("interrupts") != cells(0, DART_IRQ, 4):
        raise ValueError("MTP DART is not the ADT's dart-mtp: " + DART)
    if (dart.get("status") != b"disabled\0" or "phandle" in dart or "power-domains" in dart
            or "apple,dma-range" in dart):
        raise ValueError("MTP DART not in its boot036 state: " + DART)
    if "/aliases" not in before or "keyboard" in before["/aliases"] or any(p in before for p in NEW_NODES):
        raise ValueError("boot036 DT already holds MTP nodes or a keyboard alias")
    handle = {}
    for key, path in PHANDLES:
        handle[key] = _phandle(after.get(path, {}))
        if handle[key] is None:
            raise ValueError("phandle missing or invalid: " + path)
    final = [struct.unpack(">I", node["phandle"])[0] for node in after.values()
             if len(node.get("phandle", b"")) == 4]
    if len(set(final)) != len(final):   # also a new handle that reuses a boot036 one
        raise ValueError("duplicate phandle in boot037 DT")
    expected = {path: dict(node) for path, node in before.items()}
    del expected[DART]["status"]
    expected[DART]["apple,dma-range"] = cells(*DMA_RANGE)
    expected[DART]["phandle"] = cells(handle["dart"])
    expected.update(new_nodes(aic, handle))
    expected["/aliases"]["keyboard"] = strings(KEYBOARD)
    if expected != after:
        differ = sorted(path for path in set(expected) | set(after) if expected.get(path) != after.get(path))
        raise ValueError("DT delta differs from the boot037 MTP contract: " + ", ".join(differ[:6]))


def check_config(before_text, after_text, allow_toolchain=False):
    """Raise unless the config delta is exactly the four input symbols going from n to y.

    allow_toolchain: also accept toolchain-detection differences (a packaged
    baseline); returns their names."""
    delta = config_delta(before_text, after_text)
    toolchain = sorted(name for name in delta if allow_toolchain and TOOLCHAIN.fullmatch(name))
    changed = sorted(set(delta) - set(toolchain))
    if changed != sorted(CONFIG_SET):
        raise ValueError("kernel config delta differs: unexpected %s, missing %s" % (
            sorted(set(changed) - set(CONFIG_SET)), sorted(set(CONFIG_SET) - set(changed))))
    for name in CONFIG_SET:
        if delta[name] != ("n", "y"):
            raise ValueError("CONFIG_%s must go from n to y" % name)
    before, after = parse_config(before_text), parse_config(after_text)
    shown = set(after) - set(before) - set(CONFIG_SET)
    shown = sorted(name for name in shown if not (allow_toolchain and TOOLCHAIN.fullmatch(name)))
    if shown != sorted(CONFIG_REVEALED) or any(after[name] != "n" for name in shown):
        raise ValueError("kernel config lists unexpected new symbols: %s (expected only %s, not set)" % (
            shown, list(CONFIG_REVEALED)))
    if set(before) - set(after):
        raise ValueError("kernel config lost symbols: %s" % sorted(set(before) - set(after))[:8])
    for name, value in CONFIG_NEEDED.items():
        if after.get(name) != value:
            raise ValueError("CONFIG_%s must be %s" % (name, value))
    return toolchain


def check_image(image):
    """Raise unless the Image carries the ring-transport driver's parameters, compatible and log."""
    missing = [marker.rstrip(b"\0").decode("ascii") for marker in IMAGE_MARKERS if marker not in image]
    if missing:
        raise ValueError("Image lacks the MTP ring-transport driver: " + ", ".join(missing))
