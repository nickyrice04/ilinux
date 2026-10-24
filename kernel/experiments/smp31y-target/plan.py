#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline CPU2 binding plan for one same-cluster comparison; no target API.

The published layout is a hash-pinned result of the boot021 image/source audit.
Optional retained inputs independently recheck its image and source hashes.
No machine code, controller, connection, image patch or deployment is produced.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PINS = {
    'hardware/adt/adt-sanitized.json':
        '6f143434d2f05310067559f8fa3836ae564dd9934ebc5912660f2a9f5a8a73af',
    'native/boot/attempt31g/topology-observation.json':
        'b055f570f79c6b423fb917afcd73a2c9a87aded2cf6057f9dc708048eae2db42',
    'kernel/experiments/smp31/boot021-ram-layout.json':
        '1cca59ae45158bdd6fa27400bc0ab23b909d9fec705cdb8c8d699a15f3eda12d',
    'kernel/experiments/smp31/boot021-symbols.json':
        '43fe3d39f0cc8d984ecde7a941037f66136b87316da1675a40a7f9129b5b5646',
    'kernel/experiments/t6050-dt/gen_t6050_dt.py':
        '9f22c83ec119c5032b75a7ca97e38ec7ea2a19613e580c103952961fada849f4',
}
IMAGE_BYTES = 0x3c0000
TABLE_COUNT = 32


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_inputs(root=ROOT):
    """Read pinned public inputs; import only the repository's original decoder."""
    data = {}
    for name, digest in PINS.items():
        path = root / name
        need(not path.is_symlink(), 'input_symlink')
        raw = path.read_bytes()
        need(sha(raw) == digest, 'input_digest_mismatch')
        data[name] = raw
    decoder_path = root / 'kernel/experiments/t6050-dt/gen_t6050_dt.py'
    spec = importlib.util.spec_from_file_location('_31y_original_adt', decoder_path)
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    nodes = {}
    needed = {'/', '/arm-io', '/arm-io/pmgr'} | {f'/cpus/cpu{i}' for i in range(18)}
    def walk(node):
        path = node['path'].replace('/Root/device-tree', '') or '/'
        if node['path'].startswith('/Root/device-tree') and path in needed:
            need(path not in nodes, 'duplicate_adt_node')
            nodes[path] = node['values']
        for child in node.get('children', []):
            walk(child)
    walk(json.loads(data['hardware/adt/adt-sanitized.json']))
    need(set(nodes) == needed, 'missing_adt_node')
    devices, mode, _, u8ids = decoder.decode_pmgr(nodes, decoder.arm_io_ranges(nodes))
    need(mode == 'ps-groups' and not u8ids, 'pmgr_format')
    return (nodes, devices,
            json.loads(data['native/boot/attempt31g/topology-observation.json']),
            json.loads(data['kernel/experiments/smp31/boot021-ram-layout.json']),
            json.loads(data['kernel/experiments/smp31/boot021-symbols.json']))


def non_target_spans(base, stride, target):
    """Exclude primary row0 and target row2, including the otherwise missed row1."""
    need(type(target) is int and target == 2, 'cpu2_only')
    return [dict(offset=base + stride, bytes=stride),
            dict(offset=base + (target + 1) * stride,
                 bytes=(TABLE_COUNT - target - 1) * stride)]


def derive(nodes, devices, observation, layout, symbol_record, *, target=2):
    need(type(target) is int and target == 2, 'cpu2_only')
    need('J716cAP' in nodes['/']['compatible'], 'board_mismatch')
    cpus = []
    for i in range(18):
        cpu = nodes[f'/cpus/cpu{i}']
        cluster, local = divmod(i, 6)
        need(type(cpu['cpu-id']) is int and type(cpu['logical-cpu-id']) is int and
             cpu['cpu-id'] == cpu['logical-cpu-id'] == i, 'cpu_identity')
        rawreg = int(cpu['reg'][0]['addr'], 16)
        need(rawreg == (cluster << 8 | local) and
             cpu['cluster-type'] == (['M'] if i < 12 else ['P']) and
             cpu['state'] == (['running'] if i == 0 else ['waiting']), 'cpu_topology')
        words = [int(x, 16) for x in cpu['cpu-impl-reg']]
        need(len(words) == 4 and all(0 <= w < 1 << 32 for w in words), 'impl_cells')
        impl, size = words[0] | words[1] << 32, words[2] | words[3] << 32
        need(impl == 0x210050000 + cluster * 0x1000000 + local * 0x100000 and
             size == 0x9018, 'impl_binding')
        cpus.append(dict(cpu_id=i, cluster=cluster, local_core=local,
                         reg=rawreg, impl=impl, impl_size=size))
    need(observation['read_only'] is True and observation['edt_property_ver'] == 2,
         'ordinal_provenance')
    ordinals = observation['topology']
    starts = observation['startup_plan']
    need(len(ordinals) == len(starts) == 18, 'ordinal_count')
    need([r['cpu-id'] for r in ordinals] == list(range(18)) and
         [r['cpu_id'] for r in starts] == list(range(18)), 'ordinal_ids')
    for i, cpu in enumerate(cpus):
        row, start = ordinals[i], starts[i]
        need((row['reg'], row['cluster-id'], row['die-cluster-id'], row['cluster-core-id']) ==
             (cpu['reg'], cpu['cluster'], cpu['cluster'], cpu['local_core']), 'ordinal_binding')
        need((start['cluster'], start['local_core'], start['die_start_mask'],
              start['cluster_start_offset'], start['cluster_start_mask']) ==
             (cpu['cluster'], cpu['local_core'], 1 << i,
              8 + 4 * cpu['cluster'], 1 << cpu['local_core']), 'start_binding')

    need(layout['result'] == 'OFFLINE_LAYOUT_VERIFIED' and
         layout['image_sha256'] == symbol_record['image_sha256'] and
         layout['symbol_table_sha256'] == symbol_record['symbol_table_sha256'], 'layout_identity')
    symbols = {k: int(v, 16) for k, v in layout['image_relative_symbols'].items()}
    extra = {k: int(v, 16) for k, v in symbol_record['offsets'].items()}
    need(symbols['_vectors_start'] == extra['_vectors_start'] == 0 and
         extra['_start'] == 0x800, 'entry_layout')
    # Derive from full array boundaries and the independent symbol record,
    # never use CPU1's selected row as CPU2's row.
    reset_stride, remainder = divmod(symbols['spin_table'] - symbols['smp_reset_stacks'], TABLE_COUNT)
    spin_stride, remainder2 = divmod(symbols['target_cpu'] - symbols['spin_table'], TABLE_COUNT)
    info_stride, remainder3 = divmod(extra['cpu_start_base'] - extra['cpu_info'], TABLE_COUNT)
    need((reset_stride, spin_stride, info_stride, remainder, remainder2, remainder3) ==
         (16, 64, 16, 0, 0, 0), 'array_layout')
    stack_bytes = layout['cpu1_layout']['stack_bytes']
    need(type(stack_bytes) is int and stack_bytes == 0x10000, 'stack_stride')
    bottom = symbols['secondary_stacks'] + target * stack_bytes
    top = bottom + stack_bytes
    need(symbols['secondary_stacks'] + TABLE_COUNT * stack_bytes <= IMAGE_BYTES and
         top % 0x4000 == 0, 'stack_bounds')
    spin = symbols['spin_table'] + target * spin_stride
    reset = symbols['smp_reset_stacks'] + target * reset_stride
    need(symbols['_smp_shared_start'] <= reset < reset + reset_stride <=
         symbols['spin_table'] <= spin < spin + spin_stride <= symbols['target_cpu'] and
         symbols['_reset_stack'] + 8 <= symbols['_smp_shared_end'], 'shared_bounds')
    # Aff2 is not present in ADT reg. Reuse only the audited same-class/M0
    # expectation; any actual different/partial identity must stop and be kept.
    prior_identity = int(layout['cpu1_layout']['expected_mpidr'], 16)
    need(prior_identity == 0x40001 and cpus[target]['cluster'] == cpus[0]['cluster'] == 0,
         'same_cluster_identity')
    expected_identity = (prior_identity & ~0xffff) | cpus[target]['reg']
    powers = []
    for i in (0, target):
        matches = [d for d in devices if d['name'] == f'MCPU0_{i}']
        need(len(matches) == 1, 'power_domain_count')
        d = matches[0]
        need(d['id'] == i + 1 and d['flags'] == 0 and d['parents'] == [] and
             d['group'] == d['reg_index'] == 0 and d['block'][0] == 0x280600000 and
             d['ps_offset'] == 8 * i and d['ps_offset'] + 4 <= d['block'][1], 'power_binding')
        powers.append(dict(cpu_id=i, domain=d['name'], address=d['block'][0] + d['ps_offset'],
                           width_bits=32, execution_acknowledgement=False))
    # Preserve the previously consumed T6050 start-base contract. ADT supplies
    # the PMGR block and ordinals, not the meaning of this hardware operation.
    start_base = powers[0]['address'] + 0x88000
    start = starts[target]
    return dict(schema=1, result='OFFLINE_CPU2_BINDINGS_PASS', target_cpu=target,
        same_active_cluster_control=True, expected_mpidr_low24=expected_identity,
        expected_identity_is_runtime_observation=False,
        input_sha256=dict(PINS), image_sha256=layout['image_sha256'],
        symbol_table_sha256=layout['symbol_table_sha256'],
        target_ram=dict(spin_record=spin, spin_flag=spin + 8, reset_record=reset,
            reset_stack_field=reset + 8, cpu_info_record=extra['cpu_info'] + target * info_stride,
            target_cpu_field=symbols['target_cpu'], target_cpu_value=target,
            reset_stack_pointer_field=symbols['_reset_stack'],
            dedicated_stack_bottom=bottom, dedicated_stack_top=top, stack_bytes=stack_bytes,
            wfe_mode_field=symbols['wfe_mode'], wfe_mode_value=True),
        non_target_spin_zero_spans=non_target_spans(symbols['spin_table'], spin_stride, target),
        non_target_reset_fresh_spans=non_target_spans(symbols['smp_reset_stacks'], reset_stride, target),
        reset_mirror=dict(cpu_ids=[0, target], addresses=[cpus[i]['impl'] for i in (0, target)],
            read_width_bits=64, fresh_cpu2_observation_required=True,
            destination_writes=0, mirror_is_effective_pc=False),
        opaque_state=dict(cpu_ids=[0, target], addresses=[cpus[i]['impl'] + 0x100 for i in (0, target)],
            read_width_bits=32, cpu2_access_not_yet_observed=True, semantics='UNKNOWN'),
        power_observation=powers,
        start_pair=dict(addresses=[start_base + 4, start_base + start['cluster_start_offset']],
            values=[start['die_start_mask'], start['cluster_start_mask']], width_bits=32,
            max_dispatches=1, hardware_timing_measured=False, original_leaf_rebuild_required=True),
        entry_observation=dict(vector_hook_offset=0, cold_hook_offset=0x800,
            normal_prefix_offsets=[0xc00, 0xd00], normal_record_helper_offsets=[0x1000, 0x1080],
            normal_identity_offset=8, device_record_offsets=[0x90a40, 0x90a80],
            device_identity_offset=16, first_normal_store_precedes_identity=True,
            any_nonzero_or_partial_record_stops=True, wrong_identity_is_not_a_timeout=True),
        limits=dict(arrival_seconds=3, controller_seconds=60, supervisor_seconds=65,
            start_pairs=1, additional_core_starts=0, secondary_callbacks=0, retries=0,
            vector_restoration_after_start_intent=False, allocations_freed_after_start_intent=False),
        native_execution='NOT RUN', hardware_operations=0, controller_present=False,
        deployment_ready=False, required_live_preflight='NOT SATISFIED')


def verify_retained(layout, image, source, proxy_source):
    """Hash data only. No downloaded module or instruction is executed."""
    raw = image.read_bytes()
    need(len(raw) == IMAGE_BYTES and sha(raw) == layout['image_sha256'], 'retained_image_mismatch')
    checked = {}
    for name, digest in layout['source_sha256'].items():
        path = proxy_source if name == 'proxy.c' else source / name
        need(sha(path.read_bytes()) == digest, 'retained_source_mismatch')
        checked[name] = digest
    return dict(image_verified=True, source_sha256=checked,
                symbol_bytes_rechecked=False, third_party_code_executed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--source', type=Path, help='Retained source directory; data only')
    parser.add_argument('--proxy-source', type=Path, help='Exact separately retained proxy.c')
    args = parser.parse_args()
    try:
        inputs = load_inputs()
        result = derive(*inputs)
        given = (args.image, args.source, args.proxy_source)
        need(all(given) or not any(given), 'retained_inputs_incomplete')
        result['retained_bytes'] = (verify_retained(inputs[3], *given) if all(given) else
                                    dict(rechecked=False, basis='pinned_published_layout_audit'))
        print(json.dumps(result, indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        print(json.dumps(dict(result='OFFLINE_REFUSED', hardware_operations=0,
                              native_execution='NOT RUN', deployment_ready=False)))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
