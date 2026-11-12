#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic-only tests; no camera, microphone, USB, network or boot action."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('timeline31ah', HERE/'timeline.py')
t = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(t)


def rows():
    events = ['session_open', 'camera_recording_observed', 'visual_sync',
              'handoff_requested', 'proxy_disconnected', 'proxy_reconnected',
              'linux_console_visible', 'session_close']
    return [{'schema': t.SCHEMA, 'sequence': i, 'event': event,
             'source': 'operator_mark', 'monotonic_ns': (100+i)*10**9,
             'utc_unix_ns': 1_790_000_000_000_000_000+i*10**9,
             'clock_sample_uncertainty_ns': 10}
            for i,event in enumerate(events)]


class TimelineTests(unittest.TestCase):
    def setUp(self):
        base = t.ROOT/'build/direct31ah-capture'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-', dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'build').mkdir()
        self.file = self.root/'build/timeline.jsonl'

    def put(self, data=None):
        self.file.write_text(''.join(json.dumps(r)+'\n' for r in (rows() if data is None else data)))
        return self.file

    def test_private_path_accepts_only_build_descendants(self):
        self.assertEqual(t.private_path('build/run01', self.root), self.root/'build/run01')
        for name in ('elsewhere', 'build', 'build/../escape'):
            with self.subTest(name=name), self.assertRaises(t.Refusal):
                t.private_path(name, self.root)

    def test_private_path_refuses_symlink_component(self):
        (self.root/'build/link').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(t.Refusal):
            t.private_path('build/link/new', self.root)

    def test_existing_output_is_not_overwritten(self):
        directory = self.root/'build/existing'
        directory.mkdir()
        (directory/'keep').write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            t.record(directory)
        self.assertEqual((directory/'keep').read_bytes(), b'keep')

    def test_clock_bracket_is_conservative(self):
        mono = iter([10, 13])
        self.assertEqual(t.clock_sample(lambda: next(mono), lambda: 2000), (11, 2000, 2))

    def test_reversed_clock_sampling_refuses(self):
        mono = iter([13, 10])
        with self.assertRaises(t.Refusal):
            t.clock_sample(lambda: next(mono), lambda: 2000)

    def test_arbitrary_input_is_not_stored(self):
        stream = io.StringIO()
        recorder = t.Recorder(stream, lambda: (10, 20, 1))
        before = stream.getvalue()
        with self.assertRaises(t.Refusal):
            recorder.mark('PRIVATE-EXAMPLE\nproxy_reconnected')
        self.assertEqual(before, stream.getvalue())

    def test_recorder_refuses_events_after_close(self):
        stream = io.StringIO()
        recorder = t.Recorder(stream, lambda: (10, 20, 1))
        recorder.mark('session_close', internal=True)
        with self.assertRaises(t.Refusal):
            recorder.mark('visual_sync')

    def test_recorder_bounds_event_count_while_allowing_close(self):
        recorder = t.Recorder(io.StringIO(), lambda: (10, 20, 1))
        for _ in range(t.MAX_EVENTS-2):
            recorder.mark('visual_sync')
        with self.assertRaises(t.Refusal):
            recorder.mark('visual_sync')
        recorder.mark('session_close', internal=True)
        self.assertEqual(len(recorder.rows), t.MAX_EVENTS)

    def test_recorder_refuses_time_reversal(self):
        samples = iter([(100, 20, 1), (99, 21, 1)])
        recorder = t.Recorder(io.StringIO(), lambda: next(samples))
        with self.assertRaises(t.Refusal):
            recorder.mark('visual_sync')

    def test_recorder_bounds_duration(self):
        samples = iter([(0, 20, 1), ((t.MAX_SECONDS+1)*10**9, 21, 1)])
        recorder = t.Recorder(io.StringIO(), lambda: next(samples))
        with self.assertRaises(t.Refusal):
            recorder.mark('visual_sync')

    def test_valid_closed_capture_roundtrips(self):
        self.assertEqual(t.read_rows(self.put()), rows())

    def test_partial_final_line_is_preserved_and_refused(self):
        p = self.put()
        raw = p.read_bytes()[:-1]
        p.write_bytes(raw)
        with self.assertRaises(t.Refusal):
            t.read_rows(p)
        self.assertEqual(p.read_bytes(), raw)

    def test_open_session_cannot_be_treated_as_complete(self):
        with self.assertRaises(t.Refusal):
            t.read_rows(self.put(rows()[:-1]))

    def test_event_order_and_identity_corruption_refuse(self):
        mutations = [('sequence', 30), ('event', 'entered_kernel'), ('event', []),
                     ('sequence', True), ('schema', 'different'),
                     ('source', 'verified_hardware'), ('monotonic_ns', False)]
        for field,value in mutations:
            data = rows()
            data[3][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(t.Refusal):
                t.read_rows(self.put(data))

    def test_capture_clock_reversal_refuses(self):
        data = rows()
        data[4]['monotonic_ns'] = 10
        with self.assertRaises(t.Refusal):
            t.read_rows(self.put(data))

    def test_utc_clock_adjustment_does_not_change_monotonic_alignment(self):
        data = rows()
        data[4]['utc_unix_ns'] -= 10**12
        read = t.read_rows(self.put(data))
        result = t.align(read, 2, 2*10**9, 500_000_000, 100_000_000)
        self.assertEqual(result['events'][4]['estimated_video_ns'], 4*10**9)

    def test_closed_capture_cannot_have_events_after_close(self):
        data = rows()
        data[3]['event'] = 'session_close'
        with self.assertRaises(t.Refusal):
            t.read_rows(self.put(data))

    def test_extra_fields_are_not_echoed(self):
        data = rows()
        data[3]['private-note'] = 'DO-NOT-ECHO'
        with self.assertRaises(t.Refusal):
            t.read_rows(self.put(data))

    def test_large_input_is_refused_before_parse(self):
        self.file.write_bytes(b'x'*(t.MAX_BYTES+1))
        with self.assertRaises(t.Refusal):
            t.read_rows(self.file)

    def test_decimal_time_is_exact_and_invalid_values_refuse(self):
        self.assertEqual(t.nanoseconds('2.433'), 2_433_000_000)
        for value in ('NaN', 'Infinity', '-1', '1801', '0.0000000001', 'no', True):
            with self.subTest(value=value), self.assertRaises(t.Refusal):
                t.nanoseconds(value)

    def test_sync_maps_event_differences_and_reports_uncertainty(self):
        result = t.align(rows(), 2, 2_433_000_000, 500_000_000, 100_000_000)
        self.assertEqual(result['events'][5]['estimated_video_ns'], 5_433_000_000)
        self.assertEqual(result['events'][5]['uncertainty_ns'], 600_000_020)
        self.assertEqual(result['evidence'], 'OPERATOR_ESTIMATED_ALIGNMENT')
        self.assertFalse(result['native_entry_proven'])
        self.assertFalse(result['cpu_execution_proven'])
        self.assertFalse(result['camera_controlled'])
        self.assertFalse(result['microphone_controlled'])

    def test_negative_mapped_time_is_flagged(self):
        result = t.align(rows(), 2, 0, 500_000_000, 100_000_000)
        self.assertLess(result['events'][0]['estimated_video_ns'], 0)
        self.assertTrue(result['events'][0]['possibly_before_recording'])

    def test_anchor_must_be_a_visual_sync(self):
        for sequence in (-1, 500, True, 3):
            with self.subTest(sequence=sequence), self.assertRaises(t.Refusal):
                t.align(rows(), sequence, 0, 500_000_000, 100_000_000)

    def test_zero_manual_uncertainty_is_refused(self):
        with self.assertRaises(t.Refusal):
            t.align(rows(), 2, 0, 0, 100_000_000)


if __name__ == '__main__':
    unittest.main()
