import importlib.util
import unittest
from pathlib import Path

s = importlib.util.spec_from_file_location('renderer', Path(__file__).with_name('renderer.py'))
r = importlib.util.module_from_spec(s)
s.loader.exec_module(r)


class RendererTests(unittest.TestCase):
    def test_single(self):
        self.assertEqual(r.policy({0}, {0})['lp_num_threads'], 0)

    def test_two(self):
        self.assertEqual(r.policy({0, 1}, {0, 1})['lp_num_threads'], 1)

    def test_cap(self):
        self.assertEqual(r.policy(set(range(18)), set(range(18)))['lp_num_threads'], 4)

    def test_affinity_limits(self):
        self.assertEqual(r.policy(set(range(18)), {8})['lp_num_threads'], 0)

    def test_offline_cpus(self):
        self.assertEqual(r.policy({0, 2}, {0, 1, 2, 3})['available_cpus'], [0, 2])

    def test_empty(self):
        with self.assertRaises(ValueError):
            r.policy({0}, {1})

    def test_parse(self):
        self.assertEqual(r.parse_cpus('0-3,6,8-9\n'), {0, 1, 2, 3, 6, 8, 9})

    def test_parse_bad(self):
        for text in ('', '-1', '1-0', '0-999999999', '0,,1', '0-1-2'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                r.parse_cpus(text)


if __name__ == '__main__':
    unittest.main()
