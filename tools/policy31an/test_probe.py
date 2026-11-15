#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original synthetic schema/dispatch/capture controls. No live Apple queries."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('policy31an_tested', Path(__file__).with_name('probe.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Metadata(unittest.TestCase):
    def test_known_aux_absent_and_duplicate_rpnh_are_observations(self):
        value = tool.summarize(b'(auxp): absent\n(rpnh): A\n(rpnh): B\n')
        self.assertIsNone(value['first_unsupported_candidate'])
        self.assertEqual(value['supported_tag_rows'], 2)
        self.assertEqual(value['known_relevant_fields']['auxp']['presence_classes'], ['ABSENT'])

    def test_grouped_tags_use_original_order_and_redact_values(self):
        value = tool.summarize(b'(smb0, auxp, lobo): 1\n')
        self.assertEqual(value['first_unsupported_candidate'],
                         {'class': 'PROTECTED_AUX_PRESENT', 'tag': 'auxp'})
        self.assertEqual(value['unsupported_counts']['PUBLISHED_EXTRA_TAG'], 1)
        self.assertEqual(value['known_relevant_fields']['lobo']['syntax_classes'], ['BOOLEAN'])

    def test_public_extra_keys_distinct_from_other_unknown(self):
        value = tool.summarize(b'(lobo,love): 0\n(Z9X8): SYNTHETIC_PRIVATE_VALUE\n')
        self.assertEqual(value['first_unsupported_candidate']['tag'], 'lobo')
        self.assertEqual(value['other_unknown_tag_rows'], 1)
        self.assertEqual(value['unsupported_counts']['PUBLISHED_EXTRA_TAG'], 2)
        text = json.dumps(value)
        self.assertNotIn('Z9X8', text)
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', text)

    def test_case_sensitive_names_and_first_parentheses_match_c(self):
        value = tool.summarize(b'(BORD): SECRET\n(bord): SECRET\n(label) other (lobo): 1\n')
        self.assertEqual(value['supported_tag_rows'], 1)
        self.assertEqual(value['other_unknown_tag_rows'], 1)
        self.assertNotIn('lobo', value['known_relevant_fields'])

    def test_protected_types_are_syntax_only(self):
        value = tool.summarize(b'(prot): 1234\n(hrlp): 0x1234567890abcdef\n(losv): VERSION_SECRET\n')
        self.assertEqual(value['known_relevant_fields']['prot']['syntax_classes'], ['DECIMAL'])
        self.assertEqual(value['known_relevant_fields']['hrlp']['syntax_classes'], ['HEXLIKE'])
        self.assertEqual(value['known_relevant_fields']['losv']['syntax_classes'], ['OPAQUE'])
        self.assertNotIn('VERSION_SECRET', json.dumps(value))

    def test_invalid_bounds_nul_and_group_grammar(self):
        for raw in (b'', b'A' * 65537, b'\0', b'A' * 2049):
            with self.assertRaises(ValueError):
                tool.summarize(raw)
        for raw in (b'(lobo,): 1', b'(lobo,love,auxp,auxr,auxi): 1', b'(l_ob): SECRET'):
            value = tool.summarize(raw)
            self.assertEqual(value['malformed_tag_rows'], 1)
            self.assertIsNone(value['first_unsupported_candidate'])

    def test_json_structure_redacts_values_and_unknown_keys(self):
        value = tool.json_shape(b'{"SECRET_UUID_KEY":{"lobo":true,"love":["PRIVATE",9]},"ECID":"PRIVATE"}')
        self.assertEqual(value['root_kind'], 'OBJECT')
        self.assertEqual(value['other_key_count'], 1)
        self.assertEqual(value['known_key_shapes']['lobo'], [{'kind': 'BOOLEAN', 'array_items': None}])
        self.assertEqual(value['known_key_shapes']['love'], [{'kind': 'ARRAY', 'array_items': 2}])
        text = json.dumps(value)
        self.assertNotIn('SECRET_UUID_KEY', text)
        self.assertNotIn('PRIVATE', text)

    def test_json_duplicates_depth_nodes_constants_refused(self):
        for raw in (b'{"lobo":1,"lobo":0}', b'[' * 17 + b'0' + b']' * 17,
                    b'[' + b'0,' * 2048 + b'0]', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                tool.json_shape(raw)

    def test_json_repeated_known_shapes_do_not_expand_the_display(self):
        value = tool.json_shape(json.dumps([{'lobo': True}] * 500).encode())
        self.assertEqual(value['known_key_shapes']['lobo'],
                         [{'kind': 'BOOLEAN', 'array_items': None}])
        self.assertLess(len(json.dumps(value)), 500)


class Flow(unittest.TestCase):
    def dependencies(self, change=False):
        observed = {'lab': {'APFSVolumeGroupID': 'SYNTHETIC_LAB'},
                    'original': {'APFSVolumeGroupID': 'SYNTHETIC_ORIGINAL'}}
        backend = types.SimpleNamespace(observe=mock.Mock(side_effect=[observed, observed]))
        stager = types.SimpleNamespace(LiveBackend=mock.Mock(return_value=backend),
            guard_metadata=mock.Mock(side_effect=['BINDING', 'CHANGED' if change else 'BINDING']))
        guard = types.SimpleNamespace(uuid=lambda value: value)
        return (stager, guard, object()), backend

    def live(self, replies, change=False):
        deps, backend = self.dependencies(change)
        with mock.patch.object(tool.sys, 'platform', 'darwin'), mock.patch.object(tool.os, 'geteuid', return_value=0), \
             mock.patch.object(tool, 'load_runtime', return_value=deps), \
             mock.patch.object(tool, 'capture_policy', side_effect=replies) as capture:
            value = tool.run_live()
        return value, backend, capture

    def test_both_roles_text_json_and_fresh_binding(self):
        good = {'failure_reason': None, 'bputil_exit': 0}
        value, backend, capture = self.live([(b'(lobo): 1', good), (b'{"lobo":true}', good),
                                           (b'(auxp): absent', good), (b'{}', good)])
        self.assertTrue(value['metadata_obtained'])
        self.assertTrue(value['target_consistency_rechecked'])
        self.assertEqual(backend.observe.call_count, 2)
        self.assertEqual(capture.call_count, 4)
        self.assertEqual([c.args[-1] if len(c.args) == 3 else False for c in capture.call_args_list],
                         [False, True, False, True])

    def test_json_failure_preserves_text_and_other_role(self):
        good = {'failure_reason': None}
        fail = {'failure_reason': 'BPUTIL_EXIT_NONZERO', 'bputil_exit': 1}
        value, _, capture = self.live([(b'(love): 1', good), (None, fail),
                                      (b'(auxp): absent', good), (b'{}', good)])
        self.assertTrue(value['metadata_obtained'])
        self.assertIsNone(value['roles']['LAB']['json']['shape'])
        self.assertEqual(capture.call_count, 4)

    def test_text_format_failure_still_reads_both_roles(self):
        good = {'failure_reason': None}
        value, _, capture = self.live([(b'\0', good), (b'{}', good),
                                      (b'(auxp): absent', good), (b'{}', good)])
        self.assertFalse(value['metadata_obtained'])
        self.assertIsNotNone(value['roles']['ORIGINAL']['metadata'])
        self.assertEqual(capture.call_count, 4)

    def test_changed_after_binding_refuses_without_identifiers(self):
        good = {'failure_reason': None}
        with self.assertRaises(ValueError):
            self.live([(b'(lobo): 1', good), (b'{}', good),
                       (b'(auxp): absent', good), (b'{}', good)], change=True)

    def test_interrupt_stops_without_more_commands(self):
        interrupted = {'failure_reason': 'BPUTIL_INTERRUPTED'}
        value, backend, capture = self.live([(None, interrupted)])
        self.assertFalse(value['metadata_obtained'])
        self.assertEqual(value['failed_stage'], 'LAB_POLICY_INTERRUPTED')
        self.assertEqual(capture.call_count, 1)
        self.assertEqual(backend.observe.call_count, 1)

    def test_capture_fixed_args_and_private_stderr_discard(self):
        capture = tool.pinned_module(ROOT, tool.CAPTURE, tool.CAPTURE_SHA)
        child = subprocess.Popen([sys.executable, '-I', '-c',
            'import sys;sys.stdout.write("PRIVATE_OUT");sys.stderr.write("PRIVATE_ERR");sys.exit(7)'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with mock.patch.object(tool.subprocess, 'Popen', return_value=child) as spawn:
            raw, result = tool.capture_policy(capture, 'SYNTHETIC_GROUP', True)
        self.assertIsNone(raw)
        self.assertEqual(result['bputil_exit'], 7)
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual(spawn.call_args.args[0], ['/usr/bin/bputil', '-d', '-v', 'SYNTHETIC_GROUP', '-j'])


class Dispatch(unittest.TestCase):
    def call(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = tool.main(args)
        return rc, output.getvalue()

    def test_default_inert_and_bad_args_private(self):
        with mock.patch.object(tool, 'run_live') as live:
            self.assertEqual(self.call([])[0], 0)
            rc, output = self.call(['--PRIVATE_ARGUMENT'])
        live.assert_not_called()
        self.assertEqual(rc, 2)
        self.assertNotIn('PRIVATE_ARGUMENT', output)

    def test_guard_timeout_exception_is_redacted(self):
        with mock.patch.object(tool, 'run_live',
                               side_effect=subprocess.TimeoutExpired(['PRIVATE_COMMAND'], 1)):
            rc, output = self.call(['--live'])
        self.assertEqual(rc, 2)
        self.assertNotIn('PRIVATE_COMMAND', output)
        self.assertFalse(json.loads(output)['metadata_obtained'])

    def test_actual_pinned_runtime_load_is_inert(self):
        with mock.patch.object(tool.subprocess, 'Popen') as spawn:
            stager, guard, capture = tool.load_runtime(ROOT)
        spawn.assert_not_called()
        self.assertTrue(callable(stager.guard_metadata))
        self.assertTrue(callable(guard.disk_info))
        self.assertTrue(callable(capture.collect_process))

    def test_fixture_workspace_only_and_no_live_loader(self):
        base = ROOT / 'build/policy31an-tests'
        base.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(dir=base)).resolve()
        self.addCleanup(shutil.rmtree, directory)
        path = directory / 'fixture.json'
        path.write_text(json.dumps({'schema': 'ilinux31an-synthetic-policy-fixture-v1',
                                   'roles': {'LAB': '(lobo): 1', 'ORIGINAL': '(auxp): absent'}}))
        with mock.patch.object(tool, 'load_runtime') as loader:
            rc, output = self.call(['--fixture', str(path)])
        loader.assert_not_called()
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output)['scope'], 'SYNTHETIC_CONTROL')
        alias = directory / 'alias.json'
        alias.symlink_to(path)
        self.assertEqual(self.call(['--fixture', str(alias)])[0], 2)

    def test_pinned_module_changed_or_symlink_refused_before_execution(self):
        base = ROOT / 'build/policy31an-tests'
        base.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(dir=base)).resolve()
        self.addCleanup(shutil.rmtree, directory)
        path = directory / 'module.py'
        path.write_text('raise RuntimeError("MUST_NOT_EXECUTE")\n')
        with self.assertRaises(ValueError):
            tool.pinned_module(directory, 'module.py', '0' * 64)
        (directory / 'alias.py').symlink_to(path)
        with self.assertRaises(OSError):
            tool.pinned_module(directory, 'alias.py', '0' * 64)


if __name__ == '__main__':
    unittest.main(verbosity=2)
