# SPDX-License-Identifier: MIT
"""Wire-sequence, failure and publication checks; synthetic values only."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('observer', Path(__file__).with_name('observer.py'))
o = importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
BASE = 1 << 40


class Proxy:
    def __init__(self, words=(BASE | 1, BASE | 0x801)):
        self.words = iter(words)
        self.calls = []
        self.base = BASE
        self.fail_read = self.fail_ack = None
        self.reads = self.acks = 0
        self.count = 0
        self.metadata = object()

    def get_base(self):
        self.calls.append(('get_base',))
        return self.base

    def read64(self, address, *args, **kwargs):
        self.calls.append(('read64', address, args, kwargs))
        if address not in o.RVBAR:
            return 73
        self.reads += 1
        if self.reads == self.fail_read:
            raise TimeoutError('private raw transport detail')
        return next(self.words)

    def get_exc_count(self):
        self.calls.append(('get_exc_count',))
        self.acks += 1
        if self.acks == self.fail_ack:
            raise TimeoutError('private raw acknowledgment detail')
        return self.count

    def arbitrary(self, *args, **kwargs):
        self.calls.append(('arbitrary', args, kwargs))
        return self.metadata

    def raises(self):
        raise LookupError('ordinary forwarding')


def pair(observer, cpu):
    observer.read64(o.RVBAR[cpu])
    observer.get_exc_count()


class ObserverTests(unittest.TestCase):
    def setup_observer(self, words=(BASE | 1, BASE | 0x801), journal=None):
        proxy = Proxy(words)
        observer = o.ProxyObserver(proxy, journal)
        observer.get_base()
        return proxy, observer

    def test_success_has_exact_existing_wire_sequence(self):
        proxy, observer = self.setup_observer()
        pair(observer, 0)
        pair(observer, 1)
        result = observer.finish()
        self.assertEqual(proxy.calls, [
            ('get_base',), ('read64', o.RVBAR[0], (), {}), ('get_exc_count',),
            ('read64', o.RVBAR[1], (), {}), ('get_exc_count',)])
        self.assertEqual((result['read_attempts'], result['read_returns'],
                          result['validated_reads'], result['guard_check_attempts']), (2, 2, 2, 2))
        self.assertEqual(result['state'], 'complete')
        self.assertFalse(result['mirrors_equal'])
        self.assertEqual([r['unknown_low_bits_class'] for r in result['rows']],
                         ['zero', 'bit11_only'])
        self.assertTrue(all(r['legacy_page_field_matches_vectors'] for r in result['rows']))
        self.assertEqual(result['exact_entry_offset'], 'UNKNOWN')
        self.assertEqual(result['effective_reset_route'], 'UNKNOWN')

    def test_no_result_published_until_exception_ack(self):
        reports = []
        proxy, observer = self.setup_observer(journal=reports.append)
        observer.read64(o.RVBAR[0])
        self.assertTrue(all(r['rows'] == [] for r in reports))
        self.assertEqual(reports[0]['read_attempts'], 1)
        self.assertEqual(reports[0]['read_returns'], 0)
        self.assertEqual(observer.report()['pending_cpu_id'], 0)
        observer.get_exc_count()
        self.assertEqual(observer.report()['validated_reads'], 1)
        self.assertIsNone(observer.report()['mirrors_equal'])

    def test_bounded_unknown_fields_and_mirror_equality(self):
        for first, second, equal in (
                (BASE | 0x805, BASE | 0x805, True),
                (BASE | 0x805, BASE | 0x809, False)):
            proxy, observer = self.setup_observer((first | (1 << 63), second | (1 << 63)))
            pair(observer, 0)
            pair(observer, 1)
            result = observer.finish()
            self.assertEqual(result['mirrors_equal'], equal)
            self.assertTrue(all(r['unknown_upper_bits_present'] for r in result['rows']))
            self.assertTrue(all(r['bit11_set'] for r in result['rows']))
            self.assertTrue(all(r['unknown_low_bits_class'] == 'other' for r in result['rows']))

    def test_firmware_field_distinguishes_bit11_without_effective_entry_claim(self):
        proxy, observer = self.setup_observer()
        pair(observer, 0)
        pair(observer, 1)
        report = observer.finish()
        self.assertEqual([r['firmware_format_field_relation'] for r in report['rows']],
                         ['image_base', 'image_base_plus_0x800'])
        self.assertTrue(all(r['firmware_format_low_bits_10_1_class'] == 'zero'
                            for r in report['rows']))
        self.assertEqual(report['exact_entry_offset'], 'UNKNOWN')
        self.assertEqual(report['effective_reset_route'], 'UNKNOWN')
        other = o.classify(BASE | 0x1001, BASE)
        self.assertEqual(other['firmware_format_field_relation'], 'other')

    def test_firmware_bit41_in_address_field_bit42_outside_it(self):
        inside = o.classify((1 << 41) | 1, 1 << 41)
        self.assertEqual(inside['firmware_format_field_relation'], 'image_base')
        self.assertEqual(inside['firmware_format_high_bits_63_42_class'], 'zero')
        self.assertTrue(inside['legacy_page_field_matches_vectors'])
        outside = o.classify(BASE | (1 << 42) | 1, BASE)
        self.assertEqual(outside['firmware_format_field_relation'], 'image_base')
        self.assertEqual(outside['firmware_format_high_bits_63_42_class'], 'nonzero')
        self.assertEqual(outside['firmware_format_bits_47_42_class'], 'nonzero')
        self.assertFalse(outside['legacy_page_field_matches_vectors'])
        self.assertFalse(outside['unknown_upper_bits_present'])

    def test_firmware_outside_fields_are_bounded_not_discarded(self):
        for bit in range(1, 11):
            row = o.classify(BASE | 1 | (1 << bit), BASE)
            self.assertEqual(row['firmware_format_low_bits_10_1_class'], 'nonzero')
            self.assertEqual(row['firmware_format_field_relation'], 'image_base')
        for bit in range(42, 64):
            row = o.classify(BASE | 1 | (1 << bit), BASE)
            self.assertEqual(row['firmware_format_high_bits_63_42_class'], 'nonzero')
            self.assertEqual(row['firmware_format_bits_47_42_class'],
                             'nonzero' if bit <= 47 else 'zero')
            self.assertEqual(row['firmware_format_field_relation'], 'image_base')

    def test_firmware_base_must_fit_without_truncation(self):
        for base in (None, True, False, 0, -1, BASE + 1, 1 << 42, 1 << 48):
            with self.assertRaisesRegex(o.ObservationError, '^rvbar_image_base_invalid$'):
                o.classify(BASE | 1, base)

    def test_read_failures_preserve_completed_prefix_and_freeze(self):
        for failed_cpu in (0, 1):
            proxy, observer = self.setup_observer()
            proxy.fail_read = failed_cpu + 1
            if failed_cpu:
                pair(observer, 0)
            with self.assertRaisesRegex(o.ObservationError, '^rvbar_read_failed$'):
                pair(observer, failed_cpu)
            report = observer.report()
            self.assertEqual(report['validated_reads'], failed_cpu)
            self.assertIsNone(report['mirrors_equal'])
            calls = list(proxy.calls)
            with self.assertRaises(o.ObservationError):
                observer.arbitrary()
            self.assertEqual(proxy.calls, calls)
            self.assertEqual(observer.report(), report)

    def test_lost_acknowledgment_never_commits_unchecked_word(self):
        for failed_cpu in (0, 1):
            proxy, observer = self.setup_observer()
            proxy.fail_ack = failed_cpu + 1
            if failed_cpu:
                pair(observer, 0)
            with self.assertRaisesRegex(o.ObservationError, '^rvbar_exception_ack_failed$'):
                pair(observer, failed_cpu)
            self.assertEqual(observer.report()['validated_reads'], failed_cpu)
            self.assertEqual(observer.report()['read_returns'], failed_cpu + 1)
            self.assertIsNone(observer._pending_word)
            self.assertIsNone(observer._first_word)

    def test_exception_ack_requires_integer_zero(self):
        for count in (True, False, None, '0', 1, -1, 1 << 64):
            proxy, observer = self.setup_observer()
            proxy.count = count
            with self.assertRaisesRegex(o.ObservationError, '^rvbar_exception_ack_nonzero_or_invalid$'):
                pair(observer, 0)
            self.assertEqual(observer.report()['rows'], [])

    def test_bad_words_rejected_after_ack_and_before_next_read(self):
        for word in (None, True, False, '0', -1, 1 << 64, *o.INVALID_WORDS):
            proxy, observer = self.setup_observer((word, BASE | 1))
            with self.assertRaises(o.ObservationError):
                pair(observer, 0)
            self.assertEqual(proxy.reads, 1)
            self.assertEqual(proxy.acks, 1)
            self.assertEqual(observer.report()['rows'], [])

    def test_wrong_order_or_duplicate_refused_before_dispatch(self):
        proxy, observer = self.setup_observer()
        with self.assertRaisesRegex(o.ObservationError, '^rvbar_read_order_or_count$'):
            observer.read64(o.RVBAR[1])
        self.assertEqual(proxy.reads, 0)
        proxy, observer = self.setup_observer()
        pair(observer, 0)
        pair(observer, 1)
        with self.assertRaisesRegex(o.ObservationError, '^rvbar_read_order_or_count$'):
            observer.read64(o.RVBAR[0])
        self.assertEqual(proxy.reads, 2)

    def test_ack_must_be_next_proxied_call_even_for_cached_method(self):
        for next_call in (lambda ob: ob.read64(100), lambda ob: ob.get_base(),
                          lambda ob: ob.arbitrary(), lambda ob: ob.finish()):
            proxy, observer = self.setup_observer()
            cached = observer.arbitrary
            observer.read64(o.RVBAR[0])
            calls = list(proxy.calls)
            with self.assertRaisesRegex(o.ObservationError, '^rvbar_exception_ack_not_immediate$'):
                next_call(observer)
            with self.assertRaises(o.ObservationError):
                cached()
            self.assertEqual(proxy.calls, calls)

    def test_existing_unrelated_proxy_behavior_forwarded(self):
        proxy, observer = self.setup_observer()
        self.assertIs(observer.metadata, proxy.metadata)
        self.assertIs(observer.arbitrary(3, keyword=7), proxy.metadata)
        self.assertEqual(observer.read64(100, 9, extra=True), 73)
        with self.assertRaisesRegex(LookupError, 'ordinary forwarding'):
            observer.raises()
        self.assertEqual(observer.get_exc_count(), 0)  # Existing pre-census check.
        self.assertEqual(observer.report()['guard_check_attempts'], 0)
        self.assertEqual(observer.report()['read_attempts'], 0)

    def test_base_missing_malformed_or_changed_refused(self):
        observer = o.ProxyObserver(Proxy())
        with self.assertRaisesRegex(o.ObservationError, '^rvbar_image_base_missing$'):
            observer.read64(o.RVBAR[0])
        for bad in (None, True, 0, -1, 1 << 42, 1 << 48, BASE + 1):
            proxy = Proxy()
            proxy.base = bad
            with self.assertRaisesRegex(o.ObservationError, '^rvbar_image_base_invalid$'):
                o.ProxyObserver(proxy).get_base()
        proxy, observer = self.setup_observer()
        proxy.base += 0x4000
        with self.assertRaisesRegex(o.ObservationError, '^rvbar_image_base_changed$'):
            observer.get_base()

    def test_reports_and_journal_snapshots_are_independent(self):
        reports = []
        proxy, observer = self.setup_observer(journal=reports.append)
        pair(observer, 0)
        before = observer.report()
        pair(observer, 1)
        self.assertEqual(before['validated_reads'], 1)
        self.assertEqual(len(before['rows']), 1)
        reports[-1]['rows'][0]['cpu_id'] = 99
        result = observer.finish()
        result['rows'].clear()
        self.assertEqual([r['cpu_id'] for r in observer.report()['rows']], [0, 1])

    def test_journal_failure_prevents_transport_and_freezes(self):
        def broken(report):
            raise OSError('private path')
        proxy, observer = self.setup_observer(journal=broken)
        with self.assertRaisesRegex(o.ObservationError, '^rvbar_journal_failed$'):
            observer.read64(o.RVBAR[0])
        self.assertEqual(proxy.reads, 0)
        self.assertEqual(observer.report()['read_attempts'], 1)
        with self.assertRaises(o.ObservationError):
            observer.get_exc_count()
        self.assertEqual(proxy.acks, 0)

    def test_no_raw_words_addresses_or_transport_detail_in_report(self):
        reports = []
        proxy, observer = self.setup_observer(journal=reports.append)
        pair(observer, 0)
        proxy.fail_ack = 2
        with self.assertRaises(o.ObservationError):
            pair(observer, 1)
        encoded = json.dumps(reports + [observer.report()])
        for secret in (BASE, BASE | 1, BASE | 0x801, *o.RVBAR):
            self.assertNotIn(str(secret), encoded)
            self.assertNotIn(hex(secret), encoded)
        self.assertNotIn('private raw', encoded)

    def test_finish_requires_both_pairs_without_extra_calls(self):
        proxy, observer = self.setup_observer()
        pair(observer, 0)
        before = list(proxy.calls)
        with self.assertRaisesRegex(o.ObservationError, '^rvbar_observation_incomplete$'):
            observer.finish()
        self.assertEqual(proxy.calls, before)
        self.assertEqual(observer.report()['validated_reads'], 1)

    def test_external_failure_abort_erases_raw_comparison_and_retains_prefix(self):
        proxy, observer = self.setup_observer()
        pair(observer, 0)
        self.assertIsNotNone(observer._first_word)
        before = list(proxy.calls)
        result = observer.abort()
        self.assertIsNone(observer._first_word)
        self.assertIsNone(observer._pending_word)
        self.assertEqual(result['validated_reads'], 1)
        self.assertEqual(result['error'], 'rvbar_preflight_aborted')
        self.assertEqual(proxy.calls, before)
        self.assertEqual(observer.abort(), result)
        with self.assertRaises(o.ObservationError):
            observer.read64(o.RVBAR[1])
        self.assertEqual(proxy.calls, before)

    def test_unexpected_critical_call_arguments_do_not_dispatch(self):
        for extra in (lambda ob: ob.read64(o.RVBAR[0], 8),
                      lambda ob: ob.read64(o.RVBAR[0], width=8),
                      lambda ob: ob.read64(float(o.RVBAR[0]))):
            proxy, observer = self.setup_observer()
            with self.assertRaises(o.ObservationError):
                extra(observer)
            self.assertEqual(proxy.reads, 0)
        proxy, observer = self.setup_observer()
        observer.read64(o.RVBAR[0])
        with self.assertRaisesRegex(o.ObservationError, '^rvbar_exception_ack_signature$'):
            observer.get_exc_count(0)
        self.assertEqual(proxy.acks, 0)


if __name__ == '__main__':
    unittest.main()
