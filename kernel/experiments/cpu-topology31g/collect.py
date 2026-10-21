#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only, narrowly filtered topology collection; no raw IORegistry output."""
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess

spec = importlib.util.spec_from_file_location('topology31g', Path(__file__).with_name('topology.py'))
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)


def collect(tree):
    cpus, pmgr = [], []
    def integer(v):
        if type(v) is bytes and len(v) == 4:
            return int.from_bytes(v, 'little')
        if type(v) is int:
            return v
        raise ValueError('ordinal_type')
    def walk(n):
        name = n.get('IORegistryEntryName', '').split('@')[0]
        if name.startswith('cpu') and 'die-cluster-id' in n:
            cpus.append({key: integer(n[key]) for key in t.KEYS})
        if name == 'pmgr':
            pmgr.append((integer(n['edt-property-ver']), n['acc-cores']))
        for child in n.get('IORegistryEntryChildren', []):
            walk(child)
    for root in ([tree] if type(tree) is dict else tree):
        walk(root)
    t.need(len(pmgr) == 1, 'pmgr_count')
    version, acc = pmgr[0]
    rows = t.plan(cpus, acc, version)
    return dict(read_only=True, source='local_IODeviceTree_safe_topology_ordinals',
                edt_property_ver=version, topology=sorted(cpus, key=lambda r:r['cpu-id']),
                # Publish interpreted nonunique mapping, never the raw registry.
                startup_plan=rows, hardware_writes=0,
                cpu1_current_start_mapping_matches=True,
                later_cluster_legacy_die_mask_mismatch_cpu_ids=[r['cpu_id'] for r in rows
                    if not r['legacy_die_mask_matches']], native_smp='NOT RUN')


if __name__ == '__main__':
    try:
        result = subprocess.run(['/usr/sbin/ioreg','-a','-p','IODeviceTree','-l','-w0'],
            capture_output=True, check=True, timeout=30)
        print(json.dumps(collect(plistlib.loads(result.stdout)), indent=2))
    except Exception as error:
        raise SystemExit('topology collection refused: ' + type(error).__name__) from None
