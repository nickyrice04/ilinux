#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pure AX typed-policy fixture tests using the installed Apple SDK only.

Run with python3 -I. Set ILINUX31AX_POLICY_SANITIZE=1 for ASan/UBSan.
No target collector, controller, policy command or writer is built or linked.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FROZEN = {
    'reader.h': ('tools/boot-object31aj-native/reader.h',
                 'bfa3bfe2af667e4b54db1913c80a35d9da4e343cddbc182464d08be674fcbf99'),
    'extra_policy.h': ('tools/boot-object31ao-native/extra_policy.h',
                       '1c3f275e3564489c95d60580734dc445beb86b6bc9e0b049ea88017e71e9fb1f'),
    'extra_policy.c': ('tools/boot-object31ao-native/extra_policy.c',
                       'c721bf59aa262a2b06f69536f5712d5a847dd48793ed33213350bb8270ef669e'),
}
CASES = (
    'required_counts', 'duplicate_tags', 'uuid_grammar', 'lpnh_grammar',
    'bounded_numbers', 'auxiliary_absence', 'target_binding', 'complete_extras',
    'original_reference_anchors', 'authority_anchors', 'nonce_rotation',
    'lab_manifest_anchor', 'extra_anchor_separation', 'domain_and_key_binding',
    'unbound_and_reset_views', 'reference_grammar',
)


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if platform.system() != 'Darwin':
            raise unittest.SkipTest('The pure probe needs the installed Apple SDK/CommonCrypto')
        cls.sanitized = os.environ.get('ILINUX31AX_POLICY_SANITIZE') == '1'
        scratch = ROOT / 'build' / 'boot-object31ax-native'
        scratch.mkdir(parents=True, exist_ok=True)
        cls.temp = Path(tempfile.mkdtemp(prefix='pure-policy-', dir=scratch))
        cls.addClassCleanup(shutil.rmtree, cls.temp)
        cls.bindings = {}
        for destination, (relative, expected) in FROZEN.items():
            data = (ROOT / relative).read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise AssertionError('Frozen pure-probe dependency changed: ' + relative)
            (cls.temp / destination).write_bytes(data)
            cls.bindings[destination] = expected
        for name in ('policy_contract.c', 'policy_contract.h', 'policy_probe.c'):
            data = (HERE / name).read_bytes()
            (cls.temp / name).write_bytes(data)
            cls.bindings[name] = hashlib.sha256(data).hexdigest()
        compiler = subprocess.run(
            ['xcrun', '--sdk', 'macosx', '--find', 'clang'], check=True,
            capture_output=True, text=True).stdout.strip()
        sdk = subprocess.run(
            ['xcrun', '--sdk', 'macosx', '--show-sdk-path'], check=True,
            capture_output=True, text=True).stdout.strip()
        cls.binary = cls.temp / 'policy-probe'
        flags = ['-std=c11', '-Wall', '-Wextra', '-Werror',
                 '-Wno-deprecated-declarations', '-isysroot', sdk,
                 '-DWORKSPACE_ROOT="' + str(ROOT) + '"']
        if cls.sanitized:
            flags += ['-O1', '-g', '-fsanitize=address,undefined',
                      '-fno-omit-frame-pointer', '-fno-sanitize-recover=all']
        else:
            flags += ['-O2']
        command = [compiler, *flags, 'policy_contract.c', 'extra_policy.c',
                   'policy_probe.c', '-framework', 'CoreFoundation', '-o', str(cls.binary)]
        built = subprocess.run(command, cwd=cls.temp, capture_output=True, text=True)
        if built.returncode:
            raise AssertionError('Pure policy-probe compilation failed:\n' + built.stderr)
        cls.environment = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
                           'LC_ALL': 'C', 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1',
                           'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
        cls.results = []
        cls.receipt = scratch / ('policy-tests-sanitized.json' if cls.sanitized else 'policy-tests-normal.json')
        cls.provenance = {
            'schema': 'ilinux31ax-pure-policy-tests-v1',
            'sanitized': cls.sanitized, 'source_sha256': cls.bindings,
            'compiler': subprocess.run([compiler, '--version'], capture_output=True,
                                       text=True, check=True).stdout.splitlines()[0],
            'sdk_version': subprocess.run(['xcrun', '--sdk', 'macosx', '--show-sdk-version'],
                                          capture_output=True, text=True, check=True).stdout.strip(),
            'target_collector_or_writer_linked': False,
            'native_or_Recovery_compatibility_claimed': False,
            'fixture_values_returned': False,
        }

    @classmethod
    def tearDownClass(cls):
        cls.receipt.write_text(json.dumps({**cls.provenance, 'cases': cls.results}, indent=2) + '\n')

    def run_case(self, name):
        result = subprocess.run([str(self.binary), name], cwd=self.temp,
                                env=self.environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(result.stderr, '')
        data = json.loads(result.stdout)
        self.assertEqual(set(data), {'case', 'passed', 'checks', 'failed',
                                     'private_values_returned', 'target_or_writer_linked'})
        self.assertEqual(data['case'], name)
        self.assertIs(data['passed'], True)
        self.assertGreater(data['checks'], 0)
        self.assertEqual(data['failed'], 0)
        self.assertIs(data['private_values_returned'], False)
        self.assertIs(data['target_or_writer_linked'], False)
        self.results.append(data)

    def test_unknown_argument_is_never_echoed(self):
        marker = 'SYNTHETIC_UNRECOGNIZED_VALUE_DO_NOT_ECHO'
        result = subprocess.run([str(self.binary), marker], cwd=self.temp,
                                env=self.environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 64)
        self.assertEqual(result.stderr, '')
        self.assertNotIn(marker, result.stdout)
        self.assertEqual(json.loads(result.stdout)['case'], 'UNRECOGNIZED')

    def test_no_target_observer_or_writer_imports(self):
        result = subprocess.run(['xcrun', 'nm', '-u', str(self.binary)],
                                capture_output=True, text=True, check=True)
        for name in ('_collect_snapshot', '_capture', '_execve', '_fork',
                     '_posix_spawn', '_system', '_mount', '_IOConnectCallStructMethod'):
            self.assertNotIn(name + '\n', result.stdout)


def _method(name):
    def test(self):
        self.run_case(name)
    test.__name__ = 'test_' + name
    return test


for _case in CASES:
    setattr(PolicyTests, 'test_' + _case, _method(_case))

if __name__ == '__main__':
    unittest.main()
