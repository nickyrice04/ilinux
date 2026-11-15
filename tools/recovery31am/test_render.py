#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused shell controls with synthetic helpers and workspace directories.

The fake validator models the display boundary; it does not qualify the native
20-key parser or any hardware mount. The native suite owns those checks.
"""
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = load('tested31am_renderer', ROOT / 'tools/recovery31am/render.py')
fixture = load('frozen31aj_plan_fixture', ROOT / 'tools/recovery31aj/test_recovery.py')

FAKE = r'''#!/usr/bin/env python3
import hashlib,json,os,pathlib,sys
p=pathlib.Path;root=p(os.environ['FAKE_ROOT']);a=sys.argv[1:];role=p(sys.argv[0]).name
s=json.loads((root/'machine.json').read_text())
def stop(code=2):sys.exit(code)
if role=='id':print(0);stop(0)
if role=='hash':print(hashlib.sha256(p(a[0]).read_bytes()).hexdigest());stop(0)
if role=='stat':
 info=p(a[-1]).stat();fmt=a[-2]
 if fmt=='%z':print(info.st_size)
 elif fmt=='%d:%i:%u:%Lp':print(str(info.st_dev)+':'+str(info.st_ino)+':0:'+oct(info.st_mode&4095)[2:])
 else:stop()
 stop(0)
if role!='ilinux31aj-reader':stop()
with (root/'helper-calls.jsonl').open('a') as f:f.write(json.dumps(a)+'\n')
def record(mode):
 value=dict(schema='ilinux31am-preboot-result-v1',scope='SYNTHETIC_CONTROL',status='REFUSED',
  stage='CLI',reason='ARGUMENTS',initial_state='UNOBSERVED',mount_attempted=False,
  mount_created=False,mount_read_only_verified=False,mount_state_uncertain=False,
  mount_exit=None,unmount_exit=None,cleanup='NOT_NEEDED',diagnostic=None,
  preboot_write_requested=False,boot_object_installed=False,security_settings_changed=False,
  native_ready=False,identifiers_returned=False,policy_values_returned=False)
 if mode in ('existing','owned','cleanup_failed'):
  value.update(initial_state='MOUNTED_VALID' if mode=='existing' else 'UNMOUNTED_EMPTY')
 if mode in ('owned','cleanup_failed'):
  value.update(mount_attempted=True,mount_created=True,mount_read_only_verified=mode=='owned',
   mount_state_uncertain=mode=='cleanup_failed',mount_exit=0,
   unmount_exit=0 if mode=='owned' else None,cleanup='UNMOUNTED' if mode=='owned' else 'REFUSED')
 return value
for option in ('--profile','--validate-result'):
 if option in a:
  f=p(a[a.index(option)+1])
  if any(x.is_symlink() for x in (f,*f.parents)):stop()
if a and a[0]=='--preboot-diagnose':
 if a[1::2]!=['--target-volume','--original-volume','--profile','--scratch']:stop()
 work=p(a[a.index('--scratch')+1])
 if work!=p.cwd() or any(x.is_symlink() for x in (work,*work.parents)):stop()
 mode=s.get('output','refusal')
 if mode in ('owned','cleanup_failed','signal'):
  child=work/'preboot';child.mkdir(mode=0o700)
  if mode=='owned':child.rmdir()
  else:(child/'fixture.keep').write_text('SYNTHETIC FOREIGN MOUNT CONTENT')
 if s.get('stderr_secret'):print('PRIVATE_SENTINEL_MUST_NOT_DISPLAY',file=sys.stderr)
 if mode=='signal':os.kill(os.getpid(),9)
 if mode=='raw':print('PRIVATE_SENTINEL_MUST_NOT_DISPLAY');stop()
 if mode=='oversized':print('PRIVATE_SENTINEL_MUST_NOT_DISPLAY'*1000);stop()
 if mode=='symbolic':
  p('diagnostic.json').unlink();p('diagnostic.json').symlink_to(root/'private-source');stop()
 value=record(mode)
 if mode=='extra':value['private']='PRIVATE_SENTINEL_MUST_NOT_DISPLAY'
 print(json.dumps(value));stop(s.get('child_rc',2))
if a and a[0]=='--validate-result':
 try:
  data=p(a[1]).read_bytes();value=json.loads(data)
  valid=len(data)<=16384 and value in [record(m) for m in ('refusal','existing','owned','cleanup_failed')]
 except (OSError,ValueError):valid=False
 if valid:print(json.dumps(value,sort_keys=True));stop(0)
 print(json.dumps(record('refusal'),sort_keys=True));stop()
stop()
'''


class Shell(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'build/31am-render-tests'
        base.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='fixture-', dir=base)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.lab, self.original = self.root / 'lab', self.root / 'original'
        for item in (self.lab, self.original):
            (item / 'System/Library/CoreServices').mkdir(parents=True)
        self.kit = self.root / 'data/Users/Shared/iLinuxBoot/31am-diagnostic'
        self.kit.mkdir(parents=True)
        self.state = self.kit.with_name('31aj-state')
        self.state.mkdir()
        (self.state / 'keep').write_text('SYNTHETIC RETAINED STATE')
        self.recovery = self.root / 'recovery'
        self.physical = self.recovery / 'System/Volumes/Data/private'
        (self.physical / 'tmp').mkdir(parents=True)
        (self.recovery / 'private').symlink_to('System/Volumes/Data/private')
        self.bin = self.root / 'fakebin'
        self.bin.mkdir()
        for name in ('id', 'stat', 'hash'):
            path = self.bin / name
            path.write_text(FAKE)
            path.chmod(0o700)
        helper = self.kit / 'ilinux31aj-reader'
        helper.write_text(FAKE)
        helper.chmod(0o700)
        self.value = fixture.plan()
        self.value['files']['helper'].update(bytes=helper.stat().st_size,
            sha256=hashlib.sha256(helper.read_bytes()).hexdigest())
        (self.kit / 'profile.json').write_bytes(render.profile.canonical(self.value))
        (self.root / 'machine.json').write_text('{}')

    def machine(self, **changes):
        path = self.root / 'machine.json'
        value = json.loads(path.read_text())
        value.update(changes)
        path.write_text(json.dumps(value))

    def calls(self):
        path = self.root / 'helper-calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def block(self):
        text = render.render(self.value)
        for name, path in ((render.KIT, self.kit), (render.LAB, self.lab),
                           (render.ORIGINAL, self.original)):
            text = text.replace(name, str(path))
        for name in ('id', 'stat'):
            text = text.replace('/usr/bin/' + name, str(self.bin / name))
        begin = text.index('hash_file() {')
        end = text.index('\n', begin)
        text = text[:begin] + 'hash_file() { "' + str(self.bin / 'hash') + '" "$1"; }' + text[end:]
        text = text.replace('/private/tmp/ilinux31am.',
                            str(self.recovery / 'private/tmp/ilinux31am.'))
        for forbidden in ('/usr/bin/bputil', '/usr/bin/kmutil', '/sbin/mount_apfs',
                          '/sbin/umount', '/Volumes/', 'rm -rf'):
            self.assertNotIn(forbidden, text)
        result = subprocess.run(['/bin/bash', '--noprofile', '--norc'], input=text,
            text=True, capture_output=True, timeout=20,
            env=dict(os.environ, FAKE_ROOT=str(self.root)))
        self.assertEqual(result.stderr, '')
        self.assertNotIn('PRIVATE_SENTINEL', result.stdout)
        self.assertNotIn(str(self.root), result.stdout)
        self.assertEqual((self.state / 'keep').read_text(), 'SYNTHETIC RETAINED STATE')
        self.assertEqual(sorted(p.name for p in self.kit.iterdir()),
                         ['ilinux31aj-reader', 'profile.json'])
        return result

    @staticmethod
    def rows(result):
        return [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]

    def test_new_cli_receives_canonical_held_scratch_once(self):
        result = self.block()
        self.assertEqual(result.returncode, 2)
        self.assertEqual([c[0] for c in self.calls()], ['--preboot-diagnose', '--validate-result'])
        args = self.calls()[0]
        self.assertEqual(args[1::2], ['--target-volume', '--original-volume', '--profile', '--scratch'])
        self.assertNotIn('/recovery/private/', args[-1])
        rows = self.rows(result)
        self.assertEqual(rows[0]['schema'], 'ilinux31am-shell-result-v1')
        self.assertNotIn('read_only', rows[0])
        self.assertNotIn('writes_authorized', rows[0])
        self.assertNotIn('filesystem_writes_requested', rows[0])
        self.assertIs(rows[0]['preboot_write_requested'], False)
        self.assertEqual(rows[-1]['stage'], 'DIAGNOSTIC_CAPTURED')
        self.assertEqual(list((self.physical / 'tmp').iterdir()), [])

    def test_existing_mount_model_is_displayed_without_shell_cleanup_action(self):
        self.machine(output='existing')
        row = self.rows(self.block())[1]
        self.assertEqual(row['initial_state'], 'MOUNTED_VALID')
        self.assertFalse(row['mount_attempted'])
        self.assertEqual(row['cleanup'], 'NOT_NEEDED')

    def test_owned_mount_model_cleanup_is_reported_before_scratch_removal(self):
        self.machine(output='owned')
        row = self.rows(self.block())[1]
        self.assertTrue(row['mount_attempted'])
        self.assertTrue(row['mount_created'])
        self.assertTrue(row['mount_read_only_verified'])
        self.assertEqual(row['cleanup'], 'UNMOUNTED')
        self.assertEqual(list((self.physical / 'tmp').iterdir()), [])

    def test_uncertain_native_child_is_retained_without_recursive_cleanup(self):
        self.machine(output='cleanup_failed')
        result = self.block()
        row = self.rows(result)[1]
        self.assertTrue(row['mount_state_uncertain'])
        self.assertFalse(row['mount_read_only_verified'])
        self.assertEqual(row['cleanup'], 'REFUSED')
        work, = list((self.physical / 'tmp').iterdir())
        self.assertEqual((work / 'preboot/fixture.keep').read_text(), 'SYNTHETIC FOREIGN MOUNT CONTENT')
        self.assertEqual([p.name for p in work.iterdir()], ['preboot'])
        self.assertIn('check the explicit read-only verification field', result.stdout)

    def test_unexpected_exit_stays_stop_after_safe_display(self):
        self.machine(child_rc=7)
        rows = self.rows(self.block())
        self.assertEqual(rows[0]['helper_exit'], 7)
        self.assertEqual(rows[1]['schema'], 'ilinux31am-preboot-result-v1')
        self.assertEqual(rows[-1]['stage'], 'HELPER_EXIT')

    def test_interrupted_helper_retains_child_and_never_claims_verified_cleanup(self):
        self.machine(output='signal', stderr_secret=True)
        result = self.block()
        rows = self.rows(result)
        self.assertEqual(rows[0]['helper_exit'], 137)
        self.assertEqual(rows[-1]['stage'], 'OUTPUT_MISSING')
        work, = list((self.physical / 'tmp').iterdir())
        self.assertTrue((work / 'preboot/fixture.keep').is_file())
        self.assertIn('read-only verification may be incomplete', result.stdout)

    def test_rejected_private_extra_or_oversized_capture_is_never_echoed(self):
        for output in ('raw', 'extra', 'oversized'):
            with self.subTest(output=output):
                self.machine(output=output, stderr_secret=True)
                self.assertEqual(self.rows(self.block())[-1]['stage'], 'VALIDATOR_FAILED')

    def test_symbolic_capture_is_not_validated(self):
        self.machine(output='symbolic')
        target = self.root / 'private-source'
        target.write_text('PRIVATE_SENTINEL_MUST_NOT_DISPLAY')
        self.assertEqual(self.rows(self.block())[-1]['stage'], 'OUTPUT_MISSING')
        self.assertEqual([c[0] for c in self.calls()], ['--preboot-diagnose'])
        self.assertEqual(target.read_text(), 'PRIVATE_SENTINEL_MUST_NOT_DISPLAY')


class SourceAndPage(unittest.TestCase):
    def test_guard_projection_is_exact_and_shell_contains_no_mount_command(self):
        self.assertEqual(render.WORK_BLOCK.replace('ilinux31am.XXXXXX', 'ilinux31al.XXXXXX'),
                         render.original.WORK_BLOCK)
        text = render.render(fixture.plan())
        self.assertEqual(text.count('--preboot-diagnose'), 1)
        self.assertEqual(text.count('--validate-result'), 1)
        for value in ('--diagnose-snapshot', '--validate-diagnostic', '/sbin/mount_apfs',
                      '/sbin/umount', 'rm -rf', '31aj-state', '--snapshot-value',
                      'comparison.key', '/usr/bin/kmutil', '/usr/bin/bputil'):
            self.assertNotIn(value, text)
        self.assertIn('31am-diagnostic', text)
        self.assertIn('read-only verification may be incomplete', text)
        syntax = subprocess.run(['/bin/bash', '-n'], input=text, text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def copied(self):
        base = ROOT / 'build/31am-render-tests'
        base.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='source-', dir=base)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        names = set(render.FROZEN) | set(render.original.FROZEN) | set(render.original.original.FROZEN)
        for name in names:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        return root

    def test_changed_frozen_or_transitive_source_never_executes(self):
        for name in ('tools/recovery31al/render.py', 'tools/recovery31aj/profile.py'):
            with self.subTest(name=name):
                root = self.copied()
                marker = root / 'MUST_NOT_EXECUTE'
                (root / name).write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n')
                with self.assertRaises(ValueError):
                    render.load_original(root)
                self.assertFalse(marker.exists())

    def test_symbolic_frozen_source_is_rejected(self):
        root = self.copied()
        source = root / 'tools/recovery31al'
        moved = source.with_name('real31al')
        source.rename(moved)
        source.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(OSError):
            render.load_original(root)

    def test_single_inert_box_contains_exact_block_and_conditional_mount_explanation(self):
        class Boxes(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.boxes, self.tags, self.inside = [], [], False
            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
                if tag == 'textarea':
                    self.boxes.append([dict(attrs), ''])
                    self.inside = True
            def handle_endtag(self, tag):
                if tag == 'textarea':
                    self.inside = False
            def handle_data(self, data):
                if self.inside:
                    self.boxes[-1][1] += data
        value = fixture.plan()
        page = render.page(value)
        parsed = Boxes()
        parsed.feed(page)
        self.assertEqual(len(parsed.boxes), 1)
        self.assertIn('readonly', parsed.boxes[0][0])
        self.assertEqual(parsed.boxes[0][1], render.render(value))
        self.assertIn('explicit authorization', page)
        self.assertIn('conditional read-only', page)
        self.assertIn('No Preboot filesystem writes', page)
        for tag in ('script', 'form', 'iframe', 'img'):
            self.assertNotIn(tag, parsed.tags)


if __name__ == '__main__':
    unittest.main(verbosity=2)
