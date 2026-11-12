#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the static J716c CPU inventory; Aura must fill runtime fields later."""
import importlib.util
import json
import struct
import sys
from pathlib import Path

spec=importlib.util.spec_from_file_location('fdt_read',Path(__file__).with_name('fdt_read.py'))
fdt=importlib.util.module_from_spec(spec);sys.modules[spec.name]=fdt;spec.loader.exec_module(fdt)
EXPECTED=[0x40000+i for i in range(6)]+[0x40100+i for i in range(6)]+[0x10200+i for i in range(6)]

def inspect(blob):
    root,reservations,boot=fdt.parse(blob)
    compatible=fdt.text(root.props['compatible'])
    if 'apple,j716c' not in compatible or 'apple,t6050' not in compatible:
        raise ValueError('wrong board/chip')
    cpus=[n for p,n in fdt.walk(root) if p.startswith('/cpus/cpu@') and p.count('/')==2]
    if len(cpus)!=18:raise ValueError('expected exactly eighteen static CPU nodes')
    seen=[];capacities=[]
    for n in cpus:
        if fdt.text(n.props.get('status',b'okay\0'))[0] not in ('ok','okay'):
            raise ValueError('CPU disabled in static candidate')
        if fdt.text(n.props['enable-method'])!=['spin-table']:
            raise ValueError('wrong CPU release method')
        if len(n.props['reg'])!=8 or len(n.props.get('cpu-release-addr',b''))!=8:
            raise ValueError('wrong CPU register/release width')
        seen.append(struct.unpack('>Q',n.props['reg'])[0])
        capacities.append(struct.unpack('>I',n.props['capacity-dmips-mhz'])[0])
    if seen!=EXPECTED or len(set(seen))!=18:
        raise ValueError('unexpected MPIDR order/topology')
    if capacities[:12]!=[794]*12 or capacities[12:]!=[1024]*6:
        raise ValueError('unexpected M/P capacity distinction')
    drom=sum('apple,thunderbolt-drom' in n.props for _,n in fdt.walk(root))
    publisher_drom=sum(len(n.props.get('apple,thunderbolt-drom',b''))>1 for _,n in fdt.walk(root))
    return {'scope':'OFFLINE_STATIC_DTB','status':'PASS','board':'apple,j716c',
        'chip':'apple,t6050','cpu_count':18,'mpidrs':[hex(x) for x in seen],
        'cluster_core_types':['M','M','P'],'cores_per_cluster':[6,6,6],
        'dt_capacity_values':capacities,'capacity_is_not_a_measurement':True,
        'enable_method':'spin-table','drom_properties':drom,'publisher_drom_properties':publisher_drom,
        'runtime_fields_pending':['cpu-release-addr','memory','framebuffer','aurora,ctxr-exec-window'],
        'native_qualified':False}

if __name__=='__main__':
    print(json.dumps(inspect(Path(sys.argv[1]).read_bytes()),indent=2))
