#!/usr/bin/env python3
"""Keep scheduler diagnostics in RAM; render S only from the bounded watchdog."""
import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1])
p = root / 'drivers/base/ilinux_probe_diag.h'
s = p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest() == '3422bfdb33721d73ae718e363f5215a308b78de7f8b7c047dcadcb6ea400ae28'
assert s.count('\tilinux_probe_fb_mark(1, phase);') == 1
s = s.replace('\tilinux_probe_fb_mark(1, phase);',
              '\t/* No framebuffer writes, printk or allocation in scheduler context. */')
anchor = '\tilinux_probe_fb_mark(3, ilinux_probe_heartbeats + 1);'
assert s.count(anchor) == 1
s = s.replace(anchor, '\tilinux_probe_fb_mark(1, READ_ONCE(ilinux_sched_phase));\n' + anchor)
p.write_text(s)
print('PASS: scheduler hook records RAM only; watchdog samples S before H')
