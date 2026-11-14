#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic workspace-only shell/path/privacy tests; no real Recovery calls."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


render = module('recovery31al_test_renderer', HERE / 'render.py')
old = module('recovery31al_original_fixture', ROOT / 'tools/recovery31aj/test_recovery.py')

FAKE = r'''#!/usr/bin/env python3
import hashlib,json,os,pathlib,sys
p=pathlib.Path;root=p(os.environ['FAKE_ROOT']);a=sys.argv[1:];role=p(sys.argv[0]).name
s=json.loads((root/'machine.json').read_text())
def stop(code=2):sys.exit(code)
def save(): (root/'machine.json').write_text(json.dumps(s))
if role=='id':print(s.get('uid',0));stop(0)
if role=='hash':print(hashlib.sha256(p(a[0]).read_bytes()).hexdigest());stop(0)
if role=='stat':
 f=p(a[-1]);info=f.stat();fmt=a[-2]
 if fmt=='%z':print(info.st_size)
 elif fmt=='%d:%i:%u:%Lp':
  if str(f)=='.' and s.get('replace_work'):
   work=p.cwd();work.rename(work.with_name('retained-owned-directory'))
   work.mkdir();(work/'foreign.keep').write_text('SYNTHETIC FOREIGN CONTENT')
   s['replace_work']=False;save()
  print(str(info.st_dev)+':'+str(info.st_ino)+':'+str(s.get('work_owner',0))+':'+s.get('work_mode',oct(info.st_mode&4095)[2:]))
 else:stop()
 stop(0)
if role!='ilinux31aj-reader':stop()
with (root/'helper-calls.jsonl').open('a') as log:log.write(json.dumps(a)+'\n')
for option in ('--profile','--validate-diagnostic'):
 if option in a:
  path=p(a[a.index(option)+1])
  if any(part.is_symlink() for part in (path,*path.parents)):stop()
def record(passed=False):
 return dict(schema='ilinux31al-snapshot-diagnostic-v1',scope='SYNTHETIC_CONTROL',
  status='INITIAL_ADMISSION_PASS' if passed else 'REFUSED',
  stage='INITIAL_ADMISSION' if passed else 'PROFILE',failure_kind='NONE' if passed else 'FORMAT',
  reason='NONE' if passed else 'PROFILE_BINDING',command='NONE',command_exit=None,stdout_bytes=0,
  snapshot_collected=passed,initial_admission_valid=passed,read_only=True,writes_authorized=False,
  native_ready=False,identifiers_returned=False,policy_values_returned=False)
if a[0]=='--diagnose-snapshot':
 if a[1::2]!=['--target-volume','--original-volume','--profile']:stop()
 if s.get('stderr_secret'):print('PRIVATE_SENTINEL_DO_NOT_DISPLAY',file=sys.stderr)
 mode=s.get('output','refusal')
 if mode=='signal':os.kill(os.getpid(),9)
 if mode=='missing':p('diagnostic.json').unlink();stop(2)
 if mode=='symbolic':
  p('diagnostic.json').unlink();p('diagnostic.json').symlink_to(root/'private-source');stop(2)
 if mode=='empty':stop(s.get('child_rc',2))
 if mode=='raw':print('PRIVATE_SENTINEL_DO_NOT_DISPLAY');stop(2)
 if mode=='oversized':print('PRIVATE_SENTINEL_DO_NOT_DISPLAY'*400);stop(2)
 value=record(mode=='pass')
 if mode=='extra':value['raw_private']='PRIVATE_SENTINEL_DO_NOT_DISPLAY'
 print(json.dumps(value));stop(s.get('child_rc',0 if mode=='pass' else 2))
if a[0]=='--validate-diagnostic':
 valid=False
 try:
  data=p(a[1]).read_bytes()
  if len(data)<=8192:
   value=json.loads(data);valid=value==record(False) or value==record(True)
 except (OSError,ValueError):pass
 if valid:print(json.dumps(value,sort_keys=True));stop(0)
 value=record();value.update(stage='DIAGNOSTIC_VALIDATION',reason='DIAGNOSTIC_FORMAT')
 print(json.dumps(value,sort_keys=True));stop()
stop()
'''


class ShellDiagnostics(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.lab = self.root / 'lab'
        self.original = self.root / 'original'
        for item in (self.lab, self.original):
            (item / 'System/Library/CoreServices').mkdir(parents=True)
        self.kit = self.root / 'data/Users/Shared/iLinuxBoot/31al-diagnostic'
        self.kit.mkdir(parents=True)
        self.state = self.kit.with_name('31aj-state')
        self.recovery = self.root / 'recovery'
        self.physical = self.recovery / 'System/Volumes/Data/private'
        (self.physical / 'tmp').mkdir(parents=True)
        (self.recovery / 'private').symlink_to('System/Volumes/Data/private')
        self.bin = self.root / 'fakebin'
        self.bin.mkdir()
        for name in ('id', 'stat', 'hash'):
            item = self.bin / name
            item.write_text(FAKE)
            item.chmod(0o700)
        helper = self.kit / 'ilinux31aj-reader'
        helper.write_text(FAKE)
        helper.chmod(0o700)
        self.p = old.plan()
        self.p['files']['helper'].update(bytes=helper.stat().st_size,
                                         sha256=hashlib.sha256(helper.read_bytes()).hexdigest())
        (self.kit / 'profile.json').write_bytes(render.profile.canonical(self.p))
        (self.kit / 'profile.json').chmod(0o600)
        self.machine()

    def machine(self, **changes):
        path = self.root / 'machine.json'
        value = json.loads(path.read_text()) if path.exists() else {}
        value.update(changes)
        path.write_text(json.dumps(value))

    def calls(self):
        path = self.root / 'helper-calls.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def run_block(self, adjust=None):
        text = render.render(self.p)
        for source, destination in ((render.KIT, self.kit), (render.LAB, self.lab),
                                    (render.ORIGINAL, self.original)):
            text = text.replace(source, str(destination))
        for name in ('id', 'stat'):
            text = text.replace('/usr/bin/' + name, str(self.bin / name))
        begin = text.index('hash_file() {')
        end = text.index('\n', begin)
        text = text[:begin] + 'hash_file() { "' + str(self.bin / 'hash') + '" "$1"; }' + text[end:]
        text = text.replace('/private/tmp/ilinux31al.',
                            str(self.recovery / 'private/tmp/ilinux31al.'))
        if adjust:
            text = adjust(text)
        for forbidden in ('/usr/bin/bputil', '/usr/bin/kmutil', '/Volumes/',
                          '/dev/tty', ' -d /private/tmp/'):
            self.assertNotIn(forbidden, text)
        result = subprocess.run(['/bin/bash', '--noprofile', '--norc'], input=text,
                                capture_output=True, text=True,
                                env=dict(os.environ, FAKE_ROOT=str(self.root)), timeout=20)
        self.assertFalse(self.state.exists())
        self.assertEqual(sorted(path.name for path in self.kit.iterdir()),
                         ['ilinux31aj-reader', 'profile.json'])
        self.assertNotIn('PRIVATE_SENTINEL', result.stdout + result.stderr)
        self.assertNotIn(str(self.root), result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def rows(self, result):
        return [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]

    def test_alias_refusal_is_visible_validated_and_removed_after_display(self):
        result = self.run_block()
        self.assertEqual(result.returncode, 2, result.stdout)
        rows = self.rows(result)
        self.assertEqual(rows[0]['stage'], 'HELPER_EXIT')
        self.assertEqual(rows[0]['helper_exit'], 2)
        self.assertEqual(rows[1]['schema'], 'ilinux31al-snapshot-diagnostic-v1')
        self.assertEqual(rows[1]['reason'], 'PROFILE_BINDING')
        self.assertEqual(rows[2]['stage'], 'DIAGNOSTIC_CAPTURED')
        self.assertEqual([row[0] for row in self.calls()],
                         ['--diagnose-snapshot', '--validate-diagnostic'])
        self.assertEqual(list((self.physical / 'tmp').iterdir()), [])

    def test_passing_admission_still_authorizes_no_install_or_native_boot(self):
        self.machine(output='pass')
        result = self.run_block()
        self.assertEqual(result.returncode, 0, result.stdout)
        native = self.rows(result)[1]
        self.assertEqual(native['status'], 'INITIAL_ADMISSION_PASS')
        self.assertIs(native['native_ready'], False)
        self.assertIs(native['writes_authorized'], False)
        self.assertIn('not permission to install or boot', result.stdout)

    def test_direct_private_layout(self):
        (self.recovery / 'private').unlink()
        (self.recovery / 'private/tmp').mkdir(parents=True)
        self.assertEqual(self.run_block().returncode, 2)
        self.assertEqual(len(self.calls()), 2)
        self.assertEqual(list((self.recovery / 'private/tmp').iterdir()), [])

    def test_unexpected_child_exit_retained_after_validated_record(self):
        self.machine(child_rc=7)
        result = self.run_block()
        rows = self.rows(result)
        self.assertEqual(rows[0]['helper_exit'], 7)
        self.assertEqual(rows[1]['reason'], 'PROFILE_BINDING')
        self.assertEqual(rows[-1]['stage'], 'HELPER_EXIT')
        self.assertNotIn('DIAGNOSTIC_CAPTURED', result.stdout)

    def test_no_output_or_missing_capture_has_own_stage(self):
        for output in ('empty', 'missing'):
            with self.subTest(output=output):
                self.machine(output=output)
                result = self.run_block()
                self.assertEqual(self.rows(result)[-1]['stage'], 'OUTPUT_MISSING')
                self.assertEqual(result.returncode, 2)

    def test_child_signal_reports_only_bounded_status_without_shell_path(self):
        self.machine(output='signal')
        result = self.run_block()
        rows = self.rows(result)
        self.assertEqual(rows[0]['stage'], 'HELPER_EXIT')
        self.assertEqual(rows[0]['helper_exit'], 137)
        self.assertEqual(rows[-1]['stage'], 'OUTPUT_MISSING')

    def test_symbolic_capture_refused_without_reading_target(self):
        self.machine(output='symbolic')
        target = self.root / 'private-source'
        target.write_text('PRIVATE_SENTINEL_DO_NOT_DISPLAY')
        result = self.run_block()
        self.assertEqual(self.rows(result)[-1]['stage'], 'OUTPUT_MISSING')
        self.assertEqual(target.read_text(), 'PRIVATE_SENTINEL_DO_NOT_DISPLAY')
        self.assertEqual([call[0] for call in self.calls()], ['--diagnose-snapshot'])

    def test_raw_extra_field_and_oversized_capture_never_display_private_input(self):
        for output in ('raw', 'extra', 'oversized'):
            with self.subTest(output=output):
                self.machine(output=output, stderr_secret=True)
                result = self.run_block()
                self.assertEqual(self.rows(result)[-1]['stage'], 'VALIDATOR_FAILED')
                self.assertNotIn('DIAGNOSTIC_CAPTURED', result.stdout)

    def test_redirection_failure_has_own_stage_and_never_runs_helper(self):
        result = self.run_block(lambda text: text.replace(
            'exec 3> ./diagnostic.json', 'exec 3> ./absent/diagnostic.json'))
        self.assertEqual(self.rows(result)[-1]['stage'], 'OUTPUT_OPEN')
        self.assertEqual(self.calls(), [])

    def test_existing_capture_is_not_overwritten(self):
        def inject(text):
            return text.replace('SHELL_STAGE=OUTPUT_OPEN\nset -C',
                                "printf '%s' 'EXISTING' > ./diagnostic.json\nSHELL_STAGE=OUTPUT_OPEN\nset -C")
        result = self.run_block(inject)
        self.assertEqual(self.rows(result)[-1]['stage'], 'OUTPUT_OPEN')
        self.assertEqual(self.calls(), [])

    def test_work_owner_and_mode_refused_before_helper(self):
        for change in ({'work_owner': 1}, {'work_owner': 0, 'work_mode': '755'}):
            with self.subTest(change=change):
                self.machine(**change)
                result = self.run_block()
                self.assertEqual(self.rows(result)[-1]['stage'], 'WORK_BINDING')
                self.assertEqual(self.calls(), [])

    def test_replaced_work_name_cannot_clean_foreign_directory(self):
        self.machine(replace_work=True)
        result = self.run_block()
        self.assertEqual(self.rows(result)[-1]['stage'], 'WORK_BINDING')
        self.assertEqual(self.calls(), [])
        foreign = list((self.physical / 'tmp').glob('ilinux31al.*/foreign.keep'))
        self.assertEqual(len(foreign), 1)
        self.assertEqual(foreign[0].read_text(), 'SYNTHETIC FOREIGN CONTENT')

    def test_helper_or_profile_tamper_refused_before_execution(self):
        for name in ('ilinux31aj-reader', 'profile.json'):
            with self.subTest(name=name):
                path = self.kit / name
                data = path.read_bytes()
                path.write_bytes(data + b'CHANGED')
                result = self.run_block()
                self.assertEqual(self.rows(result)[-1]['stage'], 'INPUT_BINDING')
                self.assertEqual(self.calls(), [])
                path.write_bytes(data)

    def test_nonroot_and_symbolic_kit_refused_before_helper(self):
        self.machine(uid=501)
        self.assertEqual(self.rows(self.run_block())[-1]['stage'], 'INPUT_BINDING')
        self.machine(uid=0)
        real = self.kit.with_name('real-kit')
        self.kit.rename(real)
        self.kit.symlink_to(real, target_is_directory=True)
        self.assertEqual(self.rows(self.run_block())[-1]['stage'], 'INPUT_BINDING')
        self.assertEqual(self.calls(), [])


class SourceAndPage(unittest.TestCase):
    def test_only_diagnostic_modes_and_no_persistent_transaction_or_boot_commands(self):
        text = render.render(old.plan())
        for forbidden in ('configure-boot', '/usr/bin/bputil', '/usr/bin/kmutil',
                          '31aj-state', 'comparison.key', '--snapshot ',
                          '--generate-comparison-key', '--snapshot-value',
                          '--target-group-private', 'candidate.macho"',
                          'm1n1-boot021.bin"', '/bin/mkdir', '/bin/mv', '/bin/rm -rf'):
            self.assertNotIn(forbidden, text)
        self.assertEqual(text.count('--diagnose-snapshot'), 1)
        self.assertEqual(text.count('--validate-diagnostic'), 1)
        self.assertLess(text.index('--validate-diagnostic'), text.index('SAFE DIAGNOSTIC'))
        syntax = subprocess.run(['/bin/bash', '-n'], input=text, capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def copied(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        for name in (*render.FROZEN, *render.original.FROZEN):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        return root

    def test_changed_frozen_renderer_refused_before_compilation(self):
        root = self.copied()
        (root / 'tools/recovery31ak/render.py').write_text('raise RuntimeError("MUST NOT RUN")')
        with self.assertRaises(ValueError):
            render.load_original(root)

    def test_symbolic_frozen_renderer_component_refused(self):
        root = self.copied()
        directory = root / 'tools/recovery31ak'
        moved = directory.with_name('real31ak')
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(OSError):
            render.load_original(root)

    def test_frozen_transitive_dependency_still_verified(self):
        root = self.copied()
        (root / 'tools/recovery31aj/profile.py').write_text('raise RuntimeError("MUST NOT RUN")')
        with self.assertRaises(ValueError):
            render.load_original(root)

    def test_single_inert_readonly_textarea_exactly_contains_block(self):
        class Boxes(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.boxes = []
                self.in_box = False
                self.tags = []
            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
                if tag == 'textarea':
                    self.boxes.append([dict(attrs), ''])
                    self.in_box = True
            def handle_data(self, value):
                if self.in_box:
                    self.boxes[-1][1] += value
            def handle_endtag(self, tag):
                if tag == 'textarea':
                    self.in_box = False
        value = old.plan()
        parser = Boxes()
        parser.feed(render.page(value))
        self.assertEqual(len(parser.boxes), 1)
        attrs, text = parser.boxes[0]
        self.assertIn('readonly', attrs)
        self.assertEqual(attrs['spellcheck'], 'false')
        self.assertEqual(text, render.render(value))
        for tag in ('script', 'form', 'iframe', 'img'):
            self.assertNotIn(tag, parser.tags)


if __name__ == '__main__':
    unittest.main()
