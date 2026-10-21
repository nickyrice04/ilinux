"""Offline supervisor tests. Only explicitly owned dummy children are started."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('supervisor31g',
    Path(__file__).with_name('attempt31g-supervisor.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DeadlineTests(unittest.TestCase):
    def test_normal_nonzero_exit(self):
        proc = subprocess.Popen([sys.executable, '-I', '-c', 'raise SystemExit(7)'],
                                start_new_session=True)
        self.assertEqual(m.wait_bounded(proc, 5), (7, False))

    def test_stalled_child_terminated(self):
        proc = subprocess.Popen([sys.executable, '-I', '-c',
                                 'import time; time.sleep(30)'], start_new_session=True)
        try:
            self.assertEqual(m.wait_bounded(proc, 0.1), (124, True))
            self.assertIsNotNone(proc.poll())
        finally:
            if proc.poll() is None:
                proc.kill(); proc.wait()

    def test_sigterm_ignored_child_killed(self):
        readfd, writefd = os.pipe()
        proc = subprocess.Popen([sys.executable, '-I', '-c',
            'import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
            f'os.write({writefd},b"r"); time.sleep(30)'],
            pass_fds=(writefd,), start_new_session=True)
        os.close(writefd)
        try:
            self.assertEqual(os.read(readfd, 1), b'r')
            self.assertEqual(m.wait_bounded(proc, 0.1), (124, True))
            self.assertEqual(proc.returncode, -signal.SIGKILL)
        finally:
            os.close(readfd)
            if proc.poll() is None:
                proc.kill(); proc.wait()

    def test_exit_race_keeps_deadline(self):
        proc = mock.Mock(pid=123)
        proc.wait.side_effect = [subprocess.TimeoutExpired('dummy', 1), 0]
        with mock.patch.object(m.os, 'killpg', side_effect=ProcessLookupError):
            self.assertEqual(m.wait_bounded(proc, 1), (124, True))
        self.assertEqual(proc.wait.call_count, 2)


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patch = mock.patch.object(m, 'ROOT', self.root)
        patch.start(); self.addCleanup(patch.stop)
        self.manifest = self.root / 'native/boot/attempt31g/source-sha256.txt'
        self.manifest.parent.mkdir(parents=True)
        for name in m.REQUIRED_SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('test-only original fixture\n')
        self.write_pins()
        self.out = self.root / 'build/native-intake/attempt31g'
        self.stdout = io.StringIO()
        redirect = contextlib.redirect_stdout(self.stdout)
        redirect.__enter__(); self.addCleanup(redirect.__exit__, None, None, None)

    def write_pins(self):
        self.manifest.write_text(''.join(
            f'{hashlib.sha256((self.root / name).read_bytes()).hexdigest()}  {name}\n'
            for name in sorted(m.REQUIRED_SOURCES)))

    def result(self):
        return json.loads((self.out / 'supervisor-result.json').read_text())

    def test_fixed_command_and_exclusive_receipts(self):
        proc = mock.Mock()
        with mock.patch.object(m.subprocess, 'Popen', return_value=proc) as spawn, \
                mock.patch.object(m, 'wait_bounded', return_value=(0, False)):
            self.assertEqual(m.run(Path('image.bin')), 0)
            args, kwargs = spawn.call_args
            self.assertEqual(args[0], [str(self.root / 'tools/m1n1-client/run.sh'),
                str(self.root / 'native/boot/smp31g.py'), '--image',
                str(Path('image.bin').absolute()), '--live', '--confirm', m.CONFIRM])
            self.assertTrue(kwargs['start_new_session'])
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(kwargs['cwd'], self.root)
            with self.assertRaisesRegex(m.Refusal, '^attempt_already_reserved$'):
                m.run(Path('image.bin'))
            spawn.assert_called_once()
        self.assertEqual(self.result()['supervisor_reason'], 'controller_exited')
        self.assertTrue(self.result()['controller_started'])
        self.assertEqual((self.out / 'supervisor-once.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.out / 'controller.json').stat().st_mode & 0o777, 0o600)

    def test_all_existing_evidence_refuses_before_spawn(self):
        self.out.mkdir(parents=True)
        with mock.patch.object(m.subprocess, 'Popen') as spawn:
            for name in m.FILES:
                with self.subTest(name=name):
                    path = self.out / name
                    path.write_text('preserve')
                    with self.assertRaisesRegex(m.Refusal, '^attempt_already_reserved$'):
                        m.run(Path('image.bin'))
                    self.assertEqual(path.read_text(), 'preserve')
                    path.unlink()
            spawn.assert_not_called()

    def test_output_parent_and_dangling_leaf_symlinks_refused(self):
        external = self.root / 'outside'
        external.mkdir()
        (self.root / 'build').symlink_to(external, target_is_directory=True)
        with mock.patch.object(m.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(m.Refusal, '^workspace_symlink$'):
                m.run(Path('image.bin'))
            (self.root / 'build').unlink()
            self.out.mkdir(parents=True)
            for name in m.FILES:
                path = self.out / name
                path.symlink_to(external / 'missing')
                with self.assertRaisesRegex(m.Refusal, '^workspace_symlink$'):
                    m.run(Path('image.bin'))
                path.unlink()
            spawn.assert_not_called()
        self.assertEqual(list(external.iterdir()), [])

    def test_spawn_failure_is_durable_and_sanitized(self):
        with mock.patch.object(m.subprocess, 'Popen', side_effect=OSError('private/path secret')):
            self.assertEqual(m.run(Path('image.bin')), 1)
        row = self.result()
        self.assertFalse(row['controller_started'])
        self.assertEqual(row['supervisor_reason'], 'supervisor_failure')
        self.assertNotIn('private/path', self.stdout.getvalue())
        self.assertNotIn('secret', self.stdout.getvalue())
        self.assertTrue((self.out / 'supervisor-once.json').is_file())

    def test_interruption_stops_owned_child_and_records(self):
        proc = mock.Mock()
        proc.poll.return_value = None
        with mock.patch.object(m.subprocess, 'Popen', return_value=proc), \
                mock.patch.object(m, 'wait_bounded', side_effect=KeyboardInterrupt), \
                mock.patch.object(m, 'stop_child') as stop:
            self.assertEqual(m.run(Path('image.bin')), 1)
            stop.assert_called_once_with(proc)
        self.assertEqual(self.result()['supervisor_reason'], 'supervisor_interrupted')
        self.assertTrue(self.result()['controller_started'])

    def test_expired_outcome_never_becomes_success(self):
        with mock.patch.object(m.subprocess, 'Popen', return_value=mock.Mock()), \
                mock.patch.object(m, 'wait_bounded', return_value=(124, True)):
            self.assertEqual(m.run(Path('image.bin')), 124)
        row = self.result()
        self.assertTrue(row['supervisor_deadline'])
        self.assertEqual(row['supervisor_reason'], 'controller_deadline')

    def test_deadline_termination_failure_preserves_unknown(self):
        with mock.patch.object(m.subprocess, 'Popen', return_value=mock.Mock()), \
                mock.patch.object(m, 'wait_bounded', side_effect=m.DeadlineTerminationFailure), \
                mock.patch.object(m, 'stop_child') as stop:
            self.assertEqual(m.run(Path('image.bin')), 124)
            stop.assert_not_called()
        row = self.result()
        self.assertTrue(row['supervisor_deadline'])
        self.assertIsNone(row['controller_exit'])
        self.assertEqual(row['supervisor_reason'], 'child_termination_unconfirmed')
        self.assertEqual(row['supervisor_exit'], 124)

    def test_sources_changed_before_spawn_remains_consumed(self):
        pins = m.verify_sources()
        with mock.patch.object(m, 'verify_sources', side_effect=[pins, '0' * 64]), \
                mock.patch.object(m.subprocess, 'Popen') as spawn:
            self.assertEqual(m.run(Path('image.bin')), 1)
            spawn.assert_not_called()
        self.assertFalse(self.result()['controller_started'])
        self.assertEqual(self.result()['supervisor_reason'], 'sources_changed_before_spawn')
        self.assertTrue((self.out / 'supervisor-once.json').exists())

    def test_wrong_confirmation_does_not_reserve_or_launch(self):
        with mock.patch.object(m, 'run') as run:
            with self.assertRaisesRegex(m.Refusal, '^confirmation$'):
                m.main(['--image', 'image.bin', '--confirm', 'START-CPU1-J716C-31D'])
            run.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_manifest_tampering_and_missing_closure_fail_before_receipt(self):
        with mock.patch.object(m.subprocess, 'Popen') as spawn:
            path = self.root / 'native/boot/smp31g.py'
            path.write_text('changed')
            with self.assertRaisesRegex(m.Refusal, '^source_digest_mismatch$'):
                m.run(Path('image.bin'))
            self.write_pins()
            self.manifest.write_text('\n'.join(self.manifest.read_text().splitlines()[1:]) + '\n')
            with self.assertRaisesRegex(m.Refusal, '^source_manifest_incomplete$'):
                m.run(Path('image.bin'))
            spawn.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_manifest_path_and_symlink_refusals(self):
        pristine = self.manifest.read_bytes()
        for name in ('../escape', '/absolute', 'native/boot/./smp31g.py'):
            self.manifest.write_text(f'{"0" * 64}  {name}\n')
            with self.assertRaisesRegex(m.Refusal, '^source_manifest_path$'):
                m.verify_sources()
        self.manifest.write_bytes(pristine)
        path = self.root / 'native/boot/smp31g.py'
        target = self.root / 'external.py'
        target.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(target)
        with self.assertRaisesRegex(m.Refusal, '^workspace_symlink$'):
            m.verify_sources()
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
