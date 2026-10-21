#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pure, bounded observation of the original 31E stackless entry recorder.

The caller supplies a read64 function and is responsible for safe mappings,
cache visibility, exceptions and deadlines. These functions never import a
transport, poll, sleep, write target memory, or establish arrival in m1n1.
Sequential observations are not an atomic snapshot or a current-PC trace.
"""
MASK64 = (1 << 64) - 1
CPU1_MPIDR = 0x40001
RECORD_OFFSET = 0x90a40
RECORD_END = 0x90a80
PHASE_OFFSET = RECORD_OFFSET
MPIDR_OFFSET = RECORD_OFFSET + 16
CURRENT_EL_OFFSET = RECORD_OFFSET + 8
SCTLR_OFFSET = RECORD_OFFSET + 24
SAMPLE_OFFSETS = (PHASE_OFFSET, MPIDR_OFFSET, CURRENT_EL_OFFSET,
                  SCTLR_OFFSET, PHASE_OFFSET)
READS_PER_SAMPLE = len(SAMPLE_OFFSETS)
PHASES = frozenset((0, 1, 2, 3, 255))
MAX_SAMPLES = 256
_ALLOWED_AFTER = {0: PHASES, 1: frozenset((1, 2, 3, 255)),
                  2: frozenset((2, 3)), 3: frozenset((3,)),
                  255: frozenset((255,))}


def _u64(value):
    return type(value) is int and 0 <= value <= MASK64


class TelemetryError(ValueError):
    """Fixed reason plus safe acquisition progress; never private read values."""
    def __init__(self, reason, *, reads_attempted=0, reads_completed=0,
                 phase_before=None, phase_after=None):
        super().__init__(reason)
        self.reason = reason
        self.reads_attempted = reads_attempted
        self.reads_completed = reads_completed
        self.phase_before = phase_before
        self.phase_after = phase_after


def classify(words):
    """Classify (phase_before, MPIDR, CurrentEL, SCTLR, phase_after).

    Only an unchanged phase 3 proves that all captured fields preceded the
    first phase read. A changing phase records progress and requires another
    caller-directed sample; it never promotes a potentially torn observation.
    EL/cache fields from incomplete samples are deliberately uninterpreted.
    """
    if type(words) not in (tuple, list) or len(words) != READS_PER_SAMPLE:
        raise TelemetryError('invalid_record_shape')
    if not all(_u64(word) for word in words):
        raise TelemetryError('invalid_record_word')
    before, mpidr, current_el, sctlr, after = words
    if before not in PHASES or after not in PHASES:
        raise TelemetryError('unknown_recorder_phase')
    if after not in _ALLOWED_AFTER[before]:
        raise TelemetryError('recorder_phase_regression')
    if mpidr not in (0, CPU1_MPIDR):
        raise TelemetryError('unexpected_recorder_identity')
    # Identity is published before phase 1. If before=0, identity may still
    # have been read before a later publication indicated by phase_after.
    if before != 0 and mpidr != CPU1_MPIDR:
        raise TelemetryError('recorder_identity_missing')
    result = {'state': 'publication_in_progress', 'phase_before': before,
              'phase_after': after, 'identity_seen': mpidr == CPU1_MPIDR,
              'complete': False, 'exception_level': None,
              'mmu_enabled': None, 'data_cache_enabled': None,
              'instruction_cache_enabled': None}
    if before != after:
        return result
    if before == 0:
        result['state'] = ('identity_store_seen' if result['identity_seen']
                           else 'no_recorder_publication_seen')
    elif before == 1:
        result['state'] = 'identity_phase_seen'
    elif before == 2:
        result['state'] = 'before_sctlr_phase_seen'
    elif before == 255:
        # Unsupported EL is an early recorder outcome, never CPU1 arrival.
        if current_el in (4, 8, 12):
            raise TelemetryError('unsupported_el_phase_inconsistent')
        result['state'] = 'unsupported_el_phase_seen'
    else:
        if current_el not in (4, 8, 12):
            raise TelemetryError('completed_recorder_el_invalid')
        result.update(state='recorder_complete', complete=True,
                      exception_level=current_el // 4,
                      mmu_enabled=bool(sctlr & 1),
                      data_cache_enabled=bool(sctlr & 4),
                      instruction_cache_enabled=bool(sctlr & (1 << 12)))
    return result


def sample(read64, image_base):
    """Make exactly five fixed 64-bit reads unless an earlier read fails.

    The injected read64 takes an absolute address. No automatic retry occurs.
    A TelemetryError retains recognized phase labels even if later reads fail.
    KeyboardInterrupt/SystemExit propagate; the outer controller owns cleanup.
    """
    if (not callable(read64) or not _u64(image_base) or image_base == 0 or
            image_base % 0x4000 or image_base > MASK64 - RECORD_END):
        raise TelemetryError('invalid_sampler_configuration')
    words = []
    for offset in SAMPLE_OFFSETS:
        try:
            word = read64(image_base + offset)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            raise TelemetryError(
                'recorder_read_failed', reads_attempted=len(words) + 1,
                reads_completed=len(words),
                phase_before=words[0] if words and words[0] in PHASES else None,
            ) from None
        if not _u64(word):
            raise TelemetryError(
                'invalid_read64_result', reads_attempted=len(words) + 1,
                reads_completed=len(words),
                phase_before=words[0] if words and words[0] in PHASES else None,
            )
        words.append(word)
        # A malformed first phase does not justify any additional target read.
        if len(words) == 1 and word not in PHASES:
            raise TelemetryError('unknown_recorder_phase', reads_attempted=1,
                                 reads_completed=1)
    try:
        result = classify(words)
    except TelemetryError as error:
        raise TelemetryError(
            error.reason, reads_attempted=READS_PER_SAMPLE,
            reads_completed=READS_PER_SAMPLE,
            phase_before=words[0] if words[0] in PHASES else None,
            phase_after=words[-1] if words[-1] in PHASES else None,
        ) from None
    result.update(reads_attempted=READS_PER_SAMPLE,
                  reads_completed=READS_PER_SAMPLE)
    return result


class Tracker:
    """Track caller-directed samples; failures and budget exhaustion latch.

    No transport is retained and no loop is started. Repeated complete samples
    must agree on the exported EL/cache bits. A higher phase retained after a
    failed read is evidence of that read only, not a validated record.
    """
    def __init__(self, *, max_samples=MAX_SAMPLES):
        if type(max_samples) is not int or not 1 <= max_samples <= MAX_SAMPLES:
            raise TelemetryError('invalid_sample_limit')
        self._limit = max_samples
        self._attempts = self._completed = 0
        self._reads_attempted = self._reads_completed = 0
        self._highest = None
        self._last_after = None
        self._identity = False
        self._complete = None
        self._last_state = 'not_sampled'
        self._error = None
        self._active = False

    def _phase(self, phase):
        if phase is not None and phase in PHASES:
            if self._highest is None or phase > self._highest:
                self._highest = phase

    def sample(self, read64, image_base):
        if self._error is not None:
            return self.report()
        if self._active:
            self._error = 'reentrant_recorder_sample'
            return self.report()
        if self._attempts >= self._limit:
            self._error = 'recorder_sample_budget_exhausted'
            return self.report()
        self._active = True
        self._attempts += 1
        local_reads = 0
        def guarded(address):
            nonlocal local_reads
            if self._error is not None:
                raise TelemetryError('recorder_tracker_closed')
            self._reads_attempted += 1
            word = read64(address)
            if _u64(word):
                self._reads_completed += 1
                if local_reads in (0, 4) and word in PHASES:
                    self._phase(word)
            local_reads += 1
            if self._error is not None:
                raise TelemetryError('recorder_tracker_closed')
            return word
        try:
            result = sample(guarded, image_base)
            self._phase(result['phase_before']); self._phase(result['phase_after'])
            if (self._last_after is not None and
                    result['phase_before'] not in _ALLOWED_AFTER[self._last_after]):
                raise TelemetryError('recorder_cross_sample_regression')
            if self._identity and not result['identity_seen']:
                raise TelemetryError('recorder_identity_regression')
            if self._complete is not None:
                keys = ('exception_level', 'mmu_enabled', 'data_cache_enabled',
                        'instruction_cache_enabled')
                if not result['complete'] or any(
                        result[key] != self._complete[key] for key in keys):
                    raise TelemetryError('completed_recorder_changed')
            self._completed += 1
            self._last_after = result['phase_after']
            self._identity |= result['identity_seen']
            self._last_state = result['state']
            if result['complete']:
                self._complete = result
        except (KeyboardInterrupt, SystemExit):
            self._error = 'recorder_read_interrupted'
            raise
        except TelemetryError as error:
            # guarded() accounts every attempted read, including interrupts.
            self._phase(error.phase_before); self._phase(error.phase_after)
            if self._error is None:
                self._error = error.reason
        finally:
            self._active = False
        return self.report()

    def report(self):
        result = {'state': self._last_state, 'samples_attempted': self._attempts,
                  'samples_completed': self._completed,
                  'reads_attempted': self._reads_attempted,
                  'reads_completed': self._reads_completed,
                  'highest_phase_seen': self._highest,
                  'identity_seen': self._identity,
                  'complete': self._complete is not None, 'error': self._error,
                  'closed': self._error is not None}
        for key in ('exception_level', 'mmu_enabled', 'data_cache_enabled',
                    'instruction_cache_enabled'):
            result[key] = self._complete[key] if self._complete else None
        return result
