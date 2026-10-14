"""Offline regressions for the private HV tools: no USB, no m1n1 imports.

Run as a script (tools/m1n1-client/run.sh native/hv/test_hv_launch.py) or
with python3 -m unittest from native/hv.
"""
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
import census  # noqa: E402
import hv_regs  # noqa: E402
import vuart_log  # noqa: E402
import test_launcher as tl  # noqa: E402

ROOT = HERE.parents[1]
RAM = 0x10000000000


def first_dir(*candidates, need):
    for c in candidates:
        if all((c / n).is_file() for n in need):
            return c
    return None


# M5 build tree, or the M1's verified release downloads.
BOOT033 = first_dir(ROOT / "build/native-boot033/verified",
                    ROOT / "build/native-boot033-download/ilinux-j716c-boot033", need=("Image",))
HV002 = first_dir(ROOT / "build/native-hv002",
                  ROOT / "build/native-hv002-download/native-hv002", need=("m1n1-hv.bin",))


def prepared_hv(memory=(RAM, 0x200000000), extra=(), **kw):
    """test_launcher.prepared() plus the /memory node m1n1 kboot adds."""
    real_fdt = tl.fdt

    def with_memory(nodes):
        return real_fdt(nodes + [("memory@10000000000", {
            "device_type": b"memory\0", "reg": struct.pack(">QQ", *memory)}, [])] + list(extra))

    kw.setdefault("bootargs", hv_launch.HV_BOOTARGS)
    with patch.object(tl, "fdt", with_memory):
        return tl.prepared(**kw)


def image(size=4096):
    data = bytearray(64)
    struct.pack_into("<QQ", data, 8, 0, size)
    data[56:60] = b"ARM\x64"
    data.extend(hv_launch.entry_guard.MAGIC + bytes(16))
    return bytes(data)


class PureTests(unittest.TestCase):
    def test_bootargs_only_add_serial_console(self):
        old, new = hv_launch.launch.BOOTARGS.split(), hv_launch.HV_BOOTARGS.split()
        self.assertEqual(set(new) - set(old),
                         {"console=ttySAC0,115200", "earlycon=s5l,0x505200000"})
        self.assertEqual(set(old) - set(new), {"earlycon=ilinuxfb"})
        consoles = [a for a in new if a.startswith("console=")]
        # tty0 stays last: /dev/console is the framebuffer, as in native boots.
        self.assertEqual(consoles, ["console=ttySAC0,115200", "console=tty0"])
        for keep in ("maxcpus=1", "nr_cpus=1", "idle=nop", "arm64.nowfxt", "cpufreq.off=1",
                     "pd_ignore_unused", "clk_ignore_unused", "panic=0"):
            self.assertIn(keep, new)

    @unittest.skipUnless(shutil.which("clang") and shutil.which("otool"), "clang/otool not available")
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
        self.assertLessEqual(lay["kernel"] + (64 << 20), lay["initrd"])
        self.assertLessEqual(lay["initrd"] + (9 << 20), lay["dt"])
        self.assertLessEqual(lay["dt"] + (256 << 10), lay["end"])
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

    def test_payload_overlap(self):
        lay = {"base": RAM + (1 << 30), "end": RAM + (1 << 30) + (128 << 20)}
        hv_launch.check_payload_overlap({"/reserved-memory/a": {"reg": struct.pack(">QQ", RAM, 1 << 20)}}, lay)
        with self.assertRaisesRegex(ValueError, "reserved-memory/b"):
            hv_launch.check_payload_overlap(
                {"/reserved-memory/b": {"reg": struct.pack(">QQ", lay["end"] - 4096, 8192)}}, lay)
        with self.assertRaisesRegex(ValueError, "framebuffer"):
            hv_launch.check_payload_overlap(
                {"/chosen/framebuffer@1": {"reg": struct.pack(">QQ", lay["base"], 4096)}}, lay)

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

    def test_hv_flags_gate(self):
        m = {"hv_single_cpu_offset": 0x10, "hv_init_failed_offset": 0x11}

        def proxy(single, failed):
            return SimpleNamespace(read8=lambda a: {0x1010: single, 0x1011: failed}[a])

        hv_launch.check_hv_flags(proxy(1, 0), 0x1000, m)
        with self.assertRaisesRegex(ValueError, "single-CPU"):
            hv_launch.check_hv_flags(proxy(0, 0), 0x1000, m)
        with self.assertRaisesRegex(ValueError, "refused"):
            hv_launch.check_hv_flags(proxy(1, 1), 0x1000, m)

    def test_cpu_start_hook_is_reserved(self):
        calls = []
        pmgr = SimpleNamespace(get_reg=lambda i: (0x280600000, 0x1fc000))
        hv = SimpleNamespace(adt={"/arm-io/pmgr": pmgr}, log=lambda s: calls.append(("log", s)),
                             map_hook=lambda a, n, write: calls.append(("hook", a, n)),
                             add_tracer=lambda z, ident, mode: calls.append(("tracer", z, ident, mode)))
        hv_launch.hook_cpu_start(hv, lambda a, n: (a, n), "RESERVED")
        self.assertEqual(calls, [("hook", 0x280688000, 0x20),
                                 ("tracer", (0x280688000, 0x20), "CPU_START", "RESERVED")])

    def test_reconnect_retries_then_verifies(self):
        attempts, closed, now = [], [], [0.0]

        class Transport:
            def close(self): closed.append(1)

        def opener(device):
            attempts.append(device)
            if len(attempts) < 3:
                raise OSError("gone")
            return Transport(), "iface"

        nops = []
        proxy = SimpleNamespace(nop=lambda: nops.append(1))
        out = hv_launch.reconnect("auto", lambda iface: proxy, opener=opener,
                                  sleep=lambda s: now.__setitem__(0, now[0] + s),
                                  clock=lambda: now[0])
        self.assertEqual(len(attempts), 3)
        self.assertEqual(out[1:], ("iface", proxy))
        self.assertEqual(nops, [1])

    def test_reconnect_closes_failed_port_and_times_out(self):
        closed, now = [], [0.0]

        class Transport:
            def close(self): closed.append(1)

        def bad_nop():
            raise OSError("no answer")

        with self.assertRaisesRegex(ValueError, "did not answer"):
            hv_launch.reconnect("auto", lambda i: SimpleNamespace(nop=bad_nop), wait=2,
                                opener=lambda d: (Transport(), "iface"),
                                sleep=lambda s: now.__setitem__(0, now[0] + s), clock=lambda: now[0])
        self.assertTrue(closed)

    def test_reconnect_does_not_swallow_global_timeout(self):
        def opener(device):
            raise TimeoutError("preflight exceeded")

        with self.assertRaises(TimeoutError):
            hv_launch.reconnect("auto", lambda i: None, opener=opener, sleep=lambda s: None)

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
        events, data = [], {}
        iface = SimpleNamespace(writemem=lambda a, d: (events.append(("write", a, len(d))),
                                                       data.__setitem__(a, d)))
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
        # 0x10004-byte image -> 0x14000; SEPFW blob 0x4000; boot args 0x4000.
        base, region, size = 0x800000000, 0x900000000, 0x1C000
        self.assertEqual(reloads[0][1:], (region + size, base + 0x18000, region, base, size))
        self.assertEqual(data[region + size], hv_launch.stub(base + 0x800))
        self.assertEqual(data[region + 0x18000], b"ba")
        self.assertEqual(mm._properties["SEPFW"], (base + 0x14000, 0x100))
        self.assertEqual(mm._types["SEPFW"], "T")
        self.assertEqual(mm.BootArgs, (base + 0x18000, 0x4000))
        self.assertLess(events.index(("push_adt",)), events.index(reloads[0]))


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
            return hv_launch.prepare_guest(self.iface, self.proxy, self.utils,
                                           self.files, self.hv_files, self.m)

    def test_sequence_and_placement(self):
        lay = self.run_prepare()
        self.assertGreater(lay["base"], self.utils.heap_top)
        self.assertEqual([c for c in self.proxy.calls if isinstance(c[0], str)],
                         [("bootargs", hv_launch.HV_BOOTARGS)])  # no stdout-path, as native
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

    def test_reserved_overlap_stops_before_hardware_prep(self):
        base = hv_launch.align_up(self.utils.heap_top + (16 << 20), 2 << 20)
        resv = ("reserved-memory", {"#address-cells": struct.pack(">I", 2),
                                    "#size-cells": struct.pack(">I", 2), "ranges": b""},
                [("fw@0", {"reg": struct.pack(">QQ", base + (1 << 20), 1 << 20)}, [])])
        self.iface.tree = prepared_hv(extra=[resv])
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.run_prepare()
        self.assertNotIn(("request", 0x7F0), self.calls)
        self.assertNotIn("dapf", [c[0] for c in self.calls])


ECV1 = {(3, 0, 0, 7, 0): 1 << 60}


class CensusTests(unittest.TestCase):
    def fake(self, values, trap=()):
        class Utils:
            def mrs(self, enc):
                if enc in trap:
                    raise RuntimeError("Exception occurred")
                return values.get(enc, 0)
        return Utils()

    def rows(self, values=None, trap=()):
        merged = dict(ECV1)
        merged.update(values or {})
        return census.census(self.fake(merged, trap), (RuntimeError,))

    def test_reads_every_hv_path_register(self):
        rows = self.rows()
        names = [r[0] for r in rows]
        self.assertEqual(len(rows), len(hv_regs.REGS))
        for name in ("ACTLR_EL2", "PMCR0", "IPI_SR_EL1", "UPMCR0", "UPMSR"):
            self.assertIn(name, names)
        self.assertIn(("ID_AA64MMFR0_EL1", "readable", "ECV=1"), rows)
        self.assertEqual(census.verdict(rows), [])

    def test_enabled_guest_timer_fiqs_no_longer_block(self):
        rows = self.rows({(3, 5, 15, 1, 3): 3})
        self.assertIn(("VM_TMR_FIQ_ENA_EL2", "readable", "ENA_V=1 ENA_P=1"), rows)
        self.assertEqual(census.verdict(rows), [])

    def test_missing_ecv_blocks(self):
        rows = census.census(self.fake({}), (RuntimeError,))
        self.assertTrue(any("no ECV" in b for b in census.verdict(rows)))

    def test_trap_is_reported_not_raised(self):
        rows = self.rows(trap=[(3, 4, 15, 4, 7)])
        self.assertIn(("AMX_CTL_EL2", "trapped", "RuntimeError"), rows)
        self.assertIn("AMX_CTL_EL2", census.verdict(rows))

    def test_hot_path_registers_block_when_trapped(self):
        for enc, name in (((3, 1, 15, 0, 0), "PMCR0"), ((3, 5, 15, 1, 1), "IPI_SR_EL1")):
            self.assertIn(name, census.verdict(self.rows(trap=[enc])))

    def test_unused_registers_are_informational(self):
        rows = self.rows(trap=[(3, 6, 15, 14, 6), (3, 7, 15, 0, 4), (3, 7, 15, 6, 4)])
        self.assertEqual(sum(r[1] == "trapped" for r in rows), 3)
        self.assertEqual(census.verdict(rows), [])

    def test_no_raw_values_printed(self):
        rows = self.rows({(3, 4, 14, 1, 0): 0xDEADBEEF})
        self.assertNotIn("deadbeef", repr(rows).lower())

    def test_launcher_preflight_uses_the_same_rules(self):
        self.assertEqual(len(hv_launch.register_preflight(self.fake(ECV1), (RuntimeError,))),
                         len(hv_regs.REGS))
        with self.assertRaisesRegex(ValueError, "preflight BLOCKED: .*PMCR0"):
            hv_launch.register_preflight(self.fake(ECV1, trap=[(3, 1, 15, 0, 0)]), (RuntimeError,))
        with self.assertRaisesRegex(ValueError, "no ECV"):
            hv_launch.register_preflight(self.fake({}), (RuntimeError,))


class VuartTests(unittest.TestCase):
    def test_selects_only_interface_3(self):
        P = vuart_log.usb_identity.Port
        ports = [P("/dev/a", 0x1209, 0x316D, 1, 0x0A), P("/dev/b", 0x1209, 0x316D, 3, 0x0A)]
        self.assertEqual(vuart_log.select_vuart(ports), "/dev/b")
        with self.assertRaises(ValueError):
            vuart_log.select_vuart(ports[:1])
        with self.assertRaises(ValueError):
            vuart_log.select_vuart(ports + [P("/dev/c", 0x1209, 0x316D, 3, 0x0A)])

    def test_reopens_after_disconnect(self):
        class Gone(Exception):
            pass

        class Port:
            def __init__(self, chunks):
                self.chunks = list(chunks)

            def read(self, n):
                item = self.chunks.pop(0)
                if isinstance(item, BaseException):
                    raise item
                return item

            def close(self):
                pass

        ports = [Port([b"boot021 ", Gone()]), Port([b"", b"linux", KeyboardInterrupt()])]
        log, out, notes = io.BytesIO(), io.BytesIO(), []
        with self.assertRaises(KeyboardInterrupt):
            vuart_log.serve(log, out, lambda: "/dev/b", lambda p: ports.pop(0), (Gone,),
                            sleep=lambda s: None, notify=notes.append)
        self.assertEqual(log.getvalue(), b"boot021 linux")
        self.assertEqual(sum("disconnected" in n for n in notes), 1)


def extract_timer_block(patch_text):
    """The exact source-masked timer code added to src/hv/hv_exc.c by the patch,
    taken from the post-patch side of its hunk (context lines included)."""
    in_file, hunks = False, []
    for line in patch_text.splitlines():
        if line.startswith("diff --git"):
            in_file = line.endswith("src/hv/hv_exc.c")
        elif in_file and line.startswith("@@"):
            hunks.append([])
        elif in_file and hunks and line[:1] in (" ", "+"):
            hunks[-1].append(line[1:])
    for hunk in hunks:
        text = "\n".join(hunk) + "\n"
        if "#define ILINUX_TMR_V " in text:
            start = text.index("#define ILINUX_TMR_V ")
            fn = text.index("void hv_ilinux_timers_reset(void)")
            return text[start:text.index("\n}\n", fn) + 3]
    raise AssertionError("timer block not found in patch")


@unittest.skipUnless(shutil.which("cc"), "no C compiler")
class TimerModelTests(unittest.TestCase):
    def test_source_masked_guest_timers(self):
        patch_file = HERE / Path(hv_launch.manifest()["m1n1_patch"]).name
        block = extract_timer_block(patch_file.read_text())
        self.assertIn("static bool hv_ilinux_update_timers(void)", block)
        self.assertIn("static bool hv_ilinux_timer_access(u64 reg, bool is_read, u64 *val)", block)
        self.assertNotIn("VM_TMR_FIQ_ENA", block.split("*/", 1)[1])  # never written by hv002
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "timer_block.inc").write_text(block)
            shutil.copy(HERE / "test_timer_model.c", Path(d) / "model.c")
            subprocess.run(["cc", "-std=c11", "-g", "-O1", "-Wall", "-Wextra", "-Werror",
                            "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                            "-I", d, "model.c", "-o", "model"], cwd=d, check=True)
            out = subprocess.run([str(Path(d) / "model")], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("timer model PASS", out.stdout)


@unittest.skipUnless(BOOT033 and HV002, "local build packages not present")
class PackageTests(unittest.TestCase):
    def test_real_packages_verify_offline(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(hv_launch.main(["--package", str(BOOT033), "--hv-package", str(HV002)]), 0)
        self.assertIn("OFFLINE ONLY", out.getvalue())

    def test_tampered_hv_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("m1n1-hv.bin", "System.map", "m1n1-hv-symbols.txt"):
                shutil.copy(HV002 / name, Path(d) / name)
            data = bytearray((Path(d) / "m1n1-hv.bin").read_bytes())
            data[-1] ^= 1
            (Path(d) / "m1n1-hv.bin").write_bytes(bytes(data))
            img = (BOOT033 / "Image").read_bytes()
            with self.assertRaisesRegex(ValueError, "checksum"):
                hv_launch.verify_hv_package(Path(d), img)

    def test_non_hv002_build_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("m1n1-hv.bin", "System.map"):
                shutil.copy(HV002 / name, Path(d) / name)
            syms = (HV002 / "m1n1-hv-symbols.txt").read_text().splitlines(keepends=True)
            stripped = "".join(l for l in syms if not l.rstrip().endswith(" hv_ilinux_timers_reset"))
            self.assertNotEqual(len(stripped), sum(map(len, syms)))
            (Path(d) / "m1n1-hv-symbols.txt").write_text(stripped)
            m = hv_launch.manifest()
            m["files"]["m1n1-hv-symbols.txt"] = {
                "size": len(stripped.encode()), "sha256": hashlib.sha256(stripped.encode()).hexdigest()}
            with patch.object(hv_launch, "manifest", return_value=m):
                with self.assertRaisesRegex(ValueError, "hv_ilinux_timers_reset"):
                    hv_launch.verify_hv_package(Path(d), (BOOT033 / "Image").read_bytes())

    def test_symbol_offsets_must_match_build(self):
        m = hv_launch.manifest()
        m["hv_init_failed_offset"] += 8
        with patch.object(hv_launch, "manifest", return_value=m):
            with self.assertRaisesRegex(ValueError, "hv_ilinux_init_failed"):
                hv_launch.verify_hv_package(HV002, (BOOT033 / "Image").read_bytes())


if __name__ == "__main__":
    unittest.main()
