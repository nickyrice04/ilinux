# SPDX-License-Identifier: MIT
"""Retain sanitized evidence from the census's existing two guarded reads.

This adapter never initiates a proxy transaction itself. Its caller substitutes
it for one controller's proxy during preflight, then restores that proxy in a
finally block. The existing census supplies get_base(), read64() and the
immediately following get_exc_count(). No global module patch is needed.

The retained legacy classification and matching firmware writer's bits41:11
format are separate views. Neither establishes an effective reset destination.
Raw words exist only transiently for comparison; reports contain no addresses.
"""
from copy import deepcopy


RVBAR = (0x210050000, 0x210150000)
PAGE_MASK = ((1 << 48) - 1) & ~0xfff
LOW_UNKNOWN_MASK = 0xffe
HIGH_UNKNOWN_MASK = ((1 << 64) - 1) ^ ((1 << 48) - 1)
INVALID_WORDS = (0, (1 << 64) - 1, 0xbad0bad0bad0bad0)
# Behavioral format supplied by the matching firmware-writer investigation.
# Its sole observed caller aligns the entry to 4 KiB. A field matching +0x800
# is therefore a diagnostic distinction, not a claim that it is the live PC.
FIRMWARE_ADDRESS_MASK = 0x3fffffff800
FIRMWARE_LOW_OUTSIDE_MASK = 0x7fe
FIRMWARE_HIGH_OUTSIDE_MASK = ((1 << 64) - 1) ^ ((1 << 42) - 1)
FIRMWARE_LEGACY_HIGH_OUTSIDE_MASK = ((1 << 48) - 1) ^ ((1 << 42) - 1)


class ObservationError(ValueError):
    """Only fixed non-identifying reason strings are emitted."""


def validate_base(base):
    if type(base) is not int or not 0 < base < 1 << 42 or base % 0x4000:
        raise ObservationError('rvbar_image_base_invalid')


def classify(word, base):
    validate_base(base)
    if type(word) is not int or not 0 <= word < 1 << 64:
        raise ObservationError('rvbar_word_type_or_width')
    if word in INVALID_WORDS:
        raise ObservationError('rvbar_invalid_word')
    low = word & LOW_UNKNOWN_MASK
    firmware_field = word & FIRMWARE_ADDRESS_MASK
    return {
        'legacy_page_field_matches_vectors': (word & PAGE_MASK) == base,
        'legacy_lock_bit0': bool(word & 1),
        'unknown_low_bits_class': ('zero' if low == 0 else
                                  'bit11_only' if low == 0x800 else 'other'),
        'bit11_set': bool(word & 0x800),
        'unknown_upper_bits_present': bool(word & HIGH_UNKNOWN_MASK),
        'firmware_format_field_relation': (
            'image_base' if firmware_field == base else
            'image_base_plus_0x800' if firmware_field == base + 0x800 else 'other'),
        'firmware_format_low_bits_10_1_class': (
            'nonzero' if word & FIRMWARE_LOW_OUTSIDE_MASK else 'zero'),
        'firmware_format_high_bits_63_42_class': (
            'nonzero' if word & FIRMWARE_HIGH_OUTSIDE_MASK else 'zero'),
        'firmware_format_bits_47_42_class': (
            'nonzero' if word & FIRMWARE_LEGACY_HIGH_OUTSIDE_MASK else 'zero'),
    }


class ProxyObserver:
    """Observe, without adding calls, one ordered CPU0/CPU1 census pair.

    journal receives independent sanitized report dictionaries. A report row
    is committed only after the corresponding exception-count reply is the
    integer zero. A failure freezes evidence and prevents further proxied
    calls. finish() is local validation and sends no command. Call abort()
    when inherited preflight fails elsewhere, to erase transient words while
    retaining an already validated prefix.
    """

    def __init__(self, proxy, journal=None):
        self._proxy = proxy
        self._journal = journal if journal is not None else lambda report: None
        self._base = None
        self._pending_cpu = None
        self._pending_word = None
        self._first_word = None
        self._rows = []
        self._attempts = 0
        self._returns = 0
        self._guard_checks = 0
        self._mirrors_equal = None
        self._error = None

    def report(self):
        return deepcopy({
            'state': ('error' if self._error else
                      'complete' if len(self._rows) == 2 else 'collecting'),
            'read_attempts': self._attempts,
            'read_returns': self._returns,
            'guard_check_attempts': self._guard_checks,
            'validated_reads': len(self._rows),
            'pending_cpu_id': self._pending_cpu,
            'rows': self._rows,
            'mirrors_equal': self._mirrors_equal,
            'exact_entry_offset': 'UNKNOWN',
            'effective_reset_route': 'UNKNOWN',
            'error': self._error,
        })

    def _clear_private(self):
        self._pending_cpu = self._pending_word = self._first_word = None

    def _emit(self):
        try:
            self._journal(self.report())
        except BaseException as exc:
            if self._error is None:
                self._error = 'rvbar_journal_failed'
            self._clear_private()
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise ObservationError(self._error) from None

    def _fail(self, reason):
        if self._error is None:
            self._error = reason
            self._clear_private()
            self._emit()
        raise ObservationError(self._error) from None

    def _before(self, name):
        if self._error:
            raise ObservationError(self._error)
        if self._pending_cpu is not None and name != 'get_exc_count':
            self._fail('rvbar_exception_ack_not_immediate')

    def _critical_call(self, name, reason, *args):
        try:
            return getattr(self._proxy, name)(*args)
        except (KeyboardInterrupt, SystemExit):
            if self._error is None:
                self._error = 'rvbar_proxy_interrupted'
                self._clear_private()
                self._emit()
            raise
        except Exception:
            self._fail(reason)

    def get_base(self, *args, **kwargs):
        self._before('get_base')
        # This is the caller's existing command, never an additional query.
        base = self._proxy.get_base(*args, **kwargs)
        try:
            validate_base(base)
        except ObservationError as exc:
            self._fail(str(exc))
        if self._base is not None and self._base != base:
            self._fail('rvbar_image_base_changed')
        self._base = base
        return base

    def read64(self, address, *args, **kwargs):
        self._before('read64')
        if address not in RVBAR:
            return self._proxy.read64(address, *args, **kwargs)
        if type(address) is not int or args or kwargs:
            self._fail('rvbar_read_signature')
        if self._base is None:
            self._fail('rvbar_image_base_missing')
        if self._attempts >= 2 or address != RVBAR[self._attempts]:
            self._fail('rvbar_read_order_or_count')
        self._pending_cpu = self._attempts
        self._attempts += 1
        self._emit()  # The read intent is durable before transport dispatch.
        word = self._critical_call('read64', 'rvbar_read_failed', address)
        self._returns += 1
        self._pending_word = word
        self._emit()
        # Preserve the frozen census sequence: it checks exceptions before
        # interpreting even a sentinel or malformed read result.
        return word

    def get_exc_count(self, *args, **kwargs):
        self._before('get_exc_count')
        if self._pending_cpu is None:
            return self._proxy.get_exc_count(*args, **kwargs)
        if args or kwargs:
            self._fail('rvbar_exception_ack_signature')
        self._guard_checks += 1
        self._emit()
        count = self._critical_call('get_exc_count', 'rvbar_exception_ack_failed')
        if type(count) is not int or count != 0:
            self._fail('rvbar_exception_ack_nonzero_or_invalid')
        try:
            row = classify(self._pending_word, self._base)
        except ObservationError as exc:
            self._fail(str(exc))
        cpu = self._pending_cpu
        self._rows.append({'cpu_id': cpu, **row})
        if cpu == 0:
            self._first_word = self._pending_word
        else:
            self._mirrors_equal = self._first_word == self._pending_word
            self._first_word = None
        self._pending_cpu = self._pending_word = None
        self._emit()
        return count

    def finish(self):
        self._before('finish')
        if len(self._rows) != 2 or self._attempts != 2 or self._guard_checks != 2:
            self._fail('rvbar_observation_incomplete')
        return self.report()

    def abort(self):
        """Local cleanup after a failure outside the intercepted read pair."""
        newly_aborted = self._error is None and len(self._rows) != 2
        if newly_aborted:
            self._error = 'rvbar_preflight_aborted'
        self._clear_private()
        if newly_aborted:
            self._emit()
        return self.report()

    def __getattr__(self, name):
        member = getattr(self._proxy, name)
        if not callable(member):
            return member

        def forward(*args, **kwargs):
            self._before(name)
            return member(*args, **kwargs)

        return forward
