#!/usr/bin/env python3
"""Instrument the reviewed boot027 scheduling boundary in a fresh VM copy."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
here = Path(__file__).resolve().parent
for name, digest in json.loads((here / 'source-sha256.json').read_text()).items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
        raise SystemExit('STOP: source differs from reviewed boot027: ' + name)

def once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit('STOP: ambiguous source anchor: ' + repr(old))
    return text.replace(old, new, 1)

core = root / 'kernel/sched/core.c'
s = core.read_text()
# Scheduler hooks store a few scalars and update fixed framebuffer cells only.
s = once(s, '#include "sched.h"', '#include "sched.h"\n\nextern void ilinux_probe_sched_mark(unsigned int phase, int prev, int next);')
start = s.index('static void __sched notrace __schedule(')
end = s.index('\nvoid __noreturn do_task_dead(', start)
part = s[start:end]
part = once(part, '\t/* Trace preemptions consistently', '\tilinux_probe_sched_mark(1, 0, 0);\n\n\t/* Trace preemptions consistently')
part = once(part, '\trq_lock(rq, &rf);', '\tilinux_probe_sched_mark(2, 0, 0);\n\trq_lock(rq, &rf);\n\tilinux_probe_sched_mark(3, 0, 0);')
part = once(part, '\tnext = pick_next_task(rq, rq->donor, &rf);', '\tilinux_probe_sched_mark(4, 0, 0);\n\tnext = pick_next_task(rq, rq->donor, &rf);')
part = once(part, 'picked:\n', 'picked:\n\tilinux_probe_sched_mark(5, prev->pid, next->pid);\n')
part = once(part, '\t\trq = context_switch(rq, prev, next, &rf);', '\t\tilinux_probe_sched_mark(6, 0, 0);\n\t\trq = context_switch(rq, prev, next, &rf);\n\tilinux_probe_sched_mark(8, 0, 0);')
part = once(part, '\ttrace_sched_exit_tp(is_switch);', '\tilinux_probe_sched_mark(9, 0, 0);\n\ttrace_sched_exit_tp(is_switch);')
s = s[:start] + part + s[end:]
start = s.index('static struct rq *finish_task_switch(')
end = s.index('\n/*', start)
part = s[start:end]
part = once(part, '\tunsigned int prev_state;\n', '\tunsigned int prev_state;\n\n\tilinux_probe_sched_mark(7, 0, 0);\n')
s = s[:start] + part + s[end:]

fb = root / 'drivers/firmware/efi/ilinux_earlycon.c'
f = fb.read_text()
f = once(f, 'static bool mapping_failed;', 'static bool mapping_failed;\n#include "ilinux-status-strip.h"')
f = once(f, 'if (cy + fb_font->height * 2 > fb_height)', 'if (cy + fb_font->height * 2 > fb_text_height)')
f = once(f, '\tmapping_failed = !fb_mapping;', '\tmapping_failed = !fb_mapping;\n\tif (fb_mapping && ilinux_probe_diag) {\n\t\tfb_text_height = fb_height - fb_font->height;\n\t\tcx = 0; cy = 0;\n\t\tfor (unsigned int lane = 0; lane < 4; lane++)\n\t\t\tilinux_probe_fb_mark(lane, 0);\n\t}')
f = once(f, 'if (fb_mapping && !console_is_registered(fb_console))', 'if (fb_mapping && !ilinux_probe_diag && !console_is_registered(fb_console))')
f = once(f, '\tcx = 0; cy = fb_font->height * 4;', '\tfb_text_height = fb_height;\n\tcx = 0; cy = fb_font->height * 4;')
# Validate every transformation before writing the isolated tree.
core.write_text(s)
fb.write_text(f)
(fb.parent / 'ilinux-status-strip.h').write_bytes((here / 'status-strip.h').read_bytes())
(root / 'drivers/base/ilinux_probe_diag.h').write_bytes((here / 'ilinux_probe_diag.h').read_bytes())
print('PASS: bounded preemption/IRQ-independent status and pre-armed watchdog applied')
