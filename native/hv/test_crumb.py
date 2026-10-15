"""Offline regressions for the hv003 m1n1 early-boot breadcrumbs (private iLinux).

0002-ilinux-hv-t6050-hv003-crumbs.patch adds a framebuffer breadcrumb painter
between ILINUX-CRUMB-BEGIN/END in src/startup.c and 16 calls (c0..c15) in
_start_c()/m1n1_main(). These tests need no hardware and no m1n1 build:

* the exact block is taken from the post-patch side of the patch, compiled with
  ASan/UBSan around test_crumb_model.c (exact-size fake framebuffers, fake MMU,
  recording mmu_add_mapping/dsb) and run;
* deliberate mutations of that block (wrong pitch, a missing guard, mapping on
  every call, ...) must each make the model fail;
* the patch is checked as text: additions only, each call right after the
  intended init call, c0 before the .bss clear;
* when the pinned m1n1 tree is present, patches 0001 and 0002 are applied to a
  copy and main.c/startup.c are syntax-checked as aarch64 in four build
  variants (default, BRINGUP, no USE_FB, RELEASE).

Run with python3 -I native/hv/test_crumb.py or python3 -m unittest from native/hv.
"""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCH = HERE / "0002-ilinux-hv-t6050-hv003-crumbs.patch"
PATCH_HV002 = HERE / "0001-ilinux-hv-t6050-hv002.patch"
PIN = "57a9339ffd1876e78297b17d34dece8cff8fa1ba"
BEGIN = "/* ILINUX-CRUMB-BEGIN */"
END = "/* ILINUX-CRUMB-END */"


def post_patch_hunks(patch_text, filename):
    """Post-patch side (context and added lines) of every hunk of one file."""
    in_file, hunks = False, []
    for line in patch_text.splitlines():
        if line.startswith("diff --git"):
            in_file = line.endswith("/" + filename)
        elif not in_file:
            continue
        elif line.startswith("@@"):
            hunks.append([])
        elif hunks and line[:1] in (" ", "+"):
            hunks[-1].append(line[1:])
    return hunks


def extract_block(patch_text):
    """The exact painter block added to src/startup.c, markers included."""
    for hunk in post_patch_hunks(patch_text, "src/startup.c"):
        text = "\n".join(hunk) + "\n"
        if BEGIN in text:
            start = text.index(BEGIN)
            end = text.index(END, start) + len(END)
            return text[start:end] + "\n"
    raise AssertionError("crumb block not found in patch")


def cc_available():
    return shutil.which("cc") is not None


def build_and_run(block, werror=True):
    """Compile the harness around `block`; returns (compiled, run_result_or_None, output)."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "crumb_block.inc").write_text(block)
        shutil.copy(HERE / "test_crumb_model.c", d / "model.c")
        flags = ["-std=c11", "-g", "-O1", "-Wall", "-Wextra"]
        if werror:
            flags.append("-Werror")
        cc = subprocess.run(["cc", *flags, "-fsanitize=address,undefined",
                             "-fno-sanitize-recover=all", "-I", str(d), "model.c", "-o", "model"],
                            cwd=d, capture_output=True, text=True)
        if cc.returncode:
            return False, None, cc.stderr
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
        run = subprocess.run([str(d / "model")], capture_output=True, text=True, env=env, timeout=300)
        return True, run, run.stdout + run.stderr


MUTATIONS = {
    # geometry constants of the shared contract
    "wrong pitch": [("#define ILINUX_CRUMB_PITCH      28U", "#define ILINUX_CRUMB_PITCH      27U")],
    "block constant 25": [("#define ILINUX_CRUMB_BLOCK      24U", "#define ILINUX_CRUMB_BLOCK      25U")],
    "block constant 23": [("#define ILINUX_CRUMB_BLOCK      24U", "#define ILINUX_CRUMB_BLOCK      23U")],
    "wrong origin x": [("#define ILINUX_CRUMB_ORIGIN_X   8U", "#define ILINUX_CRUMB_ORIGIN_X   9U")],
    "origin y too low": [("#define ILINUX_CRUMB_ORIGIN_Y   4U", "#define ILINUX_CRUMB_ORIGIN_Y   3U")],
    "origin y too high": [("#define ILINUX_CRUMB_ORIGIN_Y   4U", "#define ILINUX_CRUMB_ORIGIN_Y   5U")],
    # The painter's own loops, with the guards left alone: a real store past the end of the
    # exact-size framebuffer, which only ASan can see.
    "one row too many (ASan overrun)": [("row < ILINUX_CRUMB_BLOCK; row++", "row <= ILINUX_CRUMB_BLOCK; row++")],
    "one column too many": [("col < ILINUX_CRUMB_BLOCK; col++", "col <= ILINUX_CRUMB_BLOCK; col++")],
    "row start moved down (ASan overrun)": [
        ("(ILINUX_CRUMB_ORIGIN_Y + row) * stride", "(ILINUX_CRUMB_ORIGIN_Y + 1 + row) * stride")],
    "wrong colour": [("#define ILINUX_CRUMB_COLOR      0xffffffffU",
                      "#define ILINUX_CRUMB_COLOR      0xfffffeffU")],
    "one slot too many": [("#define ILINUX_CRUMB_SLOTS      21U", "#define ILINUX_CRUMB_SLOTS      22U")],
    "c0 in slot 4": [("#define ILINUX_CRUMB_FIRST_STEP 5U", "#define ILINUX_CRUMB_FIRST_STEP 4U")],
    "step off by one": [("ilinux_crumb(&cur_boot_args.video, ILINUX_CRUMB_FIRST_STEP + step);",
                         "ilinux_crumb(&cur_boot_args.video, ILINUX_CRUMB_FIRST_STEP + step + 1);")],
    "step range unchecked": [("    if (step < ILINUX_CRUMB_STEPS)\n        ilinux_crumb(&cur_boot_args.video",
                              "    if (1)\n        ilinux_crumb(&cur_boot_args.video")],
    # guards
    "no slot guard": [("    if (slot >= ILINUX_CRUMB_SLOTS)\n        return false;\n", "")],
    "no base guard": [("    if (video->base == 0 || (video->base & 3))\n        return false;\n", "")],
    "zero base allowed": [("if (video->base == 0 || (video->base & 3))", "if (video->base & 3)")],
    "misaligned base allowed": [("if (video->base == 0 || (video->base & 3))", "if (video->base == 0)")],
    "no depth guard": [("    if (depth != 30 && depth != 32)\n        return false;\n", "")],
    "depth 30 refused": [("depth != 30 && depth != 32", "depth != 32")],
    "depth not masked": [("const u64 depth = video->depth & 0xff;", "const u64 depth = video->depth;")],
    "no width guard": [("    if (video->width < span)\n        return false;\n", "")],
    "width guard off by one": [("video->width < span)", "video->width < span - 1)")],
    "no height guard": [("    if (video->height < ILINUX_CRUMB_ORIGIN_Y + ILINUX_CRUMB_BLOCK)\n"
                         "        return false;\n", "")],
    "no stride guard": [("    if (video->stride < span * 4)\n        return false;\n", "")],
    "no stride alignment guard": [("    if (video->stride & 3)\n        return false;\n", "")],
    "no size bound": [("    if (video->stride > ILINUX_CRUMB_MAX_STRIDE || video->height > ILINUX_CRUMB_MAX_HEIGHT)\n"
                       "        return false;\n", "")],
    "stride bound too large": [("#define ILINUX_CRUMB_MAX_STRIDE ((u64)0x10000)",
                                "#define ILINUX_CRUMB_MAX_STRIDE ((u64)0x10000000)")],
    "height bound too large": [("#define ILINUX_CRUMB_MAX_HEIGHT ((u64)0x4000)",
                                "#define ILINUX_CRUMB_MAX_HEIGHT ((u64)0x40000000)")],
    "no wrap guard": [("    if (video->stride * video->height > ~(u64)0 - video->base)\n"
                       "        return false;\n", "")],
    # mapping and MMU state
    "maps on every call": [("            ilinux_crumb_state = ILINUX_CRUMB_ST_MAPPED;\n", "")],
    "maps with the MMU off": [("    if (mmu_on) {\n", "    if (1) {\n")],
    "maps in any unmapped state": [("if (ilinux_crumb_state == ILINUX_CRUMB_ST_ARMED) {",
                                    "if (ilinux_crumb_state != ILINUX_CRUMB_ST_MAPPED) {")],
    "never armed": [("    if (!mmu_on)\n        ilinux_crumb_state = ILINUX_CRUMB_ST_ARMED;\n", "")],
    "armed only for a valid geometry": [
        ("    if (!mmu_on)\n        ilinux_crumb_state = ILINUX_CRUMB_ST_ARMED;\n\n"
         "    if (!ilinux_crumb_geometry_ok(video, slot))\n        return;\n",
         "    if (!ilinux_crumb_geometry_ok(video, slot))\n        return;\n\n"
         "    if (!mmu_on)\n        ilinux_crumb_state = ILINUX_CRUMB_ST_ARMED;\n")],
    "paints through foreign tables": [
        ("        if (ilinux_crumb_state != ILINUX_CRUMB_ST_MAPPED)\n            return;\n", "")],
    "no 16K alignment guard": [("            if (video->base & 0x3fff)\n                return;\n", "")],
    "unaligned map size": [("ALIGN_UP(video->stride * video->height, 0x4000)",
                            "video->stride * video->height")],
    "wrong map target": [("mmu_add_mapping(video->base, video->base,", "mmu_add_mapping(video->base, 0,")],
    "wrong memory attribute": [("MAIR_IDX_NORMAL_NC", "0")],
    "wrong permissions": [("                            PERM_RW);", "                            0);")],
    "state in .bss": [("static u32 ilinux_crumb_state = ILINUX_CRUMB_ST_UNSEEN;",
                       "static u32 ilinux_crumb_state;")],
    # synchronisation
    "no dsb": [('    sysop("dsb sy");\n', "")],
    "dsb before the stores": [('    ilinux_crumb_fill(video->base, video->stride, slot);\n    sysop("dsb sy");\n',
                               '    sysop("dsb sy");\n    ilinux_crumb_fill(video->base, video->stride, slot);\n')],
    # console shadow copy (c15)
    "shadow uses the width": [("ilinux_crumb_fill((u64)shadow, video->stride, slot);",
                               "ilinux_crumb_fill((u64)shadow, video->width * 4, slot);")],
    "shadow unguarded": [("if (!shadow || !ilinux_crumb_geometry_ok(video, slot))", "if (!shadow)")],
    "shadow null unchecked": [("if (!shadow || !ilinux_crumb_geometry_ok(video, slot))",
                               "if (!ilinux_crumb_geometry_ok(video, slot))")],
    "shadow step off by one": [("ilinux_crumb_shadow(&cur_boot_args.video, shadow, ILINUX_CRUMB_FIRST_STEP + step);",
                                "ilinux_crumb_shadow(&cur_boot_args.video, shadow, "
                                "ILINUX_CRUMB_FIRST_STEP + step + 1);")],
}


def mutate(block, edits):
    out = block
    for old, new in edits:
        assert out.count(old) == 1, "mutation text must occur exactly once: %r" % old
        out = out.replace(old, new)
    assert out != block
    return out


@unittest.skipUnless(cc_available(), "no C compiler")
class CrumbModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch_text = PATCH.read_text()
        cls.block = extract_block(cls.patch_text)

    def test_block_shape(self):
        b = self.block
        self.assertTrue(b.startswith(BEGIN) and b.rstrip().endswith(END))
        self.assertEqual(self.patch_text.count(BEGIN), 1)
        self.assertEqual(self.patch_text.count(END), 1)
        # Non-static entry points used from main.c (declared extern there).
        for sig in ("void ilinux_crumb(const struct boot_video *video, unsigned int slot)",
                    "void ilinux_crumb_shadow(const struct boot_video *video, u32 *shadow, unsigned int slot)",
                    "void ilinux_crumb_step(unsigned int step)",
                    "void ilinux_crumb_shadow_step(unsigned int step, u32 *shadow)"):
            self.assertIn(sig, b)
        # No printf, no allocation, no other side effects in the painter.
        for forbidden in ("printf", "malloc", "memalign", "uart_", "msr(", "isb"):
            self.assertNotIn(forbidden, b)
        # Mapping uses the same call as fb_init().
        self.assertIn("MAIR_IDX_NORMAL_NC", b)
        self.assertIn("ALIGN_UP(video->stride * video->height, 0x4000)", b)
        self.assertIn("mmu_active()", b)

    def test_exact_block_passes(self):
        compiled, run, out = build_and_run(self.block)
        self.assertTrue(compiled, out)
        self.assertEqual(run.returncode, 0, out)
        self.assertIn("crumb model PASS", out)

    def test_mutations_are_caught(self):
        jobs = {name: mutate(self.block, edits) for name, edits in MUTATIONS.items()}

        def one(item):
            name, text = item
            return name, build_and_run(text, werror=False)

        with ThreadPoolExecutor(max_workers=max(2, min(8, (os.cpu_count() or 2)))) as pool:
            results = list(pool.map(one, jobs.items()))
        for name, (compiled, run, out) in results:
            with self.subTest(name):
                self.assertTrue(compiled, "mutation %r does not compile:\n%s" % (name, out))
                self.assertNotEqual(run.returncode, 0, "mutation survived: " + name)


class PatchTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PATCH.read_text()
        cls.startup = [l for h in post_patch_hunks(cls.text, "src/startup.c") for l in h]
        cls.main = [l for h in post_patch_hunks(cls.text, "src/main.c") for l in h]

    def next_code(self, lines, index):
        for line in lines[index + 1:]:
            if line.strip():
                return line.strip()
        return None

    def assert_follows(self, lines, anchor, crumb, after=0):
        """`crumb` is the very next code line after the first `anchor` at or past `after`."""
        for i in range(after, len(lines)):
            if lines[i].strip() == anchor:
                self.assertEqual(self.next_code(lines, i), crumb, "after %r" % anchor)
                return i
        self.fail("anchor not in the patch hunks: %r" % anchor)

    def test_only_two_files_and_additions_only(self):
        files = re.findall(r"^diff --git a/(\S+) b/\S+$", self.text, re.M)
        self.assertEqual(files, ["src/main.c", "src/startup.c"])
        removed = [l for l in self.text.splitlines() if l.startswith("-") and not l.startswith("---")]
        self.assertEqual(removed, [], "no existing line may be changed or removed")

    def test_c0_precedes_the_bss_clear_and_uses_the_raw_pointer(self):
        c0 = "ilinux_crumb(&((struct boot_args *)boot_args)->video, ILINUX_CRUMB_FIRST_STEP);"
        lines = [l.strip() for l in self.startup]
        self.assertEqual(lines.count(c0), 1)
        memset = next(i for i, l in enumerate(lines) if l.startswith("memset64(_bss_start"))
        self.assertLess(lines.index(c0), memset)
        # Nothing but the u32 declaration and the comment may come before it in _start_c().
        start = next(i for i, l in enumerate(lines) if l.startswith("void _start_c("))
        between = [l for l in lines[start + 1:lines.index(c0)] if l and not l.startswith("/*")]
        self.assertEqual(between, ["{", "UNUSED(base);", "u32 cpu_id = 0;"])

    def test_startup_calls_follow_their_init_calls(self):
        s = self.startup
        # c1 follows the whole first ADT walk (the /cpus lookup, closed by the #endif), not just
        # the pointer, so an ADT problem and a UART/DockChannel problem land in different windows.
        # No crumb call may sit between the bss clear/boot_args copy and that walk.
        self.assertEqual(self.text.count("ilinux_crumb_step(1);"), 1)
        i = self.assert_follows(s, "#endif", "ilinux_crumb_step(1);", 0)
        i = self.assert_follows(s, "ilinux_crumb_step(1);", "if (in_el2())", i)
        i = self.assert_follows(s, "dockchannel_uart_init();", "ilinux_crumb_step(2);", i)
        i = self.assert_follows(s, "init_cpu();", "ilinux_crumb_step(3);", i)
        i = self.assert_follows(s, "dump_boot_args(&cur_boot_args);", "ilinux_crumb_step(4);", i)
        i = self.assert_follows(s, "exception_initialize();", "ilinux_crumb_step(5);", i)
        self.assert_follows(s, "ilinux_crumb_step(5);", "m1n1_main();", i)

    def test_main_calls_follow_their_init_calls(self):
        m = self.main
        i = 0
        for anchor, step in (("firmware_init();", 6), ("heapblock_init();", 7), ("mcc_init();", 8),
                             ("mmu_init();", 9), ("aic_init();", 10), ("smp_init();", 11),
                             ("wdt_disable();", 12), ("pmgr_init();", 13)):
            i = self.assert_follows(m, anchor, "ilinux_crumb_step(%d);" % step, i)
        i = self.assert_follows(m, "display_shutdown(DCP_SLEEP_IF_EXTERNAL);", "ilinux_crumb_step(14);", i)
        i = self.assert_follows(m, "fb_display_logo();", "ilinux_crumb_step(15);", i)
        # c15 is also stored in the console's shadow copy, or fb_update() erases it.
        self.assert_follows(m, "ilinux_crumb_step(15);", "ilinux_crumb_shadow_step(15, fb.ptr);", i)

    def test_every_step_is_called_exactly_once(self):
        calls = re.findall(r"^\+\s+ilinux_crumb_step\((\d+)\);$", self.text, re.M)
        self.assertEqual(sorted(map(int, calls)), list(range(1, 16)))
        self.assertEqual(len(re.findall(r"^\+\s+ilinux_crumb\(&\(\(struct boot_args", self.text, re.M)), 1)
        self.assertEqual(len(re.findall(r"^\+\s+ilinux_crumb_shadow_step\(", self.text, re.M)), 1)

    def test_calls_sit_inside_the_existing_build_conditionals(self):
        """c8..c11 and c13 need not-BRINGUP; c14/c15 also USE_FB (as the calls they follow)."""
        m = self.main
        stack, where = [], {}
        # The hunks only show a window of main.c, so rebuild the nesting from the lines kept
        # around the calls: the directives between the calls are all in the post image.
        for line in m:
            s = line.strip()
            if s.startswith("#if"):
                stack.append(s)
            elif s.startswith("#endif") and stack:
                stack.pop()
            m_call = re.match(r"ilinux_crumb_step\((\d+)\);$", s)
            if m_call:
                where[int(m_call.group(1))] = list(stack)
        self.assertEqual(sorted(where), list(range(6, 16)))
        for step in (14, 15):
            self.assertIn("#ifdef USE_FB", where[step])
        for step in (13, 14, 15):
            self.assertIn("#ifndef BRINGUP", where[step])
        # c12 follows wdt_disable(), which is outside the BRINGUP block in the stock file.
        self.assertNotIn("#ifdef USE_FB", where[12])


def pinned_tree():
    candidates = []
    if os.environ.get("M1N1_TREE"):
        candidates.append(Path(os.environ["M1N1_TREE"]))
    candidates += [ROOT.parent / "apple-silicon-linux-research/third_party/m1n1",
                   ROOT / "third_party/m1n1"]
    for tree in candidates:
        if (tree / ".git").exists():
            head = subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"],
                                  capture_output=True, text=True)
            if head.returncode == 0 and head.stdout.strip() == PIN:
                return tree
    return None


def aarch64_clang():
    clang = shutil.which("clang")
    if not clang:
        return None
    probe = subprocess.run([clang, "--target=aarch64-linux-gnu", "-x", "c", "-fsyntax-only", "-"],
                           input="int x;\n", capture_output=True, text=True)
    return clang if probe.returncode == 0 else None


class ContractTests(unittest.TestCase):
    """The patch's #defines and the host's constants are one shared contract.

    hv_chainload.py (host marks, copy stub, screen-reading tables) and the m1n1
    patch are written separately; a drifted number would put blocks where the
    operator tables say they are not.
    """

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(HERE))
        import hv_chainload
        cls.hc = hv_chainload
        block = extract_block(PATCH.read_text())
        cls.defines = {}
        for name, value in re.findall(r"^#define (ILINUX_CRUMB_[A-Z_0-9]+)\s+(.+?)\s*$", block,
                                      re.MULTILINE):
            cls.defines[name] = value

    def number(self, name):
        text = self.defines[name]
        match = re.fullmatch(r"\(?(?:\(u64\))?(0x[0-9a-fA-F]+|\d+)U?\)?", text)
        self.assertIsNotNone(match, "unparsed value of %s: %r" % (name, text))
        return int(match.group(1), 0)

    def test_geometry_and_slot_numbers_equal_the_host_constants(self):
        hc = self.hc
        expected = {
            "ILINUX_CRUMB_BLOCK": hc.BLOCK,
            "ILINUX_CRUMB_PITCH": hc.PITCH,
            "ILINUX_CRUMB_ORIGIN_X": hc.ORIGIN_X,
            "ILINUX_CRUMB_ORIGIN_Y": hc.ORIGIN_Y,
            "ILINUX_CRUMB_SLOTS": hc.SLOTS,
            "ILINUX_CRUMB_COLOR": hc.COLOR,
            "ILINUX_CRUMB_FIRST_STEP": hc.SLOT_M1N1_FIRST,
            "ILINUX_CRUMB_STEPS": hc.M1N1_STEPS,
        }
        for name, want in expected.items():
            with self.subTest(name):
                self.assertIn(name, self.defines)
                self.assertEqual(self.number(name), want)

    def test_strip_width_and_the_guards_match_the_host_predicate(self):
        hc = self.hc
        span = self.number("ILINUX_CRUMB_ORIGIN_X") + self.number("ILINUX_CRUMB_SLOTS") * \
            self.number("ILINUX_CRUMB_PITCH")
        self.assertEqual(span, hc.STRIP_WIDTH)
        # The painter refuses a stride below span*4 and a width below span; the host's
        # video_ok() uses the same two numbers, and the stub additionally needs stride % 4 == 0.
        block = extract_block(PATCH.read_text())
        for guard in ("video->width < span", "video->stride < span * 4", "video->stride & 3",
                      "video->height < ILINUX_CRUMB_ORIGIN_Y + ILINUX_CRUMB_BLOCK",
                      "depth != 30 && depth != 32"):
            with self.subTest(guard):
                self.assertIn(guard, block)
        video = lambda **kw: type("V", (), dict(base=0x1000, stride=hc.STRIP_WIDTH * 4,
                                                 width=hc.STRIP_WIDTH, height=28, depth=32, **kw))()
        self.assertTrue(hc.video_ok(video()))
        self.assertFalse(hc.video_ok(type("V", (), dict(base=0x1000, stride=hc.STRIP_WIDTH * 4 - 4,
                                                         width=hc.STRIP_WIDTH, height=28, depth=32))()))
        self.assertFalse(hc.video_ok(type("V", (), dict(base=0x1000, stride=hc.STRIP_WIDTH * 4,
                                                         width=hc.STRIP_WIDTH - 1, height=28, depth=32))()))


@unittest.skipUnless(pinned_tree() and aarch64_clang() and shutil.which("git") and shutil.which("tar"),
                     "pinned m1n1 tree or an aarch64-capable clang not available")
class BuildVariantTests(unittest.TestCase):
    """Patches 0001 + 0002 apply to the pinned tree and the files still compile."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tree = Path(cls.tmp.name) / "m1n1"
        cls.tree.mkdir()
        tar = subprocess.run("git -C '%s' archive %s | tar -x -C '%s'" % (pinned_tree(), PIN, cls.tree),
                             shell=True, capture_output=True, text=True)
        assert tar.returncode == 0, tar.stderr
        for patch in (PATCH_HV002, PATCH):
            for mode in ("--check", None):
                cmd = ["git", "apply"] + ([mode] if mode else []) + [str(patch)]
                r = subprocess.run(cmd, cwd=cls.tree, capture_output=True, text=True)
                assert r.returncode == 0, "%s %s: %s" % (patch.name, mode, r.stderr)
        (cls.tree / "build").mkdir()
        (cls.tree / "build/build_tag.h").write_text('#define BUILD_TAG "test"\n')
        (cls.tree / "build/build_cfg.h").write_text("")
        cls.clang = aarch64_clang()
        include = subprocess.run([cls.clang, "-print-file-name=include"], capture_output=True,
                                 text=True).stdout.strip()
        cls.flags = ["--target=aarch64-linux-gnu", "-std=gnu11", "-O2", "-Wall", "-Wundef",
                     "-Wsign-compare", "-Wunused-parameter", "-Wno-multichar", "-ffreestanding",
                     "-fpic", "-fno-stack-protector", "-mstrict-align", "-march=armv8.2-a",
                     "-mgeneral-regs-only", "-nostdinc", "-isystem", include, "-isystem", "sysinc",
                     "-Isrc", "-Isrc/hv", "-Werror=implicit-function-declaration", "-fsyntax-only"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def compile(self, defines=(), no_fb=False):
        config = self.tree / "config.h"
        original = config.read_text()
        try:
            if no_fb:
                config.write_text(original.replace("#define USE_FB\n", ""))
                self.assertNotIn("\n#define USE_FB", config.read_text())
            for name in ("src/main.c", "src/startup.c"):
                r = subprocess.run([self.clang, *self.flags, *defines, name], cwd=self.tree,
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, name + "\n" + r.stderr)
                # Stock BRINGUP builds already warn about an unused usb_up; ours add nothing.
                self.assertNotIn("ilinux", r.stderr.lower(), name + "\n" + r.stderr)
        finally:
            config.write_text(original)

    def test_default(self):
        self.compile()

    def test_bringup(self):
        self.compile(["-DBRINGUP"])

    def test_without_framebuffer(self):
        self.compile(no_fb=True)
        self.compile(["-DBRINGUP"], no_fb=True)

    def test_release(self):
        self.compile(["-DRELEASE"])
        self.compile(["-DRELEASE", "-DCHAINLOADING"])


if __name__ == "__main__":
    unittest.main()
