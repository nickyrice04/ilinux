#!/usr/bin/env python3
"""Extract actual driver functions for register-access tests, never rewrite them."""
import sys
import re
from pathlib import Path

s = Path(sys.argv[1]).read_text()
out = Path(sys.argv[2])

def function(name):
    matches = list(re.finditer(r'^static [^\n]*\b' + name + r'\(', s, re.M))
    assert len(matches) == 1, name
    start = matches[0].start()
    brace = s.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (s[end] == '{') - (s[end] == '}')
        end += 1
    return s[start:end] + '\n'

pieces = [s[s.index('#define AIC_INFO\t'):s.index('static const struct of_device_id')]]
start = s.index('struct aic_irq_chip {')
pieces.append(s[start:s.index('\nstatic void aic_handle_ipi', start)])
start = s.index('#define TIMER_FIRING')
pieces.append(s[start:s.index('\nstatic void', start)])
for name in ['aic_fiq_get_idx', 'aic_fiq_set_mask', 'aic_fiq_clear_mask',
             'aic_fiq_mask', 'aic_fiq_unmask', 'aic_fiq_eoi',
             'aic_handle_irq', 'aic_handle_fiq', 'aic_irq_domain_translate',
             'aic_init_cpu']:
    pieces.append(function(name))
assert '.compatible = "apple,t6050-aic3",\n\t\t.data = &aic3_t6050_info' in s
assert '\tif (irqc->info.guest_timer_fiq)\n\t\tvgic_set_kvm_info(&vgic_info);' in s
out.write_text('\n'.join(pieces))
