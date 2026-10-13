"""VM-only integration test against the pinned upstream M1N1Proxy serializer."""
import os
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_launcher import LauncherTests, FakeInterface, FakeUtils, prepared
sys.path.insert(0, str(Path(os.environ["M1N1_SOURCE"]) / "proxyclient"))
from m1n1.proxy import M1N1Proxy


class Heap:
    def malloc(self, size): return 0x8000
    def free(self, addr): pass


class Wire(FakeInterface):
    def __init__(self):
        super().__init__(prepared())
        self.opcodes = []

    def proxyreq(self, request, **kwargs):
        opcode, *args = struct.unpack("<7Q", request)
        self.opcodes.append(opcode)
        replies = {M1N1Proxy.P_GET_CHIPID: 0x6050, M1N1Proxy.P_GET_BASE: 0x1000,
                   M1N1Proxy.P_READ64: 0x9000}
        allowed = {M1N1Proxy.P_NOP, M1N1Proxy.P_SMP_IS_ALIVE,
                   M1N1Proxy.P_KBOOT_SET_CHOSEN, M1N1Proxy.P_KBOOT_SET_INITRD,
                   M1N1Proxy.P_KBOOT_PREPARE_DT, M1N1Proxy.P_DC_CVAU,
                   M1N1Proxy.P_IC_IVAU, M1N1Proxy.P_KBOOT_BOOT} | set(replies)
        if opcode not in allowed:
            raise AssertionError("unexpected opcode: " + hex(opcode))
        return struct.pack("<QqQ", opcode, 0, replies.get(opcode, 0))


class ProtocolTest(unittest.TestCase):
    def test_real_proxy_has_no_smp_start_or_cpufreq_init(self):
        fixture = LauncherTests()
        fixture.setUp()
        fixture.iface = Wire()
        fixture.proxy = M1N1Proxy(fixture.iface)
        fixture.proxy.heap = Heap()
        fixture.run_launch(FakeUtils)
        ops = fixture.iface.opcodes
        self.assertEqual(ops.count(M1N1Proxy.P_KBOOT_BOOT), 1)
        self.assertEqual(ops[-1], M1N1Proxy.P_KBOOT_BOOT)
        self.assertEqual(ops.count(M1N1Proxy.P_SMP_IS_ALIVE), 64)
        self.assertNotIn(M1N1Proxy.P_SMP_START_SECONDARIES, ops)
        self.assertNotIn(M1N1Proxy.P_CPUFREQ_INIT, ops)


if __name__ == "__main__":
    unittest.main(defaultTest="ProtocolTest")
