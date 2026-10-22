#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Four-read cold-tripwire observer. Any nonzero phase is a terminal STOP.

No transport, timer, writes or retry. Phase 3 means EL was published, never that
the terminal loop was executed, CPU1 reset released, or Linux SMP was reached.
"""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('_31k_identity_map',
    Path(__file__).resolve().parents[1]/'smp31f-entry/telemetry.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
identity_classification = previous.identity_classification
IDENTITY_KEYS = previous.IDENTITY_KEYS
MASK64 = (1 << 64)-1
RECORD_OFFSET, RECORD_END = 0x90a80, 0x90ac0
SAMPLE_OFFSETS = (RECORD_OFFSET, RECORD_OFFSET+16, RECORD_OFFSET+8, RECORD_OFFSET)
# Arrival-loop observations plus eight bounded callback loops and boundaries.
# This is only an acquisition ceiling; unchanged controller wall deadlines apply.
READS_PER_SAMPLE, MAX_SAMPLES = 4, 2048
PHASES = frozenset((0, 1, 2, 3))


def _u64(value):
    return type(value) is int and 0 <= value <= MASK64


class TelemetryError(ValueError):
    def __init__(self, reason, *, reads_attempted=0, reads_completed=0,
                 phase_before=None, phase_after=None, any_record_seen=False):
        super().__init__(reason)
        self.reason = reason
        self.reads_attempted, self.reads_completed = reads_attempted, reads_completed
        self.phase_before, self.phase_after = phase_before, phase_after
        self.any_record_seen = any_record_seen


def classify(words):
    if type(words) not in (tuple, list) or len(words) != READS_PER_SAMPLE:
        raise TelemetryError('invalid_cold_record_shape')
    if not all(_u64(word) for word in words):
        raise TelemetryError('invalid_cold_record_word')
    before, mpidr, current_el, after = words
    seen = bool(before or after)
    if before not in PHASES or after not in PHASES:
        raise TelemetryError('unknown_cold_phase', any_record_seen=seen)
    if after < before:
        raise TelemetryError('cold_phase_regression', phase_before=before,
                             phase_after=after, any_record_seen=seen)
    identity = identity_classification(mpidr if before >= 2 else None)
    result = dict(phase_before=before, phase_after=after, any_record_seen=seen,
                  stop_required=seen, highest_phase_seen=max(before, after),
                  complete=False, record_complete=False, park_verified=False,
                  reset_route='UNKNOWN', exception_level=None, error=None,
                  state='publication_in_progress', **identity)
    if before == after:
        result['state'] = ('no_cold_publication_seen', 'pre_mrs_cold_phase_seen',
                           'cold_identity_published', 'cold_el_published')[before]
    if before >= 2 and identity['identity_status'] != 'expected_cpu1':
        result['error'] = 'unexpected_cold_identity'
    if before >= 3:
        if current_el not in (4, 8, 12):
            result['error'] = result['error'] or 'committed_cold_el_invalid'
        else:
            result['exception_level'] = current_el//4
    result['record_complete'] = before == after == 3 and result['error'] is None
    return result


def sample(read64, image_base):
    if (not callable(read64) or not _u64(image_base) or image_base == 0 or
            image_base % 0x4000 or image_base > MASK64-RECORD_END):
        raise TelemetryError('invalid_cold_sampler_configuration')
    words = []
    for offset in SAMPLE_OFFSETS:
        try:
            value = read64(image_base+offset)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            raise TelemetryError('cold_record_read_failed', reads_attempted=len(words)+1,
                reads_completed=len(words),
                phase_before=words[0] if words and words[0] in PHASES else None,
                any_record_seen=bool(words and words[0])) from None
        if not _u64(value):
            raise TelemetryError('invalid_cold_read64_result', reads_attempted=len(words)+1,
                reads_completed=len(words),
                phase_before=words[0] if words and words[0] in PHASES else None,
                any_record_seen=bool(words and words[0]))
        words.append(value)
        if len(words) == 1 and value not in PHASES:
            raise TelemetryError('unknown_cold_phase', reads_attempted=1,
                                 reads_completed=1, any_record_seen=bool(value))
    try:
        result = classify(words)
    except TelemetryError as error:
        raise TelemetryError(error.reason, reads_attempted=4, reads_completed=4,
            phase_before=words[0] if words[0] in PHASES else None,
            phase_after=words[-1] if words[-1] in PHASES else None,
            any_record_seen=bool(words[0] or words[-1])) from None
    result.update(reads_attempted=4, reads_completed=4)
    return result


class Tracker:
    """Single campaign, closes on any publication, error, or budget exhaustion."""
    def __init__(self, *, max_samples=MAX_SAMPLES):
        if type(max_samples) is not int or not 1 <= max_samples <= MAX_SAMPLES:
            raise TelemetryError('invalid_cold_sample_limit')
        self._limit, self._active, self._closed = max_samples, False, False
        self._report = dict(samples_attempted=0, samples_completed=0,
            reads_attempted=0, reads_completed=0, highest_phase_seen=None,
            any_record_seen=False, stop_required=False, complete=False,
            record_complete=False, park_verified=False, reset_route='UNKNOWN',
            exception_level=None, error=None, state='not_sampled',
            **identity_classification())

    def _phase(self, value):
        if _u64(value) and value:
            self._report['any_record_seen'] = True
            self._report['stop_required'] = True
        if value in PHASES and type(value) is int:
            old = self._report['highest_phase_seen']
            self._report['highest_phase_seen'] = value if old is None else max(old, value)

    def sample(self, read64, image_base):
        if self._closed:
            return self.report()
        if self._active:
            self._report.update(error='reentrant_cold_sample', stop_required=True)
            self._closed = True
            return self.report()
        if self._report['samples_attempted'] >= self._limit:
            self._report.update(error='cold_sample_budget_exhausted', stop_required=True)
            self._closed = True
            return self.report()
        self._active = True
        self._report['samples_attempted'] += 1
        index = 0
        def guarded(address):
            nonlocal index
            if self._closed:
                raise TelemetryError('cold_tracker_closed')
            self._report['reads_attempted'] += 1
            value = read64(address)
            if self._closed:
                raise TelemetryError('cold_tracker_closed')
            if _u64(value):
                self._report['reads_completed'] += 1
                if index in (0, 3):
                    self._phase(value)
            index += 1
            return value
        try:
            result = sample(guarded, image_base)
            self._report['samples_completed'] += 1
            for key in ('state', 'error', 'record_complete', 'exception_level') + IDENTITY_KEYS:
                self._report[key] = result[key]
            self._closed = bool(result['any_record_seen'] or result['error'])
        except TelemetryError as error:
            self._report.update(error=self._report['error'] or error.reason,
                                stop_required=True)
            self._closed = True
        except (KeyboardInterrupt, SystemExit):
            self._report.update(error='cold_acquisition_interrupted', stop_required=True)
            self._closed = True
            raise
        finally:
            self._active = False
        return self.report()

    def report(self):
        return dict(self._report)
