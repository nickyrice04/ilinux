#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline classification of sanitized 31M/31N controller reports.

This checks reporting invariants, not hardware or the truth of supplied data.
There is no target interface, live mode, execution path, or readiness grant.
Only fixed labels, selected counts and a canonical input hash are returned.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat

MAX_BYTES = 1024 * 1024
MAX_NODES = 32768
MAX_DEPTH = 20
MAX_STRING = 8192
MAX_COUNT = 100000
IDENTITIES = {'not_committed', 'expected_cpu1', 'other_known_cpu', 'unknown',
              'unexpected_cpu'}


class EvidenceError(ValueError):
    """A fixed diagnostic label; never contains untrusted report content."""
    def __init__(self, reason, classification='REFUSED'):
        super().__init__(reason)
        self.reason, self.classification = reason, classification


def require(condition, reason, classification='REFUSED'):
    if not condition:
        raise EvidenceError(reason, classification)


def field(obj, key):
    require(type(obj) is dict, 'OBJECT_TYPE')
    require(key in obj, 'MISSING_FIELD', 'INCOMPLETE')
    return obj[key]


def integer(value, maximum=MAX_COUNT):
    require(type(value) is int and 0 <= value <= maximum, 'COUNTER_TYPE_OR_RANGE')
    return value


def number(obj, key, maximum=MAX_COUNT):
    return integer(field(obj, key), maximum)


def boolean(obj, key):
    value = field(obj, key)
    require(type(value) is bool, 'BOOLEAN_TYPE')
    return value


def tree_check(value):
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        require(nodes <= MAX_NODES and depth <= MAX_DEPTH, 'STRUCTURE_LIMIT')
        if type(item) is dict:
            require(all(type(k) is str and len(k) <= MAX_STRING for k in item),
                    'KEY_TYPE_OR_LIMIT')
            pending.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            pending.extend((v, depth + 1) for v in item)
        elif type(item) is str:
            require(len(item) <= MAX_STRING, 'STRING_LIMIT')
        elif type(item) is float:
            require(math.isfinite(item), 'NONFINITE_NUMBER')
        elif type(item) is int:
            require(-(1 << 64) <= item < (1 << 64), 'INTEGER_LIMIT')
        else:
            require(item is None or type(item) is bool, 'VALUE_TYPE')


def duplicate_free(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'DUPLICATE_KEY')
        out[key] = value
    return out


def invalid_constant(_value):
    raise EvidenceError('NONFINITE_NUMBER')


def read_report(path):
    """Read at most 1 MiB from one regular file, without following a symlink."""
    try:
        require(stat.S_ISREG(os.lstat(path).st_mode), 'REPORT_FILE_TYPE')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode), 'REPORT_FILE_TYPE')
            require(info.st_size <= MAX_BYTES, 'REPORT_SIZE')
            raw = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
            require(info.st_size == after.st_size == len(raw) and
                    info.st_mtime_ns == after.st_mtime_ns, 'REPORT_CHANGED_DURING_READ')
        require(len(raw) <= MAX_BYTES, 'REPORT_SIZE')
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=duplicate_free,
                           parse_constant=invalid_constant)
        tree_check(value)
        return value
    except EvidenceError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError, OverflowError):
        raise EvidenceError('REPORT_READ_OR_JSON') from None


class Review:
    def __init__(self):
        self.complete = True
        self.positive = 0
        self.counts = {}

    def completed(self, condition):
        self.complete &= bool(condition)

    def error(self, obj, required=True):
        if not required and 'error' not in obj:
            return
        value = field(obj, 'error')
        require(value is None or type(value) is str, 'ERROR_FIELD_TYPE')
        self.completed(value is None)

    def counter_pair(self, obj, attempted, completed):
        a, c = number(obj, attempted), number(obj, completed)
        require(c <= a, 'COUNTER_COMPLETION_EXCEEDS_ATTEMPT')
        self.completed(a == c)
        return a, c

    def record(self, row, maximum_phase):
        phase = number(row, 'highest_phase_seen', 255)
        require(phase <= maximum_phase or phase == 255 and maximum_phase == 4,
                'RECORD_PHASE_RANGE')
        identity = field(row, 'identity_status')
        require(type(identity) is str and identity in IDENTITIES, 'IDENTITY_LABEL')
        if 'any_record_seen' in row:
            seen = boolean(row, 'any_record_seen')
            require(seen or phase == 0 and identity == 'not_committed',
                    'RECORD_STATE_CONTRADICTION')
        else:
            seen = phase != 0 or identity != 'not_committed'
        if identity != 'not_committed':
            require(phase >= 2, 'IDENTITY_WITHOUT_COMMIT_PHASE')
        positive = seen or phase != 0 or identity != 'not_committed'
        if 'cpu1_execution' in row:
            execution = field(row, 'cpu1_execution')
            require(execution in ('UNVERIFIED', 'PREFIX_IDENTITY_OBSERVED'),
                    'RECORD_EXECUTION_LABEL')
            require((execution == 'PREFIX_IDENTITY_OBSERVED') ==
                    (identity == 'expected_cpu1' and phase >= 2 and positive),
                    'RECORD_EXECUTION_CONTRADICTION')
        self.positive += int(positive)
        return positive

    def channel(self, row, width, maximum_phase):
        if maximum_phase == 2:
            field(row, 'cpu1_execution')
        sa, sc = self.counter_pair(row, 'samples_attempted', 'samples_completed')
        ra, rc = self.counter_pair(row, 'reads_attempted', 'reads_completed')
        require(ra <= width * sa and rc >= width * sc, 'CHANNEL_READ_BUDGET')
        positive = self.record(row, maximum_phase)
        for key in ('identity_seen', 'identity_recorded', 'identity_sample_complete',
                    'record_complete', 'stop_required'):
            if key in row:
                flag = boolean(row, key)
                require(not flag or positive, 'RECORD_FLAG_CONTRADICTION')
        if maximum_phase in (3, 4):
            done = boolean(row, 'complete')
            require(not done or row['highest_phase_seen'] >= maximum_phase,
                    'RECORD_COMPLETE_WITHOUT_PHASE')
            identity_keys = ('observed_cpu_id', 'observed_cluster', 'observed_core',
                             'observed_core_type', 'observed_macos_class',
                             'identity_mapping_evidence')
            identity = row['identity_status']
            values = [field(row, key) for key in identity_keys]
            if identity in ('not_committed', 'unknown'):
                require(all(value is None for value in values), 'IDENTITY_METADATA_CONTRADICTION')
            elif identity in ('expected_cpu1', 'other_known_cpu'):
                cpu, cluster, core = (integer(value, 17) for value in values[:3])
                expected = (cpu // 6, cpu % 6, 'M' if cpu < 12 else 'P',
                            'Performance' if cpu < 12 else 'Super', 'expected_mpidr_map')
                require(tuple(values[1:]) == expected and
                        (identity == 'expected_cpu1') == (cpu == 1),
                        'IDENTITY_METADATA_CONTRADICTION')
            if maximum_phase == 3:
                require(field(row, 'reset_route') == 'UNKNOWN' and
                        not boolean(row, 'park_verified'), 'UNSUPPORTED_COLD_CLAIM')
        self.error(row)
        self.completed(sa > 0 and sc > 0)
        if not positive and field(row, 'error') is None:
            self.completed(ra == rc == width * sc and sa == sc)
        return dict(samples=sc, reads=rc)

    def paired(self, row):
        field(row, 'cpu1_execution')
        sa, sc = self.counter_pair(row, 'samples_attempted', 'samples_completed')
        ra, rc = self.counter_pair(row, 'reads_attempted', 'reads_completed')
        require(ra <= sa * 6 and rc >= sc * 3, 'PAIRED_READ_BUDGET')
        mi = number(row, 'maintenance_intents')
        ma, mc = self.counter_pair(row, 'maintenance_attempted', 'maintenance_acknowledged')
        require(mc <= ma <= mi <= sa, 'MAINTENANCE_ORDER')
        self.completed(mi == ma == mc)
        positive = self.record(row, 2)
        self.error(row)
        self.completed(not boolean(row, 'journal_failed'))
        require(field(row, 'visibility_cause') == 'UNKNOWN' and
                boolean(row, 'negative_excludes_execution') is False and
                boolean(row, 'effects_limited_to_cpu0') is False,
                'UNSUPPORTED_VISIBILITY_CLAIM')
        self.completed(sa > 0 and sc > 0)
        for name in ('cached', 'maintained'):
            part = field(row, name)
            if part is None:
                self.completed(False)
                continue
            reads = number(part, 'reads_completed', 3)
            done = boolean(part, 'complete')
            require(not done or reads == 3, 'TRIAD_COMPLETE_WITHOUT_READS')
            part_positive = self.record(part, 2)
            require(positive or not part_positive, 'PAIRED_STATE_CONTRADICTION')
            self.completed(done)
        if not positive and field(row, 'error') is None:
            if sa == sc and ra == rc:
                require(ra == 6 * sc and mi == sc, 'PAIRED_COMPLETE_COUNT_MISMATCH')
            self.completed(sa == sc and ra == rc == 6 * sc and mi == sc)
        return dict(samples=sc, reads=rc, maintenance=mc)

    def control(self, row, label, reads, cache=False):
        self.completed(field(row, 'result') == label)
        a, c = self.counter_pair(row, 'reads_attempted', 'reads_completed')
        require(a <= reads, 'CONTROL_READ_BUDGET')
        self.completed(a == c == reads)
        first, last = ('stores_attempted', 'stores_acknowledged') if cache else (
            'writes_attempted', 'writes_acknowledged')
        a, c = self.counter_pair(row, first, last)
        require(a <= 2, 'CONTROL_STORE_BUDGET')
        self.completed(a == c == 2)
        if cache:
            a, c = self.counter_pair(row, 'maintenance_attempted', 'maintenance_acknowledged')
            require(a <= 2, 'CONTROL_MAINTENANCE_BUDGET')
            self.completed(a == c == 2)
        else:
            ri, wi = number(row, 'read_intents'), number(row, 'write_intents')
            require(row['reads_attempted'] <= ri <= reads and a <= wi <= 2,
                    'CONTROL_INTENT_ORDER')
            self.completed(ri == reads and wi == 2)
        for key in ('marker_observed', 'canaries_preserved', 'original_restored'):
            self.completed(boolean(row, key))
        visibility = 'cpu1_record_visibility' if label == 'CPU0_OBSERVER_CONTROL_PASS' else 'cpu1_visibility'
        require(field(row, visibility) == 'NOT_TESTED', 'UNSUPPORTED_CONTROL_CLAIM')
        if label == 'CPU0_OBSERVER_CONTROL_PASS':
            require(field(row, 'cpu1_execution') == 'NOT_TESTED', 'UNSUPPORTED_CONTROL_CLAIM')
        self.error(row, required=False)
        if 'journal_failed' in row:
            self.completed(not boolean(row, 'journal_failed'))

    def power_state(self, report, kind, phases):
        obj = field(report, kind)
        rows = field(obj, 'samples')
        require(type(rows) is list and len(rows) <= len(phases), 'STATE_SAMPLE_SHAPE')
        ra, rc = self.counter_pair(obj, 'reads_attempted', 'reads_completed')
        require(ra <= len(phases) * 2, 'STATE_READ_BUDGET')
        known, complete_rows = 0, 0
        for index, row in enumerate(rows):
            require(field(row, 'phase') == phases[index], 'STATE_PHASE_ORDER')
            done = boolean(row, 'complete')
            require(index == len(rows) - 1 or done, 'STATE_CONTINUED_AFTER_INCOMPLETE')
            require(row.get('cpu0') is not None or row.get('cpu1') is None,
                    'STATE_CPU_READ_ORDER')
            values = []
            for cpu in ('cpu0', 'cpu1'):
                item = field(row, cpu)
                if item is None:
                    require(not done, 'STATE_COMPLETE_WITHOUT_VALUES')
                    continue
                require(type(item) is dict, 'STATE_VALUE_TYPE')
                known += 1
                if kind == 'power_observation':
                    number(item, 'desired', 15)
                    values.append(number(item, 'actual', 15))
                    for key in ('parent_missing', 'device_disabled', 'auto_enabled'):
                        boolean(item, key)
                else:
                    values.append(number(item, 'low_byte', 255))
                    changed = field(item, 'changed_from_baseline')
                    require(changed is None if index == 0 else type(changed) is bool,
                            'STATE_BASELINE_COMPARISON_TYPE')
                    if index and rows[0].get(cpu) is not None:
                        require(changed == (item['low_byte'] != rows[0][cpu]['low_byte']),
                                'STATE_BASELINE_COMPARISON')
            if kind == 'cpu_state_observation' and done:
                require(boolean(row, 'cores_equal') == (values[0] == values[1]),
                        'STATE_CORE_EQUALITY')
            complete_rows += int(done)
        require(known == rc and complete_rows * 2 <= rc <= ra,
                'STATE_COUNT_MISMATCH')
        self.completed(len(rows) == len(phases) and complete_rows == len(phases) and ra == rc)
        self.error(obj)
        for key in ('entry_execution', 'reset_release'):
            require(field(obj, key) == 'NOT_ESTABLISHED', 'UNSUPPORTED_STATE_CLAIM')
        if kind == 'cpu_state_observation':
            self.completed(not boolean(obj, 'journal_failed'))
            require(field(obj, 'program_counter') == 'NOT_OBSERVED' and
                    field(obj, 'running_state') == 'NOT_ESTABLISHED' and
                    field(obj, 't6050_register_semantics') == 'UNKNOWN',
                    'UNSUPPORTED_STATE_CLAIM')
        if len(phases) == 3:
            require(field(obj, 'omitted_phases') == ['after_first_start'] and
                    field(obj, 'omission_reason') == 'consecutive_start_pair' and
                    number(obj, 'maximum_reads') == 6, 'STATE_OMISSION_CONTRACT')
            self.completed(not boolean(obj, 'phase_adapter_failed'))
        return rc

    def start_pair(self, report):
        pair = field(report, 'start_pair')
        required = ('intent_durable', 'dispatch_attempted', 'reply_received',
                    'return_token_matched', 'diagnostics_verified')
        facts = [boolean(pair, key) for key in required]
        require(all(not facts[i] or all(facts[:i]) for i in range(len(facts))),
                'PAIR_EVENT_ORDER')
        ack = number(pair, 'stores_acknowledged', 2)
        possibilities = field(pair, 'possible_completed_stores')
        require(type(possibilities) is list and possibilities and
                all(type(v) is int and v in (0, 1, 2) for v in possibilities) and
                possibilities == sorted(set(possibilities)), 'PAIR_POSSIBILITIES')
        require(not boolean(pair, 'pair_atomic') and
                not boolean(pair, 'completion_proves_cpu1_execution') and
                not boolean(pair, 'retry_authorized') and
                not boolean(pair, 'hardware_timing_measured'), 'UNSUPPORTED_PAIR_CLAIM')
        require(field(pair, 'stores_attempted_individually') == 'NOT OBSERVED' and
                field(pair, 'inherited_attempt_counter_meaning') == 'pair_contains_two_potential_stores',
                'PAIR_COUNTER_MEANING')
        if field(pair, 'result') == 'START_PAIR_COMPLETION_CONFIRMED':
            require(all(facts) and ack == 2 and possibilities == [2],
                    'PAIR_COMPLETION_CONTRADICTION')
        else:
            self.completed(False)
            require(ack == 0, 'UNCONFIRMED_PAIR_ACKNOWLEDGED')
        require(ack == number(report, 'start_writes_acknowledged', 2),
                'PAIR_TOP_LEVEL_ACK_MISMATCH')


def result(classification, reason, digest=None, experiment='UNKNOWN', counts=None):
    return dict(schema=1, classification=classification, reason=reason,
                experiment=experiment, report_canonical_sha256=digest,
                counts=counts or {}, cpu1_execution='UNVERIFIED',
                first_instruction_fetch='UNKNOWN', firmware_cause='UNKNOWN',
                report_authenticity='NOT_ESTABLISHED',
                negative_excludes_execution=False, native_ready=False,
                hardware_operations=0)


def classify(report):
    """Validate one supported report shape; never infer CPU1 execution from it."""
    digest, experiment, review = None, 'UNKNOWN', Review()
    try:
        tree_check(report)
        require(type(report) is dict, 'REPORT_OBJECT')
        canonical = json.dumps(report, sort_keys=True, separators=(',', ':'),
                               allow_nan=False).encode('utf-8')
        require(len(canonical) <= MAX_BYTES, 'REPORT_SIZE')
        digest = hashlib.sha256(canonical).hexdigest()
        name = field(report, 'experiment')
        require(name in ('smp31m', 'smp31n'), 'UNSUPPORTED_EXPERIMENT')
        experiment = '31M' if name == 'smp31m' else '31N'
        for key in ('cpu1_arrival_verified', 'cpu1_prefix_identity_observed',
                    'counter_progress_verified', 'park_verified'):
            review.positive += int(boolean(report, key))
        a, c = review.counter_pair(report, 'start_writes_attempted', 'start_writes_acknowledged')
        require(a <= 2, 'START_BUDGET')
        review.completed(a == c == 2)
        review.counts['start_stores_acknowledged'] = c
        review.counts['mutation_intents'] = number(report, 'mutation_requests')
        review.counts['callbacks_completed'] = number(report, 'requests_completed')
        require(number(report, 'requests_planned') == 0 and
                review.counts['callbacks_completed'] == 0, 'CALLBACK_COUNT')
        review.positive += int(review.counts['callbacks_completed'] > 0)
        require(field(report, 'linux_boot') == 'NOT RUN' and
                field(report, 'native_linux_smp') == 'NOT RUN', 'UNSUPPORTED_LINUX_CLAIM')
        for key in ('effective_reset_route', 'cache_visibility_cause', 'device_visibility_cause'):
            require(field(report, key) == 'UNKNOWN', 'UNSUPPORTED_CAUSAL_CLAIM')
        require(number(report, 'cpu0_post_start_record_stores') == 0,
                'POST_START_OBSERVER_STORE')
        for key in ('cache_records_frozen', 'normal_entry_armed', 'cold_entry_armed',
                    'reset_format_gate_passed', 'native_attempt_consumed'):
            review.completed(boolean(report, key))
        review.counts['arrival_samples'] = number(report, 'arrival_samples')
        review.completed(review.counts['arrival_samples'] > 0)
        if experiment == '31N':
            review.start_pair(report)
        for key, label, reads, cache in (
                ('cpu0_control', 'CPU0_OBSERVER_CONTROL_PASS', 24, False),
                ('cpu0_normal_control', 'CPU0_NORMAL_CONTROL_PASS', 24, False),
                ('cpu0_cache_control', 'CPU0_CACHE_CONTROL_PASS', 48, True)):
            review.control(field(report, key), label, reads, cache)
        for key, width, maxphase in (('recorder_observation', 5, 4),
                                     ('cold_observation', 4, 3)):
            counts = review.channel(field(report, key), width, maxphase)
            for metric, value in counts.items():
                review.counts[key + '_' + metric] = value
        for name in ('vector', 'cold'):
            row = field(field(report, 'normal_observation'), name)
            review.channel(row, 3, 2)
            row = field(field(report, 'paired_observation'), name)
            for metric, value in review.paired(row).items():
                review.counts['paired_' + name + '_' + metric] = value
        phases = ('before_start', 'after_second_start', 'final') if experiment == '31N' else (
            'before_start', 'after_first_start', 'after_second_start', 'final')
        for key in ('power_observation', 'cpu_state_observation'):
            review.counts[key + '_reads'] = review.power_state(report, key, phases)
        intents = number(report, 'cache_maintenance_intents')
        ma, mc = review.counter_pair(report, 'cache_maintenance_attempted',
                                     'cache_maintenance_acknowledged')
        require(mc <= ma <= intents, 'TOTAL_MAINTENANCE_ORDER')
        local = report['cpu0_cache_control']['maintenance_acknowledged'] + sum(
            report['paired_observation'][k]['maintenance_acknowledged'] for k in ('vector', 'cold'))
        require(mc == local, 'TOTAL_MAINTENANCE_MISMATCH')
        review.completed(intents == ma == mc)
        review.counts['maintenance_acknowledged'] = mc
        review.error(report, required=False)
        terminal = field(report, 'terminal_observation_error')
        require(terminal is None or type(terminal) is str, 'ERROR_FIELD_TYPE')
        review.completed(terminal is None)
        connection = field(report, 'connection')
        review.completed(not boolean(connection, 'connection_journal_failed') and
                         not boolean(connection, 'native_journal_failed') and
                         boolean(connection, 'transport_closed'))
        review.counts['reported_positive_indicators'] = review.positive
        if not review.complete:
            return result('INCOMPLETE', 'PARTIAL_OR_FAULTED_EVIDENCE', digest, experiment, review.counts)
        if review.positive:
            return result('REPORTED_POSITIVE_REQUIRES_RECORD_REVIEW',
                          'SANITIZED_METADATA_IS_NOT_RAW_IDENTITY', digest, experiment, review.counts)
        require(field(report, 'result') == 'STOP' and field(report, 'phase') == 'cpu1_arrival' and
                field(report, 'reason') == 'cpu1_arrival_timeout',
                'NOT_A_NATURAL_ARRIVAL_TIMEOUT', 'INCOMPLETE')
        return result('NATURAL_TIMEOUT_WITHOUT_VISIBLE_ENTRY',
                      'COMPLETE_NEGATIVE_OBSERVATION_NOT_FETCH_PROOF', digest, experiment, review.counts)
    except EvidenceError as exc:
        return result(exc.classification, exc.reason, digest, experiment, review.counts)
    except (ValueError, TypeError, RecursionError, OverflowError):
        return result('REFUSED', 'REPORT_VALUE_INVALID', digest, experiment, review.counts)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps(result('REFUSED', 'ARGUMENTS_INVALID'), sort_keys=True))
        raise SystemExit(2)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        output = classify(read_report(args.report))
    except EvidenceError as exc:
        output = result(exc.classification, exc.reason)
    print(json.dumps(output, sort_keys=True))
    return {'REFUSED': 1, 'INCOMPLETE': 2}.get(output['classification'], 0)


if __name__ == '__main__':
    raise SystemExit(main())
