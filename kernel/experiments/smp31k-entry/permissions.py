#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31K cold tripwire probes; unchanged frozen PAR semantics, no target I/O."""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('_31k_permission_base',
    Path(__file__).resolve().parents[1]/'smp31e-entry/permissions.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
select_regime = previous.select_regime
validate_probe = previous.validate_probe


def probe_plan(base):
    result = []
    replacements = {'hook': ('cold_hook', 0x800),
                    'stub_first': ('cold_stub_first', 0xb00),
                    'stub_last': ('cold_stub_last', 0xb48),
                    'record_first': ('cold_record_first', 0x90a80),
                    'record_last': ('cold_record_last', 0x90ab8)}
    for original in previous.probe_plan(base):
        probe = dict(original)
        for old, (new, offset) in replacements.items():
            if probe['name'].startswith(old+'_'):
                delta = base+offset-probe['physical']
                probe['name'] = new+probe['name'][len(old):]
                probe['physical'] += delta
                probe['address'] += delta
                break
        result.append(probe)
    return tuple(result)
