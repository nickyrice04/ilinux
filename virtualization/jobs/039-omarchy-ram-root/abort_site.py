#!/usr/bin/env python3
"""abort_site.py BINARY SYMBOL OFFSET: print the C strings an AArch64 function loads (adrp+add)
in the 0x200 bytes before SYMBOL+OFFSET, e.g. the message of the assertion that aborted there
(Hyprland's RASSERT logs its message, then raises SIGABRT). Uses objdump; standard library."""
import re
import struct
import subprocess
import sys

binary, symbol, offset = sys.argv[1], sys.argv[2], int(sys.argv[3], 0)
nm = subprocess.run(["nm", "-D", "--defined-only", binary], capture_output=True, text=True).stdout
value = next(int(l.split()[0], 16) for l in nm.splitlines() if l.split()[-1] == symbol)
site = value + offset
dis = subprocess.run(["objdump", "-d", "--no-show-raw-insn", f"--start-address={site - 0x200:#x}",
                      f"--stop-address={site + 4:#x}", binary], capture_output=True, text=True).stdout
with open(binary, "rb") as f:
    elf = f.read()
phoff = struct.unpack_from("<Q", elf, 32)[0]
phentsize, phnum = struct.unpack_from("<HH", elf, 54)
loads = []
for i in range(phnum):
    p_type, _, off, vaddr, _, filesz, _, _ = struct.unpack_from("<IIQQQQQQ", elf, phoff + i * phentsize)
    if p_type == 1:
        loads.append((vaddr, off, filesz))


def cstring(addr):
    for vaddr, off, filesz in loads:
        if vaddr <= addr < vaddr + filesz:
            start = off + addr - vaddr
            return elf[start:elf.index(b"\0", start)].decode(errors="replace")
    return None


page = {}
print(f"abort site {site:#x} = {symbol}+{offset:#x}")
for line in dis.splitlines():
    m = re.match(r"\s*([0-9a-f]+):\s+adrp\s+(x\d+), ([0-9a-f]+)", line)
    if m:
        page[m.group(2)] = int(m.group(3), 16)
        continue
    m = re.match(r"\s*([0-9a-f]+):\s+add\s+(x\d+), (x\d+), #0x([0-9a-f]+)", line)
    if m and m.group(3) in page:
        s = cstring(page[m.group(3)] + int(m.group(4), 16))
        if s and len(s) > 3:
            print(f"{int(m.group(1), 16):#x}: {s[:200]!r}")
