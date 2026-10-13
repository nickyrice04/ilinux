"""Validate the actual serialized handshake with a fake serial transport."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "third_party/m1n1/proxyclient"))
spec = importlib.util.spec_from_file_location("usb_check", HERE / "usb-check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
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


if __name__ == "__main__":
    unittest.main()
