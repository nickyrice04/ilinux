#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Check exact 31K entry addressing and make incoming-state assumptions explicit.

An offline, original software oracle; no firmware, cache or Apple CPU emulator.
Only pinned public boot021 bytes and the already-published original recorders
are examined. No input code is executed and no target API is available.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, HERE.parent / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vector = load('_31l_vector_builder', 'smp31f-entry/builder.py')
cold = load('_31l_cold_builder', 'smp31k-entry/builder.py')
IMAGE_SHA = cold.audit.IMAGE_SHA
SYMBOL_SHA = cold.audit.SYMBOL_SHA
ALIASES = {'identity': 0, 'rwx': 0x80000000000,
           'rw': 0xa0000000000, 'rx': 0xc0000000000}
# Synthetic values only. Include carries at 4 GiB, 1 TiB and the 41-bit edge.
BASES = (0x800000000, 0xffffc000, 0x100000000, 0xfffffc0000,
         0x10000000000, 0x10000004000, 0x1fffff00000)
CHANNELS = {'vector': (0, 0xa00, 0x90a40),
            'cold': (0x800, 0xb00, 0x90a80)}


def need(value, reason):
    if not value:
        raise ValueError(reason)


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def branch_target(word, pc):
    need(word & 0xfc000000 == 0x14000000, 'hook_is_not_unconditional_b')
    return pc + 4 * signed(word & 0x3ffffff, 26)


def decode_prefix(body, code_offset, record_offset):
    """Independently decode the first five words, through the first DSB.

    The prefix must use ADRP X0; ADD X0,X0,#lo12; MOVZ X8,#1;
    STR X8,[X0]; DSB SY. Register/width/shift variants fail closed.
    """
    need(type(body) is bytes and len(body) >= 20 and len(body) % 4 == 0,
         'prefix_extent')
    words = struct.unpack_from('<5I', body)
    adrp, add, marker, store, barrier = words
    need(adrp & 0x9f00001f == 0x90000000, 'prefix_adrp_x0')
    need(add & 0xffc003ff == 0x91000000, 'prefix_add_x0_no_shift')
    need(marker == 0xd2800028, 'prefix_marker_one')
    need(store == 0xf9000008, 'prefix_str_x8_x0')
    need(barrier == 0xd5033f9f, 'prefix_dsb_sy')
    pages = signed(((adrp >> 5) & 0x7ffff) << 2 | ((adrp >> 29) & 3), 21)
    low = (add >> 10) & 4095
    need((code_offset & ~4095) + pages * 4096 + low == record_offset,
         'prefix_record_address')
    return {'code_offset': code_offset, 'record_offset': record_offset,
            'pages': pages, 'low': low, 'first_store_offset': code_offset + 12,
            'prefix_sha256': hashlib.sha256(body[:20]).hexdigest()}


def address_case(prefix, base, alias):
    """Arithmetic only: a VA result is not an inferred physical translation."""
    need(type(base) is int and 0 < base < (1 << 41) and base % 0x4000 == 0,
         'synthetic_base')
    need(type(alias) is int and alias in ALIASES.values(), 'synthetic_alias')
    need(base + 0xa0000 < 1 << 41, 'synthetic_base_extent')
    pc = (base + prefix['code_offset']) | alias
    address = (pc & ~4095) + prefix['pages'] * 4096 + prefix['low']
    expected = (base + prefix['record_offset']) | alias
    need(address == expected, 'relative_address_mismatch')
    return address


def translation_case(prefix, base, alias, mmu_on):
    """Contrast an explicitly supplied same-PA alias map with MMU-off identity.

    All enabled mappings in this synthetic case are supplied premises, never
    inferred from CPU0's tables or from an alias's conventional name.
    """
    need(type(mmu_on) is bool, 'synthetic_mmu')
    va = address_case(prefix, base, alias)
    expected = base + prefix['record_offset']
    physical = va - alias if mmu_on else va
    return {'mmu_on_assumed': mmu_on, 'same_physical_record': physical == expected,
            'alias_map_supplied_as_premise': mmu_on,
            'physical_translation_proven': False}


def original_vector_routes(image):
    """Inventory all sixteen slots; presence does not select any CPU1 route."""
    need(hashlib.sha256(image).hexdigest() == IMAGE_SHA, 'image_digest')
    result = []
    for slot in range(0, 0x800, 0x80):
        word, = struct.unpack_from('<I', image, slot)
        branch_at = slot if word & 0xfc000000 == 0x14000000 else slot + 4
        target = branch_target(struct.unpack_from('<I', image, branch_at)[0], branch_at)
        result.append({'slot': hex(slot), 'direct_target': hex(target),
                       '31k_vector_hook_on_first_word': slot == 0})
    return result


def scenario(*, selected=True, fetch=True, fresh=True, mapped=True,
             writable=True, visible=True, memory='device', clean=False,
             clean_supported=False, clean_completed=False, observer_reaches_poc=False):
    """Evaluate explicit synthetic premises, not architectural permission rules.

    'normal_private_dirty' is an injected noncoherent first-store hypothesis.
    Mixed Normal/Device attributes are not assumed architecturally compatible.
    The optional clean comparison also needs supported/completed maintenance and
    an observer which reaches its PoC; a clean instruction alone proves nothing.
    """
    bools = (selected, fetch, fresh, mapped, writable, visible, clean,
             clean_supported, clean_completed, observer_reaches_poc)
    need(all(type(value) is bool for value in bools), 'scenario_boolean')
    need(memory in ('device', 'normal_private_dirty'), 'scenario_memory')
    out = {'phase': 0, 'first_store_executed': False, 'clean_comparison': clean,
           'native_execution': 'NOT RUN', 'hardware_behavior_proven': False}
    for premise, reason in ((selected, 'different_entry_or_reset_not_released'),
                            (fetch, 'instruction_fetch_not_available'),
                            (fresh, 'instrumented_instructions_not_observed'),
                            (mapped, 'record_translation_not_available'),
                            (writable, 'record_store_not_permitted')):
        if not premise:
            return dict(out, reason=reason)
    out['first_store_executed'] = True
    if not visible:
        return dict(out, reason='injected_store_visibility_failure')
    if memory == 'normal_private_dirty':
        if not clean:
            return dict(out, reason='injected_dirty_store_not_published_by_dsb')
        if not (clean_supported and clean_completed and observer_reaches_poc):
            return dict(out, reason='clean_contract_not_established')
    return dict(out, phase=1, reason='first_marker_visible_under_all_premises')


def hypotheses():
    cases = {
        'another_entry_or_no_reset_release': dict(selected=False),
        'first_fetch_denied': dict(fetch=False),
        'old_instructions_visible': dict(fresh=False),
        'first_store_unmapped': dict(mapped=False),
        'first_store_readonly': dict(writable=False),
        'first_store_invisible': dict(visible=False),
        'normal_dirty_dsb_only': dict(memory='normal_private_dirty'),
        'normal_dirty_clean_without_contract': dict(memory='normal_private_dirty', clean=True),
        'normal_dirty_clean_with_full_assumptions': dict(memory='normal_private_dirty', clean=True,
            clean_supported=True, clean_completed=True, observer_reaches_poc=True),
        'device_same_physical_visible': {},
    }
    return {name: scenario(**kwargs) for name, kwargs in cases.items()}


def observation_constraint(report, outcomes):
    """Accept only the known 31K negative-prefix shape; never fill missing data."""
    need(type(report) is dict and report.get('experiment') == 'smp31k', 'report_experiment')
    control = report.get('cpu0_control', {})
    need(type(control) is dict and control.get('result') == 'CPU0_OBSERVER_CONTROL_PASS' and
         control.get('cpu1_record_visibility') == 'NOT_TESTED', 'report_control')
    for name in ('cold_observation', 'recorder_observation'):
        row = report.get(name, {})
        need(type(row) is dict and type(row.get('highest_phase_seen')) is int and row['highest_phase_seen'] == 0 and
             row.get('identity_status') == 'not_committed' and 'error' in row and
             row['error'] is None, 'report_negative_prefix')
        counters = ('samples_attempted', 'samples_completed', 'reads_attempted', 'reads_completed')
        need(all(type(row.get(key)) is int and 0 < row[key] <= 100000
                 for key in counters), 'report_observation_counters')
        width = 4 if name == 'cold_observation' else 5
        need(row['samples_attempted'] == row['samples_completed'] and
             row['reads_attempted'] == row['reads_completed'] == width * row['samples_completed'],
             'report_observation_counter_consistency')
    need(report.get('cpu1_arrival_verified') is False and
         report.get('park_verified') is False, 'report_execution_not_verified')
    canonical = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return {'report_canonical_json_sha256': hashlib.sha256(canonical).hexdigest(),
            'cpu0_control_pass_does_not_prove_cpu1_mapping': True,
            'compatible_injected_hypotheses': [name for name, row in outcomes.items()
                if row['phase'] == 0],
            'incompatible_only_if_every_synthetic_premise_holds': [name for name, row in outcomes.items()
                if row['phase'] != 0],
            'cause_identified': False, 'effective_entry': 'UNKNOWN',
            'no_raw_word_zero_claim': True, 'native_next_attempt_ready': False}


def check(image, symbols=None, report=None):
    verified = cold.audit.audit(image, symbols)
    prefixes, sweeps, translations, incompatible_aliases = {}, 0, 0, 0
    for name, builder in (('vector', vector), ('cold', cold)):
        hook, offset, record = CHANNELS[name]
        body, _ = builder.program()
        hook_word = builder.branch(hook, offset)
        need(branch_target(hook_word, hook) == offset, 'hook_branch_target')
        prefix = decode_prefix(body, offset, record)
        for base in BASES:
            for alias in ALIASES.values():
                address_case(prefix, base, alias)
                sweeps += 1
                for enabled in (False, True):
                    mapped = translation_case(prefix, base, alias, enabled)
                    need(mapped['same_physical_record'] == (enabled or alias == 0),
                         'translation_premise_mismatch')
                    translations += 1
                    incompatible_aliases += not mapped['same_physical_record']
        prefixes[name] = dict(prefix, hook_offset=hook,
            context_system_reads_before_first_store=0, stack_operations_before_first_store=0)
    outcomes = hypotheses()
    return {'schema': 1, 'result': 'OFFLINE_ENTRY_CONTRACT_PASS',
            'image_sha256': IMAGE_SHA, 'symbol_sha256': SYMBOL_SHA if symbols else None,
            'symbol_mode': verified['symbol_mode'], 'prefixes': prefixes,
            'address_cases_checked': sweeps, 'original_vector_slots': original_vector_routes(image),
            'translation_cases_checked': translations,
            'mmu_off_alias_cases_not_same_record': incompatible_aliases,
            'alias_limit': 'With MMU off, a nonidentity alias is a different physical address; no alias translation is assumed.',
            'scenarios': outcomes,
            '31k_constraint': observation_constraint(report, outcomes) if report is not None else None,
            'native_execution': 'NOT RUN', 'cpu1_effective_entry': 'UNKNOWN',
            'native_next_attempt_ready': False, 'hardware_emulator': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--symbols', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        for path in (args.image, args.symbols, args.report):
            need(path is None or path.is_file() and not path.is_symlink(), 'input_file')
        result = check(args.image.read_bytes(), args.symbols.read_bytes() if args.symbols else None,
                       json.loads(args.report.read_text()) if args.report else None)
    except (OSError, ValueError, UnicodeError) as exc:
        # Never echo input content or local filenames into a public artifact.
        reason = str(exc) if type(exc) is ValueError and str(exc).isidentifier() else type(exc).__name__
        result = {'result': 'OFFLINE_REFUSED', 'reason': reason,
                  'native_execution': 'NOT RUN', 'native_next_attempt_ready': False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'OFFLINE_ENTRY_CONTRACT_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
