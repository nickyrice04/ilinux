#!/usr/bin/env python3
"""Apply diagnostic instrumentation to an isolated copy of job-020 source."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
here = Path(__file__).resolve().parent
head = root / "arch/arm64/kernel/head.S"
s = head.read_text()
assert "ilinux_entry_mark" not in s
s = s.replace('#include "efi-header.S"', '#include "efi-header.S"\n#include "ilinux-entry-markers.inc"')
s = s.replace("SYM_CODE_START(primary_entry)\n", "SYM_CODE_START(primary_entry)\n\tilinux_entry_mark 0\n", 1)
s = s.replace("\tmov\tx20, x0\n", "\tmov\tx20, x0\n\tilinux_entry_mark 1\n", 1)
s = s.replace("\tb\t__primary_switch\n", "\tilinux_entry_mark 2\n\tb\t__primary_switch\n", 1)
assert s.count("\tilinux_entry_mark ") == 3
s += '\n\t.pushsection ".idmap.text", "a"\n\t.balign 8\n\t.ascii "ILINUX-FB024-V1"\n\t.byte 0\nSYM_DATA_START(ilinux_fb_descriptor)\n\t.quad 0, 0\nSYM_DATA_END(ilinux_fb_descriptor)\n\t.popsection\n'
head.write_text(s)
(head.parent / "ilinux-entry-markers.inc").write_bytes((here / "entry-markers.inc").read_bytes())
(root / "drivers/firmware/efi/ilinux_earlycon.c").write_bytes((here / "ilinux_earlycon.c").read_bytes())
makefile = root / "drivers/firmware/efi/Makefile"
with makefile.open("a") as out:
    out.write("\nobj-$(CONFIG_EFI_EARLYCON) += ilinux_earlycon.o\n")
print("PASS: three pre-MMU entry markers and flat-DT early framebuffer console applied")
