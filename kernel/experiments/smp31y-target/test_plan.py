# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline tests of target isolation and source/topology drift refusals."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('cpu2_plan', Path(__file__).with_name('plan.py'))
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)


class TargetPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = plan.load_inputs()

    def test_actual_bindings(self):
        result = plan.derive(*self.inputs)
        ram = result['target_ram']
        self.assertEqual((ram['spin_record'], ram['reset_record'], ram['cpu_info_record']),
                         (0x90290, 0x90030, 0x117208))
        self.assertEqual((ram['dedicated_stack_bottom'], ram['dedicated_stack_top']),
                         (0x178000, 0x188000))
        self.assertEqual(result['expected_mpidr_low24'], 0x40002)
        self.assertEqual(result['start_pair']['addresses'], [0x280688004, 0x280688008])
        self.assertEqual(result['start_pair']['values'], [4, 4])
        self.assertEqual(result['reset_mirror']['addresses'], [0x210050000, 0x210250000])
        self.assertEqual(result['power_observation'][1]['address'], 0x280600010)
        self.assertFalse(result['deployment_ready'])
        self.assertFalse(result['controller_present'])

    def test_non_target_spans_cover_cpu1_but_never_cpu2(self):
        result = plan.derive(*self.inputs)
        for name, base, stride in [('non_target_spin_zero_spans', 0x90210, 64),
                                   ('non_target_reset_fresh_spans', 0x90010, 16)]:
            covered = set()
            for span in result[name]:
                covered.update(range((span['offset'] - base) // stride,
                                     (span['offset'] + span['bytes'] - base) // stride))
            self.assertEqual(covered, set(range(32)) - {0, 2})

    def test_only_cpu2(self):
        for target in (0, 1, 3, 6, 12, 17, 32, -1, True, 2.0, '2'):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'cpu2_only'):
                plan.derive(*self.inputs, target=target)

    def test_cross_cluster_or_wrong_core_rejected(self):
        for field, value in [('reg', [{'addr':'0x100','size':'0x0'}]),
                             ('cluster-type', ['P']), ('state', ['running'])]:
            inputs = deepcopy(self.inputs)
            inputs[0]['/cpus/cpu2'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                plan.derive(*inputs)

    def test_ordinal_mask_drift_rejected(self):
        for field, value in [('die_start_mask', 2), ('cluster_start_mask', 2),
                             ('cluster_start_offset', 12)]:
            inputs = deepcopy(self.inputs)
            inputs[2]['startup_plan'][2][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'start_binding'):
                plan.derive(*inputs)

    def test_duplicate_ordinal_rejected(self):
        inputs = deepcopy(self.inputs)
        inputs[2]['topology'][2] = deepcopy(inputs[2]['topology'][1])
        with self.assertRaisesRegex(ValueError, 'ordinal_ids'):
            plan.derive(*inputs)

    def test_array_and_stack_drift_rejected(self):
        inputs = deepcopy(self.inputs)
        inputs[3]['image_relative_symbols']['spin_table'] = '0x90220'
        with self.assertRaisesRegex(ValueError, 'array_layout'):
            plan.derive(*inputs)
        inputs = deepcopy(self.inputs)
        inputs[3]['cpu1_layout']['stack_bytes'] = 0x20000
        with self.assertRaisesRegex(ValueError, 'stack_stride'):
            plan.derive(*inputs)

    def test_pmgr_alias_or_span_rejected(self):
        for field, value in [('ps_offset', 8), ('parents', [1]), ('flags', 1)]:
            inputs = deepcopy(self.inputs)
            next(d for d in inputs[1] if d['name'] == 'MCPU0_2')[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'power_binding'):
                plan.derive(*inputs)

    def test_pinned_input_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in plan.PINS:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((plan.ROOT / name).read_bytes())
            (root / next(iter(plan.PINS))).write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'input_digest_mismatch'):
                plan.load_inputs(root)


if __name__ == '__main__':
    unittest.main()
