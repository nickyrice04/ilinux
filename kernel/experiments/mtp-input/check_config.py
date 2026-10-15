#!/usr/bin/env python3
"""Config delta for native keyboard/trackpad input, checked against a kernel .config.

usage: python3 -I check_config.py KERNEL_CONFIG [--fragment OUT]

Reports (a) which symbols the delta must change, (b) which preconditions already
hold, and (c) any dependency the delta would leave unmet. With --fragment it
writes a merge_config.sh-style fragment containing only the lines to change.
Stdlib only; reads the .config as text and never executes anything.
"""
import argparse
import re
import sys
from pathlib import Path

# The delta. Every entry says why; all are Kconfig facts from the pinned Asahi tree
# (77cb8f24) except the two marked "policy".
SET = {
    "APPLE_RTKIT_HELPER": ("y", "dockchannel-hid defers until its apple,helper-cpu device has "
                           "probed (dockchannel-hid.c probe: device_link + DL_DEV_DRIVER_BOUND); "
                           "without this driver nothing binds the MTP node"),
    "HID_APPLE": ("y", "Apple keyboard quirks: fn/media mapping, layout; the internal keyboard "
                  "is HID_TYPE_SPI_KEYBOARD (dockchannel-hid.c)"),
    "HID_MAGICMOUSE": ("y", "multi-touch trackpad reports (HID_TYPE_SPI_MOUSE interface)"),
    "HIDRAW": ("y", "raw access for first-light debugging of reports (/dev/hidraw*)"),
}
RECOMMENDED = {
    "FW_LOADER_USER_HELPER": ("n", "policy: trackpad firmware is read from the initramfs; with the "
                              "helper on, a missing blob stalls open() ~60 s instead of failing fast"),
}
# Already required by the driver stack; the delta is only valid on top of these.
PRECONDITIONS = {
    "APPLE_RTKIT": "y", "APPLE_MAILBOX": "y", "APPLE_DART": "y", "APPLE_DOCKCHANNEL": "y",
    "HID_DOCKCHANNEL": "y", "HID": "y", "INPUT": "y", "INPUT_EVDEV": "y", "OF": "y",
    "IOMMU_DMA": "y", "FW_LOADER": "y", "LEDS_CLASS": "y", "NEW_LEDS": "y",
}
LINE = re.compile(r"^(?:# )?CONFIG_([A-Z0-9_]+)(?:=(.*)| is not set)$")


def load(path):
    state = {}
    for raw in Path(path).read_text().splitlines():
        m = LINE.match(raw.strip())
        if not m:
            continue
        name, value = m.group(1), m.group(2)
        state[name] = value if value is not None else "n"
    return state


def evaluate(state):
    result = {"change": {}, "recommend": {}, "met": {}, "unmet": {}, "absent": []}
    for name, (want, why) in SET.items():
        have = state.get(name, "n")
        if have != want:
            result["change"][name] = (have, want, why)
    for name, (want, why) in RECOMMENDED.items():
        have = state.get(name, "n")
        if have != want:
            result["recommend"][name] = (have, want, why)
    for name, want in PRECONDITIONS.items():
        if name not in state:
            result["absent"].append(name)
        elif state[name] == want:
            result["met"][name] = want
        else:
            result["unmet"][name] = (state[name], want)
    return result


def fragment(result):
    lines = ["# kernel/experiments/mtp-input: native keyboard/trackpad input"]
    for name, (_, want, _) in sorted(result["change"].items()):
        lines.append("CONFIG_%s=%s" % (name, want))
    for name, (_, want, _) in sorted(result["recommend"].items()):
        lines.append("# policy: CONFIG_%s=%s" % (name, want) if want != "n"
                     else "# CONFIG_%s is not set" % name)
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--fragment")
    args = ap.parse_args()
    result = evaluate(load(args.config))
    print("config:", args.config)
    print("change (%d):" % len(result["change"]))
    for name, (have, want, why) in sorted(result["change"].items()):
        print("  CONFIG_%-22s %s -> %s   %s" % (name, have, want, why))
    print("recommended (%d):" % len(result["recommend"]))
    for name, (have, want, why) in sorted(result["recommend"].items()):
        print("  CONFIG_%-22s %s -> %s   %s" % (name, have, want, why))
    print("preconditions met: %d; unmet: %s; absent: %s" % (
        len(result["met"]), sorted(result["unmet"]) or "none", sorted(result["absent"]) or "none"))
    if args.fragment:
        Path(args.fragment).write_text(fragment(result))
    return 1 if result["unmet"] or result["absent"] else 0


if __name__ == "__main__":
    sys.exit(main())
