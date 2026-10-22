#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original fault tests; frozen reports are input data, never altered."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('offline_evidence31o', HERE / 'evidence.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
PINS = {
    'm': '9cb29ff573b2ddf52ed94978df700943a50bafa5be742ac480986b5f77b891ca',
    'n': 'bcc5f1b8bcfc79e50cdb7372616efbe3e2c46ea3341f7ee3d54db0affb74db6a',
}


def fixture(kind='n'):
    path = ROOT / ('native/boot/attempt31%s-controller-2026-10-22.json' % kind)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PINS[kind]:
        raise AssertionError('frozen_fixture_changed')
    return e.read_report(path)


class EvidenceTests(unittest.TestCase):
    def classify(self, report, expected):
        output = e.classify(report)
        self.assertEqual(output['classification'], expected, output)
        self.assertEqual(output['cpu1_execution'], 'UNVERIFIED')
        self.assertEqual(output['first_instruction_fetch'], 'UNKNOWN')
        self.assertEqual(output['firmware_cause'], 'UNKNOWN')
        self.assertFalse(output['negative_excludes_execution'])
        self.assertFalse(output['native_ready'])
        self.assertEqual(output['hardware_operations'], 0)
        return output

    def test_frozen_native_reports(self):
        for kind, maintenance, reads in (('m', 258, 8), ('n', 254, 6)):
            with self.subTest(kind=kind):
                report = fixture(kind)
                before = copy.deepcopy(report)
                output = self.classify(report, 'NATURAL_TIMEOUT_WITHOUT_VISIBLE_ENTRY')
                self.assertEqual(output['counts']['maintenance_acknowledged'], maintenance)
                self.assertEqual(output['counts']['cpu_state_observation_reads'], reads)
                self.assertEqual(report, before)
                self.assertEqual(output['report_authenticity'], 'NOT_ESTABLISHED')

    def test_canonical_hash_ignores_dictionary_order(self):
        original = fixture()
        reordered = dict(reversed(list(original.items())))
        self.assertEqual(e.classify(original)['report_canonical_sha256'],
                         e.classify(reordered)['report_canonical_sha256'])

    def test_missing_fields_do_not_become_negative(self):
        paths = [('start_pair',), ('paired_observation',), ('normal_observation',),
                 ('cpu0_control',), ('connection',), ('power_observation', 'samples'),
                 ('start_pair', 'intent_durable'), ('start_pair', 'reply_received'),
                 ('start_pair', 'diagnostics_verified'), ('reason',)]
        for path in paths:
            with self.subTest(path=path):
                report = fixture()
                item = report
                for key in path[:-1]:
                    item = item[key]
                del item[path[-1]]
                self.classify(report, 'INCOMPLETE')

    def test_counter_types_include_bool_rejection(self):
        for value in (True, False, -1, 1.0, '2', None, 100001):
            for path in (('arrival_samples',), ('start_pair', 'stores_acknowledged'),
                         ('cpu0_control', 'reads_attempted'),
                         ('paired_observation', 'cold', 'maintenance_acknowledged')):
                with self.subTest(value=value, path=path):
                    report, node = fixture(), None
                    node = report
                    for key in path[:-1]:
                        node = node[key]
                    node[path[-1]] = value
                    self.classify(report, 'REFUSED')

    def test_each_pair_completion_fact_required(self):
        keys = ('intent_durable', 'dispatch_attempted', 'reply_received',
                'return_token_matched', 'diagnostics_verified')
        for key in keys:
            for value in (False, 1, None, 'yes'):
                with self.subTest(key=key, value=value):
                    report = fixture()
                    report['start_pair'][key] = value
                    self.classify(report, 'REFUSED')

    def test_pair_completion_uncertainty_is_incomplete(self):
        report = fixture()
        report['start_pair'].update(result='START_PAIR_COMPLETION_UNCERTAIN',
                                   reply_received=False, return_token_matched=False,
                                   diagnostics_verified=False, stores_acknowledged=0,
                                   possible_completed_stores=[0, 1, 2])
        report['start_writes_acknowledged'] = 0
        self.classify(report, 'INCOMPLETE')

    def test_pair_ack_and_possibility_contradictions(self):
        for key, value in (('stores_acknowledged', 1),
                           ('possible_completed_stores', [0, 1, 2]),
                           ('possible_completed_stores', [True]),
                           ('possible_completed_stores', [2, 2]),
                           ('possible_completed_stores', [])):
            with self.subTest(key=key, value=value):
                report = fixture()
                report['start_pair'][key] = value
                self.classify(report, 'REFUSED')
        report = fixture()
        report['start_writes_acknowledged'] = 1
        self.classify(report, 'REFUSED')

    def test_pair_cannot_claim_atomicity_execution_retry_or_timing(self):
        for key in ('pair_atomic', 'completion_proves_cpu1_execution',
                    'retry_authorized', 'hardware_timing_measured'):
            report = fixture()
            report['start_pair'][key] = True
            self.classify(report, 'REFUSED')

    def test_control_pass_label_alone_is_insufficient(self):
        for key in ('cpu0_control', 'cpu0_normal_control', 'cpu0_cache_control'):
            for flag in ('marker_observed', 'canaries_preserved', 'original_restored'):
                report = fixture()
                report[key][flag] = False
                self.classify(report, 'INCOMPLETE')

    def test_control_counters_and_visibility_claims(self):
        report = fixture()
        report['cpu0_cache_control']['reads_completed'] = 49
        self.classify(report, 'REFUSED')
        report = fixture()
        report['cpu0_normal_control']['cpu1_visibility'] = 'VERIFIED'
        self.classify(report, 'REFUSED')

    def test_observer_faults_are_incomplete_not_negative(self):
        for key in ('recorder_observation', 'cold_observation'):
            report = fixture()
            report[key]['error'] = 'synthetic_fault'
            self.classify(report, 'INCOMPLETE')
        for part in ('cold', 'vector'):
            report = fixture()
            report['paired_observation'][part]['error'] = 'synthetic_fault'
            self.classify(report, 'INCOMPLETE')

    def test_journal_and_transport_failures_are_incomplete(self):
        for key, value in (('native_journal_failed', True),
                           ('connection_journal_failed', True), ('transport_closed', False)):
            report = fixture()
            report['connection'][key] = value
            self.classify(report, 'INCOMPLETE')
        report = fixture()
        report['paired_observation']['vector']['journal_failed'] = True
        self.classify(report, 'INCOMPLETE')

    def test_completed_samples_require_their_reads(self):
        for key in ('recorder_observation', 'cold_observation'):
            report = fixture()
            report[key]['reads_completed'] -= 1
            self.classify(report, 'REFUSED')
        report = fixture()
        report['paired_observation']['vector']['reads_completed'] = 1
        self.classify(report, 'REFUSED')

    def test_partial_final_observation_is_incomplete(self):
        report = fixture()
        row = report['cold_observation']
        row['samples_attempted'] += 1
        row['reads_attempted'] += 1
        self.classify(report, 'INCOMPLETE')

    def test_maintenance_totals_cannot_be_fabricated(self):
        report = fixture()
        report['cache_maintenance_acknowledged'] -= 1
        self.classify(report, 'REFUSED')
        report = fixture()
        report['paired_observation']['vector']['maintenance_intents'] -= 1
        self.classify(report, 'REFUSED')

    def test_phase_order_and_omission_contract(self):
        for key in ('power_observation', 'cpu_state_observation'):
            report = fixture()
            report[key]['samples'][1]['phase'] = 'after_first_start'
            self.classify(report, 'REFUSED')
            report = fixture()
            report[key]['omitted_phases'] = []
            self.classify(report, 'REFUSED')

    def test_state_partial_completion_is_not_fabricated(self):
        for key in ('power_observation', 'cpu_state_observation'):
            report = fixture()
            row = report[key]
            row['samples'][-1]['complete'] = False
            row['samples'][-1]['cpu1'] = None
            row['reads_completed'] -= 1
            self.classify(report, 'INCOMPLETE')

    def test_state_counter_and_comparison_contradictions(self):
        report = fixture()
        report['cpu_state_observation']['samples'][-1]['cores_equal'] = False
        self.classify(report, 'REFUSED')
        report = fixture()
        report['cpu_state_observation']['samples'][-1]['cpu1']['changed_from_baseline'] = False
        self.classify(report, 'REFUSED')
        report = fixture()
        report['power_observation']['reads_completed'] = 5
        self.classify(report, 'REFUSED')

    def test_power_transition_is_never_execution(self):
        report = fixture()
        self.assertEqual(report['power_observation']['samples'][-1]['cpu1']['actual'], 15)
        self.classify(report, 'NATURAL_TIMEOUT_WITHOUT_VISIBLE_ENTRY')
        report['power_observation']['entry_execution'] = 'PROVEN'
        self.classify(report, 'REFUSED')

    def test_positive_metadata_requires_raw_record_review(self):
        for key in ('cpu1_arrival_verified', 'cpu1_prefix_identity_observed',
                    'park_verified', 'counter_progress_verified'):
            report = fixture()
            report[key] = True
            self.classify(report, 'REPORTED_POSITIVE_REQUIRES_RECORD_REVIEW')

    def test_committed_prefix_label_does_not_become_execution_proof(self):
        report = fixture()
        row = report['normal_observation']['vector']
        row.update(highest_phase_seen=2, any_record_seen=True, identity_status='expected_cpu1',
                   cpu1_execution='PREFIX_IDENTITY_OBSERVED')
        self.classify(report, 'REPORTED_POSITIVE_REQUIRES_RECORD_REVIEW')

    def test_identity_without_commit_is_refused(self):
        report = fixture()
        report['normal_observation']['vector'].update(any_record_seen=True,
                                                    identity_status='expected_cpu1')
        self.classify(report, 'REFUSED')
        report = fixture()
        report['cold_observation']['observed_cpu_id'] = 1
        self.classify(report, 'REFUSED')

    def test_record_and_nested_triad_contradictions(self):
        report = fixture()
        report['cold_observation']['record_complete'] = True
        self.classify(report, 'REFUSED')
        report = fixture()
        report['paired_observation']['vector']['cached']['reads_completed'] = 2
        self.classify(report, 'REFUSED')
        report = fixture()
        report['paired_observation']['vector']['maintained']['any_record_seen'] = True
        self.classify(report, 'REFUSED')

    def test_unknown_or_causal_claims_are_not_silently_accepted(self):
        for key in ('effective_reset_route', 'cache_visibility_cause', 'device_visibility_cause'):
            report = fixture()
            report[key] = 'CONFIRMED'
            self.classify(report, 'REFUSED')
        report = fixture()
        report['cpu0_post_start_record_stores'] = 1
        self.classify(report, 'REFUSED')

    def test_positive_execution_label_cannot_hide_behind_zero_record(self):
        for group in ('normal_observation', 'paired_observation'):
            for channel in ('vector', 'cold'):
                for label in ('PREFIX_IDENTITY_OBSERVED', 'VERIFIED', True):
                    report = fixture()
                    report[group][channel]['cpu1_execution'] = label
                    self.classify(report, 'REFUSED')

    def test_no_callbacks_are_planned_by_supported_campaigns(self):
        for kind in ('m', 'n'):
            for planned, completed in ((1, 0), (1, 1), (0, 1)):
                report = fixture(kind)
                report.update(requests_planned=planned, requests_completed=completed)
                self.classify(report, 'REFUSED')

    def test_complete_negative_pair_requires_both_complete_triads_per_sample(self):
        report = fixture()
        row = report['paired_observation']['vector']
        row['reads_attempted'] -= 3
        row['reads_completed'] -= 3
        self.classify(report, 'REFUSED')

    def test_not_natural_timeout_is_incomplete(self):
        for key, value in (('reason', 'outer_deadline'), ('phase', 'connect'), ('result', 'ERROR')):
            report = fixture()
            report[key] = value
            self.classify(report, 'INCOMPLETE')

    def test_untrusted_strings_are_not_reemitted(self):
        report = fixture()
        secret = 'PRIVATE_SENTINEL_NEVER_ECHO'
        report['notes'] = secret
        report['terminal_observation_error'] = secret
        output = self.classify(report, 'INCOMPLETE')
        self.assertNotIn(secret, json.dumps(output))

    def test_reader_rejects_duplicate_nonfinite_malformed_and_oversized(self):
        payloads = [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}',
                    b'{"x":1e1000}', b'{', b'\xff', b' ' * (e.MAX_BYTES + 1)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'input.json'
            for raw in payloads:
                with self.subTest(kind=raw[:30]):
                    path.write_bytes(raw)
                    with self.assertRaises(e.EvidenceError):
                        e.read_report(path)

    def test_reader_rejects_symlink_and_nonregular_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'target.json'
            target.write_text('{}')
            link = root / 'alias.json'
            link.symlink_to(target)
            fifo = root / 'fifo'
            os.mkfifo(fifo)
            for path in (link, root, fifo):
                with self.assertRaises(e.EvidenceError):
                    e.read_report(path)

    def test_direct_input_tree_bounds_and_types(self):
        deep = 0
        for _ in range(e.MAX_DEPTH + 2):
            deep = [deep]
        for value in ([], {'a': float('nan')}, {'a': object()}, {1: 2}, {'a': deep},
                      {'a': 'x' * (e.MAX_STRING + 1)}, {'a': 1 << 100},
                      {'a': [0] * (e.MAX_NODES + 1)}):
            self.classify(value, 'REFUSED')

    def test_cli_uses_fixed_error_and_no_live_option(self):
        completed = subprocess.run([sys.executable, '-I', str(HERE / 'evidence.py'),
                                    '--report', '/missing/PRIVATE_SENTINEL'],
                                   capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn('PRIVATE_SENTINEL', completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout)['classification'], 'REFUSED')
        refused = subprocess.run([sys.executable, '-I', str(HERE / 'evidence.py'),
                                  '--report', 'unused', '--live', 'PRIVATE_SENTINEL'],
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(refused.returncode, 2)
        self.assertNotIn('PRIVATE_SENTINEL', refused.stdout + refused.stderr)
        self.assertEqual(json.loads(refused.stdout)['reason'], 'ARGUMENTS_INVALID')


if __name__ == '__main__':
    unittest.main()
