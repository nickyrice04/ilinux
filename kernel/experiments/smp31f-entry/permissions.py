#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""31F fixed vector hook probes; shared helper/decoder remain frozen31E."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('permissions31e',Path(__file__).resolve().parents[1]/'smp31e-entry/permissions.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
HELPER_TAIL=previous.HELPER_TAIL
select_regime=previous.select_regime
verify_helper_tail=previous.verify_helper_tail
validate_probe=previous.validate_probe


def probe_plan(base):
    # Same first page, existing alias and memory-attribute checks. The new
    # vector hook is offset0; preserve all other reviewed probe semantics.
    result=[]
    for probe in previous.probe_plan(base):
        probe=dict(probe)
        if probe['name'].startswith('hook_'):
            old=probe['physical']
            probe['physical']=base
            probe['address']-=old-base
        if probe['name'].startswith('stub_last_'):
            old=probe['physical']
            probe['physical']=base+0xaa4
            probe['address']-=old-probe['physical']
        result.append(probe)
    return tuple(result)
