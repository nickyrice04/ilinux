# SPDX-License-Identifier: MIT
"""Bounded CPU implementation-window observations; no I/O or target code.

Source scope: public m1n1 57a9339ffd1876e78297b17d34dece8cff8fa1ba,
src/hv/hv.c:42-88 accepts a four-byte access at cpu-impl-reg + 0x100 and
filters its low byte when a guest has not started the corresponding CPU.
src/smp.c:244-249 polls the low byte with a 64-bit read during non-deep stop.
Neither source establishes t6050 reset, execution, PC or running-state bits.
This component deliberately reports only an uninterpreted low-byte value.

The caller must bind these two addresses to the live ADT, validate mapping and
access width, and choose the transport. Intended integration uses a guarded
32-bit baseline before CPU1 starts, then a reviewed guard-free 32-bit helper.
The component never selects a transport, reads a register or authorizes a boot.

sample(phase, read32, persist) calls read32(cpu_id), once per CPU in fixed
order. persist receives a defensive sanitized snapshot before each read and
after each validated result. Any protocol, read, decode or journal failure
freezes the tracker. A successful callback is the caller's durability contract.
"""
from copy import deepcopy

SOURCE_COMMIT = '57a9339ffd1876e78297b17d34dece8cff8fa1ba'
REGISTER_OFFSET = 0x100
READ_BYTES = 4
ADDRESSES = (0x210050100, 0x210150100)
PHASES = ('before_start', 'after_first_start', 'after_second_start', 'final')
MAX_READS = 8
INVALID_WORDS = (0xffffffff, 0xbad0bad0)


class ObservationError(ValueError):
    """Fixed non-identifying reason; transport and raw values are never echoed."""


def address(cpu):
    if type(cpu) is not int or cpu not in (0, 1):
        raise ObservationError('cpu_state_cpu_id')
    return ADDRESSES[cpu]


def low_byte(word):
    if type(word) is not int or not 0 <= word < 1 << 32:
        raise ObservationError('cpu_state_word_type_or_width')
    if word in INVALID_WORDS:
        raise ObservationError('cpu_state_invalid_word')
    return word & 0xff  # Zero is a legitimate observation, not a sentinel.


class Tracker:
    def __init__(self):
        self._rows = []
        self._attempts = self._completed = 0
        self._error = None
        self._active = False
        self._journal_failed = False

    def report(self):
        return deepcopy(dict(
            samples=self._rows, reads_attempted=self._attempts,
            reads_completed=self._completed, error=self._error,
            journal_failed=self._journal_failed,
            entry_execution='NOT_ESTABLISHED', reset_release='NOT_ESTABLISHED',
            running_state='NOT_ESTABLISHED', program_counter='NOT_OBSERVED',
            t6050_register_semantics='UNKNOWN'))

    def _freeze(self, reason):
        if self._error is None:
            self._error = reason

    def _emit(self, persist, *, terminal=False):
        try:
            persist(self.report())
        except BaseException as exc:
            self._journal_failed = True
            self._freeze('cpu_state_journal_failed')
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise ObservationError(self._error) from None
        # A callback may have attempted reentrant sampling and swallowed its
        # refusal. That still closes this tracker before any further read.
        if self._error is not None and not terminal:
            raise ObservationError(self._error)

    def _fail(self, reason, persist):
        self._freeze(reason)
        self._emit(persist, terminal=True)
        raise ObservationError(self._error) from None

    def sample(self, phase, read32, persist):
        if self._error is not None:
            raise ObservationError(self._error)
        if self._active:
            # Do not invoke persist recursively from its own callback.
            self._freeze('cpu_state_reentrant_sample')
            raise ObservationError(self._error)
        if not callable(persist):
            self._freeze('cpu_state_persist_not_callable')
            raise ObservationError(self._error)
        if not callable(read32):
            self._fail('cpu_state_reader_not_callable', persist)
        if (type(phase) is not str or len(self._rows) >= len(PHASES) or
                phase != PHASES[len(self._rows)]):
            self._fail('cpu_state_sample_order', persist)

        self._active = True
        row = dict(phase=phase, complete=False, cpu0=None, cpu1=None,
                   cores_equal=None)
        self._rows.append(row)
        try:
            for cpu in (0, 1):
                if self._attempts >= MAX_READS:
                    self._fail('cpu_state_read_budget', persist)
                self._attempts += 1
                self._emit(persist)  # Durable intent precedes dispatch.
                try:
                    value = read32(cpu)
                except (KeyboardInterrupt, SystemExit):
                    self._freeze('cpu_state_read_interrupted')
                    try:
                        self._emit(persist, terminal=True)
                    except BaseException:
                        pass  # Preserve the original operator interruption.
                    raise
                except Exception:
                    self._fail('cpu_state_read_failed', persist)
                if self._error is not None:
                    # A reader can also attempt a nested sample.
                    self._fail(self._error, persist)
                try:
                    low = low_byte(value)
                except ObservationError as exc:
                    self._fail(str(exc), persist)
                # No full word is retained in tracker state or a report.
                baseline = (None if phase == PHASES[0] else
                            self._rows[0]['cpu' + str(cpu)]['low_byte'])
                row['cpu' + str(cpu)] = dict(
                    low_byte=low,
                    changed_from_baseline=None if baseline is None else low != baseline)
                self._completed += 1
                self._emit(persist)
            row['cores_equal'] = row['cpu0']['low_byte'] == row['cpu1']['low_byte']
            row['complete'] = True
            self._emit(persist)
            return self.report()
        finally:
            self._active = False
