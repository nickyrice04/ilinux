#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the fixed 31N controller once, with an independent 65-second deadline.

This is the live launcher, not the offline intake. No USB operations exist in
this parent. Exclusive local evidence is retained even on child failure; no
retry, reconnect, target cleanup, or macOS/boot-setting operation is attempted.
The child discovery wait is included in this 65-second deadline. Supervisor
reservation does not claim native consumption; consult the child evidence.
The separate human 90-second return timer is still required.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CONFIRM = 'START-CPU1-J716C-31N'
LIVE_READY = True
DEADLINE_SECONDS = 65
TERMINATION_SECONDS = 2
ACTION = 'power off M5 and return to Macintosh HD; no retry'
FILES = ('supervisor-once.json', 'connection.jsonl', 'consumed.jsonl', 'controller.json',
         'controller.stderr', 'supervisor-result.json')
# Deliberately static: verify the complete required closure before importing or
# spawning the controller. Tests compare this set to the offline intake's set.
REQUIRED_SOURCES = frozenset({
    'hardware/adt/adt-sanitized.json',
    'kernel/experiments/cpu-topology31f/audit.py',
    'kernel/experiments/cpu-topology31f/capture_linux.py',
    'kernel/experiments/cpu-topology31f/test_topology.py',
    'kernel/experiments/cpu-topology31g/collect.py',
    'kernel/experiments/cpu-topology31g/test_topology.py',
    'kernel/experiments/cpu-topology31g/topology.py',
    'kernel/experiments/smp31/audit_boot021.py',
    'kernel/experiments/smp31/audit_console31d.py',
    'kernel/experiments/smp31/boot021-ram-layout.json',
    'kernel/experiments/smp31/helper31b.S',
    'kernel/experiments/smp31/memory_fixture31c.py',
    'kernel/experiments/smp31/rea-validation.json',
    'kernel/experiments/smp31/renderer.py',
    'kernel/experiments/smp31/test_audit_boot021.py',
    'kernel/experiments/smp31/test_client31b_vm.py',
    'kernel/experiments/smp31/test_client31c_vm.py',
    'kernel/experiments/smp31/test_client31d_vm.py',
    'kernel/experiments/smp31/test_client31e_vm.py',
    'kernel/experiments/smp31/test_client31f_vm.py',
    'kernel/experiments/smp31/test_client31g_vm.py',
    'kernel/experiments/smp31/test_client31h_vm.py',
    'kernel/experiments/smp31/test_client31i_vm.py',
    'kernel/experiments/smp31/test_client31j_vm.py',
    'kernel/experiments/smp31/test_client31k_vm.py',
    'kernel/experiments/smp31/test_client31l_vm.py',
    'kernel/experiments/smp31/test_client31m_vm.py',
    'kernel/experiments/smp31/test_client31n_vm.py',
    'kernel/experiments/smp31/test_console31d.c',
    'kernel/experiments/smp31/test_helper31b.c',
    'kernel/experiments/smp31/test_loop31b.c',
    'kernel/experiments/smp31/test_parser_vm.py',
    'kernel/experiments/smp31/test_renderer.py',
    'kernel/experiments/smp31e-emulator/README.md',
    'kernel/experiments/smp31e-emulator/emulate.py',
    'kernel/experiments/smp31e-emulator/first_frame.S',
    'kernel/experiments/smp31e-emulator/recorder_check.py',
    'kernel/experiments/smp31e-emulator/test_emulate.py',
    'kernel/experiments/smp31e-emulator/test_first_frame.c',
    'kernel/experiments/smp31e-emulator/test_recorder_check.py',
    'kernel/experiments/smp31e-entry/.gitignore',
    'kernel/experiments/smp31e-entry/README.md',
    'kernel/experiments/smp31e-entry/audit.json',
    'kernel/experiments/smp31e-entry/audit.py',
    'kernel/experiments/smp31e-entry/build_recorder.py',
    'kernel/experiments/smp31e-entry/observe.py',
    'kernel/experiments/smp31e-entry/permission_helper.S',
    'kernel/experiments/smp31e-entry/permissions.py',
    'kernel/experiments/smp31e-entry/recorder.S',
    'kernel/experiments/smp31e-entry/start_helper.S',
    'kernel/experiments/smp31e-entry/telemetry.py',
    'kernel/experiments/smp31e-entry/test_audit.py',
    'kernel/experiments/smp31e-entry/test_observe.py',
    'kernel/experiments/smp31e-entry/test_permissions.py',
    'kernel/experiments/smp31e-entry/test_recorder.py',
    'kernel/experiments/smp31e-entry/test_telemetry.py',
    'kernel/experiments/smp31e-observer/README.md',
    'kernel/experiments/smp31e-observer/collector.py',
    'kernel/experiments/smp31e-observer/test_collector.py',
    'kernel/experiments/smp31f-entry/audit.py',
    'kernel/experiments/smp31f-entry/builder.py',
    'kernel/experiments/smp31f-entry/permissions.py',
    'kernel/experiments/smp31f-entry/recorder.S',
    'kernel/experiments/smp31f-entry/recorder_check.py',
    'kernel/experiments/smp31f-entry/telemetry.py',
    'kernel/experiments/smp31f-entry/test_permissions.py',
    'kernel/experiments/smp31f-entry/test_recorder_check.py',
    'kernel/experiments/smp31f-entry/test_telemetry.py',
    'kernel/experiments/smp31g-observation/fixture.py',
    'kernel/experiments/smp31g-observation/live_binding.py',
    'kernel/experiments/smp31g-observation/plan.py',
    'kernel/experiments/smp31g-observation/read32.S',
    'kernel/experiments/smp31g-observation/test_binding_vm.py',
    'kernel/experiments/smp31g-observation/test_plan.py',
    'kernel/experiments/smp31g-observation/test_read32.c',
    'kernel/experiments/smp31g-observation/test_tracker.py',
    'kernel/experiments/smp31g-observation/tracker.py',
    'kernel/experiments/smp31g-publication/audit.py',
    'kernel/experiments/smp31g-publication/test_audit.py',
    'kernel/experiments/smp31h-reset-format/audit.py',
    'kernel/experiments/smp31h-reset-format/cpu_state.py',
    'kernel/experiments/smp31h-reset-format/observer.py',
    'kernel/experiments/smp31h-reset-format/test_audit.py',
    'kernel/experiments/smp31h-reset-format/test_cpu_state.py',
    'kernel/experiments/smp31h-reset-format/test_observer.py',
    'kernel/experiments/smp31i-readback/gate.py',
    'kernel/experiments/smp31i-readback/test_gate.py',
    'kernel/experiments/smp31k-control/README.md',
    'kernel/experiments/smp31k-control/audit.py',
    'kernel/experiments/smp31k-control/control.S',
    'kernel/experiments/smp31k-control/control.py',
    'kernel/experiments/smp31k-control/test_control.py',
    'kernel/experiments/smp31k-entry/README.md',
    'kernel/experiments/smp31k-entry/audit.py',
    'kernel/experiments/smp31k-entry/builder.py',
    'kernel/experiments/smp31k-entry/model.py',
    'kernel/experiments/smp31k-entry/permissions.py',
    'kernel/experiments/smp31k-entry/telemetry.py',
    'kernel/experiments/smp31k-entry/test_tripwire.py',
    'kernel/experiments/smp31k-entry/tripwire.S',
    'kernel/experiments/smp31k-entry/tripwire.ld',
    'kernel/experiments/smp31l-candidate/README.md',
    'kernel/experiments/smp31l-candidate/audit.py',
    'kernel/experiments/smp31l-candidate/builder.py',
    'kernel/experiments/smp31l-candidate/model.py',
    'kernel/experiments/smp31l-candidate/prefix.S',
    'kernel/experiments/smp31l-candidate/test_candidate.py',
    'kernel/experiments/smp31l-candidate/validation.json',
    'kernel/experiments/smp31l-observer/observer.py',
    'kernel/experiments/smp31l-observer/test_observer.py',
    'kernel/experiments/smp31m-observer/README.md',
    'kernel/experiments/smp31m-observer/audit.py',
    'kernel/experiments/smp31m-observer/ctr.S',
    'kernel/experiments/smp31m-observer/observer.py',
    'kernel/experiments/smp31m-observer/test_audit.py',
    'kernel/experiments/smp31m-observer/test_observer.py',
    'kernel/experiments/smp31m-observer/validation.json',
    'kernel/experiments/smp31n-startpair/README.md',
    'kernel/experiments/smp31n-startpair/audit.py',
    'kernel/experiments/smp31n-startpair/plan.py',
    'kernel/experiments/smp31n-startpair/start_pair.S',
    'kernel/experiments/smp31n-startpair/test_plan.py',
    'kernel/experiments/smp31n-startpair/test_prior_gap.py',
    'kernel/experiments/t6050-dt/gen_t6050_dt.py',
    'kernel/experiments/usb-gadget-dt/fdtedit.py',
    'native/boot/README.md',
    'native/boot/attempt31b-controller-2026-10-21.json',
    'native/boot/attempt31b/validation.json',
    'native/boot/attempt31b/validation.md',
    'native/boot/attempt31c-controller-2026-10-21.json',
    'native/boot/attempt31c/review.md',
    'native/boot/attempt31c/validation.json',
    'native/boot/attempt31d-controller-2026-10-21.json',
    'native/boot/attempt31d/console-binding.json',
    'native/boot/attempt31d/review.md',
    'native/boot/attempt31d/validation.json',
    'native/boot/attempt31e/controller-review.md',
    'native/boot/attempt31e/publication-review.md',
    'native/boot/attempt31e/review.md',
    'native/boot/attempt31f/controller-review.md',
    'native/boot/attempt31f/entry-review.md',
    'native/boot/attempt31f/plan.md',
    'native/boot/attempt31f/startup-review.md',
    'native/boot/attempt31g/controller-review.md',
    'native/boot/attempt31g/controller-validation.md',
    'native/boot/attempt31g/source-sha256.txt',
    'native/boot/attempt31g/topology-observation.json',
    'native/boot/attempt31h-controller-2026-10-21.json',
    'native/boot/attempt31h-plan.md',
    'native/boot/attempt31h/controller-review.md',
    'native/boot/attempt31h/controller-validation.md',
    'native/boot/attempt31h/source-sha256.txt',
    'native/boot/attempt31i/controller-review.md',
    'native/boot/attempt31i/controller-validation.md',
    'native/boot/attempt31i/source-sha256.txt',
    'native/boot/attempt31j-host-m1-2026-10-21.json',
    'native/boot/attempt31j-host/source-sha256.txt',
    'native/boot/attempt31j-host/validation.json',
    'native/boot/attempt31j/controller-review.md',
    'native/boot/attempt31j/controller-validation.md',
    'native/boot/attempt31j/source-sha256.txt',
    'native/boot/attempt31k/controller-review.md',
    'native/boot/attempt31k/controller-validation.md',
    'native/boot/attempt31k/source-sha256.txt',
    'native/boot/attempt31l-2026-10-22-result.md',
    'native/boot/attempt31l-controller-2026-10-22.json',
    'native/boot/attempt31l/controller-review.md',
    'native/boot/attempt31l/controller-validation.md',
    'native/boot/attempt31l/source-sha256.txt',
    'native/boot/attempt31m-2026-10-22-result.md',
    'native/boot/attempt31m-controller-2026-10-22.json',
    'native/boot/attempt31m/controller-review.md',
    'native/boot/attempt31m/controller-validation.md',
    'native/boot/attempt31m/source-sha256.txt',
    'native/boot/attempt31n/controller-review.md',
    'native/boot/attempt31n/controller-validation.md',
    'native/boot/cpu_observe.py',
    'native/boot/dapf_guard.py',
    'native/boot/entry_guard.py',
    'native/boot/fdt.py',
    'native/boot/gpio_guard.py',
    'native/boot/launch.py',
    'native/boot/package-manifest.json',
    'native/boot/smp31_census.py',
    'native/boot/smp31b.py',
    'native/boot/smp31c.py',
    'native/boot/smp31d.py',
    'native/boot/smp31e.py',
    'native/boot/smp31f.py',
    'native/boot/smp31g.py',
    'native/boot/smp31h.py',
    'native/boot/smp31i.py',
    'native/boot/smp31j.py',
    'native/boot/smp31k.py',
    'native/boot/smp31l.py',
    'native/boot/smp31m.py',
    'native/boot/smp31n.py',
    'native/boot/test_smp31_census.py',
    'native/boot/test_smp31b.py',
    'native/boot/test_smp31c.py',
    'native/boot/test_smp31d.py',
    'native/boot/test_smp31e.py',
    'native/boot/test_smp31f.py',
    'native/boot/test_smp31g.py',
    'native/boot/test_smp31h.py',
    'native/boot/test_smp31i.py',
    'native/boot/test_smp31j.py',
    'native/boot/test_smp31k.py',
    'native/boot/test_smp31l.py',
    'native/boot/test_smp31m.py',
    'native/boot/test_smp31n.py',
    'research/native31g-reset-routing.md',
    'research/native31h-reset-entry.md',
    'research/native31i-readback.md',
    'research/native31j-connection.md',
    'research/native31j-host-discovery.md',
    'research/native31k-entry.md',
    'research/native31l-entry.md',
    'research/native31l-first-fetch.md',
    'research/native31l-platform-prepare.md',
    'research/native31m-firmware.md',
    'research/native31m-result-review.md',
    'research/native31m-upstream.md',
    'research/native31n-firmware.md',
    'research/native31n-result-review.md',
    'research/native31n-upstream.md',
    'research/testing-strategy-31e.md',
    'reverse-engineering/findings/cpu-startup-2026-10-21/README.md',
    'reverse-engineering/findings/cpu-startup-2026-10-21/validation.json',
    'reverse-engineering/findings/cpu-startup31k/entry-provenance-validation.json',
    'reverse-engineering/findings/cpu-startup31l-first-fetch/validation.json',
    'reverse-engineering/findings/cpu-startup31l-platform/validation.json',
    'reverse-engineering/findings/cpu-startup31l/entry-provenance-validation.json',
    'reverse-engineering/findings/cpu-startup31m/validation.json',
    'reverse-engineering/findings/cpu-startup31n/validation.json',
    'tools/boot-campaign/README.md',
    'tools/boot-campaign/campaign.py',
    'tools/boot-campaign/fixtures/31b-controller.json',
    'tools/boot-campaign/fixtures/31c-controller.json',
    'tools/boot-campaign/fixtures/31d-controller.json',
    'tools/boot-campaign/fixtures/sha256.json',
    'tools/boot-campaign/fixtures/synthetic-partial-entry.json',
    'tools/boot-campaign/fixtures/synthetic-success.json',
    'tools/boot-campaign/test_campaign.py',
    'tools/m1n1-client/attempt31b-instructions.md',
    'tools/m1n1-client/attempt31b-supervise.py',
    'tools/m1n1-client/attempt31c-instructions.md',
    'tools/m1n1-client/attempt31c-supervise.py',
    'tools/m1n1-client/attempt31d-instructions.md',
    'tools/m1n1-client/attempt31d-supervise.py',
    'tools/m1n1-client/attempt31e-instructions.md',
    'tools/m1n1-client/attempt31e-offline.py',
    'tools/m1n1-client/attempt31e-supervisor.py',
    'tools/m1n1-client/attempt31f-instructions.md',
    'tools/m1n1-client/attempt31f-offline.py',
    'tools/m1n1-client/attempt31f-supervisor.py',
    'tools/m1n1-client/attempt31g-instructions.md',
    'tools/m1n1-client/attempt31g-offline.py',
    'tools/m1n1-client/attempt31g-supervisor.py',
    'tools/m1n1-client/attempt31h-instructions.md',
    'tools/m1n1-client/attempt31h-offline.py',
    'tools/m1n1-client/attempt31h-supervisor.py',
    'tools/m1n1-client/attempt31i-instructions.md',
    'tools/m1n1-client/attempt31i-offline.py',
    'tools/m1n1-client/attempt31i-supervisor.py',
    'tools/m1n1-client/attempt31j-host-instructions.md',
    'tools/m1n1-client/attempt31j-instructions.md',
    'tools/m1n1-client/attempt31j-offline.py',
    'tools/m1n1-client/attempt31j-supervisor.py',
    'tools/m1n1-client/attempt31k-instructions.md',
    'tools/m1n1-client/attempt31k-offline.py',
    'tools/m1n1-client/attempt31k-supervisor.py',
    'tools/m1n1-client/attempt31l-instructions.md',
    'tools/m1n1-client/attempt31l-offline.py',
    'tools/m1n1-client/attempt31l-supervisor.py',
    'tools/m1n1-client/attempt31m-instructions.md',
    'tools/m1n1-client/attempt31m-offline.py',
    'tools/m1n1-client/attempt31m-supervisor.py',
    'tools/m1n1-client/attempt31n-instructions.md',
    'tools/m1n1-client/attempt31n-offline.py',
    'tools/m1n1-client/attempt31n-supervisor.py',
    'tools/m1n1-client/m1n1-revision.txt',
    'tools/m1n1-client/pin_check.py',
    'tools/m1n1-client/run.sh',
    'tools/m1n1-client/stage-b-instructions.md',
    'tools/m1n1-client/test_attempt31b_supervise.py',
    'tools/m1n1-client/test_attempt31c_supervise.py',
    'tools/m1n1-client/test_attempt31d_supervise.py',
    'tools/m1n1-client/test_attempt31e_offline.py',
    'tools/m1n1-client/test_attempt31e_supervisor.py',
    'tools/m1n1-client/test_attempt31f_offline.py',
    'tools/m1n1-client/test_attempt31f_supervisor.py',
    'tools/m1n1-client/test_attempt31g_offline.py',
    'tools/m1n1-client/test_attempt31g_supervisor.py',
    'tools/m1n1-client/test_attempt31h_offline.py',
    'tools/m1n1-client/test_attempt31h_supervisor.py',
    'tools/m1n1-client/test_attempt31i_offline.py',
    'tools/m1n1-client/test_attempt31i_supervisor.py',
    'tools/m1n1-client/test_attempt31j_offline.py',
    'tools/m1n1-client/test_attempt31j_supervisor.py',
    'tools/m1n1-client/test_attempt31k_offline.py',
    'tools/m1n1-client/test_attempt31k_supervisor.py',
    'tools/m1n1-client/test_attempt31l_offline.py',
    'tools/m1n1-client/test_attempt31l_supervisor.py',
    'tools/m1n1-client/test_attempt31m_offline.py',
    'tools/m1n1-client/test_attempt31m_supervisor.py',
    'tools/m1n1-client/test_attempt31n_offline.py',
    'tools/m1n1-client/test_attempt31n_supervisor.py',
    'tools/m1n1-client/test_usb_connection31j.py',
    'tools/m1n1-client/test_usb_discovery31j.py',
    'tools/m1n1-client/test_usb_identity.py',
    'tools/m1n1-client/usb-check.py',
    'tools/m1n1-client/usb-discovery31j.py',
    'tools/m1n1-client/usb_connection31j.py',
    'tools/m1n1-client/usb_identity.py',
    'tools/m1n1-client/verify-package.py',
    'virtualization/jobs/059-smp31b/run.sh',
    'virtualization/jobs/060-smp31c/run.sh',
    'virtualization/jobs/061-smp31d/run.sh',
    'virtualization/jobs/062-smp31e/run.sh',
    'virtualization/jobs/063-smp31e-controller/run.sh',
    'virtualization/jobs/064-smp31f/run.sh',
    'virtualization/jobs/065-smp31g/run.sh',
    'virtualization/jobs/066-smp31h/run.sh',
    'virtualization/jobs/067-smp31i/run.sh',
    'virtualization/jobs/068-smp31j/run.sh',
    'virtualization/jobs/069-smp31k/run.sh',
    'virtualization/jobs/071-smp31l/run.sh',
    'virtualization/jobs/072-smp31m/run.sh',
    'virtualization/jobs/073-smp31n/run.sh',
})



class Refusal(Exception):
    """Only fixed, non-sensitive labels reach public output."""


class DeadlineTerminationFailure(Exception):
    """The deadline fired, but child termination could not be confirmed."""


def require(ok, label):
    if not ok:
        raise Refusal(label)


def no_symlink(path):
    require(path.is_relative_to(ROOT), 'path_outside_workspace')
    for item in (path, *path.parents):
        if item == ROOT or item.is_relative_to(ROOT):
            require(not item.is_symlink(), 'workspace_symlink')


def verify_sources():
    """Do not import the controller merely to check its own digest."""
    manifest = ROOT / 'native/boot/attempt31n/source-sha256.txt'
    no_symlink(manifest)
    require(manifest.is_file() and manifest.stat().st_size <= 65536,
            'source_manifest')
    data = manifest.read_bytes()
    seen = set()
    try:
        lines = data.decode('ascii').splitlines()
    except UnicodeDecodeError:
        raise Refusal('source_manifest_syntax') from None
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', line)
        require(match is not None, 'source_manifest_syntax')
        digest, name = match.groups()
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts
                and relative.as_posix() == name and name not in seen,
                'source_manifest_path')
        path = ROOT / relative
        no_symlink(path)
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                'source_digest_mismatch')
        seen.add(name)
    require(REQUIRED_SOURCES <= seen, 'source_manifest_incomplete')
    return hashlib.sha256(data).hexdigest()


def durable_json(path, value):
    """Exclusive creation never follows or overwrites an earlier receipt."""
    no_symlink(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    dirfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def open_capture(path):
    no_symlink(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    return os.fdopen(fd, 'wb')


def signal_group(proc, sig):
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        # A child may exit between TimeoutExpired/poll and killpg. Reap it;
        # preserve the expired outcome rather than treating this as success.
        pass


def stop_child(proc):
    signal_group(proc, signal.SIGTERM)
    try:
        proc.wait(timeout=TERMINATION_SECONDS)
    except subprocess.TimeoutExpired:
        signal_group(proc, signal.SIGKILL)
        proc.wait(timeout=TERMINATION_SECONDS)


def wait_bounded(proc, seconds=DEADLINE_SECONDS):
    """seconds is injectable for offline tests, never a command-line option."""
    try:
        return proc.wait(timeout=seconds), False
    except subprocess.TimeoutExpired:
        try:
            stop_child(proc)
        except (Exception, KeyboardInterrupt):
            raise DeadlineTerminationFailure() from None
        return 124, True


def run(image):
    require(LIVE_READY, 'native_release_not_ready')
    pins = verify_sources()
    out = ROOT / 'build/native-intake/attempt31n'
    no_symlink(out)
    out.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        path = out / name
        no_symlink(path)
        require(not path.exists(), 'attempt_already_reserved')
    start = time.monotonic()
    # This reserves one launcher invocation, not a native experiment. The child
    # creates consumed.jsonl only after verified discovery and before Serial.
    # Never infer that consumption from process creation or this static snapshot.
    durable_json(out / 'supervisor-once.json', {
        'experiment': 'smp31n', 'invocation_reserved': True,
        'consumed': False, 'scope': 'supervisor_invocation_only',
        'source_manifest_sha256': pins,
    })
    proc = None
    rc, expired, reason = None, False, 'supervisor_failure'
    supervisor_exit = 1
    try:
        with open_capture(out / 'controller.json') as stdout, \
                open_capture(out / 'controller.stderr') as stderr:
            require(verify_sources() == pins, 'sources_changed_before_spawn')
            proc = subprocess.Popen([
                str(ROOT / 'tools/m1n1-client/run.sh'),
                str(ROOT / 'native/boot/smp31n.py'), '--image', str(image.absolute()),
                '--live', '--confirm', CONFIRM,
            ], stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                cwd=ROOT, start_new_session=True)
            rc, expired = wait_bounded(proc)
            supervisor_exit = rc
            reason = 'controller_deadline' if expired else 'controller_exited'
    except (Exception, KeyboardInterrupt) as exc:
        supervisor_exit = 1
        reason = 'supervisor_interrupted' if isinstance(exc, KeyboardInterrupt) else (
            str(exc) if isinstance(exc, Refusal) else 'supervisor_failure')
        if isinstance(exc, DeadlineTerminationFailure):
            expired, supervisor_exit = True, 124
            reason = 'child_termination_unconfirmed'
        elif proc is not None and proc.poll() is None:
            try:
                stop_child(proc)
            except (Exception, KeyboardInterrupt):
                # Target state stays unknown. Never try another controller.
                reason = 'child_termination_unconfirmed'
    # Child final/consumed journal is authoritative for native consumption.
    # controller_started records process spawn only, including pre-open refusals.
    result = {
        'experiment': 'smp31n', 'controller_exit': rc,
        'supervisor_exit': supervisor_exit,
        'controller_started': proc is not None,
        'supervisor_deadline': expired, 'supervisor_reason': reason,
        'elapsed_seconds': round(time.monotonic() - start, 3),
        'source_manifest_sha256': pins,
        'action': ACTION,
    }
    durable_json(out / 'supervisor-result.json', result)
    print(json.dumps(result, indent=2))
    return supervisor_exit


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--confirm', required=True)
    args = parser.parse_args(argv)
    require(args.confirm == CONFIRM, 'confirmation')
    return run(args.image)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(json.dumps({'result': 'STOP',
                          'reason': str(exc) if isinstance(exc, Refusal)
                          else ('supervisor_interrupted' if isinstance(exc, KeyboardInterrupt)
                                else 'supervisor_failure'),
                          'action': ('stay in macOS; 31N native release is not ready'
                                     if isinstance(exc, Refusal) and str(exc) == 'native_release_not_ready'
                                     else ACTION)}))
        raise SystemExit(1)
