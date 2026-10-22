# SPDX-License-Identifier: GPL-2.0-or-later
"""Fixed CPU0 observer control; no transport, discovery, or native entrypoint.

Caller publishes the leaf in its already owned helper allocation and verifies
the proposed translation probes before constructing Control. Callbacks are
strictly bound by the caller to this plan. Saved RAM stays private. The control
never invokes or modifies the CPU1 recorder and never establishes CPU1 visibility.
"""
import copy
from dataclasses import dataclass
import hashlib
import math
import struct
import time

ALLOCATION_BYTES = 0x4000
IMAGE_BYTES = 3932160
IMAGE_SHA256 = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
LEAF_OFFSET = 0x200
SCRATCH_OFFSET = 0x90b00
SCRATCH_BYTES = 64
WORD_OFFSETS = tuple(range(0, SCRATCH_BYTES, 8))
MARKER_OFFSET = 32
MARKER_INDEX = MARKER_OFFSET // 8
MARKER = 0x314b435055304f4b
RETURN_VALUE = 0x314b
RX_ALIAS = 0xc0000000000
MAX_SECONDS = 2.0
WORDS = (0xf9000001, 0xd5033f9f, 0xd2862960, 0xd65f03c0)
LEAF = struct.pack('<4I', *WORDS)
LEAF_SHA256 = hashlib.sha256(LEAF).hexdigest()
MASK64 = (1 << 64) - 1


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def u64(value):
    return type(value) is int and 0 <= value <= MASK64


def address_integer(value):
    """Accept parser int subclasses, never numeric ducks or bool addresses.

    Construct decorates BootArgs values for hexadecimal display. Invoke the
    built-in integer descriptor to preserve their stored numeric value without
    calling subclass conversion/comparison overrides. Observation words remain
    subject to the separate, exact-int u64 check.
    """
    need(type(value) is not bool and issubclass(type(value), int),
         'control_address_type')
    number = int.__int__(value)
    need(u64(number), 'control_address_type')
    return number


@dataclass(frozen=True)
class Layout:
    """Private runtime addresses. Never serialize this object to public output."""
    image: int
    helper: int
    ram_lo: int
    ram_hi: int

    @property
    def leaf(self):
        return (self.helper | RX_ALIAS) + LEAF_OFFSET

    @property
    def scratch(self):
        return self.image + SCRATCH_OFFSET

    @property
    def marker_address(self):
        return self.scratch + MARKER_OFFSET


def layout(image, helper, ram_lo, ram_hi):
    image, helper, ram_lo, ram_hi = (
        address_integer(value) for value in (image, helper, ram_lo, ram_hi))
    # M5 DRAM starts at 1 TiB; retain the established <2 TiB physical bound
    # rather than the older chips' lower-address assumption. Alias bits remain
    # disjoint, and the controller already binds these bounds to live BootArgs.
    need(0x800000000 <= ram_lo < ram_hi < 1 << 41, 'control_ram_bounds')
    need(image % ALLOCATION_BYTES == 0 and helper % ALLOCATION_BYTES == 0,
         'control_alignment')
    need(ram_lo <= image < image + IMAGE_BYTES <= ram_hi, 'control_image_bounds')
    need(ram_lo <= helper < helper + ALLOCATION_BYTES <= ram_hi, 'control_helper_bounds')
    need(helper + ALLOCATION_BYTES <= image or helper >= image + IMAGE_BYTES,
         'control_image_overlap')
    need(400 <= LEAF_OFFSET < LEAF_OFFSET + len(LEAF) <= ALLOCATION_BYTES and
         0x90ac0 <= SCRATCH_OFFSET < SCRATCH_OFFSET + SCRATCH_BYTES <= 0xa0000,
         'control_layout_overlap')
    return Layout(image, helper, ram_lo, ram_hi)


def verify_image_padding(image):
    need(type(image) is bytes and len(image) == IMAGE_BYTES and
         hashlib.sha256(image).hexdigest() == IMAGE_SHA256, 'control_image_digest')
    need(image[SCRATCH_OFFSET:SCRATCH_OFFSET + SCRATCH_BYTES] == bytes(SCRATCH_BYTES),
         'control_image_padding')
    return True


def validate_layout(plan):
    need(type(plan) is Layout, 'control_layout_type')
    need(all(u64(value) for value in (plan.image, plan.helper, plan.ram_lo, plan.ram_hi)),
         'control_layout_invalid')
    need(plan == layout(plan.image, plan.helper, plan.ram_lo, plan.ram_hi),
         'control_layout_invalid')
    return plan


def translation_probes(plan):
    """Original fixed-span AT requests; caller uses its verified EL regime.

    The leaf uses Normal memory. The distinct shared scratch record must be
    Device-nGnRnE through its identity address, matching the existing recorder.
    AT does not establish execute permission; the returning call is the control.
"""
    validate_layout(plan)
    probes = [dict(name='control_leaf_alias_read', address=plan.leaf,
                   physical=plan.helper + LEAF_OFFSET, write=False,
                   permission_fault=False, attr=0xff, shareability=2)]
    for name, offset in (('first', WORD_OFFSETS[0]), ('last', WORD_OFFSETS[-1])):
        for write in (False, True):
            probes.append(dict(name='control_scratch_' + name + ('_write' if write else '_read'),
                address=plan.scratch + offset, physical=plan.scratch + offset,
                write=write, permission_fault=False, attr=0, shareability=None))
    return tuple(probes)


class ControlError(ValueError):
    """Sanitized report plus private cause, preserving an outer alarm/interrupt."""
    def __init__(self, reason, report, cause=None):
        super().__init__(reason)
        self.reason, self.report, self.cause = reason, copy.deepcopy(report), cause


class Control:
    """One bounded control with no retry or fault-cleanup path.

read64(address) uses the same existing CPU0 LDR helper as recorder observations.
store(value) invokes only this plan's leaf and exact marker address, journals
the controller's mutation intent, performs its immediate exception check, and
returns the leaf value. read64 also performs the immediate exception check.
journal(snapshot) persists each prefix before requests. starts() must return
the controller's live start-intent count, strictly zero throughout this control.
All callbacks and state snapshots remain synchronous; no target code is run here.
"""
    def __init__(self, plan, *, read64, store, journal, starts,
                 clock=time.monotonic, publication_verified=False):
        self.plan = validate_layout(plan)
        need(publication_verified is True, 'control_publication_unverified')
        need(all(callable(v) for v in (read64, store, journal, starts, clock)),
             'control_callback_type')
        self.read64, self.store, self.journal = read64, store, journal
        self.starts, self.clock = starts, clock
        self.used = False
        self.started = self.last = None
        self.state = dict(schema='cpu0_observer_control31k', result='NOT RUN',
            phase='initial', scope='cpu0_shared_device_ram_observer',
            read_intents=0, reads_attempted=0, reads_completed=0,
            write_intents=0, writes_attempted=0,
            writes_acknowledged=0, marker_observed=False, canaries_preserved=False,
            original_restored=False, journal_failed=False, elapsed_seconds=0.0,
            cpu1_execution='NOT_TESTED', cpu1_record_visibility='NOT_TESTED')

    def stop(self, reason, cause=None):
        self.state.update(result='STOP', reason=reason)
        raise ControlError(reason, self.state, cause) from None

    def budget(self):
        try:
            count = self.starts()
            if type(count) is not int or count != 0:
                self.stop('control_after_start_intent')
            now = self.clock()
            if type(now) not in (int, float) or not math.isfinite(now):
                self.stop('control_clock_invalid')
            if self.last is not None and now < self.last:
                self.stop('control_clock_regressed')
            if self.started is None:
                self.started = now
            elapsed = now - self.started
            if not math.isfinite(elapsed):
                self.stop('control_clock_invalid')
            self.last = now
            self.state['elapsed_seconds'] = round(elapsed, 6)
            if elapsed >= MAX_SECONDS:
                self.stop('control_deadline')
        except ControlError:
            raise
        except (Exception, KeyboardInterrupt) as exc:
            self.stop('control_budget_failed', exc)

    def emit(self, phase):
        self.state['phase'] = phase
        try:
            self.journal(copy.deepcopy(self.state))
        except (Exception, KeyboardInterrupt) as exc:
            self.state['journal_failed'] = True
            self.stop('control_journal_failed', exc)

    def read_block(self, phase):
        words = []
        for offset in WORD_OFFSETS:
            self.budget()
            self.state['read_intents'] += 1
            self.emit(phase)
            self.budget()
            self.state['reads_attempted'] += 1
            try:
                value = self.read64(self.plan.scratch + offset)
            except (Exception, KeyboardInterrupt) as exc:
                self.stop('control_read_failed', exc)
            if not u64(value):
                self.stop('control_read_value')
            self.state['reads_completed'] += 1
            self.budget()
            words.append(value)
        return tuple(words)

    def write_word(self, value, phase):
        self.budget()
        self.state['write_intents'] += 1
        self.emit(phase)
        self.budget()
        self.state['writes_attempted'] += 1
        try:
            returned = self.store(value)
        except (Exception, KeyboardInterrupt) as exc:
            self.stop('control_store_failed', exc)
        if type(returned) is not int or returned != RETURN_VALUE:
            self.stop('control_store_return')
        self.state['writes_acknowledged'] += 1
        self.budget()

    def run(self):
        if self.used:
            self.stop('control_already_used')
        self.used = True
        try:
            self.budget()
            self.state['result'] = 'RUNNING'
            original = self.read_block('baseline')
            if original != (0,) * len(WORD_OFFSETS):
                self.stop('control_scratch_not_fresh')
            self.write_word(MARKER, 'marker_write')
            observed = self.read_block('marker_read')
            expected = list(original)
            expected[MARKER_INDEX] = MARKER
            if observed != tuple(expected):
                self.stop('control_marker_or_canary_mismatch')
            self.state.update(marker_observed=True, canaries_preserved=True)
            self.emit('marker_verified')
            self.write_word(original[MARKER_INDEX], 'restore_write')
            if self.read_block('restore_read') != original:
                self.stop('control_restore_mismatch')
            self.state['original_restored'] = True
            self.budget()
            self.state['result'] = 'CPU0_OBSERVER_CONTROL_PASS'
            self.emit('complete')
            self.budget()
            return copy.deepcopy(self.state)
        except ControlError:
            raise
        except (Exception, KeyboardInterrupt) as exc:
            self.stop('control_interrupted', exc)
