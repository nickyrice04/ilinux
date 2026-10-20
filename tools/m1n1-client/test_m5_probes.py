#!/usr/bin/env python3
"""Offline tests of the M5 desktop probes (tools/m1n1-client/m5-probes/, written for attempt 26).

The probes run on the M5 over SSH, so what can be checked here is what the sources promise:
  * every script parses, and keytiming.py's own `--selftest` passes (its report on made-up data, the bookkeeping for a kernel
    worker that renames itself, children's CPU time and per-thread totals), and its report copes with no data at all;
  * the three read-only scripts stay read-only: no grab of the input device, no write, no kill or remove, and only the
    `hyprctl` verbs that read (getoption, monitors, clients, layers, activewindow);
  * the two runtime-only A/B scripts keep their contract: they refuse to start with a window open, restore in a `finally`
    block (and on SIGHUP/SIGTERM), touch only their own /tmp/ab-* files, use only the Hyprland Lua calls the report lists, only
    the `hyprctl` verbs eval/getoption/clients/activewindow/reload, and nothing that powers off, installs, downloads or sudoes;
  * the README names every script;
  * each of those properties is checked on mutated copies of the sources too: a copy with the property broken must be flagged.
    python3 -I tools/m1n1-client/test_m5_probes.py
"""
import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIR = HERE / "m5-probes"
READ_ONLY = ("keytiming.py", "inspect_desktop.py", "frame_probe.py")
RUNTIME = ("tap_ab.py", "tap_ab_repeat.py")
ALL = READ_ONLY + RUNTIME

READ_VERBS = {"getoption", "monitors", "clients", "layers", "activewindow"}
RUNTIME_VERBS = READ_VERBS | {"eval", "reload"}
LUA_ALLOWED = {"hl.config", "hl.dispatch", "hl.exec_cmd", "hl.dsp.send_key_state", "hl.dsp.window.float", "hl.dsp.window.resize",
               "hl.dsp.window.center", "hl.dsp.window.close"}
READ_ONLY_BANNED = (
    (r"EVIOCGRAB|\bfcntl\b|\bioctl\b", "grabs or controls a device"),
    (r"os\.write\(|\.write\(", "writes"),
    (r"open\([^)]*,\s*['\"][wax+]", "opens a file for writing"),
    (r"\bpkill\b|\bkill\b|os\.remove|os\.unlink|\brm\b", "kills or removes"),
)
RUNTIME_BANNED = (
    (r"\breboot\b|\bpoweroff\b|\bshutdown\b|\bsystemctl\b|\bpacman\b|\bmkfs\b|\bdd\b|\bsudo\b|\bcurl\b|\bwget\b|\bssh\b",
     "powers off, installs, downloads or escalates"),
    (r"rm -rf|rm -fr", "removes recursively"),
)


def source(name):
    return (DIR / name).read_text()


def hyprctl_verbs(src):
    verbs = set(re.findall(r'\["hyprctl",\s*"(\w+)"', src))
    verbs |= set(re.findall(r'\bhctl\(\s*"(\w+)"', src))
    verbs |= set(re.findall(r'\bh\(\s*"(\w+)"', src))
    return verbs


def violations(name, src):
    """What a probe's source breaks of its promises; an empty list for a good one."""
    out = []
    read_only = name in READ_ONLY
    for verb in sorted(hyprctl_verbs(src) - (READ_VERBS if read_only else RUNTIME_VERBS)):
        out.append("hyprctl verb %r is not allowed" % verb)
    code = re.sub(r'""".*?"""', "", src, count=1, flags=re.S)           # the module docstring talks about all of this
    for pattern, why in (READ_ONLY_BANNED if read_only else RUNTIME_BANNED):
        if re.search(pattern, code):
            out.append("%s: %s" % ("read-only script" if read_only else "runtime script", why))
    if read_only:
        return out
    for token in sorted(set(re.findall(r"hl\.[A-Za-z_][A-Za-z0-9_.]*", code)) - LUA_ALLOWED):
        out.append("Lua call %s is not in the reviewed list" % token)
    for literal in re.findall(r'"(/tmp/[^"%\s]*)', code):
        if not literal.startswith("/tmp/ab-"):
            out.append("touches %s outside /tmp/ab-*" % literal)
    for targets in re.findall(r"rm -f ([^\"']+)", code):
        for t in targets.split():
            if not t.startswith("/tmp/ab-"):
                out.append("removes %s" % t)
    if "finally:" not in code:
        out.append("no finally block")
    else:
        tail = code[code.index("finally:"):]
        if not re.search(r"set_(anim|repeat)\(original", tail):
            out.append("the finally block does not restore the setting")
    guard = code.find("a window is open already; refusing")
    first_try = re.search(r"^try:\n", code, re.M)
    if guard < 0 or not first_try or guard > first_try.start():
        out.append("does not refuse to start with a window open before changing anything")
    if "signal.SIGHUP" not in code or "signal.SIGTERM" not in code:
        out.append("does not handle SIGHUP and SIGTERM")
    return out


def load_keytiming():
    spec = importlib.util.spec_from_file_location("m5_keytiming", DIR / "keytiming.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Files(unittest.TestCase):
    def test_all_scripts_exist_and_parse(self):
        for name in ALL:
            compile(source(name), name, "exec")

    def test_readme_names_every_script(self):
        readme = (DIR / "README.md").read_text()
        for name in ALL:
            self.assertIn(name, readme, name)


class KeyTiming(unittest.TestCase):
    def test_selftest_passes_from_a_file_and_from_stdin(self):
        for argv, stdin in (([sys.executable, "-I", str(DIR / "keytiming.py"), "--selftest"], None),
                            ([sys.executable, "-I", "-", "--selftest"], source("keytiming.py"))):
            r = subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("selftest OK", r.stdout)

    def test_report_without_any_data(self):
        text = load_keytiming().report([], [], [], None)
        self.assertIn("no key events", text)

    def test_renamed_worker_is_not_counted_from_zero(self):
        mod = load_keytiming()
        use = mod.delta_use({"7": ("kworker/u4:0-events_unbound", 79, 0)}, {"7": ("kworker/u4:0-dchid-keyboard", 80, 0)}, 100.0)
        self.assertAlmostEqual(use["kworker/u4:0-dchid-keyboard"], 0.01)

    def test_a_modifier_held_for_the_enter_does_not_end_the_run(self):
        src = source("keytiming.py")
        self.assertIn("not super_down", src)
        self.assertIn("(125, 126)", src)


class Promises(unittest.TestCase):
    def test_the_probes_keep_their_promises(self):
        for name in ALL:
            self.assertEqual(violations(name, source(name)), [], name)

    def test_mutations_are_caught(self):
        mutations = []
        for name in READ_ONLY:
            mutations.append((name, "os.write(1, b'x')\n", "append"))
            mutations.append((name, "EVIOCGRAB = 0x40044590\n", "append"))
            mutations.append((name, "import subprocess\nsubprocess.run(['rm', '-f', 'x'])\n", "append"))
        mutations += [("frame_probe.py", ("getoption", "keyword"), "replace"), ("inspect_desktop.py", ("getoption", "eval"), "replace")]
        for name in RUNTIME:
            mutations += [(name, ("finally:", "except KeyboardInterrupt:"), "replace"),
                          (name, ("a window is open already; refusing", "ok"), "replace"),
                          (name, ("hl.dsp.window.close", "hl.dsp.window.kill"), "replace"),
                          (name, ("set_anim(original", "set_anim(True") if name == "tap_ab.py" else ("set_repeat(original", "set_repeat(250"),
                           "replace"),
                          (name, ("signal.SIGHUP", "signal.SIGUSR1"), "replace"),
                          (name, ("rm -f /tmp/ab-typed-*.txt", "rm -f /home/omarchy/*"), "replace"),
                          (name, "import os\nos.system('sudo reboot')\n", "append"),
                          (name, ('hctl("eval", "hl.dispatch(hl.dsp.window.close())")', 'hctl("dispatch", "killactive")'), "replace")]
        caught = 0
        for name, change, how in mutations:
            src = source(name)
            if how == "append":
                mutated = src + "\n" + change
            else:
                self.assertIn(change[0], src, "%s: %r is not in the source (the mutation would test nothing)" % (name, change[0]))
                mutated = src.replace(change[0], change[1])
            self.assertNotEqual(mutated, src)
            self.assertTrue(violations(name, mutated), "not caught: %s %r" % (name, change))
            caught += 1
        self.assertGreaterEqual(caught, 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
