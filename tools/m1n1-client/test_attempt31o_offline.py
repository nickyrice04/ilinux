#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline closure, bounded input and no-live-interface regression checks."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('intake31o', Path(__file__).with_name('attempt31o-offline.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.digest = hashlib.sha256(b'synthetic').hexdigest()
        self.rows = [self.digest + '  ' + name for name in sorted(m.REQUIRED)]
        for name in m.REQUIRED:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'synthetic')
        self.manifest = self.root / m.MANIFEST
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        self.save()
        p = patch.object(m, 'N_MANIFEST_SHA', self.digest)
        p.start(); self.addCleanup(p.stop)

    def save(self):
        self.manifest.write_text('\n'.join(self.rows) + '\n')

    def test_complete_frozen_and_new_closure(self):
        self.assertEqual(m.source_pins(self.root)[0], len(m.REQUIRED))
        self.assertTrue(m.previous.REQUIRED <= m.REQUIRED)

    def test_missing_extra_and_noncanonical_source_refused(self):
        for row in (self.rows[0], self.digest + '  ../escape',
                    self.digest + '  native//extra', self.digest + '  native/./extra'):
            old = self.rows[:]
            self.rows.append(row); self.save()
            with self.assertRaises(ValueError): m.source_pins(self.root)
            self.rows = old
        self.rows.pop(); self.save()
        with self.assertRaisesRegex(ValueError, 'manifest_closure'): m.source_pins(self.root)

    def test_modified_legacy_source_refused(self):
        (self.root / 'native/boot/smp31n.py').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'source_digest'): m.source_pins(self.root)

    def test_modified_result_refused(self):
        (self.root / 'native/boot/attempt31n-controller-2026-10-22.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'source_digest'): m.source_pins(self.root)

    def test_frozen_manifest_must_match_even_if_new_manifest_repinned(self):
        path = self.root / 'native/boot/attempt31n/source-sha256.txt'
        path.write_bytes(b'changed')
        digest = hashlib.sha256(b'changed').hexdigest()
        self.rows = [digest + row[64:] if row.endswith('attempt31n/source-sha256.txt') else row
                     for row in self.rows]
        self.save()
        with self.assertRaisesRegex(ValueError, 'frozen_n_manifest'): m.source_pins(self.root)

    def test_symlink_source_refused(self):
        path = self.root / 'native/boot/smp31n.py'
        path.unlink(); path.symlink_to(self.root / 'native/boot/smp31m.py')
        with self.assertRaisesRegex(ValueError, 'source_symlink'): m.source_pins(self.root)

    def test_input_limits_and_empty_file(self):
        path = self.root / 'input'
        for data in (b'', b'12345'):
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'input_size_or_type'): m.read_regular(path, 4)
        path.write_bytes(b'1234')
        self.assertEqual(m.read_regular(path, 4), b'1234')

    def test_input_symlink_and_fifo_refused_without_blocking(self):
        path = self.root / 'input'
        path.symlink_to(self.manifest)
        with self.assertRaises(OSError): m.read_regular(path, 65536)
        fifo = self.root / 'pipe'; os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'input_size_or_type'): m.read_regular(fifo, 65536)

    def test_no_live_argument_or_sensitive_error_echo(self):
        for args in (['--live'], ['--confirm', 'PRIVATE_SECRET']):
            result = subprocess.run([sys.executable, '-I', str(Path(m.__file__)),
                                     '--image', '/PRIVATE_SECRET/input', *args],
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(b'PRIVATE_SECRET', result.stdout + result.stderr)
            value = json.loads(result.stdout)
            self.assertFalse(value['restart_ready'])
            self.assertEqual(value['hardware_operations'], 0)

    def test_failed_subprocess_output_is_not_forwarded(self):
        fake = subprocess.CompletedProcess([], 1, b'PRIVATE_SECRET', b'PRIVATE_SECRET')
        with patch.object(m.subprocess, 'run', return_value=fake):
            with self.assertRaisesRegex(ValueError, '^offline_check_failed$'):
                m.run_check('fixed_test.py')

    def test_decoder_reopened_input_must_match_initial_pin(self):
        value = dict(result='RCfg_STRUCTURAL_PASS', sha256=m.DATA_SHA, size_bytes=459150,
                     command_count=22855, named_sequence_count=417,
                     evaluated_conditions=False, firmware_emulator=False, native_operations=0)
        m.verify_firmware_summary(value)
        # The first read could match while the child parsed a replaced payload.
        for key, replacement in (('sha256', '0' * 64), ('size_bytes', 459151),
                                 ('evaluated_conditions', True), ('native_operations', False)):
            changed = dict(value, **{key: replacement})
            with self.assertRaisesRegex(ValueError, 'firmware_summary_not_matching_input'):
                m.verify_firmware_summary(changed)


if __name__ == '__main__':
    unittest.main()
