#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original failure and source-binding tests for offline31Q."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('tested31q', ROOT / 'tools/m1n1-client/attempt31q-offline.py')
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


class IntakeTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        source = root / 'source.py'
        source.write_bytes(b'original synthetic source\n')
        manifest = root / M.MANIFEST
        manifest.parent.mkdir(parents=True)
        line = hashlib.sha256(source.read_bytes()).hexdigest() + '  source.py\n'
        manifest.write_text(line)
        return root, source, manifest, line

    def test_source_content_bound(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(M, 'REQUIRED', {'source.py'}):
            root, source, _, _ = self.fixture(folder)
            self.assertEqual(M.source_pins(root)[0], 1)
            source.write_bytes(b'changed\n')
            with self.assertRaisesRegex(ValueError, '^source_digest$'):
                M.source_pins(root)

    def test_closure_cannot_omit_dependency(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(M, 'REQUIRED', {'source.py', 'required.py'}):
            root, _, _, _ = self.fixture(folder)
            with self.assertRaisesRegex(ValueError, '^manifest_closure$'):
                M.source_pins(root)

    def test_duplicate_traversal_and_noncanonical_paths(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(M, 'REQUIRED', {'source.py'}):
            root, _, manifest, line = self.fixture(folder)
            for text in (line + line, line.replace('source.py', '../source.py'),
                         line.replace('source.py', './source.py'), line.replace('source.py', '/source.py')):
                manifest.write_text(text)
                with self.assertRaises(ValueError):
                    M.source_pins(root)

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(M, 'REQUIRED', {'source.py'}):
            root, source, _, _ = self.fixture(folder)
            target = source.with_name('target.py')
            source.rename(target)
            source.symlink_to(target.name)
            with self.assertRaisesRegex(ValueError, '^source_symlink$'):
                M.source_pins(root)

    def test_child_errors_do_not_expose_output(self):
        failure = subprocess.CompletedProcess(['fixture'], 1, b'PRIVATE_STDOUT', b'PRIVATE_STDERR')
        with patch.object(M.subprocess, 'run', return_value=failure):
            with self.assertRaisesRegex(ValueError, '^offline_check_failed$'):
                M.run(['fixture'])

    def test_skipped_empty_or_uncounted_suite_refused(self):
        for output in (b'Ran 0 tests in 0s\nOK', b'Ran 8 tests in 0s\nOK (skipped=1)', b'OK'):
            with patch.object(M, 'run', return_value=(b'', output)):
                with self.assertRaises(ValueError): M.suite('fixture.py')
        with patch.object(M, 'run', return_value=(b'', b'Ran 8 tests in 0s\nOK')):
            self.assertEqual(M.suite('fixture.py')['methods'], 8)

    def test_prior_result_cannot_promote_native(self):
        good = dict(result='OFFLINE_PASS_NATIVE_HOLD', restart_ready=False,
            native31p='HOLD / NOT RUN', gpu_native_acceleration='NOT RUN',
            cpu1_execution='UNVERIFIED', hardware_operations=0,
            previous_python_methods=63, new_python_methods=59,
            original_c_codec={'result': 'PASS'})
        M.check_previous(good)
        for key, value in [('restart_ready', True), ('native31p', 'PASS'),
                           ('gpu_native_acceleration', 'PASS'), ('cpu1_execution', 'PASS'),
                           ('hardware_operations', 1), ('hardware_operations', False),
                           ('previous_python_methods', True), ('new_python_methods', 0),
                           ('original_c_codec', {'result': 'SKIPPED'})]:
            with self.assertRaises(ValueError, msg=key): M.check_previous(dict(good, **{key: value}))

    def test_argument_errors_are_private_and_offline(self):
        for args in ([], ['--live'], ['--unknown', 'PRIVATE_ARGUMENT_SENTINEL']):
            result = subprocess.run([sys.executable, '-I', str(ROOT / 'tools/m1n1-client/attempt31q-offline.py'), *args], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('PRIVATE_ARGUMENT_SENTINEL', result.stdout + result.stderr)
            parsed = json.loads(result.stdout)
            self.assertIs(parsed['restart_ready'], False)
            self.assertEqual(parsed['hardware_operations'], 0)

    def test_unknown_c_component_cannot_execute(self):
        with patch.object(M, 'run') as run:
            with self.assertRaisesRegex(ValueError, '^component_name$'):
                M.compile_component('../other', 'cc')
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
