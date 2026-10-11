#!/usr/bin/env python3
"""Map each SoC device-tree node (AppleARMIODevice nub) to the macOS driver
classes attached beneath it in the IOService plane.

Read-only: runs `ioreg -p IOService -w0` (no properties) and keeps only the
nub names (which come from the Apple Device Tree) and IOKit *class* names of
their descendants.  Entry names below the nubs are discarded, so connected
peripherals' names (which may be personal) never reach the output.

Usage: ioreg_driver_map.py OUT.tsv
"""
import re
import subprocess
import sys

LINE = re.compile(r"^(?P<indent>[ |]*)\+-o (?P<name>.+?)  <class (?P<cls>[A-Za-z0-9_]+)")


def main():
    out_path = sys.argv[1]
    text = subprocess.run(["ioreg", "-p", "IOService", "-w0"], check=True,
                          capture_output=True, text=True).stdout
    rows = []
    stack = []  # (depth, name, cls)
    current_nub = None  # (depth, name)
    drivers = {}
    order = []
    for line in text.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        depth = len(m.group("indent")) // 2
        name, cls = m.group("name"), m.group("cls")
        if current_nub and depth <= current_nub[0]:
            current_nub = None
        if cls == "AppleARMIODevice":
            current_nub = (depth, name)
            if name not in drivers:
                drivers[name] = []
                order.append(name)
            continue
        if current_nub and depth <= current_nub[0] + 3:
            lst = drivers[current_nub[1]]
            if cls not in lst:
                lst.append(cls)
    with open(out_path, "w") as f:
        f.write("adt_node\tmacos_driver_classes(depth<=3)\n")
        for n in order:
            f.write("%s\t%s\n" % (n, ",".join(drivers[n])))
    print("nubs:", len(order), file=sys.stderr)


if __name__ == "__main__":
    main()
