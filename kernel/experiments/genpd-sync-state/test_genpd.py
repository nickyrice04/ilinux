"""Offline regressions for the boot034 genpd experiment (private iLinux).

Runs without a Linux build: the ladder is compiled from the exact block in
apply.py against stubbed kernel types (ASan/UBSan). If a Linux tree with
drivers/pmdomain/core.c is available (LINUX_TREE, or third_party/asahi-linux
at the repository's workspace), apply.py is also exercised against the real file.
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
APPLY = HERE / "apply.py"


def ladder_block():
    text = APPLY.read_text()
    m = re.search(r"/\* ILINUX-LADDER-BEGIN \*/.*?/\* ILINUX-LADDER-END \*/", text, re.S)
    assert m, "ladder block markers missing"
    return m.group(0)


def core_source():
    candidates = []
    if os.environ.get("LINUX_TREE"):
        candidates.append(Path(os.environ["LINUX_TREE"]))
    candidates += [HERE.parents[2] / "third_party/asahi-linux",
                   HERE.parents[3] / "apple-silicon-linux-research/third_party/asahi-linux"]
    for tree in candidates:
        direct = tree / "drivers/pmdomain/core.c"
        if direct.is_file():
            return direct.read_bytes()
        if (tree / ".git").exists():
            r = subprocess.run(["git", "-C", str(tree), "show", "HEAD:drivers/pmdomain/core.c"],
                               capture_output=True)
            if r.returncode == 0:
                return r.stdout
    return None


def build_and_run(block, extra_cflags=()):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "ladder_block.inc").write_text(block + "\n")
        shutil.copy(HERE / "test_ladder.c", d / "model.c")
        cc = subprocess.run(["cc", "-std=gnu11", "-g", "-O1", "-Wall", "-Wextra", "-Werror",
                             "-Wno-unused-function", "-Wno-unused-parameter",
                             "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                             "-I", str(d), *extra_cflags, "model.c", "-o", "model"],
                            cwd=d, capture_output=True, text=True)
        if cc.returncode:
            return None, cc.stderr
        run = subprocess.run([str(d / "model")], capture_output=True, text=True)
        return run, run.stdout + run.stderr


@unittest.skipUnless(shutil.which("cc"), "no C compiler")
class LadderModel(unittest.TestCase):
    def test_exact_block_passes(self):
        run, out = build_and_run(ladder_block())
        self.assertIsNotNone(run, out)
        self.assertEqual(run.returncode, 0, out)
        self.assertIn("ladder model PASS", out)

    def test_mutations_are_caught(self):
        base = ladder_block()
        mutations = {
            "ignores always-on": ("&&\n\t\t    !genpd_is_always_on(genpd)) {", ") {"),
            "keeps stay_on": ("\tpick->stay_on = false;\n", ""),
            "never reschedules": ("\tschedule_delayed_work(&ilinux_genpd_ladder_work,\n"
                                  "\t\t\t      msecs_to_jiffies(ILINUX_LADDER_STEP_MS));\n", ""),
            "armed without the fix": ("\tif (!pd_ignore_unused)\n\t\treturn 0;\n", ""),
            "ignores power state": ("\t\tif (genpd_status_on(genpd) && genpd->stay_on &&\n", "\t\tif (genpd->stay_on &&\n"),
        }
        for name, (old, new) in mutations.items():
            with self.subTest(name):
                self.assertEqual(base.count(old), 1, name)
                run, out = build_and_run(base.replace(old, new))
                failed = run is None or run.returncode != 0
                self.assertTrue(failed, "mutation survived: " + name)


class ApplyAgainstTree(unittest.TestCase):
    def setUp(self):
        self.core = core_source()
        if self.core is None:
            self.skipTest("no Linux tree with drivers/pmdomain/core.c")

    def apply(self, data):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / "drivers/pmdomain"
        path.mkdir(parents=True)
        (path / "core.c").write_bytes(data)
        run = subprocess.run([sys.executable, "-I", str(APPLY), d.name], capture_output=True, text=True)
        return run, (path / "core.c").read_text()

    def test_digest_matches_reviewed_file(self):
        digest = re.search(r"CORE_SHA256 = '([0-9a-f]{64})'", APPLY.read_text()).group(1)
        self.assertEqual(hashlib.sha256(self.core).hexdigest(), digest)

    def test_applies_once_with_all_changes(self):
        run, text = self.apply(self.core)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(text.count("if (pd_ignore_unused) {\n\t\tpr_info_once("), 2)
        self.assertEqual(text.count('pr_info("ilinux-genpd: power off %s\\n", genpd->name);'), 1)
        self.assertEqual(text.count("ILINUX-LADDER-BEGIN"), 1)
        # pd_ignore_unused is defined before its new uses and before the ladder.
        define = text.index("static bool pd_ignore_unused;")
        self.assertLess(define, text.index("ILINUX-LADDER-BEGIN"))
        self.assertLess(define, text.index("void of_genpd_sync_state("))

    def test_refuses_modified_or_already_patched_file(self):
        run, text = self.apply(self.core + b"\n")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("reviewed digest", run.stderr)
        run2, _ = self.apply(text.encode())
        self.assertNotEqual(run2.returncode, 0)


if __name__ == "__main__":
    unittest.main()
