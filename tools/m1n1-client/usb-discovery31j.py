#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify one cached macOS USB registry query without opening a device.

Exit 0 means a completed host diagnostic, not native boot readiness. With
--require-primary, exit 0 additionally requires one verified primary callout;
exit 2 means no unique primary. Query, parse, tree and path failures exit 1.
Empty stdout is an observation, not proof of target absence or a USB cause.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import sys


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('frozen_usb_identity_31j', HERE / 'usb_identity.py')
identity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(identity)

QUERY = ('/usr/sbin/ioreg', '-a', '-l', '-p', 'IOService', '-r', '-c', 'IOUSBHostDevice')
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_NODES = 100000
MAX_DEPTH = 128


class ShapeError(ValueError):
    pass


class ArgumentsError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's usual error includes unknown arguments, possibly paths.
        raise ArgumentsError()


def validate_tree(roots):
    """Validate structure/types before the frozen identity resolver sees it."""
    if type(roots) is not list:
        raise ShapeError()
    stack = [(root, 0) for root in roots]
    visited = 0
    while stack:
        node, depth = stack.pop()
        visited += 1
        if type(node) is not dict or depth > MAX_DEPTH or visited > MAX_NODES:
            raise ShapeError()
        cls = node.get('IOObjectClass')
        if cls is not None and type(cls) is not str:
            raise ShapeError()
        children = node.get('IORegistryEntryChildren', [])
        if type(children) is not list:
            raise ShapeError()
        if len(children) + visited + len(stack) > MAX_NODES:
            raise ShapeError()
        fields = ()
        if cls in ('IOUSBHostDevice', 'IOUSBDevice') or 'bDeviceClass' in node:
            fields += (('idVendor', 65535), ('idProduct', 65535))
        if cls in ('IOUSBHostInterface', 'IOUSBInterface') or 'bInterfaceNumber' in node:
            fields += (('bInterfaceNumber', 255), ('bInterfaceClass', 255))
        for name, maximum in fields:
            if name in node and (type(node[name]) is not int or not 0 <= node[name] <= maximum):
                # bool/float equality must not impersonate integer descriptors.
                raise ShapeError()
        if cls == 'IOSerialBSDClient' and 'IOCalloutDevice' in node and type(node['IOCalloutDevice']) is not str:
            raise ShapeError()
        stack.extend((child, depth + 1) for child in children)


def base_report(require_primary):
    return dict(schema='usb_discovery31j', require_primary=require_primary,
                result='HOST_DIAGNOSTIC_REFUSED', phase='platform', category='unsupported_platform',
                query_attempts=0, query_returned=False, inventory_classified=False,
                primary_verified=False, native_ready=False, device_opens=0, target_requests=0)


def refused(report, phase, category):
    report.update(result='HOST_DIAGNOSTIC_REFUSED', phase=phase, category=category)
    return report, 1


def unavailable(report, category):
    report.update(phase='identity', category=category,
                  result='PRIMARY_INTERFACE_UNAVAILABLE' if report['require_primary'] else 'HOST_DIAGNOSTIC_COMPLETE')
    return report, 2 if report['require_primary'] else 0


def inspect_host(require_primary=False):
    """One fixed query; no retries, device opens, target requests or receipts."""
    report = base_report(require_primary)
    if sys.platform != 'darwin':
        return report, 1
    report['query_attempts'] = 1
    try:
        query = subprocess.run(list(QUERY), stdin=subprocess.DEVNULL,
                               capture_output=True, check=False, timeout=15)
    except subprocess.TimeoutExpired:
        return refused(report, 'query', 'query_timeout')
    except FileNotFoundError:
        return refused(report, 'query', 'query_executable_missing')
    except PermissionError:
        return refused(report, 'query', 'query_permission_denied')
    except (Exception, KeyboardInterrupt):
        return refused(report, 'query', 'query_failed')
    report['query_returned'] = True
    if type(query.returncode) is not int or query.returncode != 0:
        return refused(report, 'query', 'query_nonzero_exit')
    raw = query.stdout
    if type(raw) is not bytes or type(query.stderr) is not bytes:
        return refused(report, 'query', 'query_output_type')
    report['stderr_present'] = bool(query.stderr)
    if len(raw) > MAX_OUTPUT_BYTES:
        return refused(report, 'parse', 'stdout_size_limit')
    if raw == b'':
        # Never turn this into []: the command returned no parseable archive.
        report['stdout_kind'] = 'empty'
        report, status = unavailable(report, 'empty_stdout_unresolved')
        report['phase'] = 'parse'
        return report, status
    if all(byte in b' \t\r\n' for byte in raw):
        report['stdout_kind'] = 'whitespace'
        return refused(report, 'parse', 'whitespace_stdout')
    report['stdout_kind'] = ('binary_candidate' if raw.startswith(b'bplist00') else
                             'xml_candidate' if raw.startswith((b'<?xml', b'<plist')) else 'other')
    try:
        roots = plistlib.loads(raw)
    except (Exception, KeyboardInterrupt):
        return refused(report, 'parse', 'invalid_plist')
    report['stdout_kind'] = 'binary_plist' if raw.startswith(b'bplist00') else 'xml_plist'
    try:
        validate_tree(roots)
        ports = identity.registry_ports(roots)
    except ShapeError:
        return refused(report, 'tree', 'invalid_registry_shape')
    except (Exception, KeyboardInterrupt):
        return refused(report, 'tree', 'registry_metadata_invalid')
    candidates = sum(port.primary for port in ports)
    report.update(inventory_classified=True, modem_interfaces=len(ports), primary_candidates=candidates)
    if candidates == 0:
        return unavailable(report, 'no_primary_candidate')
    if candidates != 1:
        return unavailable(report, 'ambiguous_primary_candidates')
    try:
        # Frozen checks retain exact VID/PID, interface 1/class 0x0a, and lstat.
        # The path remains private in memory and is never opened or returned.
        identity.select_primary(ports, 'auto')
    except FileNotFoundError:
        return refused(report, 'path', 'primary_path_absent')
    except PermissionError:
        return refused(report, 'path', 'primary_path_access_denied')
    except ValueError:
        return refused(report, 'path', 'primary_path_not_character')
    except (Exception, KeyboardInterrupt):
        return refused(report, 'path', 'primary_path_check_failed')
    report.update(primary_verified=True, phase='complete', category='primary_verified',
                  result='PRIMARY_INTERFACE_VERIFIED' if require_primary else 'HOST_DIAGNOSTIC_COMPLETE')
    return report, 0


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--require-primary', action='store_true',
                        help='require one exact primary character-device candidate; never open it')
    try:
        args = parser.parse_args(argv)
        report, status = inspect_host(args.require_primary)
    except ArgumentsError:
        report, status = refused(base_report(False), 'arguments', 'invalid_arguments')
    except (Exception, KeyboardInterrupt):
        # Last-resort containment never emits exception messages or a traceback.
        report, status = refused(base_report(False), 'diagnostic', 'diagnostic_failed')
    print(json.dumps(report, sort_keys=True))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
