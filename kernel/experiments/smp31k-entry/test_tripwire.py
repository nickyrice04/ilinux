#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original offline layout, encoder, fault-model and observation tests."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import unittest

HERE = Path(__file__).resolve().parent
def load(name):
    spec = importlib.util.spec_from_file_location('_31k_test_'+name, HERE/(name+'.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
builder, audit, telemetry, model, permissions = map(load,
    ('builder', 'audit', 'telemetry', 'model', 'permissions'))
IMAGE = SYMBOLS = None
BASE = 0x800000000


class ProgramTests(unittest.TestCase):
    def test_size_and_terminal_branch(self):
        body, labels = builder.program()
        self.assertEqual(len(body), 76)
        self.assertEqual(struct.unpack_from('<I', body, 72)[0], 0x14000000)
        self.assertEqual(labels['terminal_spin'], 0xb48)
    def test_hook_branch(self):
        self.assertEqual(builder.branch(0x800, 0xb00), 0x140000c0)
    def test_no_resume(self):
        self.assertIsNone(builder.RESUME)
        self.assertFalse(model.run()['bss_reached'])
    def test_first_store_before_mrs(self):
        result = model.run(halt_before=5)
        self.assertEqual(result['published_phases'], [1])
        self.assertEqual(result['system_reads'], [])
    def test_first_store_fault_is_zero(self):
        result = model.run(halt_before=3)
        self.assertEqual(result['memory'][builder.RECORD], 0)
        self.assertEqual(result['system_reads'], [])
    def test_invisible_stores_remain_zero(self):
        result = model.run(invisible_stores=True)
        self.assertTrue(result['terminal_spin_selected'])
        self.assertFalse(any(result['memory'].values()))
        self.assertFalse(result['hardware_visibility_proven'])
    def test_fault_every_instruction(self):
        for fault in range(20):
            with self.subTest(fault=fault):
                result = model.run(halt_before=fault)
                self.assertEqual(result['lr'], result['original_lr'])
                self.assertEqual(result['sp'], 0x70000000)
                self.assertFalse(result['bss_reached'])
                self.assertTrue(all(builder.RECORD <= address < builder.RECORD_END
                                    for address, _ in result['stores']))
    def test_three_phases(self):
        self.assertEqual(model.run()['published_phases'], [1, 2, 3])
    def test_phase3_before_loop(self):
        result = model.run(halt_before=17)
        self.assertEqual(result['memory'][builder.RECORD], 3)
        self.assertFalse(result['terminal_spin_selected'])
    def test_all_identities_spin_without_bss(self):
        for identity in (0x40000, 0x40001, 0x40005, 0x40100, 0x10200, 0xffffff):
            with self.subTest(identity=identity):
                result = model.run(mpidr=identity)
                self.assertTrue(result['terminal_spin_selected'])
                self.assertFalse(result['bss_reached'])
    def test_identity_low24_only(self):
        self.assertEqual(model.run(mpidr=0x1234567800040001)['memory'][builder.RECORD+16],
                         0x40001)
    def test_invalid_el_still_spins(self):
        self.assertTrue(model.run(current_el=0)['terminal_spin_selected'])
    def test_sp_lr_and_other_registers(self):
        result = model.run()
        self.assertEqual(result['lr'], result['original_lr'])
        self.assertEqual(len(result['untouched_registers']), 28)
    def test_bootargs_not_recorded(self):
        magic = 0x1234567890
        result = model.run(incoming_x0=magic)
        self.assertNotIn(magic, result['memory'].values())
        self.assertEqual(result['x0'], builder.RECORD)
    def test_mutant_program_refused(self):
        body, _ = builder.program()
        for offset in range(0, len(body), 4):
            mutant = bytearray(body)
            mutant[offset] ^= 1
            with self.assertRaisesRegex(ValueError, 'exact_original'):
                model.run(body=bytes(mutant))
    def test_no_forbidden_instruction_classes(self):
        words = struct.unpack('<19I', builder.program()[0])
        self.assertFalse(any(word & 0xfff00000 == 0xd5100000 for word in words))
        self.assertFalse(any(word & 0xfc000000 == 0x94000000 for word in words))
        self.assertNotIn(0xd503205f, words)  # WFE deliberately excluded.
        self.assertNotIn(0xd65f03c0, words)


class TelemetryTests(unittest.TestCase):
    def observe(self, words):
        values = iter(words)
        return telemetry.sample(lambda _: next(values), BASE)
    def test_zero_ignores_uncommitted_registers(self):
        row = self.observe((0, 0xffffffffffffffff, 0xffffffffffffffff, 0))
        self.assertEqual(row['identity_status'], 'not_committed')
        self.assertFalse(row['any_record_seen'])
    def test_all_committed_phases_stop(self):
        for phase in (1, 2, 3):
            row = self.observe((phase, 0x40001, 8, phase))
            self.assertTrue(row['stop_required'])
            self.assertFalse(row['complete'])
            self.assertFalse(row['park_verified'])
    def test_phase1_ignores_identity(self):
        self.assertEqual(self.observe((1, 123, 0, 1))['identity_status'], 'not_committed')
    def test_known_cpu0_categorized(self):
        row = self.observe((2, 0x40000, 0, 2))
        self.assertEqual(row['observed_cpu_id'], 0)
        self.assertEqual(row['error'], 'unexpected_cold_identity')
    def test_super_class_categorized(self):
        row = self.observe((2, 0x10200, 0, 2))
        self.assertEqual(row['observed_macos_class'], 'Super')
        self.assertTrue(row['stop_required'])
    def test_unknown_identity_categorized(self):
        row = self.observe((2, 0xffffff, 0, 2))
        self.assertEqual(row['identity_status'], 'unknown')
        self.assertNotIn('mpidr', row)
    def test_invalid_el(self):
        row = self.observe((3, 0x40001, 0, 3))
        self.assertEqual(row['error'], 'committed_cold_el_invalid')
        self.assertFalse(row['record_complete'])
    def test_valid_el_all_levels(self):
        for el in (4, 8, 12):
            row = self.observe((3, 0x40001, el, 3))
            self.assertEqual(row['exception_level'], el//4)
            self.assertTrue(row['record_complete'])
            self.assertFalse(row['complete'])
    def test_publication_during_read_stops_without_identity_claim(self):
        row = self.observe((0, 0x40001, 8, 3))
        self.assertTrue(row['stop_required'])
        self.assertEqual(row['identity_status'], 'not_committed')
        self.assertIsNone(row['exception_level'])
    def test_regression_refused(self):
        with self.assertRaisesRegex(telemetry.TelemetryError, 'regression'):
            self.observe((3, 0x40001, 8, 1))
    def test_unknown_phase_refused(self):
        with self.assertRaises(telemetry.TelemetryError) as caught:
            self.observe((4, 0, 0, 4))
        self.assertTrue(caught.exception.any_record_seen)
    def test_fixed_four_reads(self):
        addresses = []
        telemetry.sample(lambda address: addresses.append(address) or 0, BASE)
        self.assertEqual(addresses, [BASE+x for x in telemetry.SAMPLE_OFFSETS])
    def test_failure_each_read(self):
        for fail in range(4):
            calls = []
            def read(address):
                calls.append(address)
                if len(calls) == fail+1:
                    raise RuntimeError('private must not escape')
                return 1
            tracker = telemetry.Tracker()
            row = tracker.sample(read, BASE)
            self.assertEqual(row['reads_attempted'], fail+1)
            self.assertEqual(row['reads_completed'], fail)
            self.assertEqual(row['any_record_seen'], fail > 0)
            self.assertTrue(row['stop_required'])
            self.assertNotIn('private', json.dumps(row))
    def test_closed_after_positive_observation(self):
        tracker = telemetry.Tracker()
        data = iter((3, 0x40001, 8, 3))
        first = tracker.sample(lambda _: next(data), BASE)
        later = tracker.sample(lambda _: self.fail('must not read again'), BASE)
        self.assertEqual(first, later)
    def test_closed_after_wrong_identity(self):
        tracker = telemetry.Tracker()
        data = iter((2, 0x40000, 0, 2))
        tracker.sample(lambda _: next(data), BASE)
        self.assertTrue(tracker.sample(lambda _: self.fail('read'), BASE)['stop_required'])
    def test_unknown_phase_tracker_sticky_stop(self):
        tracker = telemetry.Tracker()
        row = tracker.sample(lambda _: 255, BASE)
        self.assertTrue(row['any_record_seen'])
        self.assertTrue(row['stop_required'])
        self.assertIsNone(row['highest_phase_seen'])
    def test_sample_budget(self):
        tracker = telemetry.Tracker(max_samples=1)
        tracker.sample(lambda _: 0, BASE)
        row = tracker.sample(lambda _: self.fail('read'), BASE)
        self.assertEqual(row['error'], 'cold_sample_budget_exhausted')
    def test_full_default_budget_and_no_extra_reads(self):
        tracker = telemetry.Tracker()
        for _ in range(telemetry.MAX_SAMPLES):
            row = tracker.sample(lambda _: 0, BASE)
            self.assertIsNone(row['error'])
        self.assertEqual(row['reads_completed'], 8192)
        row = tracker.sample(lambda _: self.fail('budgeted read'), BASE)
        self.assertEqual(row['error'], 'cold_sample_budget_exhausted')
    def test_interrupt_preserved_and_tracker_closed(self):
        tracker = telemetry.Tracker()
        def interrupted(_):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            tracker.sample(interrupted, BASE)
        row = tracker.sample(lambda _: self.fail('read after interrupt'), BASE)
        self.assertEqual(row['error'], 'cold_acquisition_interrupted')
        self.assertTrue(row['stop_required'])
    def test_invalid_configuration(self):
        for base in (0, -1, BASE+1, True, 1 << 64):
            with self.assertRaises(telemetry.TelemetryError):
                telemetry.sample(lambda _: self.fail('read'), base)
    def test_reentrant_reader_closes_tracker(self):
        tracker = telemetry.Tracker()
        def reader(_):
            tracker.sample(lambda _: self.fail('inner read'), BASE)
            return 0
        row = tracker.sample(reader, BASE)
        self.assertEqual(row['error'], 'reentrant_cold_sample')
        self.assertTrue(row['stop_required'])


class LayoutTests(unittest.TestCase):
    def fixture(self):
        return bytearray(0xa0000), dict(audit.LAYOUT, _text_size=0x1000,
                                      _rela_start=0x80000, _rela_end=0x80000)
    def test_synthetic_empty_ranges(self):
        image, named = self.fixture()
        self.assertTrue(audit.region_audit(image, named)['zero_padding'])
    def test_every_region_nonzero_refused(self):
        for start, _ in audit.REGIONS.values():
            image, named = self.fixture()
            image[start] = 1
            with self.assertRaisesRegex(ValueError, 'candidate_not_zero'):
                audit.region_audit(image, named)
    def test_allocated_symbols_refused(self):
        image, named = self.fixture()
        for start, _ in audit.REGIONS.values():
            with self.assertRaisesRegex(ValueError, 'candidate_symbol'):
                audit.region_audit(image, named, [(start, 'D', 'owned')])
    def test_relocation_destination_and_addend_refused(self):
        for start, _ in audit.REGIONS.values():
            for destination, addend in ((start, 0), (0, start)):
                image, named = self.fixture()
                named['_rela_end'] += 24
                struct.pack_into('<QQQ', image, named['_rela_start'], destination, 1027, addend)
                with self.assertRaisesRegex(ValueError, 'candidate_relocation'):
                    audit.region_audit(image, named)
    def test_direct_branch_refused(self):
        image, named = self.fixture()
        struct.pack_into('<I', image, 0x100, builder.branch(0x100, 0xb00))
        with self.assertRaisesRegex(ValueError, 'candidate_direct_reference'):
            audit.region_audit(image, named)
    def test_cold_hook_relocation_refused(self):
        image, named = self.fixture()
        named['_rela_end'] += 24
        struct.pack_into('<QQQ', image, named['_rela_start'], 0x800, 1027, 0)
        with self.assertRaisesRegex(ValueError, 'cold_hook_relocation'):
            audit.region_audit(image, named)
    def test_cold_entry_direct_reference_refused(self):
        image, named = self.fixture()
        struct.pack_into('<I', image, 0x100, builder.branch(0x100, 0x800))
        with self.assertRaisesRegex(ValueError, 'cold_entry_direct_reference'):
            audit.region_audit(image, named)
    def test_adjacent_adrp_add_refused(self):
        for start, _ in audit.REGIONS.values():
            image, named = self.fixture()
            struct.pack_into('<II', image, 0x100, builder.adrp(0x100, start),
                             0x91000000 | (start & 4095) << 10)
            with self.assertRaisesRegex(ValueError, 'candidate_direct_reference'):
                audit.region_audit(image, named)
    def test_unknown_image_refused(self):
        with self.assertRaisesRegex(ValueError, 'image_digest'):
            builder.build(bytes(0xa0000))
    def test_permission_exact_spans(self):
        probes = permissions.probe_plan(BASE)
        self.assertEqual(len(probes), 16)
        self.assertEqual(set(p['physical']-BASE for p in probes),
                         {0x800, 0xb00, 0xb48, 0x90a80, 0x90ab8})
        for probe in probes:
            self.assertTrue(probe['name'].startswith('cold_'))
            self.assertEqual(probe['attr'], 0 if 'record' in probe['name'] else 255)
    def test_full_actual_image_if_supplied(self):
        if IMAGE is None:
            self.skipTest('actual pinned image not supplied')
        plan, body, hook = builder.build(IMAGE, SYMBOLS)
        self.assertEqual(plan['entry_audit']['symbol_mode'],
                         'full_symbols' if SYMBOLS is not None else 'reviewed_layout_only')
        self.assertEqual(len(body), 76)
        self.assertEqual(hook, struct.pack('<I', 0x140000c0))
        self.assertFalse(plan['native_deployment_ready'])
    def test_actual_image_mutation_refused_if_supplied(self):
        if IMAGE is None:
            self.skipTest('actual pinned image not supplied')
        for offset in (0, 0x800, 0xb00, 0x90a80, 0x90b00, len(IMAGE)-1):
            image = bytearray(IMAGE)
            image[offset] ^= 1
            with self.assertRaisesRegex(ValueError, 'image_digest'):
                builder.build(bytes(image), SYMBOLS)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--symbols', type=Path)
    args, rest = parser.parse_known_args()
    IMAGE = args.image.read_bytes() if args.image else None
    SYMBOLS = args.symbols.read_bytes() if args.symbols else None
    unittest.main(argv=[__file__]+rest)
