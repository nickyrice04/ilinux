"""Reserved GPIO geometry, malformed metadata, and pre-upload failure tests."""
import contextlib
import io
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gpio_guard
import launch
from fdt import properties
from test_launcher import FakeADT, FakeUtils, FakeInterface, FakeProxy, prepared


class GPIOGuardTests(unittest.TestCase):
    def test_observed_adt(self):
        gpio_guard.check_adt(FakeADT())

    def test_order_independent(self):
        adt = FakeADT()
        adt.gpio['no-restore-gpio-pins'] = struct.pack('<5I', *sorted(gpio_guard.PINS))
        gpio_guard.check_adt(adt)

    def test_missing_node(self):
        with self.assertRaises(ValueError):
            gpio_guard.check_adt({})

    def test_missing_fields(self):
        for key in FakeADT().gpio:
            with self.subTest(key=key), self.assertRaises(ValueError):
                adt = FakeADT()
                del adt.gpio[key]
                gpio_guard.check_adt(adt)

    def test_wrong_geometry(self):
        for key, value in [('compatible', 'gpio,t8101'), ('compatible', ['gpio,t8103']),
                           ('#gpio-pins', 220), ('#gpio-pins', True),
                           ('#gpio-int-groups', 8)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                adt = FakeADT()
                adt.gpio[key] = value
                gpio_guard.check_adt(adt)

    def test_bad_pin_lists(self):
        for raw in [b'', bytes(19), bytes(21), [5, 6, 7, 112, 141],
                    struct.pack('>5I', 5, 6, 7, 112, 141),
                    struct.pack('<5I', 5, 5, 7, 112, 141),
                    struct.pack('<5I', 5, 6, 8, 112, 141),
                    struct.pack('<5I', 5, 6, 7, 112, 221)]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                adt = FakeADT()
                adt.gpio['no-restore-gpio-pins'] = raw
                gpio_guard.check_adt(adt)

    def test_dt(self):
        gpio_guard.check_tree(properties(prepared()))

    def test_dt_tampering(self):
        tree = properties(prepared())
        for key in tree[gpio_guard.PATH]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                changed = properties(prepared())
                changed[gpio_guard.PATH][key] = b''
                gpio_guard.check_tree(changed)
        with self.assertRaises(ValueError):
            gpio_guard.check_tree({})

    def test_disabled_dt(self):
        tree = properties(prepared())
        tree[gpio_guard.PATH]['status'] = b'disabled\0'
        with self.assertRaises(ValueError):
            gpio_guard.check_tree(tree)

    def test_mismatch_stops_before_payload_or_dapf(self):
        proxy, iface = FakeProxy(), FakeInterface(prepared())

        def factory(p):
            utils = FakeUtils(p)
            utils.adt.gpio['no-restore-gpio-pins'] = bytes(20)
            return utils

        manifest = {'m1n1_version_marker': 'version', 'm1n1_version_offset': 0x100}
        with contextlib.redirect_stdout(io.StringIO()), patch.object(launch.dapf_guard, 'prepare') as dapf:
            with self.assertRaisesRegex(ValueError, 'GPIO'):
                launch.launch_session(iface, proxy, factory, manifest, {})
        dapf.assert_not_called()
        self.assertEqual(iface.writes, [])
        self.assertEqual(proxy.boots, [])


if __name__ == '__main__':
    unittest.main()
