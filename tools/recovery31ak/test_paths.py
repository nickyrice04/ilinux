#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recovery-like alias fixtures only; never real Recovery/boot/policy calls."""
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
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


render = module('recovery31ak_test_renderer', HERE / 'render.py')
old = module('recovery31ak_frozen_flow_fixture',
             ROOT / 'tools/recovery31aj/test_recovery.py')

# The original synthetic fake is extended with the omitted Recovery deployment
# condition: the native helper refuses any symbolic component in supplied paths.
STRICT = old.FAKE.replace(
    "elif fmt=='%u:%Lp':print('0:'+oct(f.stat().st_mode&511)[2:])\n else:stop()",
    """elif fmt=='%u:%Lp':print('0:'+oct(f.stat().st_mode&511)[2:])
 elif fmt=='%d:%i:%u:%Lp':
  info=f.stat();owner=s.get('work_owner',0);mode=s.get('work_mode',oct(info.st_mode&4095)[2:])
  if str(f)=='.' and s.get('replace_work_at_cwd_check'):
   parent=root/'recovery/System/Volumes/Data/private/tmp'
   work=next(x for x in parent.iterdir() if x.name.startswith('ilinux31ak.'))
   work.rename(work.with_name('retained-owned-directory'))
   work.mkdir();(work/'foreign.keep').write_text('SYNTHETIC FOREIGN CONTENT')
   s['replace_work_at_cwd_check']=False;save()
  print(str(info.st_dev)+':'+str(info.st_ino)+':'+str(owner)+':'+mode)
 else:stop()""")
STRICT = STRICT.replace("if role!='ilinux31aj-reader':stop()\n", """if role!='ilinux31aj-reader':stop()
for option in ('--profile','--validate-snapshot','--baseline','--comparison-key'):
 if option not in a:continue
 path=p(a[a.index(option)+1])
 bad=any(part.is_symlink() for part in (path,*path.parents))
 with (root/'helper-paths.jsonl').open('a') as log:log.write(json.dumps({'option':option,'symbolic_component':bad})+'\\n')
 if bad:stop()
""")
assert STRICT != old.FAKE and "elif fmt=='%d:%i:%u:%Lp'" in STRICT


class RecoveryPaths(unittest.TestCase):
    machine = old.ShellFlowTests.machine
    calls = old.ShellFlowTests.calls

    def setUp(self):
        old.ShellFlowTests.setUp(self)
        self.recovery = self.root / 'recovery'
        self.physical = self.recovery / 'System/Volumes/Data/private'
        (self.physical / 'tmp').mkdir(parents=True)
        (self.recovery / 'private').symlink_to('System/Volumes/Data/private')
        for name in ('id', 'stat', 'hash', 'bputil', 'kmutil'):
            f = self.bin / name
            f.write_text(STRICT)
            f.chmod(0o700)
        helper = self.kit / 'ilinux31aj-reader'
        helper.write_text(STRICT)
        helper.chmod(0o700)
        self.p['files']['helper'].update(bytes=helper.stat().st_size,
                                         sha256=hashlib.sha256(helper.read_bytes()).hexdigest())
        data = render.profile.canonical(self.p)
        (self.kit / 'profile.json').write_bytes(data)
        (self.root / 'profile.json').write_bytes(data)

    def paths(self):
        path = self.root / 'helper-paths.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def run_block(self, operation, frozen=False):
        renderer = render.original if frozen else render
        text = renderer.render(self.p, operation)
        for a, b in ((render.KIT, str(self.kit)), (render.STATE, str(self.state)),
                     (render.LAB, str(self.lab)), (render.ORIGINAL, str(self.original))):
            text = text.replace(a, b)
        for tool in ('id', 'stat', 'bputil', 'kmutil'):
            text = text.replace('/usr/bin/' + tool, str(self.bin / tool))
        begin = text.index('hash_file() {')
        end = text.index('\n', begin)
        text = text[:begin] + 'hash_file() { "' + str(self.bin / 'hash') + '" "$1"; }' + text[end:]
        for tag in ('31aj', '31ak'):
            text = text.replace('/private/tmp/ilinux' + tag + '.',
                                str(self.recovery / ('private/tmp/ilinux' + tag + '.')))
        text = text.replace('/dev/tty', str(self.root / 'tty'))
        for forbidden in ('/usr/bin/bputil', '/usr/bin/kmutil', '/Volumes/', '/dev/tty', ' -d /private/tmp/'):
            self.assertNotIn(forbidden, text)
        return subprocess.run(['/bin/bash', '--noprofile', '--norc'], input=text,
                              text=True, capture_output=True,
                              env=dict(os.environ, FAKE_ROOT=str(self.root)), timeout=20)

    def install(self):
        result = self.run_block('install')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_frozen_31aj_reproduces_capability_refusal_under_system_alias(self):
        result = self.run_block('install', frozen=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('helper capability', result.stderr)
        self.assertTrue(any(row['symbolic_component'] for row in self.paths()))
        self.assertFalse(self.state.exists())
        self.assertEqual(self.calls(), [])

    def test_alias_layout_full_install_and_restore_use_only_physical_helper_paths(self):
        installed = self.install()
        result = self.run_block('restore')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([row['op'] for row in self.calls()], ['candidate', 'ctrr', 'boot021'])
        self.assertTrue(self.paths())
        self.assertFalse(any(row['symbolic_component'] for row in self.paths()))
        self.assertIn('CANDIDATE READBACK VERIFIED', installed.stdout)
        self.assertEqual(list((self.physical / 'tmp').iterdir()), [])

    def test_direct_private_layout_remains_supported(self):
        (self.recovery / 'private').unlink()
        # Turn the alias into a real directory without changing any real /private.
        (self.physical / 'tmp').rmdir()
        (self.recovery / 'private/tmp').mkdir(parents=True)
        self.install()
        self.assertEqual(self.run_block('restore').returncode, 0)
        self.assertEqual([row['op'] for row in self.calls()], ['candidate', 'ctrr', 'boot021'])

    def test_capability_refusal_is_pre_enrollment_not_blind_restore_advice(self):
        self.machine(cap_fail=True)
        result = self.run_block('install')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PRE_ENROLLMENT_STOP', result.stderr)
        self.assertIn('Do not run restore blindly', result.stderr)
        self.assertNotIn('POST_COMMAND_STOP', result.stderr)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.calls(), [])

    def test_restore_missing_baseline_has_specific_preflight_advice(self):
        result = self.run_block('restore')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RESTORE_PREFLIGHT_STOP', result.stderr)
        self.assertIn('Restoration is not confirmed', result.stderr)
        self.assertNotIn('POST_COMMAND_STOP', result.stderr)
        self.assertEqual(self.calls(), [])

    def test_install_command_failure_still_gets_readback_and_post_command_advice(self):
        self.machine(candidate_rc=124)
        result = self.run_block('install')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('POST_COMMAND_STOP', result.stderr)
        self.assertTrue((self.state / 'candidate.json').is_file())
        self.assertEqual([row['op'] for row in self.calls()], ['candidate'])
        self.assertNotEqual(self.run_block('install').returncode, 0)
        self.assertEqual([row['op'] for row in self.calls()], ['candidate'])

    def test_restore_command_failure_still_gets_readback_and_stops(self):
        self.install()
        self.machine(ctrr_rc=130)
        result = self.run_block('restore')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('POST_COMMAND_STOP', result.stderr)
        self.assertTrue((self.state / 'raw-policy.json').is_file())
        self.assertEqual([row['op'] for row in self.calls()], ['candidate', 'ctrr'])

    def test_wrong_new_work_owner_refused_before_helper_and_state(self):
        self.machine(work_owner=1)
        result = self.run_block('install')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('work ownership or mode', result.stderr)
        self.assertEqual(self.paths(), [])
        self.assertEqual(self.calls(), [])
        self.assertFalse(self.state.exists())

    def test_wrong_new_work_mode_refused_before_helper_and_state(self):
        self.machine(work_mode='755')
        result = self.run_block('install')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('work ownership or mode', result.stderr)
        self.assertEqual(self.paths(), [])
        self.assertEqual(self.calls(), [])

    def test_name_replacement_at_held_cwd_check_stops_without_foreign_cleanup(self):
        self.machine(replace_work_at_cwd_check=True)
        result = self.run_block('install')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('entered work identity', result.stderr)
        self.assertEqual(self.calls(), [])
        foreign = list((self.physical / 'tmp').glob('ilinux31ak.*/foreign.keep'))
        self.assertEqual(len(foreign), 1)
        self.assertEqual(foreign[0].read_text(), 'SYNTHETIC FOREIGN CONTENT')
        self.assertEqual(self.paths(), [])

    def test_restore_remains_independent_of_candidate_presence(self):
        self.install()
        (self.kit / 'candidate.macho').unlink()
        result = self.run_block('restore')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_already_restored_does_not_repeat_commands(self):
        self.install()
        self.assertEqual(self.run_block('restore').returncode, 0)
        before = self.calls()
        self.assertEqual(self.run_block('restore').returncode, 0)
        self.assertEqual(self.calls(), before)


class SourceAndRendering(unittest.TestCase):
    def copied(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        for name in render.FROZEN:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        return root

    def test_changed_frozen_dependency_refused_before_compilation(self):
        root = self.copied()
        (root / 'tools/recovery31aj/profile.py').write_text('raise RuntimeError("MUST NOT RUN")')
        with self.assertRaises(ValueError):
            render.load_original(root)

    def test_symbolic_frozen_source_component_refused(self):
        root = self.copied()
        parent = root / 'tools/recovery31aj'
        moved = parent.with_name('original')
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(OSError):
            render.load_original(root)

    def test_both_blocks_parse_and_keep_write_arguments_and_core_guards(self):
        value = old.plan()
        for operation in ('install', 'restore'):
            block = render.render(value, operation)
            result = subprocess.run(['/bin/bash', '-n'], input=block,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for line in render.original.render(value, operation).splitlines():
                if '/usr/bin/kmutil ' in line or '/usr/bin/bputil ' in line:
                    self.assertIn(line.replace('if ', 'if work_binding && ', 1), block)
            for forbidden in ('/bin/rm -rf', '/sbin/reboot', '/usr/sbin/bless', 'bputil -n'):
                self.assertNotIn(forbidden, block)
            for unchanged in ('safe_path "$KIT"', 'safe_path "$STATE"',
                              'recovery-transaction-v2', '--comparison-key "$KEY"',
                              'check_file "$KIT/profile.json"'):
                self.assertIn(unchanged, block)

    def test_html_readonly_boxes_contain_exact_new_blocks_without_script(self):
        class Boxes(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.current = None
                self.boxes = {}
            def handle_starttag(self, tag, attrs):
                self_tag = tag
                if self_tag == 'script':
                    raise AssertionError('script not expected')
                if tag == 'textarea':
                    data = dict(attrs)
                    assert 'readonly' in data and data.get('spellcheck') == 'false'
                    self.current = data['id']
                    self.boxes[self.current] = ''
            def handle_endtag(self, tag):
                if tag == 'textarea':
                    self.current = None
            def handle_data(self, data):
                if self.current is not None:
                    self.boxes[self.current] += data
        parser = Boxes()
        parser.feed(render.page(old.plan()))
        self.assertEqual(set(parser.boxes), {'install-block', 'restore-block'})
        for operation in ('install', 'restore'):
            self.assertEqual(parser.boxes[operation + '-block'], render.render(old.plan(), operation))


if __name__ == '__main__':
    unittest.main(verbosity=2)
