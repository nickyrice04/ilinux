#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pure candidate plan for CPU0/CPU1 PMGR PS observations; no transport.

This module does not authorize or perform MMIO, even when input validation
passes. Source semantics and target accessibility are separate evidence.
"""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[3]
PHASES = ('before_start', 'after_first_start', 'after_second_start', 'final')
EXPECTED = ((0, 'MCPU0_0', 1, 0x280600000),
            (1, 'MCPU0_1', 2, 0x280600008))


def require(value, reason):
    if not value:
        raise ValueError(reason)


def allowlist(nodes):
    """Validate ADT-derived addresses with the existing original decoder.

    Only two CPU-domain PS registers are proposed. CPU_START, cluster-power,
    CPU implementation/debug registers and all other clusters are excluded.
    """
    spec = importlib.util.spec_from_file_location('_31g_original_dt',
        ROOT / 'kernel/experiments/t6050-dt/gen_t6050_dt.py')
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    devices, mode, groups, u8ids = decoder.decode_pmgr(nodes, decoder.arm_io_ranges(nodes))
    require(mode == 'ps-groups' and not u8ids, 'unexpected_pmgr_table_format')
    rows = []
    for cpu, name, dev_id, address in EXPECTED:
        matches = [d for d in devices if d['name'] == name]
        require(len(matches) == 1, 'cpu_domain_missing_or_duplicate')
        d = matches[0]
        require(d['id'] == dev_id and d['flags'] == 0 and d['parents'] == [] and
                d['group'] == 0 and d['reg_index'] == 0 and
                d['block'][0] == 0x280600000 and d['ps_offset'] == 8 * cpu and
                d['block'][0] + d['ps_offset'] == address and
                d['ps_offset'] + 4 <= d['block'][1], 'cpu_ps_binding_mismatch')
        rows.append(dict(cpu_id=cpu, domain=name, address=address, width_bits=32,
                         adt_cluster=0, adt_core_type='M', macos_class='Performance'))
    return tuple(rows)


def fields(value):
    """Decode known PMGR PS fields without retaining reserved/unknown bits."""
    require(type(value) is int and 0 <= value < 1 << 32, 'invalid_ps_word')
    return dict(desired=value & 15, actual=(value >> 4) & 15,
                parent_missing=bool(value & (1 << 11)),
                device_disabled=bool(value & (1 << 10)),
                auto_enabled=bool(value & (1 << 28)))


def compare(samples):
    """Summarize bounded sequential observations, never claim CPU execution.

    Accept only a prefix of the fixed phases. No inference uses the sticky
    clock/power-gate history bits, and no value is interpreted as reset release.
    """
    require(type(samples) in (list, tuple) and 0 < len(samples) <= 4,
            'sample_bound')
    rows = []
    for index, sample in enumerate(samples):
        require(type(sample) is dict and set(sample) == {'phase', 'cpu0', 'cpu1'} and
                sample['phase'] == PHASES[index], 'sample_order_or_shape')
        rows.append(dict(phase=sample['phase'], cpu0=fields(sample['cpu0']),
                         cpu1=fields(sample['cpu1'])))
    before, last = rows[0], rows[-1]
    return dict(read_only_candidate=True, observations=len(rows), mmio_reads_performed=0,
                phase=last['phase'], fields=rows,
                target_actual_changed=before['cpu1']['actual'] != last['cpu1']['actual'],
                target_desired_changed=before['cpu1']['desired'] != last['cpu1']['desired'],
                target_actual_equals_legacy_active=last['cpu1']['actual'] == 15,
                primary_actual_equals_legacy_active=last['cpu0']['actual'] == 15,
                entry_execution='NOT_ESTABLISHED', reset_release='NOT_ESTABLISHED',
                effective_reset_destination='NOT_ESTABLISHED',
                native_smp='NOT_ESTABLISHED', additional_write_authorized=False)
