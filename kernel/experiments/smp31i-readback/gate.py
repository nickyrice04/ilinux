# SPDX-License-Identifier: MIT
"""Original readback gate over two already-sanitized RVBAR observations.

The matching-board firmware investigation identifies a verification mask of
0x3fffffff801: address bits41:11 and bit0. It excludes upper bits63:42 from
that comparison; it does not establish those bits' hardware meaning. See the
31I research record for artifact/function/offset provenance.

This gate removes only the unsupported upper63:48-zero requirement from31H.
It retains full-word mirror equality and all existing image/lock/low-field
constraints, including the legacy bits47:42-zero condition. Those constraints
are intentionally stronger than the firmware comparison alone.

Input must be the frozen31H observer's complete, guarded two-read report.
No raw register word, address, client, target operation or mutation is used.
Passing this gate cannot establish the effective reset route or CPU execution.
"""

FIRMWARE_READBACK_MASK = 0x3fffffff801
REFUSAL = 'reset_format_requires_review'
REPORT_KEYS = frozenset((
    'state', 'read_attempts', 'read_returns', 'guard_check_attempts',
    'validated_reads', 'pending_cpu_id', 'rows', 'mirrors_equal',
    'exact_entry_offset', 'effective_reset_route', 'error',
))
ROW_KEYS = frozenset((
    'cpu_id', 'legacy_page_field_matches_vectors', 'legacy_lock_bit0',
    'unknown_low_bits_class', 'bit11_set', 'unknown_upper_bits_present',
    'firmware_format_field_relation', 'firmware_format_low_bits_10_1_class',
    'firmware_format_high_bits_63_42_class', 'firmware_format_bits_47_42_class',
))


def need(condition):
    if not condition:
        raise ValueError(REFUSAL)


def text_is(value, expected):
    return type(value) is str and value == expected


def validate(report):
    """Return a fresh fixed-schema decision, or a fixed non-identifying error.

    The observer commits each row only after its immediate exception count is
    the integer zero. Counts and complete/error fields must establish that
    protocol before any field can pass this gate. This is local validation;
    it neither repeats reads nor independently authenticates a captured report.
    """
    need(type(report) is dict and set(report) == REPORT_KEYS)
    need(text_is(report['state'], 'complete'))
    for key in ('read_attempts', 'read_returns', 'guard_check_attempts',
                'validated_reads'):
        need(type(report[key]) is int and report[key] == 2)
    need(report['pending_cpu_id'] is None and report['error'] is None)
    need(report['mirrors_equal'] is True)
    need(text_is(report['exact_entry_offset'], 'UNKNOWN') and
         text_is(report['effective_reset_route'], 'UNKNOWN'))
    rows = report['rows']
    need(type(rows) is list and len(rows) == 2)
    high_present = []
    for cpu, row in enumerate(rows):
        need(type(row) is dict and set(row) == ROW_KEYS)
        need(type(row['cpu_id']) is int and row['cpu_id'] == cpu)
        need(row['legacy_page_field_matches_vectors'] is True and
             row['legacy_lock_bit0'] is True and row['bit11_set'] is False)
        for key, expected in (
                ('unknown_low_bits_class', 'zero'),
                ('firmware_format_field_relation', 'image_base'),
                ('firmware_format_low_bits_10_1_class', 'zero'),
                ('firmware_format_bits_47_42_class', 'zero')):
            need(text_is(row[key], expected))
        # With bits47:42 zero, the entire reported upper63:42 classification
        # must agree with the observer's separate upper63:48-presence boolean.
        present = row['unknown_upper_bits_present']
        need(type(present) is bool)
        need(text_is(row['firmware_format_high_bits_63_42_class'],
                     'nonzero' if present else 'zero'))
        high_present.append(present)
    # Equal full-word mirrors cannot have differing upper-field classes.
    need(high_present[0] == high_present[1])
    return {
        'result': 'RESET_ADDRESS_READBACK_PASS',
        'firmware_readback_mask': FIRMWARE_READBACK_MASK,
        'address_field_matches_image_base': True,
        'full_word_mirrors_equal': True,
        'legacy_lock_bit0': True,
        'low_bits_10_1_and_47_42_zero': True,
        'upper_bits_63_48': 'present_uninterpreted' if high_present[0] else 'zero',
        'upper_bits_required_zero': False,
        'upper_field_semantics': 'UNKNOWN',
        'exact_entry_offset': 'UNKNOWN',
        'effective_reset_route': 'UNKNOWN',
        'cpu1_execution': 'UNVERIFIED',
        'hardware_operations': 0,
    }
