"""Offline regressions: no imports of upstream code and no physical devices."""
import contextlib
import io
import json
from pathlib import Path
import struct
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
        self.adt = {"/": SimpleNamespace(compatible=["J716cAP"])}
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
        def wrong(p):
            u = FakeUtils(p)
            u.adt["/"].compatible = ["J714cAP"]
            return u
        with self.assertRaisesRegex(ValueError, "board"):
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


if __name__ == "__main__":
    unittest.main()
