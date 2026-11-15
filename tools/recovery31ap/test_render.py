#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused new renderer controls; inherited shell flow is byte-exact."""
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


render = load('render31ap_tested', Path(__file__).with_name('render.py'))
fixture = load('frozen31aj_plan', ROOT / 'tools/recovery31aj/test_recovery.py')


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.boxes = []

    def handle_starttag(self, tag, attrs):
        if tag == 'textarea':
            self.inside = True
            self.boxes.append('')

    def handle_endtag(self, tag):
        if tag == 'textarea':
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.boxes[-1] += data


class Renderer(unittest.TestCase):
    def setUp(self):
        self.value = fixture.plan()

    def test_only_kit_and_shell_schema_change(self):
        old = render.original.render(self.value)
        new = render.render(self.value)
        back = new.replace(render.KIT, render.original.KIT, 1)
        back = back.replace('ilinux31ap-shell-result-v1', 'ilinux31am-shell-result-v1', 1)
        self.assertEqual(back, old)
        self.assertNotIn('31am-diagnostic', new)
        self.assertIn('31ap-diagnostic', new)
        self.assertEqual(new.count('--preboot-diagnose'), 1)
        self.assertEqual(new.count('--validate-result'), 1)

    def test_rendered_scratch_name_satisfies_frozen_native_contract(self):
        # Read the actual production engine's fixed basename constraints rather
        # than assigning a new prefix merely because this attempt has a new name.
        source = (ROOT / 'tools/boot-object31am-native/preboot.c').read_text()
        predicate = re.search(r'strncmp\(base\+1,"([A-Za-z0-9.]+)",(\d+)\)', source)
        suffix = re.search(r'size_t suffix=strlen\(base\+(\d+)\);if\(suffix<(\d+)\|\|suffix>(\d+)\)', source)
        self.assertIsNotNone(predicate)
        self.assertIsNotNone(suffix)
        template = re.search(r'/([A-Za-z0-9.]+\.XXXXXX)', render.render(self.value)).group(1)
        name = template.replace('XXXXXX', 'ABC123')
        prefix, width = predicate.group(1), int(predicate.group(2))
        start, low, high = map(int, suffix.groups())
        self.assertEqual(width, len(prefix))
        self.assertEqual(start, width + 1)  # base points at the preceding slash.
        self.assertTrue(name.startswith(prefix))
        self.assertTrue(low <= len(name[width:]) <= high)
        self.assertTrue(name[width:].isascii() and name[width:].isalnum())
        self.assertEqual(render.WORK_BLOCK, render.original.WORK_BLOCK)

    def test_exact_one_box_and_new_title(self):
        text = render.page(self.value)
        page = Page()
        page.feed(text)
        self.assertEqual(page.boxes, [render.render(self.value)])
        self.assertIn('<title>31AP typed-policy Preboot check</title>', text)
        self.assertNotIn('<title>31AM', text)
        self.assertNotIn('<script', text)
        self.assertNotIn('--install', page.boxes[0])
        self.assertNotIn('--restore', page.boxes[0])

    def test_shell_passes_bash_syntax(self):
        completed = subprocess.run(['/bin/bash', '-n'], input=render.render(self.value),
                                   text=True, capture_output=True, timeout=5)
        self.assertEqual(completed.returncode, 0)

    def test_bad_anchor_refuses(self):
        for text in ('absent', 'old old'):
            with self.assertRaises(ValueError):
                render.once(text, 'old', 'new')

    def test_unadmitted_renderer_never_executes(self):
        parent = ROOT / 'build/31ap-render-tests'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as folder:
            root = Path(folder)
            path = root / next(iter(render.FROZEN))
            path.parent.mkdir(parents=True)
            path.write_text('raise RuntimeError("MUST_NOT_EXECUTE")\n')
            with self.assertRaises(ValueError):
                render.load_original(root)
            path.unlink()
            path.symlink_to(ROOT / next(iter(render.FROZEN)))
            with self.assertRaises(OSError):
                render.load_original(root)


if __name__ == '__main__':
    unittest.main()
