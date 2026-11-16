#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""New namespace/profile/whole-box controls; no boot/controller/backend/socket."""
import copy
import html.parser
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location('tested31au_' + name,
                                                Path(__file__).with_name(name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


package, profile, render = module('package'), module('profile'), module('render')


class Boxes(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.boxes, self.active = [], None

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


class Render(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.as_module, _, cls.old, cls.retained = package.frozen()
        cls.profile = profile.derive(cls.old[3][profile.SOURCE])
        cls.renderer = render.derive(cls.old[3][render.SOURCE],
                                    cls.old[3][profile.SOURCE], cls.profile,
                                    cls.as_module, ROOT)
        # Explicit synthetic naming control, never a production delivery record.
        cls.value = copy.deepcopy(cls.old[5])
        cls.value['schema'] = cls.profile.SCHEMA
        cls.value['initial_payload'] = 'BOOT021'
        cls.value['files']['helper']['name'] = 'ilinux31au-reader'

    def test_new_profile_admits_boot021_initial_and_rejects_old_transition(self):
        self.profile.validate(self.value)
        old = copy.deepcopy(self.value)
        old['initial_payload'] = '31AF'
        with self.assertRaises(ValueError):
            self.profile.validate(old)
        old = copy.deepcopy(self.value)
        old['files']['helper']['name'] = 'ilinux31aj-reader'
        with self.assertRaises(ValueError):
            self.profile.validate(old)

    def test_profile_and_renderer_reject_changed_frozen_source(self):
        for adapter in (profile, render):
            raw = self.old[3][adapter.SOURCE] + b' changed'
            with self.assertRaises(ValueError):
                if adapter is profile:
                    profile.derive(raw)
                else:
                    render.derive(raw, self.old[3][profile.SOURCE], self.profile,
                                  self.as_module, ROOT)

    def test_only_new_names_and_same_corrected_hash_bootstrap(self):
        for operation in ('install', 'restore'):
            text = self.renderer.render(self.value, operation)
            expected = self.as_module.render(self.value, operation,
                                             self.renderer.original)
            self.assertEqual(text, expected.replace('31AS', '31AU').replace('31as', '31au'))
            self.assertIn('ilinux31au.XXXXXX', text)
            self.assertIn('/31au-kit', text)
            self.assertIn('H="$WORK/ilinux31au-reader"', text)
            self.assertIn('ilinux31au-reader" 125168', text)
            self.assertNotIn('31ar', text)
            self.assertNotIn('31AR', text)
            self.assertNotIn('ilinux31aj-reader', text)
            self.assertNotIn('/usr/bin/cmp', text)
            self.assertNotIn('/usr/bin/awk', text)
            self.assertIn('ilinux31au-reader', text)
            self.assertIn('/bin/chmod 700 ./ilinux31au-reader', text)
            self.assertIn('--transaction ' + operation, text)
            self.assertIn('--validate-transaction-result', text)
            self.assertEqual(subprocess.run(['/bin/bash', '-n'], input=text,
                                            text=True, capture_output=True).returncode, 0)

    def test_restore_does_not_require_candidate(self):
        text = self.renderer.render(self.value, 'restore')
        # Public profile embeds the candidate pin but no candidate operation.
        lines = [line for line in text.splitlines() if line.startswith(('check_file ',
                 'work_binding && /bin/cp', 'work_binding && /bin/rm'))]
        self.assertNotIn('candidate.macho', '\n'.join(lines))

    def test_required_tools_preflight_retained_and_no_clipboard_exercise(self):
        text = self.renderer.render(self.value, 'install')
        for tool in self.as_module.REQUIRED:
            self.assertIn(tool, text)
        self.assertLess(text.index('for REQUIRED31AU'), text.index('WORK_RAW='))
        self.assertNotIn('pbcopy', text)
        self.assertNotIn('clipboard', text)
        self.assertNotIn('/sbin/reboot', text)

    def test_whole_combined_and_independent_boxes_are_exact(self):
        for operation, expected in ((None, ('install', 'restore')),
                                    ('install', ('install',)), ('restore', ('restore',))):
            parser = Boxes()
            page = self.renderer.page(self.value, operation)
            parser.feed(page)
            self.assertEqual(parser.boxes,
                             [self.renderer.render(self.value, item) for item in expected])
            self.assertIn('31AU guarded diagnostic transaction', page)
            self.assertIn('Macintosh HD', page)

    def test_unknown_operation_and_changed_profile_refuse(self):
        with self.assertRaises(ValueError):
            self.renderer.render(self.value, 'retry')
        broken = copy.deepcopy(self.value)
        broken['publication_authorizes_writes'] = True
        with self.assertRaises(ValueError):
            self.renderer.render(broken, 'install')


if __name__ == '__main__':
    unittest.main(verbosity=2)
