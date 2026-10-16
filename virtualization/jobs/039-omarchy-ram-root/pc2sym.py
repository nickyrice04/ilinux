#!/usr/bin/env python3
"""pc2sym.py SYSTEM.MAP < hmp-registers.log: name the kernel symbol of every PC= and X30= value
in QEMU 'info registers' output (the guest must boot with nokaslr). Standard library only."""
import bisect
import re
import sys

syms = []
for line in open(sys.argv[1]):
    parts = line.split()
    if len(parts) == 3 and parts[1] in "tTwW":
        syms.append((int(parts[0], 16), parts[2]))
syms.sort()
addrs = [a for a, _ in syms]
for line in sys.stdin:
    for reg, value in re.findall(r"\b(PC|X30)=([0-9a-f]{16})", line):
        v = int(value, 16)
        i = bisect.bisect_right(addrs, v) - 1
        name = f"{syms[i][1]}+{v - syms[i][0]:#x}" if i >= 0 else "?"
        print(f"{reg} {value} {name}")
