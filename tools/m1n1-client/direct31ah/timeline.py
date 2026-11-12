#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local operator marks and bounded offline video-time alignment.

This opens no camera, microphone, serial port, network connection or other app.
Video and controller captures remain separate, human-controlled evidence.
"""
import argparse
import decimal
import json
import os
from pathlib import Path
import select
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = 'ilinux-direct31ah-operator-timeline-v1'
MAX_BYTES = 256 * 1024
MAX_EVENTS = 256
MAX_SECONDS = 1800
LABELS = frozenset({
    'camera_recording_observed', 'visual_sync', 'handoff_requested',
    'proxy_disconnected', 'proxy_reconnected', 'linux_console_visible',
    'cpu_workers_complete', 'linux_desktop_visible', 'stop_condition',
    'camera_recording_stopped', 'returned_macos',
})
ALL_LABELS = LABELS | {'session_open', 'session_close'}
FIELDS = {'schema', 'sequence', 'event', 'source', 'monotonic_ns',
          'utc_unix_ns', 'clock_sample_uncertainty_ns'}


class Refusal(ValueError):
    """A fixed, non-identifying refusal code."""


def private_path(value, root=ROOT):
    """Accept only nonsymlink paths strictly under this checkout's build/."""
    root = root.resolve(strict=True)
    build = root / 'build'
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    try:
        relative = path.relative_to(build)
    except ValueError:
        raise Refusal('output_outside_build')
    if not relative.parts or any(part in ('.', '..') for part in relative.parts):
        raise Refusal('invalid_private_path')
    current = root
    for part in ('build', *relative.parts):
        current = current / part
        if current.is_symlink():
            raise Refusal('symlink_private_path')
    if path.resolve(strict=False) != path:
        raise Refusal('noncanonical_private_path')
    return path


def clock_sample(monotonic=time.monotonic_ns, wall=time.time_ns):
    before = monotonic()
    utc = wall()
    after = monotonic()
    if type(before) is not int or type(after) is not int or type(utc) is not int:
        raise Refusal('invalid_clock_sample')
    if before < 0 or utc < 0 or after < before:
        raise Refusal('clock_sample_reversed')
    return (before + after) // 2, utc, (after - before + 1) // 2


class Recorder:
    def __init__(self, stream, sample=clock_sample):
        self.stream = stream
        self.sample = sample
        self.rows = []
        self.closed = False
        self.mark('session_open', internal=True)

    def mark(self, event, internal=False):
        allowed = ALL_LABELS if internal else LABELS
        if event not in allowed:
            raise Refusal('unknown_event_not_recorded')
        if self.closed:
            raise Refusal('session_already_closed')
        if len(self.rows) >= MAX_EVENTS - (0 if event == 'session_close' else 1):
            raise Refusal('event_limit_reached')
        mono, utc, uncertainty = self.sample()
        if self.rows:
            if mono < self.rows[-1]['monotonic_ns']:
                raise Refusal('monotonic_clock_reversed')
            if mono - self.rows[0]['monotonic_ns'] > MAX_SECONDS * 10**9:
                raise Refusal('session_time_limit_reached')
        row = {'schema': SCHEMA, 'sequence': len(self.rows), 'event': event,
               'source': 'operator_mark', 'monotonic_ns': mono,
               'utc_unix_ns': utc, 'clock_sample_uncertainty_ns': uncertainty}
        self.stream.write(json.dumps(row, sort_keys=True) + '\n')
        self.stream.flush()
        self.rows.append(row)
        self.closed = event == 'session_close'
        return row


def read_rows(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise Refusal('timeline_file_refused')
    try:
        raw = path.read_bytes()
        if not raw.endswith(b'\n'):
            raise Refusal('incomplete_timeline_line')
        lines = raw.splitlines()
        if not 2 <= len(lines) <= MAX_EVENTS:
            raise Refusal('invalid_event_count')
        rows = [json.loads(line) for line in lines]
    except (UnicodeError, json.JSONDecodeError):
        raise Refusal('invalid_timeline_json')
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise Refusal('invalid_record_fields')
        if (row['schema'] != SCHEMA or type(row['sequence']) is not int
                or row['sequence'] != index or row['source'] != 'operator_mark'
                or type(row['event']) is not str or row['event'] not in ALL_LABELS):
            raise Refusal('invalid_record_identity')
        for key in ('monotonic_ns', 'utc_unix_ns', 'clock_sample_uncertainty_ns'):
            if type(row[key]) is not int or not 0 <= row[key] < 2**64:
                raise Refusal('invalid_clock_field')
        if index and row['monotonic_ns'] < rows[index-1]['monotonic_ns']:
            raise Refusal('nonmonotonic_timeline')
        if index and row['event'] == 'session_open':
            raise Refusal('duplicate_session_open')
        if index != len(rows)-1 and row['event'] == 'session_close':
            raise Refusal('event_after_session_close')
    if rows[0]['event'] != 'session_open' or rows[-1]['event'] != 'session_close':
        raise Refusal('session_not_closed')
    if rows[-1]['monotonic_ns'] - rows[0]['monotonic_ns'] > MAX_SECONDS * 10**9:
        raise Refusal('timeline_duration_limit')
    return rows


def nanoseconds(value):
    if not isinstance(value, str):
        raise Refusal('invalid_time_argument')
    try:
        number = decimal.Decimal(value)
    except decimal.InvalidOperation:
        raise Refusal('invalid_time_argument')
    if not number.is_finite() or not 0 <= number <= MAX_SECONDS:
        raise Refusal('invalid_time_argument')
    scaled = number * 10**9
    if scaled != scaled.to_integral_value():
        raise Refusal('subnanosecond_argument')
    return int(scaled)


def align(rows, sequence, video_ns, manual_uncertainty_ns, video_uncertainty_ns):
    if type(sequence) is not int or not 0 <= sequence < len(rows):
        raise Refusal('invalid_sync_sequence')
    anchor = rows[sequence]
    if anchor['event'] != 'visual_sync':
        raise Refusal('anchor_is_not_visual_sync')
    if manual_uncertainty_ns < 10**6:
        raise Refusal('manual_uncertainty_too_small')
    combined = manual_uncertainty_ns + video_uncertainty_ns + anchor['clock_sample_uncertainty_ns']
    events = []
    for row in rows:
        estimate = video_ns + row['monotonic_ns'] - anchor['monotonic_ns']
        events.append({'sequence': row['sequence'], 'event': row['event'],
                       'estimated_video_ns': estimate,
                       'uncertainty_ns': combined + row['clock_sample_uncertainty_ns'],
                       'possibly_before_recording': estimate - combined < 0})
    return {'schema': 'ilinux-direct31ah-video-alignment-v1',
            'evidence': 'OPERATOR_ESTIMATED_ALIGNMENT', 'sync_sequence': sequence,
            'clock_scale_assumption': '1x; no drift correction',
            'manual_uncertainty_ns': manual_uncertainty_ns,
            'video_time_uncertainty_ns': video_uncertainty_ns,
            'camera_controlled': False, 'microphone_controlled': False,
            'native_entry_proven': False, 'cpu_execution_proven': False,
            'events': events}


def record(directory):
    directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.mkdir(mode=0o700, exist_ok=False)
    fd = os.open(directory/'timeline.jsonl', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        recorder = Recorder(stream)
        print('Camera/audio/proxy control: NONE. Enter one fixed event label, or stop.')
        print('Labels: ' + ', '.join(sorted(LABELS)))
        try:
            while True:
                left = MAX_SECONDS - (time.monotonic_ns() - recorder.rows[0]['monotonic_ns']) / 10**9
                if left <= 0 or not select.select([sys.stdin], [], [], left)[0]:
                    break
                value = sys.stdin.readline()
                if not value or value.strip() == 'stop':
                    break
                try:
                    row = recorder.mark(value.strip())
                    print(json.dumps({'sequence': row['sequence'], 'event': row['event']}))
                except Refusal as exc:
                    print('REFUSED: ' + str(exc), file=sys.stderr)
        except KeyboardInterrupt:
            pass
        # Do not invent a close timestamp if scheduling overran the time limit.
        try:
            recorder.mark('session_close', internal=True)
        except Refusal:
            print('STOP: session_incomplete_keep_private_timeline', file=sys.stderr)
            return 2
    print('Timeline closed. All marks are operator observations, not device proof.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    capture = sub.add_parser('record', help='record typed labels only; no camera access')
    capture.add_argument('--out', required=True, help='new directory strictly under build/')
    alignment = sub.add_parser('align', help='read private marks and estimate video offsets')
    alignment.add_argument('--timeline', required=True)
    alignment.add_argument('--sync-sequence', type=int, required=True)
    alignment.add_argument('--video-seconds', required=True, help='actual media timestamp of the visible sync')
    alignment.add_argument('--manual-uncertainty-seconds', required=True)
    alignment.add_argument('--video-time-uncertainty-seconds', required=True)
    args = parser.parse_args(argv)
    if args.mode == 'record':
        return record(private_path(args.out))
    rows = read_rows(private_path(args.timeline))
    result = align(rows, args.sync_sequence, nanoseconds(args.video_seconds),
                   nanoseconds(args.manual_uncertainty_seconds),
                   nanoseconds(args.video_time_uncertainty_seconds))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Refusal as exc:
        print('STOP: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
    except (OSError, ValueError, OverflowError):
        print('STOP: local_timeline_operation_failed', file=sys.stderr)
        raise SystemExit(2)
