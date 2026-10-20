#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "weather", Path(__file__).with_name("disable_weather.py"))
weather = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weather)


class WeatherConfig(unittest.TestCase):
    def test_installed_five_section_layout_and_other_settings_survive(self):
        cfg = {"version": 1, "idle": {"lock": 300}, "dock": {"pinned": ["foot"]},
               "plugins": [], "bar": {"position": "top", "layout": {
                   "left": [{"id": "omarchy.menu"}],
                   "centerBegin": [{"id": "omarchy.indicators"}],
                   "center": [{"id": "omarchy.clock", "format": "HH:mm"}],
                   "centerEnd": [{"id": "omarchy.elsewhen"},
                                 {"id": "omarchy.weather"},
                                 {"id": "omarchy.system-update"}],
                   "right": [{"id": "omarchy.audio"}]}}}
        result = weather.without_weather(cfg)
        expected = [{"id": "omarchy.elsewhen"}, {"id": "omarchy.system-update"}]
        self.assertEqual(result["bar"]["layout"]["centerEnd"], expected)
        self.assertEqual(len(cfg["bar"]["layout"]["centerEnd"]), 3)
        restored = weather.without_weather(cfg)
        restored["bar"]["layout"]["centerEnd"] = cfg["bar"]["layout"]["centerEnd"]
        self.assertEqual(restored, cfg)
        self.assertEqual(weather.without_weather(result), result)

    def test_invalid_schema_refused(self):
        for cfg in (None, {}, {"version": 2}, {"version": 1, "bar": []},
                    {"version": 1, "bar": {"layout": {"left": "wrong"}}},
                    {"version": 1, "bar": {"layout": {"left": [{}]}}}):
            with self.subTest(cfg=cfg), self.assertRaises(ValueError):
                weather.without_weather(cfg)


if __name__ == "__main__":
    unittest.main()
