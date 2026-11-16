# SPDX-License-Identifier: MIT
"""Pure finite eligibility gate; never opens, pings or stops a watchdog.

A future Linux adapter must supply qualified monotonic timestamps, exclusive
verified physical watchdog ownership and an authenticated one-session stream.
These decisions alone establish none of those hardware/transport properties.
"""
import re

LEASE_MS = 3000
MIN_SPACING_MS = 500
PET_BUDGET_MS = 70000
HARDWARE_BUDGET_MS = 10000
CONDITIONAL_RESET_BOUND_MS = PET_BUDGET_MS + 2 * HARDWARE_BUDGET_MS
MAX_FRAME_BYTES = 32
FRAME = re.compile(rb'ILINUX31AY ([1-9][0-9]{0,2})\n\Z', re.ASCII)


def valid_time(value):
    return type(value) is int and 0 <= value <= (1 << 63) - 1


class Lease:
    def __init__(self, arm_ms):
        if not valid_time(arm_ms) or arm_ms > (1 << 63) - 1 - CONDITIONAL_RESET_BOUND_MS:
            raise ValueError('INVALID_MONOTONIC_ARM_TIME')
        self.arm_ms = arm_ms
        self.observed_ms = arm_ms
        self.hard_ms = arm_ms + PET_BUDGET_MS
        self.lease_ms = arm_ms + LEASE_MS
        self.previous_pet_ms = None
        self.sequence = 0
        self.stop_reason = None

    def _stop(self, reason):
        if self.stop_reason is None:
            self.stop_reason = reason
        return 'STOP_RENEWAL', self.stop_reason

    def check(self, now_ms, healthy=True):
        """Poll with caller-owned time/health; a terminal stop cannot recover."""
        if self.stop_reason is not None:
            return 'STOP_RENEWAL', self.stop_reason
        if not valid_time(now_ms) or now_ms < self.observed_ms:
            return self._stop('CLOCK_INVALID_OR_REGRESSED')
        self.observed_ms = now_ms
        if healthy is not True:
            return self._stop('HEALTH_NOT_CONFIRMED')
        if now_ms >= self.hard_ms:
            return self._stop('HARD_DEADLINE')
        if now_ms >= self.lease_ms:
            return self._stop('HOST_LEASE_EXPIRED')
        return 'WAIT_NO_KEEPALIVE', None

    def accept(self, frame, now_ms, healthy=True):
        """Only a fresh complete frame permits one future UAPI keepalive."""
        action, reason = self.check(now_ms, healthy)
        if action == 'STOP_RENEWAL':
            return action, reason
        if not isinstance(frame, bytes) or not 1 <= len(frame) <= MAX_FRAME_BYTES:
            return self._stop('INVALID_LEASE_FRAME')
        match = FRAME.fullmatch(frame)
        if not match:
            return self._stop('INVALID_LEASE_FRAME')
        sequence = int(match.group(1))
        if sequence != self.sequence + 1 or sequence > 160:
            return self._stop('LEASE_SEQUENCE')
        if self.previous_pet_ms is not None and now_ms - self.previous_pet_ms < MIN_SPACING_MS:
            return self._stop('RENEWAL_BURST')
        self.sequence = sequence
        self.previous_pet_ms = now_ms
        self.lease_ms = min(self.hard_ms, now_ms + LEASE_MS)
        return 'ONE_KEEPALIVE_ELIGIBLE', None
