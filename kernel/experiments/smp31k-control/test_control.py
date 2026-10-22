"""Synthetic transaction and fault tests; no hardware or client import."""
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import control as c

IMAGE = 0x810000000
HELPER = 0x820000000
LO, HI = 0x800000000, 0x880000000


class Fixture:
    def __init__(self, fault=None):
        self.plan = c.layout(IMAGE, HELPER, LO, HI)
        self.memory = bytearray(c.SCRATCH_BYTES)
        self.trace, self.rows = [], []
        self.now, self.start_intents = 0.0, 0
        self.fault = fault
        self.journal_fault = None
        self.after = None
        self.bad_return = False
        self.bad_read = None

    def io(self, kind, address, value=None):
        index = len(self.trace)
        self.trace.append((kind, address, value))
        if self.fault == (index, 'before'):
            raise OSError('PRIVATE_SYNTHETIC')
        if kind == 'read':
            if address not in tuple(self.plan.scratch + at for at in c.WORD_OFFSETS):
                raise AssertionError('read outside fixed scratch')
            result = struct.unpack_from('<Q', self.memory, address - self.plan.scratch)[0]
            if self.bad_read == index:
                result = True
        else:
            if address != self.plan.marker_address:
                raise AssertionError('write outside fixed marker')
            struct.pack_into('<Q', self.memory, address - self.plan.scratch, value)
            result = 0 if self.bad_return else c.RETURN_VALUE
        if self.after is not None:
            self.after(index, kind)
        if self.fault == (index, 'after'):
            raise OSError('PRIVATE_SYNTHETIC')
        return result

    def journal(self, row):
        self.rows.append(row)
        if self.journal_fault == len(self.rows) - 1:
            raise OSError('PRIVATE_SYNTHETIC')

    def runner(self, **kwargs):
        options = dict(read64=lambda address: self.io('read', address),
                       store=lambda value: self.io('store', self.plan.marker_address, value),
                       journal=self.journal, starts=lambda: self.start_intents,
                       clock=lambda: self.now, publication_verified=True)
        options.update(kwargs)
        return c.Control(self.plan, **options)


class ControlTests(unittest.TestCase):
    def failure(self, fixture, runner=None, reason=None):
        with self.assertRaises(c.ControlError) as captured:
            (runner or fixture.runner()).run()
        exc = captured.exception
        if reason is not None:
            self.assertEqual(exc.reason, reason)
        self.assertEqual(exc.report['result'], 'STOP')
        text = json.dumps(exc.report)
        for private in ('PRIVATE_SYNTHETIC', hex(IMAGE), hex(HELPER), str(c.MARKER), '/Users/'):
            self.assertNotIn(private, text)
        self.assertEqual(exc.report['cpu1_execution'], 'NOT_TESTED')
        self.assertEqual(exc.report['cpu1_record_visibility'], 'NOT_TESTED')
        return exc

    def test_success_restores_exact_record_and_labels_scope(self):
        f = Fixture()
        result = f.runner().run()
        self.assertEqual(result['result'], 'CPU0_OBSERVER_CONTROL_PASS')
        self.assertEqual(result['scope'], 'cpu0_shared_device_ram_observer')
        for field in ('marker_observed', 'canaries_preserved', 'original_restored'):
            self.assertIs(result[field], True)
        self.assertEqual((result['read_intents'], result['reads_attempted'], result['reads_completed']),
                         (24, 24, 24))
        self.assertEqual((result['write_intents'], result['writes_attempted'], result['writes_acknowledged']),
                         (2, 2, 2))
        self.assertEqual(f.memory, bytes(64))
        self.assertEqual([v for kind, address, v in f.trace if kind == 'store'], [c.MARKER, 0])
        self.assertTrue(all(IMAGE + 0x90b00 <= address < IMAGE + 0x90b40
                            for kind, address, value in f.trace))
        self.assertFalse(any(IMAGE + 0x90a40 <= address < IMAGE + 0x90ac0
                             for kind, address, value in f.trace))

    def test_intents_are_persisted_before_dispatch(self):
        f = Fixture()
        expected = {'read': 0, 'store': 0}
        def check(index, kind):
            row = f.rows[-1]
            key = 'reads_attempted' if kind == 'read' else 'writes_attempted'
            self.assertEqual(row[key], expected[kind])
            expected[kind] += 1
            self.assertEqual(row['read_intents' if kind == 'read' else 'write_intents'], expected[kind])
        f.after = check
        f.runner().run()
        self.assertEqual(expected, {'read': 24, 'store': 2})

    def test_all_io_fault_boundaries_stop_without_cleanup(self):
        reference = Fixture()
        reference.runner().run()
        for index in range(len(reference.trace)):
            for side in ('before', 'after'):
                with self.subTest(index=index, side=side):
                    f = Fixture((index, side))
                    exc = self.failure(f)
                    self.assertEqual(f.trace, reference.trace[:index + 1])
                    self.assertIsInstance(exc.cause, OSError)
                    self.assertFalse(exc.report['original_restored'])

    def test_partial_marker_store_is_not_automatically_restored(self):
        f = Fixture((8, 'after'))
        exc = self.failure(f, reason='control_store_failed')
        self.assertEqual(struct.unpack_from('<Q', f.memory, c.MARKER_OFFSET)[0], c.MARKER)
        self.assertEqual(exc.report['writes_attempted'], 1)
        self.assertEqual(exc.report['writes_acknowledged'], 0)

    def test_every_nonfresh_word_refuses_before_mutation(self):
        for offset in c.WORD_OFFSETS:
            f = Fixture()
            struct.pack_into('<Q', f.memory, offset, c.MARKER if offset == c.MARKER_OFFSET else 17)
            exc = self.failure(f, reason='control_scratch_not_fresh')
            self.assertEqual(exc.report['writes_attempted'], 0)
            self.assertEqual(len(f.trace), 8)

    def test_canary_corruption_stops_without_restore(self):
        for offset in c.WORD_OFFSETS:
            if offset == c.MARKER_OFFSET:
                continue
            f = Fixture()
            def after(index, kind):
                if index == 8:
                    struct.pack_into('<Q', f.memory, offset, 7)
            f.after = after
            exc = self.failure(f, reason='control_marker_or_canary_mismatch')
            self.assertEqual(exc.report['writes_attempted'], 1)
            self.assertFalse(exc.report['marker_observed'])

    def test_missing_marker_stops_before_restore(self):
        f = Fixture()
        def after(index, kind):
            if index == 8:
                struct.pack_into('<Q', f.memory, c.MARKER_OFFSET, 0)
        f.after = after
        self.failure(f, reason='control_marker_or_canary_mismatch')
        self.assertEqual(len([row for row in f.trace if row[0] == 'store']), 1)

    def test_restore_corruption_never_reports_pass(self):
        f = Fixture()
        def after(index, kind):
            if index == 17:
                struct.pack_into('<Q', f.memory, c.MARKER_OFFSET, 99)
        f.after = after
        exc = self.failure(f, reason='control_restore_mismatch')
        self.assertFalse(exc.report['original_restored'])
        self.assertTrue(exc.report['marker_observed'])

    def test_wrong_leaf_return_stops_after_single_store(self):
        f = Fixture(); f.bad_return = True
        exc = self.failure(f, reason='control_store_return')
        self.assertEqual((exc.report['writes_attempted'], exc.report['writes_acknowledged']), (1, 0))

    def test_noninteger_read_refused(self):
        f = Fixture(); f.bad_read = 0
        exc = self.failure(f, reason='control_read_value')
        self.assertEqual((exc.report['reads_attempted'], exc.report['reads_completed']), (1, 0))

    def test_journal_failure_cannot_dispatch_following_request(self):
        reference = Fixture(); reference.runner().run()
        for index in range(len(reference.rows)):
            with self.subTest(index=index):
                f = Fixture(); f.journal_fault = index
                exc = self.failure(f, reason='control_journal_failed')
                self.assertTrue(exc.report['journal_failed'])
                row = f.rows[-1]
                self.assertEqual(len(f.trace), row['reads_attempted'] + row['writes_attempted'])
                self.assertIsInstance(exc.cause, OSError)

    def test_journal_snapshot_cannot_modify_internal_state(self):
        f = Fixture()
        def journal(row):
            row['writes_attempted'] = 999
            row['result'] = 'FORGED'
        result = f.runner(journal=journal).run()
        self.assertEqual(result['writes_attempted'], 2)
        self.assertEqual(result['result'], 'CPU0_OBSERVER_CONTROL_PASS')

    def test_any_start_intent_prohibits_control(self):
        for count in (1, 2, -1, True, None):
            f = Fixture(); f.start_intents = count
            exc = self.failure(f, reason='control_after_start_intent')
            self.assertEqual(f.trace, [])
            self.assertEqual(exc.report['writes_attempted'], 0)

    def test_late_start_intent_stops_before_next_request(self):
        f = Fixture()
        f.after = lambda index, kind: setattr(f, 'start_intents', 1)
        self.failure(f, reason='control_after_start_intent')
        self.assertEqual(len(f.trace), 1)

    def test_deadline_after_marker_ack_has_no_restore(self):
        f = Fixture()
        def after(index, kind):
            if index == 8:
                f.now = c.MAX_SECONDS
        f.after = after
        exc = self.failure(f, reason='control_deadline')
        self.assertEqual(len(f.trace), 9)
        self.assertEqual(exc.report['writes_acknowledged'], 1)
        self.assertFalse(exc.report['original_restored'])

    def test_clock_faults_are_refused(self):
        for value in (float('inf'), float('nan'), True, None, '1'):
            f = Fixture()
            self.failure(f, f.runner(clock=lambda: value), 'control_clock_invalid')
            self.assertEqual(f.trace, [])
        f = Fixture()
        ticks = iter((1.0, 0.0))
        self.failure(f, f.runner(clock=lambda: next(ticks)), 'control_clock_regressed')
        self.assertEqual(f.trace, [])

    def test_outer_interrupt_and_alarm_remain_private_causes(self):
        class OuterAlarm(ValueError):
            pass
        for cause in (OuterAlarm('controller_deadline'), KeyboardInterrupt()):
            for callback in ('read64', 'store', 'journal', 'starts', 'clock'):
                with self.subTest(callback=callback, cause=type(cause).__name__):
                    f = Fixture()
                    def fail(*args):
                        raise cause
                    exc = self.failure(f, f.runner(**{callback: fail}))
                    self.assertIs(exc.cause, cause)

    def test_runner_is_single_use_after_success_or_failure(self):
        for fault in (None, (8, 'after')):
            f = Fixture(fault); runner = f.runner()
            if fault is None:
                runner.run()
            else:
                self.failure(f, runner)
            trace = list(f.trace)
            self.failure(f, runner, 'control_already_used')
            self.assertEqual(f.trace, trace)

    def test_publication_gate_precedes_callbacks(self):
        f = Fixture()
        for value in (False, 1, None):
            with self.assertRaisesRegex(ValueError, '^control_publication_unverified$'):
                f.runner(publication_verified=value)
        self.assertEqual(f.trace, [])


class LayoutTests(unittest.TestCase):
    def test_parser_integer_subclasses_are_normalized_before_address_math(self):
        class DisplayInteger(int):
            def __int__(self):
                raise AssertionError('must preserve intrinsic integer value')
            def __lt__(self, other):
                raise AssertionError('must compare normalized addresses')
            def __mod__(self, other):
                raise AssertionError('must align normalized addresses')
        base = 0x10000000000
        values = (base+0x20000, base+0x420000, base+0x4000,
                  base+0x2000000000-0x8000)
        plan = c.layout(*(DisplayInteger(value) for value in values))
        self.assertEqual(plan, c.layout(*values))
        self.assertTrue(all(type(value) is int for value in
                            (plan.image, plan.helper, plan.ram_lo, plan.ram_hi)))
        self.assertTrue(c.validate_layout(plan))
        self.assertFalse(c.u64(DisplayInteger(0)))
        with self.assertRaisesRegex(ValueError, '^control_layout_invalid$'):
            c.validate_layout(c.Layout(*(DisplayInteger(value) for value in values)))

    def test_address_numeric_ducks_booleans_and_subclass_overflow_refused(self):
        class DisplayInteger(int):
            pass
        class NumericDuck:
            def __int__(self):
                raise AssertionError('must not convert arbitrary objects')
            def __index__(self):
                raise AssertionError('must not convert arbitrary objects')
        for value in (True, False, 1.0, '1', NumericDuck(),
                      DisplayInteger(-1), DisplayInteger(1 << 64)):
            for index in range(4):
                values = [IMAGE, HELPER, LO, HI]
                values[index] = value
                with self.assertRaisesRegex(ValueError, '^control_address_type$'):
                    c.layout(*values)

    def test_m5_high_dram_bounds_keep_alias_bits_disjoint(self):
        base = 0x10000000000
        plan = c.layout(base+0x20000, base+0x420000,
                        base+0x4000, base+0x2000000000-0x8000)
        self.assertEqual(plan.leaf, (base+0x420000 | c.RX_ALIAS)+512)
        self.assertEqual(plan.leaf & ~c.RX_ALIAS, base+0x420200)
        with self.assertRaisesRegex(ValueError, '^control_ram_bounds$'):
            c.layout(base+0x20000, base+0x420000, base+0x4000, 1 << 41)

    def test_fixed_spans_and_translation_attributes(self):
        plan = c.layout(IMAGE, HELPER, LO, HI)
        self.assertEqual(plan.leaf, (HELPER | c.RX_ALIAS) + 512)
        self.assertEqual(plan.marker_address, IMAGE + 0x90b20)
        self.assertEqual(c.SCRATCH_BYTES, 64)
        probes = c.translation_probes(plan)
        self.assertEqual(len(probes), 5)
        self.assertEqual(probes[0]['attr'], 0xff)
        self.assertTrue(all(row['attr'] == 0 for row in probes[1:]))
        self.assertEqual({row['physical'] for row in probes[1:]},
                         {IMAGE + 0x90b00, IMAGE + 0x90b38})

    def test_invalid_bounds_alignment_and_aliases_refused(self):
        arguments = [(IMAGE, HELPER, LO, HI)]
        for index in range(4):
            for value in (True, -1, 1 << 64, None):
                args = list(arguments[0]); args[index] = value
                with self.assertRaises(ValueError):
                    c.layout(*args)
        for args in ((IMAGE + 8, HELPER, LO, HI), (IMAGE, HELPER + 8, LO, HI),
                     (IMAGE, IMAGE, LO, HI), (IMAGE, HELPER | c.RX_ALIAS, LO, HI),
                     (LO - c.ALLOCATION_BYTES, HELPER, LO, HI),
                     (IMAGE, HI, LO, HI), (IMAGE, HELPER, HI, LO)):
            with self.assertRaises(ValueError):
                c.layout(*args)

    def test_forged_layout_and_unpinned_images_refused(self):
        forged = c.Layout(IMAGE, IMAGE, LO, HI)
        with self.assertRaises(ValueError):
            c.translation_probes(forged)
        for image in (b'', bytes(c.IMAGE_BYTES), bytearray(c.IMAGE_BYTES), None):
            with self.assertRaisesRegex(ValueError, '^control_image_digest$'):
                c.verify_image_padding(image)

    def test_leaf_is_one_fixed_width_store_and_return(self):
        words = struct.unpack('<4I', c.LEAF)
        self.assertEqual(words[0] & 0xffc003ff, 0xf9000001)
        self.assertEqual((words[0] >> 10) & 0xfff, 0)
        self.assertEqual(words[1], 0xd5033f9f)
        self.assertEqual(words[2] & 0xffe0001f, 0xd2800000)
        self.assertEqual((words[2] >> 5) & 0xffff, c.RETURN_VALUE)
        self.assertEqual(words[3], 0xd65f03c0)
        self.assertEqual(len(c.LEAF), 16)


if __name__ == '__main__':
    unittest.main()
