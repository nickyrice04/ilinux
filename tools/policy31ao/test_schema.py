#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original synthetic metadata-shape controls; no processes or live queries."""
import importlib.util
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location('policy31ao_schema_tested',
                                            Path(__file__).with_name('schema.py'))
schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schema)


class TextShape(unittest.TestCase):
    def test_all_catalog_fields_present_even_when_unseen(self):
        result = schema.scan_text(b'Policy display header\n(lobo): true\n')
        self.assertTrue(result['qualified'])
        self.assertEqual(set(result['fields']), set(schema.CATALOG))
        self.assertEqual(result['fields']['love']['rows'], 0)
        self.assertEqual(result['fields']['lobo']['presence']['PRESENT'], 1)
        self.assertFalse(result['catalog_complete'])
        self.assertTrue(result['formatter_catalog_qualified'])
        self.assertEqual(len(schema.FORMATTER_TEXT_CATALOG), 30)
        self.assertTrue(set(schema.FORMATTER_TEXT_CATALOG) <= set(schema.CATALOG))
        self.assertEqual(schema.FORMATTER_JSON_ONLY, ('CRPO', 'smb5'))

    def test_presence_and_duplicates_are_counts_not_admission(self):
        result = schema.scan_text(b'(auxp): absent\n(auxp):\n(auxp): 1\n(rpnh): A\n(rpnh): B')
        self.assertEqual(result['fields']['auxp']['presence'],
                         {'ABSENT': 1, 'EMPTY': 1, 'PRESENT': 1})
        self.assertEqual(result['fields']['rpnh']['rows'], 2)
        self.assertEqual(result['fields']['auxp']['predicates']['boolean'], 1)

    def test_predicates_overlap_on_zero_one_and_decimal(self):
        result = schema.scan_text(b'(smb0): 1\n(stng): 4294967296\n')
        one = result['fields']['smb0']['predicates']
        self.assertEqual([one[p] for p in ('boolean', 'uint32', 'uint64decimal')], [1, 1, 1])
        counter = result['fields']['stng']['predicates']
        self.assertEqual([counter[p] for p in ('uint32', 'uint64decimal', 'uint64hex')], [0, 1, 0])

    def test_unsigned_boundaries_and_noncanonical_decimal(self):
        for value, u32, u64d, u64h in (
                (b'4294967295', True, True, False),
                (b'18446744073709551615', False, True, False),
                (b'18446744073709551616', False, False, False),
                (b'0xffffffffffffffff', False, False, True),
                (b'0x10000000000000000', False, False, False),
                (b'01', False, False, False), (b'-1', False, False, False)):
            with self.subTest(value=value):
                predicates = schema.scalar_predicates(value)
                self.assertEqual((predicates['uint32'], predicates['uint64decimal'],
                                  predicates['uint64hex']), (u32, u64d, u64h))

    def test_hash_uuid_and_versions_never_return_content(self):
        raw = (b'(spih): ' + b'a' * 96 + b'\n(vuid): 01234567-89ab-cdef-0123-456789abcdef\n'
               b'(love): 26.2.1\n(LOVE): 25G83\n')
        result = schema.scan_text(raw)
        self.assertEqual(result['fields']['spih']['predicates']['hash96'], 1)
        self.assertEqual(result['fields']['vuid']['predicates']['uuid128'], 1)
        self.assertEqual(result['fields']['love']['predicates']['version_dotted'], 1)
        self.assertEqual(result['fields']['LOVE']['predicates']['version_build'], 1)
        text = json.dumps(result)
        for secret in ('a' * 96, '01234567-89ab-cdef-0123-456789abcdef', '26.2.1', '25G83'):
            self.assertNotIn(secret, text)

    def test_group_larger_than_native_four_is_observed(self):
        result = schema.scan_text(b'(smb0,smb1,smb2,smb3,smb4): false')
        self.assertTrue(result['qualified'])
        self.assertEqual(result['group_sizes']['5_8'], 1)
        self.assertEqual(result['native4_incompatible_rows'], 1)
        self.assertEqual(result['known_tag_occurrences'], 5)

    def test_group_bound_and_empty_tag_have_fixed_reasons(self):
        result = schema.scan_text(b'(' + b','.join([b'lobo'] * 33) + b'): 1\n(lobo,): false')
        self.assertFalse(result['qualified'])
        self.assertEqual(result['malformed_reasons']['GROUP_BOUND'], 1)
        self.assertEqual(result['malformed_reasons']['EMPTY_TAG'], 1)
        self.assertEqual(result['known_tag_occurrences'], 0)

    def test_case_is_exact_and_unknown_names_only_aggregate(self):
        result = schema.scan_text(b'(CPRO): true\n(CRPO): SECRET_VALUE\n(cpro): SECRET_VALUE\n')
        self.assertEqual(result['fields']['CPRO']['rows'], 1)
        self.assertEqual(result['fields']['CRPO']['rows'], 1)
        self.assertEqual(result['unknown_tag_occurrences'], 1)
        self.assertEqual(result['unknown_tag_rows'], 1)
        text = json.dumps(result)
        for secret in ('cpro', 'SECRET_VALUE'):
            self.assertNotIn(secret, text)

    def test_qualified_six_component_vector_is_shape_only(self):
        result = schema.scan_text(b'(love): 26.1.0.1.2,3\n')
        self.assertEqual(result['fields']['love']['predicates']['version_vector6'], 1)
        self.assertEqual(result['fields']['love']['predicates']['version_vector6_uint32'], 1)
        self.assertNotIn('26.1.0.1.2,3', json.dumps(result))
        for value in (b'26.1.0.1,2', b'26.1.0.1.2.3', b'26.01.0.1.2,3',
                      b'26.1.0.1.2,18446744073709551616'):
            self.assertFalse(schema.scalar_predicates(value)['version_vector6'])

    def test_bare_hex_and_version_component_width_are_overlapping(self):
        predicates = schema.scalar_predicates(b'123')
        self.assertTrue(predicates['uint64decimal'])
        self.assertTrue(predicates['uint64barehex'])
        self.assertTrue(predicates['uint32barehex'])
        self.assertFalse(predicates['uint64hex'])
        self.assertTrue(schema.scalar_predicates(b'FFFFFFFFFFFFFFFF')['uint64barehex'])
        self.assertFalse(schema.scalar_predicates(b'FFFFFFFFFFFFFFFF')['uint32barehex'])
        self.assertFalse(schema.scalar_predicates(b'10000000000000000')['uint64barehex'])
        wide = schema.scalar_predicates(b'26.1.0.1.2,4294967296')
        self.assertTrue(wide['version_vector6'])
        self.assertFalse(wide['version_vector6_uint32'])

    def test_known_derived_expression_is_separate_from_stored_tags(self):
        result = schema.scan_text(b'(smb0 && smb1): true\n(smb0): false\n')
        self.assertTrue(result['qualified'])
        self.assertEqual(result['non_tag_expression_rows'], 1)
        self.assertEqual(result['expressions']['SMB0_AND_SMB1']['rows'], 1)
        self.assertEqual(result['fields']['smb0']['rows'], 1)
        self.assertEqual(result['fields']['smb1']['rows'], 0)
        self.assertEqual(result['native4_compatible_rows'], 1)
        for raw in (b'(smb0&&smb2): 1', b'(SMB0&&SMB1): 1', b'(smb0||smb1): 1'):
            self.assertEqual(schema.scan_text(raw)['non_tag_expression_rows'], 0)

    def test_first_parenthesis_label_does_not_silently_recover_field(self):
        result = schema.scan_text(b'Auxiliary Kernel Collection (AuxKC) Policy Hash (auxp): absent')
        self.assertEqual(result['malformed_reasons']['FIRST_PAREN_LABEL'], 1)
        self.assertFalse(result['native_first_paren_compatible'])
        self.assertEqual(result['fields']['auxp']['rows'], 0)

    def test_malformed_grammars_and_duplicate_group_counts(self):
        cases = ((b'(): value', 'EMPTY_GROUP'), (b'(lob): value', 'TAG_LENGTH'),
                 (b'(l_ob): value', 'TAG_CHAR'), (b'(lobo: value', 'MISSING_CLOSE'),
                 (b'(lobo) value', 'MISSING_COLON'), (b'((lobo): value', 'NESTED_GROUP'),
                 ('(lob\u00e9): value'.encode(), 'NONASCII_TAG'))
        for raw, reason in cases:
            with self.subTest(reason=reason):
                result = schema.scan_text(raw)
                self.assertEqual(result['malformed_reasons'][reason], 1)
        result = schema.scan_text(b'(lobo,lobo): true')
        self.assertEqual(result['duplicate_tag_rows'], 1)
        self.assertEqual(result['fields']['lobo']['rows'], 2)

    def test_input_bounds_and_utf8_fail_without_exceptions(self):
        for raw, reason in ((None, 'INPUT_TYPE'), (b'', 'INPUT_BOUND'),
                            (b'x' * 65537, 'INPUT_BOUND'), (b'\xff', 'UTF8'),
                            (b'\0', 'NUL'), (b'x' * 2049, 'LINE_BOUND')):
            with self.subTest(reason=reason):
                result = schema.scan_text(raw)
                self.assertFalse(result['qualified'])
                self.assertEqual(result['failure_reason'], reason)

    def test_unknown_duplicates_do_not_return_names_or_values(self):
        result = schema.scan_text(b'(Q9Z8,Q9Z8,lobo): SUPER_PRIVATE_TOKEN\n')
        self.assertEqual(result['unknown_tag_occurrences'], 2)
        self.assertEqual(result['duplicate_tag_rows'], 1)
        self.assertNotIn('Q9Z8', json.dumps(result))
        self.assertNotIn('SUPER_PRIVATE_TOKEN', json.dumps(result))


class JsonShape(unittest.TestCase):
    def test_whole_document_shapes_only(self):
        raw = b'{"PRIVATE_KEY":{"lobo":true,"love":["PRIVATE_VALUE",9]},"ECID":"PRIVATE_IDENTIFIER"}'
        result = schema.scan_json(raw)
        self.assertTrue(result['qualified'])
        self.assertEqual(result['fields']['lobo']['kinds']['BOOLEAN'], 1)
        self.assertEqual(result['fields']['love']['kinds']['ARRAY'], 1)
        self.assertEqual(result['unknown_key_occurrences'], 1)
        for secret in ('PRIVATE_KEY', 'PRIVATE_VALUE', 'PRIVATE_IDENTIFIER'):
            self.assertNotIn(secret, json.dumps(result))

    def test_utf8_envelope_syntax_duplicates_depth_nodes_are_distinct(self):
        cases = ((b'\xff', 'UTF8'), (b'prefix {"lobo":1}', 'ENVELOPE'),
                 (b'{"lobo":}', 'SYNTAX'), (b'{"lobo":1,"lobo":0}', 'DUPLICATE'),
                 (b'[' * 17 + b'0' + b']' * 17, 'DEPTH'),
                 (b'[' + b'0,' * 2048 + b'0]', 'NODES'))
        for raw, stage in cases:
            with self.subTest(stage=stage):
                result = schema.scan_json(raw)
                self.assertFalse(result['qualified'])
                self.assertEqual(result['failure_stage'], stage)

    def test_no_substring_extraction_or_multiple_documents(self):
        for raw in (b'prefix {"lobo":true}', b'{"lobo":true} suffix',
                    b'{"lobo":true} {"love":"PRIVATE"}', b'{}\n[]'):
            result = schema.scan_json(raw)
            self.assertFalse(result['qualified'])
            self.assertEqual(result['failure_stage'], 'ENVELOPE')

    def test_nested_unknown_duplicate_is_refused_without_key(self):
        result = schema.scan_json(b'{"lobo":{"PRIVATE_KEY":1,"PRIVATE_KEY":2}}')
        self.assertEqual(result['failure_stage'], 'DUPLICATE')
        self.assertNotIn('PRIVATE_KEY', json.dumps(result))

    def test_braces_and_escapes_in_strings_do_not_increase_depth(self):
        raw = json.dumps({'love': '\\"' + '[' * 50 + ']' * 50}).encode()
        result = schema.scan_json(raw)
        self.assertTrue(result['qualified'])
        self.assertEqual(result['max_depth'], 1)

    def test_constants_and_raw_controls_refused(self):
        for raw in (b'{"love":NaN}', b'{"love":Infinity}', b'{"love":"a\x00b"}'):
            self.assertEqual(schema.scan_json(raw)['failure_stage'], 'SYNTAX')

    def test_numbers_are_discarded_without_float_overflow(self):
        result = schema.scan_json(b'{"stng":1e999999,"ECID":' + b'9' * 5000 + b'}')
        self.assertTrue(result['qualified'])
        self.assertEqual(result['fields']['stng']['kinds']['NUMBER'], 1)
        self.assertEqual(result['fields']['ECID']['kinds']['NUMBER'], 1)

    def test_unpaired_surrogate_refused(self):
        for raw in (b'{"love":"\\ud800"}', b'{"\\ud800":1}'):
            self.assertEqual(schema.scan_json(raw)['failure_stage'], 'SYNTAX')

    def test_case_distinct_and_all_fields_have_fixed_shape(self):
        result = schema.scan_json(b'{"LOVE":"PRIVATE","love":"PRIVATE","Love":"PRIVATE"}')
        self.assertEqual(result['fields']['LOVE']['key_occurrences'], 1)
        self.assertEqual(result['fields']['love']['key_occurrences'], 1)
        self.assertEqual(result['unknown_key_occurrences'], 1)
        self.assertEqual(set(result['fields']), set(schema.CATALOG))
        self.assertNotIn('Love', json.dumps(result))

    def test_input_bounds_root_scalar_and_whitespace(self):
        for raw in (None, b'', b'x' * 65537, b'true', b'"PRIVATE"', b'1', b'null'):
            self.assertEqual(schema.scan_json(raw)['failure_stage'], 'ENVELOPE')
        self.assertTrue(schema.scan_json(b' \t\r\n[]\n')['qualified'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
