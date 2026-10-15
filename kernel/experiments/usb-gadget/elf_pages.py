#!/usr/bin/env python3
"""Fail unless every ELF file under the given directories loads on a 16 KiB-page kernel.

usage: elf_pages.py DIR...
For each PT_LOAD segment: p_align >= 16 KiB and p_vaddr == p_offset (mod 16 KiB).
Prints one line per ELF file and exits 1 on any failure.
"""
from pathlib import Path
import struct
import sys

PAGE = 16384


def check(path):
    data = path.read_bytes()
    phoff, = struct.unpack_from("<Q", data, 32)
    phentsize, phnum = struct.unpack_from("<HH", data, 54)
    aligns = []
    for i in range(phnum):
        p_type, _, offset, vaddr, _, _, _, align = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phentsize)
        if p_type == 1:
            if align < PAGE or (vaddr - offset) % PAGE:
                return "BAD align=%#x vaddr=%#x offset=%#x" % (align, vaddr, offset)
            aligns.append(align)
    return "OK align=%#x" % min(aligns) if aligns else "BAD no PT_LOAD"


def main(argv):
    bad = 0
    for root in argv[1:]:
        for path in sorted(Path(root).rglob("*")):
            if path.is_file() and not path.is_symlink() and path.read_bytes()[:4] == b"\x7fELF":
                result = check(path)
                bad += result.startswith("BAD")
                print("%s %s" % (result, path.relative_to(root)))
    print("%s: %d ELF file(s) failed the 16 KiB page check" % ("FAIL" if bad else "PASS", bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
