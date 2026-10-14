#!/usr/bin/env python3
"""Add bounded diagnostics to the exact retained dd.c, in an isolated copy."""
import hashlib
from pathlib import Path
import sys
root = Path(sys.argv[1])
here = Path(__file__).resolve().parent
path = root / 'drivers/base/dd.c'
s = path.read_text()
expected = (here / 'dd-source.sha256').read_text().strip()
if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
    raise SystemExit('STOP: deferred-probe source differs from reviewed boot025')
s = s.replace('#include "power/power.h"', '#include "power/power.h"\n#include "ilinux_probe_diag.h"', 1)
s = s.replace('\t\tbus_probe_device(dev);', '\t\tilinux_probe_retry(dev, true);\n\t\tbus_probe_device(dev);\n\t\tilinux_probe_retry(dev, false);', 1)
worker_start = s.index('static void deferred_probe_work_func(')
worker_end = s.index('static DECLARE_WORK(deferred_probe_work,', worker_start)
w = s[worker_start:worker_end]
w = w.replace('\tmutex_lock(&deferred_probe_mutex);', '\tilinux_probe_worker_mark(1);\n\tmutex_lock(&deferred_probe_mutex);\n\tilinux_probe_worker_mark(2);', 1)
w = w.replace('\t\tdevice_pm_move_to_tail(dev);', '\t\tilinux_probe_worker_mark(3);\n\t\tdevice_pm_move_to_tail(dev);')
w = w.replace('\t\tbus_probe_device(dev);', '\t\tilinux_probe_worker_mark(4);\n\t\tbus_probe_device(dev);\n\t\tilinux_probe_worker_mark(5);')
w = w.replace('\t\tmutex_lock(&deferred_probe_mutex);', '\t\tilinux_probe_worker_mark(6);\n\t\tmutex_lock(&deferred_probe_mutex);\n\t\tilinux_probe_worker_mark(2);')
w = w.replace('\tmutex_unlock(&deferred_probe_mutex);\n}', '\tmutex_unlock(&deferred_probe_mutex);\n\tilinux_probe_worker_mark(7);\n}')
s = s[:worker_start] + w + s[worker_end:]
start = s.index('static int deferred_probe_initcall(void)')
end = s.index('late_initcall(deferred_probe_initcall);', start)
part = s[start:end]
part = part.replace('{\n', '{\n\tilinux_probe_begin();\n\tilinux_probe_mark(3);\n', 1)
part = part.replace('\tdriver_deferred_probe_enable = true;', '\tilinux_probe_mark(4);\n\tdriver_deferred_probe_enable = true;', 1)
part = part.replace('\tflush_work(&deferred_probe_work);', '\tilinux_probe_mark(5);\n\tflush_work(&deferred_probe_work);\n\tilinux_probe_mark(6);', 1)
# Second trigger/flush is still performed; no bypass or timeout of driver work.
needle = '\tdriver_deferred_probe_trigger();\n\tflush_work(&deferred_probe_work);'
assert part.count(needle) == 1
part = part.replace(needle, '\tdriver_deferred_probe_trigger();\n\tilinux_probe_mark(7);\n\tflush_work(&deferred_probe_work);\n\tilinux_probe_mark(8);')
part = part.replace('\treturn 0;', '\tilinux_probe_end();\n\treturn 0;', 1)
s = s[:start] + part + s[end:]
path.write_text(s)
(path.parent / 'ilinux_probe_diag.h').write_bytes((here / 'ilinux_probe_diag.h').read_bytes())
print('PASS: deferred-probe diagnostics applied; both triggers/flushes retained')
