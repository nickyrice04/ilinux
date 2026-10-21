#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Acquisition-neutral, bounded CPU1 observations. No transport or live CLI.

An injected callable receives only fixed image-relative offsets. The caller is
responsible for the acquisition's correctness, side effects and deadline. This
module cannot preempt a blocked callable and never establishes boot readiness.
"""
import importlib.util
from pathlib import Path


_source = Path(__file__).resolve().parent.parent / 'smp31e-entry' / 'observe.py'
_spec = importlib.util.spec_from_file_location('_smp31e_classifiers', _source)
classifiers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(classifiers)

STACK_BOTTOM = 0x94000
STACK_TOP = 0xa0000
NORMAL_STACK_TOP = 0x178000
CANARY = 0xd1a631e0d1a631e0
LOWER_CANARIES = (STACK_BOTTOM, STACK_BOTTOM + 8)
SPIN_FLAG = 0x90258
SPIN_MPIDR = 0x90250
RESET_MPIDR = 0x90020
RESET_STACK = 0x90028
FRAME_SLOTS = (-24, -56, -72, -696, -744)
FRAME_READS = tuple(STACK_TOP + slot for slot in FRAME_SLOTS)
# Publication ordering matters: read the flag BEFORE the identity fields.
# A flag published later is deliberately not promoted into this observation.
SAMPLE_ORDER = (SPIN_FLAG, SPIN_MPIDR, RESET_MPIDR, RESET_STACK,
                *LOWER_CANARIES, *FRAME_READS)
READ_ALLOWLIST = frozenset(SAMPLE_ORDER)
READS_PER_SAMPLE = len(SAMPLE_ORDER)
MAX_SAMPLES = 256
MAX_READS = MAX_SAMPLES * READS_PER_SAMPLE


class _Abort(Exception):
    """Internal, fixed public reason only."""


class Collector:
    """Call sample() explicitly; no automatic polling, sleep or retries.

    max_samples bounds acquisition attempts, including interrupted samples.
    Every attempted read consumes budget before invoking the callable. STOP,
    budget exhaustion or observed arrival closes this collector permanently.
    New objects contain no imported/restored prior hardware state.
    """

    def __init__(self, read64, image_base, *, max_samples=64):
        if (not callable(read64) or not classifiers.u64(image_base) or
                image_base == 0 or image_base % 0x4000 or
                image_base > classifiers.MASK64 - NORMAL_STACK_TOP or
                type(max_samples) is not int or not 1 <= max_samples <= MAX_SAMPLES):
            raise ValueError('invalid_collector_configuration')
        if classifiers.FRAME_SLOTS != FRAME_SLOTS:
            raise ValueError('classifier_contract_changed')
        self._read64 = read64
        self._base = image_base
        self._limit = max_samples
        self._samples = 0
        self._complete = 0
        self._reads = 0
        self._closed = False
        self._active = False
        self._reason = 'not_sampled'
        self._stage = 'not_sampled'
        self._flag_count = 0
        self._canaries_checked = 0
        self._canaries_intact = False
        self._frames = classifiers.stack_markers(dict.fromkeys(FRAME_SLOTS, 0), image_base)
        self._arrival = False

    def _close(self, reason):
        # A later call cannot replace the first closing event or clear failure.
        if not self._closed:
            self._closed = True
            self._reason = reason

    def _read(self, offset):
        if self._closed:
            raise _Abort('collector_closed')
        if offset not in READ_ALLOWLIST:
            raise _Abort('offset_not_allowlisted')
        if self._reads >= self._limit * READS_PER_SAMPLE:
            raise _Abort('read_budget_exhausted')
        self._reads += 1
        try:
            value = self._read64(offset)
        except (KeyboardInterrupt, SystemExit):
            self._close('read_interrupted')
            raise
        except Exception:
            raise _Abort('read_error') from None
        if self._closed:  # An adversarial callback could re-enter sample().
            raise _Abort('collector_closed')
        if not classifiers.u64(value):
            raise _Abort('invalid_read64_result')
        return value

    def sample(self):
        """Read at most eleven allowlisted words and return a sanitized report.

        reset_stage() accepts either partial reset publication order. This
        observer is scoped to initial arrival, before any CPU1 callback: flag
        counts beyond one are therefore refused even with matching identity.
        Sequential words are not an atomic or current-PC snapshot.
        """
        if self._closed:
            return self.report()
        if self._active:
            self._close('reentrant_sample')
            return self.report()
        if self._samples >= self._limit:
            self._close('sample_budget_exhausted')
            return self.report()
        self._active = True
        self._samples += 1
        self._canaries_checked = 0
        self._canaries_intact = False
        try:
            flag = self._read(SPIN_FLAG)
            spin_mpidr = self._read(SPIN_MPIDR)
            mpidr = self._read(RESET_MPIDR)
            stack = self._read(RESET_STACK)
            try:
                stage = classifiers.reset_stage(mpidr, stack, spin_mpidr, flag,
                                                self._base + NORMAL_STACK_TOP)
            except ValueError:
                raise _Abort('identity_inconsistent') from None
            if flag not in (0, 1):
                raise _Abort('unexpected_flag_count')
            self._stage = stage
            self._flag_count = flag
            for offset in LOWER_CANARIES:
                intact = self._read(offset) == CANARY
                self._canaries_checked += 1
                if not intact:
                    raise _Abort('lower_canary_changed')
            self._canaries_intact = True
            words = dict.fromkeys(FRAME_SLOTS, 0)
            for slot in FRAME_SLOTS:
                words[slot] = self._read(STACK_TOP + slot)
                # Preserve a recognized earlier word even if a later read
                # fails. Zero-filled unread slots cannot match a valid base.
                matches = classifiers.stack_markers(words, self._base)
                for label, matched in matches.items():
                    self._frames[label] |= matched
            self._complete += 1
            self._reason = 'sample_complete'
            if stage == 'arrival_flag_seen':
                self._arrival = True
                self._close('arrival_observed_only')
            elif self._samples == self._limit:
                self._close('sample_budget_exhausted')
        except _Abort as exc:
            self._close(str(exc))
        finally:
            self._active = False
        return self.report()

    def report(self):
        """Copy only fixed labels, booleans and bounded counts; never raw RAM."""
        return {
            'component': 'smp31e_observer_prototype',
            'proposal_only': True,
            'native_deployment_ready': False,
            'entry_authorized': False,
            'current_pc_known': False,
            'atomic_snapshot': False,
            'hardware_compatibility_claim': 'NONE',
            'closed': self._closed,
            'reason': self._reason,
            'last_identity_stage': self._stage,
            'samples_attempted': self._samples,
            'samples_completed': self._complete,
            'sample_limit': self._limit,
            'read_calls': self._reads,
            'read_limit': self._limit * READS_PER_SAMPLE,
            'last_valid_flag_count': self._flag_count,
            'last_sample_canaries_checked': self._canaries_checked,
            'last_sample_canaries_intact': self._canaries_intact,
            'recognized_frame_remnants': dict(self._frames),
            'arrival_observed': self._arrival,
        }
