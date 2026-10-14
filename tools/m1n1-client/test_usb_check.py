"""Offline identity and real protocol tests; never open a device."""
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "third_party/m1n1/proxyclient"))
from test_usb_identity import check, DiscoveryTests
from m1n1.proxy import M1N1Proxy, UartInterface, UartTimeout


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
