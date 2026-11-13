# SPDX-License-Identifier: MIT
"""Synthetic metadata/own-process controls. Never invokes actual bputil/root."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock,patch

SPEC=importlib.util.spec_from_file_location('probe',Path(__file__).with_name('schema_probe.py'))
p=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(p)

def raw_rows():return b''.join(f'Known ({key}): absent\n'.encode() for key in sorted(p.FIELDS))
def own_process(code):
    return subprocess.Popen([sys.executable,'-I','-c',code],stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
def diagnostic(code=0,n=64,stderr=False):
    return {'failure_kind':None,'failure_reason':None,'bputil_exit':code,'stdout_bytes':n,
            'stderr_present':stderr,'stderr_complete':True,'stdout_limit_exceeded':False}
def backend():
    return types.SimpleNamespace(LAB_MOUNT='/synthetic-lab',MAX_POLICY=65536,
      require=lambda v:None if v else (_ for _ in ()).throw(ValueError()),
      capture=Mock(side_effect=[b'Mac17,6\n',b'synthetic-apfs']),
      disk_info=Mock(side_effect=[{'fixture':'lab'},{'VolumeName':'Macintosh HD','APFSVolumeGroupID':'SYNTHETIC_ORIGINAL_GROUP'}]),
      plistlib=types.SimpleNamespace(loads=lambda v:{'synthetic':True}),
      guard_target=Mock(return_value={'group':'SYNTHETIC_LAB_GROUP'}),uuid=lambda v:v)

class Probe(unittest.TestCase):
    def test_values_and_unlisted_identifiers_never_returned(self):
        raw=b'Known (prot): PRIVATE_MARKER\nOther (losv): absent\nidentity (ECID): PRIVATE_IDENTIFIER\n'
        out=p.summarize(raw)
        self.assertEqual(out['known_metadata_present'],['prot']);self.assertEqual(out['known_metadata_absent'],['losv'])
        self.assertEqual(out['known_metadata_unseen'],sorted(p.FIELDS-{'prot','losv'}))
        self.assertNotIn('PRIVATE',json.dumps(out));self.assertFalse(out['all_fixed_fields_observed'])
    def test_all_fixed_fields_observed_without_value_output(self):
        out=p.summarize(raw_rows());self.assertTrue(out['all_fixed_fields_observed']);self.assertTrue(out['format_qualified'])
        self.assertEqual(out['known_metadata_absent'],sorted(p.FIELDS));self.assertEqual(out['known_metadata_present'],[])
    def test_unknown_rows_never_become_absent_fields(self):
        out=p.summarize(b'Other (smb0): absent\n')
        self.assertEqual(out['known_metadata_unseen'],sorted(p.FIELDS));self.assertEqual(out['known_metadata_absent'],[])
        self.assertEqual(out['format_reason'],'NO_KNOWN_METADATA_ROWS');self.assertFalse(out['format_qualified'])
    def test_duplicate_absent_rows_reported_instead_of_exception(self):
        out=p.summarize(b'Known (prot): absent\nKnown (prot): absent\n')
        self.assertEqual(out['known_metadata_duplicated'],['prot']);self.assertEqual(out['known_metadata_row_counts'],{'prot':2})
        self.assertEqual(out['known_metadata_absent'],['prot']);self.assertEqual(out['format_reason'],'DUPLICATE_METADATA_ROWS')
    def test_conflicting_presence_not_resolved_using_first_or_last_row(self):
        for raw in (b'x (prot): absent\nx (prot): PRIVATE\n',b'x (prot): PRIVATE\nx (prot): absent\n'):
            out=p.summarize(raw);self.assertEqual(out['known_metadata_conflicting_presence'],['prot'])
            self.assertEqual(out['known_metadata_present'],[]);self.assertEqual(out['known_metadata_absent'],[])
            self.assertEqual(out['format_reason'],'CONFLICTING_METADATA_PRESENCE');self.assertNotIn('PRIVATE',json.dumps(out))
    def test_different_values_only_report_duplicate_presence(self):
        out=p.summarize(b'x (prot): PRIVATE_ONE\nx (prot): PRIVATE_TWO\n')
        self.assertEqual(out['known_metadata_present'],['prot']);self.assertEqual(out['known_metadata_conflicting_presence'],[])
        self.assertEqual(out['known_metadata_duplicated'],['prot']);self.assertNotIn('PRIVATE',json.dumps(out))
    def test_empty_field_is_neither_present_nor_absent(self):
        out=p.summarize(b'x (prot): \n');self.assertEqual(out['known_metadata_empty'],['prot'])
        self.assertEqual(out['known_metadata_present'],[]);self.assertEqual(out['known_metadata_absent'],[])
        self.assertEqual(out['format_reason'],'EMPTY_METADATA_ROWS')
    def test_malformed_fixed_field_has_explicit_format_reason(self):
        out=p.summarize(b'Known (prot) missing-colon PRIVATE\n')
        self.assertEqual(out['known_metadata_malformed'],['prot']);self.assertNotIn('prot',out['known_metadata_unseen'])
        self.assertEqual(out['format_reason'],'MALFORMED_METADATA_ROWS');self.assertNotIn('PRIVATE',json.dumps(out))
    def test_bound_nul_and_empty_refusals_have_fixed_reasons(self):
        for raw in (b'\0',b'x'*65537,b''):
            with self.assertRaises(p.ProbeFailure):p.summarize(raw)
            self.assertEqual(p.failure_kind,'FORMAT');self.assertIn(p.failure_reason,p.FORMAT_REASONS)
    def test_explicit_absent_case_and_spacing(self):
        out=p.summarize(b'x (prot) : Absent\n')
        self.assertEqual(out['known_metadata_absent'],['prot'])
    def test_default_has_no_host_calls(self):
        with patch.object(p,'run') as run,contextlib.redirect_stdout(io.StringIO()):self.assertEqual(p.main([]),0)
        run.assert_not_called()
    def test_failure_details_not_echoed(self):
        out=io.StringIO()
        with patch.object(p,'run',side_effect=ValueError('PRIVATE_DETAIL')),contextlib.redirect_stdout(out):self.assertEqual(p.main(['--live']),2)
        self.assertNotIn('PRIVATE',out.getvalue());self.assertFalse(json.loads(out.getvalue())['settings_changed'])
    def test_stage_is_fixed_enum_not_external_content(self):
        out=io.StringIO()
        with patch.object(p,'stage','PRIVATE_STAGE'),patch.object(p,'run',side_effect=ValueError()),contextlib.redirect_stdout(out):p.main(['--live'])
        self.assertEqual(json.loads(out.getvalue())['failed_stage'],'REFUSED')

class Capture(unittest.TestCase):
    def test_completed_process_keeps_only_stderr_presence(self):
        proc=own_process("import sys;sys.stdout.buffer.write(b'x (prot): absent\\n');sys.stderr.write('PRIVATE_STDERR')")
        raw,d=p.collect_process(proc,seconds=3)
        self.assertEqual(raw,b'x (prot): absent\n');self.assertEqual(d['bputil_exit'],0)
        self.assertEqual(d['stdout_bytes'],len(raw));self.assertTrue(d['stderr_present']);self.assertTrue(d['stderr_complete'])
        self.assertNotIn('PRIVATE',json.dumps(d));self.assertIsNone(d['failure_reason'])
    def test_nonzero_exit_is_read_failure_not_format_failure(self):
        proc=own_process("import sys;sys.stderr.write('PRIVATE_FAILURE');sys.exit(7)")
        raw,d=p.collect_process(proc,seconds=3)
        self.assertEqual(raw,b'');self.assertEqual(d['failure_kind'],'READ');self.assertEqual(d['failure_reason'],'BPUTIL_EXIT_NONZERO')
        self.assertEqual(d['bputil_exit'],7);self.assertTrue(d['stderr_present']);self.assertNotIn('PRIVATE',json.dumps(d))
    def test_zero_exit_empty_stdout_is_distinct_read_failure(self):
        proc=own_process("import sys;sys.stderr.write('PRIVATE_ONLY_STDERR')")
        raw,d=p.collect_process(proc,seconds=3)
        self.assertEqual(raw,b'');self.assertEqual(d['bputil_exit'],0);self.assertEqual(d['failure_reason'],'BPUTIL_STDOUT_EMPTY')
        self.assertTrue(d['stderr_present'])
    def test_stdout_cap_reports_lower_bound_without_extra_storage(self):
        proc=own_process("import sys;sys.stdout.buffer.write(b'x'*4096)")
        raw,d=p.collect_process(proc,cap=64,seconds=3)
        self.assertEqual(len(raw),65);self.assertEqual(d['stdout_bytes'],65)
        self.assertTrue(d['stdout_limit_exceeded']);self.assertEqual(d['failure_reason'],'BPUTIL_STDOUT_LIMIT')
    def test_timeout_has_no_exception_or_process_text_output(self):
        proc=own_process('import time;time.sleep(2)')
        _,d=p.collect_process(proc,seconds=.2)
        self.assertEqual(d['failure_reason'],'BPUTIL_TIMEOUT');self.assertEqual(d['failure_kind'],'READ')
        self.assertIsInstance(d['bputil_exit'],int)
    def test_large_stderr_is_drained_not_returned(self):
        proc=own_process("import sys;sys.stderr.write('PRIVATE'*100000);sys.stdout.write('x (prot): absent\\n')")
        raw,d=p.collect_process(proc,seconds=3)
        self.assertTrue(d['stderr_present']);self.assertTrue(d['stderr_complete']);self.assertIsNone(d['failure_reason'])
        self.assertLess(len(json.dumps(d)),350);self.assertNotIn('PRIVATE',json.dumps(d))
    def test_interruption_is_a_fixed_read_reason_and_reaps_child(self):
        proc=own_process('import time;time.sleep(2)')
        with patch.object(p.selectors.DefaultSelector,'select',side_effect=KeyboardInterrupt()):
            _,d=p.collect_process(proc,seconds=3)
        self.assertEqual(d['failure_reason'],'BPUTIL_INTERRUPTED');self.assertEqual(d['failure_kind'],'READ')
        self.assertIsNotNone(proc.poll())
    def test_policy_capture_uses_only_fixed_read_command_and_private_group_argument(self):
        proc=own_process("import sys;sys.stdout.write('x (prot): absent\\n')")
        with patch.object(p.subprocess,'Popen',return_value=proc) as spawn:
            raw=p.capture_policy('SYNTHETIC_PRIVATE_GROUP')
        self.assertEqual(raw,b'x (prot): absent\n')
        self.assertEqual(spawn.call_args.args[0],['/usr/bin/bputil','-d','-v','SYNTHETIC_PRIVATE_GROUP'])
        self.assertNotIn('PRIVATE',json.dumps(p.policy_diagnostic))
    def test_spawn_failure_never_echoes_command_or_exception(self):
        with patch.object(p.subprocess,'Popen',side_effect=OSError('PRIVATE_PATH')):
            with self.assertRaises(p.ProbeFailure):p.capture_policy('SYNTHETIC_PRIVATE_GROUP')
        self.assertEqual(p.failure_reason,'BPUTIL_EXEC_FAILURE');self.assertIsNone(p.policy_diagnostic['bputil_exit'])
        self.assertNotIn('PRIVATE',json.dumps(p.policy_diagnostic))

class Workflow(unittest.TestCase):
    def invoke(self,policy_reader):
        out=io.StringIO();b=backend()
        with patch.object(p.sys,'platform','darwin'),patch.object(p.os,'geteuid',return_value=0), \
             patch.object(p,'load_helper',return_value=b),patch.object(p,'capture_policy',side_effect=policy_reader) as read, \
             contextlib.redirect_stdout(out):
            result=p.main(['--live'])
        return result,json.loads(out.getvalue()),read
    def test_duplicate_lab_format_still_collects_original_metadata_once(self):
        def reader(group):
            p.policy_diagnostic=diagnostic()
            return b'x (prot): absent\nx (prot): PRIVATE_DUPLICATE\n' if group=='SYNTHETIC_LAB_GROUP' else raw_rows()
        code,out,read=self.invoke(reader)
        self.assertEqual(code,2);self.assertEqual(out['failed_stage'],'LAB_POLICY');self.assertEqual(out['failure_kind'],'FORMAT')
        self.assertEqual(out['failure_reason'],'CONFLICTING_METADATA_PRESENCE');self.assertEqual(read.call_count,2)
        self.assertTrue(out['roles']['ORIGINAL']['metadata']['all_fixed_fields_observed'])
        self.assertEqual(out['roles']['LAB']['read_diagnostic']['bputil_exit'],0)
        self.assertNotIn('PRIVATE',json.dumps(out));self.assertNotIn('GROUP',json.dumps(out))
    def test_lab_read_failure_does_not_hide_original_metadata(self):
        def reader(group):
            p.policy_diagnostic=diagnostic()
            if group=='SYNTHETIC_LAB_GROUP':
                p.policy_diagnostic.update(failure_kind='READ',failure_reason='BPUTIL_EXIT_NONZERO',bputil_exit=3,stderr_present=True)
                p.fail('READ','BPUTIL_EXIT_NONZERO')
            return raw_rows()
        code,out,read=self.invoke(reader)
        self.assertEqual(code,2);self.assertEqual(out['failure_kind'],'READ');self.assertEqual(out['policy_read_diagnostic']['bputil_exit'],3)
        self.assertEqual(read.call_count,2);self.assertIsNone(out['roles']['LAB']['metadata'])
        self.assertTrue(out['partial_metadata_obtained'])
    def test_both_roles_complete_has_no_identity_values(self):
        def reader(group):p.policy_diagnostic=diagnostic();return raw_rows()
        code,out,read=self.invoke(reader)
        self.assertEqual(code,0);self.assertTrue(out['metadata_obtained']);self.assertEqual(read.call_count,2)
        self.assertFalse(out['identifiers_returned']);self.assertFalse(out['policy_values_returned'])
        self.assertNotIn('GROUP',json.dumps(out))
    def test_nul_is_format_failure_after_successful_command(self):
        def reader(group):p.policy_diagnostic=diagnostic(n=1);return b'\0' if group=='SYNTHETIC_LAB_GROUP' else raw_rows()
        code,out,_=self.invoke(reader)
        self.assertEqual(code,2);self.assertEqual(out['failure_kind'],'FORMAT');self.assertEqual(out['failure_reason'],'POLICY_NUL')
        self.assertEqual(out['policy_read_diagnostic']['bputil_exit'],0)

if __name__=='__main__':unittest.main()
