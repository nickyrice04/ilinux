#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused synthetic/mocked desktop-wrapper controls; no live Apple queries."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


tool = load('policy31ao_wrapper_tested', Path(__file__).with_name('probe.py'))
scanner = load('policy31ao_scanner_for_wrapper_tests', Path(__file__).with_name('schema.py'))


def native_result(accepted=True):
    return {'schema': 'ilinux31ao-native-policy-parse-v1',
            'scope': 'DESKTOP_SYNTAX_ONLY', 'input_within_bounds': True,
            'old_parser_accepted': False, 'proposed_parser_accepted': accepted,
            'old_failure_line': 1, 'proposed_failure_line': 0 if accepted else 2,
            'read_only': True, 'admission_verified': False, 'native_ready': False,
            'policy_values_returned': False, 'identifiers_returned': False}


def good_capture():
    return {'failure_reason': None, 'bputil_exit': 0, 'stdout_bytes': 42}


def replies():
    return [(b'(lobo): 1\n(love): 26.1.0.1.2,3\n(Q9Z8): PRIVATE_TEXT\n', good_capture()),
            (b'{"CRPO":true,"PRIVATE_KEY":"PRIVATE_JSON"}', good_capture()),
            (b'(auxp): absent\n(smb0 && smb1): true\n', good_capture()),
            (b'{"smb5":false}', good_capture())]


class Files(unittest.TestCase):
    def directory(self):
        base = ROOT / 'build/policy31ao-tests'
        base.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(dir=base)).resolve()
        self.addCleanup(shutil.rmtree, directory)
        return directory

    def test_pinned_leaf_dependencies_load_without_processes(self):
        with mock.patch.object(tool.subprocess, 'Popen') as spawn:
            base = tool.module(ROOT, tool.BASE, tool.BASE_SHA)
            schema = tool.module(ROOT, tool.SCANNER, tool.SCANNER_SHA)
            acl = tool.module(ROOT, tool.ACL_GUARD, tool.ACL_GUARD_SHA)
        spawn.assert_not_called()
        self.assertTrue(callable(base.load_runtime))
        self.assertTrue(callable(schema.scan_text))
        self.assertTrue(callable(acl.no_extended_acl))

    def test_wrong_module_hash_refuses_before_execution(self):
        directory = self.directory()
        (directory / 'leaf.py').write_text('raise RuntimeError("PRIVATE_MUST_NOT_RUN")\n')
        with self.assertRaises(ValueError):
            tool.module(directory, 'leaf.py', '0' * 64)

    def test_module_and_parent_symlinks_refuse(self):
        directory = self.directory()
        actual = directory / 'actual'
        actual.mkdir()
        leaf = actual / 'leaf.py'
        blob = b'ANSWER = 3\n'
        leaf.write_bytes(blob)
        (directory / 'leaf.py').symlink_to(leaf)
        (directory / 'alias').symlink_to(actual, target_is_directory=True)
        for relative in ('leaf.py', 'alias/leaf.py'):
            with self.subTest(relative=relative), self.assertRaises(OSError):
                tool.module(directory, relative, hashlib.sha256(blob).hexdigest())

    def test_bounded_reader_refuses_escape_empty_and_oversize(self):
        directory = self.directory()
        (directory / 'empty').write_bytes(b'')
        (directory / 'large').write_bytes(b'12345')
        for relative, limit in (('../outside', 8), ('/outside', 8), ('empty', 8), ('large', 4)):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                tool.read_bounded(directory, relative, limit)

    def test_same_descriptor_metadata_change_refuses(self):
        directory = self.directory()
        (directory / 'leaf').write_bytes(b'abc')
        original = tool.os.fstat
        calls = []
        def fstat(fd):
            value = original(fd)
            calls.append(fd)
            if len(calls) == 2:
                keys = ('st_mode', 'st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
                changed = {key: getattr(value, key) for key in keys}
                changed['st_mtime_ns'] += 1
                return types.SimpleNamespace(**changed)
            return value
        with mock.patch.object(tool.os, 'fstat', side_effect=fstat), self.assertRaises(ValueError):
            tool.read_bounded(directory, 'leaf', 8)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])

    def test_native_binary_pin_and_symlink_checks(self):
        directory = self.directory()
        blob = b'SYNTHETIC_NOT_EXECUTABLE'
        (directory / 'native').write_bytes(blob)
        (directory / 'alias').symlink_to(directory / 'native')
        with mock.patch.object(tool, 'NATIVE', 'native'), \
             mock.patch.object(tool, 'NATIVE_SHA', hashlib.sha256(blob).hexdigest()):
            tool.check_native(directory)
        with mock.patch.object(tool, 'NATIVE', 'native'), \
             mock.patch.object(tool, 'NATIVE_SHA', '0' * 64), self.assertRaises(ValueError):
            tool.check_native(directory)
        with mock.patch.object(tool, 'NATIVE', 'alias'), \
             mock.patch.object(tool, 'NATIVE_SHA', hashlib.sha256(blob).hexdigest()), self.assertRaises(OSError):
            tool.check_native(directory)


class NativePipe(unittest.TestCase):
    def parse(self, output=None, error=b'', returncode=0, exception=None, raw=b'PRIVATE_RAW'):
        process = types.SimpleNamespace(returncode=returncode, kill=mock.Mock())
        encoded = json.dumps(native_result()).encode() if output is None else output
        process.communicate = mock.Mock(side_effect=[exception, (b'', b'')] if exception else None,
                                        return_value=(encoded, error))
        with mock.patch.object(tool, 'parser_process') as context:
            context.return_value.__enter__.return_value = process
            value = tool.native_parse(Path('/synthetic-root'), raw)
        return value, process, context

    def test_input_uses_private_stdin_fixed_args_and_environment(self):
        value, process, context = self.parse()
        self.assertTrue(value['proposed_parser_accepted'])
        context.assert_called_once_with(Path('/synthetic-root'))
        self.assertNotIn('PRIVATE_RAW', str(context.call_args))
        process.communicate.assert_called_once_with(input=b'PRIVATE_RAW', timeout=5)

    def test_invalid_private_input_refuses_before_process(self):
        for raw in (None, b'', b'x' * 65537):
            with self.subTest(raw_type=type(raw).__name__), \
                 mock.patch.object(tool, 'parser_process') as context, self.assertRaises(ValueError):
                tool.native_parse(ROOT, raw)
            context.assert_not_called()

    def test_schema_is_exact_typed_and_bounded(self):
        changes = ({'PRIVATE_FIELD': 'PRIVATE_VALUE'}, {'scope': 'RECOVERY'},
                   {'schema': 'OTHER'}, {'read_only': 1}, {'native_ready': True},
                   {'old_parser_accepted': 1}, {'input_within_bounds': 'true'},
                   {'old_failure_line': True}, {'proposed_failure_line': -1},
                   {'old_failure_line': 10001}, {'proposed_failure_line': 1.0})
        for change in changes:
            output = native_result()
            output.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.parse(json.dumps(output).encode())
        missing = native_result()
        missing.pop('identifiers_returned')
        for output in (json.dumps(missing).encode(), b'[]', b'PRIVATE_NOT_JSON', b'x' * 2049):
            with self.subTest(output_size=len(output)), self.assertRaises((ValueError, json.JSONDecodeError)):
                self.parse(output)

    def test_duplicate_native_schema_key_refuses(self):
        output = json.dumps(native_result()).encode()
        duplicate = b'{"native_ready":true,' + output[1:]
        with self.assertRaises(ValueError):
            self.parse(duplicate)

    def test_nonzero_or_private_stderr_refuses(self):
        for error, code in ((b'PRIVATE_STDERR', 0), (b'', 2)):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.parse(error=error, returncode=code)

    def test_timeout_kills_and_drains_private_child(self):
        process = types.SimpleNamespace(returncode=None, kill=mock.Mock())
        process.communicate = mock.Mock(side_effect=[subprocess.TimeoutExpired(['PRIVATE_CMD'], 5),
                                                    (b'PRIVATE_OUT', b'PRIVATE_ERR')])
        with mock.patch.object(tool, 'parser_process') as context:
            context.return_value.__enter__.return_value = process
            with self.assertRaises(subprocess.TimeoutExpired):
                tool.native_parse(ROOT, b'PRIVATE_RAW')
        process.kill.assert_called_once_with()
        self.assertEqual(process.communicate.call_count, 2)


class ScratchExecution(unittest.TestCase):
    def directory(self):
        base = ROOT / 'build/policy31ao-tests'
        base.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(dir=base)).resolve()
        (directory / 'build').mkdir()
        self.addCleanup(shutil.rmtree, directory)
        guard = tool.read_bounded(ROOT, tool.ACL_GUARD, tool.LIMIT)
        self.assertEqual(hashlib.sha256(guard).hexdigest(), tool.ACL_GUARD_SHA)
        leaf = directory / tool.ACL_GUARD
        leaf.parent.mkdir(parents=True)
        leaf.write_bytes(guard)
        return directory

    def trusted_bytes(self):
        if not (ROOT / tool.NATIVE).is_file():
            self.skipTest('Pinned original desktop parser has not been built')
        return tool.check_native(ROOT)

    def test_actual_original_parser_private_copy_permissions_and_cleanup(self):
        directory = self.directory()
        data = self.trusted_bytes()
        prior_cwd = Path.cwd()
        with mock.patch.object(tool, 'check_native', return_value=data):
            with tool.parser_process(directory) as child:
                self.assertEqual(Path.cwd(), prior_cwd)
                entries = list((directory / 'build').iterdir())
                self.assertEqual(len(entries), 1)
                scratch = entries[0]
                executable = scratch / 'desktop-parser'
                self.assertEqual(scratch.stat().st_uid, tool.os.geteuid())
                self.assertEqual(scratch.stat().st_mode & 0o777, 0o700)
                self.assertEqual(executable.stat().st_mode & 0o777, 0o500)
                self.assertEqual(executable.stat().st_nlink, 1)
                self.assertEqual(executable.read_bytes(), data)
                self.assertEqual([p.name for p in scratch.iterdir()], ['desktop-parser'])
                output, error = child.communicate(input=b'(Q9Z8): PRIVATE_SYNTHETIC_POLICY\n', timeout=5)
                self.assertEqual(child.returncode, 0)
                self.assertEqual(error, b'')
                self.assertNotIn(b'PRIVATE_SYNTHETIC_POLICY', output)
                self.assertEqual(json.loads(output)['scope'], 'DESKTOP_SYNTAX_ONLY')
        self.assertEqual(Path.cwd(), prior_cwd)
        self.assertEqual(list((directory / 'build').iterdir()), [])

    def test_ancestor_rename_keeps_verified_execution_and_cleanup_bound(self):
        directory = self.directory()
        data = self.trusted_bytes()
        prior_cwd = Path.cwd()
        spawn = tool.subprocess.Popen
        calls = []
        def renamed_spawn(argv, **kwargs):
            calls.append((argv, kwargs))
            self.assertEqual(Path.cwd().parent, directory / 'build')
            (directory / 'build').rename(directory / 'moved-build')
            return spawn(argv, **kwargs)
        with mock.patch.object(tool, 'check_native', return_value=data), \
             mock.patch.object(tool.subprocess, 'Popen', side_effect=renamed_spawn):
            value = tool.native_parse(directory, b'PRIVATE_SYNTHETIC_POLICY\n')
        self.assertFalse(value['native_ready'])
        self.assertEqual(Path.cwd(), prior_cwd)
        self.assertEqual(list((directory / 'moved-build').iterdir()), [])
        self.assertEqual(calls[0][0], ['./desktop-parser', '--stdin'])
        self.assertIs(calls[0][1]['stdin'], subprocess.PIPE)
        self.assertEqual(calls[0][1]['env']['LC_ALL'], 'C')
        self.assertNotIn('PRIVATE_SYNTHETIC_POLICY', str(calls))

    def test_spawn_and_write_failure_restore_cwd_and_remove_owned_scratch(self):
        directory = self.directory()
        prior_cwd = Path.cwd()
        with mock.patch.object(tool, 'check_native', return_value=b'SYNTHETIC_BYTES'), \
             mock.patch.object(tool.subprocess, 'Popen', side_effect=OSError('PRIVATE_SPAWN')):
            with self.assertRaises(OSError):
                with tool.parser_process(directory):
                    self.fail('Spawn failure must not yield a child')
        self.assertEqual(Path.cwd(), prior_cwd)
        self.assertEqual(list((directory / 'build').iterdir()), [])
        with mock.patch.object(tool, 'check_native', return_value=b'SYNTHETIC_BYTES'), \
             mock.patch.object(tool.os, 'write', return_value=0), \
             mock.patch.object(tool.subprocess, 'Popen') as spawn:
            with self.assertRaises(ValueError):
                with tool.parser_process(directory):
                    self.fail('Failed write must not yield a child')
        spawn.assert_not_called()
        self.assertEqual(Path.cwd(), prior_cwd)
        self.assertEqual(list((directory / 'build').iterdir()), [])

    def test_replaced_scratch_directory_is_not_removed(self):
        directory = self.directory()
        process = types.SimpleNamespace(poll=mock.Mock(return_value=0))
        replacement = moved = None
        with mock.patch.object(tool, 'check_native', return_value=b'SYNTHETIC_BYTES'), \
             mock.patch.object(tool.subprocess, 'Popen', return_value=process):
            with self.assertRaises(ValueError):
                with tool.parser_process(directory):
                    original = next((directory / 'build').iterdir())
                    moved = original.with_name(original.name + '-moved')
                    original.rename(moved)
                    original.mkdir(mode=0o700)
                    replacement = original / 'keep'
                    replacement.write_text('SYNTHETIC_UNRELATED_FILE')
        self.assertEqual(replacement.read_text(), 'SYNTHETIC_UNRELATED_FILE')
        self.assertEqual(list(moved.iterdir()), [])

    def test_replaced_executable_is_not_removed(self):
        directory = self.directory()
        process = types.SimpleNamespace(poll=mock.Mock(return_value=0))
        replacement = original = None
        with mock.patch.object(tool, 'check_native', return_value=b'SYNTHETIC_BYTES'), \
             mock.patch.object(tool.subprocess, 'Popen', return_value=process):
            with self.assertRaises(ValueError):
                with tool.parser_process(directory):
                    scratch = next((directory / 'build').iterdir())
                    replacement = scratch / 'desktop-parser'
                    original = scratch / 'retained-original'
                    replacement.rename(original)
                    replacement.write_bytes(b'SYNTHETIC_UNRELATED_FILE')
        self.assertEqual(replacement.read_bytes(), b'SYNTHETIC_UNRELATED_FILE')
        self.assertEqual(original.read_bytes(), b'SYNTHETIC_BYTES')

    def test_directory_and_file_acl_refusal_precede_writes_or_spawn(self):
        for outcomes in ([False], [True, False]):
            with self.subTest(outcomes=outcomes):
                directory = self.directory()
                acl = types.SimpleNamespace(no_extended_acl=mock.Mock(side_effect=outcomes))
                with mock.patch.object(tool, 'module', return_value=acl), \
                     mock.patch.object(tool, 'check_native', return_value=b'SYNTHETIC_BYTES'), \
                     mock.patch.object(tool.os, 'write') as write, \
                     mock.patch.object(tool.subprocess, 'Popen') as spawn:
                    with self.assertRaises(ValueError):
                        with tool.parser_process(directory):
                            self.fail('ACL refusal must not yield a child')
                self.assertEqual(acl.no_extended_acl.call_count, len(outcomes))
                write.assert_not_called()
                spawn.assert_not_called()
                self.assertEqual(list((directory / 'build').iterdir()), [])


class Flow(unittest.TestCase):
    def context(self, captures=None, native=None, changed=False):
        observed = {'lab': {'APFSVolumeGroupID': 'PRIVATE_LAB_GROUP'},
                    'original': {'APFSVolumeGroupID': 'PRIVATE_ORIGINAL_GROUP'}}
        backend = types.SimpleNamespace(observe=mock.Mock(side_effect=[copy.deepcopy(observed),
                                                                      copy.deepcopy(observed)]))
        stager = types.SimpleNamespace(LiveBackend=mock.Mock(return_value=backend),
            guard_metadata=mock.Mock(side_effect=['PRIVATE_BINDING',
                                                  'PRIVATE_CHANGED' if changed else 'PRIVATE_BINDING']))
        guard = types.SimpleNamespace(uuid=lambda value: value)
        capture = mock.Mock(side_effect=replies() if captures is None else captures)
        base = types.SimpleNamespace(load_runtime=mock.Mock(return_value=(stager, guard, object())),
                                     capture_policy=capture)
        def dependency(root, name, digest):
            self.assertEqual((name, digest), (tool.BASE, tool.BASE_SHA) if name == tool.BASE
                             else (tool.SCANNER, tool.SCANNER_SHA))
            return base if name == tool.BASE else scanner
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(tool.sys, 'platform', 'darwin'))
        stack.enter_context(mock.patch.object(tool.os, 'geteuid', return_value=0))
        stack.enter_context(mock.patch.object(tool, 'module', side_effect=dependency))
        pin = stack.enter_context(mock.patch.object(tool, 'check_native'))
        parse = stack.enter_context(mock.patch.object(tool, 'native_parse',
            side_effect=[native_result(), native_result()] if native is None else native))
        return stack, backend, stager, capture, parse, pin

    def live(self, **kwargs):
        stack, backend, stager, capture, parse, pin = self.context(**kwargs)
        with stack:
            value = tool.run_live(Path('/synthetic-root'))
        return value, backend, stager, capture, parse, pin

    def test_four_captures_two_roles_two_private_native_parses(self):
        value, backend, stager, capture, parse, pin = self.live()
        self.assertTrue(value['metadata_obtained'])
        self.assertTrue(value['both_proposed_parsers_accepted'])
        self.assertTrue(value['target_consistency_rechecked'])
        self.assertEqual(capture.call_count, 4)
        self.assertEqual(parse.call_count, 2)
        self.assertEqual(backend.observe.call_count, 2)
        self.assertEqual(stager.guard_metadata.call_count, 2)
        self.assertEqual(pin.call_count, 2)
        self.assertEqual([c.args[1:] for c in capture.call_args_list],
                         [('PRIVATE_LAB_GROUP',), ('PRIVATE_LAB_GROUP', True),
                          ('PRIVATE_ORIGINAL_GROUP',), ('PRIVATE_ORIGINAL_GROUP', True)])
        self.assertEqual([c.args[1] for c in parse.call_args_list],
                         [replies()[0][0], replies()[2][0]])
        self.assertFalse(value['native_ready'])
        self.assertFalse(value['admission_verified'])

    def test_compact_observation_retains_counts_and_no_input_content(self):
        value, *_ = self.live()
        lab = value['roles']['LAB']
        self.assertEqual(lab['text']['fields']['lobo']['predicates']['boolean'], 1)
        self.assertEqual(lab['text']['unknown_tag_occurrences'], 1)
        self.assertEqual(lab['json']['shape']['fields']['CRPO']['kinds'], {'BOOLEAN': 1})
        self.assertIn('auxp', lab['text']['unseen_catalog_fields'])
        self.assertNotIn('auxp', lab['text']['fields'])
        encoded = json.dumps(value)
        for marker in ('Q9Z8', 'PRIVATE_TEXT', 'PRIVATE_KEY', 'PRIVATE_JSON',
                       'PRIVATE_LAB_GROUP', 'PRIVATE_BINDING', '26.1.0.1.2,3'):
            self.assertNotIn(marker, encoded)

    def test_changed_fresh_binding_refuses(self):
        stack, backend, stager, capture, parse, pin = self.context(changed=True)
        with stack, self.assertRaises(ValueError):
            tool.run_live(Path('/synthetic-root'))
        self.assertEqual(backend.observe.call_count, 2)
        self.assertEqual(capture.call_count, 4)

    def test_native_failure_does_not_erase_text_or_other_role(self):
        value, _, _, capture, parse, _ = self.live(
            native=[RuntimeError('PRIVATE_NATIVE_DETAIL'), native_result()])
        self.assertTrue(value['metadata_obtained'])
        self.assertFalse(value['both_proposed_parsers_accepted'])
        self.assertEqual(value['roles']['LAB']['native_failure'], 'DESKTOP_PARSER_CHECK_FAILED')
        self.assertIsNotNone(value['roles']['ORIGINAL']['native_syntax'])
        self.assertEqual((capture.call_count, parse.call_count), (4, 2))
        self.assertNotIn('PRIVATE_NATIVE_DETAIL', json.dumps(value))

    def test_capture_failures_preserve_other_role_and_json_stage(self):
        captures = replies()
        captures[0] = (None, {'failure_reason': 'BPUTIL_EXIT_NONZERO', 'bputil_exit': 1})
        captures[1] = (b'PRIVATE_PREFIX {"lobo":true}', good_capture())
        value, _, _, capture, parse, _ = self.live(captures=captures)
        self.assertFalse(value['metadata_obtained'])
        self.assertEqual(value['roles']['LAB']['json']['shape']['failure_stage'], 'ENVELOPE')
        self.assertIsNotNone(value['roles']['ORIGINAL']['text'])
        self.assertEqual((capture.call_count, parse.call_count), (4, 1))
        self.assertNotIn('PRIVATE_PREFIX', json.dumps(value))

    def test_text_and_json_interrupt_stop_further_work(self):
        for index, label, parse_count in ((0, 'LAB_TEXT_INTERRUPTED', 0),
                                           (1, 'LAB_JSON_INTERRUPTED', 1),
                                           (2, 'ORIGINAL_TEXT_INTERRUPTED', 1)):
            captures = replies()[:index] + [(None, {'failure_reason': 'BPUTIL_INTERRUPTED'})]
            value, backend, _, capture, parse, _ = self.live(captures=captures)
            with self.subTest(label=label):
                self.assertEqual(value['failed_stage'], label)
                self.assertEqual(capture.call_count, index + 1)
                self.assertEqual(parse.call_count, parse_count)
                self.assertEqual(backend.observe.call_count, 1)

    def test_native_interrupt_stops_before_json_capture(self):
        value, backend, _, capture, parse, _ = self.live(native=[KeyboardInterrupt()])
        self.assertEqual(value['failed_stage'], 'LAB_NATIVE_INTERRUPTED')
        self.assertEqual((capture.call_count, parse.call_count), (1, 1))
        self.assertEqual(backend.observe.call_count, 1)


class Dispatch(unittest.TestCase):
    def call(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = tool.main(args)
        return code, output.getvalue()

    def test_default_help_and_bad_args_are_inert_without_reflection(self):
        with mock.patch.object(tool, 'run_live') as live, \
             mock.patch.object(tool, 'module') as module:
            self.assertEqual(self.call([])[0], 0)
            with self.assertRaises(SystemExit) as stop:
                self.call(['--help'])
            self.assertEqual(stop.exception.code, 0)
            code, output = self.call(['--PRIVATE_ARGUMENT'])
        self.assertEqual(code, 2)
        self.assertNotIn('PRIVATE_ARGUMENT', output)
        live.assert_not_called()
        module.assert_not_called()

    def test_guard_timeout_exception_and_interrupt_are_redacted(self):
        for exception in (subprocess.TimeoutExpired(['PRIVATE_COMMAND'], 2),
                          RuntimeError('PRIVATE_MESSAGE'), KeyboardInterrupt()):
            with mock.patch.object(tool, 'run_live', side_effect=exception):
                code, output = self.call(['--live'])
            with self.subTest(exception=type(exception).__name__):
                self.assertEqual(code, 2)
                value = json.loads(output)
                self.assertEqual(value['failed_stage'], 'GUARD_OR_RUNTIME')
                self.assertFalse(value['native_ready'])
                self.assertNotIn('PRIVATE', output)

    def test_non_darwin_or_nonroot_refuses_before_dependency_load(self):
        for platform, uid in (('linux', 0), ('darwin', 501)):
            with mock.patch.object(tool.sys, 'platform', platform), \
                 mock.patch.object(tool.os, 'geteuid', return_value=uid), \
                 mock.patch.object(tool, 'module') as dependency:
                code, output = self.call(['--live'])
            self.assertEqual(code, 2)
            self.assertFalse(json.loads(output)['metadata_obtained'])
            dependency.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
