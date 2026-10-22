# SPDX-License-Identifier: MIT
"""Synthetic host-only diagnostics; every subprocess and lstat is mocked."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import plistlib
import stat
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('discovery31j', HERE / 'usb-discovery31j.py')
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


def device(stem='PRIVATE_SYNTHETIC', vid=0x1209, pid=0x316d):
    return {'IOObjectClass': 'IOUSBHostDevice', 'idVendor': vid, 'idProduct': pid,
            'USB Serial Number': 'PRIVATE_SYNTHETIC_SERIAL',
            'IORegistryEntryChildren': [
                {'IOObjectClass': 'IOUSBHostInterface', 'bInterfaceNumber': number,
                 'bInterfaceClass': 10, 'IORegistryEntryChildren': [
                     {'IOObjectClass': 'AppleUSBACMData', 'IORegistryEntryChildren': [
                         {'IOObjectClass': 'IOSerialBSDClient',
                          'IOCalloutDevice': '/dev/cu.usbmodem' + stem + str(number)}]}]}
                for number in (1, 3)]}


class DiagnosticTests(unittest.TestCase):
    def run_case(self, roots=None, raw=None, returncode=0, query_error=None,
                 mode=stat.S_IFCHR, path_error=None, require=False, platform='darwin', args=None):
        if raw is None:
            raw = plistlib.dumps([device()] if roots is None else roots)
        out, err = io.StringIO(), io.StringIO()
        result = SimpleNamespace(stdout=raw, stderr=b'PRIVATE_SYNTHETIC_STDERR', returncode=returncode)
        with patch.object(discovery.sys, 'platform', platform), \
                patch.object(discovery.subprocess, 'run', return_value=result, side_effect=query_error) as run, \
                patch.object(discovery.identity.Path, 'lstat', return_value=SimpleNamespace(st_mode=mode), side_effect=path_error) as lstat, \
                patch('builtins.open', side_effect=AssertionError('No device/file open allowed')), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = discovery.main(args if args is not None else ['--require-primary'] if require else [])
        text = out.getvalue() + err.getvalue()
        self.assertEqual(err.getvalue(), '')
        for private in ('PRIVATE_SYNTHETIC', '/dev/', '/Users/', 'Traceback', 'ioreg'):
            self.assertNotIn(private, text)
        report = json.loads(out.getvalue())
        self.assertFalse(report['native_ready'])
        self.assertEqual(report['device_opens'], 0)
        self.assertEqual(report['target_requests'], 0)
        self.assertLessEqual(run.call_count, 1)
        self.assertLessEqual(lstat.call_count, 1)
        return rc, report, run, lstat

    def test_primary_verified_without_opening(self):
        for require in (False, True):
            with self.subTest(require=require):
                rc, report, run, lstat = self.run_case(require=require)
                self.assertEqual(rc, 0)
                self.assertTrue(report['primary_verified'])
                self.assertEqual(report['primary_candidates'], 1)
                self.assertEqual(report['modem_interfaces'], 2)
                self.assertEqual(report['result'], 'PRIMARY_INTERFACE_VERIFIED' if require else 'HOST_DIAGNOSTIC_COMPLETE')
                run.assert_called_once_with(list(discovery.QUERY), stdin=subprocess.DEVNULL,
                                            capture_output=True, check=False, timeout=15)
                lstat.assert_called_once()

    def test_unsupported_host_never_queries(self):
        rc, report, run, lstat = self.run_case(platform='linux')
        self.assertEqual((rc, report['category']), (1, 'unsupported_platform'))
        run.assert_not_called()
        lstat.assert_not_called()

    def test_query_errors_no_retry_and_no_private_output(self):
        cases = ((subprocess.TimeoutExpired('PRIVATE_SYNTHETIC', 15, output=b'PRIVATE_SYNTHETIC', stderr=b'PRIVATE_SYNTHETIC'), 'query_timeout'),
                 (FileNotFoundError('PRIVATE_SYNTHETIC'), 'query_executable_missing'),
                 (PermissionError('PRIVATE_SYNTHETIC'), 'query_permission_denied'),
                 (OSError('PRIVATE_SYNTHETIC'), 'query_failed'),
                 (KeyboardInterrupt('PRIVATE_SYNTHETIC'), 'query_failed'))
        for error, category in cases:
            with self.subTest(category=category):
                rc, report, run, lstat = self.run_case(query_error=error)
                self.assertEqual((rc, report['phase'], report['category']), (1, 'query', category))
                run.assert_called_once()
                lstat.assert_not_called()

    def test_nonzero_exit_never_parses_or_checks_path(self):
        rc, report, run, lstat = self.run_case(returncode=1, raw=b'PRIVATE_SYNTHETIC')
        self.assertEqual((rc, report['category']), (1, 'query_nonzero_exit'))
        run.assert_called_once()
        lstat.assert_not_called()

    def test_exact_empty_distinct_from_valid_empty_registry(self):
        for require in (False, True):
            rc, report, _, lstat = self.run_case(raw=b'', require=require)
            self.assertEqual(rc, 2 if require else 0)
            self.assertEqual(report['category'], 'empty_stdout_unresolved')
            self.assertFalse(report['inventory_classified'])
            self.assertNotIn('primary_candidates', report)
            lstat.assert_not_called()
            rc, report, _, lstat = self.run_case(roots=[], require=require)
            self.assertEqual(rc, 2 if require else 0)
            self.assertEqual(report['category'], 'no_primary_candidate')
            self.assertTrue(report['inventory_classified'])
            self.assertEqual(report['primary_candidates'], 0)
            lstat.assert_not_called()

    def test_whitespace_is_not_empty_or_stripped(self):
        for raw in (b' ', b'\n\t\r '):
            rc, report, _, _ = self.run_case(raw=raw)
            self.assertEqual((rc, report['category']), (1, 'whitespace_stdout'))

    def test_bad_plists_and_prefixes_never_repaired(self):
        good = plistlib.dumps([device()])
        cases = (b'PRIVATE_SYNTHETIC', b'<?xml version="1.0"?><plist><array>',
                 b'bplist00PRIVATE_SYNTHETIC', b'PRIVATE_SYNTHETIC\n' + good,
                 b' \n' + good, good + b'PRIVATE_SYNTHETIC')
        for raw in cases:
            with self.subTest(prefix=raw[:8]):
                rc, report, _, lstat = self.run_case(raw=raw)
                self.assertEqual((rc, report['category']), (1, 'invalid_plist'))
                lstat.assert_not_called()

    def test_binary_archive_uses_same_identity(self):
        raw = plistlib.dumps([device()], fmt=plistlib.FMT_BINARY)
        rc, report, _, _ = self.run_case(raw=raw, require=True)
        self.assertEqual(rc, 0)
        self.assertEqual(report['stdout_kind'], 'binary_plist')
        self.assertTrue(report['primary_verified'])

    def test_wrong_roots_and_invalid_tree_shapes(self):
        roots = ({}, 'PRIVATE_SYNTHETIC', [1], [{'IORegistryEntryChildren': None}],
                 [{'IORegistryEntryChildren': {}}], [{'IOObjectClass': 1}],
                 [{'IORegistryEntryChildren': ['PRIVATE_SYNTHETIC']}])
        for root in roots:
            # plist has no null value; test the structural validator separately.
            if root == [{'IORegistryEntryChildren': None}]:
                with self.assertRaises(discovery.ShapeError):
                    discovery.validate_tree(root)
                continue
            rc, report, _, lstat = self.run_case(roots=root)
            self.assertEqual((rc, report['category']), (1, 'invalid_registry_shape'))
            lstat.assert_not_called()

    def test_bounds_fail_closed(self):
        with patch.object(discovery, 'MAX_OUTPUT_BYTES', 4):
            rc, report, _, _ = self.run_case()
            self.assertEqual((rc, report['category']), (1, 'stdout_size_limit'))
        with patch.object(discovery, 'MAX_NODES', 2):
            rc, report, _, _ = self.run_case()
            self.assertEqual((rc, report['category']), (1, 'invalid_registry_shape'))
        with patch.object(discovery, 'MAX_DEPTH', 1):
            rc, report, _, _ = self.run_case()
            self.assertEqual((rc, report['category']), (1, 'invalid_registry_shape'))

    def test_no_primary_and_ambiguity_do_not_check_a_path(self):
        for roots, category in (([device(vid=1)], 'no_primary_candidate'),
                                ([device(pid=1)], 'no_primary_candidate'),
                                ([device('ONE'), device('TWO')], 'ambiguous_primary_candidates')):
            for require in (False, True):
                rc, report, _, lstat = self.run_case(roots=roots, require=require)
                self.assertEqual((rc, report['category']), (2 if require else 0, category))
                self.assertFalse(report['primary_verified'])
                lstat.assert_not_called()

    def test_wrong_or_missing_interface_is_never_primary(self):
        for key, value in (('bInterfaceNumber', 3), ('bInterfaceClass', 2),
                           ('bInterfaceNumber', None), ('bInterfaceClass', None)):
            root = device()
            interface = root['IORegistryEntryChildren'][0]
            if value is None:
                del interface[key]
            else:
                interface[key] = value
            rc, report, _, lstat = self.run_case(roots=[root], require=True)
            self.assertEqual((rc, report['category']), (2, 'no_primary_candidate'))
            lstat.assert_not_called()

    def test_metadata_requires_real_bounded_integers(self):
        for key, value in (('idVendor', 4617.0), ('idProduct', '12653'),
                           ('bInterfaceNumber', True), ('bInterfaceNumber', 1.0),
                           ('bInterfaceClass', 10.0), ('bInterfaceNumber', 256),
                           ('idProduct', -1)):
            root = device()
            node = root if key.startswith('id') else root['IORegistryEntryChildren'][0]
            node[key] = value
            rc, report, _, lstat = self.run_case(roots=[root], require=True)
            self.assertEqual((rc, report['category']), (1, 'invalid_registry_shape'))
            lstat.assert_not_called()

    def test_duplicate_metadata_deduplicates_conflicts_refuse(self):
        root = device()
        rc, report, _, _ = self.run_case(roots=[root, copy.deepcopy(root)], require=True)
        self.assertEqual((rc, report['primary_candidates']), (0, 1))
        conflict = copy.deepcopy(root)
        conflict['idProduct'] = 1
        rc, report, _, lstat = self.run_case(roots=[root, conflict], require=True)
        self.assertEqual((rc, report['category']), (1, 'registry_metadata_invalid'))
        lstat.assert_not_called()

    def test_nearest_device_and_interface_ancestry_is_retained(self):
        root = device()
        interface = root['IORegistryEntryChildren'][0]
        orphan = copy.deepcopy(interface['IORegistryEntryChildren'][0])
        nested = {'IOObjectClass': 'IOUSBHostDevice', 'IORegistryEntryChildren': [interface]}
        for child in (orphan, nested):
            root['IORegistryEntryChildren'] = [child]
            rc, report, _, lstat = self.run_case(roots=[root], require=True)
            self.assertEqual((rc, report['category']), (2, 'no_primary_candidate'))
            lstat.assert_not_called()

    def test_bad_paths_and_paths_outside_modem_namespace_are_not_selected(self):
        for path in ('/dev/cu.usbmodemBAD/../other', '/tmp/PRIVATE_SYNTHETIC', '/dev/tty.usbmodemA1'):
            root = device()
            root['IORegistryEntryChildren'][0]['IORegistryEntryChildren'][0]['IORegistryEntryChildren'][0]['IOCalloutDevice'] = path
            rc, report, _, lstat = self.run_case(roots=[root], require=True)
            self.assertEqual((rc, report['category']), (2, 'no_primary_candidate'))
            lstat.assert_not_called()

    def test_stale_symlink_regular_and_inaccessible_paths_refuse(self):
        for mode in (stat.S_IFLNK, stat.S_IFREG, stat.S_IFDIR):
            rc, report, _, lstat = self.run_case(mode=mode, require=True)
            self.assertEqual((rc, report['category']), (1, 'primary_path_not_character'))
            lstat.assert_called_once()
        for error, category in ((FileNotFoundError('/dev/PRIVATE_SYNTHETIC'), 'primary_path_absent'),
                                (PermissionError('/dev/PRIVATE_SYNTHETIC'), 'primary_path_access_denied'),
                                (OSError('/dev/PRIVATE_SYNTHETIC'), 'primary_path_check_failed')):
            rc, report, _, lstat = self.run_case(path_error=error, require=True)
            self.assertEqual((rc, report['category']), (1, category))
            lstat.assert_called_once()

    def test_unknown_arguments_do_not_leak_or_query(self):
        rc, report, run, lstat = self.run_case(args=['--device=/Users/PRIVATE_SYNTHETIC'])
        self.assertEqual((rc, report['category']), (1, 'invalid_arguments'))
        run.assert_not_called()
        lstat.assert_not_called()

    def test_no_dynamic_exception_message_in_last_resort(self):
        with patch.object(discovery, 'inspect_host', side_effect=RuntimeError('/Users/PRIVATE_SYNTHETIC')):
            rc, report, run, lstat = self.run_case()
        self.assertEqual((rc, report['category']), (1, 'diagnostic_failed'))
        run.assert_not_called()
        lstat.assert_not_called()


if __name__ == '__main__':
    unittest.main()
