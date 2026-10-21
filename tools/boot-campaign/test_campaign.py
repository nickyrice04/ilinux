# SPDX-License-Identifier: GPL-2.0-or-later
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import campaign as c


def events(kind='synthetic', boot='fixture-success'):
    rows=[]
    for stage in c.STAGES:
        row=dict(stage=stage.name, outcome='pass', duration_ms=10,
                 source_kind=kind, boot_label=boot, elapsed_ms=(len(rows)+1)*10,
                 checks={check:True for check in stage.checks})
        if stage.kind=='cpu_start':
            row.update(start_intent=True,writes_attempted=2,writes_acknowledged=2)
        rows.append(row)
    return rows


def envelope(rows=None, kind='synthetic', boot='fixture-success'):
    rows=events(kind,boot) if rows is None else rows
    elapsed=0
    for row in rows:
        elapsed += row['duration_ms']; row['elapsed_ms']=elapsed
    return dict(schema_version=1,source_kind=kind,boot_label=boot,events=rows)


class PlanTests(unittest.TestCase):
    def test_one_transition_and_bounded_batch(self):
        plan=c.plan_document()
        self.assertEqual(plan['cpu_start_transitions'],1)
        self.assertLessEqual(plan['maximum_stage_total_ms']+plan['reserved_controller_exit_margin_ms'],60000)
        stages=plan['stages'];start=next(i for i,s in enumerate(stages) if s['kind']=='cpu_start')
        self.assertIn('prestart_bundle',[s['name'] for s in stages[:start]])
        self.assertEqual(plan['status'],'DESIGN_ONLY_NOT_A_LIVE_HANDOFF')

    def test_plan_rejects_overbudget_forward_dependency_and_second_start(self):
        with self.assertRaises(c.Invalid):c.plan_document(50000)
        stage=replace(c.STAGES[0],requires=('future',))
        with self.assertRaisesRegex(c.Invalid,'prerequisite'):c.validate_plan((stage,)+c.STAGES[1:])
        stage=replace(c.STAGES[-1],kind='cpu_start')
        with self.assertRaisesRegex(c.Invalid,'exactly_one'):c.validate_plan(c.STAGES[:-1]+(stage,))

    def test_complete_model_proves_no_live_capability(self):
        result=c.replay_document(envelope())
        self.assertEqual(result['result'],'MODEL_OR_RECORD_COMPLETE')
        self.assertEqual(result['eligible_live_operations'],[])
        self.assertIs(result['resume_allowed'],False)
        self.assertEqual(result['hardware_compatibility_claim'],'NONE')
        self.assertEqual(result['start_intents'],1)
        self.assertTrue(all(not v['usable_for_live_resume'] for v in result['capabilities'].values()))

    def test_vm_static_and_past_native_stay_separate_from_current_boot(self):
        for kind in ('vm_report','static_analysis','native_report'):
            result=c.replay_document(envelope(kind=kind))
            self.assertEqual(result['source_kind'],kind)
            self.assertEqual(result['eligible_live_operations'],[])
            self.assertTrue(all(v['source_kind']==kind and v['scope']==('historical_boot_only' if kind=='native_report' else kind+'_scenario_only')
                                for v in result['capabilities'].values()))

    def test_failed_check_does_not_grant_capability(self):
        row=events()[0];row['checks']['fresh_boot']=False
        result=c.replay_document(envelope([row]))
        self.assertEqual(result['stop_reason'],'checks_incomplete')
        self.assertEqual(result['capabilities'],{})
        self.assertTrue(all(r['status']=='SKIPPED_AFTER_STOP' for r in result['remaining']))

    def test_nonboolean_or_missing_check_cannot_pass(self):
        row=events()[0];row['checks']['fresh_boot']='true'
        with self.assertRaisesRegex(c.Invalid,'non_boolean'):c.replay_document(envelope([row]))
        row=events()[0];del row['checks']['fresh_boot']
        self.assertEqual(c.replay_document(envelope([row]))['result'],'STOP')

    def test_partial_entry_timeout_retains_observation_and_skips_all_requests(self):
        rows=events()[:6]
        rows[-1].update(outcome='timeout',checks={},observation='early_marker_seen',duration_ms=3000)
        result=c.replay_document(envelope(rows))
        self.assertEqual(result['result'],'STOP')
        self.assertEqual(result['records'][-1]['observation'],'early_marker_seen')
        self.assertNotIn('cpu1_arrival',result['capabilities'])
        self.assertEqual([s['stage'] for s in result['remaining']],
                         ['cpu1_timer_pair','cpu1_memory_echo','final_park'])

    def test_late_success_is_timeout_not_permission(self):
        rows=events()[:6];rows[-1]['duration_ms']=3001
        result=c.replay_document(envelope(rows))
        self.assertEqual(result['stop_reason'],'stage_deadline')
        self.assertNotIn('cpu1_arrival',result['capabilities'])

    def test_interstage_gap_counts_toward_controller_deadline(self):
        doc=envelope(events()[:4]);doc['events'][-1]['elapsed_ms']=56000
        result=c.replay_document(doc)
        self.assertEqual(result['stop_reason'],'campaign_deadline')
        self.assertEqual(result['start_intents'],0)
        self.assertNotIn('cpu0_baseline',result['capabilities'])

    def test_elapsed_time_cannot_overlap_or_move_backwards(self):
        doc=envelope(events()[:2]);doc['events'][1]['elapsed_ms']=10
        with self.assertRaisesRegex(c.Invalid,'elapsed_time'):c.replay_document(doc)

    def test_lost_start_reply_has_unknown_completion_and_no_retry(self):
        rows=events()[:5];rows[-1].update(outcome='transport_lost',writes_acknowledged=1,checks={})
        engine=c.Replay('synthetic','fixture-success')
        for row in rows:engine.advance(row)
        result=engine.report()
        self.assertEqual(result['records'][-1]['writes_attempted'],2)
        self.assertEqual(result['records'][-1]['writes_acknowledged'],1)
        self.assertNotIn('start_acknowledged',result['capabilities'])
        with self.assertRaisesRegex(c.Invalid,'no_retry'):engine.advance(rows[-1])

    def test_all_failure_kinds_close_campaign_without_skipping_safety_gate(self):
        for index in range(len(c.STAGES)):
            for outcome in ('fail','timeout','transport_lost'):
                with self.subTest(index=index,outcome=outcome):
                    rows=events()[:index+1];rows[-1].update(outcome=outcome,checks={})
                    result=c.replay_document(envelope(rows))
                    self.assertEqual(result['result'],'STOP')
                    self.assertEqual(result['stop_reason'],outcome)
                    self.assertTrue(all(row['status']=='SKIPPED_AFTER_STOP' for row in result['remaining']))

    def test_optional_unavailable_skips_but_required_unavailable_stops(self):
        rows=events();rows[3].update(outcome='unsupported',checks={})
        rows[7].update(outcome='unsupported',checks={})
        result=c.replay_document(envelope(rows))
        self.assertEqual(result['result'],'MODEL_OR_RECORD_COMPLETE')
        self.assertNotIn('cpu0_baseline',result['capabilities'])
        self.assertNotIn('payload_echo_observed',result['capabilities'])
        self.assertEqual(result['records'][3]['status'],'SKIPPED_UNSUPPORTED')
        row=events()[0];row.update(outcome='unsupported',checks={})
        self.assertEqual(c.replay_document(envelope([row]))['stop_reason'],'required_stage_unsupported')

    def test_out_of_order_duplicate_and_cross_boot_events_refused(self):
        row=events()[1]
        with self.assertRaisesRegex(c.Invalid,'out_of_order'):c.replay_document(envelope([row]))
        rows=events()[:2];rows[1]['boot_label']='another-boot'
        with self.assertRaisesRegex(c.Invalid,'mixed_boot'):c.replay_document(envelope(rows))
        rows=events()[:2];rows[1]['source_kind']='vm_report'
        with self.assertRaisesRegex(c.Invalid,'mixed_evidence'):c.replay_document(envelope(rows))
        row=events()[0]
        with self.assertRaisesRegex(c.Invalid,'out_of_order'):c.replay_document(envelope([row,row]))

    def test_start_pass_requires_intent_and_two_acknowledged_writes(self):
        for attempted,ack,intent in ((2,1,True),(1,1,True),(0,0,False),(2,2,False)):
            rows=events()[:5];rows[-1].update(writes_attempted=attempted,writes_acknowledged=ack,start_intent=intent)
            with self.assertRaises(c.Invalid):c.replay_document(envelope(rows))

    def test_extra_command_fields_and_resume_state_refused(self):
        rows=events()[:1];rows[0]['command']='do-not-execute'
        with self.assertRaisesRegex(c.Invalid,'unknown_event'):c.replay_document(envelope(rows))
        document=envelope();document['resume_state']={'cpu1_arrival':True}
        with self.assertRaisesRegex(c.Invalid,'envelope'):c.replay_document(document)
        with self.assertRaises(TypeError):c.Replay('synthetic','fixture-success',resume={'cpu1_arrival':True})

    def test_new_boot_cannot_inherit_previous_capabilities(self):
        successful=c.replay_document(envelope())
        self.assertIn('cpu1_arrival',successful['capabilities'])
        new=c.Replay('synthetic','new-boot')
        self.assertEqual(new.capabilities,{})
        row=events(boot='new-boot')[6]
        with self.assertRaisesRegex(c.Invalid,'out_of_order'):new.advance(row)

    def test_unknown_source_kind_and_unbounded_event_lists_refused(self):
        doc=envelope(kind='trusted-live')
        with self.assertRaisesRegex(c.Invalid,'evidence_kind'):c.replay_document(doc)
        doc=envelope();doc['events']*=2
        with self.assertRaisesRegex(c.Invalid,'event_count'):c.replay_document(doc)

    def test_public_history_fixtures_preserve_uncertainty(self):
        for name,starts in (('31b',0),('31c',2),('31d',2)):
            doc=json.loads((HERE/'fixtures'/f'{name}-controller.json').read_text())
            result=c.historical(doc)
            self.assertEqual(result['completed_start_requests'],starts)
            self.assertEqual(result['cpu1_instruction_execution'],'UNKNOWN')
            self.assertEqual(result['eligible_live_operations'],[])
        self.assertEqual(result['sequential_samples'],171)
        self.assertEqual(result['next_offline_work'],'earlier_entry_instrumentation_and_batched_observer_design')

    def test_history_does_not_invent_stage_timing_or_promote_changed_record(self):
        doc=json.loads((HERE/'fixtures/31d-controller.json').read_text())
        result=c.historical(doc)
        self.assertNotIn('stage_timings',result)
        doc['start_writes_acknowledged']=1
        with self.assertRaises(c.Invalid):c.historical(doc)
        doc=json.loads((HERE/'fixtures/31d-controller.json').read_text())
        doc['cpu1_arrival_verified']=True
        with self.assertRaises(c.Invalid):c.historical(doc)

    def test_cli_is_offline_and_does_not_echo_private_unknown_input(self):
        result=subprocess.run([sys.executable,'-I',str(HERE/'campaign.py'),'--format','json','plan'],
                              capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(result.stdout)['status'],'DESIGN_ONLY_NOT_A_LIVE_HANDOFF')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'input.json';path.write_text('{private-identifier: secret}')
            result=subprocess.run([sys.executable,'-I',str(HERE/'campaign.py'),'replay',str(path)],
                                  capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertNotIn('secret',result.stdout+result.stderr)
            self.assertNotIn(str(path),result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
