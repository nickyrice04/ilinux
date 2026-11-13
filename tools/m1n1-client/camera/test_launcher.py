#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Output boundary tests only; never build, launch or open capture hardware."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('camera_builder', Path(__file__).with_name('build_recorder.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BoundaryTests(unittest.TestCase):
    def test_symlink_parent_refused_without_touching_destination(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve(); outside = root / 'outside'; outside.mkdir()
            (root / 'build').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError): builder.private_directory(root, ('build', 'media'))
            self.assertEqual(list(outside.iterdir()), [])

    def test_traversal_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for part in ('..', '.', '', '/tmp', 'build/escape'):
                with self.assertRaises(ValueError): builder.private_directory(Path(d), (part,))

    def test_existing_media_not_modified(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            directory = builder.private_directory(root, ('build', 'camera-capture'))
            clip = directory / 'prior.mov'; clip.write_bytes(b'prior evidence')
            self.assertEqual(builder.private_directory(root, ('build', 'camera-capture')), directory)
            self.assertEqual(clip.read_bytes(), b'prior evidence')


if __name__ == '__main__': unittest.main(verbosity=2)
