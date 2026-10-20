"""Second A/B on the M5's running desktop (written for attempt 26), run as the omarchy user over SSH from the M1:

    ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' < tools/m1n1-client/m5-probes/tap_ab_repeat.py > build/native-intake/tap-ab-repeat.txt

RUNTIME-ONLY, NOT READ-ONLY: run it only with the human's approval for this run, and with no window open on the M5's desktop
(it refuses otherwise) and nobody touching the M5's keyboard. Changes, all in the running session only (nothing saved, a reboot
undoes it): Hyprland's
`input.repeat_delay` is raised to 1000 ms for phase D and put back to its original value at the end; in phase E a terminal is made a small
floating window (600x400) with `hl.dsp.window.float/resize/center`. Terminals are opened and closed and keys sent exactly as in the
first A/B (`tap_ab.py`): a press, 75 ms, then the release, through `hl.dsp.send_key_state`; each terminal writes what it received to a file.
"""
import json
import os
import signal
import subprocess
import sys
import time

TICK = float(os.sysconf("SC_CLK_TCK"))
RT = "/run/user/%d" % os.getuid()
ENV = dict(os.environ, XDG_RUNTIME_DIR=RT, HYPRLAND_INSTANCE_SIGNATURE=sorted(os.listdir(RT + "/hypr"))[0])
LETTERS, EXPECT = 5, 10
rows, typed = [], []


def say(*a):
    try:
        print(*a, flush=True)
    except OSError:
        pass


signal.signal(signal.SIGHUP, lambda s, f: sys.exit(1))
signal.signal(signal.SIGTERM, lambda s, f: sys.exit(1))


def hctl(*args):
    t = time.monotonic()
    r = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=120, env=ENV)
    return (r.stdout + r.stderr).strip().replace("\n", " ")[:200], time.monotonic() - t


HP = subprocess.run(["pgrep", "-x", "Hyprland"], capture_output=True, text=True).stdout.split()[0]


def cum():
    f = [int(x) for x in open("/proc/stat").readline().split()[1:9]]
    s = open("/proc/%s/stat" % HP).read()
    r = s[s.rfind(")") + 2:].split()
    return sum(f) - f[3] - f[4], sum(f), int(r[11]) + int(r[12])


def measure(phase, cyc, label, action, min_wait=0.8, thr=25.0, quiet_s=1.0, timeout=40.0):
    b0, _, h0 = cum()
    t0 = time.monotonic()
    info = action() or {}
    pb, pt, ph = cum()
    pn = time.monotonic()
    last, quiet = (pn, pb, ph), 0.0
    while True:
        time.sleep(0.1)
        b, tt, h = cum()
        n = time.monotonic()
        pct = 100.0 * (b - pb) / (tt - pt) if tt > pt else 0.0
        if pct >= thr:
            last, quiet = (n, b, h), 0.0
        else:
            quiet += n - pn
        pb, pt, pn = b, tt, n
        if (quiet >= quiet_s and n - t0 >= min_wait) or n - t0 >= timeout:
            break
    row = dict(phase=phase, cyc=cyc, label=label, busy_for=last[0] - t0, hypr=(last[2] - h0) / TICK,
               cpu=(last[1] - b0) / TICK, **info)
    rows.append(row)
    say("ROW %-14s c%d %-9s busy %5.1f s | Hyprland %5.2f s | all CPU %5.2f s | %s" % (
        phase, cyc, label, row["busy_for"], row["hypr"], row["cpu"], " ".join("%s=%s" % kv for kv in info.items())))
    return row


def foot_running():
    # the default terminal on the attempt-26 image is foot; use another name here for another terminal
    return subprocess.run(["pgrep", "-x", "foot"], capture_output=True).returncode == 0


def open_terminal(script):
    def act():
        out, dt = hctl("eval", "hl.exec_cmd([==[uwsm-app -- xdg-terminal-exec %s]==])" % script)
        t = time.monotonic()
        while time.monotonic() - t < 25 and not foot_running():
            time.sleep(0.25)
        return {"exec": out[:20], "foot_up_s": round(time.monotonic() - t, 2)}
    return act


def make_small():
    def act():
        lua = ('hl.dispatch(hl.dsp.window.float({ action = "on" }))\n'
               'hl.dispatch(hl.dsp.window.resize({ x = 600, y = 400, relative = false }))\n'
               'hl.dispatch(hl.dsp.window.center())')
        out, _ = hctl("eval", lua)
        time.sleep(0.3)
        geom = subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True, timeout=60, env=ENV).stdout
        try:
            w = json.loads(geom)
            g = "floating=%s size=%s" % (w.get("floating"), w.get("size"))
        except ValueError:
            g = "activewindow unreadable: " + geom[:60]
        say("GEOM %s" % g)
        return {"eval": out[:20]}
    return act


def key_lua(name, state):
    return 'hl.dispatch(hl.dsp.send_key_state({ mods = "", key = "%s", state = "%s" }))' % (name, state)


def tap(name, hold=0.075):
    def act():
        o1, d1 = hctl("eval", key_lua(name, "down"))
        time.sleep(hold)
        o2, d2 = hctl("eval", key_lua(name, "up"))
        return {"up_wait_s": round(d2, 2), "ok": "ok" if o1 == "ok" and o2 == "ok" else (o1 + "|" + o2)[:60]}
    return act


def burst():
    def act():
        waits = []
        for _ in range(LETTERS):
            waits.append(tap("h")()["up_wait_s"])
            time.sleep(0.075)
        return {"up_waits_s": ",".join("%.2f" % w for w in waits)}
    return act


def cycle(phase, cyc, small=False):
    tag = "%s-%d" % (phase, cyc)
    script, path = "/tmp/ab-term-%s.sh" % tag, "/tmp/ab-typed-%s.txt" % tag
    with open(script, "w") as fh:
        fh.write("#!/bin/sh\nIFS= read -r l\nprintf '%%s' \"$l\" > %s\n" % path)
    os.chmod(script, 0o755)
    measure(phase, cyc, "open", open_terminal(script), min_wait=2.5)
    if small:
        measure(phase, cyc, "float", make_small(), min_wait=1.5)
    for i in range(LETTERS):
        r = measure(phase, cyc, "letter%d" % (i + 1), tap("h"), min_wait=0.8)
        if i == 0 and r.get("ok") != "ok":
            raise SystemExit("send_key_state did not answer ok: %r" % (r.get("ok"),))
    measure(phase, cyc, "burst", burst(), min_wait=1.0)
    measure(phase, cyc, "enter", tap("Return"), min_wait=1.0)
    got = ""
    try:
        got = open(path).read()
    except OSError:
        pass
    typed.append((phase, cyc, len(got), got.count("h")))
    say("TYPED %-14s c%d: the terminal received %d characters (%d of them h); expected %d" % (phase, cyc, len(got), got.count("h"), EXPECT))
    if foot_running():
        hctl("eval", "hl.dispatch(hl.dsp.window.close())")
        measure(phase, cyc, "close", lambda: None, min_wait=1.0)
    for f in (script, path):
        try:
            os.remove(f)
        except OSError:
            pass
    time.sleep(1.0)


def idle(label, secs=5.0):
    b0, t0, h0 = cum()
    time.sleep(secs)
    b1, t1, h1 = cum()
    say("IDLE %-14s busy %4.1f%% over %.0f s (Hyprland %.2f s)" % (label, 100.0 * (b1 - b0) / (t1 - t0), secs, (h1 - h0) / TICK))


def get_int(opt):
    try:
        return int(json.loads(hctl("getoption", opt, "-j")[0])["int"])
    except (ValueError, KeyError):
        return None


def set_repeat(ms):
    return hctl("eval", "hl.config({ input = { repeat_delay = %d } })" % ms)[0]


original = get_int("input:repeat_delay")
say("PREFLIGHT Hyprland pid %s; repeat_delay %s ms; rate %s/s; animations: %s" % (
    HP, original, get_int("input:repeat_rate"), hctl("getoption", "animations:enabled", "-j")[0][:70]))
out, _ = hctl("clients", "-j")
if out != "[]":
    raise SystemExit("a window is open already; refusing to send keys (or hyprctl did not answer): %s" % out[:120])
if original is None or set_repeat(original) != "ok":
    raise SystemExit("could not read or set input.repeat_delay through eval")
try:
    idle("start")
    say("SET repeat_delay 1000: %s; now %s" % (set_repeat(1000), get_int("input:repeat_delay")))
    cycle("D-delay-1000", 1)
    cycle("D-delay-1000", 2)
    say("SET repeat_delay %s: %s; now %s" % (original, set_repeat(original), get_int("input:repeat_delay")))
    cycle("E-small-float", 1, small=True)
    cycle("E-small-float", 2, small=True)
finally:
    if foot_running():
        hctl("eval", "hl.dispatch(hl.dsp.window.close())")
    restored = set_repeat(original if original is not None else 250)
    subprocess.run(["sh", "-c", "rm -f /tmp/ab-typed-*.txt /tmp/ab-term-*.sh"])
    say("RESTORE repeat_delay -> %s: %s; now %s" % (original, restored, get_int("input:repeat_delay")))
    idle("end")

say("")
say("=== SUMMARY: mean per step (busy-for = seconds the CPU stayed at or above 25% after the action began)")
for phase in ("D-delay-1000", "E-small-float"):
    for kind, match in (("open terminal", lambda r: r["label"] == "open"), ("float+resize", lambda r: r["label"] == "float"),
                        ("each isolated letter", lambda r: r["label"].startswith("letter")), ("5-letter burst", lambda r: r["label"] == "burst"),
                        ("Enter", lambda r: r["label"] == "enter")):
        sel = [r for r in rows if r["phase"] == phase and match(r)]
        if sel:
            n = float(len(sel))
            waits = [r["up_wait_s"] for r in sel if "up_wait_s" in r]
            say("%-14s %-21s busy-for %5.1f s | Hyprland %5.2f s | all CPU %5.2f s%s | (%d samples)" % (
                phase, kind, sum(r["busy_for"] for r in sel) / n, sum(r["hypr"] for r in sel) / n, sum(r["cpu"] for r in sel) / n,
                (" | release wait %.2f s" % (sum(waits) / len(waits))) if waits else "", len(sel)))
say("typed counts (characters received, h count, expected %d): %s" % (EXPECT, "; ".join("%s c%d: %d/%d" % (p, c, n, h) for p, c, n, h in typed)))
