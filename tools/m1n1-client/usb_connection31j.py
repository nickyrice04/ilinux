# SPDX-License-Identifier: MIT
"""Bounded cached-registry observations before any device is opened.

The returned callout path is private; only the separate report may be logged.
No transport backend, serial open, native receipt or target request exists here.
An outer controller exception is retained privately as callback_exception so
the caller can preserve its own deadline/interrupt provenance without printing
an arbitrary exception message. This module never retries such a failure.
"""
import copy
import importlib.util
import math
from pathlib import Path
import plistlib
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('frozen_host_diagnostic31j', HERE / 'usb-discovery31j.py')
host = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(host)

MAX_QUERIES = 4
QUERY_TIMEOUT_SECONDS = 3.0
WAIT_SECONDS = 1.0
TOTAL_SECONDS = 15.0
WAITABLE = frozenset(('empty_stdout_unresolved', 'no_primary_candidate'))


class ConnectionRefusal(Exception):
    """Fixed-label refusal with a sanitized snapshot and private provenance."""
    def __init__(self, reason, report, callback_exception=None, interruptions=()):
        super().__init__(reason)
        self.reason = reason
        self.report = copy.deepcopy(report)
        self.interruptions = tuple(interruptions) + (() if callback_exception is None else (callback_exception,))
        self.callback_exception = self.interruptions[0] if self.interruptions else None


def _observe(timeout, row):
    """Perform exactly one query. Return private path and private interruption."""
    def outcome(phase, category, interruption=None):
        row.update(state='complete', phase=phase, category=category)
        return None, interruption

    try:
        query = subprocess.run(list(host.QUERY), stdin=subprocess.DEVNULL,
                               capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        return outcome('query', 'query_timeout')
    except FileNotFoundError:
        return outcome('query', 'query_executable_missing')
    except PermissionError:
        return outcome('query', 'query_permission_denied')
    except (Exception, KeyboardInterrupt) as exc:
        return outcome('query', 'query_failed', exc)
    row['query_returned'] = True
    if type(query.returncode) is not int or query.returncode != 0:
        return outcome('query', 'query_nonzero_exit')
    raw = query.stdout
    if type(raw) is not bytes or type(query.stderr) is not bytes:
        return outcome('query', 'query_output_type')
    row['stderr_present'] = bool(query.stderr)
    if len(raw) > host.MAX_OUTPUT_BYTES:
        return outcome('parse', 'stdout_size_limit')
    if raw == b'':
        row['stdout_kind'] = 'empty'
        return outcome('parse', 'empty_stdout_unresolved')
    if all(byte in b' \t\r\n' for byte in raw):
        row['stdout_kind'] = 'whitespace'
        return outcome('parse', 'whitespace_stdout')
    row['stdout_kind'] = ('binary_candidate' if raw.startswith(b'bplist00') else
                          'xml_candidate' if raw.startswith((b'<?xml', b'<plist')) else 'other')
    try:
        roots = plistlib.loads(raw)
    except (Exception, KeyboardInterrupt) as exc:
        return outcome('parse', 'invalid_plist', exc)
    row['stdout_kind'] = 'binary_plist' if raw.startswith(b'bplist00') else 'xml_plist'
    try:
        host.validate_tree(roots)
        ports = host.identity.registry_ports(roots)
    except host.ShapeError:
        return outcome('tree', 'invalid_registry_shape')
    except (Exception, KeyboardInterrupt) as exc:
        return outcome('tree', 'registry_metadata_invalid', exc)
    candidates = sum(port.primary for port in ports)
    row.update(inventory_classified=True, modem_interfaces=len(ports), primary_candidates=candidates)
    if candidates == 0:
        return outcome('identity', 'no_primary_candidate')
    if candidates != 1:
        return outcome('identity', 'ambiguous_primary_candidates')
    try:
        path = host.identity.select_primary(ports, 'auto')
    except FileNotFoundError:
        return outcome('path', 'primary_path_absent')
    except PermissionError:
        return outcome('path', 'primary_path_access_denied')
    except ValueError as exc:
        # The outer controller's deadline Refusal also derives from ValueError.
        return outcome('path', 'primary_path_not_character', exc)
    except (Exception, KeyboardInterrupt) as exc:
        return outcome('path', 'primary_path_check_failed', exc)
    row.update(state='complete', phase='complete', category='primary_verified', primary_verified=True)
    return path, None


class _Discovery:
    def __init__(self, progress, clock, sleep):
        self.progress, self.clock, self.sleep = progress, clock, sleep
        self.started = self.last = None
        self.report = dict(schema='usb_connection31j', result='OBSERVING',
                           reason='pending', phase='discovery', query_attempts=0,
                           query_returns=0, elapsed_seconds=0.0, ready=False,
                           native_ready=False, device_opens=0, target_requests=0,
                           progress_callback_failed=False,
                           observations=[])

    def stop(self, reason, phase='discovery', interruption=None, interruptions=()):
        self.report.update(result='STOP', reason=reason, phase=phase, ready=False)
        raise ConnectionRefusal(reason, self.report, interruption, interruptions) from None

    def now(self):
        try:
            value = self.clock()
        except (Exception, KeyboardInterrupt) as exc:
            self.stop('clock_failed', 'clock', exc)
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except (Exception, KeyboardInterrupt) as exc:
            # An outer alarm Refusal inherits ValueError; never discard it.
            self.stop('clock_invalid', 'clock', exc)
        if not valid:
            self.stop('clock_invalid', 'clock')
        if self.last is not None and value < self.last:
            self.stop('clock_regressed', 'clock')
        if self.started is None:
            self.started = value
        elapsed = value - self.started
        try:
            finite_elapsed = math.isfinite(elapsed)
        except (Exception, KeyboardInterrupt) as exc:
            self.stop('clock_invalid', 'clock', exc)
        if not finite_elapsed:
            self.stop('clock_invalid', 'clock')
        self.last = value
        self.report['elapsed_seconds'] = round(elapsed, 6)
        return value

    def budget(self):
        remaining = TOTAL_SECONDS - (self.now() - self.started)
        if remaining <= 0:
            self.stop('discovery_deadline', 'deadline')
        return remaining

    def emit(self, interruptions=()):
        if self.progress is not None:
            try:
                self.progress(copy.deepcopy(self.report))
            except (Exception, KeyboardInterrupt) as exc:
                self.report['progress_callback_failed'] = True
                self.stop('progress_callback_failed', 'progress', exc, interruptions)

    def run(self):
        if sys.platform != 'darwin':
            self.stop('unsupported_platform', 'platform')
        self.now()
        for index in range(1, MAX_QUERIES + 1):
            self.budget()
            row = dict(query_index=index, state='scheduled', phase='query', category='pending',
                       query_returned=False, inventory_classified=False, primary_verified=False)
            self.report['observations'].append(row)
            self.emit()  # Callback failure means this query never starts.
            remaining = self.budget()  # Include time spent in the callback.
            timeout = min(QUERY_TIMEOUT_SECONDS, remaining)
            row.update(state='querying', started_at_seconds=self.report['elapsed_seconds'])
            self.report['query_attempts'] += 1
            try:
                path, interruption = _observe(timeout, row)
            except (Exception, KeyboardInterrupt) as exc:
                row.update(state='complete', phase='query', category='discovery_failed')
                path, interruption = None, exc
            self.report['query_returns'] += int(row['query_returned'])
            timing_failure = None
            try:
                self.now()
                row['elapsed_seconds'] = round(self.report['elapsed_seconds'] - row['started_at_seconds'], 6)
            except ConnectionRefusal as exc:
                timing_failure = exc
            interruptions = (() if interruption is None else (interruption,))
            if timing_failure is not None:
                interruptions += timing_failure.interruptions
            # Retain earlier interruptions if this evidence write also fails.
            self.emit(interruptions)
            if timing_failure is not None:
                self.stop(timing_failure.reason, timing_failure.report['phase'], interruptions=interruptions)
            if row['category'] not in WAITABLE and row['category'] != 'primary_verified':
                self.stop(row['category'], row['phase'], interruption)
            self.budget()  # Never return a path after query/callback consumed the deadline.
            if path is not None:
                self.report.update(result='PRIMARY_INTERFACE_VERIFIED', reason='primary_verified',
                                   phase='complete', ready=True)
                return path, copy.deepcopy(self.report)
            if index == MAX_QUERIES:
                self.stop('enumeration_unavailable', 'identity')
            remaining = self.budget()
            if remaining <= WAIT_SECONDS:
                self.stop('discovery_deadline', 'deadline')
            try:
                self.sleep(WAIT_SECONDS)
            except (Exception, KeyboardInterrupt) as exc:
                self.stop('enumeration_wait_failed', 'wait', exc)
            # Recheck clock/deadline before any subsequent cached query.
        self.stop('enumeration_unavailable', 'identity')


def discover_primary(progress=None, clock=time.monotonic, sleep=time.sleep):
    """Return (private_path, sanitized_report), or raise ConnectionRefusal.

progress(snapshot) runs before and after each query. Only an exact empty stdout
or a valid zero-primary inventory can wait for another observation. The
snapshot given to callbacks is independent of internal state. Successful return
means metadata/lstat readiness only, never a handshake or native readiness.
"""
    session = _Discovery(progress, clock, sleep)
    try:
        return session.run()
    except ConnectionRefusal:
        raise
    except (Exception, KeyboardInterrupt) as exc:
        # Preserve the current prefix if an asynchronous outer alarm interrupts
        # bookkeeping between the explicitly guarded query/callback operations.
        session.stop('discovery_interrupted', 'discovery', exc)
