# SPDX-License-Identifier: MIT
"""Pure frame/clock/failure tests, with no platform or device operations."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('lease31ay', Path(__file__).with_name('lease.py'))
lease = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lease)


def frame(sequence):
    return ('ILINUX31AY %d\n' % sequence).encode()


class LeaseTests(unittest.TestCase):
    def test_fresh_renewals_cannot_extend_fixed_deadline(self):
        state = lease.Lease(100)
        for seq in range(1, 141):
            self.assertEqual(state.accept(frame(seq), 100 + (seq - 1) * 500),
                             ('ONE_KEEPALIVE_ELIGIBLE', None))
        self.assertEqual(state.hard_ms, 70100)
        self.assertEqual(state.check(70100), ('STOP_RENEWAL', 'HARD_DEADLINE'))
        self.assertEqual(lease.CONDITIONAL_RESET_BOUND_MS, 90000)

    def test_polling_is_never_a_keepalive(self):
        state = lease.Lease(0)
        self.assertEqual(state.check(100), ('WAIT_NO_KEEPALIVE', None))
        self.assertEqual(state.sequence, 0)

    def test_no_initial_host_and_expired_host_lease_stop(self):
        state = lease.Lease(0)
        self.assertEqual(state.check(3000), ('STOP_RENEWAL', 'HOST_LEASE_EXPIRED'))
        state = lease.Lease(0)
        state.accept(frame(1), 10)
        self.assertEqual(state.accept(frame(2), 3010), ('STOP_RENEWAL', 'HOST_LEASE_EXPIRED'))

    def test_expired_gate_never_rearms_on_valid_packet(self):
        state = lease.Lease(0)
        first = state.check(3001)
        self.assertEqual(state.accept(frame(1), 3002), first)
        self.assertEqual(state.sequence, 0)

    def test_clock_regression_invalid_values_and_overflow_refuse(self):
        for value in (-1, True, 1.5, '0', None, (1 << 63) - 1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    lease.Lease(value)
        for value in (-1, True, None, 9):
            state = lease.Lease(10)
            self.assertEqual(state.accept(frame(1), value)[0], 'STOP_RENEWAL')
        state = lease.Lease(0)
        state.check(500)
        self.assertEqual(state.accept(frame(1), 499), ('STOP_RENEWAL', 'CLOCK_INVALID_OR_REGRESSED'))

    def test_health_failure_is_terminal(self):
        for value in (False, None, 1, 'true'):
            state = lease.Lease(0)
            result = state.accept(frame(1), 0, healthy=value)
            self.assertEqual(result, ('STOP_RENEWAL', 'HEALTH_NOT_CONFIRMED'))
            self.assertEqual(state.accept(frame(1), 1), result)

    def test_duplicates_gaps_old_and_excess_sequences_refuse(self):
        for bad in (1, 3, 0, 161):
            state = lease.Lease(0)
            state.accept(frame(1), 0)
            self.assertEqual(state.accept(frame(bad), 500)[0], 'STOP_RENEWAL')
        state = lease.Lease(0)
        self.assertEqual(state.accept(frame(2), 0), ('STOP_RENEWAL', 'LEASE_SEQUENCE'))

    def test_buffered_burst_cannot_renew_indefinitely(self):
        state = lease.Lease(0)
        state.accept(frame(1), 0)
        result = state.accept(frame(2), 1)
        self.assertEqual(result, ('STOP_RENEWAL', 'RENEWAL_BURST'))
        self.assertEqual(state.accept(frame(2), 500), result)

    def test_malformed_extra_and_oversized_frames_refuse(self):
        for data in (b'', b'ILINUX31AY 01\n', b'ILINUX31AY -1\n', b'ILINUX31AY 1',
                     b'ILINUX31AY 1\r\n', b'ILINUX31AY 1\nILINUX31AY 2\n',
                     b'ILINUX31AY 1\0\n', b'ILINUX31AY 1\nextra', b'X' * 33,
                     b'\xff\n', 'ILINUX31AY 1\n', None):
            with self.subTest(data=data):
                self.assertEqual(lease.Lease(0).accept(data, 0)[0], 'STOP_RENEWAL')

    def test_final_two_intervals_include_single_release_ping(self):
        # Model only: last allowed pet <70s, then at most one close before
        # that physical expiry (<80s), then its final expiry remains <90s.
        for last_pet in (0, 69999):
            first_expiry = last_pet + lease.HARDWARE_BUDGET_MS
            for close in (last_pet, first_expiry - 1):
                self.assertLess(close + lease.HARDWARE_BUDGET_MS,
                                lease.CONDITIONAL_RESET_BOUND_MS)


if __name__ == '__main__':
    unittest.main()
