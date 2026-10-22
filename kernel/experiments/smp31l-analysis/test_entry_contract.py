#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact prefix mutants, incoming-state counterexamples and pinned evidence."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_entry_contract31l', HERE / 'entry_contract.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
IMAGE = SYMBOLS = REPORT = IMAGE_PATH = None


class ContractTests(unittest.TestCase):
    def test_two_prefixes_are_position_independent_over_high_addresses(self):
        for name, builder in (('vector', c.vector), ('cold', c.cold)):
            _, offset, record = c.CHANNELS[name]
            prefix = c.decode_prefix(builder.program()[0], offset, record)
            for base in c.BASES:
                for alias in c.ALIASES.values():
                    with self.subTest(name=name, base=base, alias=alias):
                        self.assertEqual(c.address_case(prefix, base, alias),
                                         (base + record) | alias)

    def test_high_base_is_not_truncated_to_32_bits(self):
        body, _ = c.cold.program()
        p = c.decode_prefix(body, 0xb00, 0x90a80)
        self.assertGreater(c.address_case(p, 0x10000000000, 0), 1 << 32)

    def test_mmu_off_alias_is_not_a_same_pa_shortcut(self):
        p = c.decode_prefix(c.cold.program()[0], 0xb00, 0x90a80)
        for alias in c.ALIASES.values():
            with self.subTest(alias=alias):
                self.assertEqual(c.translation_case(p, 0x10000000000, alias, False)
                                 ['same_physical_record'], alias == 0)
                self.assertTrue(c.translation_case(p, 0x10000000000, alias, True)
                                ['same_physical_record'])

    def test_alias_name_does_not_establish_permissions(self):
        for alias in c.ALIASES:
            with self.subTest(alias=alias):
                self.assertEqual(c.scenario(fetch=False)['phase'], 0)
                self.assertEqual(c.scenario(writable=False)['phase'], 0)

    def test_prefix_mutants_reject_wrong_register_width_shift_and_destination(self):
        body, _ = c.cold.program()
        words = list(struct.unpack_from('<5I', body))
        mutants = ((0, words[0] ^ 1), (0, words[0] ^ (1 << 5)),
                   (1, words[1] ^ 1), (1, words[1] | (1 << 22)),
                   (1, words[1] ^ (1 << 10)), (2, 0xd2800048),
                   (2, 0x52800028), (3, 0xb9000008), (3, 0xf9000408),
                   (3, 0xf9000009), (4, 0xd503201f))
        for index, replacement in mutants:
            changed = bytearray(body)
            struct.pack_into('<I', changed, index * 4, replacement)
            with self.subTest(index=index, replacement=replacement):
                with self.assertRaises(ValueError):
                    c.decode_prefix(bytes(changed), 0xb00, 0x90a80)

    def test_moved_prefix_requires_reencoding_adrp(self):
        with self.assertRaisesRegex(ValueError, 'prefix_record_address'):
            c.decode_prefix(c.cold.program()[0], 0x1b00, 0x90a80)

    def test_branch_displacement_sign_and_link_mutant(self):
        self.assertEqual(c.branch_target(0x17fffffe, 0x1000), 0xff8)
        with self.assertRaisesRegex(ValueError, 'hook_is_not_unconditional_b'):
            c.branch_target(0x94000000, 0)

    def test_bad_base_and_alias_inputs_rejected(self):
        p = c.decode_prefix(c.cold.program()[0], 0xb00, 0x90a80)
        for base in (True, 0, -1, 0x10000000100, 1 << 41, (1 << 41) - 0x4000):
            with self.subTest(base=base), self.assertRaises(ValueError):
                c.address_case(p, base, 0)
        with self.assertRaises(ValueError):
            c.address_case(p, 0x10000000000, 0x1000)

    def test_negative_phase_does_not_identify_execution_failure(self):
        missing = c.scenario(selected=False)
        dirty = c.scenario(memory='normal_private_dirty')
        self.assertEqual(missing['phase'], dirty['phase'])
        self.assertFalse(missing['first_store_executed'])
        self.assertTrue(dirty['first_store_executed'])

    def test_dsb_is_not_modeled_as_dirty_cache_writeback(self):
        self.assertEqual(c.scenario(memory='normal_private_dirty')['phase'], 0)
        self.assertEqual(c.scenario(memory='device')['phase'], 1)

    def test_clean_requires_all_independent_premises(self):
        complete = dict(memory='normal_private_dirty', clean=True,
                        clean_supported=True, clean_completed=True, observer_reaches_poc=True)
        self.assertEqual(c.scenario(**complete)['phase'], 1)
        for name in ('clean_supported', 'clean_completed', 'observer_reaches_poc'):
            changed = dict(complete, **{name: False})
            with self.subTest(name=name):
                self.assertEqual(c.scenario(**changed)['phase'], 0)
        self.assertEqual(c.scenario(**dict(complete, visible=False))['phase'], 0)

    def test_clean_cannot_repair_missing_fetch_or_store(self):
        for premise in ('selected', 'fetch', 'fresh', 'mapped', 'writable'):
            with self.subTest(premise=premise):
                state = c.scenario(memory='normal_private_dirty', clean=True,
                    clean_supported=True, clean_completed=True, observer_reaches_poc=True,
                    **{premise: False})
                self.assertEqual(state['phase'], 0)
                self.assertFalse(state['first_store_executed'])

    def test_unknown_scenario_values_rejected(self):
        for kwargs in ({'fetch': 1}, {'memory': 'unknown'}, {'mmu': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, TypeError)):
                c.scenario(**kwargs)

    def test_synthetic_outcomes_never_claim_hardware(self):
        for state in c.hypotheses().values():
            self.assertFalse(state['hardware_behavior_proven'])
            self.assertEqual(state['native_execution'], 'NOT RUN')


class PinnedTests(unittest.TestCase):
    def setUp(self):
        if IMAGE is None:
            self.skipTest('pass --image to run exact-artifact tests')

    def test_full_artifact_and_report(self):
        result = c.check(IMAGE, SYMBOLS, REPORT)
        self.assertEqual(result['address_cases_checked'], 56)
        self.assertEqual(result['translation_cases_checked'], 112)
        self.assertEqual(result['mmu_off_alias_cases_not_same_record'], 42)
        self.assertFalse(result['native_next_attempt_ready'])
        self.assertFalse(result['hardware_emulator'])

    def test_vector_slot_zero_is_not_the_entire_exception_table(self):
        slots = c.original_vector_routes(IMAGE)
        self.assertEqual(len(slots), 16)
        self.assertEqual([s['slot'] for s in slots if s['31k_vector_hook_on_first_word']], ['0x0'])
        self.assertEqual(slots[0]['direct_target'], '0x8fc')
        self.assertEqual(slots[4]['direct_target'], '0x10000')

    def test_image_and_symbol_corruption_rejected(self):
        changed = bytearray(IMAGE)
        changed[0x1000] ^= 1
        with self.assertRaises(ValueError):
            c.check(bytes(changed), SYMBOLS)
        if SYMBOLS is not None:
            with self.assertRaises(ValueError):
                c.check(IMAGE, SYMBOLS + b'\n')

    def test_report_missing_negative_prefix_is_not_assumed_zero(self):
        if REPORT is None:
            self.skipTest('pass --report to check the actual evidence shape')
        for channel in ('cold_observation', 'recorder_observation'):
            changed = copy.deepcopy(REPORT)
            changed[channel].pop('highest_phase_seen')
            with self.subTest(channel=channel), self.assertRaises(ValueError):
                c.observation_constraint(changed, c.hypotheses())

    def test_report_bool_phase_or_missing_error_is_rejected(self):
        if REPORT is None:
            self.skipTest('pass --report to check the actual evidence shape')
        for change in ('bool', 'missing_error'):
            changed = copy.deepcopy(REPORT)
            if change == 'bool':
                changed['cold_observation']['highest_phase_seen'] = False
            else:
                changed['cold_observation'].pop('error')
            with self.subTest(change=change), self.assertRaises(ValueError):
                c.observation_constraint(changed, c.hypotheses())

    def test_actual_cpu0_positive_leaves_multiple_causes_possible(self):
        if REPORT is None:
            self.skipTest('pass --report to check the actual evidence shape')
        result = c.observation_constraint(REPORT, c.hypotheses())
        self.assertFalse(result['cause_identified'])
        self.assertIn('normal_dirty_dsb_only', result['compatible_injected_hypotheses'])
        self.assertIn('another_entry_or_no_reset_release', result['compatible_injected_hypotheses'])

    def test_nonobject_report_subsections_fail_closed(self):
        if REPORT is None:
            self.skipTest('pass --report to check the actual evidence shape')
        for field in ('cpu0_control', 'cold_observation', 'recorder_observation'):
            for invalid in (None, [], False, 0, 'not an object'):
                changed = copy.deepcopy(REPORT)
                changed[field] = invalid
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    c.observation_constraint(changed, c.hypotheses())

    def test_unacquired_missing_or_inconsistent_counts_are_rejected(self):
        if REPORT is None:
            self.skipTest('pass --report to check the actual evidence shape')
        for channel in ('cold_observation', 'recorder_observation'):
            for value in (None, 0, False, -1, 1.5, 100001):
                changed = copy.deepcopy(REPORT)
                changed[channel]['samples_completed'] = value
                with self.subTest(channel=channel, value=value), self.assertRaises(ValueError):
                    c.observation_constraint(changed, c.hypotheses())
            changed = copy.deepcopy(REPORT)
            changed[channel]['reads_completed'] -= 1
            with self.assertRaisesRegex(ValueError, 'report_observation_counter_consistency'):
                c.observation_constraint(changed, c.hypotheses())

    def test_cli_bad_subsections_emit_only_sanitized_refusal(self):
        if REPORT is None:
            self.skipTest('pass --report to check the actual evidence shape')
        with tempfile.TemporaryDirectory(prefix='entry-contract31l-') as directory:
            report_path = Path(directory) / 'malformed.json'
            for field, value in (('cpu0_control', None), ('cold_observation', []),
                                 ('recorder_observation', 'invalid')):
                changed = copy.deepcopy(REPORT)
                changed[field] = value
                report_path.write_text(json.dumps(changed))
                run = subprocess.run([sys.executable, '-I', str(HERE / 'entry_contract.py'),
                    '--image', str(IMAGE_PATH), '--report', str(report_path)],
                    text=True, capture_output=True, timeout=10)
                with self.subTest(field=field):
                    self.assertEqual(run.returncode, 1)
                    self.assertEqual(run.stderr, '')
                    output = json.loads(run.stdout)
                    self.assertEqual(output['result'], 'OFFLINE_REFUSED')
                    self.assertFalse(output['native_next_attempt_ready'])
                    self.assertNotIn(directory, run.stdout)

    def test_report_provenance_is_order_independent_and_content_sensitive(self):
        if REPORT is None:
            self.skipTest('pass --report to check the actual evidence shape')
        report = dict(reversed(list(REPORT.items())))
        first = c.observation_constraint(REPORT, c.hypotheses())['report_canonical_json_sha256']
        second = c.observation_constraint(report, c.hypotheses())['report_canonical_json_sha256']
        self.assertEqual(first, second)
        report['reason'] = 'synthetic_different_reason'
        self.assertNotEqual(first, c.observation_constraint(report, c.hypotheses())
                            ['report_canonical_json_sha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--symbols', type=Path)
    parser.add_argument('--report', type=Path)
    args, rest = parser.parse_known_args()
    IMAGE_PATH = args.image
    IMAGE = args.image.read_bytes() if args.image else None
    SYMBOLS = args.symbols.read_bytes() if args.symbols else None
    REPORT = json.loads(args.report.read_text()) if args.report else None
    unittest.main(argv=[__file__] + rest)
