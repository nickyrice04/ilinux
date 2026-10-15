"""Offline regressions for the private HV tools: no USB, no m1n1 imports.

Run as a script (tools/m1n1-client/run.sh native/hv/test_hv_launch.py) or
with python3 -m unittest from native/hv. Covers the manifest schemas 1 and 2
(including a make_hv_package.py round trip on a synthetic export), the copy
stub encoding, the open/reconnect behaviour with injected m1n1.proxy modules
and the package tests against whatever local build the repository manifest
describes (skipped with a reason when none is present).
"""
import contextlib
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time
import types
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "boot"))
import hv_chainload  # noqa: E402
import hv_launch  # noqa: E402
import make_hv_package  # noqa: E402
import census  # noqa: E402
import hv_regs  # noqa: E402
import vuart_log  # noqa: E402
import test_hv_chainload as thc  # noqa: E402  (fake live target shared with the chainload tests)
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
BOOT034 = first_dir(ROOT / "build/native-boot034/verified",
                    ROOT / "build/native-boot034-download/ilinux-j716c-boot034", need=("Image",))


def package_matches_manifest(directory, m):
    """True when directory holds every file m lists with its recorded size and SHA-256."""
    files = m["files"]
    for name, info in files.items():
        path = directory / name
        if not path.is_file() or path.stat().st_size != info["size"]:
            return False
    return all(hashlib.sha256((directory / n).read_bytes()).hexdigest() == i["sha256"]
               for n, i in files.items())


def find_hv_package():
    """The local hv package directory the repository's hv-manifest.json describes, or None.

    Any build/native-hv* layout is considered (the M5 build tree, the staged directory of
    make_hv_package.py, the M1's release download); an older build whose files no longer
    match the manifest is not used, so a manifest for a newer build skips instead of failing.
    """
    try:
        m = hv_launch.manifest()
        found = []
        for pattern in ("build/native-hv*/ilinux-j716c-hv*", "build/native-hv*",
                        "build/native-hv*-download/*", "build/native-hv*-download"):
            found += sorted(ROOT.glob(pattern))
        for candidate in found:
            if candidate.is_dir() and package_matches_manifest(candidate, m):
                return candidate
    except (OSError, KeyError, ValueError):
        pass
    return None


def find_listed_guest(directory):
    """The first local guest package whose Image the hv manifest lists, or None."""
    if directory is None:
        return None
    m = hv_launch.manifest()
    for guest in (BOOT034, BOOT033):
        if guest is None:
            continue
        try:
            hv_launch.system_map_name(m, (guest / "Image").read_bytes())
        except (OSError, ValueError):
            continue
        return guest
    return None


HV_PKG = find_hv_package()
GUEST = find_listed_guest(HV_PKG)
NO_PACKAGE = ("no local hv package matching native/hv/hv-manifest.json (and a guest package it "
              "lists) under build/native-hv*")


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

    @staticmethod
    def assemble(src):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "s.s").write_text(src)
            subprocess.run(["clang", "-c", "-target", "arm64-apple-macos", "s.s", "-o", "s.o"],
                           cwd=d, check=True)
            text = subprocess.run(["otool", "-t", "s.o"], cwd=d, check=True,
                                  capture_output=True, text=True).stdout
        words = [w for line in text.splitlines()[2:] for w in line.split()[1:]]
        return b"".join(struct.pack("<I", int(w, 16)) for w in words)

    @unittest.skipUnless(shutil.which("clang") and shutil.which("otool"), "clang/otool not available")
    def test_stub_matches_assembler(self):
        # Independent source (not the module's): in-tree loop, barriers, 8-aligned pool.
        src = ("1: ldp x5, x6, [x1], #16\n stp x5, x6, [x2]\n dc cvau, x2\n ic ivau, x2\n"
               " add x2, x2, #16\n sub x3, x3, #16\n cbnz x3, 1b\n dsb ish\n isb\n"
               " ldr x4, 2f\n br x4\n .p2align 3\n2: .quad 0x1122334455667788\n")
        self.assertEqual(self.assemble(src), hv_launch.stub(0x1122334455667788))

    @unittest.skipUnless(shutil.which("clang") and shutil.which("otool"), "clang/otool not available")
    def test_painting_stub_matches_an_independent_assembler_source(self):
        # Written out by hand here, with the geometry as literal numbers (24 rows, a
        # 20*28+24 = 584 pixel strip, a 4*28+24 = 136 pixel bar, slot 3 at +3*28*4 = 336
        # bytes): the entry mark (one 24x24 block in slot 3, x7-x12 only), then the in-tree
        # loop and barriers, then clear the strip, then ONE white bar over slots 0-4, then
        # dsb sy, with an 8-aligned pool of (origin, stride, color, entry).
        src = """
        ldr x7, 2f
        ldr x8, 3f
        ldr x9, 4f
        add x7, x7, #336
        mov w10, #24
20:     mov x11, x7
        mov w12, #24
21:     str w9, [x11], #4
        subs w12, w12, #1
        b.ne 21b
        add x7, x7, x8
        subs w10, w10, #1
        b.ne 20b
        dsb sy
1:      ldp x5, x6, [x1], #16
        stp x5, x6, [x2]
        dc cvau, x2
        ic ivau, x2
        add x2, x2, #16
        sub x3, x3, #16
        cbnz x3, 1b
        dsb ish
        isb
        ldr x5, 2f
        ldr x6, 3f
        ldr x7, 4f
        mov x11, x5
        mov w8, #24
10:     mov x9, x11
        mov w10, #584
11:     str wzr, [x9], #4
        subs w10, w10, #1
        b.ne 11b
        add x11, x11, x6
        subs w8, w8, #1
        b.ne 10b
        mov w8, #24
12:     mov x9, x5
        mov w10, #136
13:     str w7, [x9], #4
        subs w10, w10, #1
        b.ne 13b
        add x5, x5, x6
        subs w8, w8, #1
        b.ne 12b
        dsb sy
        ldr x4, 5f
        br x4
        .p2align 3
2:      .quad 0x10003003220
3:      .quad 3200
4:      .quad 0xffffffff
5:      .quad 0x1122334455667788
"""
        got = self.assemble(src)
        self.assertEqual(got, hv_launch.stub(0x1122334455667788, (0x10003003220, 3200)))
        self.assertEqual(len(got), 224)
        self.assertLessEqual(len(got), hv_chainload.STUB_MAX)
        # the pool starts at an 8-byte boundary and holds exactly origin, stride, color, entry
        self.assertEqual(struct.unpack_from("<4Q", got, 192),
                         (0x10003003220, 3200, 0xFFFFFFFF, 0x1122334455667788))
        # the bar store is still the last store of the stub and the entry mark is the first
        words = struct.unpack_from("<48I", got)
        self.assertEqual(words[0] & 0xFF000000, 0x58000000)          # ldr x7, <pool origin>
        self.assertEqual(words[7], 0xB8004569)                       # str w9, [x11], #4 (entry mark)

    def test_stub_pool_is_8_byte_aligned(self):
        # hv002's stub kept its literal at offset 36: unaligned once the MMU is off.
        for paint, pool in ((None, 48), ((0x10003000100, 3200), 192)):
            code = hv_launch.stub(0x800000800, paint)
            self.assertEqual(pool % 8, 0)
            self.assertEqual(len(code) - pool, 8 if paint is None else 32)
            self.assertEqual(code, hv_chainload.stub(0x800000800, paint))
            # every literal load targets an offset inside the 8-aligned pool
            words = struct.unpack_from("<%dI" % (pool // 4), code)
            for index, word in enumerate(words):
                if word & 0xFF000000 == 0x58000000:                    # ldr xt, literal
                    target = index * 4 + ((word >> 5) & 0x7FFFF) * 4
                    self.assertGreaterEqual(target, pool)
                    self.assertEqual(target % 8, 0)

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


class ChainloadTests(unittest.TestCase):
    def test_python_flow_no_rvbar_writes_and_one_reload(self):
        t = thc.Target()
        types = {3: SimpleNamespace(build=lambda tba: b"ba")}
        with contextlib.redirect_stdout(io.StringIO()):
            hv_launch.chainload_python(t.iface, t.proxy, t.utils, b"\0" * 0x10000,
                                       thc.blob_api(), types)
        self.assertFalse(hasattr(hv_launch, "chainload"))      # renamed
        self.assertEqual(t.of("write64"), [])
        reloads = t.of("reload")
        self.assertEqual(len(reloads), 1)
        # 0x10004-byte image -> 0x14000; SEPFW 0x8000, RAMDisk 0x1000, TrustCache 0x4000
        # (each 16K aligned) -> boot args at 0x24000, total 0x28000.
        base, region, size = thc.BASE, t.heap_events[0][1], 0x28000
        self.assertEqual(reloads[0][1:], (region + size, base + 0x24000, region, base, size))
        paint = hv_chainload.stub_paint(t.vid)
        code = hv_launch.stub(base + 0x800, paint)
        self.assertEqual(len(code), 224)
        self.assertEqual(t.mem.read(region + size, len(code)), code)
        self.assertEqual(t.mem.read(region + 0x24000, 2), b"ba")
        self.assertEqual(t.mm._properties["SEPFW"], (base + 0x14000, 0x8000))
        self.assertEqual(t.mm._types["SEPFW"], "T")
        self.assertEqual(t.mm.BootArgs, (base + 0x24000, 0x4000))
        self.assertLess(t.events.index(("push_adt",)), t.events.index(reloads[0]))

    def test_intree_flow_is_the_default_and_never_pushes_the_adt(self):
        t = thc.Target()
        with contextlib.redirect_stdout(io.StringIO()):
            plan = hv_launch.chainload_intree(t.iface, t.proxy, t.utils, b"\0" * 0x10000)
        self.assertEqual(t.of("push_adt"), [])
        self.assertEqual(t.of("write64"), [])
        self.assertEqual(len(t.of("reload")), 1)
        self.assertEqual(plan.new_base + plan.bootargs_off, t.of("reload")[0][2])

    def test_generic_error_text_for_a_build_without_the_hv_patch(self):
        # The text must not name one release: hv003 builds are checked by the same code.
        import inspect
        source = inspect.getsource(hv_launch.verify_hv_package)
        self.assertNotIn("hv002", source)
        self.assertIn("hv m1n1 build", source)


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


def manifest_patch_names(m):
    """Patch file names of a schema 1 ("m1n1_patch") or schema 2 ("m1n1_patches") manifest."""
    if "m1n1_patches" in m:
        return [entry["file"] for entry in m["m1n1_patches"]]
    return [Path(m["m1n1_patch"]).name]


def timer_block_from_the_manifest_patches():
    """The hv002 timer block, looked for across the manifest's whole patch list."""
    for name in manifest_patch_names(hv_launch.manifest()):
        try:
            return extract_timer_block((HERE / name).read_text())
        except AssertionError:
            continue
    raise AssertionError("no patch listed in the manifest carries the timer block")


@unittest.skipUnless(shutil.which("cc"), "no C compiler")
class TimerModelTests(unittest.TestCase):
    def test_source_masked_guest_timers(self):
        block = timer_block_from_the_manifest_patches()
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

    def test_block_is_found_in_either_schema_and_in_any_position(self):
        v1 = {"schema": 1, "m1n1_patch": "native/hv/0001-ilinux-hv-t6050-hv002.patch"}
        v2 = {"schema": 2, "m1n1_patches": [
            {"file": "0001-ilinux-hv-t6050-hv002.patch"},
            {"file": "0002-ilinux-hv-t6050-hv003-crumbs.patch"}]}
        self.assertEqual(manifest_patch_names(v1), ["0001-ilinux-hv-t6050-hv002.patch"])
        self.assertEqual(manifest_patch_names(v2), ["0001-ilinux-hv-t6050-hv002.patch",
                                                    "0002-ilinux-hv-t6050-hv003-crumbs.patch"])
        want = extract_timer_block((HERE / "0001-ilinux-hv-t6050-hv002.patch").read_text())
        for m in (v1, v2, dict(v2, m1n1_patches=list(reversed(v2["m1n1_patches"])))):
            with patch.object(hv_launch, "manifest", return_value=m):
                self.assertEqual(timer_block_from_the_manifest_patches(), want)
        # a manifest without the block in any listed patch is an error, not a silent skip
        nothing = {"schema": 2, "m1n1_patches": [{"file": "0002-ilinux-hv-t6050-hv003-crumbs.patch"}]}
        with patch.object(hv_launch, "manifest", return_value=nothing):
            with self.assertRaisesRegex(AssertionError, "no patch listed"):
                timer_block_from_the_manifest_patches()


# === manifests: schema 1 and schema 2 ========================================================
class ManifestSchemaTests(unittest.TestCase):
    """manifest_patches() on its own: no files, no package."""

    GOOD = "ecde6b2b9342c91d55b0254217bd940adde234837d23927dee381eea3ad9b11e"
    OTHER = "457480e01e85f68499314d6797701c7f9dfb7c36e628b9a00fb4c3f4feb1c590"

    def test_schema_1_keeps_its_single_patch_and_default_required_symbols(self):
        m = {"schema": 1, "m1n1_patch": "native/hv/0001-ilinux-hv-t6050-hv002.patch",
             "m1n1_patch_sha256": self.GOOD}
        patches, required = hv_launch.manifest_patches(m)
        self.assertEqual(patches, [("0001-ilinux-hv-t6050-hv002.patch", self.GOOD)])
        self.assertEqual(required, ["kboot_prepare_hv_guest", "hv_ilinux_timers_reset"])

    def test_schema_2_lists_patches_and_required_symbols(self):
        m = {"schema": 2, "m1n1_patches": [{"file": "a.patch", "sha256": self.GOOD},
                                           {"file": "b.patch", "sha256": self.OTHER}],
             "required_symbols": ["x", "y", "ilinux_crumb"]}
        patches, required = hv_launch.manifest_patches(m)
        self.assertEqual(patches, [("a.patch", self.GOOD), ("b.patch", self.OTHER)])
        self.assertEqual(required, ["x", "y", "ilinux_crumb"])

    def test_schema_1_keys_do_not_leak_into_schema_2_and_back(self):
        # a schema 2 manifest without its own list is refused, not read through the schema 1 keys
        m = {"schema": 2, "m1n1_patch": "native/hv/0001.patch", "m1n1_patch_sha256": self.GOOD,
             "required_symbols": ["x"]}
        with self.assertRaisesRegex(ValueError, "lists no m1n1 patches"):
            hv_launch.manifest_patches(m)
        m = {"schema": 1, "m1n1_patches": [{"file": "a.patch", "sha256": self.GOOD}]}
        with self.assertRaisesRegex(ValueError, "names no m1n1 patch"):
            hv_launch.manifest_patches(m)

    def test_malformed_manifests_are_refused(self):
        good = {"schema": 2, "m1n1_patches": [{"file": "a.patch", "sha256": self.GOOD}],
                "required_symbols": ["x"]}
        hv_launch.manifest_patches(good)
        cases = {
            "unknown schema": (dict(good, schema=3), "unsupported hv manifest schema"),
            "no schema": ({k: v for k, v in good.items() if k != "schema"},
                          "unsupported hv manifest schema"),
            "empty patch list": (dict(good, m1n1_patches=[]), "lists no m1n1 patches"),
            "patch list not a list": (dict(good, m1n1_patches={"file": "a"}),
                                      "lists no m1n1 patches"),
            "no required symbols": ({k: v for k, v in good.items() if k != "required_symbols"},
                                    "no required symbols"),
            "empty required symbols": (dict(good, required_symbols=[]), "no required symbols"),
            "non-string symbol": (dict(good, required_symbols=["x", 3]), "no required symbols"),
            "path in the name": (dict(good, m1n1_patches=[{"file": "native/hv/a.patch",
                                                            "sha256": self.GOOD}]),
                                 "invalid patch file name"),
            "traversal": (dict(good, m1n1_patches=[{"file": "../a.patch", "sha256": self.GOOD}]),
                          "invalid patch file name"),
            "hidden file": (dict(good, m1n1_patches=[{"file": ".a.patch", "sha256": self.GOOD}]),
                            "invalid patch file name"),
            "empty name": (dict(good, m1n1_patches=[{"file": "", "sha256": self.GOOD}]),
                           "invalid patch file name"),
            "entry not an object": (dict(good, m1n1_patches=["a.patch"]),
                                    "invalid patch file name"),
            "short digest": (dict(good, m1n1_patches=[{"file": "a.patch", "sha256": "abc"}]),
                             "invalid patch digest"),
            "uppercase digest": (dict(good, m1n1_patches=[{"file": "a.patch",
                                                            "sha256": self.GOOD.upper()}]),
                                 "invalid patch digest"),
            "duplicate": (dict(good, m1n1_patches=[{"file": "a.patch", "sha256": self.GOOD}] * 2),
                          "listed twice"),
        }
        for name, (m, message) in cases.items():
            with self.subTest(name), self.assertRaisesRegex(ValueError, message):
                hv_launch.manifest_patches(m)
        with self.assertRaisesRegex(ValueError, "names no m1n1 patch"):
            hv_launch.manifest_patches({"schema": 1})


# === a package round trip on a synthetic export (no VM build needed) =========================
def synthetic_export(directory, guest_dir, marker="ilinux-57a9339-hv003"):
    """Write a job out/export directory for make_hv_package.py from local boot inputs.

    The "hv image" is the installed boot021 object with its version marker replaced by the
    equal-length hv marker (padded with NULs), so every DAPF table/path offset is unchanged.
    The symbol file carries fake nm lines, toolchain.txt the pinned commit and the digests of
    the real patches, and System.map is derived from the real guest Image (_text, _end,
    descriptor, initcall).
    Returns (image bytes, hv bytes, marker text, image digest, patch paths).
    """
    boot = json.loads((HERE.parent / "boot" / "package-manifest.json").read_text())
    old = boot["m1n1_version_marker"].encode() + b"\0"
    new = ("##m1n1_ver##" + marker).encode() + b"\0"
    hv = bytearray((guest_dir / "m1n1.bin").read_bytes())
    offset = boot["m1n1_version_offset"]
    assert bytes(hv[offset:offset + len(old)]) == old and len(new) <= len(old)
    hv[offset:offset + len(old)] = new + bytes(len(old) - len(new))
    export = directory / "export"
    export.mkdir(parents=True)
    (export / "m1n1-hv.bin").write_bytes(bytes(hv))
    offsets = {"dt": 0x116538, "hv_ilinux_single_cpu": 0x35A559, "hv_ilinux_init_failed": 0x35A558,
               "kboot_prepare_hv_guest": 0x4F2A0, "hv_ilinux_timers_reset": 0x2D8E0,
               "ilinux_crumb": 0x1A340}
    (export / "m1n1-hv-symbols.txt").write_text("".join(
        "%016x %s %s\n" % (value, "D" if name in ("dt", "hv_ilinux_single_cpu",
                                                  "hv_ilinux_init_failed") else "T", name)
        for name, value in sorted(offsets.items(), key=lambda kv: kv[1])))
    image = (guest_dir / "Image").read_bytes()
    text = 0xFFFFC00080000000
    size = struct.unpack_from("<Q", image, 16)[0]
    descriptor = hv_launch.entry_guard.descriptor_offset(image)
    (export / "System.map").write_text(
        "%x T _text\n%x T deferred_probe_initcall\n%x D ilinux_fb_descriptor\n%x B _end\n"
        % (text, text + 0x100, text + descriptor, text + size))
    patches = [HERE / "0001-ilinux-hv-t6050-hv002.patch", HERE / "0002-ilinux-hv-t6050-hv003-crumbs.patch"]
    # the VM job's record: tool versions, then "m1n1 <commit> + <sha256> + <sha256>"
    (export / "toolchain.txt").write_text(
        "Linux synthetic aarch64\ngcc (synthetic)\nGNU ld (synthetic)\n" +
        "m1n1 %s + %s\n" % (hv_launch.launch.M1N1_COMMIT, " + ".join(
            hashlib.sha256(p.read_bytes()).hexdigest() for p in patches)))
    return image, bytes(hv), marker, hashlib.sha256(image).hexdigest(), patches


SYNTH_GUEST = BOOT034 or BOOT033
SYNTH_REASON = ("needs build/native-boot033 (or boot034)/verified Image and m1n1.bin: the "
                "synthetic export is derived from them")


@unittest.skipUnless(SYNTH_GUEST and (SYNTH_GUEST / "m1n1.bin").is_file(), SYNTH_REASON)
class RoundTripTests(unittest.TestCase):
    """make_hv_package.main() on a synthetic export, then hv_launch.verify_hv_package()."""

    PACKAGE = "ilinux-j716c-hv-synth"

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        # the guest package's own name, so that main() (which compares it) accepts the table
        cls.GUEST_PACKAGE = json.loads((SYNTH_GUEST / "package-manifest.json").read_text())["package"]
        cls.image, cls.hv, cls.marker, cls.digest, cls.patches = synthetic_export(root / "job", SYNTH_GUEST)
        cls.manifest_path = root / "hv-manifest.json"
        cls.destination = root / "dest"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = make_hv_package.main([
                "--out", str(root / "job"), "--name", cls.PACKAGE, "--marker", cls.marker,
                "--patch", str(cls.patches[0]), "--patch", str(cls.patches[1]),
                "--guest", "%s=%s=System.map" % (cls.digest, cls.GUEST_PACKAGE),
                "--destination", str(cls.destination), "--manifest-out", str(cls.manifest_path)])
        assert rc == 0, out.getvalue()
        cls.stage = cls.destination / cls.PACKAGE

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def verify(self, m=None, directory=None, image=None, guest_package=None):
        m = m if m is not None else json.loads(self.manifest_path.read_text())
        with patch.object(hv_launch, "manifest", return_value=m):
            return hv_launch.verify_hv_package(directory or self.stage,
                                               image if image is not None else self.image,
                                               guest_package=guest_package)

    def manifest_copy(self):
        return json.loads(self.manifest_path.read_text())

    def test_the_manifest_is_schema_2_with_both_patches_and_the_crumb_symbol(self):
        m = self.manifest_copy()
        self.assertEqual(m["schema"], 2)
        self.assertEqual([e["file"] for e in m["m1n1_patches"]], [p.name for p in self.patches])
        for entry, path in zip(m["m1n1_patches"], self.patches):
            self.assertEqual(entry["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(m["required_symbols"],
                         ["kboot_prepare_hv_guest", "hv_ilinux_timers_reset", "ilinux_crumb"])
        self.assertNotIn("m1n1_patch", m)                   # the schema-1 keys are not written
        self.assertEqual(m["guests"], {self.digest: {"package": self.GUEST_PACKAGE,
                                                     "system_map": "System.map"}})
        self.assertEqual(m["hv_version_marker"], "##m1n1_ver##" + self.marker)
        self.assertEqual(m["hv_dt_pointer_offset"], 0x116538)
        self.assertEqual(m["hv_single_cpu_offset"], 0x35A559)
        self.assertEqual(m["hv_init_failed_offset"], 0x35A558)

    def test_the_launcher_accepts_what_make_hv_package_wrote(self):
        m, loaded = self.verify(guest_package=self.GUEST_PACKAGE)
        self.assertEqual(m["schema"], 2)
        self.assertEqual(set(loaded), set(m["files"]))
        self.assertEqual(loaded["m1n1-hv.bin"], self.hv)
        # the repository path: main() reads the manifest through hv_launch.manifest()
        self.assertEqual(hv_launch.system_map_name(m, self.image),
                         ("System.map", self.GUEST_PACKAGE))

    def test_main_verifies_the_synthetic_package_offline(self):
        """The command-line path: guest package, schema 2 manifest, offline verification only."""
        with patch.object(hv_launch, "manifest", return_value=self.manifest_copy()), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            rc = hv_launch.main(["--package", str(SYNTH_GUEST), "--hv-package", str(self.stage)])
        self.assertEqual(rc, 0)
        self.assertIn("Package PASS: ", out.getvalue())
        self.assertIn("OFFLINE ONLY", out.getvalue())
        # and a manifest that names another guest package is refused at the same entry point
        other = self.manifest_copy()
        other["guests"][self.digest]["package"] = "ilinux-j716c-boot999"
        with patch.object(hv_launch, "manifest", return_value=other), \
                contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(ValueError, "different guest package"):
            hv_launch.main(["--package", str(SYNTH_GUEST), "--hv-package", str(self.stage)])

    def staged_copy(self, directory):
        """A writable copy of the staged package directory."""
        target = Path(directory) / "pkg"
        shutil.copytree(self.stage, target)
        return target

    def test_a_missing_required_symbol_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = self.staged_copy(d)
            lines = (pkg / "m1n1-hv-symbols.txt").read_text().splitlines(keepends=True)
            stripped = "".join(l for l in lines if not l.rstrip().endswith(" ilinux_crumb"))
            self.assertNotEqual(stripped, "".join(lines))
            (pkg / "m1n1-hv-symbols.txt").write_text(stripped)
            m = self.manifest_copy()
            m["files"]["m1n1-hv-symbols.txt"] = {
                "size": len(stripped.encode()), "sha256": hashlib.sha256(stripped.encode()).hexdigest()}
            with self.assertRaisesRegex(ValueError, "hv build lacks ilinux_crumb"):
                self.verify(m=m, directory=pkg)
            # the same file passes when the manifest does not require the breadcrumb symbol
            m["required_symbols"] = ["kboot_prepare_hv_guest", "hv_ilinux_timers_reset"]
            self.verify(m=m, directory=pkg)

    def test_make_hv_package_itself_refuses_a_build_without_a_required_symbol(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            synthetic_export(root / "job", SYNTH_GUEST)
            sym = root / "job/export/m1n1-hv-symbols.txt"
            sym.write_text("".join(l for l in sym.read_text().splitlines(keepends=True)
                                   if not l.rstrip().endswith(" ilinux_crumb")))
            with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
                make_hv_package.main([
                    "--out", str(root / "job"), "--name", "x", "--marker", self.marker,
                    "--patch", str(self.patches[0]), "--patch", str(self.patches[1]),
                    "--guest", "%s=%s=System.map" % (self.digest, self.GUEST_PACKAGE),
                    "--destination", str(root / "dest"),
                    "--manifest-out", str(root / "m.json")])
            self.assertIn("ilinux_crumb", str(cm.exception))

    def test_a_patch_whose_hash_differs_is_refused(self):
        for index in (0, 1):
            m = self.manifest_copy()
            m["m1n1_patches"][index]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "hv patch differs from the manifest: " +
                                        self.patches[index].name):
                self.verify(m=m)
        # the digest must match the file next to the launcher, not another listed patch
        m = self.manifest_copy()
        m["m1n1_patches"][0]["sha256"], m["m1n1_patches"][1]["sha256"] = (
            m["m1n1_patches"][1]["sha256"], m["m1n1_patches"][0]["sha256"])
        with self.assertRaisesRegex(ValueError, "hv patch differs from the manifest"):
            self.verify(m=m)

    def test_a_listed_patch_that_does_not_exist_is_refused(self):
        m = self.manifest_copy()
        m["m1n1_patches"].append({"file": "9999-not-a-patch.patch", "sha256": "1" * 64})
        with self.assertRaisesRegex(ValueError, "hv patch file is missing next to the launcher: "
                                                "9999-not-a-patch.patch"):
            self.verify(m=m)
        m = self.manifest_copy()
        m["m1n1_patches"][0]["file"] = "native/hv/" + self.patches[0].name   # a path, not a name
        with self.assertRaisesRegex(ValueError, "invalid patch file name"):
            self.verify(m=m)

    def test_every_listed_patch_is_checked_not_only_the_first(self):
        m = self.manifest_copy()
        m["m1n1_patches"].reverse()
        self.verify(m=m)                                   # order does not matter
        m["m1n1_patches"][0]["sha256"] = "2" * 64
        with self.assertRaisesRegex(ValueError, "hv patch differs from the manifest"):
            self.verify(m=m)
        m = self.manifest_copy()
        m["m1n1_patches"][-1]["sha256"] = "2" * 64         # the LAST entry is checked too
        with self.assertRaisesRegex(ValueError, "hv patch differs from the manifest"):
            self.verify(m=m)

    def test_the_schema_1_path_is_unchanged(self):
        """One patch, no symbol list: the two default required symbols apply."""
        m = self.manifest_copy()
        for key in ("m1n1_patches", "required_symbols", "guests"):
            m.pop(key)
        m.update({"schema": 1, "m1n1_patch": "native/hv/" + self.patches[0].name,
                  "m1n1_patch_sha256": hashlib.sha256(self.patches[0].read_bytes()).hexdigest(),
                  "guest_package": self.GUEST_PACKAGE, "guest_image_sha256": self.digest})
        loaded_m, loaded = self.verify(m=m, guest_package=self.GUEST_PACKAGE)
        self.assertEqual(loaded_m["schema"], 1)
        self.assertEqual(hv_launch.system_map_name(m, self.image), ("System.map", self.GUEST_PACKAGE))
        # the breadcrumb symbol is not required by schema 1 ...
        with tempfile.TemporaryDirectory() as d:
            pkg = self.staged_copy(d)
            for name in ("ilinux_crumb", "hv_ilinux_timers_reset"):
                lines = (pkg / "m1n1-hv-symbols.txt").read_text().splitlines(keepends=True)
                stripped = "".join(l for l in lines if not l.rstrip().endswith(" " + name))
                (pkg / "m1n1-hv-symbols.txt").write_text(stripped)
                m["files"]["m1n1-hv-symbols.txt"] = {
                    "size": len(stripped.encode()), "sha256": hashlib.sha256(stripped.encode()).hexdigest()}
                if name == "ilinux_crumb":
                    self.verify(m=m, directory=pkg)
                else:                                       # ... the timer symbol still is
                    with self.assertRaisesRegex(ValueError, "hv build lacks hv_ilinux_timers_reset"):
                        self.verify(m=m, directory=pkg)
        # a wrong patch hash is refused in schema 1 too
        m["m1n1_patch_sha256"] = "3" * 64
        with self.assertRaisesRegex(ValueError, "hv patch differs from the manifest"):
            self.verify(m=m)

    # --- the build record ties the commit and the patches to the binary (review R5) -----------
    def record_variant(self, directory, text):
        """Write text as the staged toolchain.txt and return a manifest that lists its new digest."""
        (Path(directory) / "toolchain.txt").write_text(text)
        m = self.manifest_copy()
        data = text.encode()
        m["files"]["toolchain.txt"] = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        return m

    def test_the_synthetic_record_names_the_commit_and_both_patch_digests(self):
        record = (self.stage / "toolchain.txt").read_text()
        self.assertIn(hv_launch.launch.M1N1_COMMIT, record)
        for path in self.patches:
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), record)
        self.assertRegex(record, r"(?m)^m1n1 [0-9a-f]{40} \+ [0-9a-f]{64} \+ [0-9a-f]{64}$")

    def test_a_patch_digest_the_build_record_does_not_name_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = self.staged_copy(d)
            record = (pkg / "toolchain.txt").read_text()
            for path in self.patches:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                m = self.record_variant(pkg, record.replace(digest, "0" * 64))
                with self.assertRaisesRegex(ValueError, "hv build record does not name the digest "
                                                        "of patch " + path.name):
                    self.verify(m=m, directory=pkg)
            # the untouched record passes, and so does an upper-case spelling of the same digests
            self.verify(m=self.record_variant(pkg, record), directory=pkg)
            self.verify(m=self.record_variant(pkg, record.upper()), directory=pkg)

    def test_a_commit_the_build_record_does_not_name_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = self.staged_copy(d)
            record = (pkg / "toolchain.txt").read_text()
            m = self.record_variant(pkg, record.replace(hv_launch.launch.M1N1_COMMIT, "f" * 40))
            with self.assertRaisesRegex(ValueError, "hv build record does not name the manifest's "
                                                    "m1n1 commit"):
                self.verify(m=m, directory=pkg)
            m = self.record_variant(pkg, "Linux synthetic aarch64\n")      # names nothing
            with self.assertRaisesRegex(ValueError, "does not name the manifest's m1n1 commit"):
                self.verify(m=m, directory=pkg)

    def test_a_schema_2_package_without_a_listed_record_is_refused(self):
        m = self.manifest_copy()
        m["files"].pop("toolchain.txt")
        with self.assertRaisesRegex(ValueError, "does not list the build record"):
            self.verify(m=m)

    def test_a_patch_edited_after_the_build_is_caught_by_the_record(self):
        """The review's repro: the patch file is edited and the manifest digest edited to match.
        The hash check alone accepts that; the build record still carries the build's digest."""
        m = self.manifest_copy()
        # the file next to the launcher is the one the manifest digest names (so the hash check
        # passes) ... but the build record, hash-verified as part of the package, names another
        with tempfile.TemporaryDirectory() as d:
            pkg = self.staged_copy(d)
            record = (pkg / "toolchain.txt").read_text()
            stale = self.record_variant(pkg, record.replace(m["m1n1_patches"][1]["sha256"],
                                                            "1" * 64))
            with self.assertRaisesRegex(ValueError, "does not name the digest of patch "
                                                    "0002-ilinux-hv-t6050-hv003-crumbs.patch"):
                self.verify(m=stale, directory=pkg)

    def test_schema_1_does_not_consult_the_build_record(self):
        m = self.manifest_copy()
        for key in ("m1n1_patches", "required_symbols", "guests"):
            m.pop(key)
        m.update({"schema": 1, "m1n1_patch": "native/hv/" + self.patches[0].name,
                  "m1n1_patch_sha256": hashlib.sha256(self.patches[0].read_bytes()).hexdigest(),
                  "guest_package": self.GUEST_PACKAGE, "guest_image_sha256": self.digest})
        with tempfile.TemporaryDirectory() as d:
            pkg = self.staged_copy(d)
            (pkg / "toolchain.txt").write_text("nothing useful\n")
            m["files"]["toolchain.txt"] = {"size": 15, "sha256": hashlib.sha256(
                b"nothing useful\n").hexdigest()}
            self.verify(m=m, directory=pkg, guest_package=self.GUEST_PACKAGE)
            m["files"].pop("toolchain.txt")
            self.verify(m=m, directory=pkg, guest_package=self.GUEST_PACKAGE)

    def test_unknown_schema_and_other_guests_are_refused(self):
        m = self.manifest_copy()
        m["schema"] = 3
        with self.assertRaisesRegex(ValueError, "unsupported hv manifest schema"):
            self.verify(m=m)
        with self.assertRaisesRegex(ValueError, "not one this hv package"):
            self.verify(image=self.image + b"x")
        with self.assertRaisesRegex(ValueError, "different guest package"):
            self.verify(guest_package="ilinux-j716c-boot999")

    def test_a_tampered_file_is_refused_by_size_or_digest(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = self.staged_copy(d)
            data = bytearray((pkg / "m1n1-hv.bin").read_bytes())
            data[1000] ^= 1
            (pkg / "m1n1-hv.bin").write_bytes(bytes(data))
            with self.assertRaisesRegex(ValueError, "checksum mismatch: m1n1-hv.bin"):
                self.verify(directory=pkg)
            (pkg / "m1n1-hv.bin").write_bytes(bytes(data) + b"\0")
            with self.assertRaisesRegex(ValueError, "size mismatch: m1n1-hv.bin"):
                self.verify(directory=pkg)

    def test_the_version_marker_must_be_at_the_recorded_offset(self):
        m = self.manifest_copy()
        m["hv_version_offset"] += 1
        with self.assertRaisesRegex(ValueError, "version marker not at the recorded offset"):
            self.verify(m=m)

    def test_offsets_come_from_the_symbol_file(self):
        for key in ("hv_dt_pointer_offset", "hv_single_cpu_offset", "hv_init_failed_offset"):
            m = self.manifest_copy()
            m[key] += 8
            with self.assertRaisesRegex(ValueError, "hv symbol offset differs from the build"):
                self.verify(m=m)


class StopLineTests(unittest.TestCase):
    PATHS = ("/dev/cu.usbmodemSECRET9", "/dev/tty.usbmodem2B0012345671", "/dev/cu.usbmodemP_01")

    def test_scrub_removes_callout_paths_and_nothing_else(self):
        for path in self.PATHS:
            text = "could not open port '%s': [Errno 2] No such file or directory" % path
            out = hv_launch.scrub(text)
            self.assertNotIn("usbmodem", out)
            self.assertNotIn("SECRET", out)
            self.assertEqual(out, "could not open port '<device>': [Errno 2] No such file or directory")
        both = hv_launch.scrub("%s and %s" % self.PATHS[:2])
        self.assertEqual(both, "<device> and <device>")
        for plain in ("no path here", "/dev/disk3s1 is not a callout", "/tmp/cu.usbmodem is a file"):
            self.assertEqual(hv_launch.scrub(plain), plain)

    def test_stop_line_is_always_one_line(self):
        exc = RuntimeError("first line\nsecond %s\r\n\tthird  " % self.PATHS[0])
        line = hv_launch.stop_line(exc)
        self.assertEqual(line, "STOP: RuntimeError first line second <device> third")
        self.assertEqual(len(line.splitlines()), 1)
        self.assertEqual(hv_launch.stop_line(KeyboardInterrupt()), "STOP: KeyboardInterrupt")
        self.assertEqual(hv_launch.stop_line(RuntimeError("   \n ")), "STOP: RuntimeError")

    def test_stop_line_carries_the_class_and_a_scrubbed_text(self):
        exc = RuntimeError("write failed on %s (errno 5)" % self.PATHS[0])
        self.assertEqual(hv_launch.stop_line(exc), "STOP: RuntimeError write failed on <device> (errno 5)")

    def test_cli_prints_one_scrubbed_line_and_returns_1(self):
        err = io.StringIO()
        boom = OSError("[Errno 6] Device not configured: '%s'" % self.PATHS[1])
        with patch.object(hv_launch, "main", side_effect=boom), contextlib.redirect_stderr(err):
            self.assertEqual(hv_launch.cli(["--package", "x"]), 1)
        self.assertEqual(err.getvalue().splitlines(),
                         ["STOP: OSError [Errno 6] Device not configured: '<device>'"])
        # a clean run keeps main()'s return value; SystemExit (argparse) is not swallowed
        with patch.object(hv_launch, "main", return_value=0):
            self.assertEqual(hv_launch.cli([]), 0)
        with patch.object(hv_launch, "main", side_effect=SystemExit(2)):
            with self.assertRaises(SystemExit):
                hv_launch.cli([])

    # --- Ctrl-C and everything else that is not an Exception (review R1) ----------------------
    SECRET = "/dev/cu.usbmodemSECRET0123456789"

    @staticmethod
    def chained_ctrl_c(path):
        """KeyboardInterrupt as raised in proxy.reload() -> wait_boot()'s reconnect loop: its
        __context__ chain carries pyserial's 'could not open port <callout path>' text."""
        class SerialException(OSError):
            pass

        def main(argv=None):
            try:
                raise SerialException("device reports readiness to read but returned no data")
            except SerialException:
                try:
                    raise SerialException(2, "could not open port %s: [Errno 2] No such file or "
                                             "directory: '%s'" % (path, path))
                except SerialException:
                    raise KeyboardInterrupt()
        return main

    def run_cli(self, main):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(hv_launch, "main", main), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            try:
                rc = hv_launch.cli([])
            except KeyboardInterrupt:      # a regression must fail this test, not abort the run
                self.fail("KeyboardInterrupt escaped cli()")
        return rc, out.getvalue(), err.getvalue()

    def check_ctrl_c_is_one_clean_line(self):
        rc, out, err = self.run_cli(self.chained_ctrl_c(self.SECRET))
        self.assertEqual(rc, 130)
        self.assertEqual(err, "STOP: KeyboardInterrupt\n")
        self.assertEqual(out, "")
        for text in (out, err):
            for leak in ("SECRET", "usbmodem", "/dev/", "Traceback", "During handling", "direct cause"):
                self.assertNotIn(leak, text)

    def test_ctrl_c_with_a_serial_path_in_its_chain_prints_one_line_and_exits_130(self):
        self.check_ctrl_c_is_one_clean_line()
        # an explicit cause is never printed either
        def main(argv=None):
            raise KeyboardInterrupt() from OSError("could not open port %s" % self.SECRET)
        rc, out, err = self.run_cli(main)
        self.assertEqual((rc, err, out), (130, "STOP: KeyboardInterrupt\n", ""))
        # a path in the interrupt's own text is scrubbed, not echoed
        rc, out, err = self.run_cli(lambda argv=None: (_ for _ in ()).throw(
            KeyboardInterrupt("reading from " + self.SECRET)))
        self.assertEqual((rc, err), (130, "STOP: KeyboardInterrupt reading from <device>\n"))

    def test_any_other_base_exception_is_one_scrubbed_line_and_exit_1(self):
        class Fatal(BaseException):
            pass

        rc, out, err = self.run_cli(lambda argv=None: (_ for _ in ()).throw(
            Fatal("lost %s" % self.SECRET)))
        self.assertEqual((rc, err, out), (1, "STOP: Fatal lost <device>\n", ""))
        # a plain Exception keeps exit 1, SystemExit keeps its code
        rc, out, err = self.run_cli(lambda argv=None: (_ for _ in ()).throw(
            RuntimeError("write failed on %s" % self.SECRET)))
        self.assertEqual((rc, err), (1, "STOP: RuntimeError write failed on <device>\n"))
        with patch.object(hv_launch, "main", side_effect=SystemExit(7)):
            with self.assertRaises(SystemExit) as caught:
                hv_launch.cli([])
        self.assertEqual(caught.exception.code, 7)

    def test_a_closed_stderr_does_not_turn_the_stop_line_into_a_traceback(self):
        class Closed(io.StringIO):
            def write(self, text):
                raise OSError("stderr closed")
        with patch.object(hv_launch, "main", self.chained_ctrl_c(self.SECRET)), \
                patch.object(sys, "stderr", Closed()):
            try:
                rc = hv_launch.cli([])
            except KeyboardInterrupt:
                self.fail("KeyboardInterrupt escaped cli()")
        self.assertEqual(rc, 130)

    def test_a_second_ctrl_c_while_the_line_is_written_does_not_escape(self):
        class Interrupted(io.StringIO):
            def write(self, text):
                raise KeyboardInterrupt()
        with patch.object(hv_launch, "main", self.chained_ctrl_c(self.SECRET)), \
                patch.object(sys, "stderr", Interrupted()):
            try:
                rc = hv_launch.cli([])
            except KeyboardInterrupt:
                self.fail("the second KeyboardInterrupt escaped cli()")
        self.assertEqual(rc, 130)

    def test_mutation_that_catches_only_exceptions_lets_the_chain_out(self):
        def old_cli(argv=None):
            try:
                return hv_launch.main(argv)
            except Exception as exc:
                print(hv_launch.stop_line(exc), file=sys.stderr)
                return 1

        self.check_ctrl_c_is_one_clean_line()                       # the real cli passes
        with patch.object(hv_launch, "cli", old_cli):
            with self.assertRaises((AssertionError, KeyboardInterrupt)):
                self.check_ctrl_c_is_one_clean_line()

    def test_a_real_sigint_through_the_script_entry_point_exits_130_with_one_line(self):
        """End to end: a real SIGINT while the launcher sits in a blocking read."""
        with tempfile.TemporaryDirectory() as d:
            fifo = Path(d) / "package-manifest.json"
            os.mkfifo(fifo)                    # opening it for reading blocks until a writer comes
            def default_sigint():       # a harness may start us with SIGINT ignored (background job)
                signal.signal(signal.SIGINT, signal.SIG_DFL)
            proc = subprocess.Popen([sys.executable, "-I", str(HERE / "hv_launch.py"),
                                     "--package", d, "--hv-package", d],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    preexec_fn=default_sigint)
            writer = None
            try:
                deadline = time.monotonic() + 30
                while writer is None:
                    try:       # succeeds only once the launcher has opened the read end
                        writer = os.open(str(fifo), os.O_WRONLY | os.O_NONBLOCK)
                    except OSError as exc:
                        if exc.errno != errno.ENXIO:
                            raise
                        if proc.poll() is not None or time.monotonic() > deadline:
                            self.fail("the launcher never reached the blocking read")
                        time.sleep(0.05)
                # Let the child get from open() into its blocking read(): CPython runs a Python
                # signal handler only at a bytecode boundary or when a syscall returns EINTR, so a
                # SIGINT that lands between the last boundary and the read() syscall is not seen
                # until the read returns (about 2% of the runs when it is sent at the very instant
                # the rendezvous completes). Pending signals coalesce, so a second SIGINT after
                # a quiet period is still exactly one KeyboardInterrupt.
                time.sleep(0.5)
                proc.send_signal(signal.SIGINT)
                try:
                    out, err = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.send_signal(signal.SIGINT)
                    out, err = proc.communicate(timeout=30)
            finally:
                if writer is not None:
                    os.close(writer)
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
        self.assertEqual(proc.returncode, 130)
        self.assertEqual(err, "STOP: KeyboardInterrupt\n")
        self.assertEqual(out, "")

    def test_the_script_entry_point_uses_it(self):
        run = subprocess.run([sys.executable, "-I", str(HERE / "hv_launch.py"), "--package",
                              "/nonexistent-guest-package", "--hv-package", "/nonexistent-hv"],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 1)
        self.assertTrue(run.stderr.startswith("STOP: "), run.stderr)
        self.assertEqual(len(run.stderr.strip().splitlines()), 1)        # no traceback
        self.assertNotIn("Traceback", run.stderr)


# === open_primary / reconnect with injected m1n1.proxy objects ================================
class OpenPortTests(unittest.TestCase):
    """No pyserial and no device: the m1n1.proxy module is replaced by fakes."""

    def setUp(self):
        self.opens, self.interfaces, self.fail_open, self.fail_init = [], [], None, None
        outer = self

        class Serial:
            def __init__(self, path, baud):
                if outer.fail_open is not None:
                    raise outer.fail_open
                outer.opens.append((path, baud))
                self.path, self.closed, self.timeout = path, False, None

            def close(self):
                self.closed = True

        class UartInterface:
            DEFAULT_BAUD_RATE = 115200

            def __init__(self, device=None):
                if outer.fail_init is not None:
                    raise outer.fail_init
                self.dev = device
                self.tty_enable = True           # the real class enables the TTY echo
                outer.interfaces.append(self)

        proxy_module = types.ModuleType("m1n1.proxy")
        proxy_module.Serial, proxy_module.UartInterface = Serial, UartInterface
        package = types.ModuleType("m1n1")
        package.proxy = proxy_module
        self.port = hv_launch.usb_identity.Port("/dev/cu.usbmodemSYNTHETIC1", 0x1209, 0x316D, 1, 10)
        patches = [patch.dict(sys.modules, {"m1n1": package, "m1n1.proxy": proxy_module}),
                   patch.object(hv_launch.usb_identity, "discover", return_value=[self.port]),
                   patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFCHR))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_target_console_text_is_never_echoed(self):
        transport, iface = hv_launch.open_primary("auto")
        self.assertIs(iface.tty_enable, False)               # kboot's serial line stays off screen
        self.assertIs(iface.dev, transport)
        self.assertEqual(transport.timeout, 15)
        self.assertEqual(self.opens, [(self.port.path, 115200)])

    def test_every_reconnect_opens_with_the_echo_disabled(self):
        attempts = {"n": 0}
        real_discover = hv_launch.usb_identity.discover

        def flaky():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise OSError("registry busy /dev/cu.usbmodemSECRET9")
            return real_discover()

        with patch.object(hv_launch.usb_identity, "discover", side_effect=flaky):
            clock = [0.0]
            transport, iface, proxy = hv_launch.reconnect(
                "auto", lambda i: SimpleNamespace(nop=lambda: None), wait=10,
                sleep=lambda s: clock.__setitem__(0, clock[0] + s), clock=lambda: clock[0])
        self.assertEqual(attempts["n"], 3)
        self.assertTrue(self.interfaces)
        self.assertTrue(all(i.tty_enable is False for i in self.interfaces))
        self.assertIs(iface.tty_enable, False)

    def test_mutation_without_the_echo_switch_is_caught(self):
        mutant = thc.mutated_hv_launch(("        iface.tty_enable = False\n", ""))
        _, iface = mutant.open_primary("auto")
        self.assertIs(iface.tty_enable, True)                 # the mutant echoes: what the test sees
        _, iface = hv_launch.open_primary("auto")
        self.assertIs(iface.tty_enable, False)

    def test_identity_failures_name_only_the_exception_class(self):
        for error in (OSError("ioreg failed for /dev/cu.usbmodemSECRET9"),
                      subprocess.CalledProcessError(1, ["ioreg", "/dev/cu.usbmodemSECRET9"]),
                      ValueError("Need exactly one m1n1 primary data interface; no port opened")):
            with self.subTest(type(error).__name__):
                with patch.object(hv_launch.usb_identity, "discover", side_effect=error):
                    with self.assertRaises(ValueError) as caught:
                        hv_launch.open_primary("auto")
                text = str(caught.exception)
                self.assertEqual(text, "USB identity check failed (%s); no port opened"
                                 % type(error).__name__)
                self.assertNotIn("SECRET", text)
                self.assertTrue(caught.exception.__suppress_context__)   # no chained original
                self.assertEqual(self.opens, [])

    def test_a_requested_path_that_is_not_the_primary_is_refused_without_the_path(self):
        with self.assertRaises(ValueError) as caught:
            hv_launch.open_primary("/dev/cu.usbmodemOTHER77")
        self.assertNotIn("OTHER77", str(caught.exception))
        self.assertIn("USB identity check failed (ValueError)", str(caught.exception))
        self.assertEqual(self.opens, [])

    def test_open_failures_name_only_the_exception_class(self):
        class SerialException(OSError):         # pyserial's class derives from IOError
            pass

        for error in (FileNotFoundError(2, "No such file or directory", "/dev/cu.usbmodemSECRET9"),
                      SerialException("could not open port '/dev/cu.usbmodemSECRET9'"),
                      PermissionError(13, "Permission denied: '/dev/cu.usbmodemSECRET9'")):
            with self.subTest(type(error).__name__):
                self.fail_open = error
                with self.assertRaises(RuntimeError) as caught:
                    hv_launch.open_primary("auto")
                text = str(caught.exception)
                self.assertEqual(text, "USB transport failed (%s); do not automatically retry"
                                 % type(error).__name__)
                self.assertNotIn("SECRET", text)
                self.assertTrue(caught.exception.__suppress_context__)

    def test_a_failing_interface_constructor_closes_the_port_and_is_sanitized(self):
        self.fail_init = OSError(5, "I/O error on /dev/cu.usbmodemSECRET9")
        transports = []
        real = sys.modules["m1n1.proxy"].Serial

        def spy(path, baud):
            t = real(path, baud)
            transports.append(t)
            return t

        sys.modules["m1n1.proxy"].Serial = spy
        with self.assertRaises(RuntimeError) as caught:
            hv_launch.open_primary("auto")
        self.assertEqual(str(caught.exception),
                         "USB transport failed (OSError); do not automatically retry")
        self.assertEqual(len(transports), 1)
        self.assertTrue(transports[0].closed)

    def test_the_global_alarm_and_ctrl_c_pass_through_untouched(self):
        with patch.object(hv_launch.usb_identity, "discover",
                          side_effect=TimeoutError("preflight exceeded 300 seconds")):
            with self.assertRaises(TimeoutError):
                hv_launch.open_primary("auto")
        self.fail_open = TimeoutError("alarm")
        with self.assertRaises(TimeoutError):
            hv_launch.open_primary("auto")
        self.fail_open = None
        self.fail_init = KeyboardInterrupt()
        transports = []
        real = sys.modules["m1n1.proxy"].Serial
        sys.modules["m1n1.proxy"].Serial = lambda p, b: transports.append(real(p, b)) or transports[-1]
        with self.assertRaises(KeyboardInterrupt):
            hv_launch.open_primary("auto")
        self.assertTrue(transports[0].closed)

    def test_reconnect_failure_text_says_power_off_and_read_the_strip(self):
        now = [0.0]
        with patch.object(hv_launch.usb_identity, "discover", side_effect=OSError("gone")):
            with self.assertRaises(ValueError) as caught:
                hv_launch.reconnect("auto", lambda i: None, wait=2,
                                    sleep=lambda s: now.__setitem__(0, now[0] + s),
                                    clock=lambda: now[0])
        self.assertEqual(str(caught.exception),
                         "m1n1 did not answer after chainload; POWER OFF completely and read the "
                         "strip per hv-instructions.md")
        self.assertTrue(caught.exception.__suppress_context__)

    def test_close_quietly_only_lets_the_alarm_through(self):
        hv_launch.close_quietly(SimpleNamespace(close=lambda: (_ for _ in ()).throw(OSError("x"))))
        hv_launch.close_quietly(SimpleNamespace(close=lambda: None))
        with self.assertRaises(TimeoutError):
            hv_launch.close_quietly(SimpleNamespace(
                close=lambda: (_ for _ in ()).throw(TimeoutError("alarm"))))


# === local package tests (need a build matching the repository manifest) =====================
@unittest.skipUnless(HV_PKG and GUEST, NO_PACKAGE)
class PackageTests(unittest.TestCase):
    """Against the real files the repository's hv-manifest.json describes (any schema)."""

    @classmethod
    def setUpClass(cls):
        cls.image = (GUEST / "Image").read_bytes()
        cls.m = hv_launch.manifest()
        cls.map_name, cls.package = hv_launch.system_map_name(cls.m, cls.image)

    def stage(self, directory):
        """Every file the manifest lists, copied into directory."""
        for name in self.m["files"]:
            shutil.copy(HV_PKG / name, Path(directory) / name)

    def test_real_packages_verify_offline(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(hv_launch.main(["--package", str(GUEST), "--hv-package", str(HV_PKG)]), 0)
        self.assertIn("OFFLINE ONLY", out.getvalue())

    def test_the_manifest_schema_is_one_the_launcher_knows(self):
        self.assertIn(self.m["schema"], (1, 2))
        patches, required = hv_launch.manifest_patches(self.m)
        self.assertTrue(patches)
        for name, digest in patches:
            self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), digest, name)
        self.assertIn("hv_ilinux_timers_reset", required)

    def test_the_build_record_of_the_real_package_names_commit_and_patches(self):
        if self.m["schema"] != 2:
            self.skipTest("schema 1 manifests are not tied to the build record")
        record = (HV_PKG / "toolchain.txt").read_text().lower()
        self.assertIn(self.m["m1n1_commit"], record)
        for entry in self.m["m1n1_patches"]:
            self.assertIn(entry["sha256"], record, entry["file"])

    def test_tampered_hv_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            self.stage(d)
            data = bytearray((Path(d) / "m1n1-hv.bin").read_bytes())
            data[-1] ^= 1
            (Path(d) / "m1n1-hv.bin").write_bytes(bytes(data))
            with self.assertRaisesRegex(ValueError, "checksum"):
                hv_launch.verify_hv_package(Path(d), self.image)

    def test_a_build_missing_any_required_symbol_is_rejected(self):
        required = hv_launch.manifest_patches(self.m)[1]
        for symbol in required:
            with self.subTest(symbol), tempfile.TemporaryDirectory() as d:
                self.stage(d)
                syms = (HV_PKG / "m1n1-hv-symbols.txt").read_text().splitlines(keepends=True)
                stripped = "".join(l for l in syms if not l.rstrip().endswith(" " + symbol))
                self.assertNotEqual(len(stripped), sum(map(len, syms)))
                (Path(d) / "m1n1-hv-symbols.txt").write_text(stripped)
                m = dict(self.m, files=dict(self.m["files"]))
                m["files"]["m1n1-hv-symbols.txt"] = {
                    "size": len(stripped.encode()), "sha256": hashlib.sha256(stripped.encode()).hexdigest()}
                with patch.object(hv_launch, "manifest", return_value=m):
                    with self.assertRaisesRegex(ValueError, symbol):
                        hv_launch.verify_hv_package(Path(d), self.image)

    def multi_guest(self, directory, alt=None):
        """The package with this guest's map stored under another name, as a guests table."""
        self.stage(directory)
        alt = alt if alt is not None else (HV_PKG / self.map_name).read_bytes()
        (Path(directory) / "System.map-alt").write_bytes(alt)
        m = json.loads(json.dumps(self.m))
        m["files"]["System.map-alt"] = {"size": len(alt), "sha256": hashlib.sha256(alt).hexdigest()}
        m["guests"] = {hashlib.sha256(self.image).hexdigest(): {
            "package": self.package or "ilinux-j716c-guest", "system_map": "System.map-alt"}}
        m.pop("guest_image_sha256", None)
        m.pop("guest_package", None)
        return m

    def test_guests_table_selects_the_map_by_image_hash(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.multi_guest(Path(d))
            with patch.object(hv_launch, "manifest", return_value=m):
                _, loaded = hv_launch.verify_hv_package(Path(d), self.image, guest_package=self.package)
        self.assertIn("System.map-alt", loaded)

    def test_guests_table_map_must_describe_the_image(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.multi_guest(Path(d), alt=b"ffffc00080000000 T _text\n")
            with patch.object(hv_launch, "manifest", return_value=m):
                with self.assertRaisesRegex(ValueError, "lacks"):
                    hv_launch.verify_hv_package(Path(d), self.image)

    def test_guests_table_files_are_all_hash_verified(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.multi_guest(Path(d))
            data = bytearray((Path(d) / "System.map-alt").read_bytes())
            data[-2] ^= 1                                          # same size, other content
            (Path(d) / "System.map-alt").write_bytes(bytes(data))
            with patch.object(hv_launch, "manifest", return_value=m):
                with self.assertRaisesRegex(ValueError, "checksum mismatch: System.map-alt"):
                    hv_launch.verify_hv_package(Path(d), self.image)

    def test_guests_table_rejections(self):
        with tempfile.TemporaryDirectory() as d:
            m = self.multi_guest(Path(d))
            with patch.object(hv_launch, "manifest", return_value=m):
                with self.assertRaisesRegex(ValueError, "not one this hv package"):
                    hv_launch.verify_hv_package(Path(d), self.image + b"x")
                with self.assertRaisesRegex(ValueError, "different guest package"):
                    hv_launch.verify_hv_package(Path(d), self.image, guest_package="ilinux-j716c-boot999")
            unlisted = dict(m, files={k: v for k, v in m["files"].items() if k != "System.map-alt"})
            with patch.object(hv_launch, "manifest", return_value=unlisted):
                with self.assertRaisesRegex(ValueError, "not listed"):
                    hv_launch.verify_hv_package(Path(d), self.image)
            traversal = dict(m, guests={h: dict(g, system_map="../System.map") for h, g in m["guests"].items()})
            with patch.object(hv_launch, "manifest", return_value=traversal):
                with self.assertRaisesRegex(ValueError, "invalid guests entry"):
                    hv_launch.verify_hv_package(Path(d), self.image)

    def test_the_guest_package_name_is_checked(self):
        if self.package is None:
            self.skipTest("the manifest records no package name for this guest")
        with self.assertRaisesRegex(ValueError, "different guest package"):
            hv_launch.verify_hv_package(HV_PKG, self.image, guest_package=self.package + "-other")

    def test_symbol_offsets_must_match_build(self):
        m = hv_launch.manifest()
        m["hv_init_failed_offset"] += 8
        with patch.object(hv_launch, "manifest", return_value=m):
            with self.assertRaisesRegex(ValueError, "hv_ilinux_init_failed"):
                hv_launch.verify_hv_package(HV_PKG, self.image)


@unittest.skipUnless(BOOT033, "needs build/native-boot033/verified")
class GuestManifestTests(unittest.TestCase):
    def test_guest_manifest_follows_package_name(self):
        m = hv_launch.guest_manifest_for(BOOT033)
        self.assertEqual(m["package"], "ilinux-j716c-boot033")
        with tempfile.TemporaryDirectory() as d:
            own = json.loads((BOOT033 / "package-manifest.json").read_text())
            own["files"]["Image"]["size"] += 1
            (Path(d) / "package-manifest.json").write_text(json.dumps(own))
            with self.assertRaisesRegex(ValueError, "differs from the repository"):
                hv_launch.guest_manifest_for(Path(d))
            own["package"] = "ilinux-j716c-boot999"
            (Path(d) / "package-manifest.json").write_text(json.dumps(own))
            with self.assertRaisesRegex(ValueError, "no repository manifest"):
                hv_launch.guest_manifest_for(Path(d))


class CensusCliTests(unittest.TestCase):
    """census.py shares hv_launch's R1 rule: no traceback, no chain, no device path."""

    def run_cli(self, exc):
        import census
        err = io.StringIO()

        def main(argv=None):
            raise exc
        with patch.object(census, "main", main), contextlib.redirect_stderr(err):
            code = census.cli([])
        return code, err.getvalue()

    def test_ctrl_c_with_a_chained_device_path_prints_one_clean_line(self):
        try:
            try:
                raise OSError("could not open port /dev/cu.usbmodemSECRET9")
            except OSError:
                raise KeyboardInterrupt
        except KeyboardInterrupt as exc:
            error = exc
        code, err = self.run_cli(error)
        self.assertEqual(code, 130)
        self.assertEqual(err, "STOP: KeyboardInterrupt\n")

    def test_ordinary_errors_are_scrubbed_to_one_line(self):
        code, err = self.run_cli(RuntimeError("failed on /dev/cu.usbmodemSECRET9 now"))
        self.assertEqual(code, 1)
        self.assertNotIn("SECRET", err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(err.count("\n"), 1)

    def test_system_exit_passes_through(self):
        with self.assertRaises(SystemExit):
            self.run_cli(SystemExit(2))


if __name__ == "__main__":
    unittest.main()
