#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline RVBAR evidence audit; no target/client imports or register reads.

The pinned m1n1 interpretation assigns bits47:12 to a page and bit0 to lock.
This tool retains the other fields without inventing t6050 address semantics.
It does not claim an entry offset, PC, or effective reset route.
"""
PAGE_MASK = ((1 << 48) - 1) & ~0xfff
LOCK_MASK = 1
UNKNOWN_LOW_MASK = 0xffe
UNKNOWN_HIGH_MASK = ((1 << 64) - 1) ^ ((1 << 48) - 1)


def classify(value, base):
    if type(value) is not int or not 0 <= value < 1 << 64:
        raise ValueError('rvbar_word_type_or_width')
    if type(base) is not int or not 0 < base < 1 << 48 or base % 0x4000:
        raise ValueError('image_base')
    if value in (0, (1 << 64)-1, 0xbad0bad0bad0bad0):
        raise ValueError('rvbar_invalid_word')
    page = value & PAGE_MASK
    return dict(legacy_lock_bit=bool(value & LOCK_MASK),
                legacy_page_matches_vector_page=page == base,
                unclassified_low_set_bits=[b for b in range(1,12) if value & (1 << b)],
                unclassified_high_set_bits=[b for b in range(48,64) if value & (1 << b)],
                exact_entry_offset='UNKNOWN', effective_reset_route='UNKNOWN',
                native_execution='NOT RUN')


def ambiguity_example(base=1 << 40):
    # Synthetic words only. They differ in bit11, NOT in a proved address field.
    first, second = base | 1, base | 0x801
    old_same = (first & PAGE_MASK, bool(first & 1)) == (second & PAGE_MASK, bool(second & 1))
    return dict(synthetic=True, old_classification_collides=old_same,
                new_classification_distinguishes=classify(first,base) != classify(second,base),
                bit11_address_meaning='NOT_ESTABLISHED', hardware_operations=0)


if __name__ == '__main__':
    import json
    print(json.dumps(ambiguity_example(),indent=2))
