#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline CPU-bring-up campaign planner and evidence replay.

No transport, subprocess, device access, live dispatch or resume exists here.
A model result checks workflow logic; it cannot establish native compatibility.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

SCHEMA = 1
KINDS = {'read_only', 'ram_setup', 'cpu_start', 'ram_request'}
EVIDENCE_KINDS = {'synthetic', 'native_report', 'vm_report', 'static_analysis'}
OUTCOMES = {'pass', 'fail', 'timeout', 'transport_lost', 'unsupported'}
LABEL = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}\Z')


class Invalid(ValueError):
    """A fixed message suitable for public output; never echo input contents."""


def need(condition, message):
    if not condition:
        raise Invalid(message)


def number(value, maximum):
    return type(value) is int and 0 <= value <= maximum


@dataclass(frozen=True)
class Stage:
    name: str
    kind: str
    limit_ms: int
    requires: tuple[str, ...]
    provides: tuple[str, ...]
    checks: tuple[str, ...]
    optional: bool = False


# A design contract only. The native controller must separately implement and
# review every selected observation, address, operation and timeout. In
# particular, RAM-only does not mean free of cache/coherency or exception risk.
STAGES = (
    Stage('fresh_identity', 'read_only', 10000, (), ('fresh_target',),
          ('image_pinned', 'model_matches', 'fresh_boot', 'only_cpu0_running', 'direct_usb')),
    Stage('ram_reset_snapshot', 'read_only', 10000, ('fresh_target',), ('ram_valid', 'reset_snapshot'),
          ('usable_ram_valid', 'reset_mirror_captured', 'no_prior_request')),
    Stage('observer_setup', 'ram_setup', 10000, ('ram_valid', 'reset_snapshot'), ('observer_ready',),
          ('bounded_observer_verified', 'publication_completed')),
    Stage('prestart_bundle', 'read_only', 4000, ('observer_ready',), ('cpu0_baseline',),
          ('cpu0_features_captured', 'counter_baseline_captured', 'ram_layout_captured'), True),
    Stage('cpu1_start', 'cpu_start', 3000, ('fresh_target', 'observer_ready'), ('start_acknowledged',),
          ('exact_target', 'two_writes_acknowledged')),
    Stage('entry_trace', 'read_only', 3000, ('start_acknowledged',), ('cpu1_arrival',),
          ('entry_marker_seen', 'arrival_seen', 'cpu1_identity_matches')),
    Stage('cpu1_timer_pair', 'ram_request', 3000, ('cpu1_arrival',), ('timer_pair_observed',),
          ('two_requests_completed', 'counter_advanced')),
    Stage('cpu1_memory_echo', 'ram_request', 4000, ('cpu1_arrival', 'timer_pair_observed'),
          ('payload_echo_observed',), ('bounded_pattern_matches', 'primary_remained_responsive'), True),
    Stage('final_park', 'read_only', 2000, ('cpu1_arrival', 'timer_pair_observed'), ('park_observed',),
          ('reviewed_park_state', 'primary_remained_responsive')),
)
DEFAULT_BUDGET = 60000
EXIT_RESERVE = 5000
LIMITS = [
    'Offline planning/replay only; no hardware operation is available.',
    'Synthetic, VM and static evidence do not prove native behavior.',
    'Historical native observations describe their recorded boot only.',
    'No live continuation, retry, reconnect, reset or resume is authorized.',
    'CPU1 arrival/timer/payload checks do not prove Linux SMP, all cores, full coherency or efficiency.',
]


def validate_plan(stages=STAGES, budget_ms=DEFAULT_BUDGET):
    need(number(budget_ms, 60000) and budget_ms > EXIT_RESERVE, 'invalid_budget')
    known = set()
    names = set()
    transitions = 0
    for stage in stages:
        need(LABEL.fullmatch(stage.name) and stage.name not in names, 'invalid_stage_id')
        need(stage.kind in KINDS, 'invalid_stage_kind')
        need(number(stage.limit_ms, 60000) and stage.limit_ms > 0, 'invalid_stage_bound')
        need(set(stage.requires) <= known, 'missing_or_forward_prerequisite')
        need(not (known & set(stage.provides)), 'duplicate_capability')
        # Optional stages may supply useful measurements, never required gates.
        if not stage.optional:
            known.update(stage.provides)
        transitions += stage.kind == 'cpu_start'
        names.add(stage.name)
    need(transitions == 1, 'requires_exactly_one_start_transition')
    need(sum(s.limit_ms for s in stages) + EXIT_RESERVE <= budget_ms, 'budget_exceeded')


def plan_document(budget_ms=DEFAULT_BUDGET):
    validate_plan(budget_ms=budget_ms)
    return {
        'schema_version': SCHEMA,
        'status': 'DESIGN_ONLY_NOT_A_LIVE_HANDOFF',
        'controller_budget_ms': budget_ms,
        'reserved_controller_exit_margin_ms': EXIT_RESERVE,
        'maximum_stage_total_ms': sum(stage.limit_ms for stage in STAGES),
        'cpu_start_transitions': 1,
        'stages': [dict(name=s.name, kind=s.kind, limit_ms=s.limit_ms,
                        requires=list(s.requires), provides=list(s.provides),
                        checks=list(s.checks), optional=s.optional,
                        implementation='requires_separate_native_review') for s in STAGES],
        'limits': LIMITS,
    }


class Replay:
    """Sequential event replay; a new instance always begins at fresh identity.

    There is deliberately no restore/resume constructor. An event's source
    and boot label must match the envelope; no cross-boot mixing is accepted.
    Even successful replay outputs are historical/model capabilities, never
    live permissions or host state.
    """
    def __init__(self, source_kind, boot_label, *, budget_ms=DEFAULT_BUDGET):
        validate_plan(budget_ms=budget_ms)
        need(source_kind in EVIDENCE_KINDS, 'invalid_evidence_kind')
        need(isinstance(boot_label, str) and LABEL.fullmatch(boot_label), 'invalid_boot_label')
        self.source_kind, self.boot_label = source_kind, boot_label
        self.budget_ms = budget_ms
        self.elapsed_ms = self.index = 0
        self.capabilities = {}
        self.records = []
        self.stopped = False
        self.start_intents = 0
        self.stop_reason = None

    def advance(self, event):
        need(isinstance(event, dict), 'invalid_event')
        need(set(event) <= {'stage', 'outcome', 'duration_ms', 'elapsed_ms', 'source_kind', 'boot_label',
                           'checks', 'start_intent', 'writes_attempted', 'writes_acknowledged',
                           'observation'}, 'unknown_event_field')
        need(not self.stopped and self.index < len(STAGES), 'campaign_closed_no_retry')
        stage = STAGES[self.index]
        need(event.get('stage') == stage.name, 'stage_out_of_order')
        need(event.get('source_kind') == self.source_kind, 'mixed_evidence_kind')
        need(event.get('boot_label') == self.boot_label, 'mixed_boot_session')
        need(event.get('outcome') in OUTCOMES, 'invalid_outcome')
        need(number(event.get('duration_ms'), 3600000), 'invalid_duration')
        need(number(event.get('elapsed_ms'), 3600000) and
             event['elapsed_ms'] >= self.elapsed_ms + event['duration_ms'], 'invalid_elapsed_time')
        need(isinstance(event.get('checks', {}), dict), 'invalid_checks')
        need(set(event.get('checks', {})) <= set(stage.checks), 'unknown_check')
        need(all(type(v) is bool for v in event.get('checks', {}).values()), 'non_boolean_check')
        need(set(stage.requires) <= self.capabilities.keys(), 'prerequisite_unverified')
        observation = event.get('observation', 'not_recorded')
        need(observation in {'not_recorded', 'no_marker_seen', 'early_marker_seen',
                             'reset_identity_seen', 'spin_identity_seen', 'arrival_seen'},
             'unknown_observation')
        record = dict(stage=stage.name, kind=stage.kind, duration_ms=event['duration_ms'],
                      elapsed_ms=event['elapsed_ms'],
                      observation=observation, source_kind=self.source_kind,
                      boot_label=self.boot_label)
        if stage.kind == 'cpu_start':
            need(type(event.get('start_intent')) is bool, 'missing_start_intent')
            attempted, acknowledged = event.get('writes_attempted'), event.get('writes_acknowledged')
            need(number(attempted, 2) and number(acknowledged, attempted), 'invalid_start_counts')
            need(event['start_intent'] or attempted == 0, 'write_without_intent')
            self.start_intents += int(event['start_intent'])
            need(self.start_intents <= 1, 'second_start_forbidden')
            record.update(start_intent=event['start_intent'], writes_attempted=attempted,
                          writes_acknowledged=acknowledged)
            if event['outcome'] == 'pass':
                need(event['start_intent'] and attempted == acknowledged == 2, 'incomplete_start_ack')
        else:
            need(not ({'start_intent', 'writes_attempted', 'writes_acknowledged'} & event.keys()),
                 'start_fields_on_non_start_stage')
        self.elapsed_ms = event['elapsed_ms']
        outcome = event['outcome']
        reason = None
        if event['duration_ms'] > stage.limit_ms:
            outcome, reason = 'timeout', 'stage_deadline'
        elif self.elapsed_ms + EXIT_RESERVE > self.budget_ms:
            outcome, reason = 'timeout', 'campaign_deadline'
        elif outcome == 'pass' and not all(event.get('checks', {}).get(k) is True for k in stage.checks):
            outcome, reason = 'fail', 'checks_incomplete'
        elif outcome == 'unsupported' and stage.optional:
            record['status'] = 'SKIPPED_UNSUPPORTED'
        elif outcome != 'pass':
            reason = 'required_stage_unsupported' if outcome == 'unsupported' else outcome
        if reason is not None:
            self.stopped = True
            self.stop_reason = reason
            record['status'] = 'STOP'
            record['reason'] = reason
        elif outcome == 'pass':
            record['status'] = 'PASS_RECORDED'
            for capability in stage.provides:
                self.capabilities[capability] = {
                    'source_kind': self.source_kind, 'boot_label': self.boot_label,
                    'stage': stage.name, 'scope': ('historical_boot_only' if self.source_kind == 'native_report'
                        else self.source_kind + '_scenario_only'), 'usable_for_live_resume': False,
                }
        self.records.append(record)
        self.index += 1
        return record

    def report(self):
        remaining = [dict(stage=s.name, status='SKIPPED_AFTER_STOP' if self.stopped else 'NOT_REPLAYED')
                     for s in STAGES[self.index:]]
        complete = self.index == len(STAGES) and not self.stopped
        return {
            'schema_version': SCHEMA, 'mode': 'OFFLINE_REPLAY',
            'result': 'MODEL_OR_RECORD_COMPLETE' if complete else 'STOP' if self.stopped else 'INCOMPLETE',
            'source_kind': self.source_kind, 'boot_label': self.boot_label,
            'elapsed_recorded_ms': self.elapsed_ms, 'start_intents': self.start_intents,
            'stop_reason': self.stop_reason, 'records': self.records, 'remaining': remaining,
            'capabilities': self.capabilities, 'eligible_live_operations': [],
            'resume_allowed': False, 'hardware_compatibility_claim': 'NONE', 'limits': LIMITS,
        }


def replay_document(document):
    need(isinstance(document, dict) and set(document) ==
         {'schema_version', 'source_kind', 'boot_label', 'events'}, 'invalid_replay_envelope')
    need(document['schema_version'] == SCHEMA, 'unsupported_schema')
    need(isinstance(document['events'], list) and len(document['events']) <= len(STAGES),
         'invalid_event_count')
    engine = Replay(document['source_kind'], document['boot_label'])
    for event in document['events']:
        engine.advance(event)
    return engine.report()


HISTORICAL_SHAS = {
    'smp31b': 'ea37bdfe6a9f32531c07dcdada340465833e49f7d1ecb72e36c1fe3d814dbd14',
    'smp31c': 'b4021e4669e42732e4f1130f5a997451ecfdcbf94326a6bdd4bd63620cafe208',
    'smp31d': 'e41c9a29748007b08e06e077e45d63deb494eb0b3ec75e0142dc4aeb9f4e3ba5',
}


def historical(document):
    """Summarize real final records without inventing per-stage timing/events."""
    need(isinstance(document, dict), 'invalid_historical_record')
    attempt = document.get('experiment')
    need(attempt in HISTORICAL_SHAS, 'unsupported_historical_attempt')
    need(document.get('source_manifest_sha256') == HISTORICAL_SHAS[attempt], 'historical_manifest_mismatch')
    need(document.get('result') == 'STOP', 'unexpected_historical_result')
    attempted, acknowledged = document.get('start_writes_attempted'), document.get('start_writes_acknowledged')
    need(number(attempted, 2) and number(acknowledged, attempted), 'invalid_start_counts')
    need(document.get('cpu1_arrival_verified') is False and
         number(document.get('requests_completed'), 0),
         'historical_arrival_inconsistent')
    need(document.get('linux_boot') == document.get('native_linux_smp') == 'NOT RUN',
         'historical_linux_inconsistent')
    expected = {'smp31b': ('preflight', 'ram_bounds', 0, 0),
                'smp31c': ('cpu1_arrival', 'cpu1_arrival_timeout', 2, 9),
                'smp31d': ('cpu1_arrival', 'cpu1_arrival_timeout', 2, 13)}[attempt]
    need(number(document.get('mutation_requests'), 13), 'invalid_mutation_count')
    need((document.get('phase'), document.get('reason'), attempted,
          document.get('mutation_requests')) == expected, 'historical_outcome_mismatch')
    need(acknowledged == attempted, 'historical_ack_mismatch')
    out = dict(attempt=attempt, evidence_kind='native_report', outcome='STOP',
        completed_start_requests=acknowledged, native_arrival_verified=False,
        live_resume_allowed=False, eligible_live_operations=[],
        source_manifest_sha256=HISTORICAL_SHAS[attempt],
        cpu1_instruction_execution='UNKNOWN', linux_smp='NOT RUN')
    if attempt == 'smp31b':
        out.update(next_offline_work='repair_and_test_ram_gate', entry_observation='NOT OBSERVED')
    elif attempt == 'smp31c':
        out.update(next_offline_work='diagnose_before_arrival_with_additional_observability',
                   entry_observation='NOT RECORDED')
    else:
        need(document.get('entry_observation') == 'no_reset_record_seen' and
             document.get('arrival_samples') == 171, 'historical_observation_mismatch')
        need(document.get('diagnostic_uart_check') == {
            'direct_usb_proxy': True, 'bases_expected_or_zero': True,
            'enabled_count': 2, 'ram_zeroes_published': True}, 'historical_uart_mismatch')
        out.update(next_offline_work='earlier_entry_instrumentation_and_batched_observer_design',
                   entry_observation='no_reset_record_seen', sequential_samples=171)
    return out


def read_json(path):
    need(path.is_file() and not path.is_symlink(), 'input_file_required')
    need(path.stat().st_size <= 256 * 1024, 'input_too_large')
    return json.loads(path.read_text())


def markdown(document):
    if 'stages' in document:
        lines = ['Offline CPU campaign design — NOT a native handoff', '',
                 'All adapters still need implementation/review; this tool cannot run them.', '',
                 '| Stage | Kind | Bound | Depends on | Optional |',
                 '|---|---|---:|---|---|']
        for row in document['stages']:
            lines.append('| {} | {} | {} ms | {} | {} |'.format(
                row['name'], row['kind'], row['limit_ms'], ', '.join(row['requires']) or 'fresh intake',
                'yes' if row['optional'] else 'no'))
        lines += ['', f"Stage bounds: {document['maximum_stage_total_ms']} ms; "
                  f"reserved margin: {document['reserved_controller_exit_margin_ms']} ms; "
                  f"controller budget: {document['controller_budget_ms']} ms."]
    elif document.get('mode') == 'OFFLINE_REPLAY':
        lines = [f"Offline replay: {document['result']}", '',
                 f"Evidence: {document['source_kind']}; recorded boot: {document['boot_label']}.", '',
                 '| Stage | Outcome | Recorded duration |', '|---|---|---:|']
        lines += [f"| {r['stage']} | {r['status']} | {r['duration_ms']} ms |" for r in document['records']]
        lines += [f"| {r['stage']} | {r['status']} | unknown |" for r in document['remaining']]
        lines += ['', 'Live operations permitted: none. Resume: unavailable. Hardware compatibility claim: none.']
    else:
        lines = [f"Historical report: {document['attempt']}", '',
                 f"Outcome: {document['outcome']}; CPU1 entry: unverified; "
                 f"acknowledged startup writes: {document['completed_start_requests']}.",
                 f"Observation: {document['entry_observation']}. Executed instructions: unknown.",
                 f"Next offline work: {document['next_offline_work']}.",
                 'No hardware resume or unchanged retry is available.']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', choices=('markdown', 'json'), default='markdown')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan'); p.add_argument('--budget-ms', type=int, default=DEFAULT_BUDGET)
    p = sub.add_parser('replay'); p.add_argument('input', type=Path)
    p = sub.add_parser('history'); p.add_argument('input', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'plan':
        document = plan_document(args.budget_ms)
    elif args.command == 'replay':
        document = replay_document(read_json(args.input))
    else:
        document = historical(read_json(args.input))
    print(json.dumps(document, indent=2) if args.format == 'json' else markdown(document), end='\n')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Invalid, OSError, ValueError, TypeError, KeyError):
        # Input may contain private text: never echo arbitrary parser or file errors.
        print('REFUSED: invalid offline input; no operations executed.', file=sys.stderr)
        raise SystemExit(2)
