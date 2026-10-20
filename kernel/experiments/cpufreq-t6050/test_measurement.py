#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from measurement import snapshot


class SnapshotTests(unittest.TestCase):
    def test_missing_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = snapshot(root)
            self.assertEqual(list(root.iterdir()), [])
            self.assertIsNone(result["thermal_zones"])
            self.assertIsNone(result["energy_joules"])
            self.assertIsNone(result["power_watts"])
            self.assertEqual(result["policies"], {})

    def test_requested_rate_is_labeled(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            policy = root / "sys/devices/system/cpu/cpufreq/policy0"
            policy.mkdir(parents=True)
            p = policy / "scaling_cur_freq"
            p.write_text("1344000\n")
            result = snapshot(root)
            self.assertEqual(result["policies"]["policy0"]["scaling_cur_freq"], "1344000")
            self.assertIn("not measured", result["frequency_semantics"])
            self.assertEqual(p.read_text(), "1344000\n")


if __name__ == "__main__":
    unittest.main()
