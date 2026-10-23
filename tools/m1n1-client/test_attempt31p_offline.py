#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Adversarial source binding and result checks for the offline-only handoff."""
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
spec = importlib.util.spec_from_file_location('offline31p_tested',
    ROOT / 'tools/m1n1-client/attempt31p-offline.py')
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


class IntakeTests(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        source = root / 'checked.py'
        source.write_bytes(b'original fixture\n')
        manifest = root / M.MANIFEST
        manifest.parent.mkdir(parents=True)
        line = hashlib.sha256(source.read_bytes()).hexdigest() + '  checked.py\n'
        manifest.write_text(line)
        return source, manifest, line

    def test_manifest_binds_contents(self):
        with tempfile.TemporaryDirectory() as d, patch.object(M, 'REQUIRED', {'checked.py'}):
            source, _, _ = self.fixture(d)
            self.assertEqual(M.source_pins(Path(d))[0], 1)
            source.write_bytes(b'replacement\n')
            with self.assertRaisesRegex(ValueError, '^source_digest$'):
                M.source_pins(Path(d))

    def test_manifest_requires_exact_set(self):
        with tempfile.TemporaryDirectory() as d, patch.object(M, 'REQUIRED', {'checked.py', 'absent.py'}):
            self.fixture(d)
            with self.assertRaisesRegex(ValueError, '^manifest_closure$'):
                M.source_pins(Path(d))

    def test_duplicate_and_traversal_paths(self):
        with tempfile.TemporaryDirectory() as d, patch.object(M, 'REQUIRED', {'checked.py'}):
            _, manifest, line = self.fixture(d)
            for text in [line + line, line.replace('checked.py', '../checked.py'),
                         line.replace('checked.py', './checked.py')]:
                manifest.write_text(text)
                with self.assertRaises(ValueError):
                    M.source_pins(Path(d))

    def test_symlink_is_not_source(self):
        with tempfile.TemporaryDirectory() as d, patch.object(M, 'REQUIRED', {'checked.py'}):
            source, _, _ = self.fixture(d)
            target = source.with_name('other.py')
            source.rename(target)
            source.symlink_to(target.name)
            with self.assertRaisesRegex(ValueError, '^source_symlink$'):
                M.source_pins(Path(d))

    def test_compiler_or_child_failure_is_not_pass(self):
        result = subprocess.CompletedProcess(['example'], 1, b'private stdout', b'private stderr')
        with patch.object(M.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, '^offline_check_failed$'):
                M.run(['example'])

    def test_no_skipped_or_empty_suites(self):
        for output in [b'Ran 0 tests in 0s\nOK', b'Ran 3 tests in 0s\nOK (skipped=1)', b'OK']:
            with patch.object(M, 'run', return_value=(b'', output)):
                with self.assertRaises(ValueError):
                    M.suite('fixed.py')
        with patch.object(M, 'run', return_value=(b'', b'Ran 3 tests in 0s\nOK')):
            self.assertEqual(M.suite('fixed.py')['methods'], 3)

    def test_malformed_arguments_stay_offline_and_private(self):
        marker = 'PRIVATE_SENTINEL_FOR_ARG_TEST'
        for args in [['--live'], ['--unrecognized', marker], []]:
            result = subprocess.run([sys.executable, '-I', str(ROOT /
                'tools/m1n1-client/attempt31p-offline.py'), *args],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(marker, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertFalse(data['restart_ready'])
            self.assertEqual(data['hardware_operations'], 0)

    def test_gpu_summary_never_promotes_native_or_address_claims(self):
        good = dict(schema='ilinux-gpu31p-contract-v1', status='STRUCTURAL_PASS',
            sanitized_adt_sha256=M.ADT_SHA, native_validation='NOT_RUN',
            gpu_enablement='HOLD', descriptor_cpu_address_domain='UNQUALIFIED',
            uat_layout='UNKNOWN', firmware_abi='UNKNOWN', hardware_operations=0,
            cpu_memory_reservations_generated=0, mmio_writes_generated=0,
            role_count=2)
        M.verify_gpu_summary(good)
        for key, value in [('native_validation', 'PASS'), ('gpu_enablement', 'READY'),
                           ('descriptor_cpu_address_domain', 'CPU_PHYSICAL'),
                           ('sanitized_adt_sha256', '0' * 64), ('role_count', True),
                           ('mmio_writes_generated', 1), ('hardware_operations', False),
                           ('cpu_memory_reservations_generated', 1)]:
            changed = dict(good, **{key: value})
            with self.assertRaises(ValueError, msg=key):
                M.verify_gpu_summary(changed)


if __name__ == '__main__':
    unittest.main()
