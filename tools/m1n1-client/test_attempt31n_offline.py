#!/usr/bin/env python3
"""Source closure/refusal tests; no subprocess or native path is exercised."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('intake31n',
    Path(__file__).with_name('attempt31n-offline.py'))
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)


class Pins(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.digest = hashlib.sha256(b'synthetic').hexdigest()
        self.rows = [self.digest + '  ' + name for name in sorted(intake.REQUIRED)]
        for name in intake.REQUIRED:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'synthetic')
        self.manifest = self.root / intake.MANIFEST
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        self.save()

    def save(self):
        self.manifest.write_text('\n'.join(self.rows) + '\n')

    def test_complete_transitive_closure(self):
        count, digest = intake.source_pins(self.root)
        self.assertEqual(count, len(intake.REQUIRED))
        self.assertEqual(digest, hashlib.sha256(self.manifest.read_bytes()).hexdigest())

    def test_missing_transitive_module_refused(self):
        self.rows = [r for r in self.rows if not r.endswith('/observe.py')]
        self.save()
        with self.assertRaisesRegex(ValueError, 'manifest_incomplete'):
            intake.source_pins(self.root)

    def test_modified_transitive_module_refused(self):
        (self.root / 'kernel/experiments/smp31e-entry/observe.py').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'source_digest'):
            intake.source_pins(self.root)

    def test_symlink_refused_even_when_bytes_match(self):
        path = self.root / 'kernel/experiments/smp31e-entry/observe.py'
        path.unlink()
        path.symlink_to(self.root / 'kernel/experiments/smp31e-entry/audit.py')
        with self.assertRaisesRegex(ValueError, 'source_symlink'):
            intake.source_pins(self.root)

    def test_traversal_refused(self):
        self.rows.append(self.digest + '  ../../outside')
        self.save()
        with self.assertRaisesRegex(ValueError, 'manifest_path'):
            intake.source_pins(self.root)

    def test_duplicate_refused(self):
        self.rows.append(self.rows[0])
        self.save()
        with self.assertRaisesRegex(ValueError, 'manifest_path'):
            intake.source_pins(self.root)

    def test_noncanonical_paths_refused(self):
        for name in ('native/boot/./smp31n.py', 'native//boot/smp31n.py'):
            with self.subTest(name=name):
                self.rows.append(self.digest + '  ' + name)
                self.save()
                with self.assertRaisesRegex(ValueError, 'manifest_path'):
                    intake.source_pins(self.root)
                self.rows.pop()

    def test_new_observer_and_candidate_are_required(self):
        original = list(self.rows)
        for name in ('kernel/experiments/smp31n-startpair/start_pair.S',
                     'research/native31n-upstream.md',
                     'native/boot/smp31n.py',
                     'native/boot/attempt31m/source-sha256.txt'):
            with self.subTest(name=name):
                self.rows = [r for r in original if not r.endswith('  ' + name)]
                self.save()
                with self.assertRaisesRegex(ValueError, 'manifest_incomplete'):
                    intake.source_pins(self.root)

    def test_frozen_m_closure_remains_required(self):
        self.assertTrue(intake.previous.REQUIRED <= intake.REQUIRED)
        self.assertEqual(intake.TESTS[:len(intake.previous.TESTS)], intake.previous.TESTS)
        self.assertIn('tools/m1n1-client/test_attempt31m_supervisor.py', intake.TESTS)


if __name__ == '__main__':
    unittest.main()
