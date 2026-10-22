# SPDX-License-Identifier: GPL-2.0-or-later
"""Original fixed CPU1 start-pair leaf and pure contracts. No target API.

Removing observer/USB/journal work between the two existing stores tests an
instrumentation-timing hypothesis, not a proven t6050 hardware requirement.
"""
import hashlib
import struct

LEAF_OFFSET = 0x240
HELPER_BYTES = 0x4000
START_ADDRESSES = (0x280688004, 0x280688008)
VALUE = 2
RETURN_TOKEN = 0x314e
WORDS = (0xd2900008, 0xf2b00d08, 0xf2c00048, 0x52800049,
         0xd5033f9f, 0xb9000509, 0xd5033f9f, 0xb9000909,
         0xd5033f9f, 0xd28629c0, 0xd65f03c0)
LEAF = struct.pack('<11I', *WORDS)
RX_ALIAS = 0xc0000000000


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def verify_leaf(payload=LEAF):
    """Exact allowlist, not a general ARM decoder or arbitrary code checker."""
    need(type(payload) is bytes and payload == LEAF, 'start_pair_leaf_changed')
    return dict(result='FIXED_START_PAIR_LEAF_PASS', bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(), instructions=11,
                store_width_bits=32, store_count=2, store_value=VALUE,
                store_offsets=[20, 28], completion_barrier_offset=32,
                instructions_between_stores=['DSB SY'],
                host_transactions_between_stores=0, atomic=False,
                interrupts_modified=False, stack_accesses=0, memory_reads=0,
                system_register_writes=0, cache_operations=0,
                native_execution='NOT RUN')


def entry_address(helper, lower, upper):
    # The pinned BootArgs parser returns integer subclasses. Preserve their
    # exact arithmetic rather than coercing arbitrary input; bool is not an
    # address even though Python makes it an int subclass.
    need(all(isinstance(value, int) and not isinstance(value, bool)
             for value in (helper, lower, upper)),
         'start_pair_address_type')
    need(0 < lower <= helper < helper+HELPER_BYTES <= upper < 1 << 41 and
         helper % HELPER_BYTES == 0, 'start_pair_allocation')
    need(LEAF_OFFSET % 64 == 0 and LEAF_OFFSET + len(LEAF) <= 0x1000,
         'start_pair_leaf_layout')
    return (helper | RX_ALIAS) + LEAF_OFFSET


def validate_completion(token, diagnostics):
    """Only after the normal return AND the existing clean diagnostics check.

    A failed call can have completed zero, one or both MMIO stores. Never
    convert a missing token, bad token or unknown diagnostic into a per-store
    acknowledgment, and never retry the pair.
    """
    need(type(token) is int and token == RETURN_TOKEN, 'start_pair_return_token')
    need(type(diagnostics) is int and diagnostics == 0, 'start_pair_diagnostics')
    return dict(result='START_PAIR_COMPLETION_CONFIRMED', stores_acknowledged=2,
                completion_proves_cpu1_execution=False,
                pair_atomic=False, hardware_timing_measured=False)


def uncertain_completion():
    return dict(result='START_PAIR_COMPLETION_UNKNOWN', stores_acknowledged=0,
                possible_completed_stores=[0, 1, 2], retry_authorized=False,
                further_target_operation_authorized=False,
                completion_proves_cpu1_execution=False)
