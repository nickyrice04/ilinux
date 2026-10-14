"""Offline regressions: no imports of upstream code and no physical devices."""
import contextlib
import io
import json
from pathlib import Path
import struct
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch
from fdt import properties, check_stage_b


def fdt(nodes):
    names = b""
    body = b""

    def word(n):
        return struct.pack(">I", n)

    def pad(b):
        return b + b"\0" * (-len(b) % 4)

    def add(name, props, children):
        nonlocal names, body
        body += word(1) + pad(name.encode() + b"\0")
        for key, val in props.items():
            body += word(3) + word(len(val)) + word(len(names)) + pad(val)
            names += key.encode() + b"\0"
        for child in children:
            add(*child)
        body += word(2)

    add("", {"compatible": b"apple,j716c\0apple,t6050\0"}, nodes)
    body += word(9)
    # 16-byte empty reservation block precedes the structure.
    return struct.pack(">10I", 0xD00DFEED, 56 + len(body) + len(names), 56,
                       56 + len(body), 40, 17, 16, 0, len(names), len(body)) + b"\0" * 16 + body + names


def prepared(cpu_count=1, storage=False, framebuffer=True, bootargs=None):
    children = [("nvme@1", {"compatible": b"apple,t6050-nvme-ans2\0", "status": b"okay\0" if storage else b"disabled\0"}, [])]
    children += [("perf@" + str(i), {"compatible": b"apple,t8112-cluster-cpufreq\0", "status": b"disabled\0"}, []) for i in range(3)]
    nodes = [("soc", {}, children), ("cpus", {}, [("cpu@" + str(i), {}, []) for i in range(cpu_count)])]
    frame = [("framebuffer", {"compatible": b"simple-framebuffer\0"}, [])] if framebuffer else []
    nodes.append(("chosen", {"bootargs": ((bootargs or launch.BOOTARGS) + "\0").encode()}, frame))
    return fdt(nodes)


class FakeInterface:
    def __init__(self, tree):
        self.tree, self.writes, self.marker = tree, [], b"version\0"

    def readmem(self, addr, size):
        return self.marker if addr == 0x1100 else self.tree[:size]

    def writemem(self, addr, data):
        self.writes.append((addr, data))


class FakeProxy:
    def __init__(self):
        self.alive, self.chip, self.dt_result, self.boots = -1, 0x6050, 0, []
        self.calls = []

    def nop(self): pass
    def get_chipid(self): return self.chip
    def get_base(self): return 0x1000
    def smp_is_alive(self, cpu): return cpu == self.alive
    def kboot_set_chosen(self, name, value): self.calls.append((name, value))
    def kboot_set_initrd(self, addr, size): self.calls.append((addr, size))
    def kboot_prepare_dt(self, addr): return self.dt_result
    def read64(self, addr): return 0x9000
    def dc_cvau(self, addr, size): pass
    def ic_ivau(self, addr, size): pass
    def kboot_boot(self, addr): self.boots.append(addr)
    # No SMP-start, cpufreq-init, PMU or shell method exists; any call fails.


class FakeUtils:
    def __init__(self, proxy):
        self.adt = SimpleNamespace(compatible=["J716cAP"])
        self.ba = SimpleNamespace(video=SimpleNamespace(base=1, width=1, height=1))
        self.next = 0x200000

    def memalign(self, alignment, size):
        self.next = (self.next + alignment - 1) & -alignment
        value = self.next
        self.next += size
        return value

    def msr(self, reg, value):
        assert (reg, value) == ("DAIF", 0xC0)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.proxy = FakeProxy()
        self.iface = FakeInterface(prepared())
        self.manifest = {"m1n1_version_marker": "version", "m1n1_version_offset": 0x100,
                         "m1n1_dt_pointer_offset": 0x200}
        image = bytearray(64)
        struct.pack_into("<QQ", image, 8, 0, 4096)
        image[56:60] = b"ARM\x64"
        self.files = {"Image": bytes(image), "t6050-j716c-stage-b.dtb": prepared(),
                      "initramfs-stage-b.cpio.gz": b"initrd"}

    def run_launch(self, factory=FakeUtils):
        with contextlib.redirect_stdout(io.StringIO()):
            launch.launch_session(self.iface, self.proxy, factory, self.manifest, self.files)

    def reject(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.run_launch()
        self.assertFalse(self.proxy.boots)

    def test_single_core_sequence(self):
        self.run_launch()
        self.assertEqual(self.proxy.boots, [0x200000])
        self.assertEqual(len(self.iface.writes), 3)

    def test_nonzero_image_offset(self):
        image = bytearray(self.files["Image"])
        struct.pack_into("<Q", image, 8, 0x80000)
        self.files["Image"] = bytes(image)
        self.run_launch()
        self.assertEqual(self.proxy.boots, [0x280000])

    def test_wrong_chip_before_writes(self):
        self.proxy.chip = 0x8103
        self.reject("chip")
        self.assertFalse(self.iface.writes)

    def test_wrong_m1n1_before_writes(self):
        self.iface.marker = b"wrong\0"
        self.reject("packaged build")
        self.assertFalse(self.iface.writes)

    def test_existing_secondary_before_writes(self):
        self.proxy.alive = 31
        self.reject("secondary")
        self.assertFalse(self.iface.writes)

    def test_wrong_board(self):
        for compatible in (["J714cAP"], [], "prefix-J716cAP-suffix"):
            def wrong(p):
                u = FakeUtils(p)
                u.adt.compatible = compatible
                return u
            with self.subTest(compatible=compatible), self.assertRaisesRegex(ValueError, "board"):
                self.run_launch(wrong)
            self.assertFalse(self.iface.writes)

    def test_prepare_failure(self):
        self.proxy.dt_result = -1
        self.reject("preparation")

    def test_two_prepared_cpus(self):
        self.iface.tree = prepared(cpu_count=2)
        self.reject("exactly one CPU")

    def test_enabled_storage(self):
        self.iface.tree = prepared(storage=True)
        self.reject("storage")

    def test_missing_framebuffer(self):
        self.iface.tree = prepared(framebuffer=False)
        self.reject("framebuffer")

    def test_unexpected_bootargs(self):
        self.iface.tree = prepared(bootargs=launch.BOOTARGS + " root=/dev/nvme0n1")
        self.reject("appended bootargs")

    def test_m1n1_workaround_append(self):
        self.iface.tree = prepared(bootargs=launch.BOOTARGS + " idle=nop arm64.nowfxt")
        self.run_launch()
        self.assertEqual(len(self.proxy.boots), 1)

    def test_bad_prepared_header(self):
        self.iface.tree = b"\x00" * 8
        self.reject("DT size")

    def test_offline_does_not_connect(self):
        with patch.object(launch, "verify_package", return_value=(self.manifest, self.files)), \
             patch.object(launch.usb_identity, "discover", side_effect=AssertionError("discovery ran")), \
             patch.object(launch, "connect_and_launch", side_effect=AssertionError("USB opened")), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launch.main(["--package", "/fake"]), 0)

    def test_launch_requires_explicit_gate(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            launch.main(["--package", "/fake", "--launch"])

    def test_corruption_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, info = next(iter(json.loads((launch.HERE / "package-manifest.json").read_text())["files"].items()))
            p = root / first
            p.write_bytes(b"x" * info["size"])
            with self.assertRaisesRegex(ValueError, "checksum"):
                launch.verify_package(root)
            p.unlink()
            p.symlink_to(root / "elsewhere")
            with self.assertRaisesRegex(ValueError, "missing file"):
                launch.verify_package(root)

    def test_truncated_fdt_is_rejected(self):
        blob = prepared()
        for length in (0, 12, 39, len(blob) - 1):
            with self.subTest(length=length), self.assertRaises(ValueError):
                properties(blob[:length])


class ControllerTests(unittest.TestCase):
    """Exercise identity/pin gates and transport ownership with fake modules."""

    def setUp(self):
        self.port = launch.usb_identity.Port("/dev/cu.usbmodemSYNTHETIC1", 0x1209, 0x316d, 1, 10)
        self.transport = SimpleNamespace(closed=False)
        self.opens = []

        def close():
            self.transport.closed = True

        def serial(device, baud):
            self.opens.append((device, baud))
            return self.transport

        self.transport.close = close
        class Interface:
            DEFAULT_BAUD_RATE = 115200

            def __init__(iface, device):
                iface.dev = device

        self.proxy_module = SimpleNamespace(Serial=serial, UartInterface=Interface,
                                            M1N1Proxy=lambda iface: object())
        modules = {"m1n1": SimpleNamespace(), "m1n1.proxy": self.proxy_module,
                   "m1n1.proxyutils": SimpleNamespace(ProxyUtils=object)}
        patches = [
            patch.dict(sys.modules, modules),
            patch.object(launch.subprocess, "check_output", side_effect=[launch.M1N1_COMMIT, ""]),
            patch.object(launch.usb_identity, "discover", return_value=[self.port]),
            patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFCHR)),
            patch.object(launch.signal, "signal", return_value="old-handler"),
            patch.object(launch.signal, "alarm"),
            patch.object(launch, "launch_session"),
        ]
        self.mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)
        (_, self.git, self.discovery, self.lstat, self.signal, self.alarm, self.session) = self.mocks

    def connect(self, requested="auto"):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            launch.connect_and_launch(requested, Path("/fake-client"), {}, {})
        self.assertNotIn("SYNTHETIC", output.getvalue())

    def test_auto_selects_non_suffix_primary_and_closes(self):
        self.connect()
        self.assertEqual(self.opens, [(self.port.path, 115200)])
        self.assertTrue(self.transport.closed)
        self.session.assert_called_once()
        self.assertEqual([call.args for call in self.alarm.call_args_list], [(180,), (0,)])
        self.signal.assert_called_with(launch.signal.SIGALRM, "old-handler")

    def test_explicit_verified_primary_works(self):
        self.connect(self.port.path)
        self.session.assert_called_once()

    def test_wrong_explicit_port_stops_before_open(self):
        with self.assertRaisesRegex(ValueError, "USB identity"):
            self.connect("/dev/cu.usbmodemSYNTHETIC3")
        self.assertEqual(self.opens, [])
        self.session.assert_not_called()

    def test_missing_primary_stops_before_open(self):
        self.discovery.return_value = []
        with self.assertRaisesRegex(ValueError, "no port opened"):
            self.connect()
        self.assertEqual(self.opens, [])

    def test_two_primaries_stop_before_open(self):
        self.discovery.return_value = [self.port, self.port._replace(path="/dev/cu.usbmodemOTHER1")]
        with self.assertRaisesRegex(ValueError, "no port opened"):
            self.connect()
        self.assertEqual(self.opens, [])

    def test_registry_failure_redacts_identifiers(self):
        self.discovery.side_effect = OSError("SYNTHETIC private data")
        with self.assertRaises(ValueError) as error:
            self.connect()
        self.assertNotIn("SYNTHETIC", str(error.exception))
        self.assertEqual(self.opens, [])

    def test_wrong_pin_stops_before_discovery(self):
        self.git.side_effect = ["wrong-pin", ""]
        with self.assertRaisesRegex(ValueError, "clean pinned"):
            self.connect()
        self.discovery.assert_not_called()
        self.assertEqual(self.opens, [])

    def test_dirty_client_stops_before_discovery(self):
        self.git.side_effect = [launch.M1N1_COMMIT, " M tracked.py"]
        with self.assertRaisesRegex(ValueError, "clean pinned"):
            self.connect()
        self.discovery.assert_not_called()
        self.assertEqual(self.opens, [])

    def test_interface_init_failure_closes_and_redacts(self):
        with patch.object(self.proxy_module.UartInterface, "__init__",
                          side_effect=OSError("SYNTHETIC private callout")):
            with self.assertRaises(RuntimeError) as error:
                self.connect()
        self.assertNotIn("SYNTHETIC", str(error.exception))
        self.assertTrue(self.transport.closed)
        self.session.assert_not_called()

    def test_preflight_failure_closes_without_retry(self):
        self.session.side_effect = ValueError("target mismatch")
        with self.assertRaisesRegex(ValueError, "target mismatch"):
            self.connect()
        self.assertTrue(self.transport.closed)
        self.assertEqual(len(self.opens), 1)
        self.session.assert_called_once()

    def test_alarm_closes_without_retry(self):
        def deadline(*_):
            handler = self.signal.call_args_list[0].args[1]
            handler()
        self.session.side_effect = deadline
        with self.assertRaisesRegex(RuntimeError, "TimeoutError"):
            self.connect()
        self.assertTrue(self.transport.closed)
        self.assertEqual(len(self.opens), 1)
        self.alarm.assert_called_with(0)

    def test_interruption_closes_transport(self):
        self.session.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.connect()
        self.assertTrue(self.transport.closed)
        self.signal.assert_called_with(launch.signal.SIGALRM, "old-handler")

    def test_close_failure_still_cancels_alarm_and_redacts(self):
        def fail_close():
            raise OSError("SYNTHETIC private callout")
        self.transport.close = fail_close
        with self.assertRaises(RuntimeError) as error:
            self.connect()
        self.assertNotIn("SYNTHETIC", str(error.exception))
        self.alarm.assert_called_with(0)
        self.signal.assert_called_with(launch.signal.SIGALRM, "old-handler")

    def test_cli_accepts_explicit_auto_only_after_gates(self):
        with patch.object(launch, "verify_package", return_value=({}, {})), \
             patch.object(launch, "connect_and_launch") as connect, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launch.main(["--package", "/fake", "--launch", "--device", "auto",
                                          "--confirm", launch.CONFIRM]), 0)
        self.assertEqual(connect.call_args.args[0], "auto")


if __name__ == "__main__":
    unittest.main()
