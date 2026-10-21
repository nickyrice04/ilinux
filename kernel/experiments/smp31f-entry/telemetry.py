#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded, pure observation of the unfiltered 31F entry recorder.

The caller owns mappings, cache visibility, exceptions and deadlines. This
module never imports a transport, polls, sleeps or writes target memory.
Sequential observations do not establish an atomic snapshot or current PC.
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
PHASES = frozenset((0, 1, 2, 3, 4, 255))
IDENTITY_PHASES = frozenset((2, 3, 4, 255))
MAX_SAMPLES = 256
_ALLOWED_AFTER = {0: PHASES, 1: frozenset((1, 2, 3, 4, 255)),
                  2: frozenset((2, 3, 4, 255)),
                  3: frozenset((3, 4, 255)), 4: frozenset((4,)),
                  255: frozenset((255,))}
IDENTITY_KEYS = ('identity_status', 'observed_cpu_id', 'observed_cluster',
                 'observed_core', 'observed_core_type', 'observed_macos_class',
                 'identity_mapping_evidence')
CACHE_KEYS = ('mmu_enabled', 'data_cache_enabled', 'instruction_cache_enabled')


def _u64(value):
    return type(value) is int and 0 <= value <= MASK64


def identity_classification(value=None):
    """Map only the 18 reviewed expected identities; never infer an E core.

    CPU0 was observed, secondary identities are an upstream-derived expected
    mapping checked against this machine's ADT. This is diagnostic labeling,
    not a measurement of scheduling capacity or independent identity proof.
    """
    result = dict(identity_status='not_committed' if value is None else 'unknown',
                  observed_cpu_id=None, observed_cluster=None, observed_core=None,
                  observed_core_type=None, observed_macos_class=None,
                  identity_mapping_evidence=None)
    for cpu in range(18):
        cluster, core = divmod(cpu, 6)
        kind = 'M' if cpu < 12 else 'P'
        expected = ((4 if kind == 'M' else 1) << 16) | cluster << 8 | core
        if type(value) is int and value == expected:
            result.update(identity_status='expected_cpu1' if cpu == 1 else 'other_known_cpu',
                          observed_cpu_id=cpu, observed_cluster=cluster,
                          observed_core=core, observed_core_type=kind,
                          observed_macos_class='Performance' if kind == 'M' else 'Super',
                          identity_mapping_evidence='expected_mpidr_map')
            break
    return result


class TelemetryError(ValueError):
    """Fixed reason and acquisition progress; no raw register/transport values."""
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

    A field is interpreted only if its commit phase preceded the first read.
    Stable phase 3 permits EL interpretation; only stable phase 4 with expected
    CPU1 identity permits cache interpretation and completion. Wrong identity
    is retained in sanitized form and carries an error, never completion.
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
    identity = identity_classification(mpidr if before in IDENTITY_PHASES else None)
    expected = identity['identity_status'] == 'expected_cpu1'
    result = dict(state='publication_in_progress', phase_before=before,
                  phase_after=after, identity_seen=expected,
                  identity_recorded=before in IDENTITY_PHASES,
                  complete=False, exception_level=None, error=None,
                  **identity, **dict.fromkeys(CACHE_KEYS))
    if before in IDENTITY_PHASES and not expected:
        result.update(state='unexpected_identity_phase_seen',
                      error='unexpected_recorder_identity')
        return result
    if before != after:
        return result
    states = {0: 'no_recorder_publication_seen', 1: 'pre_mrs_entry_phase_seen',
              2: 'identity_phase_seen', 3: 'before_sctlr_phase_seen',
              4: 'recorder_complete', 255: 'unsupported_el_phase_seen'}
    result['state'] = states[before]
    if before in (3, 4):
        if current_el not in (4, 8, 12):
            result['error'] = 'committed_recorder_el_invalid'
            return result
        result['exception_level'] = current_el // 4
    if before == 255:
        result['error'] = ('unsupported_el_phase_inconsistent' if current_el in (4, 8, 12)
                           else 'unsupported_recorder_el')
    elif before == 4:
        result.update(complete=True, mmu_enabled=bool(sctlr & 1),
                      data_cache_enabled=bool(sctlr & 4),
                      instruction_cache_enabled=bool(sctlr & (1 << 12)))
    return result


def sample(read64, image_base):
    """Five fixed reads unless an earlier read fails; no retries."""
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
            raise TelemetryError('recorder_read_failed', reads_attempted=len(words) + 1,
                                 reads_completed=len(words),
                                 phase_before=words[0] if words and words[0] in PHASES else None) from None
        if not _u64(word):
            raise TelemetryError('invalid_read64_result', reads_attempted=len(words) + 1,
                                 reads_completed=len(words),
                                 phase_before=words[0] if words and words[0] in PHASES else None)
        words.append(word)
        if len(words) == 1 and word not in PHASES:
            raise TelemetryError('unknown_recorder_phase', reads_attempted=1, reads_completed=1)
    try:
        result = classify(words)
    except TelemetryError as error:
        raise TelemetryError(error.reason, reads_attempted=READS_PER_SAMPLE,
                             reads_completed=READS_PER_SAMPLE,
                             phase_before=words[0] if words[0] in PHASES else None,
                             phase_after=words[-1] if words[-1] in PHASES else None) from None
    result.update(reads_attempted=READS_PER_SAMPLE, reads_completed=READS_PER_SAMPLE)
    return result


class Tracker:
    """Caller-directed observations with sticky diagnostics and a read budget.

    A failed read can retain a recognized phase and identity classification,
    explicitly marked as an incomplete sample. It cannot manufacture completion.
    Later failures preserve earlier successful evidence but close the tracker.
    """
    def __init__(self, *, max_samples=MAX_SAMPLES):
        if type(max_samples) is not int or not 1 <= max_samples <= MAX_SAMPLES:
            raise TelemetryError('invalid_sample_limit')
        self._limit = max_samples
        self._attempts = self._completed = 0
        self._reads_attempted = self._reads_completed = 0
        self._highest = self._last_after = None
        self._identity = False
        self._identity_recorded = False
        self._identity_fields = identity_classification()
        self._identity_sample_complete = False
        self._el = self._complete = None
        self._last_state = 'not_sampled'
        self._error = None
        self._active = False

    def _phase(self, phase):
        if phase is not None and phase in PHASES:
            if self._highest is None or phase > self._highest:
                self._highest = phase

    def _retain_identity(self, fields, *, complete_sample):
        if fields['identity_status'] != 'not_committed':
            self._identity_fields = {key: fields[key] for key in IDENTITY_KEYS}
            self._identity_recorded = True
            self._identity |= fields['identity_status'] == 'expected_cpu1'
            self._identity_sample_complete = complete_sample

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
        local_words = []
        pending_identity = None

        def guarded(address):
            nonlocal pending_identity
            if self._error is not None:
                raise TelemetryError('recorder_tracker_closed')
            self._reads_attempted += 1
            word = read64(address)
            if _u64(word):
                self._reads_completed += 1
                if len(local_words) in (0, 4) and word in PHASES:
                    self._phase(word)
                if len(local_words) == 1 and local_words[0] in IDENTITY_PHASES:
                    pending_identity = identity_classification(word)
            local_words.append(word)
            if self._error is not None:
                raise TelemetryError('recorder_tracker_closed')
            return word

        try:
            result = sample(guarded, image_base)
            self._phase(result['phase_before']); self._phase(result['phase_after'])
            self._retain_identity(result, complete_sample=True)
            self._completed += 1
            self._last_state = result['state']
            if (self._last_after is not None and
                    result['phase_before'] not in _ALLOWED_AFTER[self._last_after]):
                raise TelemetryError('recorder_cross_sample_regression')
            if result['error'] is not None:
                raise TelemetryError(result['error'])
            if self._el is not None and (
                    result['exception_level'] is not None and result['exception_level'] != self._el or
                    result['phase_before'] == result['phase_after'] == 255):
                raise TelemetryError('committed_recorder_el_changed')
            if self._complete is not None and (not result['complete'] or any(
                    result[key] != self._complete[key] for key in CACHE_KEYS)):
                raise TelemetryError('completed_recorder_changed')
            self._last_after = result['phase_after']
            if result['exception_level'] is not None:
                self._el = result['exception_level']
            if result['complete']:
                self._complete = result
        except (KeyboardInterrupt, SystemExit):
            if pending_identity is not None:
                self._retain_identity(pending_identity, complete_sample=False)
            self._error = 'recorder_read_interrupted'
            raise
        except TelemetryError as error:
            self._phase(error.phase_before); self._phase(error.phase_after)
            if pending_identity is not None and len(local_words) < READS_PER_SAMPLE:
                self._retain_identity(pending_identity, complete_sample=False)
            if self._error is None:
                self._error = error.reason
        finally:
            self._active = False
        return self.report()

    def report(self):
        result = dict(state=self._last_state, samples_attempted=self._attempts,
                      samples_completed=self._completed,
                      reads_attempted=self._reads_attempted,
                      reads_completed=self._reads_completed,
                      highest_phase_seen=self._highest, identity_seen=self._identity,
                      identity_recorded=self._identity_recorded,
                      identity_sample_complete=self._identity_sample_complete,
                      complete=self._complete is not None, error=self._error,
                      closed=self._error is not None, exception_level=self._el,
                      **self._identity_fields)
        for key in CACHE_KEYS:
            result[key] = self._complete[key] if self._complete else None
        return result
