#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Bind two PS reads and CPU1 startup to this machine's live parsed ADT.

Called only before startup. Parsed/raw ADT never leaves transient memory.
"""
import contextlib
import importlib.util
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('topology31g', ROOT / 'kernel/experiments/cpu-topology31g/topology.py')
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
ADDRESSES = (0x280600000, 0x280600008)


def bind(root):
    t.need(root._pmgr_path == '/arm-io/pmgr' and not root._pmgr_u8id and
           root._pmgr_use_group_and_offset, 'pmgr_format')
    pmgr = root['/arm-io/pmgr']
    cpus = [{key: getattr(cpu, key.replace('-', '_')) for key in t.KEYS}
            for cpu in root['/cpus']]
    rows = t.plan(cpus, pmgr.acc_cores, pmgr.edt_property_ver)
    target = rows[1]
    t.need(target['die_start_mask'] == target['cluster_start_mask'] == 2 and
           target['cluster_start_offset'] == 8, 'cpu1_start_mapping')
    for cpu, address in enumerate(ADDRESSES):
        devices = [d for d in pmgr.devices if d.name == 'MCPU0_' + str(cpu)]
        t.need(len(devices) == 1, 'ps_device_count')
        d = devices[0]
        block, size = root.pmgr_dev_get_block(d)
        t.need(root.pmgr_dev_get_id(d) == cpu + 1 and
               not any(v for k,v in d.flags.items() if not k.startswith('_')) and
               not any(root.pmgr_dev_get_parents(d)) and d.group == 0 and
               pmgr.ps_groups[0].reg == 0 and pmgr.ps_groups[0].offset == 0 and
               block == ADDRESSES[0] and d.offset == 8 * cpu and
               root.pmgr_dev_get_addr(d) == address and d.offset + 4 <= size,
               'ps_address_binding')
    return dict(live_adt_bound=True, cpu_ids=[0,1], width_bits=32,
                cpu1_start_mapping_unchanged=True, all18_topology_mapping_validated=True,
                later_cluster_legacy_mask_mismatch_cpu_ids=list(range(6,18)))


def read(iface, proxy):
    from m1n1.tgtypes import BootArgs_r2, BootArgs_r3
    from m1n1.adt import load_adt
    address, revision = proxy.get_bootargs_rev()
    t.need(revision in (2,3), 'ps_bootargs_revision')
    ba = iface.readstruct(address, BootArgs_r3 if revision == 3 else BootArgs_r2)
    lo, hi = ba.phys_base, ba.phys_base + ba.mem_size
    ptr, size = ba.devtree - ba.virt_base + ba.phys_base, ba.devtree_size
    t.need(ba.revision == revision and 1<<40 <= lo < hi <= (1<<40)+(1<<37) and
           0 < size <= 2*1024**2 and lo <= ptr < ptr+size <= hi, 'ps_adt_bounds')
    raw = iface.readmem(ptr,size)
    t.need(len(raw) == size, 'ps_adt_short_read')
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return bind(load_adt(raw))
