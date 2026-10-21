#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pure classifiers for sequential CPU1 RAM observations; no target access.

Partial reset-record publications are not ordered by C assignment order.
The pinned compiled image publishes MPIDR before stack; reads can interleave.
Only the final arrival condition establishes the complete matching identity.
"""
MASK64 = (1 << 64) - 1
CPU1_MPIDR = 0x40001


def u64(value):
    return type(value) is int and 0 <= value <= MASK64


def reset_stage(mpidr, stack, spin_mpidr, flag, expected_stack):
    if not all(u64(x) for x in (mpidr, stack, spin_mpidr, flag, expected_stack)):
        raise ValueError('invalid_u64')
    if expected_stack == 0 or expected_stack % 16:
        raise ValueError('invalid_expected_stack')
    stages = {
        (MASK64, 0): 'no_reset_record_seen',
        (CPU1_MPIDR, 0): 'mpidr_publication_seen',
        (MASK64, expected_stack): 'stack_publication_seen',
        (CPU1_MPIDR, expected_stack): 'reset_identity_seen',
    }
    stage = stages.get((mpidr, stack))
    if stage is None:
        raise ValueError('unexpected_reset_record')
    if spin_mpidr not in (0, CPU1_MPIDR):
        raise ValueError('unexpected_spin_identity')
    if flag:
        if stage != 'reset_identity_seen' or spin_mpidr != CPU1_MPIDR:
            raise ValueError('arrival_identity_incomplete')
        return 'arrival_flag_seen'
    if spin_mpidr:
        if stage != 'reset_identity_seen':
            raise ValueError('spin_identity_before_reset_record')
        return 'spin_identity_seen'
    return stage


# Negative byte offsets from the *actual entry stack top*, not the reset-table
# stack value (which the installed code computes from secondary_stacks[]).
FRAME_SLOTS = (-24, -56, -72, -696, -744)
FRAME_RETURN_OFFSETS = {
    -24: {0x974: 'reset_c_non_el3_frame', 0x97c: 'reset_c_el3_frame'},
    -56: {0x32924: 'secondary_uart_puts_frame', 0x32934: 'primary_uart_puts_frame'},
    -72: {0x32958: 'init_cpu_frame'},
    -696: {0x32944: 'reset_c_stack_printf_frame',
           0x32954: 'reset_c_mpidr_printf_frame',
           0x3296c: 'reset_c_post_init_printf_frame'},
    -744: {0x15024: 'init_cpu_part_printf_frame',
           0x15064: 'init_cpu_name_printf_frame'},
}


def stack_markers(words, image_base):
    """Match only fixed compiled call-site return addresses; never emit raw RAM.

    Positive matches are remnants of expected call frames, not a current PC,
    proof a function returned, or a unique chronological trace. Missing matches
    cannot exclude execution: callees overwrite/reuse stack storage.
    """
    if not u64(image_base) or image_base % 0x4000 or set(words) != set(FRAME_SLOTS):
        raise ValueError('invalid_stack_snapshot')
    if not all(u64(value) for value in words.values()):
        raise ValueError('invalid_stack_word')
    return {label: words[offset] == image_base + relative
            for offset, choices in FRAME_RETURN_OFFSETS.items()
            for relative, label in choices.items()}
