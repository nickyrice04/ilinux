"""Offline registry-selection and real protocol tests; never open a device."""
import contextlib
import copy
import importlib.util
import io
from pathlib import Path
import plistlib
import stat
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "third_party/m1n1/proxyclient"))
spec = importlib.util.spec_from_file_location("usb_check", HERE / "usb-check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
from m1n1.proxy import M1N1Proxy, UartInterface, UartTimeout


def usb_device(stem="SYNTHETIC", vid=0x1209, pid=0x316d):
    # Synthetic fixtures only: never save a real IORegistry or a device serial.
    return {
        "IOObjectClass": "IOUSBHostDevice", "idVendor": vid, "idProduct": pid,
        "USB Serial Number": "DO-NOT-PRINT-SYNTHETIC",
        "IORegistryEntryChildren": [
            {"IOObjectClass": "IOUSBHostInterface", "bInterfaceNumber": number,
             "bInterfaceClass": 10, "IORegistryEntryChildren": [
                 {"IOObjectClass": "AppleUSBACMData", "IORegistryEntryChildren": [
                     {"IOObjectClass": "IOSerialBSDClient",
                      "IOCalloutDevice": "/dev/cu.usbmodem" + stem + str(number)}]}]}
            for number in (1, 3)]}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.lstat = patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFCHR))
        self.lstat.start()
        self.addCleanup(self.lstat.stop)

    def test_primary_independent_of_filename(self):
        for stem in ("P_0", "SYNTHETIC", "unrelated_ending_"):
            with self.subTest(stem=stem):
                ports = check.registry_ports([usb_device(stem)])
                self.assertEqual(check.select_primary(ports), "/dev/cu.usbmodem" + stem + "1")
                self.assertEqual([p.primary for p in ports], [True, False])

    def test_name_cannot_override_interface(self):
        root = usb_device()
        root["IORegistryEntryChildren"][0]["bInterfaceNumber"] = 3
        ports = check.registry_ports([root])
        with self.assertRaises(ValueError):
            check.select_primary(ports)

    def test_wrong_vendor_or_product_rejected_even_with_old_suffix(self):
        for vid, pid in ((0x1234, 0x316d), (0x1209, 0x9999)):
            with self.subTest(vid=vid, pid=pid), self.assertRaises(ValueError):
                check.select_primary(check.registry_ports([usb_device("P_0", vid, pid)]))

    def test_missing_or_wrong_interface_metadata_rejected(self):
        for key, value in (("bInterfaceNumber", None), ("bInterfaceClass", None),
                           ("bInterfaceNumber", 0), ("bInterfaceNumber", "1"),
                           ("bInterfaceClass", 2)):
            root = usb_device()
            root["IORegistryEntryChildren"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                check.select_primary(check.registry_ports([root]))

    def test_secondary_and_unknown_path_cannot_be_selected(self):
        ports = check.registry_ports([usb_device()])
        for path in (ports[1].path, "/dev/cu.usbmodemOTHER1"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                check.select_primary(ports, path)

    def test_explicit_verified_path_accepted(self):
        ports = check.registry_ports([usb_device()])
        self.assertEqual(check.select_primary(ports, ports[0].path), ports[0].path)

    def test_multiple_primaries_are_ambiguous_even_with_explicit_path(self):
        ports = check.registry_ports([usb_device("ONE"), usb_device("TWO")])
        for request in ("auto", ports[0].path):
            with self.subTest(request=request), self.assertRaises(ValueError):
                check.select_primary(ports, request)

    def test_empty_registry_rejected(self):
        with self.assertRaises(ValueError):
            check.select_primary(check.registry_ports([]))

    def test_duplicate_subtree_deduplicated_and_conflict_rejected(self):
        root = usb_device()
        ports = check.registry_ports([root, copy.deepcopy(root)])
        self.assertEqual(len(ports), 2)
        check.select_primary(ports)
        conflict = copy.deepcopy(root)
        conflict["idProduct"] = 0x9999
        with self.assertRaises(ValueError):
            check.registry_ports([root, conflict])

    def test_sibling_and_nested_device_do_not_inherit_primary_identity(self):
        root = usb_device()
        interface = root["IORegistryEntryChildren"][0]
        orphan = copy.deepcopy(interface["IORegistryEntryChildren"][0])
        nested = {"IOObjectClass": "IOUSBHostDevice", "IORegistryEntryChildren": [interface]}
        root["IORegistryEntryChildren"] = [orphan, nested]
        with self.assertRaises(ValueError):
            check.select_primary(check.registry_ports([root]))

    def test_stale_symlink_and_regular_file_rejected(self):
        ports = check.registry_ports([usb_device()])
        for mode in (stat.S_IFREG, stat.S_IFLNK):
            with patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=mode)):
                with self.assertRaises(ValueError):
                    check.select_primary(ports)
        with patch.object(Path, "lstat", side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                check.select_primary(ports)

    def test_ioreg_is_read_only_captured_and_bounded(self):
        raw = plistlib.dumps([usb_device()])
        with patch.object(check.sys, "platform", "darwin"), \
                patch.object(check.subprocess, "run", return_value=SimpleNamespace(stdout=raw)) as run:
            self.assertEqual(len(check.discover()), 2)
        run.assert_called_once_with(
            ["/usr/sbin/ioreg", "-a", "-l", "-p", "IOService", "-r", "-c", "IOUSBHostDevice"],
            capture_output=True, check=True, timeout=15)

    def run_main(self, args, roots=None, discovery_error=None, handshake_error=None):
        out, err = io.StringIO(), io.StringIO()
        ports = check.registry_ports([usb_device()] if roots is None else roots)
        with patch.object(check, "discover", return_value=ports, side_effect=discovery_error), \
                patch.object(check, "handshake", side_effect=handshake_error) as handshake, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = check.main(args)
        text = out.getvalue() + err.getvalue()
        self.assertNotIn("SYNTHETIC", text)
        self.assertNotIn("/dev/cu.", text)
        return status, text, handshake

    def test_discovery_never_handshakes_and_redacts_paths(self):
        status, text, handshake = self.run_main([])
        self.assertEqual(status, 0)
        self.assertIn("Discovery only", text)
        handshake.assert_not_called()

    def test_connect_performs_exactly_one_handshake(self):
        status, text, handshake = self.run_main(["--connect"])
        self.assertEqual(status, 0)
        handshake.assert_called_once_with("/dev/cu.usbmodemSYNTHETIC1")
        self.assertIn("Handshake start UTC:", text)
        self.assertIn("Handshake end UTC:", text)
        self.assertIn("Handshake elapsed:", text)

    def test_discovery_failures_do_not_handshake(self):
        for roots in ([], [usb_device("ONE"), usb_device("TWO")], [usb_device(pid=1)]):
            status, text, handshake = self.run_main(["--connect"], roots=roots)
            self.assertEqual(status, 2)
            handshake.assert_not_called()
        status, text, handshake = self.run_main(
            ["--connect"], discovery_error=ValueError("SYNTHETIC private diagnostic"))
        self.assertEqual(status, 2)
        handshake.assert_not_called()

    def test_handshake_failure_is_not_retried_or_leaked(self):
        status, text, handshake = self.run_main(
            ["--connect"], handshake_error=TimeoutError("SYNTHETIC private diagnostic"))
        self.assertEqual(status, 1)
        self.assertIn("Handshake FAILED: TimeoutError", text)
        handshake.assert_called_once()


class FakeSerial:
    def __init__(self, *_):
        self.sent = []
        self.pending = b""
        self.closed = False

    def flushOutput(self):
        pass

    def flushInput(self):
        pass

    def write(self, packet):
        self.sent.append(packet)
        opcode = struct.unpack("<Q", packet[4:12])[0]
        reply = struct.pack("<IiQqQ", UartInterface.REQ_PROXY, 0, opcode, 0, 0)
        self.pending = reply + struct.pack("<I", UartInterface.checksum(self, reply))

    def read(self, size):
        result, self.pending = self.pending[:size], self.pending[size:]
        return result

    def close(self):
        self.closed = True


class HandshakeTests(unittest.TestCase):
    def test_only_proxy_nop_is_sent(self):
        transport = FakeSerial()
        with patch("m1n1.proxy.Serial", return_value=transport):
            check.handshake("/dev/fake")
        self.assertTrue(transport.closed)
        self.assertEqual(len(transport.sent), 1)
        packet = transport.sent[0]
        self.assertEqual(struct.unpack("<I", packet[:4])[0], UartInterface.REQ_PROXY)
        self.assertEqual(struct.unpack("<7Q", packet[4:60]), (M1N1Proxy.P_NOP, 0, 0, 0, 0, 0, 0))

    def test_timeout_closes_port(self):
        transport = FakeSerial()
        transport.read = lambda _: b""
        with patch("m1n1.proxy.Serial", return_value=transport):
            with self.assertRaises(UartTimeout):
                check.handshake("/dev/fake")
        self.assertTrue(transport.closed)

    def test_initialization_failure_closes_port(self):
        transport = FakeSerial()
        with patch("m1n1.proxy.Serial", return_value=transport), \
                patch("m1n1.proxy.UartInterface", side_effect=OSError):
            with self.assertRaises(OSError):
                check.handshake("/dev/fake")
        self.assertTrue(transport.closed)
        self.assertEqual(transport.sent, [])

    def test_deadline_is_armed_and_port_closed_on_alarm(self):
        transport = FakeSerial()
        transport.read = lambda _: (_ for _ in ()).throw(TimeoutError())
        with patch("m1n1.proxy.Serial", return_value=transport), \
                patch.object(check.signal, "alarm") as alarm:
            with self.assertRaises(TimeoutError):
                check.handshake("/dev/fake")
        self.assertEqual([call.args for call in alarm.call_args_list], [(10,), (0,)])
        self.assertTrue(transport.closed)
        self.assertEqual(len(transport.sent), 1)


if __name__ == "__main__":
    unittest.main()
