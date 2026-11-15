#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused 31AL Preboot-path regressions using synthetic CF fixtures only.

Compose the existing original build/fixture harness without inheriting its
29 test methods. No live, mount, diskutil or bputil mode is invoked.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'preboot31am_frozen_harness', ROOT / 'tools/boot-object31al-native/test_native.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class PrebootPaths(unittest.TestCase):
    setUpClass = classmethod(harness.Diagnostic.setUpClass.__func__)
    tearDownClass = classmethod(harness.Diagnostic.tearDownClass.__func__)
    setUp = harness.Diagnostic.setUp
    invoke = harness.Diagnostic.invoke
    fixture = harness.Diagnostic.fixture
    assert_refused = harness.Diagnostic.assert_refused

    @staticmethod
    def malformed_policy(value):
        value['lab_policy'] = value['lab_policy'].replace(
            '(sip0): 0', '(sip0): SYNTHETIC_PRIVATE_VALUE')

    def assert_path_refusal(self, change, reason='PREBOOT_MOUNT_PATH', kind='GUARD'):
        def apply(value):
            self.malformed_policy(value)
            change(value['preboot_info'])
        result = self.fixture(apply)
        record = self.assert_refused(result, kind, reason)
        self.assertEqual(record['stage'], 'AUX_IDENTITIES')
        self.assertEqual(record['scope'], 'SYNTHETIC_CONTROL')
        self.assertEqual(record['command'], 'NONE')
        self.assertNotIn('SYNTHETIC_PRIVATE_VALUE', result[0].stdout)

    def test_empty_unmounted_like_path_reproduces_observed_guard_before_policy(self):
        self.assert_path_refusal(lambda info: info.update(MountPoint='', Mounted=False))

    def test_lexically_unsafe_path_classes_keep_the_original_guard(self):
        for path in ('/', 'relative', '/Volumes/Preboot/', '/Volumes//Preboot',
                     '/Volumes/./Preboot', '/Volumes/../Preboot'):
            with self.subTest(path=path):
                self.assert_path_refusal(lambda info: info.update(MountPoint=path))

    def test_missing_mountpoint_is_a_format_refusal(self):
        self.assert_path_refusal(lambda info: info.pop('MountPoint'),
                                 'PREBOOT_MOUNT_FORMAT', 'FORMAT')

    def test_nonstring_mountpoints_are_format_refusals(self):
        for value in (4, False, []):
            with self.subTest(value=value):
                self.assert_path_refusal(lambda info: info.update(MountPoint=value),
                                         'PREBOOT_MOUNT_FORMAT', 'FORMAT')

    def test_canonical_paths_reach_the_deliberately_failing_policy(self):
        for path in ('/Volumes/Preboot', '/System/Volumes/Preboot', '/Volumes/Preboot 1'):
            with self.subTest(path=path):
                def apply(value):
                    value['preboot_info']['MountPoint'] = path
                    self.malformed_policy(value)
                record = self.assert_refused(self.fixture(apply), 'FORMAT',
                                             'SEMANTIC_SIP0_MALFORMED')
                self.assertEqual(record['stage'], 'LAB_POLICY')

    def test_mounted_boolean_alone_does_not_produce_the_lexical_refusal(self):
        def apply(value):
            value['preboot_info'].update(MountPoint='/Volumes/Preboot', Mounted=False)
            self.malformed_policy(value)
        record = self.assert_refused(self.fixture(apply), 'FORMAT',
                                     'SEMANTIC_SIP0_MALFORMED')
        self.assertEqual(record['stage'], 'LAB_POLICY')


if __name__ == '__main__':
    unittest.main(verbosity=2)
