#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check complete paste boundaries and independent rollback; no shell execution."""
import copy
import html.parser
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('render31ar_tested', Path(__file__).with_name('render.py'))
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class Boxes(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.boxes = []
        self.active = None

    def handle_starttag(self, tag, attrs):
        if tag == 'textarea':
            self.active = ''

    def handle_data(self, data):
        if self.active is not None:
            self.active += data

    def handle_endtag(self, tag):
        if tag == 'textarea' and self.active is not None:
            self.boxes.append(self.active)
            self.active = None


class Renderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'native/boot/attempt31ar-package/profile.json'
        cls.value = render.profile.load(path.read_bytes())

    def test_both_complete_blocks_parse_without_execution(self):
        for operation in ('install', 'restore'):
            with self.subTest(operation=operation):
                text = render.render(self.value, operation)
                result = subprocess.run(['/bin/bash', '-n'], input=text, text=True,
                                        capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(text.startswith('(\nset +x\n'))
                self.assertTrue(text.endswith(')\n'))

    def test_combined_and_independent_pages_have_exact_whole_boxes(self):
        for operation, expected in ((None, ('install', 'restore')),
                                    ('install', ('install',)), ('restore', ('restore',))):
            with self.subTest(operation=operation):
                parser = Boxes()
                parser.feed(render.page(self.value, operation))
                self.assertEqual(parser.boxes,
                                 [render.render(self.value, item) for item in expected])

    def test_restore_runs_without_candidate_path_or_copy(self):
        text = render.render(self.value, 'restore')
        self.assertNotIn('$KIT/candidate.macho', text)
        self.assertNotIn('./candidate.macho', text)
        self.assertIn('--transaction restore', text)
        self.assertIn('m1n1-boot021.bin', text)

    def test_controller_is_only_owner_of_mount_and_boot_commands(self):
        for operation in ('install', 'restore'):
            text = render.render(self.value, operation)
            for token in ('/usr/bin/kmutil', '/usr/bin/bputil', '/sbin/mount_apfs',
                          '/sbin/umount', '/sbin/reboot', 'shutdown -', 'rm -rf'):
                self.assertNotIn(token, text)
            self.assertNotIn('trap cleanup EXIT', text)
            self.assertIn('Preserve scratch', text)

    def test_canonical_held_cwd_and_exact_hashes_precede_controller(self):
        for operation in ('install', 'restore'):
            text = render.render(self.value, operation)
            start = text.index('--transaction ' + operation)
            for token in ('ilinux31ar.XXXXXX', 'cd -P "$WORK"', 'work_binding()',
                          '/usr/bin/cmp -s ./expected-profile.json ./profile.json',
                          self.value['files']['helper']['sha256']):
                self.assertLess(text.index(token), start)
            self.assertIn('test "$(/bin/pwd -P)" = "$WORK"', text)

    def test_finite_output_validation_precedes_cleanup_and_failure(self):
        for operation in ('install', 'restore'):
            text = render.render(self.value, operation)
            validate = text.index('--validate-transaction-result')
            self.assertLess(validate, text.index('test "$HELPER_EXIT" = 0'))
            self.assertLess(validate, text.index('/bin/rm -f'))
            self.assertNotIn('/bin/cat ./result.json', text)

    def test_recovery_hash_fallback_trace_off_and_fixed_deadline(self):
        text = render.render(self.value, 'install')
        self.assertIn('/sbin/sha256 -q', text)
        self.assertIn('/usr/bin/shasum -a 256', text)
        self.assertIn('/usr/bin/openssl dgst -sha256', text)
        self.assertIn('export LC_ALL=C', text)
        self.assertEqual(self.value['native_deadline_ms'], 90000)
        self.assertNotIn(r"printf '%s\\n'", text)

    def test_invalid_operation_or_changed_profile_refused(self):
        for operation in ('', 'boot', 'install; reboot'):
            with self.assertRaises(ValueError):
                render.render(self.value, operation)
        changed = copy.deepcopy(self.value)
        changed['publication_authorizes_writes'] = True
        with self.assertRaises(ValueError):
            render.render(changed, 'install')


if __name__ == '__main__':
    unittest.main(verbosity=2)
