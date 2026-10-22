"""Original offline readback-gate regressions; no native operations or client."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


gate = module('gate31i', HERE / 'gate.py')
observer = module('observer31h', HERE.parent / 'smp31h-reset-format/observer.py')
BASE = 1 << 40


def report(first=None, second=None):
    first = BASE | 1 if first is None else first
    second = first if second is None else second
    return {
        'state': 'complete', 'read_attempts': 2, 'read_returns': 2,
        'guard_check_attempts': 2, 'validated_reads': 2,
        'pending_cpu_id': None,
        'rows': [{'cpu_id': cpu, **observer.classify(word, BASE)}
                 for cpu, word in enumerate((first, second))],
        'mirrors_equal': first == second,
        'exact_entry_offset': 'UNKNOWN', 'effective_reset_route': 'UNKNOWN',
        'error': None,
    }


def frozen31h_predicate(value):
    """Exact original boolean predicate, independently spelled out for contrast."""
    return value['mirrors_equal'] is True and all(
        row['firmware_format_field_relation'] == 'image_base' and
        row['firmware_format_low_bits_10_1_class'] == 'zero' and
        row['firmware_format_high_bits_63_42_class'] == 'zero'
        for row in value['rows'])


class GateTests(unittest.TestCase):
    def refused(self, value):
        with self.assertRaisesRegex(ValueError, '^reset_format_requires_review$'):
            gate.validate(value)

    def test_published31h_observation_passes_without_inventing_raw_word(self):
        path = ROOT / 'native/boot/attempt31h-controller-2026-10-21.json'
        observed = json.loads(path.read_text())['rvbar_observation']
        original = deepcopy(observed)
        self.assertFalse(frozen31h_predicate(observed))
        result = gate.validate(observed)
        self.assertEqual(result['result'], 'RESET_ADDRESS_READBACK_PASS')
        self.assertEqual(result['upper_bits_63_48'], 'present_uninterpreted')
        self.assertEqual(result['effective_reset_route'], 'UNKNOWN')
        self.assertEqual(result['cpu1_execution'], 'UNVERIFIED')
        self.assertEqual(observed, original)

    def test_zero_upper_field_is_still_accepted(self):
        value = report()
        self.assertTrue(frozen31h_predicate(value))
        self.assertEqual(gate.validate(value)['upper_bits_63_48'], 'zero')

    def test_every_single_high_bit_and_exhaustive_high16_patterns(self):
        for bit in range(48, 64):
            word = BASE | 1 | (1 << bit)
            self.assertEqual(word & gate.FIRMWARE_READBACK_MASK, BASE | 1)
            self.assertEqual(gate.validate(report(word))['upper_bits_63_48'],
                             'present_uninterpreted')
        # All 65,536 upper16 patterns produce the same address comparison.
        # These are synthetic words, not a guess at31H's discarded raw bits.
        for high in range(1 << 16):
            word = BASE | 1 | (high << 48)
            result = gate.validate(report(word))
            if word & gate.FIRMWARE_READBACK_MASK != BASE | 1:
                self.fail('synthetic verification-mask relation changed')
            if result['upper_bits_63_48'] != ('present_uninterpreted' if high else 'zero'):
                self.fail('synthetic upper-field classification changed')

    def test_known_address_and_lock_bits_still_refuse(self):
        for word in (BASE, (BASE + 0x800) | 1, (BASE + 0x1000) | 1,
                     (BASE + 0x4000) | 1, (BASE ^ (1 << 41)) | 1):
            self.refused(report(word))

    def test_every_low_or_legacy_high_bit_still_refuses(self):
        for bit in list(range(1, 12)) + list(range(42, 48)):
            self.refused(report(BASE | 1 | (1 << bit)))

    def test_mirrors_must_match_even_when_high_classes_match(self):
        self.refused(report(BASE | 1 | (1 << 63), BASE | 1 | (1 << 62)))
        self.refused(report(BASE | 1, BASE | 1 | (1 << 63)))
        for equal in (False, None, 1, 'true'):
            value = report()
            value['mirrors_equal'] = equal
            self.refused(value)

    def test_every_protocol_count_requires_integer_two(self):
        for key in ('read_attempts', 'read_returns', 'guard_check_attempts',
                    'validated_reads'):
            for bad in (None, 0, 1, 3, True, 2.0, '2'):
                value = report()
                value[key] = bad
                self.refused(value)

    def test_incomplete_pending_or_error_reports_refuse(self):
        for key, bad in (('state', 'collecting'), ('state', 'error'),
                         ('state', True), ('pending_cpu_id', 0),
                         ('pending_cpu_id', False), ('error', 'private failure'),
                         ('error', False)):
            value = report()
            value[key] = bad
            self.refused(value)

    def test_report_and_rows_have_exact_sanitized_schema(self):
        for bad in (None, [], (), 'private payload'):
            self.refused(bad)
        for key in gate.REPORT_KEYS:
            value = report()
            del value[key]
            self.refused(value)
        value = report()
        value['raw_word'] = 'private'
        self.refused(value)
        for rows in (None, [], report()['rows'][:1], report()['rows'] * 2,
                     tuple(report()['rows']), [None, None]):
            value = report()
            value['rows'] = rows
            self.refused(value)
        for key in gate.ROW_KEYS:
            value = report()
            del value['rows'][1][key]
            self.refused(value)
        value = report()
        value['rows'][1]['raw_word'] = 'private'
        self.refused(value)

    def test_row_identity_and_boolean_fields_are_strict(self):
        for cpu in (0, 1):
            for key in ('legacy_page_field_matches_vectors', 'legacy_lock_bit0'):
                for bad in (False, 1, None, 'true'):
                    value = report()
                    value['rows'][cpu][key] = bad
                    self.refused(value)
            for bad in (True, 0, None, 'false'):
                value = report()
                value['rows'][cpu]['bit11_set'] = bad
                self.refused(value)
            for bad in (True, False, float(cpu), str(cpu), 1 - cpu, None):
                value = report()
                value['rows'][cpu]['cpu_id'] = bad
                self.refused(value)

    def test_classified_address_and_unknown_fields_require_consistency(self):
        for key in ('unknown_low_bits_class', 'firmware_format_field_relation',
                    'firmware_format_low_bits_10_1_class',
                    'firmware_format_bits_47_42_class'):
            for bad in ('other', None, 0, True):
                value = report()
                value['rows'][1][key] = bad
                self.refused(value)
        for bad in ('nonzero', None, 0, True):
            value = report()
            value['rows'][1]['firmware_format_high_bits_63_42_class'] = bad
            self.refused(value)
        for bad in (True, None, 0, 'false'):
            value = report()
            value['rows'][1]['unknown_upper_bits_present'] = bad
            self.refused(value)
        value = report(BASE | 1 | (1 << 63))
        value['rows'][1]['unknown_upper_bits_present'] = False
        value['rows'][1]['firmware_format_high_bits_63_42_class'] = 'zero'
        self.refused(value)  # Claims equal mirrors but differing high classes.

    def test_no_entry_or_execution_claim_is_accepted_or_created(self):
        for key in ('exact_entry_offset', 'effective_reset_route'):
            for bad in (0, 'image_base', '0x0', None):
                value = report()
                value[key] = bad
                self.refused(value)
        result = gate.validate(report(BASE | 1 | (1 << 63)))
        self.assertEqual(result['firmware_readback_mask'], 0x3fffffff801)
        self.assertFalse(result['upper_bits_required_zero'])
        self.assertEqual(result['upper_field_semantics'], 'UNKNOWN')
        self.assertEqual(result['exact_entry_offset'], 'UNKNOWN')
        self.assertEqual(result['effective_reset_route'], 'UNKNOWN')
        self.assertEqual(result['cpu1_execution'], 'UNVERIFIED')
        self.assertEqual(result['hardware_operations'], 0)

    def test_output_is_fresh_fixed_schema_and_has_no_raw_word(self):
        word = BASE | 1 | (0xabcd << 48)
        value = report(word)
        original = deepcopy(value)
        first = gate.validate(value)
        first['result'] = 'changed by caller'
        second = gate.validate(value)
        self.assertEqual(second['result'], 'RESET_ADDRESS_READBACK_PASS')
        self.assertEqual(value, original)
        text = json.dumps(second)
        self.assertNotIn(str(word), text)
        self.assertNotIn(hex(word), text)
        self.assertNotIn(str(BASE), text)
        self.assertNotIn(hex(BASE), text)
        self.assertNotIn('raw_word', text)


if __name__ == '__main__':
    unittest.main()
