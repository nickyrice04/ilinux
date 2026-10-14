#!/usr/bin/env python3
"""Repair boot028 diagnostic mapping and add context-switch boundaries."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
here = Path(__file__).resolve().parent
for name, digest in json.loads((here / 'source-sha256.json').read_text()).items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
        raise SystemExit('STOP: source differs from reviewed boot028: ' + name)

def once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit('STOP: ambiguous source anchor: ' + repr(old))
    return text.replace(old, new, 1)

fb = root / 'drivers/firmware/efi/ilinux_earlycon.c'
f = fb.read_text()
a = f.index('static int __init fb_remap(void)')
b = f.index('early_initcall(fb_remap);', a)
f = f[:a] + '#include "ilinux-fb-map.h"\n' + f[b:]
a = f.index('static int __init fb_setup(')
b = f.index('\n\t/* Keep top-left', a)
f = f[:a] + '''static int __init fb_setup(struct earlycon_device *dev, const char *opt)
{
	int err;
	if (opt && *opt)
		return -EINVAL;
	err = fb_prepare();
	if (err)
		return err;
''' + f[b:]

core = root / 'kernel/sched/core.c'
s = core.read_text()
a = s.index('context_switch(struct rq *rq, struct task_struct *prev,')
b = s.index('\n/*', s.index('\n}\n', a))
part = s[a:b]
for phase, call in [
    (0x10, 'prepare_task_switch(rq, prev, next);'),
    (0x11, 'arch_start_context_switch(prev);'),
    (0x12, 'if (!next->mm) {'),
    (0x13, 'mm_cid_switch_to(prev, next);'),
    (0x14, 'rseq_sched_switch_event(next);'),
    (0x15, 'prepare_lock_switch(rq, next, rf);'),
    (0x16, 'switch_to(prev, next, prev);'),
    (0x17, 'return finish_task_switch(prev);')]:
    part = once(part, '\t'+call, f'\tilinux_probe_sched_mark({phase}, 0, 0);\n\t'+call)
s = s[:a] + part + s[b:]
# Correct indentation from the preceding instrumentation without changing it.
s = once(s, '\n\tilinux_probe_sched_mark(8, 0, 0);', '\n\t\tilinux_probe_sched_mark(8, 0, 0);')

process = root / 'arch/arm64/kernel/process.c'
t = process.read_text()
a = t.index('struct task_struct *__switch_to(')
b = t.index('\n}\n', a) + 3
part = t[a:b]
for phase, call in enumerate([
    'debug_switch_state();', 'fpsimd_thread_switch(next);',
    'tls_thread_switch(next);', 'hw_breakpoint_thread_switch(next);',
    'contextidr_thread_switch(next);', 'entry_task_switch(next);',
    'ssbs_thread_switch(next);', 'cntkctl_thread_switch(prev, next);',
    'ptrauth_thread_switch_user(next);', 'permission_overlay_switch(next);',
    'gcs_thread_switch(next);', 'actlr_thread_switch(next);',
    'dsb(ish);', 'mte_thread_switch(next);',
    'if (prev->thread.sctlr_user != next->thread.sctlr_user)',
    'mpam_thread_switch(next);', 'last = cpu_switch_to(prev, next);',
    'return last;'], 0x20):
    part = once(part, '\t'+call, f'\tilinux_probe_sched_mark({phase}, 0, 0);\n\t'+call)
t = t[:a] + part + t[b:]
t = once(t, '#include <asm/switch_to.h>', '#include <asm/switch_to.h>\nextern void ilinux_probe_sched_mark(unsigned int phase, int prev, int next);')

# All anchors validated before mutating the isolated source tree.
fb.write_text(f); core.write_text(s); process.write_text(t)
(fb.parent / 'ilinux-status-strip.h').write_bytes((here / 'status-strip.h').read_bytes())
(fb.parent / 'ilinux-fb-map.h').write_bytes((here / 'fb-map.h').read_bytes())
(root / 'drivers/base/ilinux_probe_diag.h').write_bytes((here / 'ilinux_probe_diag.h').read_bytes())
print('PASS: independent validated framebuffer mapping and context-switch markers applied')
