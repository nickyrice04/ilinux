#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original pure topology-based startup planner. No hardware operations.

Only nonunique ordinals are accepted. die-cluster-id is a small topology index;
unique die-id is never accepted or read by this module.
"""
import struct

KEYS = ('cpu-id', 'reg', 'cluster-id', 'die-cluster-id', 'cluster-core-id')


def need(ok, label):
    if not ok:
        raise ValueError(label)


def plan(cpus, acc_cores, version):
    need(type(version) is int and version == 2, 'topology_version')
    need(type(acc_cores) is bytes and len(acc_cores) == 18 * 8, 'acc_cores_length')
    need(type(cpus) in (list, tuple) and len(cpus) == 18, 'topology_count')
    by_id = {}
    for cpu in cpus:
        need(type(cpu) is dict and set(cpu) == set(KEYS), 'topology_fields')
        need(all(type(v) is int and 0 <= v < 1024 for v in cpu.values()), 'topology_ordinals')
        i = cpu['cpu-id']
        need(i not in by_id and i < 18, 'topology_id')
        cluster, core = divmod(i, 6)
        need((cpu['reg'], cpu['cluster-id'], cpu['die-cluster-id'], cpu['cluster-core-id']) ==
             ((cluster << 8) | core, cluster, cluster, core), 'machine_topology_mismatch')
        by_id[i] = cpu
    need(set(by_id) == set(range(18)), 'topology_ids')
    entries = [acc_cores[i:i+8] for i in range(0, len(acc_cores), 8)]
    rows, bits = [], set()
    for i in range(18):
        cpu = by_id[i]
        matches = [r for r in entries if (r[6], r[7]) ==
                   (cpu['cluster-core-id'], cpu['cluster-id'])]
        need(len(matches) == 1, 'acc_core_mapping')
        entry = matches[0]
        # This board's observed domain IDs are ordinal+1 and masks 0..17.
        # Reject firmware/table changes for review; no silent fallback.
        domain, = struct.unpack_from('<I', entry)
        bit = entry[5]
        need(domain == i + 1 and entry[4] == 0 and bit == i and bit not in bits,
             'acc_core_binding')
        bits.add(bit)
        legacy_bit = 4 * cpu['cluster-id'] + cpu['cluster-core-id']
        rows.append(dict(cpu_id=i, adt_type='M' if i < 12 else 'P',
                         macos_class='Performance' if i < 12 else 'Super',
                         cluster=cpu['cluster-id'], local_core=cpu['cluster-core-id'],
                         die_start_mask=1 << bit,
                         cluster_start_offset=8 + 4 * cpu['die-cluster-id'],
                         cluster_start_mask=1 << cpu['cluster-core-id'],
                         legacy_die_mask_matches=legacy_bit == bit))
    return rows
