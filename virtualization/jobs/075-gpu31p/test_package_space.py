#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Boundary tests for the original offline disk-space decision."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("package_space", Path(__file__).with_name("package-space.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SpaceTests(unittest.TestCase):
    def test_new_package_and_exact_boundary(self):
        packages = [{"name": "test", "version": "2", "installed_size": 100}]
        required = 200 + m.HEADROOM
        self.assertEqual(m.requirements(packages, {}, required)["result"], "PACKAGE_SPACE_PASS")
        self.assertEqual(m.requirements(packages, {}, required - 1)["result"], "PACKAGE_SPACE_REFUSED")

    def test_shrinking_package_never_funds_another(self):
        packages = [{"name": "a", "version": "2", "installed_size": 100},
                    {"name": "b", "version": "2", "installed_size": 200}]
        result = m.requirements(packages, {"a": ("1", 1000), "b": ("1", 100)}, 1000000000)
        self.assertEqual(result["positive_delta_bytes"], 100)
        self.assertEqual(result["required_bytes"], 100 + 200 + m.HEADROOM)

    def test_unchanged_packages_need_no_replacement_space(self):
        p = [{"name": "test", "version": "2", "installed_size": 100}]
        result = m.requirements(p, {"test": ("2", 100)}, m.HEADROOM)
        self.assertEqual(result["required_bytes"], m.HEADROOM)

    def test_identical_version_size_mismatch(self):
        with self.assertRaises(ValueError):
            m.requirements([{"name": "test", "version": "2", "installed_size": 100}],
                           {"test": ("2", 99)}, 1000000000)

    def test_duplicate_package_refused(self):
        p = {"name": "test", "version": "2", "installed_size": 100}
        with self.assertRaises(ValueError):
            m.requirements([p, p], {}, 1000000000)

    def test_sizes_and_space_are_strict(self):
        for value in (True, 0, -1, 2**64, "123junk"):
            with self.assertRaises(ValueError):
                m.size(value)
        with self.assertRaises(ValueError):
            m.requirements([], {}, True)

    def test_database_fields(self):
        data = m.fields("%NAME%\ntest\n\n%SIZE%\n100\n")
        self.assertEqual(m.one(data, "NAME"), "test")
        with self.assertRaises(ValueError):
            m.fields("%NAME%\na\n\n%NAME%\nb\n")
        with self.assertRaises(ValueError):
            m.one(data, "VERSION")


if __name__ == "__main__":
    unittest.main(verbosity=2)
