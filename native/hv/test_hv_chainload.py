"""Offline regressions for the hv003 chainload: no USB, no m1n1 imports.

Covers hv_chainload.py (strip geometry, copy stub with its entry mark, clear
and bar passes, layout arithmetic and gates) and the in-tree/python chainload,
--layout-only, --chainload-only and --control stock paths of hv_launch.py
(write order, the live ADT window and its restore, reload failure, new-instance
proof, layout facts) against fake targets that record every write. Run as
`python3 -I native/hv/test_hv_chainload.py` or with `python3 -m unittest` from
native/hv.
"""
import ast
import contextlib
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import types
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "boot"))
import adt_patch  # noqa: E402
import hv_chainload as C  # noqa: E402
import hv_launch  # noqa: E402
import test_adt_patch as TA  # noqa: E402

RAM = 0x10000000000
RAM_SIZE = 0x40000000
BASE = RAM + 0x1000000
# The facts the layout gates establish beyond the destination (printed once they pass).
GATE_FACTS = ("the staging block starts at or above top_of_kernel_data and clears the source "
              "blobs being moved")
IMAGE_LEN = 0x10000
VIRT_BASE = 0xFFFFFE0010000000
BOOT_BLOBS = ("SEPFW", "SEPPatches", "uStuff", "preoslog", "RTBuddySeg", "RAMDisk",
              "SPTMDebug", "ExclaveOSIntegrityCatalog", "ExclaveOSTrustCache", "TrustCache")


def video(**kw):
    values = dict(base=RAM + 0x3000000, display=1, stride=3200, width=800, height=600, depth=30)
    values.update(kw)
    return SimpleNamespace(**values)


# --- sparse target memory ---------------------------------------------------------
class Memory:
    PAGE = 0x1000

    def __init__(self):
        self.pages = {}

    def write(self, addr, data):
        data, pos = bytes(data), 0
        while pos < len(data):
            page, off = divmod(addr + pos, self.PAGE)
            chunk = min(self.PAGE - off, len(data) - pos)
            buf = self.pages.setdefault(page, bytearray(self.PAGE))
            buf[off:off + chunk] = data[pos:pos + chunk]
            pos += chunk

    def read(self, addr, size):
        out, pos = bytearray(), 0
        while pos < size:
            page, off = divmod(addr + pos, self.PAGE)
            chunk = min(self.PAGE - off, size - pos)
            buf = self.pages.get(page)
            out += buf[off:off + chunk] if buf else bytes(chunk)
            pos += chunk
        return bytes(out)


def same_sequence(test, got, want, what):
    """assertEqual for long sequences: a mismatch reports only the first difference.

    unittest's own diff of two 17,000-entry lists takes minutes, which would make a failing
    stub test look like a hang.
    """
    got, want = list(got), list(want)
    if got == want:
        return
    first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
    test.fail("%s differs: %d entries against %d, first difference at index %d (%r against %r)"
              % (what, len(got), len(want), first,
                 got[first] if first < len(got) else None, want[first] if first < len(want) else None))


# --- a tiny AArch64 interpreter for exactly the instructions the stub uses -------
class AlignmentFault(Exception):
    pass


def _sx(value, bits):
    return value - (1 << bits) if value >> (bits - 1) else value


def run_stub(code, stub_addr, regs, mem, limit=3_000_000):
    """Execute code (bytes at stub_addr, MMU off: aligned data accesses only).

    Returns (regs, log); log holds, in program order, ("cp", addr) for each
    16-byte copy store, ("st", addr, value) for each 4-byte paint store, the
    dc/ic/dsb/isb events and the final ("br", target). Memory accesses to
    Device memory must be aligned to their size, which is what the real stub
    runs under.
    """
    x = dict(regs)
    flag_z = False
    log = []
    pc, steps = 0, 0

    def rd(n):
        return 0 if n == 31 else x.get(n, 0)

    def wr(n, v):
        if n != 31:
            x[n] = v & ((1 << 64) - 1)

    def aligned(addr, size):
        if addr % size:
            raise AlignmentFault("0x%x size %d" % (addr, size))

    while True:
        steps += 1
        if steps > limit:
            raise AssertionError("stub did not finish")
        w = struct.unpack_from("<I", code, pc)[0]
        nxt = pc + 4
        if w & 0xFFC00000 == 0xA8C00000:                      # ldp xt, xt2, [xn], #imm
            n, t, t2 = (w >> 5) & 31, w & 31, (w >> 10) & 31
            addr = rd(n)
            aligned(addr, 8)
            wr(t, int.from_bytes(mem.read(addr, 8), "little"))
            wr(t2, int.from_bytes(mem.read(addr + 8, 8), "little"))
            wr(n, addr + _sx((w >> 15) & 0x7F, 7) * 8)
        elif w & 0xFFC00000 == 0xA9000000:                    # stp xt, xt2, [xn, #imm]
            n, t, t2 = (w >> 5) & 31, w & 31, (w >> 10) & 31
            addr = rd(n) + _sx((w >> 15) & 0x7F, 7) * 8
            aligned(addr, 8)
            mem.write(addr, rd(t).to_bytes(8, "little") + rd(t2).to_bytes(8, "little"))
            log.append(("cp", addr))
        elif w in (0xD50B7B22, 0xD50B7522):                   # dc cvau, x2 / ic ivau, x2
            log.append(("dc" if w == 0xD50B7B22 else "ic", rd(2)))
        elif w & 0xFFC00000 == 0x91000000:                    # add xd, xn, #imm
            wr(w & 31, rd((w >> 5) & 31) + ((w >> 10) & 0xFFF))
        elif w & 0xFFC00000 == 0xD1000000:                    # sub xd, xn, #imm
            wr(w & 31, rd((w >> 5) & 31) - ((w >> 10) & 0xFFF))
        elif w & 0xFF000000 == 0xB5000000:                    # cbnz xt, label
            if rd(w & 31):
                nxt = pc + _sx((w >> 5) & 0x7FFFF, 19) * 4
        elif w == 0xD5033B9F:
            log.append(("dsb", "ish"))
        elif w == 0xD5033F9F:
            log.append(("dsb", "sy"))
        elif w == 0xD5033FDF:
            log.append(("isb",))
        elif w == 0xD503201F:                                 # nop
            pass
        elif w & 0xFF000000 == 0x58000000:                    # ldr xt, literal
            off = pc + _sx((w >> 5) & 0x7FFFF, 19) * 4
            aligned(stub_addr + off, 8)
            wr(w & 31, struct.unpack_from("<Q", code, off)[0])
        elif w & 0xFFFFFC1F == 0xD61F0000:                    # br xn
            log.append(("br", rd((w >> 5) & 31)))
            return x, log
        elif w & 0xFFE00000 == 0x52800000:                    # movz wd, #imm16
            wr(w & 31, (w >> 5) & 0xFFFF)
        elif w & 0xFFE0FFE0 == 0xAA0003E0:                    # mov xd, xm (orr xd, xzr, xm)
            wr(w & 31, rd((w >> 16) & 31))
        elif w & 0xFFE00C00 == 0xB8000400:                    # str wt, [xn], #imm (post-index)
            n, t = (w >> 5) & 31, w & 31
            addr = rd(n)
            aligned(addr, 4)
            mem.write(addr, (rd(t) & 0xFFFFFFFF).to_bytes(4, "little"))
            log.append(("st", addr, rd(t) & 0xFFFFFFFF))
            wr(n, addr + _sx((w >> 12) & 0x1FF, 9))
        elif w & 0xFF800000 == 0x71000000:                    # subs wd, wn, #imm
            res = (rd((w >> 5) & 31) - ((w >> 10) & 0xFFF)) & 0xFFFFFFFF
            flag_z = res == 0
            wr(w & 31, res)
        elif w & 0xFF000010 == 0x54000000:                    # b.cond
            cond = w & 15
            if cond != 1:
                raise AssertionError("only b.ne is expected")
            if not flag_z:
                nxt = pc + _sx((w >> 5) & 0x7FFFF, 19) * 4
        elif w & 0xFF200000 == 0x8B000000:                    # add xd, xn, xm
            wr(w & 31, rd((w >> 5) & 31) + rd((w >> 16) & 31))
        else:
            raise AssertionError("unexpected instruction word 0x%08x at +0x%x" % (w, pc))
        pc = nxt


# --- fake live target -------------------------------------------------------------
def u64s(*v):
    return TA.u64s(*v)


def make_adt(sepfw, others):
    props = [("SEPFW", u64s(*sepfw), 0)] if sepfw is not None else []
    mm = TA.node("memory-map", props + [(n, u64s(*v), 0) for n, v in others.items()])
    chosen = TA.node("chosen", [("firmware-version", b"iBoot-1\0", 0)], [mm])
    return TA.node("device-tree", [("compatible", b"J716cAP\0apple,t6050\0", 0)], [chosen])


def raw_boot_args(phys_base=RAM, mem_size=RAM_SIZE, top=RAM + 0x1800000, vid=None,
                  devtree=None, devtree_size=0, revision=3):
    v = vid or video()
    out = bytearray(b"\xa5" * 0x480)  # distinctive filler: only a raw copy preserves it
    struct.pack_into("<HH", out, 0, revision, 2)
    struct.pack_into("<I", out, 4, 0)
    struct.pack_into("<4Q", out, 8, VIRT_BASE, phys_base, mem_size, top)
    struct.pack_into("<6Q", out, 0x28, v.base, v.display, v.stride, v.width, v.height, v.depth)
    struct.pack_into("<I", out, 0x58, 0x1234)
    struct.pack_into("<QI", out, 0x60, devtree, devtree_size)
    out[0x6C:0x6C + 24] = b"serial=SECRETMARKER9999\0"
    return bytes(out)


class FakeAdt:
    """utils.adt: item access to the memory-map model, and build() for the python flow."""

    def __init__(self, target):
        self.target = target

    def __getitem__(self, key):
        return {"chosen": {"memory-map": self.target.mm}}[key]

    def build(self):
        """The raw ADT with the model's SEPFW pair (what a rebuild would carry), plus any extra."""
        t = self.target
        sepfw = t.mm._properties.get("SEPFW")
        data = t.adt
        if sepfw is not None and t.sepfw is not None:
            data, _, _ = adt_patch.patch_value(t.adt, "/chosen/memory-map", "SEPFW",
                                               struct.pack("<QQ", *sepfw))
        return data + t.build_extra


class Target:
    """Records every mutating call; reads never change anything."""

    def __init__(self, base=BASE, sepfw=(RAM + 0x6000000, 0x8000), vid=None,
                 ba_addr=RAM + 0x1FF0000, adt_addr=RAM + 0x2000000, heap=RAM + 0x20000000,
                 ram=(RAM, RAM_SIZE), others=None, ba_revision=3, top=RAM + 0x1800000,
                 devtree_size=None, malloc_error=False):
        self.events = []     # target-visible mutations, in order
        self.heap_events = []
        self.mem = Memory()
        self.base = base
        self.top = top
        self.malloc_error = malloc_error
        self.reload_effect = None   # called with reload's arguments after the event is recorded
        self.build_extra = b""      # appended to a rebuilt ADT by FakeAdt.build
        self.vid = vid or video()
        self.sepfw = sepfw
        small = sepfw is not None and 0 < sepfw[1] < 0x100000 and sepfw[0] < (1 << 63)
        self.sepfw_data = bytes((i * 7 + 3) & 0xFF for i in range(sepfw[1])) if small else b""
        if small:
            self.mem.write(sepfw[0], self.sepfw_data)
        self.others = {"TrustCache": (BASE + 0x8000, 0x4000), "RAMDisk": (RAM + 0x7000000, 0x1000),
                       "Absent": (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)} if others is None else others
        self.adt = make_adt(sepfw, self.others)
        self.mem.write(adt_addr, self.adt)
        self.adt_addr, self.ba_addr = adt_addr, ba_addr
        size = len(self.adt) if devtree_size is None else devtree_size
        self.raw_ba = raw_boot_args(phys_base=ram[0], mem_size=ram[1], top=top, vid=self.vid,
                                    devtree=VIRT_BASE + (adt_addr - ram[0]),
                                    devtree_size=size, revision=ba_revision)
        self.mem.write(ba_addr, self.raw_ba)
        self.next_heap = heap
        self.iface = SimpleNamespace(readmem=self._read, writemem=self._write)
        self.proxy = SimpleNamespace(
            get_bootargs=lambda: self.ba_addr, memcpy8=self._memcpy8,
            dc_cvau=lambda a, n: self.events.append(("dc_cvau", a, n)),
            ic_ivau=lambda a, n: self.events.append(("ic_ivau", a, n)),
            write64=lambda a, v: self.events.append(("write64", a, v)),
            reload=self._reload)
        ba = SimpleNamespace(
            revision=ba_revision, version=2, virt_base=VIRT_BASE, phys_base=ram[0],
            mem_size=ram[1], top_of_kernel_data=top, devtree=VIRT_BASE + (adt_addr - ram[0]),
            devtree_size=size, video=SimpleNamespace(
                base=self.vid.base, stride=self.vid.stride, width=self.vid.width,
                height=self.vid.height, depth=self.vid.depth))
        ba.copy = lambda: SimpleNamespace(**{k: v for k, v in vars(ba).items() if k != "copy"})
        props = dict(self.others)
        if sepfw is not None:
            props["SEPFW"] = sepfw
        self.mm = SimpleNamespace(_properties=props, _types={}, BootArgs=None)
        self.utils = SimpleNamespace(
            base=base, ba=ba, get_adt=lambda: self.adt, malloc=self._malloc,
            free=lambda a: self.heap_events.append(("free", a)),
            compressed_writemem=self._cwrite,
            push_adt=self._push_adt,
            adt=FakeAdt(self))

    # iface / proxy / utils behaviours
    def _read(self, addr, size):
        return self.mem.read(addr, size)

    def _write(self, addr, data):
        self.events.append(("write", addr, bytes(data)))
        self.mem.write(addr, data)

    def _cwrite(self, addr, data, progress=None):
        self.events.append(("cwrite", addr, bytes(data)))
        self.mem.write(addr, data)

    def _memcpy8(self, dst, src, size):
        self.events.append(("memcpy8", dst, src, size))
        self.mem.write(dst, self.mem.read(src, size))

    def _reload(self, *args):
        self.events.append(("reload",) + args)
        if self.reload_effect is not None:
            self.reload_effect(*args)

    def _push_adt(self):
        data = self.utils.adt.build()       # like ProxyUtils.push_adt: build, then write
        self.events.append(("push_adt",))
        self.iface.writemem(self.adt_addr, data)

    def _malloc(self, size):
        if self.malloc_error:
            raise Exception("proxy heap exhausted")
        addr = self.next_heap
        self.next_heap = (addr + size + 63) & ~63
        self.heap_events.append(("malloc", addr, size))
        return addr

    # helpers for assertions
    def of(self, kind):
        return [e for e in self.events if e[0] == kind]

    def writes_in(self, start, size):
        return [e for e in self.events if e[0] in ("write", "cwrite") and
                start <= e[1] < start + size]


def run_intree(target, image=None):
    image = image if image is not None else bytes((i * 13 + 1) & 0xFF for i in range(IMAGE_LEN))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        hv_launch.chainload_intree(target.iface, target.proxy, target.utils, image)
    return image, out.getvalue()


class UartTimeout(RuntimeError):
    """Same name and base class as m1n1.proxy.UartTimeout (UartError -> RuntimeError)."""


def python_types(t):
    """bootargs_types for chainload_python: the raw copy with only the top replaced."""
    return {3: SimpleNamespace(build=lambda tba: C.with_top_of_kernel_data(
        t.raw_ba, tba.top_of_kernel_data))}


def run_chainload(mode, t, image=None, control=False):
    """(Plan, output) of the real chainload function of the given mode against target t."""
    image = image if image is not None else bytes((i * 13 + 1) & 0xFF for i in range(IMAGE_LEN))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        if mode == "python":
            plan = hv_launch.chainload_python(t.iface, t.proxy, t.utils, image, blob_api(),
                                              python_types(t), control=control)
        else:
            plan = hv_launch.chainload_intree(t.iface, t.proxy, t.utils, image, control=control)
    return plan, out.getvalue()


def blob_api():
    def find(props, names, base):
        blobs, end = [], (base + 0x3FFF) & ~0x3FFF
        for name in names:
            value = props.get(name)
            if value is None or value == (0xFFFFFFFFFFFFFFFF,) * 2 or value[1] == 0:
                continue
            blobs.append((name, value[0], value[1], end))
            end = (end + value[1] + 0x3FFF) & ~0x3FFF
        return blobs, end

    def copy(p, blobs):
        for name, src, size, dst in blobs:
            p.memcpy8(dst, src, size)
    return (BOOT_BLOBS, find, copy, "T")


# === strip geometry =============================================================
class StripTests(unittest.TestCase):
    def test_contract_constants(self):
        self.assertEqual((C.BLOCK, C.PITCH, C.ORIGIN_X, C.ORIGIN_Y, C.SLOTS, C.COLOR),
                         (24, 28, 8, 4, 21, 0xFFFFFFFF))
        self.assertEqual((C.SLOT_HOST_GATE, C.SLOT_HOST_STAGED, C.SLOT_HOST_HANDOFF,
                          C.SLOT_STUB_ENTERED, C.SLOT_STUB, C.SLOT_M1N1_FIRST),
                         (0, 1, 2, 3, 4, 5))
        # slot 3 is the painting stub's entry mark; the bar (slots 0..4) covers it again
        self.assertFalse(hasattr(C, "SLOT_RESERVED"))
        self.assertEqual(C.STUB_BAR_SLOTS, 5)
        self.assertLessEqual(C.SLOT_STUB_ENTERED, C.SLOT_STUB)
        self.assertEqual(C.STUB_MARK_OFFSET, 3 * 28 * 4)       # 336 bytes from the strip origin
        self.assertEqual(C.STUB_MARK_OFFSET,
                         C.slot_address(video(), 3) - C.slot_address(video(), 0))
        self.assertEqual((C.STRIP_PIXELS, C.BAR_PIXELS), (20 * 28 + 24, 4 * 28 + 24))
        self.assertEqual((C.STRIP_PIXELS, C.BAR_PIXELS), (584, 136))
        self.assertEqual((C.m1n1_slot(0), C.m1n1_slot(15)), (5, 20))
        for step in (-1, 16):
            with self.assertRaises(ValueError):
                C.m1n1_slot(step)

    def test_rows_geometry_for_every_slot(self):
        v = video()
        seen = set()
        for slot in range(C.SLOTS):
            rows = C.paint_rows(v, slot)
            self.assertEqual(len(rows), 24)
            for r, (addr, data) in enumerate(rows):
                want = v.base + (4 + r) * v.stride + (8 + slot * 28) * 4
                self.assertEqual(addr, want)
                self.assertEqual(data, b"\xff" * 96)
                for px in range(24):
                    self.assertNotIn(addr + 4 * px, seen)
                    seen.add(addr + 4 * px)
        # hand-computed corner: slot 4, row 0, base 0x10003000000, stride 3200
        self.assertEqual(C.paint_rows(v, 4)[0][0], RAM + 0x3000000 + 4 * 3200 + (8 + 112) * 4)
        self.assertEqual(C.slot_address(v, 4), C.paint_rows(v, 4)[0][0])

    def test_depth_32_and_flag_bits_are_eligible(self):
        self.assertTrue(C.video_ok(video(depth=32)))
        self.assertTrue(C.video_ok(video(depth=30 | (1 << 16))))   # density/retina bits above 8
        self.assertTrue(C.video_ok(video(depth=0x1E | (0x80 << 8))))

    def test_every_guard_is_exact(self):
        ok = dict(base=RAM, stride=2384, width=596, height=28, depth=30)
        self.assertTrue(C.video_ok(SimpleNamespace(**ok)))
        bad = {"base": [0, RAM + 2, RAM + 1], "stride": [2383, 0], "width": [595, 0],
               "height": [27, 0], "depth": [24, 8, 31, 16, 0, 33]}
        for field, values in bad.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    v = SimpleNamespace(**dict(ok, **{field: value}))
                    self.assertFalse(C.video_ok(v))
                    self.assertEqual(C.paint_rows(v, 0), [])
        for slot in (-1, 21, 100):
            self.assertEqual(C.paint_rows(video(), slot), [])
        self.assertFalse(C.video_ok(SimpleNamespace(base=RAM)))      # missing attributes
        self.assertFalse(C.video_ok(None))

    def test_stub_paint_needs_aligned_stride(self):
        # the stub's origin is slot 0 (it clears the whole strip, then paints the bar)
        self.assertEqual(C.stub_paint(video()), (C.slot_address(video(), 0), 3200))
        self.assertEqual(C.slot_address(video(), 0), RAM + 0x3000000 + 4 * 3200 + 8 * 4)
        self.assertIsNone(C.stub_paint(video(stride=3201)))
        self.assertIsNone(C.stub_paint(video(base=0)))
        self.assertIsNone(C.stub_paint(video(width=100)))

    def test_strip_mode_follows_the_stub_predicate(self):
        self.assertEqual(C.strip_mode(video()), "bar")
        self.assertEqual(C.strip_mode(video(stride=3202)), "host")   # eligible, stub cannot store
        for bad in (video(base=0), video(width=100), video(depth=24), None):
            self.assertEqual(C.strip_mode(bad), "none")
        for v in (video(), video(stride=3202), video(base=0), video(depth=32)):
            self.assertEqual(C.strip_mode(v) == "bar", C.stub_paint(v) is not None)

    def test_video_report_is_hex_and_words(self):
        text = "\n".join(C.video_report(video(depth=30 | (1 << 16))))
        base = RAM + 0x3000000
        self.assertIn("framebuffer base 0x%x stride 0xc80 width 0x320 height 0x258" % base, text)
        self.assertIn("depth field 0x1001e, bpp 0x1e, RETINA flag (0x10000) set", text)
        self.assertIn("16K aligned: yes", text)
        self.assertIn("breadcrumb strip eligible for the host (video_ok): yes", text)
        self.assertIn("stub bar will paint (stub_paint): yes (strip origin 0x%x, row stride 0xc80)"
                      % C.slot_address(video(), 0), text)
        self.assertIn("new m1n1 will paint (its guard: stub_paint, stride <= 0x10000, height <= "
                      "0x4000): yes", text)
        text = "\n".join(C.video_report(video(base=RAM + 0x3000004, stride=3202, depth=32)))
        self.assertIn("RETINA flag (0x10000) clear", text)
        self.assertIn("16K aligned: no", text)
        self.assertIn("eligible for the host (video_ok): yes", text)
        self.assertIn("stub bar will paint (stub_paint): no", text)
        self.assertIn("height <= 0x4000): no", text)      # the new m1n1 rejects the same stride
        text = "\n".join(C.video_report(video(width=100)))
        self.assertIn("eligible for the host (video_ok): no", text)
        self.assertIn("stub bar will paint (stub_paint): no", text)
        self.assertIn("height <= 0x4000): no", text)
        self.assertEqual(len(C.video_report(None)), 1)
        for line in C.video_report(video()) + C.video_report(None):
            self.assertRegex(line, r"^[\x20-\x7e]*$")


# === copy stub ==================================================================
HV002_STUB = bytes.fromhex("2414c1a8" "441400a9" "227b0bd5" "22750bd5" "42400091" "634000d1"
                           "43ffffb5" "41000058" "20001fd6")   # hv002's: literal at offset 36


def assemble(source):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "s.s").write_text(source)
        subprocess.run(["clang", "-c", "-target", "arm64-apple-macos", "s.s", "-o", "s.o"],
                       cwd=d, check=True)
        text = subprocess.run(["otool", "-t", "s.o"], cwd=d, check=True,
                              capture_output=True, text=True).stdout
    words = [w for line in text.splitlines()[2:] for w in line.split()[1:]]
    return b"".join(struct.pack("<I", int(w, 16)) for w in words)


class StubTests(unittest.TestCase):
    ENTRY = 0x1122334455667788 & ~3
    PAINT = (0x10003001230, 3200)
    ROWS, STRIP_PX, BAR_PX = 24, 584, 136
    CODE = 192          # 48 words: entry mark, copy loop, barriers, clear pass, bar pass, jump
    TOTAL = 224         # code + the four-quad literal pool (<= C.STUB_MAX)

    def test_layout_of_each_variant(self):
        plain, painted = C.stub(self.ENTRY), C.stub(self.ENTRY, self.PAINT)
        self.assertEqual((len(plain), len(painted)), (56, self.TOTAL))
        self.assertEqual(len(C.STUB_PAINT_CODE), self.CODE)
        for code, pool in ((plain, 48), (painted, self.CODE)):
            self.assertEqual(pool % 8, 0)                  # literal pool starts 8-byte aligned
            self.assertEqual(len(code) - pool, 8 if code is plain else 32)
            self.assertEqual(struct.unpack_from("<Q", code, len(code) - 8)[0], self.ENTRY)
        self.assertEqual(struct.unpack_from("<QQQ", painted, self.CODE),
                         (self.PAINT[0], self.PAINT[1], C.COLOR))
        self.assertLessEqual(len(painted), C.STUB_MAX)

    def test_argument_validation(self):
        for entry in (-4, 1 << 64, 0x1002):
            with self.assertRaises(ValueError):
                C.stub(entry)
        for paint in ((0x1002, 3200), (0x1000, 3202), (0x1000, 0), (1 << 64, 4),
                      ((1 << 64) - 0x1000, 3200)):          # the rectangle would wrap
            with self.assertRaises(ValueError):
                C.stub(self.ENTRY, paint)

    @unittest.skipUnless(shutil.which("clang") and shutil.which("otool"), "clang/otool not available")
    def test_encoding_matches_assembler_byte_for_byte(self):
        top = ((1 << 64) - 1 - 23 * 0x2000 - 584 * 4) & ~3     # the highest origin that does not wrap
        for entry in (0x800000800, self.ENTRY, 0x10010db8800):
            plain = C.STUB_SOURCE.format(entry="0x%x" % entry)
            self.assertEqual(assemble(plain), C.stub(entry))
            for origin, stride in ((0x10003001230, 3200), (0x4, 4), (top, 0x2000)):
                src = C.stub_paint_source("0x%x" % origin, "0x%x" % stride, "0x%x" % C.COLOR,
                                          "0x%x" % entry)
                code = assemble(src)
                self.assertEqual(code, C.stub(entry, (origin, stride)))
                self.assertEqual(code[:len(C.STUB_PAINT_CODE)], C.STUB_PAINT_CODE)

    @unittest.skipUnless(shutil.which("clang") and shutil.which("otool"), "clang/otool not available")
    def test_source_geometry_comes_from_the_contract_constants(self):
        text = C.stub_paint_source(1, 2, 3, 4)
        for needle in ("add x7, x7, #336", "mov w10, #24", "mov w12, #24", "mov w8, #24",
                       "mov w10, #584", "mov w10, #136", "str w9, [x11], #4",
                       "str wzr, [x9], #4", "str w7, [x9], #4"):
            self.assertIn(needle, text)
        # entry mark first, then the copy loop, the clear pass, the bar, the final barrier, the jump
        mark, copy = text.index("str w9, [x11], #4"), text.index("ldp x5, x6")
        self.assertLess(mark, copy)
        self.assertLess(copy, text.index("str wzr"))
        self.assertLess(text.index("str wzr"), text.index("str w7"))
        self.assertLess(text.index("str w7"), text.rindex("dsb sy"))
        self.assertLess(text.rindex("dsb sy"), text.index("br x4"))

    def test_entry_mark_uses_only_x7_to_x13(self):
        """x0 (boot_args), x1-x3 (copy arguments) and x5/x6 (the copy loop) must be untouched."""
        mark = C._MARK_SOURCE.format(mark_off=C.STUB_MARK_OFFSET, block=C.BLOCK)
        registers = {int(n) for n in re.findall(r"\b[xw](\d+)\b", mark)}
        self.assertTrue(registers)
        self.assertTrue(registers <= set(range(7, 14)), registers)

    def execute(self, code, mem, regs, stub_addr=0x30000040):
        return run_stub(code, stub_addr, regs, mem, limit=2_000_000)

    def fixture(self, length=0x200, mem=None):
        mem = mem or Memory()
        src, dst, fb = 0x20000000, 0x40000000, 0x50000000
        data = bytes((i * 31 + 7) & 0xFF for i in range(length))
        mem.write(src, data)
        mem.write(fb, b"\x11" * (3200 * 40))
        return mem, src, dst, fb, data

    def test_copy_and_jump_without_paint(self):
        mem, src, dst, fb, data = self.fixture()
        regs = {0: 0xB00700, 1: src, 2: dst, 3: len(data)}
        x, log = self.execute(C.stub(self.ENTRY), mem, regs)
        self.assertEqual(mem.read(dst, len(data)), data)
        self.assertEqual(mem.read(fb, 3200 * 40), b"\x11" * (3200 * 40))   # nothing painted
        self.assertEqual([e for e in log if e[0] == "st"], [])             # no mark either
        self.assertEqual(log[-1], ("br", self.ENTRY))
        self.assertEqual(x[0], 0xB00700)               # boot_args pointer survives for _start
        self.assertEqual((x[1], x[2], x[3], x[4]), (src + len(data), dst + len(data), 0, self.ENTRY))
        self.assertEqual([e for e in log if e[0] == "dc"], [("dc", dst + 16 * i) for i in range(len(data) // 16)])
        self.assertEqual([e for e in log if e[0] == "ic"], [("ic", dst + 16 * i) for i in range(len(data) // 16)])
        tail = [e for e in log if e[0] in ("dsb", "isb")]
        self.assertEqual(tail, [("dsb", "ish"), ("isb",)])

    # -- the painting stub: entry mark, copy, clear the whole strip, one bar over slots 0-4
    def painted_run(self, code=None, stale_slots=(1, 7, 12, 20), length=0x200):
        mem, src, dst, fb, data = self.fixture(length)
        v = video(base=fb)
        # What boot021's redraw / an earlier chainload in this power cycle may have left.
        for slot in stale_slots:
            for addr, row in C.paint_rows(v, slot):
                mem.write(addr, row)
        before = mem.read(fb, 3200 * 40)
        regs = {0: 0xB00700, 1: src, 2: dst, 3: len(data)}
        x, log = self.execute(code or C.stub(self.ENTRY, C.stub_paint(v)), mem, regs)
        return mem, x, log, v, fb, before, src, dst, data

    def expected_strip(self, before, v, fb):
        want = bytearray(before)
        origin = C.slot_address(v, 0) - fb
        for r in range(self.ROWS):
            row = origin + r * v.stride
            want[row:row + self.STRIP_PX * 4] = bytes(self.STRIP_PX * 4)
            want[row:row + self.BAR_PX * 4] = b"\xff" * (self.BAR_PX * 4)
        return bytes(want)

    @staticmethod
    def mark_stores(v):
        """The 24 x 24 stores of the entry mark in slot 3, row-major, with their value."""
        return [(addr + 4 * c, 0xFFFFFFFF) for addr, _ in C.paint_rows(v, 3) for c in range(24)]

    def test_paint_variant_clears_the_strip_then_paints_one_bar(self):
        mem, x, log, v, fb, before, src, dst, data = self.painted_run()
        self.assertEqual(mem.read(dst, len(data)), data)               # copy semantics intact
        self.assertEqual(mem.read(fb, 3200 * 40), self.expected_strip(before, v, fb))
        # stale blocks in slots 5..20 are gone; stale slot 1 is simply covered by the bar
        for slot in (7, 12, 20):
            for addr, row in C.paint_rows(v, slot):
                self.assertEqual(mem.read(addr, 96), bytes(96))
        for addr, row in C.paint_rows(v, 1):
            self.assertEqual(mem.read(addr, 96), row)
        # exact store sequence: the 24 x 24 entry mark, 24 rows x 584 zeros (row-major), then
        # 24 rows x 136 white
        origin = C.slot_address(v, 0)
        want = self.mark_stores(v)
        want += [(origin + r * v.stride + 4 * c, 0) for r in range(24) for c in range(584)]
        want += [(origin + r * v.stride + 4 * c, 0xFFFFFFFF) for r in range(24) for c in range(136)]
        same_sequence(self, [(e[1], e[2]) for e in log if e[0] == "st"], want, "store sequence")
        # x0 survives, x1-x3 are still the copy loop's end state, the jump target is the entry
        self.assertEqual((x[0], x[1], x[2], x[3], x[4]),
                         (0xB00700, src + len(data), dst + len(data), 0, self.ENTRY))
        self.assertEqual(log[-1], ("br", self.ENTRY))
        # barriers: after the entry mark (sy), after the copy loop (ish, isb), once more before the jump (sy)
        self.assertEqual([e for e in log if e[0] in ("dsb", "isb")],
                         [("dsb", "sy"), ("dsb", "ish"), ("isb",), ("dsb", "sy")])

    def check_mark_precedes_the_copy(self, log, v):
        """The strict statement: nothing but the 576 mark stores and one dsb sy comes first."""
        first_copy = next(i for i, e in enumerate(log) if e[0] == "cp")
        same_sequence(self, [(e[1], e[2]) for e in log[:first_copy] if e[0] == "st"],
                      self.mark_stores(v), "stores before the first copied byte")
        self.assertEqual([e for e in log[:first_copy] if e[0] != "st"], [("dsb", "sy")])

    def test_entry_mark_is_painted_before_the_first_copied_byte_moves(self):
        mem, x, log, v, fb, before, *_ = self.painted_run()
        self.check_mark_precedes_the_copy(log, v)
        # ... and it is exactly slot 3's block: the first 576 stores, no other address
        stores = [e for e in log if e[0] == "st"]
        self.assertEqual({e[1] for e in stores[:576]},
                         {a + 4 * c for a, _ in C.paint_rows(v, 3) for c in range(24)})

    def test_clear_and_bar_happen_only_after_the_copy_loop_and_its_barriers(self):
        mem, x, log, v, fb, before, src, dst, data = self.painted_run()
        kinds = [e[0] for e in log]
        last = lambda kind: len(kinds) - 1 - kinds[::-1].index(kind)   # noqa: E731
        stores = [i for i, k in enumerate(kinds) if k == "st"]
        mark, rest = stores[:576], stores[576:]
        self.assertEqual(len(rest), 24 * 584 + 24 * 136)
        first_copy, last_copy = kinds.index("cp"), last("cp")
        dsb_ish, isb = log.index(("dsb", "ish")), log.index(("isb",))
        dsb_sy = last("dsb")
        self.assertLess(mark[-1], first_copy)              # the entry mark precedes the copy loop
        self.assertLess(last_copy, dsb_ish)
        self.assertLess(dsb_ish, isb)
        self.assertLess(isb, rest[0])                      # clear pass only after copy + barriers
        self.assertLess(rest[-1], dsb_sy)                  # and drained before the jump
        self.assertEqual(kinds[-2:], ["dsb", "br"])
        # mark and bar are white, the clear pass in between is all zeros
        values = [e[2] for e in log if e[0] == "st"]
        same_sequence(self, values, [0xFFFFFFFF] * 576 + [0] * (24 * 584) + [0xFFFFFFFF] * (24 * 136),
                      "stored values")
        # no store at all touches memory outside the strip rectangle
        rect = {C.slot_address(v, 0) + r * v.stride + 4 * c for r in range(24) for c in range(584)}
        self.assertEqual({e[1] for e in log if e[0] == "st"}, rect)

    def test_entry_mark_survives_a_fault_in_the_copy_loop_and_no_bar_appears(self):
        """'Slot 3 lit, no bar' is what a stub that was entered but faulted in its copy loop leaves."""
        mem, src, dst, fb, data = self.fixture()
        v = video(base=fb)
        before = mem.read(fb, 3200 * 40)
        regs = {0: 0xB00700, 1: src + 4, 2: dst, 3: len(data)}     # unaligned source: Device fault
        with self.assertRaises(AlignmentFault):
            self.execute(C.stub(self.ENTRY, C.stub_paint(v)), mem, regs)
        want = bytearray(before)
        for addr, row in C.paint_rows(v, 3):
            want[addr - fb:addr - fb + 96] = row
        self.assertEqual(mem.read(fb, 3200 * 40), bytes(want))      # slot 3 white, nothing else
        for addr, row in C.paint_rows(v, 3):
            self.assertEqual(mem.read(addr, 96), row)
        for slot in (0, 1, 2, 4, 5, 20):                            # no bar, no other block
            for addr, row in C.paint_rows(v, slot):
                self.assertEqual(mem.read(addr, 96), b"\x11" * 96)
        self.assertEqual(mem.read(dst, len(data)), bytes(len(data)))   # nothing copied
        # the plain stub has no mark: the same fault leaves the screen untouched
        mem, src, dst, fb, data = self.fixture()
        with self.assertRaises(AlignmentFault):
            self.execute(C.stub(self.ENTRY), mem, {1: src + 4, 2: dst, 3: len(data)})
        self.assertEqual(mem.read(fb, 3200 * 40), b"\x11" * (3200 * 40))

    @unittest.skipUnless(shutil.which("clang") and shutil.which("otool"), "clang/otool not available")
    def test_mutation_entry_mark_after_the_copy_loop_or_missing_is_caught(self):
        fb = 0x50000000
        origin = C.slot_address(video(base=fb), 0)
        fmt = dict(mark_off=C.STUB_MARK_OFFSET, block=C.BLOCK, rows=C.BLOCK, strip_px=C.STRIP_PIXELS,
                   bar_px=C.BAR_PIXELS, origin=origin, stride=3200, color=C.COLOR, entry=self.ENTRY)
        # the real order passes the checker
        mem, x, log, v, fb, before, *_ = self.painted_run()
        self.check_mark_precedes_the_copy(log, v)
        # the mark placed after the copy loop (but before the clear pass) is caught; so is no
        # mark at all (the previous stub). Neither changes the success state on the screen,
        # which is exactly why only the order check can tell them apart.
        late = (C._COPY_SOURCE + C._MARK_SOURCE + C._PAINT_TAIL_SOURCE).format(**fmt)
        none = (C._COPY_SOURCE + C._PAINT_TAIL_SOURCE).format(**fmt)
        for name, source in (("mark after the copy loop", late), ("no mark", none)):
            with self.subTest(name):
                mem, x, log, v, fb, before, *_ = self.painted_run(code=assemble(source))
                with self.assertRaises(AssertionError):
                    self.check_mark_precedes_the_copy(log, v)
                self.assertEqual(mem.read(fb, 3200 * 40), self.expected_strip(before, v, fb))

    def test_bar_covers_slots_0_to_4_and_the_gaps_between_them(self):
        mem, x, log, v, fb, before, *_ = self.painted_run(stale_slots=())
        for slot in range(5):                                          # incl. slot 3 (entry mark)
            for addr, row in C.paint_rows(v, slot):
                self.assertEqual(mem.read(addr, 96), row)
        for r in range(24):                                            # the 4-pixel gaps are lit too
            for slot in range(4):
                gap = C.slot_address(v, slot) + r * v.stride + 24 * 4
                self.assertEqual(mem.read(gap, 16), b"\xff" * 16)
        # slots 5..20 are cleared, not lit: only the new m1n1 may light them
        for slot in range(5, 21):
            for addr, row in C.paint_rows(v, slot):
                self.assertEqual(mem.read(addr, 96), bytes(96))
        # one pixel past the strip (right, left, above, below) is untouched
        self.assertEqual(mem.read(C.slot_address(v, 5) - 4, 4), bytes(4))     # gap before slot 5
        self.assertEqual(mem.read(C.slot_address(v, 20) + 24 * 4, 4), b"\x11" * 4)
        self.assertEqual(mem.read(C.slot_address(v, 0) - 4, 4), b"\x11" * 4)
        self.assertEqual(mem.read(C.slot_address(v, 0) - 4 * 3200, 4), b"\x11" * 4)   # row above
        self.assertEqual(mem.read(C.slot_address(v, 0) + 24 * 3200, 4), b"\x11" * 4)  # row below

    def test_stale_blocks_from_an_earlier_chainload_cannot_survive(self):
        everything = tuple(range(21))
        mem, x, log, v, fb, before, *_ = self.painted_run(stale_slots=everything)
        self.assertEqual(mem.read(fb, 3200 * 40), self.expected_strip(before, v, fb))
        for slot in range(5, 21):
            self.assertEqual(mem.read(C.slot_address(v, slot), 96), bytes(96))

    def test_mutation_clear_pass_as_narrow_as_the_bar_leaves_stale_blocks(self):
        words = list(struct.unpack("<%dI" % (len(C.STUB_PAINT_CODE) // 4), C.STUB_PAINT_CODE))
        self.assertEqual(words.count(0x5280490a), 1)                   # mov w10, #584: the clear pass
        words[words.index(0x5280490a)] = 0x5280110a                    # mov w10, #136
        fb = 0x50000000
        pool = C.stub(self.ENTRY, (C.slot_address(video(base=fb), 0), 3200))[len(C.STUB_PAINT_CODE):]
        code = struct.pack("<%dI" % len(words), *words) + pool
        mem, x, log, v, fb, before, *_ = self.painted_run(code=code)
        self.assertNotEqual(mem.read(fb, 3200 * 40), self.expected_strip(before, v, fb))
        self.assertNotEqual(mem.read(C.slot_address(v, 7), 96), bytes(96))   # stale slot 7 survived
        # the unmutated stub, same fixture, is clean
        mem, x, log, v, fb, before, *_ = self.painted_run()
        self.assertEqual(mem.read(C.slot_address(v, 7), 96), bytes(96))

    def test_every_literal_load_is_8_byte_aligned_at_any_64_byte_stub_address(self):
        # The stub runs with the MMU off (Device memory): an unaligned 8-byte
        # load faults. The emulator raises AlignmentFault for any such access.
        for painted in (False, True):
            for stub_addr in (0x30000000, 0x30000040, 0x10010DB8240):
                mem, src, dst, fb, data = self.fixture(0x40)
                paint = (fb + 4 * 3200 + 8 * 4, 3200) if painted else None
                self.execute(C.stub(self.ENTRY, paint), mem,
                             {0: 1, 1: src, 2: dst, 3: len(data)}, stub_addr=stub_addr)

    def test_a_stub_at_a_4_mod_8_address_would_fault_like_hv002(self):
        # Why the staging block's 8-byte alignment is a gate (check_layout). The first
        # instruction of the painting stub is a literal load, so it faults before it paints
        # anything: the screen stays blank, as in the hv002 session.
        for paint in (None, (0x50000000 + 4 * 3200 + 8 * 4, 3200)):
            mem, src, dst, fb, data = self.fixture(0x40)
            with self.assertRaises(AlignmentFault):
                self.execute(C.stub(self.ENTRY, paint), mem,
                             {0: 1, 1: src, 2: dst, 3: len(data)}, stub_addr=0x30000044)
            self.assertEqual(mem.read(fb, 3200 * 40), b"\x11" * (3200 * 40))
            if paint is not None:        # faulted at its first instruction: nothing happened at all
                self.assertEqual(mem.read(dst, len(data)), bytes(len(data)))

    def test_hv002_stub_would_have_faulted(self):
        """The previous stub's literal sat at offset 36: unaligned under MMU off."""
        mem, src, dst, fb, data = self.fixture(0x40)
        code = HV002_STUB + struct.pack("<Q", self.ENTRY)
        with self.assertRaises(AlignmentFault):
            self.execute(code, mem, {0: 1, 1: src, 2: dst, 3: len(data)}, stub_addr=0x10010DB8240)

    def test_emulator_rejects_a_mutated_stub(self):
        mem, src, dst, fb, data = self.fixture(0x40)
        bad = bytearray(C.stub(self.ENTRY))
        struct.pack_into("<I", bad, 12, 0xD4200000)   # brk: not an instruction we model
        with self.assertRaises(AssertionError):
            self.execute(bytes(bad), mem, {1: src, 2: dst, 3: len(data)})

    # -- item 18: the copy length and the room behind the image
    def test_copy_length_must_be_a_positive_multiple_of_16(self):
        for good in (16, 0x4000, 0x7C8000):
            self.assertEqual(C.check_copy_length(good), good)
        for bad in (0, -16, 8, 17, 0x4001, 0x4000 + 8):
            with self.subTest(length=bad), self.assertRaises(ValueError):
                C.check_copy_length(bad)

    def test_plan_construction_rejects_a_copy_length_that_never_reaches_zero(self):
        ok = C.plan_with_blobs(0x1000, BASE, (RAM, 0x4000), 0x4000, 0x8000, 0xC000)
        self.assertEqual(ok.image_size, 0xC000)
        for size in (0, -0x4000, 0xC008, 0xC001):
            with self.subTest(size=size), self.assertRaises(ValueError):
                C.plan_with_blobs(0x1000, BASE, (RAM, 0x4000), 0x4000, 0x8000, size)
        self.assertEqual(C.Plan(0x1000, BASE, None, 0, 0, 0x10, False).image_size, 0x10)
        with self.assertRaises(ValueError):
            C.Plan(0x1000, BASE, None, 0, 0, 0x18, False)
        for size in (1, 0xFFF1, 0x3FFF):                  # plan_layout always aligns: still a multiple
            self.assertEqual(C.plan_layout(size, BASE, (RAM, 0x4001)).image_size % 16, 0)

    def test_a_copy_length_that_is_not_a_multiple_of_16_never_ends(self):
        """Why: sub x3, x3, #16 skips over 0, so cbnz never falls through."""
        mem, src, dst, fb, data = self.fixture(0x40)
        with self.assertRaisesRegex(AssertionError, "did not finish"):
            run_stub(C.stub(self.ENTRY), 0x30000040, {0: 1, 1: src, 2: dst, 3: 24}, mem, limit=5000)
        mem, src, dst, fb, data = self.fixture(0x40)
        run_stub(C.stub(self.ENTRY), 0x30000040, {0: 1, 1: src, 2: dst, 3: 32}, mem, limit=5000)

    def test_stub_size_check(self):
        code = C.stub(self.ENTRY, self.PAINT)
        self.assertIs(C.check_stub_size(code), code)
        exact = bytes(C.STUB_MAX)
        self.assertIs(C.check_stub_size(exact), exact)
        with self.assertRaisesRegex(ValueError, "more than the %d bytes reserved" % C.STUB_MAX):
            C.check_stub_size(bytes(C.STUB_MAX + 1))
        with self.assertRaises(ValueError):
            C.check_stub_size(bytes(C.STUB_MAX + 8))


# === layout arithmetic and gates ===================================================
def facts(**kw):
    values = dict(adt=(RAM + 0x2000000, 0x1000), boot_args=(RAM + 0x1FF0000, 0x480),
                  framebuffer=(RAM + 0x3000000, 3200 * 600), staging=(RAM + 0x20000000, 0x30000),
                  ram=(RAM, RAM_SIZE), memory_map={})
    values.update(kw)
    return C.Facts(**values)


class LayoutTests(unittest.TestCase):
    def test_hand_computed_numbers(self):
        # 0x10000 + 4 -> 0x14000; SEPFW 0x8000 -> 0x1c000; + 0x4000 boot_args.
        p = C.plan_layout(0x10000, BASE, (RAM + 0x6000000, 0x8000))
        self.assertEqual((p.sepfw_off, p.bootargs_off, p.image_size), (0x14000, 0x1C000, 0x20000))
        self.assertEqual((p.region, p.entry, p.overflow), ((BASE, 0x20000), BASE + 0x800, False))
        # the real boot021 object: 0x3c0000 is already 16K aligned but +4 pushes it on.
        p = C.plan_layout(3932160, BASE, (RAM + 0x6000000, 0x400000))
        self.assertEqual((p.sepfw_off, p.bootargs_off, p.image_size),
                         (0x3C4000, 0x7C4000, 0x7C8000))
        # SEPFW size that is not a multiple of 16K rounds up: 0x4000 + 0x4001 -> 0xc000
        p = C.plan_layout(0x1000, BASE, (RAM, 0x4001))
        self.assertEqual((p.sepfw_off, p.bootargs_off, p.image_size), (0x4000, 0xC000, 0x10000))
        # exact multiples stay put
        p = C.plan_layout(0x3FFC, BASE, (RAM, 0x4000))
        self.assertEqual((p.sepfw_off, p.bootargs_off), (0x4000, 0x8000))
        p = C.plan_layout(0x3FFD, BASE, (RAM, 0x4000))
        self.assertEqual((p.sepfw_off, p.bootargs_off), (0x8000, 0xC000))

    def test_matches_src_chainload_c(self):
        """Independent transcription of chainload_image() with no variables."""
        for size in (0x10000, 0x3C0000, 0x3FFC, 0x3FFD, 1):
            for sepfw in (0x1, 0x4000, 0x4001, 0x123456):
                image_size = (size + 4 + 0x3FFF) & ~0x3FFF
                off = image_size
                image_size = (image_size + sepfw + 0x3FFF) & ~0x3FFF
                bootargs = image_size
                image_size += 0x4000
                p = C.plan_layout(size, BASE, (RAM, sepfw))
                self.assertEqual((p.sepfw_off, p.bootargs_off, p.image_size), (off, bootargs, image_size))

    def test_overflow_and_missing_sepfw(self):
        p = C.plan_layout(0x10000, BASE, (RAM, 0xFFFFFFFFFFFFFFFF))
        self.assertTrue(p.overflow)
        p = C.plan_layout(0x10000, (1 << 64) - 0x1000, (RAM, 0x8000))
        self.assertTrue(p.overflow)
        p = C.plan_layout(0x10000, BASE, None)
        self.assertEqual((p.sepfw, p.overflow, p.image_size), (None, False, 0x14000 + 0x4000))
        p = C.plan_layout(0x10000, BASE, (0xFFFFFFFFFFFFFF00, 0x8000))
        self.assertTrue(p.overflow)

    def plan(self, **kw):
        return C.plan_layout(0x10000, kw.pop("base", BASE), kw.pop("sepfw", (RAM + 0x6000000, 0x8000)))

    def test_clean_layout_has_no_problems(self):
        problems, notes = C.check_layout(self.plan(), facts())
        self.assertEqual((problems, notes), ([], []))

    def test_each_overlap_fires_and_adjacency_does_not(self):
        plan = self.plan()           # destination [BASE, BASE + 0x20000)
        end = BASE + 0x20000
        cases = {
            "adt": ("destination overlaps the ADT", "adt"),
            "framebuffer": ("destination overlaps the framebuffer", "framebuffer"),
        }
        for key, (message, field) in cases.items():
            for start, size, fires in ((BASE - 0x100, 0x101, True), (BASE + 0x1FFFF, 0x1000, True),
                                       (BASE + 0x8000, 0x10, True), (BASE - 0x1000, 0x1000, False),
                                       (end, 0x1000, False), (BASE, 0, False)):
                with self.subTest(key=key, start=start, size=size):
                    problems, _ = C.check_layout(plan, facts(**{field: (start, size)}))
                    self.assertEqual(any(message in p for p in problems), fires, problems)
        # framebuffer absent (base 0): no problem, no crash
        self.assertEqual(C.check_layout(plan, facts(framebuffer=None))[0], [])

    NOTE_BOOT_ARGS = ("live boot_args lies inside the destination; it will be overwritten, "
                      "m1n1 already copied it")

    def test_boot_args_inside_the_destination_is_a_note_not_a_problem(self):
        """The new m1n1 uses the staged COPY; iBoot's original of a FIRST chainload is dead."""
        plan = self.plan()           # destination [BASE, BASE + 0x20000), boot_args copy at +0x1C000
        end = BASE + 0x20000
        for start, size in ((BASE + 0x2000, 0x480), (BASE, 0x480), (BASE - 0x100, 0x480),
                            (BASE + 0x1C008, 0x480),           # 8 bytes off the planned address
                            (BASE + 0x1BFF8, 0x480), (end - 1, 0x480)):
            with self.subTest(start=start):
                problems, notes = C.check_layout(plan, facts(boot_args=(start, size)))
                self.assertEqual(problems, [])
                self.assertEqual(notes, [self.NOTE_BOOT_ARGS])
        # adjacent or apart: neither a note nor a problem
        for start in (BASE - 0x480, end, end + 0x1000, RAM + 0x1FF0000):
            problems, notes = C.check_layout(plan, facts(boot_args=(start, 0x480)))
            self.assertEqual((problems, notes), ([], []), start)
        # absent boot_args: no crash, nothing to say
        self.assertEqual(C.check_layout(plan, facts(boot_args=None)), ([], []))

    def test_boot_args_at_the_planned_address_is_the_second_chainload_problem(self):
        plan = self.plan()
        self.assertEqual(plan.new_base + plan.bootargs_off, BASE + 0x1C000)
        problems, notes = C.check_layout(plan, facts(boot_args=(BASE + 0x1C000, 0x480)))
        self.assertEqual(problems, ["destination overlaps the boot_args at the planned boot_args address"])
        self.assertEqual(notes, [])
        # the signature is the address of THIS plan: the python flow stages at +0x24000
        pplan = C.plan_with_blobs(0x10000, BASE, (RAM + 0x6000000, 0x8000), 0x14000, 0x24000, 0x28000)
        problems, notes = C.check_layout(pplan, facts(boot_args=(BASE + 0x1C000, 0x480)))
        self.assertEqual((problems, notes), ([], [self.NOTE_BOOT_ARGS]))
        problems, _ = C.check_layout(pplan, facts(boot_args=(BASE + 0x24000, 0x480)))
        self.assertEqual(problems, ["destination overlaps the boot_args at the planned boot_args address"])
        # staging that overlaps the live boot_args stays a problem in every case
        problems, _ = C.check_layout(plan, facts(boot_args=(RAM + 0x1FF0000, 0x480),
                                                 staging=(RAM + 0x1FF0100, 0x1000)))
        self.assertTrue(any("staging block overlaps the boot_args" in p for p in problems))

    def test_sepfw_already_at_the_planned_address_is_a_note(self):
        note = ("SEPFW already points at the planned relocation address; if this is not the first "
                "run since power-on, a previous chainload patched this ADT: power off completely")
        planned = BASE + 0x14000
        problems, notes = C.check_layout(C.plan_layout(0x10000, BASE, (planned, 0x8000)), facts())
        self.assertEqual((problems, notes), ([], [note]))
        for other in (planned + 8, planned - 8, RAM + 0x6000000):
            problems, notes = C.check_layout(C.plan_layout(0x10000, BASE, (other, 0x8000)), facts())
            self.assertEqual((problems, notes), ([], []), other)
        # python flow: the planned relocation address is its own sepfw offset
        pplan = C.plan_with_blobs(0x10000, BASE, (BASE + 0x18000, 0x8000), 0x18000, 0x20000, 0x24000)
        self.assertEqual(C.check_layout(pplan, facts())[1], [note])
        # invalid SEPFW values never produce the note
        for sepfw in (None, (planned, 0), (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)):
            problems, notes = C.check_layout(C.plan_layout(0x10000, BASE, sepfw), facts())
            self.assertTrue(problems)
            self.assertNotIn(note, notes)

    def test_table_marks_the_two_earlier_chainload_signatures(self):
        planned = C.plan_layout(0x10000, BASE, (BASE + 0x14000, 0x8000))
        text = C.layout_table(planned, facts())
        self.assertRegex(text, r"SEPFW \(current\)\s+0x[0-9a-f]{16} 0x[0-9a-f]{16} 0x8000\s+"
                               r"AT THE PLANNED RELOCATION ADDRESS")
        plain = C.layout_table(self.plan(), facts())
        self.assertNotIn("PLANNED RELOCATION", plain)
        self.assertNotIn("PLANNED boot_args", plain)
        inside = C.layout_table(self.plan(), facts(boot_args=(BASE + 0x2000, 0x480)))
        self.assertRegex(inside, r"boot_args \(live\).*OVERLAPS DESTINATION \(note: overwritten, "
                                 r"already copied\)")
        again = C.layout_table(self.plan(), facts(boot_args=(BASE + 0x1C000, 0x480)))
        self.assertRegex(again, r"boot_args \(live\).*AT THE PLANNED boot_args ADDRESS")
        for line in (text + again + inside).splitlines():
            self.assertRegex(line, r"^[\x20-\x7e]*$")

    # --- the staging block against the destination (item 20) -----------------------------
    STAGING_NOTE_TEXT = ("destination overlaps the start of the staging block; safe: ascending "
                         "copy, destination below staging, stub above destination end")
    STAGING_SIZE = 0x20000 + 0x100          # image_size + STUB_MAX of the default plan

    def test_destination_below_staging_overlap_is_one_note_not_a_problem(self):
        """src/chainload.c: _base + image_size above top, malloc'd buffer at top, ascending copy."""
        plan = self.plan()           # destination [BASE, BASE + 0x20000); the stub sits at staging + 0x20000
        for start in (BASE + 8, BASE + 0x1000, BASE + 0x8000, BASE + 0x1FFC0, BASE + 0x1FFF8):
            with self.subTest(start=hex(start)):
                problems, notes = C.check_layout(plan, facts(staging=(start, self.STAGING_SIZE)))
                self.assertEqual(problems, [])
                self.assertEqual(notes, [self.STAGING_NOTE_TEXT])
        # touching or apart: neither a note nor a problem
        for start in (BASE + 0x20000, BASE + 0x20008, RAM + 0x20000000):
            problems, notes = C.check_layout(plan, facts(staging=(start, self.STAGING_SIZE)))
            self.assertEqual((problems, notes), ([], []), hex(start))

    def test_destination_at_or_above_staging_start_is_a_problem(self):
        plan = self.plan()
        message = "destination overlaps the staging block"
        for start, why in ((BASE, "identical start"),
                           (BASE - 8, "staging starts 8 bytes below the destination"),
                           (BASE - 0x1000, "staging starts below and reaches in"),
                           (BASE - self.STAGING_SIZE + 8, "staging reaches 8 bytes into the destination")):
            with self.subTest(why):
                problems, notes = C.check_layout(plan, facts(staging=(start, self.STAGING_SIZE)))
                self.assertEqual(len(problems), 1, problems)
                self.assertTrue(problems[0].startswith(message), problems)
                self.assertIn("ascending copy would overwrite source bytes before reading them",
                              problems[0])
                self.assertNotIn(self.STAGING_NOTE_TEXT, notes)
        # the staging block that ends exactly at the destination start is clear
        problems, notes = C.check_layout(plan, facts(staging=(BASE - self.STAGING_SIZE, self.STAGING_SIZE)))
        self.assertEqual((problems, notes), ([], []))

    def test_a_destination_below_staging_always_ends_below_the_stub(self):
        for image_size in (0x4000, 0x20000, 0x28000, 0x7C8000):
            plan = C.Plan(0x1000, BASE, (RAM, 0x1000), 0x4000, image_size - 0x4000, image_size, False)
            for delta in (8, 16, 0x1000, image_size - 8, image_size, image_size + 0x100):
                staging = (BASE + delta, image_size + C.STUB_MAX)
                stub = staging[0] + plan.image_size
                self.assertLess(plan.new_base + plan.image_size, stub)       # the invariant itself
                state, reason = C.classify_staging_overlap(plan, staging)
                self.assertEqual((state, reason), ("safe", None) if delta < image_size
                                 else ("none", None), (image_size, delta))
        # the second clause of the rule is not dead code: a stub below the destination end
        plan = self.plan()
        state, reason = C.classify_staging_overlap(plan, (BASE + 0x1000, self.STAGING_SIZE),
                                                   stub_address=BASE + 0x1F000)
        self.assertEqual(state, "unsafe")
        self.assertIn("overwrite the copy stub", reason)
        # and with the stub where the launcher puts it, it is not hit
        self.assertEqual(C.classify_staging_overlap(plan, (BASE + 0x1000, self.STAGING_SIZE))[0], "safe")

    def test_python_plan_gets_the_same_staging_rule(self):
        pplan = C.plan_with_blobs(0x10000, BASE, (RAM + 0x6000000, 0x8000), 0x14000, 0x24000, 0x28000)
        size = 0x28000 + 0x100
        problems, notes = C.check_layout(pplan, facts(staging=(BASE + 0x2000, size)),
                                         moved=("SEPFW", "RAMDisk"))
        self.assertEqual((problems, notes), ([], [self.STAGING_NOTE_TEXT]))
        for start in (BASE, BASE - 0x1000):
            problems, _ = C.check_layout(pplan, facts(staging=(start, size)))
            self.assertEqual(len(problems), 1)
            self.assertTrue(problems[0].startswith("destination overlaps the staging block"))
        # the stub of the python plan is at staging + 0x28000: a destination below staging ends
        # below it, whatever the offsets inside the image are
        state, _ = C.classify_staging_overlap(pplan, (BASE + 0x27FF8, size))
        self.assertEqual(state, "safe")

    def test_staging_below_top_of_kernel_data_keeps_the_hard_problem(self):
        """The ascending-copy argument covers the stub's loop. The host also WRITES the staging
        block before the handoff, so a block that lies below top_of_kernel_data (inside live
        kernel data: the running m1n1's image, blobs) is still refused."""
        plan = self.plan()
        staging = (BASE + 0x1000, self.STAGING_SIZE)
        self.assertEqual(C.check_layout(plan, facts(staging=staging)),
                         ([], [self.STAGING_NOTE_TEXT]))                  # top unknown: as specified
        for top in (BASE, BASE + 0x1000):                                  # block at or above the top
            self.assertEqual(C.check_layout(plan, facts(staging=staging, top=top)),
                             ([], [self.STAGING_NOTE_TEXT]), hex(top))
        for top in (BASE + 0x1001, BASE + 0x20000, RAM + 0x1800000):       # block below the top
            problems, notes = C.check_layout(plan, facts(staging=staging, top=top))
            self.assertEqual(len(problems), 1, hex(top))
            self.assertIn("staging block lies below top_of_kernel_data, inside live kernel data",
                          problems[0])
            self.assertEqual(notes, [])
        # no overlap with the destination: a block below the top is refused all the same, a block
        # at or above it is clean
        problems, notes = C.check_layout(plan, facts(staging=(RAM + 0x20000000, 0x30000),
                                                     top=RAM + 0x30000000))
        self.assertEqual((len(problems), notes), (1, []))
        self.assertIn("staging block lies below top_of_kernel_data, inside live kernel data",
                      problems[0])
        self.assertEqual(C.check_layout(plan, facts(staging=(RAM + 0x20000000, 0x30000),
                                                    top=RAM + 0x20000000)), ([], []))

    def test_mutations_of_the_staging_rule_are_caught(self):
        plan = self.plan()

        def old_rule(plan, staging, stub_address=None):               # every overlap is a problem
            if staging is None or not C.overlaps(plan.region, staging):
                return C.STAGING_NONE, None
            return C.STAGING_UNSAFE, "overlap"

        def no_rule(plan, staging, stub_address=None):               # nothing is ever a problem
            return C.STAGING_SAFE if staging and C.overlaps(plan.region, staging) else \
                C.STAGING_NONE, None

        def below(self_test):
            problems, notes = C.check_layout(plan, facts(staging=(BASE + 0x1000, self.STAGING_SIZE)))
            self_test.assertEqual((problems, notes), ([], [self_test.STAGING_NOTE_TEXT]))

        def at_or_above(self_test):
            problems, _ = C.check_layout(plan, facts(staging=(BASE, self.STAGING_SIZE)))
            self_test.assertEqual(len(problems), 1)
        below(self)
        at_or_above(self)                                            # the real rule passes both
        with patch.object(C, "classify_staging_overlap", old_rule):
            with self.assertRaises(AssertionError):
                below(self)
        with patch.object(C, "classify_staging_overlap", no_rule):
            with self.assertRaises(AssertionError):
                at_or_above(self)

    def test_table_marks_the_staging_row(self):
        plan = self.plan()
        line = lambda text: next(l for l in text.splitlines() if l.startswith("staging block"))  # noqa: E731
        safe = line(C.layout_table(plan, facts(staging=(BASE + 0x1000, self.STAGING_SIZE))))
        self.assertTrue(safe.endswith("OVERLAPS DESTINATION START (note: ascending copy, safe)"), safe)
        unsafe = line(C.layout_table(plan, facts(staging=(BASE, self.STAGING_SIZE))))
        self.assertTrue(unsafe.endswith("OVERLAPS DESTINATION"), unsafe)
        apart = line(C.layout_table(plan, facts()))
        self.assertNotIn("OVERLAPS", apart)
        self.assertNotIn("OVERLAPS", line(C.layout_table(plan, facts(staging=None))))

    def test_staging_must_stay_clear_of_the_live_structures(self):
        plan = self.plan()
        for field, label in (("adt", "ADT"), ("boot_args", "boot_args"), ("framebuffer", "framebuffer")):
            f = facts(staging=getattr(facts(), field))
            problems, _ = C.check_layout(plan, f)
            self.assertTrue(any("staging block overlaps the " + label in p for p in problems), problems)
        problems, _ = C.check_layout(plan, facts(staging=None))
        self.assertTrue(any("could not be allocated" in p for p in problems))
        problems, _ = C.check_layout(plan, facts(staging=(RAM + RAM_SIZE - 0x10, 0x1000)))
        self.assertTrue(any("staging block lies outside RAM" in p for p in problems))

    def test_out_of_ram(self):
        plan = self.plan()
        for ram, fires in (((BASE, 0x20000), False),                 # exactly the destination
                           ((BASE, 0x1FFFF), True), ((BASE + 1, 0x20000), True),
                           ((RAM, RAM_SIZE), False), ((RAM + 0x4000000, RAM_SIZE), True),
                           ((RAM, 0), True)):
            with self.subTest(ram=ram):
                problems, _ = C.check_layout(plan, facts(ram=ram, staging=(BASE + 0x100000, 0x1000)))
                self.assertEqual(any("outside RAM" in p and "destination" in p or "RAM range unknown" in p
                                     for p in problems), fires, problems)

    def test_sepfw_problems(self):
        base = facts()
        p, _ = C.check_layout(C.plan_layout(0x10000, BASE, None), base)
        self.assertEqual([x for x in p if "SEPFW" in x], ["SEPFW is missing from the memory map"])
        p, _ = C.check_layout(C.plan_layout(0x10000, BASE, (RAM + 0x6000000, 0)), base)
        self.assertEqual([x for x in p if "SEPFW" in x], ["SEPFW has size 0"])
        sentinel = (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
        p, _ = C.check_layout(C.plan_layout(0x10000, BASE, sentinel), base)
        self.assertTrue(any("sentinel" in x for x in p))
        self.assertTrue(any("overflow" in x for x in p))    # arithmetic is flagged as well
        p, _ = C.check_layout(C.plan_layout(0x10000, (1 << 64) - 0x1000, (RAM, 0x8000)), base)
        self.assertEqual([x for x in p if "overflow" in x], ["layout arithmetic overflows 64 bits"])
        p, _ = C.check_layout(self.plan(), base)
        self.assertEqual(p, [])

    def test_alignment_gates_for_the_mmu_off_stub(self):
        problems, _ = C.check_layout(self.plan(base=BASE + 4), facts())
        self.assertTrue(any("not 8-byte aligned" in p for p in problems))
        problems, _ = C.check_layout(self.plan(), facts(staging=(RAM + 0x20000004, 0x30000)))
        self.assertTrue(any("staging block is not 8-byte aligned" in p for p in problems))

    def test_notes_name_overwritten_blobs(self):
        mm = {"SEPFW": (RAM + 0x6000000, 0x8000),               # moved: never a note
              "TrustCache": (BASE + 0x8000, 0x4000),             # inside
              "uStuff": (BASE - 0x10, 0x20),                     # straddles the start
              "preoslog": (BASE + 0x1FFF0, 0x100),               # straddles the end
              "RAMDisk": (BASE + 0x20000, 0x100),                # adjacent: no note
              "Zero": (BASE + 0x10, 0),                          # empty: no note
              "Gone": (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF),  # unset sentinel: no note
              "we ird\nname": (BASE + 0x10, 0x10)}
        problems, notes = C.check_layout(self.plan(), facts(memory_map=mm))
        self.assertEqual(problems, [])
        text = "\n".join(notes)
        for name, size in (("TrustCache", 0x4000), ("uStuff", 0x20), ("preoslog", 0x100)):
            self.assertIn("%s (0x%x bytes" % (name, size), text)
        self.assertEqual(len(notes), 4)
        for absent in ("RAMDisk", "Zero", "Gone", "SEPFW"):
            self.assertNotIn(absent, text)
        self.assertIn("we?ird?name", text)                       # sanitized
        # a flow that relocates a blob does not claim to overwrite it
        _, notes = C.check_layout(self.plan(), facts(memory_map=mm), moved=("SEPFW", "TrustCache"))
        self.assertNotIn("TrustCache", "\n".join(notes))

    def test_table_is_sanitized_hex(self):
        mm = {"TrustCache": (BASE + 0x8000, 0x4000), "Other": (RAM + 0x7000000, 0x10)}
        text = C.layout_table(self.plan(), facts(memory_map=mm, adt=(BASE + 0x100, 0x200)))
        self.assertRegex(text, r"destination\s+0x%016x 0x%016x 0x20000" % (BASE, BASE + 0x20000))
        self.assertIn("OVERLAPS DESTINATION", text)
        self.assertIn("blob TrustCache", text)
        self.assertNotIn("Other", text)
        for line in text.splitlines():
            self.assertRegex(line, r"^[\x20-\x7e]*$")
        # staging absent still renders
        self.assertIn("staging block", C.layout_table(self.plan(), facts(staging=None)))


class StagingGateTests(unittest.TestCase):
    """The staging block against live data, independent of the destination (review R4).

    The host WRITES the staging block before the handoff while the old m1n1 runs, so it must not
    start inside live kernel data (below top_of_kernel_data) and must not sit on the original
    source of a blob the flow relocates (the copy would read what the staging overwrote). Any
    other valid memory-map blob it overlaps is a NOTE only: some 16-byte ADT values are not ranges.
    """
    SIZE = 0x20000 + 0x100         # image_size + STUB_MAX of the default plan
    BELOW_TOP = "staging block lies below top_of_kernel_data, inside live kernel data"

    @staticmethod
    def plan(**kw):
        return C.plan_layout(0x10000, kw.pop("base", BASE), kw.pop("sepfw", (RAM + 0x6000000, 0x8000)))

    def test_staging_below_the_top_is_a_problem_without_any_overlap(self):
        plan = self.plan()
        start = RAM + 0x20000000                       # far from the destination
        for top, bad in ((RAM + 0x30000000, True), (RAM + 0x20000001, True),   # one byte below
                         (RAM + 0x20000000, False), (RAM + 0x10000000, False), (None, False)):
            problems, notes = C.check_layout(plan, facts(staging=(start, self.SIZE), top=top))
            self.assertEqual(problems == [self.BELOW_TOP], bad, (top, problems))
            if not bad:
                self.assertEqual((problems, notes), ([], []))
            else:
                self.assertEqual(notes, [])

    def test_below_the_top_is_reported_once_and_in_the_table(self):
        plan = self.plan()
        # overlapping the destination start AND below the top: one problem, no 'safe' note
        problems, notes = C.check_layout(plan, facts(staging=(BASE + 0x1000, self.SIZE),
                                                     top=RAM + 0x1800000))
        self.assertEqual((problems, notes), ([self.BELOW_TOP], []))
        text = C.layout_table(plan, facts(staging=(BASE + 0x1000, self.SIZE), top=RAM + 0x1800000))
        row = next(l for l in text.splitlines() if l.startswith("staging block"))
        self.assertIn("BELOW top_of_kernel_data (live kernel data)", row)
        self.assertNotIn("note: ascending copy, safe", row)
        # no overlap, below the top
        row = next(l for l in C.layout_table(plan, facts(staging=(RAM + 0x20000000, self.SIZE),
                                                         top=RAM + 0x30000000)).splitlines()
                   if l.startswith("staging block"))
        self.assertTrue(row.endswith("BELOW top_of_kernel_data (live kernel data)"), row)
        # clean: no mark at all
        row = next(l for l in C.layout_table(plan, facts(top=RAM + 0x1800000)).splitlines()
                   if l.startswith("staging block"))
        self.assertNotIn("BELOW", row)

    def test_staging_over_the_sepfw_source_is_a_problem(self):
        plan = self.plan()
        src, size = RAM + 0x6000000, self.SIZE
        for start, bad in ((src, True), (src + 0x7FF8, True),            # last 8 bytes of the source
                           (src - size + 8, True),                       # ends 8 bytes into it
                           (src - 0x100, True), (src + 0x8000, False),   # right behind it
                           (src - size, False)):                         # right before it
            problems, notes = C.check_layout(plan, facts(staging=(start, size),
                                                         memory_map={"SEPFW": plan.sepfw}))
            hits = [p for p in problems if "staging block overlaps the SEPFW source" in p]
            self.assertEqual(bool(hits), bad, (hex(start), problems))
            if bad:
                self.assertIn("(0x8000 bytes at 0x%x)" % src, hits[0])
            else:
                self.assertEqual(problems, [])
        # the plan's own SEPFW is what counts, even when the memory-map copy is missing
        problems, _ = C.check_layout(plan, facts(staging=(src, size), memory_map={}))
        self.assertTrue(any("overlaps the SEPFW source" in p for p in problems))
        # an unset or empty SEPFW has no source range
        for sepfw in ((0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF), (src, 0)):
            problems, _ = C.check_layout(C.plan_layout(0x10000, BASE, sepfw),
                                         facts(staging=(src, size)))
            self.assertFalse(any("source" in p for p in problems), problems)

    def test_every_relocated_blob_source_counts_in_the_python_flow(self):
        pplan = C.plan_with_blobs(0x10000, BASE, (RAM + 0x6000000, 0x8000), 0x14000, 0x24000, 0x28000)
        mm = {"SEPFW": pplan.sepfw, "RAMDisk": (RAM + 0x7000000, 0x1000),
              "TrustCache": (RAM + 0x8000000, 0x4000), "Gone": (0xFFFFFFFFFFFFFFFF,) * 2}
        size = 0x28000 + 0x100
        moved = ("SEPFW", "RAMDisk")
        # staging on a moved blob's source: problem naming it
        problems, _ = C.check_layout(pplan, facts(staging=(RAM + 0x7000000 - 0x100, size),
                                                  memory_map=mm), moved=moved)
        self.assertEqual(len(problems), 1)
        self.assertIn("staging block overlaps the RAMDisk source (0x1000 bytes at 0x%x)"
                      % (RAM + 0x7000000), problems[0])
        # a relocated blob whose size is not a range is no source: never a false LAYOUT FAIL
        junk = dict(mm, RAMDisk=(RAM + 0x7000000, 0xFFFFFFFFFFFFFFFF))
        problems, notes = C.check_layout(pplan, facts(staging=(RAM + 0x7000000 - 0x100, size),
                                                      memory_map=junk), moved=moved)
        self.assertEqual((problems, notes), ([], []))
        # the same layout when the blob is NOT moved (in-tree flow): a note, not a problem
        problems, notes = C.check_layout(pplan, facts(staging=(RAM + 0x7000000 - 0x100, size),
                                                      memory_map=mm), moved=("SEPFW",))
        self.assertEqual(problems, [])
        self.assertEqual(len(notes), 1)
        self.assertIn("staging block overlaps memory-map blob RAMDisk (0x1000 bytes at 0x%x); the "
                      "host writes it before the handoff" % (RAM + 0x7000000), notes[0])

    def test_other_valid_blobs_are_notes_and_invalid_ones_are_nothing(self):
        plan = self.plan()
        size = self.SIZE
        start = RAM + 0x7000000 - 0x100
        mm = {"SEPFW": plan.sepfw, "TrustCache": (RAM + 0x7000000, 0x4000),
              "Zero": (RAM + 0x7000000, 0), "Gone": (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF),
              "HalfGone": (0xFFFFFFFFFFFFFFFF, 0x10), "Wraps": (0xFFFFFFFFFFFFFFF0, 0x100),
              "GarbageSize": (RAM + 0x1000, 0xFFFFFFFFFFFFFFFF),      # not a range: no note
              "Elsewhere": (0x1234, 0x10), "odd name\n": (RAM + 0x7001000, 0x10)}
        problems, notes = C.check_layout(plan, facts(staging=(start, size), memory_map=mm))
        self.assertEqual(problems, [])
        text = "\n".join(notes)
        self.assertIn("staging block overlaps memory-map blob TrustCache (0x4000 bytes at 0x%x)"
                      % (RAM + 0x7000000), text)
        self.assertIn("blob odd?name?", text)                       # sanitized
        for absent in ("Zero", "Gone", "HalfGone", "Wraps", "GarbageSize", "Elsewhere", "SEPFW"):
            self.assertNotIn("blob " + absent, text)
        # the table says so too, per blob, without turning it into a problem
        table = C.layout_table(plan, facts(staging=(start, size), memory_map=mm))
        row = next(l for l in table.splitlines() if l.startswith("blob TrustCache"))
        self.assertTrue(row.endswith("OVERLAPPED BY STAGING (note)"), row)
        srow = next(l for l in C.layout_table(plan, facts(staging=(plan.sepfw[0], size),
                                                          memory_map={"SEPFW": plan.sepfw}))
                    .splitlines() if l.startswith("SEPFW (current)"))
        self.assertTrue(srow.endswith("OVERLAPPED BY STAGING"), srow)
        strow = next(l for l in C.layout_table(plan, facts(staging=(plan.sepfw[0], size),
                                                           memory_map={"SEPFW": plan.sepfw}))
                     .splitlines() if l.startswith("staging block"))
        self.assertTrue(strow.endswith("OVERLAPS SEPFW SOURCE"), strow)

    def test_randomized_layouts_pass_only_above_the_top_and_clear_of_the_source(self):
        """An independent oracle over seeded random layouts: the gate is clean exactly when the
        staging block starts at or above the top, is clear of the SEPFW source and is not on the
        wrong side of the destination."""
        rng = random.Random(0x1D0C7)
        far = RAM + RAM_SIZE - 0x400000          # ADT, boot_args, framebuffer at the end of RAM
        counts = {"clean": 0, "refused": 0}
        for _ in range(800):
            plan = C.plan_layout(rng.choice((0x1000, 0x10000, 0x3C0000)),
                                 RAM + rng.choice((0x1000000, 0x1004000, 0x2000000, 0x4000000)),
                                 (RAM + rng.choice((0x1100000, 0x6000000, 0x8000000, 0x10000000)),
                                  rng.choice((0x4000, 0x8000, 0x400000))))
            size = plan.image_size + C.STUB_MAX
            top = RAM + rng.randrange(0x1000000, 0x14000000, 0x4000)
            start = RAM + rng.randrange(0x400000, 0x20000000, 64)
            f = facts(adt=(far, 0x1000), boot_args=(far + 0x10000, 0x480),
                      framebuffer=(far + 0x20000, 0x100000), staging=(start, size), top=top,
                      memory_map={"SEPFW": plan.sepfw})
            problems, notes = C.check_layout(plan, f)
            dest = (plan.new_base, plan.image_size)
            below_top = start < top
            on_source = (start < plan.sepfw[0] + plan.sepfw[1] and plan.sepfw[0] < start + size)
            overlaps_dest = start < dest[0] + dest[1] and dest[0] < start + size
            wrong_side = overlaps_dest and dest[0] >= start
            want_clean = not (below_top or on_source or wrong_side)
            self.assertEqual(problems == [], want_clean,
                             (hex(start), hex(top), hex(plan.new_base), plan.sepfw, problems))
            if below_top:
                self.assertIn(self.BELOW_TOP, problems)
            if on_source:
                self.assertTrue(any("overlaps the SEPFW source" in p for p in problems))
            if wrong_side:
                self.assertTrue(any(p.startswith("destination overlaps the staging block")
                                    for p in problems))
            counts["clean" if want_clean else "refused"] += 1
        self.assertGreater(counts["clean"], 40)           # both outcomes are really exercised
        self.assertGreater(counts["refused"], 40)

    def test_randomized_targets_are_refused_at_the_gate_never_by_a_late_readback(self):
        """The fuzz that found the hole: the gate used to pass a staging block over the SEPFW
        source and the run then died in the 'staged SEPFW read back' check, after writes."""
        rng = random.Random(1234)
        counts = {"pass": 0, "gate": 0}
        for _ in range(300):
            kw = dict(base=RAM + rng.choice((0x1000000, 0x1004000, 0x2000000, 0x3FF0000, 0x200000)),
                      sepfw=(RAM + rng.choice((0x6000000, 0x1100000, 0x1010000, 0x7000000)),
                             rng.choice((0x8000, 0x4000, 0x10000, 0x7FFF, 1, 0x100000, 0x3000000))),
                      ba_addr=RAM + rng.choice((0x1FF0000, 0x1010000, 0x1020000, 0x100C000)),
                      adt_addr=RAM + rng.choice((0x2000000, 0x1030000, 0x1018000, 0x3000000)),
                      heap=RAM + rng.choice((0x20000000, 0x1050000, 0x1008000, 0x1000000,
                                             0x5FF0000, 0x6000000, 0x30000000)),
                      top=RAM + rng.choice((0x1800000, 0x1008000, 0x1100000, 0x2800000)))
            t = Target(**kw)
            try:
                run_intree(t)
            except ValueError as exc:
                text = str(exc)
                self.assertIn("layout gate FAILED", text)
                self.assertNotIn("read back", text)
                self.assertEqual(t.events, [])
                counts["gate"] += 1
                continue
            counts["pass"] += 1
            staging, size = t.heap_events[0][1], t.heap_events[0][2]
            self.assertGreaterEqual(staging, kw["top"])
            sepfw = kw["sepfw"]
            self.assertFalse(staging < sepfw[0] + sepfw[1] and sepfw[0] < staging + size,
                             (hex(staging), hex(size), sepfw))
        self.assertGreater(counts["pass"], 10)
        self.assertGreater(counts["gate"], 10)

    def test_mutations_of_the_independent_rules_are_caught(self):
        plan = self.plan()

        def top_rule(self_test):
            problems, _ = C.check_layout(plan, facts(staging=(RAM + 0x20000000, self.SIZE),
                                                     top=RAM + 0x30000000))
            self_test.assertEqual(problems, [self.BELOW_TOP])

        def source_rule(self_test):
            problems, _ = C.check_layout(plan, facts(staging=(plan.sepfw[0], self.SIZE),
                                                     memory_map={"SEPFW": plan.sepfw}))
            self_test.assertTrue(any("SEPFW source" in p for p in problems))

        top_rule(self)
        source_rule(self)                                    # the real rules pass both
        with patch.object(C, "staging_below_top", lambda facts: False):
            with self.assertRaises(AssertionError):
                top_rule(self)
        with patch.object(C, "staging_source_overlaps", lambda plan, facts, moved: []):
            with self.assertRaises(AssertionError):
                source_rule(self)


class TopOfKernelDataTests(unittest.TestCase):
    END = 0x10001020000      # BASE + 0x20000, written out so the tests do not use the code's sum

    def plan(self, base=BASE):
        return C.plan_layout(0x10000, base, (RAM + 0x6000000, 0x8000))

    CASES = (
        (0x10001800000, 0x10001800000),     # the current top is larger: kept as is
        (0x10001020000, 0x10001020000),     # equal
        (0x10001000000, 0x10001020000),     # below the destination end: the end wins
        (0x10001800123, 0x10001804000),     # larger and unaligned: aligned up to 16K
        (0x10001020001, 0x10001024000),     # one byte above the end
        (0x1234, 0x10001020000),            # nonsense low value: the end
        (0, 0x10001020000))

    def check_literals(self):
        plan = self.plan()
        self.assertEqual(plan.new_base + plan.image_size, self.END)
        for top, want in self.CASES:
            self.assertEqual(C.new_top_of_kernel_data(plan, top), want, hex(top))
        # image_size is a multiple of 16K, the base only needs 8 bytes: the sum is aligned up
        self.assertEqual(C.new_top_of_kernel_data(self.plan(BASE + 0x1008), 0), 0x10001024000)

    def test_new_top_is_max_of_current_and_destination_end_16k_aligned(self):
        self.check_literals()

    def test_never_lowers_the_top_below_live_structures(self):
        """The reason for the maximum: the in-tree value would sit under the ADT and blobs."""
        for top in (0x10001400000, 0x10001FFFFC0, 0x10002000000):
            self.assertGreaterEqual(C.new_top_of_kernel_data(self.plan(), top), top)
        # a mutation that returned the destination end alone (the in-tree/upstream value) fails
        # the independent literals above
        in_tree = lambda plan, top: plan.new_base + plan.image_size      # noqa: E731
        with patch.object(C, "new_top_of_kernel_data", in_tree):
            with self.assertRaises(AssertionError):
                self.check_literals()
        # and so does a version that forgets the alignment
        unaligned = lambda plan, top: max(top, plan.new_base + plan.image_size)   # noqa: E731
        with patch.object(C, "new_top_of_kernel_data", unaligned):
            with self.assertRaises(AssertionError):
                self.check_literals()

    def test_report_lines_current_end_and_new(self):
        end = self.END
        for top, relation, choice in (
                (end + 0x7E0000, "BELOW the current top by 0x7e0000",
                 "= the current top (the new heap starts where the old one did)"),
                (end, "EQUAL to the current top",
                 "= the current top (the new heap starts where the old one did)"),
                (end - 0x1000, "ABOVE the current top by 0x1000",
                 "= the destination end, 16K aligned (above the current top)")):
            lines, notes = C.top_report(self.plan(), top, facts())
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0], "top_of_kernel_data (current)    0x%016x" % top)
            self.assertEqual(lines[1], "destination end                 0x%016x %s" % (end, relation))
            new = max(top, end)
            self.assertEqual(lines[2], "top_of_kernel_data (new)        0x%016x %s" % (new, choice))
            for line in lines:
                self.assertRegex(line, r"^[\x20-\x7e]*$")
        # unaligned current top: the chosen value is the aligned one
        lines, _ = C.top_report(self.plan(), end + 0x123, facts())
        self.assertIn("0x%016x" % (end + 0x4000), lines[2])

    def test_notes_only_when_the_destination_ends_above_the_current_top(self):
        _, notes = C.top_report(self.plan(), self.END + 0x400000, facts())
        self.assertEqual(notes, [])
        _, notes = C.top_report(self.plan(), self.END, facts())
        self.assertEqual(notes, [])
        _, notes = C.top_report(self.plan(), self.END - 0x1000, facts())
        self.assertEqual(len(notes), 1)
        self.assertIn("destination ends above the current top_of_kernel_data by 0x1000", notes[0])
        # facts is optional
        self.assertEqual(C.top_report(self.plan(), self.END)[1], [])


class BootArgsTests(unittest.TestCase):
    def test_parse_and_retop_touch_only_offset_0x20(self):
        raw = raw_boot_args(devtree=VIRT_BASE + 0x2000000, devtree_size=0x1234)
        view = C.parse_boot_args(raw)
        self.assertEqual((view.revision, view.phys_base, view.mem_size, view.devtree_size),
                         (3, RAM, RAM_SIZE, 0x1234))
        self.assertEqual(view.adt_address, RAM + 0x2000000)
        self.assertEqual((view.video.base, view.video.stride, view.video.depth),
                         (RAM + 0x3000000, 3200, 30))
        new = C.with_top_of_kernel_data(raw, 0x1122334455667788)
        diff = [i for i in range(len(raw)) if raw[i] != new[i]]
        self.assertTrue(diff and min(diff) >= 0x20 and max(diff) < 0x28, diff)
        self.assertEqual(struct.unpack_from("<Q", new, 0x20)[0], 0x1122334455667788)
        self.assertEqual(len(new), 0x480)
        with self.assertRaises(ValueError):
            C.with_top_of_kernel_data(raw[:0x400], 1)
        with self.assertRaises(ValueError):
            C.with_top_of_kernel_data(raw, 1 << 64)
        with self.assertRaises(ValueError):
            C.parse_boot_args(b"\0" * 8)


# === in-tree chainload against a recording fake target ================================
class IntreeTests(unittest.TestCase):
    def setUp(self):
        self.t = Target()

    def test_exact_write_set(self):
        image, out = run_intree(self.t)
        t = self.t
        staging = t.heap_events[0][1]
        size = 0x20000 + C.STUB_MAX
        self.assertEqual(t.heap_events, [("malloc", staging, size)])
        # ADT: exactly one write, 16 bytes, at the SEPFW value, equal to the new SEPFW pair.
        off, vsize, _ = adt_patch.locate(t.adt, "/chosen/memory-map", "SEPFW")
        self.assertEqual(vsize, 16)
        adt_writes = t.writes_in(t.adt_addr, len(t.adt))
        self.assertEqual(adt_writes, [("write", t.adt_addr + off,
                                       struct.pack("<QQ", BASE + 0x14000, 0x8000))])
        after = t.mem.read(t.adt_addr, len(t.adt))
        diff = [i for i in range(len(after)) if after[i] != t.adt[i]]
        self.assertTrue(diff and min(diff) >= off and max(diff) < off + 16)
        # boot_args copy: the raw bytes with only offset 0x20 changed, to the CURRENT top (it is
        # larger than the destination end here), written as an independent literal.
        self.assertEqual(struct.unpack_from("<Q", t.raw_ba, 0x20)[0], 0x10001800000)
        want = bytearray(t.raw_ba)
        struct.pack_into("<Q", want, 0x20, 0x10001800000)
        got = t.mem.read(staging + 0x1C000, 0x480)
        self.assertEqual(got, bytes(want))
        self.assertIn(b"SECRETMARKER9999", got)                  # cmdline and filler preserved raw
        self.assertEqual(got[0x100:0x110], b"\xa5" * 16)
        # image + 4 zero bytes at the start of staging, SEPFW at the plan's offset.
        self.assertEqual(t.mem.read(staging, IMAGE_LEN + 4), image + b"\0" * 4)
        self.assertEqual(t.mem.read(staging + 0x14000, 0x8000), t.sepfw_data)
        self.assertEqual(t.of("memcpy8"), [("memcpy8", staging + 0x14000, t.sepfw[0], 0x8000)])
        # nothing else: no push_adt, no RVBAR (write64), no stray writes into live structures
        self.assertEqual(t.of("push_adt"), [])
        self.assertEqual(t.of("write64"), [])
        self.assertEqual(t.writes_in(BASE, 0x20000), [])
        self.assertEqual(t.writes_in(t.ba_addr, 0x480), [])

    def test_stub_and_single_reload(self):
        image, out = run_intree(self.t)
        t = self.t
        staging = t.heap_events[0][1]
        reloads = t.of("reload")
        self.assertEqual(len(reloads), 1)
        stub_addr = staging + 0x20000
        self.assertEqual(reloads[0][1:], (stub_addr, BASE + 0x1C000, staging, BASE, 0x20000))
        paint = (C.slot_address(t.vid, 0), t.vid.stride)          # strip origin = slot 0
        code = C.stub(BASE + 0x800, paint)
        self.assertEqual(len(code), len(C.STUB_PAINT_CODE) + 32)
        self.assertEqual(len(code), 224)
        self.assertEqual(t.mem.read(stub_addr, len(code)), code)
        # cache maintenance covers every touched range before the reload
        before = t.events[:t.events.index(reloads[0])]
        dc = [e[1:] for e in before if e[0] == "dc_cvau"]
        for rng in ((staging, IMAGE_LEN + 4), (staging + 0x14000, 0x8000),
                    (staging + 0x1C000, 0x480), (stub_addr, len(code))):
            self.assertIn(rng, dc)
        off = adt_patch.locate(t.adt, "/chosen/memory-map", "SEPFW")[0]
        self.assertIn((t.adt_addr + off, 16), dc)
        self.assertIn(("ic_ivau", stub_addr, len(code)), before)
        self.assertEqual(t.events[-1], reloads[0])               # reload is the last mutation
        self.assertEqual(t.of("reload")[0][1:], (stub_addr, BASE + 0x1C000, staging, BASE, 0x20000))

    def test_returns_the_plan_for_the_new_instance_proof(self):
        t = Target()
        image = bytes(IMAGE_LEN)
        with contextlib.redirect_stdout(io.StringIO()):
            plan = hv_launch.chainload_intree(t.iface, t.proxy, t.utils, image)
        self.assertEqual((plan.new_base, plan.bootargs_off, plan.image_size),
                         (BASE, 0x1C000, 0x20000))
        self.assertEqual(plan.new_base + plan.bootargs_off, t.of("reload")[0][2])

    # --- the live ADT window (item 4) ---------------------------------------------------
    @staticmethod
    def window_facts(t):
        """Indices of the interesting events of one successful in-tree run."""
        ev = t.events
        fb = (t.vid.base, t.vid.stride * t.vid.height)
        paints = [i for i, e in enumerate(ev) if e[0] == "write" and fb[0] <= e[1] < fb[0] + fb[1]]
        adt = [i for i, e in enumerate(ev) if e[0] == "write" and
               t.adt_addr <= e[1] < t.adt_addr + len(t.adt)]
        adt_dc = [i for i, e in enumerate(ev) if e[0] == "dc_cvau" and
                  t.adt_addr <= e[1] < t.adt_addr + len(t.adt)]
        reload_at = [i for i, e in enumerate(ev) if e[0] == "reload"]
        return paints, adt, adt_dc, reload_at

    def check_adt_window(self, t):
        """slot 2 BEFORE the ADT write; after it only the cache clean, then the reload."""
        paints, adt, adt_dc, reload_at = self.window_facts(t)
        self.assertEqual(len(paints), 3 * 24)                    # slots 0, 1, 2
        self.assertEqual((len(adt), len(adt_dc), len(reload_at)), (1, 1, 1))
        slot2 = paints[48:]
        self.assertEqual([(t.events[i][1], t.events[i][2]) for i in slot2], C.paint_rows(t.vid, 2))
        self.assertLess(slot2[-1], adt[0])                       # all of slot 2 precedes the write
        self.assertEqual([e[0] for e in t.events[adt[0] + 1:reload_at[0]]], ["dc_cvau"])
        self.assertEqual(t.events[adt[0] + 1][1:], (t.adt_addr + adt_patch.locate(
            t.adt, "/chosen/memory-map", "SEPFW")[0], 16))
        self.assertEqual(t.events[-1][0], "reload")

    def test_slot_2_is_painted_before_the_adt_write_and_only_a_cache_clean_follows(self):
        run_intree(self.t)
        self.check_adt_window(self.t)

    def test_mutation_slot_2_after_the_adt_write_is_caught_by_the_window_check(self):
        t = Target()
        run_intree(t)
        paints, adt, adt_dc, reload_at = self.window_facts(t)
        self.check_adt_window(t)                                  # the real order passes
        # reorder the event log the way the old code did: ADT, cache clean, THEN slot 2
        slot2 = [t.events[i] for i in paints[48:]]
        rest = [e for i, e in enumerate(t.events) if i not in paints[48:]]
        at = next(i for i, e in enumerate(rest) if e[0] == "dc_cvau" and
                  t.adt_addr <= e[1] < t.adt_addr + len(t.adt))
        mutated = Target()
        mutated.events = rest[:at + 1] + slot2 + rest[at + 1:]
        mutated.adt, mutated.adt_addr, mutated.vid = t.adt, t.adt_addr, t.vid
        with self.assertRaises(AssertionError):
            self.check_adt_window(mutated)

    def test_host_slots_in_order_around_the_staging(self):
        run_intree(self.t)
        t = self.t
        fb = (t.vid.base, t.vid.stride * t.vid.height)
        paints = [e for e in t.events if e[0] == "write" and fb[0] <= e[1] < fb[0] + fb[1]]
        self.assertEqual(len(paints), 3 * 24)
        for i, slot in enumerate((0, 1, 2)):
            chunk = paints[i * 24:(i + 1) * 24]
            self.assertEqual([(e[1], e[2]) for e in chunk], C.paint_rows(t.vid, slot))
        at = lambda ev: next(i for i, e in enumerate(t.events) if e is ev)     # noqa: E731
        s0, s1, s2 = at(paints[0]), at(paints[24]), at(paints[48])
        s2_last = at(paints[71])
        stage = [i for i, e in enumerate(t.events) if e[0] in ("cwrite", "memcpy8")]
        staging = t.heap_events[0][1]
        stub_write = next(i for i, e in enumerate(t.events)
                          if e[0] == "write" and e[1] == staging + 0x20000)
        stub_dc = next(i for i, e in enumerate(t.events)
                       if e[0] == "dc_cvau" and e[1] == staging + 0x20000)
        stub_ic = next(i for i, e in enumerate(t.events)
                       if e[0] == "ic_ivau" and e[1] == staging + 0x20000)
        adt_write = next(i for i, e in enumerate(t.events)
                         if e[0] == "write" and t.adt_addr <= e[1] < t.adt_addr + len(t.adt))
        adt_dc = next(i for i, e in enumerate(t.events)
                      if e[0] == "dc_cvau" and t.adt_addr <= e[1] < t.adt_addr + len(t.adt))
        reload_at = next(i for i, e in enumerate(t.events) if e[0] == "reload")
        self.assertLess(s0, min(stage))                          # gate mark precedes every staging write
        # slot 1 (staged) comes after the stub is written, read back and cache-maintained ...
        self.assertLess(max(stage), stub_write)
        self.assertLess(stub_write, stub_dc)
        self.assertLess(stub_dc, stub_ic)
        self.assertLess(stub_ic, s1)
        # ... slot 2 ("everything staged and verified") follows slot 1 and precedes the live write
        self.assertLess(s1, s2)
        self.assertLess(s2_last, adt_write)
        # the ADT patch is the last write; only its cache clean separates it from the reload
        self.assertLess(adt_write, adt_dc)
        self.assertLess(adt_dc, reload_at)
        self.assertEqual([e[0] for e in t.events[adt_write + 1:reload_at]], ["dc_cvau"])
        self.assertEqual(t.events[adt_dc][1:], (t.adt_addr + adt_patch.locate(
            t.adt, "/chosen/memory-map", "SEPFW")[0], 16))
        # before the ADT write, the live ADT bytes are exactly what the target started with
        self.assertEqual(t.writes_in(t.adt_addr, len(t.adt)), [t.events[adt_write]])

    # failure injection around the one live write ---------------------------------------
    def adt_flaky(self, t, on_write=None, dc_error=None, dead_after_patch=False):
        """Wrap t's writes into the live ADT / dc_cvau of it; returns a state dict.

        dc_error is raised by the FIRST cache clean of the ADT only (the restore's clean works).
        """
        state = {"patched": False, "dc_raised": False}
        real_write, real_dc, real_read = t._write, t.proxy.dc_cvau, t._read
        lo, hi = t.adt_addr, t.adt_addr + len(t.adt)

        def writemem(addr, data):
            if lo <= addr < hi:
                if state["patched"] and dead_after_patch:
                    raise UartTimeout("link dead /dev/cu.usbmodemSECRET1")
                if on_write is not None:
                    return on_write(state, real_write, addr, bytes(data))
                real_write(addr, data)
                state["patched"] = True
            else:
                real_write(addr, data)

        def readmem(addr, size):
            if state["patched"] and dead_after_patch:
                raise UartTimeout("link dead /dev/cu.usbmodemSECRET1")
            return real_read(addr, size)

        def dc_cvau(addr, size):
            if lo <= addr < hi and dc_error is not None and not state["dc_raised"]:
                state["dc_raised"] = True
                raise dc_error
            real_dc(addr, size)

        t.iface.writemem, t.iface.readmem, t.proxy.dc_cvau = writemem, readmem, dc_cvau
        return state

    def test_a_patch_that_does_not_land_is_reverted_and_the_outcome_says_restored(self):
        t = Target()

        def drop_patch(state, real, addr, data):
            if data == struct.pack("<QQ", BASE + 0x14000, 0x8000):
                return None                       # the target drops the new value
            real(addr, data)

        self.adt_flaky(t, on_write=drop_patch)
        with self.assertRaisesRegex(ValueError, "live ADT patch failed and was restored and "
                                                "verified .*read back differently"):
            run_intree(t)
        self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)
        self.assertEqual(t.of("reload"), [])
        off = adt_patch.locate(t.adt, "/chosen/memory-map", "SEPFW")[0]
        # the original value was written back and cleaned from the cache
        self.assertIn(("dc_cvau", t.adt_addr + off, 16), t.events)

    def test_a_failed_cache_clean_after_the_patch_is_reverted(self):
        t = Target()
        self.adt_flaky(t, dc_error=UartTimeout("no reply from /dev/cu.usbmodemSECRET1"))
        with self.assertRaises(ValueError) as caught:
            run_intree(t)
        text = str(caught.exception)
        self.assertIn("live ADT patch failed and was restored and verified (UartTimeout)", text)
        self.assertNotIn("usbmodem", text)                        # the class name only, never the text
        self.assertNotIn("SECRET", text)
        self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)   # live ADT is the original
        self.assertEqual(t.of("reload"), [])

    def test_a_dead_link_after_the_patch_reports_not_restored(self):
        t = Target()
        self.adt_flaky(t, dead_after_patch=True)
        with self.assertRaises(ValueError) as caught:
            run_intree(t)
        text = str(caught.exception)
        self.assertIn("live ADT SEPFW patched and NOT restored: POWER OFF completely before any "
                      "further run", text)
        self.assertNotIn("restored and verified", text)
        self.assertNotIn("usbmodem", text)
        off = adt_patch.locate(t.adt, "/chosen/memory-map", "SEPFW")[0]
        self.assertEqual(t.mem.read(t.adt_addr + off, 16), struct.pack("<QQ", BASE + 0x14000, 0x8000))
        self.assertEqual(t.of("reload"), [])

    def test_a_restore_that_does_not_verify_reports_not_restored(self):
        t = Target()
        count = []

        def stuck(state, real, addr, data):
            count.append(data)
            if len(count) == 1:
                real(addr, data)                  # the patch lands
                state["patched"] = True
            # every later write (the restore) is silently dropped

        self.adt_flaky(t, on_write=stuck, dc_error=UartTimeout("no reply"))
        with self.assertRaisesRegex(ValueError, "live ADT SEPFW patched and NOT restored: POWER "
                                                "OFF completely before any further run"):
            run_intree(t)
        self.assertEqual(len(count), 2)                           # the restore was attempted
        self.assertNotEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)
        self.assertEqual(t.of("reload"), [])

    def test_a_stray_byte_outside_the_value_is_not_reported_as_restored(self):
        """The outcome is judged against the WHOLE ADT, not only against the 16 patched bytes."""
        t = Target()
        off = adt_patch.locate(t.adt, "/chosen/memory-map", "SEPFW")[0]

        def stray(state, real, addr, data):
            real(addr, data)
            if not state["patched"]:
                state["patched"] = True
                t.mem.write(t.adt_addr + off + 16, bytes([t.adt[off + 16] ^ 0xFF]))   # a bad write

        self.adt_flaky(t, on_write=stray)
        with self.assertRaisesRegex(ValueError, "live ADT SEPFW patched and NOT restored: POWER OFF "
                                                "completely before any further run"):
            run_intree(t)
        # the 16 value bytes are back, the stray byte is not: exactly why 16 bytes cannot be trusted
        self.assertEqual(t.mem.read(t.adt_addr + off, 16), t.adt[off:off + 16])
        self.assertNotEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)
        self.assertEqual(t.of("reload"), [])

    def test_the_global_alarm_in_the_window_propagates_after_the_revert(self):
        for error in (TimeoutError("preflight exceeded 300 seconds"), KeyboardInterrupt()):
            with self.subTest(type(error).__name__):
                t = Target()
                self.adt_flaky(t, dc_error=error)
                out = io.StringIO()
                with contextlib.redirect_stdout(out), self.assertRaises(type(error)):
                    hv_launch.chainload_intree(t.iface, t.proxy, t.utils, bytes(IMAGE_LEN))
                self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)   # revert was attempted
                self.assertIn("live ADT patch failed and was restored and verified", out.getvalue())
                self.assertEqual(t.of("reload"), [])

    def test_the_window_failure_wording_is_the_only_exit(self):
        """A failed ADT write must never leak as a bare transport exception."""
        for error in (UartTimeout("x"), OSError("x"), RuntimeError("x"), ValueError("x")):
            t = Target()
            self.adt_flaky(t, dc_error=error)
            with self.subTest(type(error).__name__), self.assertRaisesRegex(
                    ValueError, r"live ADT patch failed and was restored and verified \(%s\)"
                    % type(error).__name__):
                run_intree(t)

    def test_mutation_without_the_revert_leaves_the_adt_patched_and_is_caught(self):
        def naive(iface, proxy, state, write, want, clean, restore, reload_args=None, out=None,
                  what="", message=""):
            write()
            if iface.readmem(state.adt_addr, len(want)) != want:
                raise ValueError("mismatch")
            proxy.dc_cvau(*clean)

        t = Target()
        self.adt_flaky(t, dc_error=UartTimeout("no reply"))
        with patch.object(hv_launch, "commit_live_adt", naive), self.assertRaises(UartTimeout):
            run_intree(t)
        off = adt_patch.locate(t.adt, "/chosen/memory-map", "SEPFW")[0]
        # the live ADT is left patched: exactly what the revert-and-report code prevents
        self.assertEqual(t.mem.read(t.adt_addr + off, 16), struct.pack("<QQ", BASE + 0x14000, 0x8000))

    def test_a_failure_before_the_adt_patch_leaves_the_live_adt_untouched(self):
        """Stub readback failure (last step before the patch): ADT never written."""
        t = Target()
        real = t._write

        def corrupt_stub(addr, data):
            staging = t.heap_events[0][1]
            if addr == staging + 0x20000:
                data = data[:-1] + bytes([data[-1] ^ 1])
            real(addr, data)

        t.iface.writemem = corrupt_stub
        with self.assertRaisesRegex(ValueError, "copy stub read back differently"):
            run_intree(t)
        self.assertEqual(t.writes_in(t.adt_addr, len(t.adt)), [])
        self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)
        self.assertEqual(t.of("reload"), [])
        self.assertEqual(t.of("ic_ivau"), [])                    # never got to cache maintenance

    def test_staging_failures_never_write_the_adt(self):
        def drop_image(t):
            t.utils.compressed_writemem = lambda addr, data, progress=None: None

        def drop_sepfw(t):
            t.proxy.memcpy8 = lambda dst, src, size: None

        def drop_boot_args(t):
            real = t._write
            staging = RAM + 0x20000000                           # the Target's first allocation

            def writemem(addr, data):
                if addr == staging + 0x1C000:                    # the staged boot_args copy
                    return                                       # dropped: reads back as zeros
                real(addr, data)
            t.iface.writemem = writemem

        def corrupt_boot_args(t):
            real = t._write
            staging = RAM + 0x20000000

            def writemem(addr, data):
                if addr == staging + 0x1C000:
                    data = data[:0x20] + bytes([data[0x20] ^ 1]) + data[0x21:]
                real(addr, data)
            t.iface.writemem = writemem

        for name, mutate, message in (("image never staged", drop_image, "staged image"),
                                      ("SEPFW never copied", drop_sepfw, "staged SEPFW"),
                                      ("boot_args write dropped", drop_boot_args,
                                       "staged boot_args read back differently"),
                                      ("boot_args write corrupted", corrupt_boot_args,
                                       "staged boot_args read back differently")):
            with self.subTest(name):
                t = Target()
                mutate(t)
                with self.assertRaisesRegex(ValueError, message):
                    run_intree(t)
                self.assertEqual(t.writes_in(t.adt_addr, len(t.adt)), [])
                self.assertEqual(t.of("reload"), [])
                self.assertEqual(t.of("push_adt"), [])
                self.assertEqual(t.of("ic_ivau"), [])            # no stub was even written

    def test_ineligible_framebuffer_paints_nothing_and_uses_plain_stub(self):
        for vid in (video(base=0), video(width=300), video(depth=24), video(stride=2300)):
            with self.subTest(vid=vars(vid)):
                t = Target(vid=vid)
                run_intree(t)
                staging = t.heap_events[0][1]
                if vid.base:
                    self.assertEqual([e for e in t.events if e[0] == "write" and
                                      vid.base <= e[1] < vid.base + vid.stride * vid.height], [])
                self.assertEqual(t.mem.read(staging + 0x20000, 56), C.stub(BASE + 0x800))
                self.assertEqual(len(t.of("reload")), 1)

    def test_unaligned_stride_paints_from_the_host_but_not_from_the_stub(self):
        t = Target(vid=video(stride=3202))        # eligible by contract, not 4-byte aligned
        run_intree(t)
        staging = t.heap_events[0][1]
        fb = t.vid
        rows = [e for e in t.events if e[0] == "write" and fb.base <= e[1] < fb.base + fb.stride * fb.height]
        self.assertEqual(len(rows), 3 * 24)
        self.assertEqual(t.mem.read(staging + 0x20000, 56), C.stub(BASE + 0x800))

    def test_stride_larger_than_four_bytes_per_pixel_is_used_for_rows_and_stub(self):
        vid = video(stride=3328)                  # 3328 != 800 * 4: padding after each row
        t = Target(vid=vid)
        run_intree(t)
        staging = t.heap_events[0][1]
        want = C.stub(BASE + 0x800, (C.slot_address(vid, 0), 3328))
        self.assertEqual(t.mem.read(staging + 0x20000, len(want)), want)
        rows = [e for e in t.events if e[0] == "write" and vid.base <= e[1] < vid.base + 3328 * 600]
        self.assertEqual([(e[1], e[2]) for e in rows[:24]], C.paint_rows(vid, 0))
        self.assertEqual(rows[1][1] - rows[0][1], 3328)

    def test_output_is_sanitized(self):
        _, out = run_intree(self.t)
        for line in out.splitlines():
            self.assertRegex(line, r"^[\x20-\x7e]*$")
        self.assertNotIn("SECRETMARKER", out)
        self.assertIn("Layout gate PASS", out)
        self.assertIn("NOTE: memory-map blob TrustCache", out)   # overwritten blob is named
        self.assertNotIn("PROBLEM", out)

    def test_breadcrumb_and_handoff_text_follow_the_stub_predicate(self):
        _, out = run_intree(self.t)                              # eligible and 4-byte aligned
        crumbs = [l for l in out.splitlines() if l.startswith("Breadcrumbs:")]
        self.assertEqual(len(crumbs), 1)
        self.assertIn("stub bar enabled", crumbs[0])
        self.assertIn("redraw may erase them", crumbs[0])         # host slots 0-2 may be erased
        self.assertIn("slots 0-4", crumbs[0])
        self.assertIn("marks its entry in slot 3", crumbs[0])
        handoff = [l for l in out.splitlines() if l.startswith("Handoff.")]
        self.assertEqual(len(handoff), 1)
        self.assertIn("host slots 0-2 may already have been erased", handoff[0])
        self.assertIn("slot 3 alone means the stub was entered but its copy or paint did not "
                      "finish", handoff[0])
        self.assertIn("Success = bar (slots 0-4) + all of 5-20 lit", handoff[0])
        self.assertNotIn("slot 4 = copy stub", out)
        # video_ok() true but the stub cannot store: text must say the stub will NOT paint
        t = Target(vid=video(stride=3202))
        self.assertTrue(C.video_ok(t.vid))
        _, out = run_intree(t)
        self.assertIn("Breadcrumbs: the copy stub will NOT paint", out)
        self.assertIn("Handoff. The copy stub will NOT paint", out)
        self.assertNotIn("stub bar enabled", out)
        self.assertNotIn("Success = bar", out)
        # not eligible at all
        t = Target(vid=video(width=300))
        _, out = run_intree(t)
        self.assertIn("Breadcrumbs: framebuffer geometry not eligible; the copy stub will NOT paint",
                      out)
        self.assertIn("Handoff. The copy stub will NOT paint", out)

    def test_layout_facts_are_printed_on_the_chainload_path_too(self):
        _, out = run_intree(Target(vid=video(depth=30 | (1 << 16))))
        self.assertIn("RETINA flag (0x10000) set", out)
        self.assertIn("stub bar will paint (stub_paint): yes", out)
        self.assertIn("top_of_kernel_data (current)", out)
        self.assertIn("top_of_kernel_data (new)", out)

    # --- the new top_of_kernel_data (item 6) ----------------------------------------------
    def staged_top(self, t):
        staging = t.heap_events[0][1]
        return struct.unpack_from("<Q", t.mem.read(staging + 0x1C000, 0x480), 0x20)[0]

    def test_staged_top_is_the_current_top_when_that_is_larger(self):
        t = Target(top=0x10001800000)           # destination end is 0x10001020000
        _, out = run_intree(t)
        self.assertEqual(self.staged_top(t), 0x10001800000)
        self.assertIn("top_of_kernel_data (new)        0x0000010001800000 = the current top", out)

    def test_staged_top_is_the_destination_end_when_that_is_larger(self):
        t = Target(top=0x10000C00000)           # below BASE: the end 0x10001020000 wins
        _, out = run_intree(t)
        self.assertEqual(self.staged_top(t), 0x10001020000)
        self.assertIn("top_of_kernel_data (new)        0x0000010001020000 = the destination end", out)
        # only offset 0x20 of the raw copy differs from the target's boot_args
        staging = t.heap_events[0][1]
        got = t.mem.read(staging + 0x1C000, 0x480)
        diff = [i for i in range(0x480) if got[i] != t.raw_ba[i]]
        self.assertTrue(diff and min(diff) >= 0x20 and max(diff) < 0x28, diff)

    def test_staged_top_is_16k_aligned_and_never_below_the_current_value(self):
        for top in (0x10001800001, 0x10001803FFF, 0x10001FFFFC0):
            with self.subTest(top=hex(top)):
                t = Target(top=top)
                run_intree(t)
                got = self.staged_top(t)
                self.assertEqual(got % 0x4000, 0)
                self.assertGreaterEqual(got, top)
                self.assertLess(got - top, 0x4000)

    def test_the_old_in_tree_value_would_have_lowered_the_top_below_live_structures(self):
        # Fixture: ADT at RAM + 0x2000000 and the live top at RAM + 0x1800000 are both ABOVE the
        # destination end (0x10001020000): the upstream value would put the new heap start under
        # them. The staged value must not be that.
        t = Target()
        run_intree(t)
        self.assertNotEqual(self.staged_top(t), BASE + 0x20000)
        self.assertGreater(t.adt_addr, BASE + 0x20000)

    # --- chainload notes and signatures (items 5 and 7) ---------------------------------
    def test_a_live_boot_args_inside_the_destination_does_not_stop_a_first_chainload(self):
        t = Target(ba_addr=BASE + 0x2000)
        _, out = run_intree(t)
        self.assertIn("NOTE: live boot_args lies inside the destination; it will be overwritten, "
                      "m1n1 already copied it", out)
        self.assertIn("boot_args (live)", out)
        self.assertEqual(len(t.of("reload")), 1)
        self.assertNotIn("PROBLEM", out)

    def test_sepfw_already_at_the_planned_address_is_noted_both_ways(self):
        t = Target(sepfw=(BASE + 0x14000, 0x8000))
        _, out = run_intree(t)
        self.assertIn("NOTE: SEPFW already points at the planned relocation address; if this is "
                      "not the first run since power-on, a previous chainload patched this ADT: "
                      "power off completely", out)
        self.assertRegex(out, r"SEPFW \(current\).*AT THE PLANNED RELOCATION ADDRESS")
        self.assertEqual(len(t.of("reload")), 1)                  # a note, not a problem
        t = Target()
        _, out = run_intree(t)
        self.assertNotIn("already points at the planned relocation address", out)
        self.assertNotIn("PLANNED RELOCATION", out)

    def test_the_in_tree_staging_overlap_passes_with_one_note(self):
        """_base + image_size above top_of_kernel_data: the buffer at top starts inside the destination."""
        top = RAM + 0x1010000                              # destination is [BASE, BASE + 0x20000)
        t = Target(top=top, heap=top)
        _, out = run_intree(t)
        self.assertIn("NOTE: destination overlaps the start of the staging block; safe: ascending "
                      "copy, destination below staging, stub above destination end", out)
        self.assertEqual(out.count("destination overlaps the start of the staging block"), 1)
        self.assertRegex(out, r"staging block\s.*OVERLAPS DESTINATION START \(note: ascending copy, "
                              r"safe\)")
        self.assertIn("Layout gate PASS: the destination clears the ADT and framebuffer; any "
                      "staging overlap is below the stub and the copy is ascending", out)
        self.assertIn(GATE_FACTS, out)
        self.assertNotIn("PROBLEM", out)
        self.assertEqual(len(t.of("reload")), 1)
        # the stub sits above the destination end, as the argument needs
        staging = t.heap_events[0][1]
        stub_addr = staging + 0x20000
        self.assertGreater(stub_addr, BASE + 0x20000)
        self.assertEqual(t.of("reload")[0][1], stub_addr)
        # the destination end (0x10001020000) is above the current top: that value is handed over
        self.assertEqual(struct.unpack_from("<Q", t.mem.read(staging + 0x1C000, 0x480), 0x20)[0],
                         0x10001020000)

    def test_the_in_tree_staging_overlap_is_not_a_problem_in_python_mode_either(self):
        top = RAM + 0x1010000
        t = Target(top=top, heap=top)
        _, out = run_chainload("python", t)
        self.assertEqual(out.count("destination overlaps the start of the staging block"), 1)
        self.assertEqual(len(t.of("reload")), 1)
        staging = t.heap_events[0][1]
        self.assertGreater(staging + 0x28000, BASE + 0x28000)

    # (Target kwargs, the problem the gate must name)
    GATE_CASES = {
        "adt overlaps": (dict(adt_addr=BASE + 0x4000), "destination overlaps the ADT"),
        "adt starts below and extends in": (dict(adt_addr=BASE - 0x40),
                                            "destination overlaps the ADT"),
        "boot_args at the planned address": (
            dict(ba_addr=BASE + 0x1C000),
            "destination overlaps the boot_args at the planned boot_args address"),
        "framebuffer overlaps": (dict(vid=video(base=BASE + 0x100)),
                                 "destination overlaps the framebuffer"),
        "framebuffer starts below and extends in": (dict(vid=video(base=BASE - 0x1000)),
                                                    "destination overlaps the framebuffer"),
        "framebuffer extent uses the stride": (
            # width * 4 * height ends 30000 bytes below the destination, stride * height 46800 above
            dict(vid=video(base=BASE - 1950000, stride=3328)),
            "destination overlaps the framebuffer"),
        "staging overlaps inside kernel data": (       # top is RAM + 0x1800000
            dict(heap=BASE + 0x1000),
            "staging block lies below top_of_kernel_data, inside live kernel data"),
        "staging below the top without any overlap": (
            dict(heap=RAM + 0x1100000),
            "staging block lies below top_of_kernel_data, inside live kernel data"),
        "staging on the SEPFW source": (dict(heap=RAM + 0x6000000),
                                        "staging block overlaps the SEPFW source"),
        "staging ending inside the SEPFW source": (dict(heap=RAM + 0x6000000 - 0x20000),
                                                   "staging block overlaps the SEPFW source"),
        "staging starts at the destination": (dict(heap=BASE),
                                              "destination overlaps the staging block"),
        "staging starts below and reaches in": (dict(heap=BASE - 0x1000),
                                                "destination overlaps the staging block"),
        "staging could not be allocated": (dict(malloc_error=True),
                                           "staging block could not be allocated"),
        "outside ram": (dict(ram=(RAM + 0x2000000, RAM_SIZE)), "destination lies outside RAM"),
        "sepfw missing": (dict(sepfw=None), "SEPFW is missing"),
        "sepfw size 0": (dict(sepfw=(RAM + 0x6000000, 0)), "SEPFW has size 0"),
        "sepfw sentinel": (dict(sepfw=(0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)), "sentinel"),
        "adt size 0": (dict(devtree_size=0), "ADT size 0x0 is implausible"),
        "adt size above the bound": (dict(devtree_size=hv_launch.MAX_ADT + 1),
                                     "ADT size 0x%x is implausible" % (hv_launch.MAX_ADT + 1)),
    }

    def test_every_gate_failure_causes_zero_target_writes(self):
        for name, (kw, message) in self.GATE_CASES.items():
            with self.subTest(name):
                t = Target(**kw)
                with self.assertRaisesRegex(ValueError, "layout gate FAILED.*" + message):
                    run_intree(t)
                self.assertEqual(t.events, [], name)               # ZERO target writes
                mallocs = [e for e in t.heap_events if e[0] == "malloc"]
                frees = [e for e in t.heap_events if e[0] == "free"]
                self.assertEqual([f[1] for f in frees], [m[1] for m in mallocs])  # staging released

    def test_each_gate_is_independent_of_the_others(self):
        """A clean target passes; flipping exactly one condition trips exactly its gate."""
        run_intree(Target())
        for name, (kw, message) in self.GATE_CASES.items():
            t = Target(**kw)
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(ValueError):
                hv_launch.chainload_intree(t.iface, t.proxy, t.utils, bytes(IMAGE_LEN))
            problems = [l[len("PROBLEM: "):] for l in out.getvalue().splitlines()
                        if l.startswith("PROBLEM: ")]
            self.assertTrue(any(message in p for p in problems), (name, problems))

    def test_a_framebuffer_below_the_destination_that_does_not_reach_it_is_fine(self):
        run_intree(Target(vid=video(base=BASE - 0x300000)))        # 0x1D4C00 bytes: ends below BASE
        # the stride, not width * 4, is the row length: 3328 * 600 ends inside the destination
        with self.assertRaisesRegex(ValueError, "destination overlaps the framebuffer"):
            run_intree(Target(vid=video(base=BASE - 1950000, stride=3328)))
        # ... while the same start with a tight stride (width * 4 = 3200) stops 30000 bytes short
        run_intree(Target(vid=video(base=BASE - 1950000, stride=3200)))

    def test_gate_report_names_the_problem(self):
        t = Target(adt_addr=BASE + 0x4000)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(ValueError):
            hv_launch.chainload_intree(t.iface, t.proxy, t.utils, bytes(IMAGE_LEN))
        self.assertIn("PROBLEM: destination overlaps the ADT", out.getvalue())
        self.assertIn("OVERLAPS DESTINATION", out.getvalue())

    def test_controller_disagreement_is_fatal_for_every_field(self):
        # the cross-check lists themselves are pinned by independent literals, so that dropping a
        # field from them cannot silently shrink the loops below
        self.assertEqual(set(hv_launch.BA_FIELDS),
                         {"virt_base", "phys_base", "mem_size", "top_of_kernel_data", "devtree",
                          "devtree_size"})
        self.assertEqual(set(hv_launch.VIDEO_FIELDS), {"base", "stride", "width", "height", "depth"})
        for name in hv_launch.BA_FIELDS:
            with self.subTest(name):
                t = Target()
                setattr(t.utils.ba, name, getattr(t.utils.ba, name) ^ 0x10)
                with self.assertRaisesRegex(ValueError, "boot_args %s differs" % name):
                    run_intree(t)
                self.assertEqual(t.events, [])
        for name in hv_launch.VIDEO_FIELDS:
            with self.subTest("video " + name):
                t = Target()
                setattr(t.utils.ba.video, name, getattr(t.utils.ba.video, name) ^ 0x10)
                with self.assertRaisesRegex(ValueError, "boot_args video %s differs" % name):
                    run_intree(t)
                self.assertEqual(t.events, [])
        # fields that are not in the cross-check lists must really be absent from them
        self.assertEqual(set(hv_launch.BA_FIELDS) & set(hv_launch.VIDEO_FIELDS), set())
        t = Target()
        t.utils.get_adt = lambda: t.adt[:-1] + b"\x01"           # copy differs from a fresh read
        with self.assertRaisesRegex(ValueError, "ADT read from the target differs"):
            run_intree(t)
        self.assertEqual(t.events, [])

    def test_unsupported_revision_and_bad_adt_are_fatal(self):
        t = Target(ba_revision=4)
        with self.assertRaisesRegex(ValueError, "revision 4"):
            run_intree(t)
        self.assertEqual(t.events, [])
        t = Target()
        t.mem.write(t.adt_addr, b"\xff" * 64)
        t.utils.get_adt = lambda: t.mem.read(t.adt_addr, len(t.adt))
        with self.assertRaisesRegex(ValueError, "ADT walk failed"):
            run_intree(t)
        self.assertEqual(t.events, [])

    def test_staging_readback_failure_stops_before_the_adt_patch(self):
        t = Target()
        real = t._cwrite

        def corrupt(addr, data, progress=None):
            real(addr, data[:-1] + bytes([data[-1] ^ 1]), progress)

        t.utils.compressed_writemem = corrupt
        with self.assertRaisesRegex(ValueError, "staged image"):
            run_intree(t)
        self.assertEqual(t.writes_in(t.adt_addr, len(t.adt)), [])
        self.assertEqual(t.of("reload"), [])

    def check_raw_boot_args(self, t):
        staging = t.heap_events[0][1]
        want = bytearray(t.raw_ba)
        struct.pack_into("<Q", want, 0x20, 0x10001800000)         # the current top, kept
        self.assertEqual(t.mem.read(staging + 0x1C000, 0x480), bytes(want))

    def test_mutation_boot_args_rebuilt_instead_of_raw_is_caught(self):
        t = Target()
        run_intree(t)
        self.check_raw_boot_args(t)                              # the real code passes

        def rebuilt(raw, value):                                 # a "construct-style" rebuild
            out = bytearray(raw)
            struct.pack_into("<Q", out, 0x20, value)
            out[0x100:0x180] = bytes(0x80)
            return bytes(out)

        t = Target()
        with patch.object(C, "with_top_of_kernel_data", rebuilt):
            run_intree(t)
        with self.assertRaises(AssertionError):
            self.check_raw_boot_args(t)

    def test_mutation_adt_patch_touching_extra_bytes_is_refused(self):
        real = adt_patch.patch_value

        def sloppy(blob, path, prop, value):
            out, off, old = real(blob, path, prop, value)
            out = bytearray(out)
            out[off + 16] ^= 0xFF                                # one stray byte after the value
            return bytes(out), off, old

        t = Target()
        with patch.object(adt_patch, "patch_value", sloppy), \
                self.assertRaisesRegex(ValueError, "outside the SEPFW value"):
            run_intree(t)
        self.assertEqual(t.writes_in(t.adt_addr, len(t.adt)), [])
        self.assertEqual(t.events, [])        # refused by a pure check: not even slot 0 is painted

    def test_mutation_adjacent_regions_counted_as_overlap_is_caught(self):
        body = LayoutTests("test_each_overlap_fires_and_adjacency_does_not")
        body.test_each_overlap_fires_and_adjacency_does_not()   # passes as written
        with patch.object(C, "overlaps", lambda a, b: a[0] <= b[0] + b[1] and b[0] <= a[0] + a[1]):
            with self.assertRaises(AssertionError):
                body.test_each_overlap_fires_and_adjacency_does_not()

    # --- reload that does not bring the port back (item 8) -----------------------------
    LINE = ("reload() did not reopen the port (%s); handoff issued, live ADT patched: trying the "
            "descriptor-checked reconnect; if that fails POWER OFF and read the strip per "
            "hv-instructions.md")

    def test_a_reload_that_raises_uarttimeout_prints_one_sanitized_line_and_returns_the_plan(self):
        for mode in ("intree", "python"):
            with self.subTest(mode):
                t = Target()

                def boom(*args):
                    raise UartTimeout("Reconnection timed out: /dev/cu.usbmodemSECRET1")

                t.reload_effect = boom
                plan, out = run_chainload(mode, t)
                self.assertIn(self.LINE % "UartTimeout", out.splitlines())
                self.assertNotIn("usbmodem", out)
                self.assertNotIn("SECRET", out)
                self.assertEqual(len(t.of("reload")), 1)          # no second attempt
                self.assertEqual(plan.new_base, BASE)

    def test_other_reload_failures_are_reported_by_class_name_only(self):
        for error in (OSError("/dev/cu.usbmodemSECRET1 gone"), RuntimeError("x"),
                      ValueError("y"), ConnectionError("z")):
            with self.subTest(type(error).__name__):
                t = Target()
                t.reload_effect = lambda *a, e=error: (_ for _ in ()).throw(e)
                plan, out = run_chainload("intree", t)
                self.assertIn(self.LINE % type(error).__name__, out.splitlines())
                self.assertNotIn("SECRET", out)

    def test_a_global_alarm_during_reload_is_not_swallowed(self):
        for mode in ("intree", "python"):
            with self.subTest(mode):
                t = Target()

                def alarm(*args):
                    raise TimeoutError("preflight exceeded 300 seconds; do not automatically retry")

                t.reload_effect = alarm
                out = io.StringIO()
                with contextlib.redirect_stdout(out), self.assertRaises(TimeoutError):
                    if mode == "python":
                        hv_launch.chainload_python(t.iface, t.proxy, t.utils, bytes(IMAGE_LEN),
                                                   blob_api(), python_types(t))
                    else:
                        hv_launch.chainload_intree(t.iface, t.proxy, t.utils, bytes(IMAGE_LEN))
                self.assertNotIn("did not reopen the port", out.getvalue())

    def test_issue_reload_unit(self):
        calls, out = [], []
        hv_launch.issue_reload(SimpleNamespace(reload=lambda *a: calls.append(a)), (1, 2, 3), out.append)
        self.assertEqual((calls, out), ([(1, 2, 3)], []))
        for error, passes in ((TimeoutError("t"), True), (KeyboardInterrupt(), True),
                              (UartTimeout("u"), False), (OSError("o"), False)):
            def reload(*a, e=error):
                raise e
            if passes:
                with self.assertRaises(type(error)):
                    hv_launch.issue_reload(SimpleNamespace(reload=reload), (), out.append)
            else:
                hv_launch.issue_reload(SimpleNamespace(reload=reload), (), out.append)
        self.assertEqual(out, [self.LINE % "UartTimeout", self.LINE % "OSError"])

    # --- handoff text for the stock control build (item 9) ------------------------------------
    CONTROL = ("stock build paints no c-blocks: success is the bar only plus the USB port "
               "returning and the new-instance proof")

    def test_control_handoff_and_breadcrumb_text_never_promises_c_blocks(self):
        for mode in ("intree", "python"):
            with self.subTest(mode):
                _, out = run_chainload(mode, Target(), control=True)
                self.assertEqual(out.count(self.CONTROL), 2, out)   # Breadcrumbs: and Handoff.
                self.assertNotIn("all of 5-20 lit", out)
                self.assertNotIn("Success = bar", out)
                self.assertNotIn("then the new m1n1 lights slots 5-20", out)
                self.assertNotIn("the new m1n1 paints slots 5-20", out)
                _, out = run_chainload(mode, Target(), control=False)
                self.assertNotIn(self.CONTROL, out)
                self.assertIn("Success = bar (slots 0-4) + all of 5-20 lit", out)
                self.assertIn("the new m1n1 paints slots 5-20", out)

    def test_control_text_for_a_stub_that_cannot_paint(self):
        for vid in (video(stride=3202), video(width=300)):
            _, out = run_chainload("intree", Target(vid=vid), control=True)
            self.assertNotIn(self.CONTROL, out)              # no bar will appear, so don't say so
            self.assertIn("paints no c-blocks", out)
            self.assertIn("the new-instance proof", out)
            self.assertNotIn("at most the new m1n1 lights slots 5-20", out)
        self.assertEqual(hv_launch.breadcrumb_status(video(), True).count(self.CONTROL), 1)
        out = []
        hv_launch.announce_handoff(video(), out.append, True)
        self.assertEqual(len(out), 1)
        self.assertIn(self.CONTROL, out[0])

    # --- item 18 at the chainload level ----------------------------------------------------
    def test_an_oversized_stub_is_refused_before_any_write(self):
        for mode in ("intree", "python"):
            with self.subTest(mode):
                t = Target()
                big = lambda entry, paint=None: bytes(C.STUB_MAX + 8)      # noqa: E731
                with patch.object(hv_launch, "stub", big), \
                        self.assertRaisesRegex(ValueError, "more than the %d bytes reserved" % C.STUB_MAX):
                    run_chainload(mode, t)
                self.assertEqual(t.events, [])

    def test_a_stub_of_exactly_the_reserved_size_is_accepted(self):
        t = Target()
        exact = lambda entry, paint=None: bytes(C.STUB_MAX)             # noqa: E731
        with patch.object(hv_launch, "stub", exact):
            run_chainload("intree", t)
        staging = t.heap_events[0][1]
        self.assertEqual(t.mem.read(staging + 0x20000, C.STUB_MAX), bytes(C.STUB_MAX))
        self.assertEqual(t.heap_events[0][2], 0x20000 + C.STUB_MAX)     # the block holds all of it


class PythonModeTests(unittest.TestCase):
    SIZE = 0x28000      # SEPFW 0x14000+0x8000 -> RAMDisk 0x1c000+0x1000 -> TrustCache 0x20000+0x4000

    def run_python(self, t, control=False):
        return run_chainload("python", t, bytes(IMAGE_LEN), control)[1]

    def test_old_flow_still_works_and_shares_the_gate_and_stub(self):
        t = Target()
        out = self.run_python(t)
        staging = t.heap_events[0][1]
        size = self.SIZE
        self.assertEqual(t.of("write64"), [])
        self.assertEqual(len(t.of("push_adt")), 1)
        reloads = t.of("reload")
        self.assertEqual(len(reloads), 1)
        self.assertEqual(reloads[0][1:], (staging + size, BASE + 0x24000, staging, BASE, size))
        self.assertEqual(t.mm._properties["SEPFW"], (BASE + 0x14000, 0x8000))
        self.assertEqual(t.mm._properties["RAMDisk"], (BASE + 0x1C000, 0x1000))
        self.assertEqual(t.mm._properties["TrustCache"], (BASE + 0x20000, 0x4000))
        self.assertEqual(t.mm.BootArgs, (BASE + 0x24000, 0x4000))
        self.assertEqual(t.mm._types["SEPFW"], "T")
        paint = C.stub_paint(t.vid)
        code = C.stub(BASE + 0x800, paint)
        self.assertEqual(t.mem.read(staging + size, len(code)), code)
        self.assertLess(t.events.index(("push_adt",)), t.events.index(reloads[0]))
        # moved blobs are not reported as overwritten
        self.assertNotIn("NOTE: memory-map blob TrustCache", out)
        self.assertIn("Layout gate PASS", out)
        self.assertIn(GATE_FACTS, out)

    def test_adt_push_is_the_last_write_and_slot_2_is_painted_before_it(self):
        t = Target()
        out = self.run_python(t)
        staging = t.heap_events[0][1]
        size = self.SIZE
        push = t.events.index(("push_adt",))
        stub_write = next(i for i, e in enumerate(t.events)
                          if e[0] == "write" and e[1] == staging + size)
        stub_ic = next(i for i, e in enumerate(t.events)
                       if e[0] == "ic_ivau" and e[1] == staging + size)
        bootargs = next(i for i, e in enumerate(t.events)
                        if e[0] == "write" and e[1] == staging + 0x24000)
        reload_at = next(i for i, e in enumerate(t.events) if e[0] == "reload")
        self.assertLess(bootargs, stub_write)
        self.assertLess(stub_write, stub_ic)
        before = t.events[stub_ic + 1:push]
        self.assertEqual([e[0] for e in before], ["write"] * 24)             # slot 2 only, BEFORE the push
        self.assertEqual([(e[1], e[2]) for e in before], C.paint_rows(t.vid, 2))
        built = t.utils.adt.build()
        after = t.events[push + 1:reload_at]
        self.assertEqual(after, [("write", t.adt_addr, built), ("dc_cvau", t.adt_addr, len(built))])
        self.assertEqual(t.mem.read(t.adt_addr, len(built)), built)
        self.assertIn("Breadcrumbs: stub bar enabled", out)
        self.assertIn("Success = bar (slots 0-4) + all of 5-20 lit", out)

    def test_returns_the_plan_for_the_new_instance_proof(self):
        t = Target()
        types = {3: SimpleNamespace(build=lambda tba: b"ba")}
        with contextlib.redirect_stdout(io.StringIO()):
            plan = hv_launch.chainload_python(t.iface, t.proxy, t.utils, bytes(IMAGE_LEN),
                                              blob_api(), types)
        self.assertEqual((plan.new_base, plan.bootargs_off, plan.image_size),
                         (BASE, 0x24000, 0x28000))
        self.assertEqual(plan.new_base + plan.bootargs_off, t.of("reload")[0][2])

    def test_gate_applies_in_python_mode(self):
        t = Target(adt_addr=BASE + 0x4000)
        with self.assertRaisesRegex(ValueError, "layout gate FAILED"):
            self.run_python(t)
        self.assertEqual(t.events, [])

    def test_boot_args_signature_is_the_python_flows_own_planned_address(self):
        t = Target(ba_addr=BASE + 0x24000)                    # where THIS flow stages boot_args
        with self.assertRaisesRegex(ValueError, "destination overlaps the boot_args at the planned "
                                                "boot_args address.*second chainload"):
            self.run_python(t)
        self.assertEqual(t.events, [])
        t = Target(ba_addr=BASE + 0x1C000)                    # the in-tree address: only a note here
        out = self.run_python(t)
        self.assertIn("NOTE: live boot_args lies inside the destination", out)
        self.assertEqual(len(t.of("reload")), 1)

    # --- top_of_kernel_data: max(current, destination end), 16K aligned ------------------------
    @staticmethod
    def staged_top(t):
        staging = t.heap_events[0][1]
        return struct.unpack_from("<Q", t.mem.read(staging + 0x24000, 0x480), 0x20)[0]

    def test_staged_top_follows_the_same_rule(self):
        for top, want in ((0x10001800000, 0x10001800000),     # current top larger: kept
                          (0x10000C00000, 0x10001028000),     # destination end (BASE + 0x28000) wins
                          (0x10001800001, 0x10001804000)):    # aligned up
            with self.subTest(top=hex(top)):
                t = Target(top=top)
                self.run_python(t)
                self.assertEqual(self.staged_top(t), want)

    # --- the rebuilt ADT: size guard, readback, restore (item 14) --------------------------------
    def test_a_rebuilt_adt_larger_than_the_live_one_is_refused_before_any_write(self):
        t = Target()
        t.build_extra = bytes(16)
        with self.assertRaisesRegex(ValueError, r"rebuilt ADT \(0x[0-9a-f]+ bytes\) is larger than "
                                                r"the live ADT \(0x[0-9a-f]+ bytes\); nothing was "
                                                r"written"):
            self.run_python(t)
        self.assertEqual(t.events, [])                         # not even slot 0, no push
        self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)
        # equal size passes, smaller passes
        t = Target()
        self.run_python(t)
        self.assertEqual(len(t.of("push_adt")), 1)

    def corrupting_push(self, t, first_only=True):
        """The first write of the rebuilt ADT lands with one byte flipped."""
        real, state = t._write, {"n": 0}

        def writemem(addr, data):
            if addr == t.adt_addr:
                state["n"] += 1
                if state["n"] == 1 or not first_only:
                    data = data[:-1] + bytes([data[-1] ^ 0x55])
            real(addr, data)
        t.iface.writemem = writemem
        return state

    def test_a_push_that_does_not_read_back_is_restored_and_the_outcome_is_stated(self):
        t = Target()
        state = self.corrupting_push(t)
        with self.assertRaisesRegex(ValueError, "python mode rewrote the whole ADT; live ADT patch "
                                                "failed and was restored and verified"):
            self.run_python(t)
        self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)      # the original ADT is back
        self.assertEqual(state["n"], 2)                                  # the push and the restore
        self.assertEqual(t.of("reload"), [])

    def test_a_push_followed_by_a_dead_link_reports_not_restored(self):
        t = Target()
        real_write, real_read, dead = t._write, t._read, []

        def writemem(addr, data):
            if addr == t.adt_addr and dead:
                raise UartTimeout("dead /dev/cu.usbmodemSECRET1")
            real_write(addr, data)
            if addr == t.adt_addr:
                dead.append(True)

        def readmem(addr, size):
            if dead:
                raise UartTimeout("dead /dev/cu.usbmodemSECRET1")
            return real_read(addr, size)

        t.iface.writemem, t.iface.readmem = writemem, readmem
        with self.assertRaises(ValueError) as caught:
            self.run_python(t)
        text = str(caught.exception)
        self.assertIn("live ADT SEPFW patched and NOT restored: POWER OFF completely before any "
                      "further run", text)
        self.assertNotIn("SECRET", text)
        self.assertNotEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)   # still the rebuilt one
        self.assertEqual(t.of("reload"), [])

    def test_the_global_alarm_during_the_push_propagates_after_the_restore(self):
        t = Target()
        real_dc, raised = t.proxy.dc_cvau, []

        def dc_cvau(addr, size):
            if addr == t.adt_addr and not raised:
                raised.append(True)
                raise TimeoutError("preflight exceeded 300 seconds")
            real_dc(addr, size)

        t.proxy.dc_cvau = dc_cvau
        out = io.StringIO()
        types = python_types(t)
        with contextlib.redirect_stdout(out), self.assertRaises(TimeoutError):
            hv_launch.chainload_python(t.iface, t.proxy, t.utils, bytes(IMAGE_LEN), blob_api(), types)
        self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)      # restored, then propagated
        self.assertIn("python mode rewrote the whole ADT; live ADT patch failed and was restored "
                      "and verified", out.getvalue())
        self.assertEqual(t.of("reload"), [])

    def test_python_flow_is_also_protected_against_a_stub_that_cannot_hold_the_copy(self):
        t = Target()
        with patch.object(hv_launch, "stub", lambda e, p=None: bytes(C.STUB_MAX + 8)), \
                self.assertRaisesRegex(ValueError, "reserved after the image"):
            self.run_python(t)
        self.assertEqual(t.events, [])


def call_chainload(mode, t, out, control=False):
    """The real chainload function of the given mode with a caller-supplied out()."""
    image = bytes((i * 13 + 1) & 0xFF for i in range(IMAGE_LEN))
    if mode == "python":
        return hv_launch.chainload_python(t.iface, t.proxy, t.utils, image, blob_api(),
                                          python_types(t), out=out, control=control)
    return hv_launch.chainload_intree(t.iface, t.proxy, t.utils, image, out=out, control=control)


class HandoffWindowTests(unittest.TestCase):
    """Review R3: what happens between the verified live ADT write and proxy.reload, and when the
    restore itself is interrupted."""

    POST = {"intree": "Live ADT patched", "python": "Live ADT rewritten"}
    PREFIX = {"intree": "", "python": "python mode rewrote the whole ADT; "}
    RESTORED = "live ADT patch failed and was restored and verified"
    NOT_RESTORED = ("live ADT SEPFW patched and NOT restored: POWER OFF completely before any "
                    "further run")
    MODES = ("intree", "python")

    @staticmethod
    def adt_writes(t):
        return t.writes_in(t.adt_addr, len(t.adt))

    def recorder(self, t, raise_on=None, error=KeyboardInterrupt):
        """(lines, out): every printed line with the ADT-write and reload counts at that time."""
        lines = []

        def out(text):
            lines.append((text, len(self.adt_writes(t)), len(t.of("reload"))))
            if raise_on is not None and text.startswith(raise_on):
                raise error()
        return lines, out

    def second_write_interrupts(self, t, error=KeyboardInterrupt):
        """The first write into the live ADT lands, the second one (the restore) is interrupted."""
        real, state = t._write, {"n": 0}
        lo, hi = t.adt_addr, t.adt_addr + len(t.adt)

        def writemem(addr, data):
            if lo <= addr < hi:
                state["n"] += 1
                if state["n"] == 2:
                    raise error()
            real(addr, data)
        t.iface.writemem = writemem
        return state

    # --- the window is as small as it can be ---------------------------------------------------
    def check_window(self, mode):
        t = Target()
        lines, out = self.recorder(t)
        call_chainload(mode, t, out)
        texts = [l[0] for l in lines]
        # every host-only text, the handoff announcement included, comes BEFORE the live write
        handoff = next(l for l in lines if l[0].startswith("Handoff."))
        staged = next(l for l in lines if l[0].startswith("Everything staged"))
        self.assertEqual((handoff[1], handoff[2]), (0, 0))
        self.assertEqual((staged[1], staged[2]), (0, 0))
        self.assertLess(texts.index(staged[0]), texts.index(handoff[0]))
        # exactly ONE print sits between the verified write and the reload request
        after = [l for l in lines if l[1] >= 1]
        self.assertEqual([l[0] for l in after if l[0].startswith(self.POST[mode])], [after[0][0]])
        self.assertEqual(len(after), 1, after)
        self.assertEqual((after[0][1], after[0][2]), (1, 0))
        self.assertEqual(t.events[-1][0], "reload")

    def test_host_text_precedes_the_write_and_one_short_print_follows(self):
        for mode in self.MODES:
            self.check_window(mode)

    # --- an interruption before reload() is entered restores ------------------------------------
    def check_print_interrupt_restores(self, mode):
        t = Target()
        lines, out = self.recorder(t, raise_on=self.POST[mode])
        with self.assertRaises(KeyboardInterrupt):
            call_chainload(mode, t, out)
        texts = [l[0] for l in lines]
        self.assertIn(self.PREFIX[mode] + self.RESTORED, texts)
        self.assertNotIn(self.PREFIX[mode] + self.NOT_RESTORED, texts)
        self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)      # the original ADT again
        self.assertEqual(t.of("reload"), [])
        self.assertEqual(len(self.adt_writes(t)), 2)                      # the patch and its restore

    def test_an_interrupted_post_patch_print_restores_the_adt(self):
        for mode in self.MODES:
            self.check_print_interrupt_restores(mode)

    def test_an_alarm_in_the_post_patch_print_restores_it_too(self):
        for mode in self.MODES:
            t = Target()
            lines, out = self.recorder(t, raise_on=self.POST[mode], error=TimeoutError)
            with self.assertRaises(TimeoutError):
                call_chainload(mode, t, out)
            self.assertIn(self.PREFIX[mode] + self.RESTORED, [l[0] for l in lines])
            self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)

    def test_an_interrupt_just_before_reload_is_entered_restores(self):
        """commit_live_adt restores for anything raised before issue_reload() flagged its entry."""
        for mode in self.MODES:
            t = Target()
            lines, out = self.recorder(t)

            def early(proxy, args, out=None, entered=None):
                raise KeyboardInterrupt()               # before 'entered' is set
            with patch.object(hv_launch, "issue_reload", early), self.assertRaises(KeyboardInterrupt):
                call_chainload(mode, t, out)
            self.assertIn(self.PREFIX[mode] + self.RESTORED, [l[0] for l in lines])
            self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)
            self.assertEqual(t.of("reload"), [])

    # --- the restore is itself interrupted ---------------------------------------------------------
    def test_a_second_interrupt_during_the_restore_says_not_restored(self):
        for mode in self.MODES:
            t = Target()
            lines, out = self.recorder(t, raise_on=self.POST[mode])   # first Ctrl-C: the print
            state = self.second_write_interrupts(t)                   # second Ctrl-C: the restore
            with self.assertRaises(KeyboardInterrupt):
                call_chainload(mode, t, out)
            texts = [l[0] for l in lines]
            self.assertIn(self.PREFIX[mode] + self.NOT_RESTORED, texts)
            self.assertFalse([x for x in texts if "restored and verified" in x])
            self.assertEqual(state["n"], 2)
            self.assertNotEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)   # still patched
            self.assertEqual(t.of("reload"), [])

    def test_an_interrupted_restore_after_a_failed_write_says_not_restored(self):
        """The write path fails (the cache clean), then the restore is interrupted."""
        for mode in self.MODES:
            t = Target()
            lines, out = self.recorder(t)
            real_dc, raised = t.proxy.dc_cvau, []

            def dc_cvau(addr, size, real_dc=real_dc, raised=raised):
                if t.adt_addr <= addr < t.adt_addr + len(t.adt) and not raised:
                    raised.append(True)
                    raise UartTimeout("no reply")           # the cache clean after the patch fails
                real_dc(addr, size)
            t.proxy.dc_cvau = dc_cvau
            self.second_write_interrupts(t)                 # ... and the restore is interrupted
            with self.assertRaises(KeyboardInterrupt):      # NOT a ValueError saying 'restored'
                call_chainload(mode, t, out)
            texts = [l[0] for l in lines]
            self.assertIn(self.PREFIX[mode] + self.NOT_RESTORED, texts)
            self.assertFalse([x for x in texts if "restored and verified" in x])
            self.assertEqual(t.of("reload"), [])

    def test_an_alarm_during_the_restore_says_not_restored(self):
        """The global alarm is an Exception: it ends the restore as 'failed' (the interrupted
        write is reported as NOT restored) and the interruption that started the rollback is the
        one that propagates."""
        for mode in self.MODES:
            t = Target()
            lines, out = self.recorder(t, raise_on=self.POST[mode])
            self.second_write_interrupts(t, error=TimeoutError)
            with self.assertRaises(KeyboardInterrupt):
                call_chainload(mode, t, out)
            texts = [l[0] for l in lines]
            self.assertIn(self.PREFIX[mode] + self.NOT_RESTORED, texts)
            self.assertFalse([x for x in texts if "restored and verified" in x])
            self.assertNotEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)

    # --- once reload() is entered there is NO restore ------------------------------------------------
    def check_reload_interrupt_never_restores(self, mode, error):
        t = Target()
        t.reload_effect = lambda *a: (_ for _ in ()).throw(error())
        lines, out = self.recorder(t)
        with self.assertRaises(error):
            call_chainload(mode, t, out)
        self.assertEqual(len(t.of("reload")), 1)
        self.assertEqual(len(self.adt_writes(t)), 1)               # the patch, no restore write
        self.assertNotEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)
        self.assertNotIn("restored", "\n".join(l[0] for l in lines))

    def test_an_interrupt_inside_reload_never_restores(self):
        for mode in self.MODES:
            for error in (KeyboardInterrupt, TimeoutError):
                self.check_reload_interrupt_never_restores(mode, error)

    def test_an_ordinary_reload_failure_is_reported_and_never_restores(self):
        for mode in self.MODES:
            t = Target()
            t.reload_effect = lambda *a: (_ for _ in ()).throw(UartTimeout("timed out"))
            lines, out = self.recorder(t)
            call_chainload(mode, t, out)                                    # returns the plan
            self.assertEqual(len(self.adt_writes(t)), 1)
            self.assertIn(IntreeTests.LINE % "UartTimeout", [l[0] for l in lines])

    # --- mutations ----------------------------------------------------------------------------------
    def check_failed_write_then_interrupted_restore(self, mode):
        t = Target()
        lines, out = self.recorder(t)
        real_dc, raised = t.proxy.dc_cvau, []

        def dc_cvau(addr, size):
            if t.adt_addr <= addr < t.adt_addr + len(t.adt) and not raised:
                raised.append(True)
                raise UartTimeout("no reply")           # the cache clean after the patch fails
            real_dc(addr, size)
        t.proxy.dc_cvau = dc_cvau
        self.second_write_interrupts(t)
        with self.assertRaises(KeyboardInterrupt):
            call_chainload(mode, t, out)
        self.assertIn(self.PREFIX[mode] + self.NOT_RESTORED, [l[0] for l in lines])

    def check_interrupt_right_after_the_write_landed(self, mode):
        """The first Ctrl-C arrives the moment the live write has landed, before any readback."""
        t = Target()
        lines, out = self.recorder(t)
        real, state = t._write, {"n": 0}
        lo, hi = t.adt_addr, t.adt_addr + len(t.adt)

        def writemem(addr, data):
            real(addr, data)
            if lo <= addr < hi:
                state["n"] += 1
                if state["n"] == 1:
                    raise KeyboardInterrupt()
        t.iface.writemem = writemem
        with self.assertRaises(KeyboardInterrupt):
            call_chainload(mode, t, out)
        self.assertIn(self.PREFIX[mode] + self.RESTORED, [l[0] for l in lines])
        self.assertEqual(t.mem.read(t.adt_addr, len(t.adt)), t.adt)
        self.assertEqual(t.of("reload"), [])

    def test_an_interrupt_the_moment_the_write_landed_restores(self):
        for mode in self.MODES:
            self.check_interrupt_right_after_the_write_landed(mode)

    def test_mutated_commits_are_caught(self):
        def read_back(iface, proxy, state, write, want, clean):
            write()
            if iface.readmem(state.adt_addr, len(want)) != want:
                raise ValueError("mismatch")
            proxy.dc_cvau(*clean)

        def unguarded(iface, proxy, state, write, want, clean, restore, reload_args=None,
                      out=print, what="", message=""):
            read_back(iface, proxy, state, write, want, clean)       # no restore anywhere
            if reload_args is not None:
                out(message)
                hv_launch.issue_reload(proxy, reload_args, out)

        def split(iface, proxy, state, write, want, clean, restore, reload_args=None,
                  out=print, what="", message=""):
            # the previous shape: only the write is guarded, the print and reload are outside
            try:
                read_back(iface, proxy, state, write, want, clean)
            except BaseException:
                hv_launch.restore_live_adt(iface, proxy, state, restore)
                raise
            if reload_args is not None:
                out(message)
                hv_launch.issue_reload(proxy, reload_args, out)

        def always(iface, proxy, state, write, want, clean, restore, reload_args=None,
                  out=print, what="", message=""):
            try:
                read_back(iface, proxy, state, write, want, clean)
                if reload_args is not None:
                    out(message)
                    hv_launch.issue_reload(proxy, reload_args, out)
            except BaseException:
                # restores even when reload() was entered: the handoff may have happened
                hv_launch.restore_live_adt(iface, proxy, state, restore)
                out(what + "; " * bool(what) + hv_launch.ADT_RESTORED)
                raise

        self.check_print_interrupt_restores("intree")                # the real code passes
        self.check_reload_interrupt_never_restores("intree", KeyboardInterrupt)
        for name, mutant in (("unguarded", unguarded), ("split", split)):
            with self.subTest(name), patch.object(hv_launch, "commit_live_adt", mutant):
                with self.assertRaises(AssertionError):
                    self.check_print_interrupt_restores("intree")
        with patch.object(hv_launch, "commit_live_adt", always):
            for mode in self.MODES:
                with self.assertRaises(AssertionError):
                    self.check_reload_interrupt_never_restores(mode, KeyboardInterrupt)

    def test_a_commit_that_lets_an_interrupted_restore_escape_silently_is_caught(self):
        def silent(iface, proxy, state, write, want, clean, restore, reload_args=None,
                   out=print, what="", message=""):
            try:
                write()
                if iface.readmem(state.adt_addr, len(want)) != want:
                    raise ValueError("mismatch")
                proxy.dc_cvau(*clean)
            except BaseException:
                hv_launch.restore_live_adt(iface, proxy, state, restore)   # no outcome line
                raise

        for mode in self.MODES:
            self.check_failed_write_then_interrupted_restore(mode)   # the real code passes
        with patch.object(hv_launch, "commit_live_adt", silent):
            for mode in self.MODES:
                with self.assertRaises(AssertionError):
                    self.check_failed_write_then_interrupted_restore(mode)


class OperatorTextTests(unittest.TestCase):
    """Review R6: when the stub cannot paint, neither will the new m1n1 (same geometry guard)."""

    HOST = video(stride=3202)           # eligible for the host, not 4-byte aligned
    NONE = video(width=300)             # not eligible at all

    def test_m1n1_will_paint_is_exactly_the_stub_predicate_plus_its_ceilings(self):
        self.assertTrue(C.m1n1_will_paint(video()))
        for v in (video(stride=3202), video(stride=3201), video(width=300), video(base=0),
                  video(depth=24), video(height=20)):
            self.assertIsNone(C.stub_paint(v))
            self.assertFalse(C.m1n1_will_paint(v), vars(v))
        # whenever the stub cannot paint, the new m1n1 cannot either
        for v in (video(), video(stride=3202), video(base=0), video(width=100), video(depth=32),
                  video(height=0x4000), video(height=0x4001), video(stride=0x10000),
                  video(stride=0x10004)):
            if C.stub_paint(v) is None:
                self.assertFalse(C.m1n1_will_paint(v))
        # the patch's ceilings (ILINUX_CRUMB_MAX_STRIDE / _MAX_HEIGHT)
        self.assertEqual((C.M1N1_MAX_STRIDE, C.M1N1_MAX_HEIGHT), (0x10000, 0x4000))
        self.assertTrue(C.m1n1_will_paint(video(stride=0x10000)))
        self.assertFalse(C.m1n1_will_paint(video(stride=0x10004)))
        self.assertTrue(C.m1n1_will_paint(video(height=0x4000)))
        self.assertFalse(C.m1n1_will_paint(video(height=0x4001)))
        self.assertFalse(C.m1n1_will_paint(video(base=(1 << 64) - 0x1000, stride=3200, height=600)))

    def test_breadcrumb_line_says_the_new_m1n1_will_not_paint_either(self):
        line = hv_launch.breadcrumb_status(self.HOST)
        self.assertIn("the copy stub will NOT paint (row stride is not 4-byte aligned)", line)
        self.assertIn("the new m1n1 will not paint either", line)
        self.assertNotIn("may still paint", line)
        self.assertNotIn("the new m1n1 paints slots 5-20", line)
        line = hv_launch.breadcrumb_status(self.NONE)
        self.assertIn("the copy stub will NOT paint", line)
        self.assertIn("the new m1n1 will not paint either", line)
        self.assertIn("the strip is disabled", line)
        # the bar mode keeps its promise for a geometry the m1n1 guard accepts ...
        self.assertIn("the new m1n1 paints slots 5-20", hv_launch.breadcrumb_status(video()))
        # ... and does not make it when the guard's stride ceiling rejects it
        wide = video(stride=0x10004)
        self.assertIsNotNone(C.stub_paint(wide))
        line = hv_launch.breadcrumb_status(wide)
        self.assertIn("stub bar enabled", line)
        self.assertIn("the new m1n1 will NOT paint slots 5-20", line)
        self.assertNotIn("the new m1n1 paints slots 5-20", line)

    def test_handoff_announcement_never_promises_new_m1n1_blocks_without_a_stub_bar(self):
        for v in (self.HOST, self.NONE):
            out = []
            hv_launch.announce_handoff(v, out.append)
            self.assertEqual(len(out), 1)
            text = out[0]
            self.assertIn("The copy stub will NOT paint", text)
            self.assertIn("the new m1n1 will not paint either", text)
            self.assertNotIn("at most the new m1n1 lights slots 5-20", text)
            self.assertIn("only the USB port returning and the new-instance proof", text)
        out = []
        hv_launch.announce_handoff(video(stride=0x10004), out.append)
        self.assertIn("the new m1n1 will NOT paint", out[0])
        self.assertNotIn("all of 5-20 lit", out[0])
        self.assertIn("the bar only", out[0])

    def test_the_chainload_output_follows(self):
        for mode in ("intree", "python"):
            _, out = run_chainload(mode, Target(vid=self.HOST))
            crumbs = [l for l in out.splitlines() if l.startswith("Breadcrumbs:")]
            self.assertEqual(len(crumbs), 1)
            self.assertIn("the new m1n1 will not paint either", crumbs[0])
            handoff = [l for l in out.splitlines() if l.startswith("Handoff.")]
            self.assertEqual(len(handoff), 1)
            self.assertIn("the new m1n1 will not paint either", handoff[0])
            self.assertIn("new m1n1 will paint (its guard: stub_paint, stride <= 0x10000, height "
                          "<= 0x4000): no", out)
        # the control build never paints c-blocks, so its texts do not talk about the new m1n1
        _, out = run_chainload("intree", Target(vid=self.HOST), control=True)
        self.assertNotIn("will not paint either", "\n".join(
            l for l in out.splitlines() if l.startswith(("Breadcrumbs:", "Handoff."))))

    def test_an_unaligned_framebuffer_base_limits_the_new_m1n1_to_c0_to_c8(self):
        """From c9 on the MMU is on and the painter must map the framebuffer, which needs a 16K
        aligned base; it returns without painting otherwise (and so does every later step)."""
        aligned, unaligned = video(base=RAM + 0x3000000), video(base=RAM + 0x3000004)
        self.assertEqual(C.m1n1_painted_steps(aligned), 16)
        self.assertEqual(C.m1n1_painted_steps(unaligned), 9)
        self.assertEqual(C.M1N1_MMU_OFF_STEPS, 9)
        # nothing at all when the guard rejects the geometry
        for v in (video(stride=3202), video(width=300), video(stride=0x10004), video(base=0)):
            self.assertEqual(C.m1n1_painted_steps(v), 0)
        line = hv_launch.breadcrumb_status(unaligned)
        self.assertIn("stub bar enabled", line)
        self.assertIn("paints only c0-c8 (slots 5-13)", line)
        self.assertIn("c9-c15 (slots 14-20) will not paint", line)
        self.assertNotIn("the new m1n1 paints slots 5-20", line)
        out = []
        hv_launch.announce_handoff(unaligned, out.append)
        self.assertIn("slots 5-13 (steps c0-c8 only", out[0])
        self.assertIn("Success = bar (slots 0-4) + all of 5-13 lit", out[0])
        self.assertNotIn("all of 5-20 lit", out[0])
        # the aligned framebuffer keeps the full promise
        out = []
        hv_launch.announce_handoff(aligned, out.append)
        self.assertIn("Success = bar (slots 0-4) + all of 5-20 lit", out[0])
        # the layout report says so as a fact too
        self.assertIn("new m1n1 paints only c0-c8 (slots 5-13)",
                      "\n".join(C.video_report(unaligned)))
        self.assertNotIn("paints only c0-c8", "\n".join(C.video_report(aligned)))
        self.assertNotIn("paints only c0-c8", "\n".join(C.video_report(video(stride=3202))))
        # the control build never paints c-blocks: no claim about them
        self.assertNotIn("c0-c8", hv_launch.breadcrumb_status(unaligned, True))
        out = []
        hv_launch.announce_handoff(unaligned, out.append, True)
        self.assertNotIn("slots 5-13", out[0])
        # through a chainload run, both flows
        for mode in ("intree", "python"):
            _, text = run_chainload(mode, Target(vid=unaligned))
            self.assertIn("paints only c0-c8 (slots 5-13)", text)
            self.assertNotIn("Success = bar (slots 0-4) + all of 5-20 lit", text)

    def test_a_mutation_that_restores_the_old_promise_is_caught(self):
        old = ("Breadcrumbs: the copy stub will NOT paint (row stride is not 4-byte aligned): no "
               "bar. Host slots 0-2 may be erased by boot021's own redraw; the new m1n1 may still "
               "paint slots 5-20.")
        with patch.object(hv_launch, "breadcrumb_status", lambda video, control=False: old):
            with self.assertRaises(AssertionError):
                self.test_breadcrumb_line_says_the_new_m1n1_will_not_paint_either()


# === live orchestration with injected m1n1 client classes =================================
BOOT_MANIFEST = json.loads((HERE.parent / "boot" / "package-manifest.json").read_text())
HV_M = {"hv_version_marker": "##m1n1_ver##ilinux-57a9339-hv003", "hv_version_offset": 600000,
        "hv_single_cpu_offset": 700000, "hv_init_failed_offset": 700001}
GUEST_M = {"package": "ilinux-j716c-boot034",
           "m1n1_version_marker": BOOT_MANIFEST["m1n1_version_marker"],
           "m1n1_version_offset": BOOT_MANIFEST["m1n1_version_offset"]}


def mutated_hv_launch(*pairs):
    """A fresh module built from hv_launch.py's source with (old, new) text replacements applied.

    Every old string must occur exactly once, so a mutant that no longer applies is an error
    instead of a silent pass. With no pairs it is an unmodified copy.
    """
    source = Path(hv_launch.__file__).read_text()
    for old, new in pairs:
        assert source.count(old) == 1, "mutation does not apply: " + old
        source = source.replace(old, new)
    module = types.ModuleType("hv_launch_mutant")
    module.__file__ = hv_launch.__file__
    exec(compile(source, hv_launch.__file__, "exec"), module.__dict__)
    return module


class LiveHarness:
    """Fake client classes; target memory marker flips when a chainload is recorded.

    chip, stage ("boot021" is the installed object; anything else answers another marker) and
    alive (CPU ids whose smp_is_alive is true) parametrize the first safety gate.
    """

    def __init__(self, target=None, flags=(0, 0), chip=0x6050, stage="boot021", alive=()):
        self.log = []
        self.target = target or Target()
        self.stage = stage
        self.chip = chip
        self.alive = set(alive)
        self.flags = flags
        self.read8_calls = []         # every hv flag byte read
        self.bootargs_now = None      # what P_GET_BOOTARGS answers once a chainload "happened"
        self.new_instance = True      # False: the chainload silently did nothing
        self.hv_init_ok = False
        self.transports = []
        self.utils_built = 0
        self.logfiles = []            # what the HV was handed by set_logfile
        h = self
        t = self.target

        class Transport:
            def __init__(self):
                self.closed = False
                h.transports.append(self)

            def close(self):
                self.closed = True

        class Iface:
            def readmem(self, addr, size):
                if h.stage == "boot021":
                    want = (BOOT_MANIFEST["m1n1_version_marker"], BOOT_MANIFEST["m1n1_version_offset"])
                elif h.stage == "hv":
                    want = (HV_M["hv_version_marker"], HV_M["hv_version_offset"])
                else:
                    want = ("wrong", 1)
                if addr == BASE + want[1]:
                    return want[0].encode() + b"\0"
                return t.iface.readmem(addr, size)

            def writemem(self, addr, data):
                t.iface.writemem(addr, data)

        class Proxy:
            def __init__(self, iface):
                self.iface = iface

            def nop(self): pass
            def get_chipid(self): return h.chip
            def get_base(self): return BASE
            def smp_is_alive(self, cpu): return cpu in h.alive
            def read8(self, addr):
                h.read8_calls.append(addr)
                return h.flags[0] if addr == BASE + HV_M["hv_single_cpu_offset"] else h.flags[1]
            def get_bootargs(self):
                return h.bootargs_now if h.bootargs_now is not None else t.proxy.get_bootargs()
            def __getattr__(self, name):
                return getattr(t.proxy, name)

        class FakeHV:
            def __init__(self, *a):
                h.log.append("HV constructed")

            def init(self):
                h.log.append("hv.init")
                if not h.hv_init_ok:
                    raise RuntimeError("HV must not run in this test")

            def set_logfile(self, fd):
                h.logfiles.append(fd)

            def load_system_map(self, path):
                h.log.append("load_system_map")
                raise RuntimeError("full path reached the system map")

        def utils_factory(proxy, **kw):
            h.utils_built += 1
            return t.utils

        self.api = SimpleNamespace(
            opener=lambda device: (Transport(), Iface()), M1N1Proxy=Proxy, ProxyUtils=utils_factory,
            ProxyError=RuntimeError, HV=FakeHV, TraceMode=SimpleNamespace(OFF=0, RESERVED=1),
            IODEV=None, irange=lambda a, n: (a, n), blob_api=blob_api(),
            bootargs_types=python_types(t))
        self.files = {"m1n1.bin": b"STOCKBOOT021\0\0\0\0" * (IMAGE_LEN // 16)}
        self.hv_files = {"m1n1-hv.bin": b"HVBUILD\0" * (IMAGE_LEN // 8)}

    def chainload_recorder(self, name):
        def record(iface, proxy, utils, image, *a, **kw):
            self.log.append((name, bytes(image)))
            self.stage = "hv" if image == self.hv_files["m1n1-hv.bin"] else "boot021"
            if name == "python":
                plan = hv_launch.python_plan(utils, len(image), utils.base, blob_api())[0]
            else:
                plan = C.plan_layout(len(image), utils.base, self.target.sepfw)
            if self.new_instance:       # the new m1n1 reports the boot_args copy it was handed
                self.bootargs_now = plan.new_base + plan.bootargs_off
            return plan
        return record

    def run(self, logfile=None, module=None, **kw):
        out = io.StringIO()
        module = module or hv_launch
        with contextlib.redirect_stdout(out), \
             patch.object(module, "register_preflight",
                          side_effect=lambda u, e: self.log.append("preflight")), \
             patch.object(module, "chainload_intree", self.chainload_recorder("intree")), \
             patch.object(module, "chainload_python", self.chainload_recorder("python")), \
             patch.object(module, "reconnect", self.reconnect):
            rc = module.run_live("auto", self.files, self.hv_files, HV_M, logfile, "System.map",
                                 self.api, guest_manifest=GUEST_M, **kw)
        return rc, out.getvalue()

    def reload_effect(self, stub, bootargs, staging, new_base, size):
        """What the new m1n1 would report: the boot_args copy it was handed, the image's marker."""
        if self.new_instance:
            self.bootargs_now = bootargs
        staged = self.target.mem.read(staging, len(self.hv_files["m1n1-hv.bin"]))
        self.stage = "hv" if staged == self.hv_files["m1n1-hv.bin"] else "boot021"

    def run_real(self, reconnect=None, module=None, logfile=None, reload_error=None, **kw):
        """run_live with the REAL chainload functions against the recording Target.

        proxy.reload gets a side effect (reload_effect) that sets bootargs_now from the argument
        it was called with, then raises reload_error when one is given (the new instance did
        come up, only reload()'s own wait did not see the port); only the register census and
        the port reopen are replaced.
        """
        out = io.StringIO()
        module = module or hv_launch

        def effect(*args):
            self.reload_effect(*args)
            if reload_error is not None:
                raise reload_error
        self.target.reload_effect = effect
        with contextlib.redirect_stdout(out), \
             patch.object(module, "register_preflight",
                          side_effect=lambda u, e: self.log.append("preflight")), \
             patch.object(module, "reconnect", reconnect or self.reconnect):
            rc = module.run_live("auto", self.files, self.hv_files, HV_M, logfile, "System.map",
                                 self.api, guest_manifest=GUEST_M, **kw)
        return rc, out.getvalue()

    def reconnect(self, device, make_proxy, opener=None, **kw):
        transport, iface = opener(device)
        return transport, iface, make_proxy(iface)


class LiveTests(unittest.TestCase):
    def test_chainload_only_never_constructs_hv(self):
        h = LiveHarness()
        rc, out = h.run(chainload_only=True)
        self.assertEqual(rc, 0)
        self.assertIn("CHAINLOAD PASS", out)
        self.assertEqual(h.log, ["preflight", ("intree", h.hv_files["m1n1-hv.bin"])])
        self.assertNotIn("HV constructed", h.log)
        self.assertTrue(all(t.closed for t in h.transports))

    def test_chainload_only_python_mode_dispatches(self):
        h = LiveHarness()
        rc, _ = h.run(chainload_only=True, mode="python")
        self.assertEqual(rc, 0)
        self.assertEqual(h.log[1][0], "python")

    def test_chainload_only_checks_the_marker(self):
        h = LiveHarness()
        real = h.chainload_recorder

        def wrong_stage(name):
            record = real(name)

            def go(*a, **kw):
                plan = record(*a, **kw)
                h.stage = "other"          # a new instance, but not the expected build
                return plan
            return go

        h.chainload_recorder = wrong_stage
        with self.assertRaisesRegex(ValueError, "does not match"):
            h.run(chainload_only=True)

    def test_chainload_only_does_not_read_or_claim_the_hv_flags(self):
        # The old pre-init read looked at two BSS bytes that are zero in any zeroed
        # memory; it could not fail meaningfully. The flags are only checked on the
        # full path, after hv.init().
        for flags in ((0, 0), (7, 0), (0, 1), (1, 1)):
            h = LiveHarness(flags=flags)
            rc, out = h.run(chainload_only=True)
            self.assertEqual(rc, 0, flags)
            self.assertEqual(h.read8_calls, [], flags)
            self.assertNotIn("implausible", out)
            self.assertNotIn("flag bytes", out)
            self.assertIn("hypervisor flags (single-CPU, ECV timer traps) are NOT checked here, "
                          "only on the full path after hv.init()", out)
        self.assertFalse(hasattr(hv_launch, "check_hv_flags_preinit"))

    def test_control_stock_chainloads_the_guest_m1n1_and_checks_boot021(self):
        h = LiveHarness()
        rc, out = h.run(chainload_only=True, control="stock")
        self.assertEqual(rc, 0)
        self.assertEqual(h.log, ["preflight", ("intree", h.files["m1n1.bin"])])   # register preflight on
        self.assertIn("stock boot021", out)
        self.assertEqual(h.read8_calls, [])                       # hv flag checks skipped
        self.assertNotIn("hv flag", out)
        self.assertIn("hypervisor flags are only checked on the full path after hv.init()", out)
        # a wrong marker afterwards is fatal, and the hv marker is NOT what is checked
        h = LiveHarness()
        h.hv_files = {"m1n1-hv.bin": h.files["m1n1.bin"]}          # recorder would flip stage to hv
        with self.assertRaisesRegex(ValueError, "does not match"):
            h.run(chainload_only=True, control="stock")

    def test_control_banner_says_power_cycle_between_runs(self):
        h = LiveHarness()
        rc, out = h.run(chainload_only=True, control="stock")
        self.assertIn("only ONE chainload can happen per boot of the original instance", out)
        self.assertIn("POWER-CYCLE between chainload runs", out)
        self.assertIn("still painting the strip", out)
        self.assertIn("power-cycle before the next chainload run", out)
        # not shown for the hv session
        _, out = LiveHarness().run(chainload_only=True)
        self.assertNotIn("POWER-CYCLE", out)

    # --- new-instance proof ---------------------------------------------------------
    def test_new_instance_proof_passes_with_the_staged_boot_args_pointer(self):
        for kwargs in ({}, {"mode": "python"}, {"control": "stock"}):
            with self.subTest(kwargs):
                h = LiveHarness()
                rc, out = h.run(chainload_only=True, **kwargs)
                self.assertEqual(rc, 0)
                self.assertRegex(out, r"New-instance proof PASS: boot_args pointer 0x[0-9a-f]+ is the "
                                      r"copy staged by this chainload\.")
                # the proof comes before the marker check
                self.assertLess(out.index("New-instance proof PASS"), out.index("Target PASS: "
                                + ("stock boot021" if kwargs.get("control") else "hv003")))

    def test_new_instance_proof_value_is_new_base_plus_bootargs_offset(self):
        h = LiveHarness()
        rc, out = h.run(chainload_only=True)
        plan = C.plan_layout(len(h.hv_files["m1n1-hv.bin"]), BASE, h.target.sepfw)
        want = plan.new_base + plan.bootargs_off
        self.assertEqual(h.bootargs_now, want)
        self.assertIn("boot_args pointer 0x%x is the copy" % want, out)
        self.assertNotEqual(want, h.target.ba_addr)               # the old instance reports another one

    def test_original_instance_still_answering_fails_the_proof_hard(self):
        for kwargs in ({}, {"mode": "python"}, {"control": "stock"}):
            with self.subTest(kwargs):
                h = LiveHarness()
                h.new_instance = False                           # the chainload silently did nothing
                with self.assertRaisesRegex(
                        ValueError, "new-instance proof FAILED: boot_args pointer 0x[0-9a-f]+ is "
                                    "still the original instance's"):
                    h.run(chainload_only=True, **kwargs)

    def test_control_marker_alone_cannot_tell_old_from_new(self):
        """Why the proof exists: the stock control's marker is identical before and after."""
        h = LiveHarness()
        h.new_instance = False
        with self.assertRaisesRegex(ValueError, "new-instance proof FAILED"):
            h.run(chainload_only=True, control="stock")
        # with the marker check alone (proof disabled) the run would have passed
        h = LiveHarness()
        h.new_instance = False
        with patch.object(hv_launch, "prove_new_instance"):
            rc, _ = h.run(chainload_only=True, control="stock")
        self.assertEqual(rc, 0)

    def test_unexpected_boot_args_pointer_fails_the_proof(self):
        h = LiveHarness()
        real = h.chainload_recorder

        def elsewhere(name):
            record = real(name)

            def go(*a, **kw):
                plan = record(*a, **kw)
                h.bootargs_now = plan.new_base + plan.bootargs_off + 0x4000    # not the staged copy
                return plan
            return go

        h.chainload_recorder = elsewhere
        with self.assertRaisesRegex(ValueError, "expected the staged copy at 0x"):
            h.run(chainload_only=True)

    def test_proof_is_required_before_the_full_path_continues(self):
        h = LiveHarness()
        h.new_instance = False
        with self.assertRaisesRegex(ValueError, "new-instance proof FAILED"):
            h.run()
        self.assertNotIn("HV constructed", h.log)                # never reached hv.init()

    def test_proof_unit(self):
        plan = C.plan_layout(0x10000, BASE, (RAM + 0x6000000, 0x8000))
        want = BASE + plan.bootargs_off
        old = RAM + 0x1FF0000
        out = []
        proxy = SimpleNamespace(get_bootargs=lambda: want)
        hv_launch.prove_new_instance(proxy, plan, old, out.append)
        self.assertEqual(len(out), 1)
        for got, message in ((old, "still the original instance"), (want + 8, "expected the staged copy"),
                             (0, "expected the staged copy")):
            with self.assertRaisesRegex(ValueError, message):
                hv_launch.prove_new_instance(SimpleNamespace(get_bootargs=lambda g=got: g), plan,
                                             old, out.append)
        # a plan whose staged copy sits at the original boot_args address proves nothing
        with self.assertRaisesRegex(ValueError, "proof impossible"):
            hv_launch.prove_new_instance(proxy, plan, want, out.append)

    def test_second_chainload_in_one_power_cycle_is_refused_by_the_gate(self):
        """After a chainload the live boot_args sit inside the next destination."""
        plan = C.plan_layout(IMAGE_LEN, BASE, (RAM + 0x6000000, 0x8000))
        t = Target(ba_addr=BASE + plan.bootargs_off)
        with self.assertRaisesRegex(ValueError, "destination overlaps the boot_args.*"
                                                "second chainload in the same power cycle"):
            run_intree(t)
        self.assertEqual(t.events, [])

    # --- layout-only --------------------------------------------------------------
    def test_layout_only_writes_nothing_and_skips_the_preflight(self):
        h = LiveHarness()
        rc, out = h.run(layout_only=True)
        self.assertEqual(rc, 0)
        self.assertIn("LAYOUT PASS", out)
        self.assertIn(GATE_FACTS, out)
        self.assertEqual(h.target.events, [])                      # no write of any kind
        self.assertEqual(h.log, [])                                # no preflight, no chainload
        self.assertIn("REGION", out)

    def test_layout_only_fail_exits_3_and_still_writes_nothing(self):
        h = LiveHarness(Target(adt_addr=BASE + 0x4000))
        rc, out = h.run(layout_only=True)
        self.assertEqual(rc, 3)                      # 2 stays "argument error"
        self.assertEqual(rc, hv_launch.EXIT_LAYOUT_FAIL)
        self.assertIn("LAYOUT FAIL", out)
        self.assertEqual(h.target.events, [])

    def test_layout_only_python_mode_uses_the_blob_plan(self):
        h = LiveHarness()
        rc, out = h.run(layout_only=True, mode="python")
        self.assertEqual((rc, h.target.events), (0, []))
        self.assertIn("LAYOUT PASS", out)
        self.assertIn("0x0000010001000000 0x0000010001028000", out)   # six-blob size 0x28000
        self.assertNotIn("blob TrustCache", out)                      # moved, not overwritten
        h = LiveHarness()
        rc, out = h.run(layout_only=True)
        self.assertIn("0x0000010001000000 0x0000010001020000", out)   # in-tree size 0x20000
        self.assertIn("blob TrustCache", out)

    def test_layout_only_prints_framebuffer_stub_and_top_of_kernel_data_facts(self):
        vid = video(depth=30 | (1 << 16))
        h = LiveHarness(Target(vid=vid))
        rc, out = h.run(layout_only=True)
        self.assertEqual((rc, h.target.events), (0, []))
        fb = vid.base
        self.assertIn("framebuffer base 0x%x stride 0xc80 width 0x320 height 0x258" % fb, out)
        self.assertIn("framebuffer depth field 0x1001e, bpp 0x1e, RETINA flag (0x10000) set", out)
        self.assertIn("framebuffer base 16K aligned: yes", out)
        self.assertIn("breadcrumb strip eligible for the host (video_ok): yes", out)
        self.assertIn("stub bar will paint (stub_paint): yes (strip origin 0x%x, row stride 0xc80)"
                      % (fb + 4 * 3200 + 8 * 4), out)
        self.assertIn("new m1n1 will paint (its guard: stub_paint, stride <= 0x10000, height <= "
                      "0x4000): yes", out)
        top, end = RAM + 0x1800000, BASE + 0x20000
        self.assertIn("top_of_kernel_data (current)    0x%016x" % top, out)
        self.assertIn("destination end                 0x%016x BELOW the current top by 0x%x"
                      % (end, top - end), out)
        self.assertIn("top_of_kernel_data (new)        0x%016x = the current top (the new heap "
                      "starts where the old one did)" % top, out)
        self.assertNotIn("destination end (new top)", out)
        # names and sizes of blobs the destination covers (already NOTEs)
        self.assertIn("NOTE: memory-map blob TrustCache (0x4000 bytes at 0x%x) lies in the "
                      "destination and will be overwritten" % (BASE + 0x8000), out)
        for line in out.splitlines():
            self.assertRegex(line, r"^[\x20-\x7e]*$")
        self.assertNotIn("SECRETMARKER", out)

    def test_layout_only_reports_the_non_eligible_and_unaligned_cases(self):
        h = LiveHarness(Target(vid=video(base=RAM + 0x3000004, stride=3202)))
        rc, out = h.run(layout_only=True)
        self.assertEqual(rc, 0)
        self.assertIn("framebuffer base 16K aligned: no", out)
        self.assertIn("RETINA flag (0x10000) clear", out)
        self.assertIn("eligible for the host (video_ok): yes", out)
        self.assertIn("stub bar will paint (stub_paint): no", out)
        self.assertIn("height <= 0x4000): no", out)          # the new m1n1 will not paint either
        h = LiveHarness(Target(vid=video(width=200)))
        rc, out = h.run(layout_only=True)
        self.assertIn("eligible for the host (video_ok): no", out)

    def test_layout_only_no_longer_notes_structures_between_the_new_and_the_current_top(self):
        # the new top is never below the current one, so nothing can fall between them
        h = LiveHarness(Target(ba_addr=RAM + 0x1500000))
        rc, out = h.run(layout_only=True)
        self.assertEqual(rc, 0)
        self.assertNotIn("between the new and the current", out)
        self.assertNotIn("NOTE: boot_args", out)

    def test_layout_only_notes_a_live_boot_args_inside_the_destination_and_passes(self):
        h = LiveHarness(Target(ba_addr=BASE + 0x2000))
        rc, out = h.run(layout_only=True)
        self.assertEqual((rc, h.target.events), (0, []))
        self.assertIn("NOTE: live boot_args lies inside the destination; it will be overwritten, "
                      "m1n1 already copied it", out)
        self.assertIn("LAYOUT PASS", out)
        # a second chainload's signature (the planned address) fails the layout check
        h = LiveHarness(Target(ba_addr=BASE + 0x1C000))
        rc, out = h.run(layout_only=True)
        self.assertEqual((rc, h.target.events), (3, []))
        self.assertIn("PROBLEM: destination overlaps the boot_args at the planned boot_args address",
                      out)

    def test_layout_only_says_exactly_what_it_does_to_the_target(self):
        h = LiveHarness()
        rc, out = h.run(layout_only=True)
        want = ("Layout check only: no memory writes; ProxyUtils issues two m1n1 heap-bookkeeping "
                "requests (heapblock_alloc(0), heapblock_set_limit).")
        self.assertIn(want, out.splitlines())
        for stale in ("never written", "read, never", "nothing was written"):
            self.assertNotIn(stale, out)
        h = LiveHarness(Target(adt_addr=BASE + 0x4000))
        rc, out = h.run(layout_only=True)
        self.assertEqual(rc, 3)
        self.assertIn("LAYOUT FAIL: no memory was written to the target.", out)
        for doc in (hv_launch.__doc__, hv_launch.layout_report.__doc__):
            self.assertIn("heapblock_alloc(0)", doc)
            self.assertIn("heapblock_set_limit", doc)
            self.assertNotIn("never written", doc)
            self.assertNotIn("writes nothing", doc)

    def test_layout_only_reports_the_staging_overlap_as_a_note(self):
        top = RAM + 0x1010000
        h = LiveHarness(Target(top=top, heap=top))
        rc, out = h.run(layout_only=True)
        self.assertEqual((rc, h.target.events), (0, []))
        self.assertIn("NOTE: destination overlaps the start of the staging block; safe: ascending "
                      "copy, destination below staging, stub above destination end", out)
        self.assertIn("LAYOUT PASS", out)

    # --- full path ------------------------------------------------------------------
    def test_full_path_constructs_hv_after_the_chainload(self):
        h = LiveHarness()
        with self.assertRaisesRegex(RuntimeError, "HV must not run"):
            h.run()
        self.assertEqual(h.log[:3], ["preflight", ("intree", h.hv_files["m1n1-hv.bin"]),
                                     "HV constructed"])
        self.assertIn("hv.init", h.log)

    # --- the first safety gate of run_live (item 11) ----------------------------------------
    def check_first_gate(self, message, **harness):
        """Every live mode stops at check_target BEFORE the register census and writes nothing."""
        for kw in ({"chainload_only": True}, {"chainload_only": True, "control": "stock"}, {},
                   {"layout_only": True}, {"chainload_only": True, "mode": "python"}):
            # no subTest here: the mutation tests below need a failure to raise
            h = LiveHarness(**harness)
            with self.assertRaisesRegex(ValueError, message):
                h.run(**kw)
            self.assertEqual(h.log, [], kw)                    # register_preflight never ran
            self.assertEqual(h.target.events, [], kw)          # zero target writes
            self.assertEqual(h.target.heap_events, [], kw)     # no staging block, no ADT work
            self.assertEqual(h.utils_built, 0, kw)             # not even ProxyUtils
            self.assertEqual(h.read8_calls, [], kw)
            self.assertTrue(h.transports and all(t.closed for t in h.transports), kw)

    def test_wrong_chip_stops_at_the_first_gate(self):
        for chip in (0x6031, 0x6000, 0):
            self.check_first_gate("target chip is not t6050", chip=chip)

    def test_wrong_m1n1_marker_stops_at_the_first_gate(self):
        for stage in ("other", "hv"):                  # another build, or the hv build already running
            self.check_first_gate("target m1n1 does not match ##m1n1_ver##ilinux-57a9339-boot021",
                                  stage=stage)

    def test_a_started_secondary_stops_at_the_first_gate(self):
        for alive in ({1}, {17}, {31}):
            self.check_first_gate("secondary already started; restart the fresh m1n1 entry",
                                  alive=alive)

    def test_first_gate_order_is_chip_then_marker_then_secondaries(self):
        h = LiveHarness(chip=0x6031, stage="other", alive={1})
        with self.assertRaisesRegex(ValueError, "target chip is not t6050"):
            h.run(chainload_only=True)
        h = LiveHarness(stage="other", alive={1})
        with self.assertRaisesRegex(ValueError, "target m1n1 does not match"):
            h.run(chainload_only=True)

    def test_mutation_without_the_first_gate_is_caught(self):
        with patch.object(hv_launch, "check_target", lambda *a: None):
            with self.assertRaises(AssertionError):
                self.check_first_gate("target chip is not t6050", chip=0x6031)
        # a gate placed after the census would also be caught: preflight is in the log then
        h = LiveHarness(chip=0x6031)
        real = hv_launch.check_target

        def late(iface, proxy, base, marker, offset):
            h.log.append("late check")
            return real(iface, proxy, base, marker, offset)
        with patch.object(hv_launch, "check_target", late):
            with self.assertRaises(ValueError):
                h.run(chainload_only=True)
        self.assertEqual(h.log, ["late check"])

    # --- the real chainload functions through run_live (item 12) ---------------------------------
    def test_real_intree_chainload_through_run_live_proves_the_new_instance(self):
        h = LiveHarness()
        rc, out = h.run_real(chainload_only=True)
        self.assertEqual(rc, 0)
        want = BASE + 0x1C000          # new_base + bootargs_off for a 0x10000 image, written out
        reloads = h.target.of("reload")
        self.assertEqual(len(reloads), 1)
        stub_addr = h.target.heap_events[0][1] + 0x20000
        self.assertEqual(reloads[0][1:], (stub_addr, want, h.target.heap_events[0][1], BASE, 0x20000))
        self.assertEqual(h.bootargs_now, want)               # what the new m1n1 reported
        self.assertIn("New-instance proof PASS: boot_args pointer 0x%x is the copy staged by this "
                      "chainload." % want, out)
        self.assertIn("CHAINLOAD PASS: hv003 answered after the chainload, new instance proven", out)
        t = h.target
        self.assertEqual(len(t.writes_in(t.adt_addr, len(t.adt))), 1)    # the 16-byte patch only
        self.assertEqual(t.of("push_adt"), [])
        self.assertEqual(h.log, ["preflight"])
        self.assertTrue(all(tr.closed for tr in h.transports))

    def test_real_python_chainload_through_run_live_proves_the_new_instance(self):
        h = LiveHarness()
        rc, out = h.run_real(chainload_only=True, mode="python")
        self.assertEqual(rc, 0)
        want = BASE + 0x24000
        reloads = h.target.of("reload")
        self.assertEqual(len(reloads), 1)
        self.assertEqual(reloads[0][2], want)
        self.assertEqual(h.bootargs_now, want)
        self.assertIn("New-instance proof PASS: boot_args pointer 0x%x is the copy staged by this "
                      "chainload." % want, out)
        self.assertEqual(len(h.target.of("push_adt")), 1)
        self.assertEqual(h.target.of("write64"), [])

    def test_real_control_chainload_through_run_live(self):
        for mode in ("intree", "python"):          # control must reach BOTH chainload functions
            h = LiveHarness()
            rc, out = h.run_real(chainload_only=True, control="stock", mode=mode)
            self.assertEqual(rc, 0, mode)
            self.assertEqual(h.stage, "boot021")              # the staged image was the stock one
            self.assertEqual(out.count("stock build paints no c-blocks: success is the bar only "
                                       "plus the USB port returning and the new-instance proof"),
                             2, mode)
            self.assertNotIn("all of 5-20 lit", out)
            self.assertIn("New-instance proof PASS", out)
            # the hv session promises the c-blocks and never the control sentence
            h = LiveHarness()
            rc, out = h.run_real(chainload_only=True, mode=mode)
            self.assertIn("Success = bar (slots 0-4) + all of 5-20 lit", out)
            self.assertNotIn("stock build paints no c-blocks", out)

    def test_real_chainload_stops_when_the_old_instance_still_answers(self):
        h = LiveHarness()
        h.new_instance = False
        with self.assertRaisesRegex(ValueError, "new-instance proof FAILED"):
            h.run_real(chainload_only=True)

    def test_mutated_argument_order_in_run_live_is_caught_by_the_real_chainload(self):
        # the unmodified copy passes (the mutation harness itself is sound) ...
        h = LiveHarness()
        rc, _ = h.run_real(module=mutated_hv_launch(), chainload_only=True)
        self.assertEqual(rc, 0)
        h = LiveHarness()
        rc, _ = h.run_real(module=mutated_hv_launch(), chainload_only=True, mode="python")
        self.assertEqual(rc, 0)
        # ... and swapping iface and proxy, or the blob API and the boot_args types, does not
        swapped_intree = mutated_hv_launch(
            ("plan = chainload_intree(iface, proxy, utils, image, control=bool(control))",
             "plan = chainload_intree(proxy, iface, utils, image, control=bool(control))"))
        with self.assertRaises(Exception):
            LiveHarness().run_real(module=swapped_intree, chainload_only=True)
        swapped_python = mutated_hv_launch(
            ("plan = chainload_python(iface, proxy, utils, image, api.blob_api, api.bootargs_types,",
             "plan = chainload_python(iface, proxy, utils, image, api.bootargs_types, api.blob_api,"))
        with self.assertRaises(Exception):
            LiveHarness().run_real(module=swapped_python, chainload_only=True, mode="python")
        # image and control swapped: the control would chainload the hv build or vice versa
        wrong_image = mutated_hv_launch(
            ('image = files["m1n1.bin"] if control else hv_files["m1n1-hv.bin"]',
             'image = hv_files["m1n1-hv.bin"] if control else files["m1n1.bin"]'))
        h = LiveHarness()
        with self.assertRaisesRegex(ValueError, "does not match"):
            h.run_real(module=wrong_image, chainload_only=True)

    # --- reload() that does not bring the port back (item 8) -----------------------------------
    LINE = IntreeTests.LINE

    def test_reload_timeout_followed_by_a_good_reconnect_still_passes(self):
        h = LiveHarness()
        rc, out = h.run_real(chainload_only=True,
                             reload_error=UartTimeout("Reconnection timed out /dev/cu.usbmodemSECRET1"))
        self.assertEqual(rc, 0)
        lines = out.splitlines()
        self.assertIn(self.LINE % "UartTimeout", lines)
        self.assertLess(lines.index(self.LINE % "UartTimeout"),
                        next(i for i, l in enumerate(lines) if l.startswith("Chainloaded ")))
        self.assertIn("New-instance proof PASS", out)
        self.assertNotIn("SECRET", out)
        self.assertEqual(len(h.target.of("reload")), 1)

    def test_reload_timeout_followed_by_a_failed_reconnect_says_power_off(self):
        real = hv_launch.reconnect

        def failing(device, make_proxy, opener=None, **kw):
            now = [0.0]

            def bad_opener(d):
                raise OSError("gone /dev/cu.usbmodemSECRET1")
            return real(device, make_proxy, wait=30, opener=bad_opener,
                        sleep=lambda s: now.__setitem__(0, now[0] + s), clock=lambda: now[0])

        h = LiveHarness()
        with self.assertRaises(ValueError) as caught:
            h.run_real(chainload_only=True, reconnect=failing,
                       reload_error=UartTimeout("Reconnection timed out"))
        text = str(caught.exception)
        self.assertIn("m1n1 did not answer after chainload; POWER OFF completely and read the strip "
                      "per hv-instructions.md", text)
        self.assertNotIn("SECRET", text)
        self.assertEqual(len(h.target.of("reload")), 1)
        t = h.target
        off = adt_patch.locate(t.adt, "/chosen/memory-map", "SEPFW")[0]
        self.assertEqual(t.mem.read(t.adt_addr + off, 16), struct.pack("<QQ", BASE + 0x14000, 0x8000))

    def test_reload_alarm_is_not_turned_into_a_reconnect(self):
        calls = []
        h = LiveHarness()
        with self.assertRaises(TimeoutError):
            h.run_real(chainload_only=True, reconnect=lambda *a, **k: calls.append(1),
                       reload_error=TimeoutError("preflight exceeded 300 seconds"))
        self.assertEqual(calls, [])

    # --- the log file (item 15) --------------------------------------------------------------------
    def full_path_harness(self):
        h = LiveHarness(flags=(1, 0))
        h.hv_init_ok = True
        return h

    def check_log_is_exclusive(self, module=None):
        with tempfile.TemporaryDirectory() as d:
            existing = Path(d) / "events.log"
            existing.write_text("earlier evidence\n")
            h = self.full_path_harness()
            try:
                with self.assertRaises(FileExistsError):
                    h.run(logfile=existing, module=module)
            finally:
                for fd in h.logfiles:
                    fd.close()
            self.assertEqual(existing.read_text(), "earlier evidence\n")    # never truncated
            self.assertEqual(h.logfiles, [])

    def test_an_existing_log_file_is_never_truncated(self):
        self.check_log_is_exclusive()
        with tempfile.TemporaryDirectory() as d:
            new = Path(d) / "new.log"
            h = self.full_path_harness()
            with self.assertRaisesRegex(RuntimeError, "reached the system map"):
                h.run(logfile=new)
            self.assertTrue(new.exists())
            self.assertEqual(len(h.logfiles), 1)              # the HV was handed the handle ...
            self.assertEqual(h.logfiles[0].mode, "x")          # ... created exclusively ...
            self.assertTrue(h.logfiles[0].closed)              # ... and it is closed at the end
            self.assertEqual(new.read_text(), "")

    def test_mutation_log_opened_with_w_truncates_and_is_caught(self):
        mutant = mutated_hv_launch(('log_handle = logfile.open("x")',
                                    'log_handle = logfile.open("w")'))
        with self.assertRaises((AssertionError, RuntimeError)):
            self.check_log_is_exclusive(module=mutant)

    def test_the_log_is_created_before_the_first_target_write(self):
        class Unopenable:
            def open(self, mode):
                raise OSError(28, "No space left on device")      # e.g. the disk filled up
        h = self.full_path_harness()
        with self.assertRaises(OSError):
            h.run(logfile=Unopenable())
        self.assertEqual(h.target.events, [])              # nothing at all reached the target
        self.assertNotIn("hv.init", h.log)
        self.assertEqual(h.logfiles, [])

    def test_the_log_handle_is_closed_when_the_run_ends(self):
        with tempfile.TemporaryDirectory() as d:
            h = self.full_path_harness()
            with self.assertRaisesRegex(RuntimeError, "reached the system map"):
                h.run(logfile=Path(d) / "run.log")
            self.assertTrue(h.logfiles[0].closed)

    def test_mutation_log_opened_late_is_caught(self):
        mutant = mutated_hv_launch(
            ('            log_handle = logfile.open("x")\n',
             '            pass\n'),
            ('        if log_handle is not None:\n            hv.set_logfile(log_handle)',
             '        if logfile:\n            hv.set_logfile(logfile.open("x"))'))

        class Unopenable:
            def open(self, mode):
                raise OSError(28, "No space left on device")
        h = self.full_path_harness()
        # the late open fails only AFTER the chainload, hv.init() and the flag checks: the
        # original raises before any of them
        with self.assertRaises(Exception):
            h.run(logfile=Unopenable(), module=mutant)
        self.assertIn("hv.init", h.log)

    def test_hv_flags_are_checked_only_after_hv_init_on_the_full_path(self):
        for flags, message in (((0, 0), "single-CPU"), ((1, 1), "refused to start")):
            h = LiveHarness(flags=flags)
            h.hv_init_ok = True
            with self.assertRaisesRegex(ValueError, message):
                h.run()
            self.assertLess(h.log.index("hv.init"), len(h.log))
            self.assertEqual(len(h.read8_calls), 2)               # read only now, after hv.init()
            self.assertNotIn("load_system_map", h.log)
        h = LiveHarness(flags=(1, 0))
        h.hv_init_ok = True
        with self.assertRaisesRegex(RuntimeError, "reached the system map"):
            h.run()
        self.assertEqual(h.log.index("hv.init") + 1, h.log.index("load_system_map"))


class CliTests(unittest.TestCase):
    def reject(self, *argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            hv_launch.main(["--package", "x", "--hv-package", "y"] + list(argv))
        self.assertEqual(cm.exception.code, 2)
        return err.getvalue()

    LIVE = ["--launch", "--device", "auto", "--confirm", hv_launch.CONFIRM]

    def test_invalid_combinations_are_rejected_before_any_package_read(self):
        self.assertIn("mutually exclusive", self.reject(*self.LIVE, "--layout-only", "--chainload-only"))
        self.assertIn("--chainload-only", self.reject(*self.LIVE, "--control", "stock"))
        self.assertIn("--chainload-only", self.reject(*self.LIVE, "--layout-only", "--control", "stock"))
        self.assertIn("need --launch", self.reject("--layout-only"))
        self.assertIn("need --launch", self.reject("--chainload-only"))
        self.assertIn("need --launch", self.reject("--chainload-mode", "python"))
        self.assertIn("invalid choice", self.reject(*self.LIVE, "--control", "other"))
        self.assertIn("invalid choice", self.reject(*self.LIVE, "--chainload-mode", "bogus"))
        # existing gates still apply to the new live modes
        self.assertIn("--confirm", self.reject("--launch", "--device", "auto", "--layout-only"))
        self.assertIn("--confirm", self.reject("--launch", "--chainload-only", "--confirm", hv_launch.CONFIRM))
        self.assertIn("--confirm", self.reject("--launch", "--device", "auto", "--chainload-only",
                                               "--confirm", "BOOT-J716C-RAM-DIAGNOSTIC"))

    def test_valid_live_modes_reach_connect_and_run(self):
        calls = []
        with patch.object(hv_launch, "verify_guest_package",
                          return_value=(GUEST_M, {"Image": b"i", "m1n1.bin": b"m"})), \
             patch.object(hv_launch, "verify_hv_package",
                          return_value=(HV_M, {"m1n1-hv.bin": b"h"})), \
             patch.object(hv_launch, "system_map_name", return_value=("System.map-boot034", None)), \
             patch.object(hv_launch, "check_control"), \
             patch.object(hv_launch, "connect_and_run",
                          side_effect=lambda *a, **kw: calls.append((a, kw)) or 0):
            for extra, want in (
                    (["--layout-only"], dict(layout_only=True, chainload_only=False, control=None, mode="intree")),
                    (["--chainload-only"], dict(layout_only=False, chainload_only=True, control=None, mode="intree")),
                    (["--chainload-only", "--control", "stock"],
                     dict(layout_only=False, chainload_only=True, control="stock", mode="intree")),
                    (["--chainload-only", "--chainload-mode", "python"],
                     dict(layout_only=False, chainload_only=True, control=None, mode="python")),
                    ([], dict(layout_only=False, chainload_only=False, control=None, mode="intree"))):
                calls.clear()
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    rc = hv_launch.main(["--package", "x", "--hv-package", "y"] + self.LIVE + extra)
                self.assertEqual(rc, 0)
                (args, kw), = calls
                for key, value in want.items():
                    self.assertEqual(kw[key], value, (extra, key))
                self.assertEqual(args[-1], Path("y") / "System.map-boot034")  # chosen map is passed
                self.assertIn("Mode:", out.getvalue())
                # the control banner tells the operator to power-cycle between runs
                self.assertEqual("POWER-CYCLE between chainload runs" in out.getvalue(),
                                 want["control"] == "stock", extra)
                if want["control"]:
                    self.assertIn("only ONE chainload can happen per boot of the original "
                                  "instance", out.getvalue())

    def test_help_and_error_texts_are_generic(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            hv_launch.main(["--help"])
        text = " ".join(out.getvalue().split())
        self.assertIn("power-cycle between control runs", text)
        self.assertNotIn("hv002", text)
        # --log is for the full run only and is never overwritten
        self.assertIn("Applies to the FULL run only", text)
        self.assertIn("an existing file is refused, choose a new name", text)
        # the layout-only help says what it really does
        self.assertIn("no memory writes; ProxyUtils issues two m1n1 heap-bookkeeping requests", text)
        # no string literal outside docstrings (error texts, help, banners) names hv002
        for name in ("hv_launch.py", "hv_chainload.py"):
            tree = ast.parse((HERE / name).read_text())
            docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and \
                        isinstance(node.body[0], ast.Expr) and \
                        isinstance(node.body[0].value, ast.Constant):
                    docs.add(id(node.body[0].value))
            literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                        and isinstance(n.value, str) and id(n) not in docs]
            if name == "hv_launch.py":
                self.assertTrue(any("hv m1n1" in t for t in literals))
            for text in literals:
                self.assertNotIn("hv002", text, name)

    def test_offline_stays_pure_verification(self):
        with patch.object(hv_launch, "verify_guest_package",
                          return_value=(GUEST_M, {"Image": b"i", "m1n1.bin": b"m"})), \
             patch.object(hv_launch, "verify_hv_package", return_value=(HV_M, {})), \
             patch.object(hv_launch, "system_map_name", return_value=("System.map", None)), \
             patch.object(hv_launch, "connect_and_run", side_effect=AssertionError("USB opened")):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(hv_launch.main(["--package", "x", "--hv-package", "y"]), 0)
        self.assertIn("OFFLINE ONLY", out.getvalue())

    @staticmethod
    def boot_manifest_for(data):
        boot = json.loads(json.dumps(BOOT_MANIFEST))
        boot["files"]["m1n1.bin"]["sha256"] = hashlib.sha256(data).hexdigest()
        return boot

    def test_control_requires_the_installed_object(self):
        data = b"the installed boot021 object"
        boot = self.boot_manifest_for(data)
        hv_launch.check_control(GUEST_M, boot, data)           # marker, offset and digest agree
        for key, value in (("m1n1_version_marker", "x"), ("m1n1_version_offset", 1)):
            with self.assertRaisesRegex(ValueError, "installed boot021"):
                hv_launch.check_control(dict(GUEST_M, **{key: value}), boot, data)
        # right marker and offset, other bytes: the digest is what refuses it
        with self.assertRaisesRegex(ValueError, "digest differs from the installed boot021 object"):
            hv_launch.check_control(GUEST_M, boot, data + b"\0")
        # an installed digest that is not recorded fails closed
        broken = dict(boot, files={k: v for k, v in boot["files"].items() if k != "m1n1.bin"})
        with self.assertRaisesRegex(ValueError, "digest is not recorded"):
            hv_launch.check_control(GUEST_M, broken, data)
        for bad in ("", "zz", "A" * 64, None):                # malformed recorded digests
            odd = dict(boot, files=dict(boot["files"], **{"m1n1.bin": {"size": 1, "sha256": bad}}))
            with self.assertRaises(ValueError):
                hv_launch.check_control(GUEST_M, odd, data)

    def test_the_repository_manifest_records_the_installed_object_digest(self):
        recorded = BOOT_MANIFEST["files"]["m1n1.bin"]["sha256"]
        self.assertRegex(recorded, r"^[0-9a-f]{64}$")
        # the retained boot021 manifest and the current one name the same installed object
        for name in ("boot021-package-manifest.json", "boot033-package-manifest.json"):
            other = json.loads((HERE.parent / "boot" / name).read_text())
            self.assertEqual(other["files"]["m1n1.bin"]["sha256"], recorded, name)

    def control_main(self, files, boot_dir=None):
        with patch.object(hv_launch, "verify_guest_package", return_value=(GUEST_M, files)), \
             patch.object(hv_launch, "verify_hv_package", return_value=(HV_M, {})), \
             patch.object(hv_launch, "system_map_name", return_value=("System.map", None)), \
             patch.object(hv_launch, "connect_and_run",
                          side_effect=lambda *a, **kw: 0) as run:
            argv = ["--package", "x", "--hv-package", "y"] + self.LIVE + [
                "--chainload-only", "--control", "stock"]
            with contextlib.redirect_stdout(io.StringIO()):
                if boot_dir is None:
                    return hv_launch.main(argv), run
                with patch.object(hv_launch, "BOOT", boot_dir):
                    return hv_launch.main(argv), run

    def test_main_refuses_a_control_guest_whose_m1n1_is_not_the_installed_object(self):
        files = {"Image": b"i", "m1n1.bin": b"right marker, wrong object"}
        with self.assertRaisesRegex(ValueError, "installed boot021"):
            self.control_main(files)
        # a guest whose marker and offset are wrong is refused the same way
        with patch.object(hv_launch, "verify_guest_package",
                          return_value=(dict(GUEST_M, m1n1_version_offset=1), files)), \
             patch.object(hv_launch, "verify_hv_package", return_value=(HV_M, {})), \
             patch.object(hv_launch, "system_map_name", return_value=("System.map", None)), \
             patch.object(hv_launch, "connect_and_run", side_effect=AssertionError("USB opened")):
            with contextlib.redirect_stdout(io.StringIO()), \
                    self.assertRaisesRegex(ValueError, "installed boot021"):
                hv_launch.main(["--package", "x", "--hv-package", "y"] + self.LIVE +
                               ["--chainload-only", "--control", "stock"])
        # connect_and_run is never reached for a refused control
        with self.assertRaises(ValueError):
            rc, run = self.control_main(files)

    def test_main_accepts_a_control_guest_that_is_the_installed_object(self):
        data = b"the installed boot021 object"
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "package-manifest.json").write_text(json.dumps(self.boot_manifest_for(data)))
            rc, run = self.control_main({"Image": b"i", "m1n1.bin": data}, boot_dir=Path(d))
        self.assertEqual(rc, 0)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args[1]["control"], "stock")

    def test_the_hv_run_does_not_need_the_control_digest(self):
        # without --control the guest's m1n1.bin is not compared (it is not chainloaded)
        with patch.object(hv_launch, "verify_guest_package",
                          return_value=(GUEST_M, {"Image": b"i", "m1n1.bin": b"anything"})), \
             patch.object(hv_launch, "verify_hv_package", return_value=(HV_M, {})), \
             patch.object(hv_launch, "system_map_name", return_value=("System.map", None)), \
             patch.object(hv_launch, "connect_and_run", return_value=0):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(hv_launch.main(["--package", "x", "--hv-package", "y"] + self.LIVE
                                                + ["--chainload-only"]), 0)

    # --- --log (item 15) ---------------------------------------------------------------------------
    def test_an_existing_log_path_is_refused_at_argument_time(self):
        with tempfile.TemporaryDirectory() as d:
            existing = Path(d) / "events.log"
            existing.write_text("earlier evidence")
            for argv in (self.LIVE, []):                       # live and offline alike
                err = self.reject(*argv, "--log", str(existing))
                self.assertIn("log file exists; choose a new name", err)
            link = Path(d) / "dangling"
            link.symlink_to(Path(d) / "nowhere")               # a dangling symlink exists too
            self.assertIn("log file exists", self.reject("--log", str(link)))
            self.assertEqual(existing.read_text(), "earlier evidence")

    # --- the log's directory (review R2): refused at argument time, not after the handoff ------
    def test_a_log_directory_that_cannot_hold_the_file_is_refused_at_argument_time(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            err = self.reject(*self.LIVE, "--log", str(root / "no-such-dir" / "events.log"))
            self.assertIn("log directory does not exist", err)
            (root / "afile").write_text("not a directory")
            err = self.reject(*self.LIVE, "--log", str(root / "afile" / "events.log"))
            self.assertIn("log path's parent is not a directory", err)
            # the same refusal offline and for every live mode: it is an argument error
            for argv in ([], list(self.LIVE) + ["--layout-only"], list(self.LIVE) + ["--chainload-only"]):
                err = self.reject(*argv, "--log", str(root / "no-such-dir" / "events.log"))
                self.assertIn("log directory does not exist", err)
            # a relative path is judged against the working directory
            cwd = os.getcwd()
            os.chdir(d)
            try:
                err = self.reject(*self.LIVE, "--log", "missing/events.log")
                self.assertIn("log directory does not exist", err)
            finally:
                os.chdir(cwd)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can write anywhere")
    def test_an_unwritable_log_directory_is_refused_at_argument_time(self):
        with tempfile.TemporaryDirectory() as d:
            ro = Path(d) / "readonly"
            ro.mkdir()
            os.chmod(ro, 0o500)                       # r-x: files cannot be created in it
            try:
                self.assertFalse(os.access(ro, os.W_OK))
                err = self.reject(*self.LIVE, "--log", str(ro / "events.log"))
                self.assertIn("log directory is not writable", err)
            finally:
                os.chmod(ro, 0o700)

    def test_a_log_name_longer_than_the_filesystem_allows_is_refused_at_argument_time(self):
        with tempfile.TemporaryDirectory() as d:
            too_long = Path(d) / ("l" * 300 + ".log")
            try:                          # the premise: the late open('x') would fail
                too_long.open("x").close()
            except OSError as exc:
                self.assertEqual(exc.errno, errno.ENAMETOOLONG)
            else:
                too_long.unlink()
                self.skipTest("this filesystem accepts 300-byte names")
            err = self.reject(*self.LIVE, "--log", str(too_long))
            self.assertIn("log file name is too long", err)
            err = self.reject("--log", str(too_long))                 # offline alike
            self.assertIn("log file name is too long", err)
            # the longest name the filesystem takes is still fine
            self.assertIsNone(hv_launch.log_path_problem(Path(d) / ("l" * 255)))
            # a name that is long in bytes, not in characters
            self.assertIn("too long",
                          hv_launch.log_path_problem(Path(d) / ("\u00e9" * 200)))

    def test_log_path_problem_unit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertIsNone(hv_launch.log_path_problem(root / "new.log"))
            (root / "old.log").write_text("x")
            self.assertEqual(hv_launch.log_path_problem(root / "old.log"),
                             "log file exists; choose a new name")
            self.assertEqual(hv_launch.log_path_problem(root),          # a directory exists too
                             "log file exists; choose a new name")
            self.assertIn("does not exist", hv_launch.log_path_problem(root / "x" / "y.log"))
            self.assertIn("not a directory", hv_launch.log_path_problem(root / "old.log" / "y.log"))
            # a plain file name resolves against the working directory
            if os.access(os.getcwd(), os.W_OK | os.X_OK):
                self.assertIsNone(hv_launch.log_path_problem(Path("hv-review-r2-unit-test.log")))

    def test_mutation_without_the_directory_checks_gets_past_the_arguments(self):
        """Without the argument-time directory checks the run would start and only fail at the
        late open('x'), after reload and hv.init(): the mutant gets past argument parsing."""
        def no_directory_checks(path):
            return "log file exists; choose a new name" if os.path.lexists(path) else None

        with tempfile.TemporaryDirectory() as d:
            argv = ["--package", "x", "--hv-package", "y", "--log", str(Path(d) / "no-dir" / "e.log")]
            err = io.StringIO()
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                hv_launch.main(argv)
            self.assertIn("log directory does not exist", err.getvalue())
            with patch.object(hv_launch, "log_path_problem", no_directory_checks):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(Exception) as caught:     # gets past the arguments
                        hv_launch.main(argv)
                self.assertNotIsInstance(caught.exception, SystemExit)

    # --- the layout-only exit codes (review R7) -------------------------------------------------
    def test_layout_fail_exits_3_and_pass_exits_0_through_main_and_cli(self):
        self.assertEqual((hv_launch.EXIT_LAYOUT_PASS, hv_launch.EXIT_LAYOUT_FAIL), (0, 3))
        for rc in (0, 3):
            with patch.object(hv_launch, "verify_guest_package",
                              return_value=(GUEST_M, {"Image": b"i", "m1n1.bin": b"m"})), \
                 patch.object(hv_launch, "verify_hv_package", return_value=(HV_M, {})), \
                 patch.object(hv_launch, "system_map_name", return_value=("System.map", None)), \
                 patch.object(hv_launch, "connect_and_run", return_value=rc):
                with contextlib.redirect_stdout(io.StringIO()):
                    argv = ["--package", "x", "--hv-package", "y"] + self.LIVE + ["--layout-only"]
                    self.assertEqual(hv_launch.main(argv), rc)
                    self.assertEqual(hv_launch.cli(argv), rc)
        # argparse errors stay 2, so 3 can only mean LAYOUT FAIL
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
            hv_launch.cli(["--package", "x", "--hv-package", "y", "--layout-only"])
        self.assertEqual(caught.exception.code, 2)

    def test_help_documents_the_exit_codes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            hv_launch.main(["--help"])
        text = " ".join(out.getvalue().split())
        self.assertIn("exit 0 (PASS) or 3 (FAIL; 2 is an argument error)", text)
        self.assertNotIn("or 2 (FAIL)", text)
        self.assertIn("It exits 0 on LAYOUT PASS and 3 on LAYOUT FAIL (2 is an argument error, "
                      "1 a STOP line, 130 Ctrl-C)", text)

    def test_a_new_log_path_reaches_connect_and_run_and_is_noted_for_partial_modes(self):
        calls = []
        with tempfile.TemporaryDirectory() as d, \
             patch.object(hv_launch, "verify_guest_package",
                          return_value=(GUEST_M, {"Image": b"i", "m1n1.bin": b"m"})), \
             patch.object(hv_launch, "verify_hv_package", return_value=(HV_M, {})), \
             patch.object(hv_launch, "system_map_name", return_value=("System.map", None)), \
             patch.object(hv_launch, "connect_and_run",
                          side_effect=lambda *a, **kw: calls.append(a) or 0):
            log = Path(d) / "new.log"
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = hv_launch.main(["--package", "x", "--hv-package", "y"] + self.LIVE +
                                    ["--log", str(log)])
            self.assertEqual(rc, 0)
            self.assertEqual(calls[-1][5], log)
            self.assertNotIn("--log applies to the full run only", out.getvalue())
            self.assertFalse(log.exists())                     # main() creates nothing itself
            for extra in (["--layout-only"], ["--chainload-only"]):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    hv_launch.main(["--package", "x", "--hv-package", "y"] + self.LIVE + extra +
                                   ["--log", str(log)])
                self.assertIn("Note: --log applies to the full run only; nothing is logged in "
                              "this mode.", out.getvalue())

    def test_layout_only_mode_line_matches_the_behaviour(self):
        with patch.object(hv_launch, "verify_guest_package",
                          return_value=(GUEST_M, {"Image": b"i", "m1n1.bin": b"m"})), \
             patch.object(hv_launch, "verify_hv_package", return_value=(HV_M, {})), \
             patch.object(hv_launch, "system_map_name", return_value=("System.map", None)), \
             patch.object(hv_launch, "connect_and_run", return_value=0):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                hv_launch.main(["--package", "x", "--hv-package", "y"] + self.LIVE + ["--layout-only"])
        self.assertIn("Mode: LIVE LAYOUT CHECK; no memory writes; ProxyUtils issues two m1n1 "
                      "heap-bookkeeping requests (heapblock_alloc(0), heapblock_set_limit)",
                      out.getvalue())
        self.assertNotIn("nothing written", out.getvalue())
        self.assertNotIn("read only", out.getvalue())


# === multi-guest manifests ==============================================================
class ManifestTests(unittest.TestCase):
    def test_system_map_selection(self):
        a, b = b"imageA", b"imageB"
        da, db = hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()
        m2 = {"guests": {da: {"package": "ilinux-j716c-boot033", "system_map": "System.map"},
                         db: {"package": "ilinux-j716c-boot034", "system_map": "System.map-boot034"}}}
        self.assertEqual(hv_launch.system_map_name(m2, a), ("System.map", "ilinux-j716c-boot033"))
        self.assertEqual(hv_launch.system_map_name(m2, b), ("System.map-boot034", "ilinux-j716c-boot034"))
        with self.assertRaisesRegex(ValueError, "not one this hv package"):
            hv_launch.system_map_name(m2, b"imageC")
        m1 = {"guest_image_sha256": da, "guest_package": "ilinux-j716c-boot033"}
        self.assertEqual(hv_launch.system_map_name(m1, a), ("System.map", "ilinux-j716c-boot033"))
        with self.assertRaisesRegex(ValueError, "not one this hv package"):
            hv_launch.system_map_name(m1, b)
        # schema-1 keys remain a fallback next to a guests table
        both = dict(m2, guest_image_sha256=hashlib.sha256(b"old").hexdigest())
        self.assertEqual(hv_launch.system_map_name(both, b"old")[0], "System.map")
        for bad in ({"system_map": "../System.map"}, {"system_map": ""}, {"system_map": 5}, {}):
            with self.assertRaisesRegex(ValueError, "invalid guests entry"):
                hv_launch.system_map_name({"guests": {da: bad}}, a)


if __name__ == "__main__":
    unittest.main()
