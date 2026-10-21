#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""VM-only actual pinned ADT parser; positive and mutation bindings."""
import importlib.util
from pathlib import Path
import sys
if sys.platform!='linux' or len(sys.argv)!=2:raise SystemExit('VM and pinned client required')
sys.path.insert(0,sys.argv[1])
from m1n1.adt import load_adt

def module(name):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
b=module('live_binding');f=module('fixture')
root=load_adt(f.adt());assert b.bind(root)['live_adt_bound']
checks=0
for change in (
    lambda r:setattr(r,'_pmgr_u8id',True),
    lambda r:setattr(r,'_pmgr_use_group_and_offset',False),
    lambda r:setattr(r['/cpus/cpu1'],'die_cluster_id',1),
    lambda r:setattr(r['/arm-io/pmgr'],'edt_property_ver',1),
    lambda r:setattr(r['/arm-io/pmgr'].devices[1],'offset',16),
    lambda r:setattr(r['/arm-io/pmgr'].devices[1],'id2',3),
    lambda r:setattr(r['/arm-io/pmgr'].devices[1].flags,'on',True),
    lambda r:setattr(r['/arm-io/pmgr'].ps_groups[0],'offset',8),
    lambda r:setattr(r['/arm-io/pmgr'].reg[0],'size',8),
    lambda r:setattr(r['/arm-io/pmgr'].reg[0],'addr',0x280600010),
    lambda r:r['/arm-io/pmgr'].devices.append(r['/arm-io/pmgr'].devices[1]),
):
    root=load_adt(f.adt());change(root)
    try:b.bind(root)
    except (ValueError,IndexError):checks+=1
    else:raise AssertionError('bad binding accepted')
print('LIVE-ADT-BINDING-PASS original fixtures; refusals='+str(checks))
