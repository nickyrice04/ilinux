"""Offline regressions for the private HV launcher: no USB, no m1n1 imports."""
import contextlib
import hashlib
import io
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "boot"))
import hv_launch  # noqa: E402
import test_launcher as tl  # noqa: E402

ROOT = HERE.parents[1]
BOOT033 = ROOT / "build/native-boot033/verified"
HV001 = ROOT / "build/native-hv001"
RAM = 0x10000000000


def prepared_hv(memory=(RAM, 0x200000000), **kw):
    """test_launcher.prepared() plus the /memory node m1n1 kboot adds."""
    real_fdt = tl.fdt

    def with_memory(nodes):
        return real_fdt(nodes + [("memory@10000000000", {
            "device_type": b"memory\0", "reg": struct.pack(">QQ", *memory)}, [])])

    with patch.object(tl, "fdt", with_memory):
        kw.setdefault("bootargs", hv_launch.HV_BOOTARGS)
        return tl.prepared(**kw)


def image(size=4096):
    data = bytearray(64)
    struct.pack_into("<QQ", data, 8, 0, size)
    data[56:60] = b"ARM\x64"
    data.extend(hv_launch.entry_guard.MAGIC + bytes(16))
    return bytes(data)


class PureTests(unittest.TestCase):
    def test_bootargs_only_move_console(self):
        old, new = hv_launch.launch.BOOTARGS.split(), hv_launch.HV_BOOTARGS.split()
        self.assertEqual(set(new) - set(old),
                         {"console=ttySAC0,115200", "earlycon=s5l,0x505200000"})
        self.assertEqual(set(old) - set(new), {"earlycon=ilinuxfb"})
        self.assertEqual(new[1], "console=ttySAC0,115200")
        for keep in ("maxcpus=1", "nr_cpus=1", "idle=nop", "arm64.nowfxt", "cpufreq.off=1"):
            self.assertIn(keep, new)

    @unittest.skipUnless(shutil.which("clang"), "clang not available")
    def test_stub_matches_assembler(self):
        src = ("1: ldp x4, x5, [x1], #16\n stp x4, x5, [x2]\n dc cvau, x2\n ic ivau, x2\n"
               " add x2, x2, #16\n sub x3, x3, #16\n cbnz x3, 1b\n ldr x1, 2f\n br x1\n"
               "2: .quad 0x1122334455667788\n")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "s.s").write_text(src)
            subprocess.run(["clang", "-c", "-target", "arm64-apple-macos", "s.s", "-o", "s.o"],
                           cwd=d, check=True)
            text = subprocess.run(["otool", "-t", "s.o"], cwd=d, check=True,
                                  capture_output=True, text=True).stdout
        words = [w for line in text.splitlines()[2:] for w in line.split()[1:]]
        got = b"".join(struct.pack("<I", int(w, 16)) for w in words)
        self.assertEqual(got, hv_launch.stub(0x1122334455667788))

    def test_layout_is_above_heap_aligned_and_ordered(self):
        lay = hv_launch.guest_layout(RAM + 0x123456, RAM + (8 << 30), image(64 << 20), 9 << 20, 256 << 10)
        self.assertEqual(lay["base"] % (2 << 20), 0)
        self.assertGreaterEqual(lay["base"], RAM + 0x123456 + (16 << 20))
        self.assertLess(lay["kernel"] + (64 << 20), lay["initrd"] + 1)
        self.assertLess(lay["initrd"] + (9 << 20), lay["dt"] + 1)
        with self.assertRaisesRegex(ValueError, "do not fit"):
            hv_launch.guest_layout(RAM, RAM + (32 << 20), image(64 << 20), 1, 1)

    def test_restrict_memory(self):
        blob = prepared_hv()
        out = hv_launch.restrict_memory(blob, RAM + (1 << 30))
        self.assertEqual(len(out), len(blob))
        tree = hv_launch.check_stage_b(out, prepared=True)
        self.assertEqual(struct.unpack(">QQ", tree["/memory@10000000000"]["reg"]),
                         (RAM + (1 << 30), 0x200000000 - (1 << 30)))
        with self.assertRaisesRegex(ValueError, "outside"):
            hv_launch.restrict_memory(blob, RAM + 0x300000000)
        with self.assertRaisesRegex(ValueError, "one /memory"):
            hv_launch.restrict_memory(tl.prepared(), RAM)

    def test_system_map_must_match_image(self):
        img = image()
        off = hv_launch.entry_guard.descriptor_offset(img)
        good = ("ffffc00080000000 T _text\nffffc00080000100 T deferred_probe_initcall\n"
                "%x D ilinux_fb_descriptor\n%x B _end\n" % (0xffffc00080000000 + off,
                                                            0xffffc00080000000 + 4096))
        hv_launch.check_system_map(good, img)
        with self.assertRaisesRegex(ValueError, "does not match"):
            hv_launch.check_system_map(good.replace("%x D" % (0xffffc00080000000 + off),
                                                    "%x D" % (0xffffc00080000008 + off)), img)
        with self.assertRaisesRegex(ValueError, "lacks"):
            hv_launch.check_system_map(good.replace("deferred_probe_initcall", "x"), img)

    def test_dapf_pin_is_scoped(self):
        old = hv_launch.dapf_guard.IMAGE_SHA256
        with self.assertRaises(RuntimeError):
            with hv_launch.hv_dapf_pin(b"x"):
                self.assertEqual(hv_launch.dapf_guard.IMAGE_SHA256, hashlib.sha256(b"x").hexdigest())
                raise RuntimeError
        self.assertEqual(hv_launch.dapf_guard.IMAGE_SHA256, old)

    def test_launch_gates(self):
        for argv in (["--launch", "--device", "auto"], ["--launch", "--confirm", hv_launch.CONFIRM],
                     ["--device", "auto"], ["--launch", "--device", "auto", "--confirm",
                                            "BOOT-J716C-RAM-DIAGNOSTIC"]):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                hv_launch.main(["--package", "x", "--hv-package", "y"] + argv)


class FakeMemoryMap:
    def __init__(self):
        self._properties = {"SEPFW": (0x5000, 0x100)}
        self._types = {}
        self.BootArgs = None


class ChainloadTests(unittest.TestCase):
    def test_no_rvbar_writes_and_one_reload(self):
        events = []
        iface = SimpleNamespace(writemem=lambda a, d: events.append(("write", a, len(d))))
        proxy = SimpleNamespace(
            dc_cvau=lambda *a: None, ic_ivau=lambda *a: None,
            write64=lambda *a: events.append(("write64",) + a),
            reload=lambda *a: events.append(("reload",) + a))
        mm = FakeMemoryMap()
        ba = SimpleNamespace(revision=2, copy=lambda: SimpleNamespace(revision=2, top_of_kernel_data=0))
        utils = SimpleNamespace(base=0x800000000, adt={"chosen": {"memory-map": mm}}, ba=ba,
                                malloc=lambda size: 0x900000000,
                                compressed_writemem=lambda *a: events.append(("cwrite",)),
                                push_adt=lambda: events.append(("push_adt",)))
        find = lambda props, names, base: ([("SEPFW", 0x5000, 0x100, base)], base + 0x4000)
        copy = lambda p, blobs: events.append(("copy", blobs))
        types = {2: SimpleNamespace(build=lambda tba: b"ba")}
        hv_launch.chainload(iface, proxy, utils, b"\0" * 0x10000, (("SEPFW",), find, copy, "T"), types)
        self.assertFalse([e for e in events if e[0] == "write64"])
        reloads = [e for e in events if e[0] == "reload"]
        self.assertEqual(len(reloads), 1)
        stub_addr = reloads[0][1]
        written = [e for e in events if e[0] == "write" and e[1] == stub_addr]
        self.assertEqual(written[0][2], len(hv_launch.stub(0)))
        self.assertEqual(mm._types["SEPFW"], "T")
        self.assertEqual(events.index(("push_adt",)) < events.index(reloads[0]), True)


class GuestTests(unittest.TestCase):
    def setUp(self):
        self.dt = prepared_hv()
        self.calls = []
        test = self

        class Proxy(tl.FakeProxy):
            def read64(self, addr): return 0x9000
            def request(self, op, *args):
                test.calls.append(("request", op))
                return 0

        class Iface(tl.FakeInterface):
            def writemem(self, addr, data):
                test.calls.append(("write", addr, len(data)))
                super().writemem(addr, data)

        self.proxy = Proxy()
        self.iface = Iface(self.dt)
        utils = tl.FakeUtils(self.proxy)
        utils.base = 0x1000
        utils.heap_top = RAM + (512 << 20)
        utils.ba.phys_base, utils.ba.mem_size = RAM, 0x200000000
        self.utils = utils
        self.files = {"Image": image(), "t6050-j716c-stage-b.dtb": self.dt,
                      "initramfs-stage-b.cpio.gz": b"initrd"}
        self.hv_files = {"m1n1-hv.bin": b"hv"}
        self.m = {"hv_dt_pointer_offset": 0x200}

    def run_prepare(self):
        with contextlib.redirect_stdout(io.StringIO()), \
             patch.object(hv_launch.dapf_guard, "prepare", return_value="plan"), \
             patch.object(hv_launch.dapf_guard, "apply",
                          side_effect=lambda *a: self.calls.append(("dapf",))), \
             patch.object(hv_launch.entry_guard, "apply",
                          side_effect=lambda *a: self.calls.append(("fb",))):
            return hv_launch.prepare_guest(self.iface, self.proxy, self.utils, None,
                                           self.files, self.hv_files, self.m)

    def test_sequence_and_placement(self):
        lay = self.run_prepare()
        self.assertGreater(lay["base"], self.utils.heap_top)
        self.assertIn(("stdout-path", "serial0"), self.proxy.calls)
        self.assertIn(("bootargs", hv_launch.HV_BOOTARGS), self.proxy.calls)
        order = [c[0] if c[0] != "request" else c for c in self.calls]
        self.assertLess(order.index("dapf"), order.index(("request", 0x7F0)))
        self.assertLess(order.index(("request", 0x7F0)), order.index("fb"))
        dt_writes = [c for c in self.calls if c[0] == "write" and c[1] == lay["dt"]]
        self.assertEqual(len(dt_writes), 1)
        written = dict((a, d) for a, d in self.iface.writes)[lay["dt"]]
        mem = hv_launch.check_stage_b(written, prepared=True)["/memory@10000000000"]["reg"]
        self.assertEqual(struct.unpack(">Q", mem[:8])[0], lay["base"])
        self.assertFalse(self.proxy.boots)

    def test_wrong_bootargs_stop_before_hardware_prep(self):
        self.iface.tree = prepared_hv(bootargs=hv_launch.launch.BOOTARGS)
        with self.assertRaisesRegex(ValueError, "bootargs"):
            self.run_prepare()
        self.assertNotIn(("request", 0x7F0), self.calls)

    def test_two_cpus_rejected(self):
        self.iface.tree = prepared_hv(cpu_count=2)
        with self.assertRaisesRegex(ValueError, "one CPU"):
            self.run_prepare()
        self.assertNotIn(("request", 0x7F0), self.calls)


@unittest.skipUnless((BOOT033 / "Image").exists() and (HV001 / "m1n1-hv.bin").exists(),
                     "local build packages not present")
class PackageTests(unittest.TestCase):
    def test_real_packages_verify_offline(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(hv_launch.main(["--package", str(BOOT033), "--hv-package", str(HV001)]), 0)
        self.assertIn("OFFLINE ONLY", out.getvalue())

    def test_tampered_hv_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("m1n1-hv.bin", "System.map"):
                shutil.copy(HV001 / name, Path(d) / name)
            data = bytearray((Path(d) / "m1n1-hv.bin").read_bytes())
            data[-1] ^= 1
            (Path(d) / "m1n1-hv.bin").write_bytes(bytes(data))
            img = (BOOT033 / "Image").read_bytes()
            with self.assertRaisesRegex(ValueError, "checksum"):
                hv_launch.verify_hv_package(Path(d), img)


if __name__ == "__main__":
    unittest.main()


import census  # noqa: E402


class CensusTests(unittest.TestCase):
    def fake(self, values, trap=()):
        class Utils:
            def mrs(self, enc):
                if enc in trap:
                    raise RuntimeError("Exception occurred")
                return values.get(enc, 0)
        return Utils()

    def test_reads_only_and_classifies(self):
        rows = census.census(self.fake({(3, 0, 0, 7, 0): 1 << 60}), (RuntimeError,))
        self.assertEqual(len(rows), len(census.REGS))
        self.assertIn(("ID_AA64MMFR0_EL1", "readable", "ECV=1"), rows)
        self.assertEqual(census.verdict(rows), [])

    def test_enabled_timer_fiq_blocks(self):
        rows = census.census(self.fake({(3, 5, 15, 1, 3): 2}), (RuntimeError,))
        self.assertTrue(census.verdict(rows))

    def test_trap_is_reported_not_raised(self):
        rows = census.census(self.fake({}, trap=[(3, 4, 15, 4, 7)]), (RuntimeError,))
        self.assertIn(("AMX_CTL_EL2", "trapped", "RuntimeError"), rows)
        self.assertIn("AMX_CTL_EL2", census.verdict(rows))

    def test_no_raw_values_printed(self):
        rows = census.census(self.fake({(3, 4, 14, 1, 0): 0xDEADBEEF}), (RuntimeError,))
        self.assertNotIn("deadbeef", repr(rows).lower())


import vuart_log  # noqa: E402


class VuartTests(unittest.TestCase):
    def test_selects_only_interface_3(self):
        P = vuart_log.usb_identity.Port
        ports = [P("/dev/a", 0x1209, 0x316D, 1, 0x0A), P("/dev/b", 0x1209, 0x316D, 3, 0x0A)]
        self.assertEqual(vuart_log.select_vuart(ports), "/dev/b")
        with self.assertRaises(ValueError):
            vuart_log.select_vuart(ports[:1])
        with self.assertRaises(ValueError):
            vuart_log.select_vuart(ports + [P("/dev/c", 0x1209, 0x316D, 3, 0x0A)])
