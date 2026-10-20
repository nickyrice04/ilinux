"""A/B on the M5's running desktop (written for attempt 26), run as the omarchy user over SSH from the M1:

    ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' < tools/m1n1-client/m5-probes/tap_ab.py > build/native-intake/tap-ab.txt

RUNTIME-ONLY, NOT READ-ONLY: run it only with the human's approval for this run, and with no window open on the M5's desktop
(it refuses otherwise) and nobody touching the M5's keyboard. What it changes, all in the running session only (nothing is saved,
a reboot undoes it):
it stops the leftover `omarchy-menu-select` processes, switches Hyprland's animations off and back on (`hl.config` through
`hyprctl eval`, the Lua config API of this Hyprland), opens and closes terminals and sends keys to the focused terminal with
`hl.dsp.send_key_state` (a press, 75 ms, then the release, as a real tap would). Each terminal runs a one-line script that reads
a line and writes it to a file in /tmp, so the characters that reached it are counted exactly (a delayed release shows up as
extra letters). It restores animations at the end.
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
LETTERS, EXPECT = 5, 10                      # five isolated taps, then five in a quick burst
rows, typed = [], []
MODS = ['mods = "", ']                      # dropped for the rest of the run if the API refuses an empty mods


def say(*a):
    try:
        print(*a, flush=True)
    except OSError:                              # the link went away: keep going so the restore below still runs
        pass


signal.signal(signal.SIGHUP, lambda s, f: sys.exit(1))
signal.signal(signal.SIGTERM, lambda s, f: sys.exit(1))


def hctl(*args):
    t = time.monotonic()
    r = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=120, env=ENV)
    return (r.stdout + r.stderr).strip().replace("\n", " ")[:160], time.monotonic() - t


HP = subprocess.run(["pgrep", "-x", "Hyprland"], capture_output=True, text=True).stdout.split()[0]


def cum():
    f = [int(x) for x in open("/proc/stat").readline().split()[1:9]]
    s = open("/proc/%s/stat" % HP).read()
    r = s[s.rfind(")") + 2:].split()
    return sum(f) - f[3] - f[4], sum(f), int(r[11]) + int(r[12])      # busy ticks, all ticks, Hyprland ticks


def measure(phase, cyc, label, action, min_wait=0.8, thr=25.0, quiet_s=1.0, timeout=40.0):
    """Run action, then poll every 0.1 s until the CPU stays under thr% for quiet_s. The row says how long the CPU stayed
    busy after the action began, and how much CPU Hyprland and the whole machine used over that stretch."""
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
    say("ROW %-12s c%d %-9s busy %5.1f s | Hyprland %5.2f s | all CPU %5.2f s | %s" % (
        phase, cyc, label, row["busy_for"], row["hypr"], row["cpu"],
        " ".join("%s=%s" % kv for kv in info.items())))
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
        return {"exec": out[:20], "exec_s": round(dt, 2), "foot_up_s": round(time.monotonic() - t, 2)}
    return act


def key_lua(name, state):
    return 'hl.dispatch(hl.dsp.send_key_state({ %skey = "%s", state = "%s" }))' % (MODS[0], name, state)


def tap(name, hold=0.075):
    def act():
        o1, d1 = hctl("eval", key_lua(name, "down"))
        if o1 != "ok" and MODS[0]:                 # perhaps an empty mods is refused: retry without it, for good
            MODS[0] = ""
            o1, d1 = hctl("eval", key_lua(name, "down"))
        time.sleep(hold)
        o2, d2 = hctl("eval", key_lua(name, "up"))
        return {"down_s": round(d1, 2), "up_wait_s": round(d2, 2), "ok": "ok" if o1 == "ok" and o2 == "ok" else (o1 + "|" + o2)[:60]}
    return act


def burst():
    def act():
        waits = []
        for _ in range(LETTERS):
            r = tap("h")()
            waits.append(r["up_wait_s"])
            time.sleep(0.075)
        return {"up_waits_s": ",".join("%.2f" % w for w in waits)}
    return act


def cycle(phase, cyc):
    tag = "%s-%d" % (phase, cyc)
    script, path = "/tmp/ab-term-%s.sh" % tag, "/tmp/ab-typed-%s.txt" % tag
    with open(script, "w") as fh:
        fh.write("#!/bin/sh\nIFS= read -r l\nprintf '%%s' \"$l\" > %s\n" % path)
    os.chmod(script, 0o755)
    measure(phase, cyc, "open", open_terminal(script), min_wait=2.5)
    for i in range(LETTERS):
        r = measure(phase, cyc, "letter%d" % (i + 1), tap("h"), min_wait=0.8)
        if i == 0 and cyc == 0 and r.get("ok") != "ok":
            raise SystemExit("send_key_state did not answer ok: %r" % (r.get("ok"),))
    measure(phase, cyc, "burst", burst(), min_wait=1.0)
    measure(phase, cyc, "enter", tap("Return"), min_wait=1.0)
    got = ""
    try:
        got = open(path).read()
    except OSError:
        pass
    typed.append((phase, cyc, len(got), got.count("h")))
    say("TYPED %-12s c%d: the terminal received %d characters (%d of them h); expected %d" % (phase, cyc, len(got), got.count("h"), EXPECT))
    if foot_running():
        hctl("eval", "hl.dispatch(hl.dsp.window.close())")
        measure(phase, cyc, "close", lambda: None, min_wait=1.0)
    for f in (script, path):
        try:
            os.remove(f)
        except OSError:
            pass
    time.sleep(1.0)


def idle(label, secs=6.0):
    b0, t0, h0 = cum()
    time.sleep(secs)
    b1, t1, h1 = cum()
    say("IDLE %-14s busy %4.1f%% over %.0f s (Hyprland %.2f s)" % (label, 100.0 * (b1 - b0) / (t1 - t0), secs, (h1 - h0) / TICK))


def anim_on():
    try:
        return bool(json.loads(hctl("getoption", "animations:enabled", "-j")[0])["bool"])
    except (ValueError, KeyError):
        return None


def set_anim(on):
    return hctl("eval", "hl.config({ animations = { enabled = %s } })" % ("true" if on else "false"))[0]


original = anim_on()
say("PREFLIGHT Hyprland pid %s; animations on: %s" % (HP, original))
out, _ = hctl("clients", "-j")
if out != "[]":
    raise SystemExit("a window is open already; refusing to send keys (or hyprctl did not answer): %s" % out[:120])
if original is None:
    raise SystemExit("could not read animations:enabled; refusing to change anything")
pre = set_anim(original is not False)               # a no-op that proves the config call works before anything changes
if pre != "ok":
    raise SystemExit("hl.config through eval did not answer ok: %r" % (pre,))
try:
    idle("start (as is)")
    cycle("A-as-is", 0)                       # warm-up: first use of the terminal and fonts
    cycle("A-as-is", 1)
    cycle("A-as-is", 2)
    pk = subprocess.run(["pkill", "-f", "omarchy-menu-select Keybindings"], capture_output=True)
    time.sleep(1.5)
    left = subprocess.run(["pgrep", "-fc", "omarchy-menu-select"], capture_output=True, text=True).stdout.strip()
    say("STOPPED the leftover omarchy-menu-select processes (pkill exit %d); still running: %s" % (pk.returncode, left))
    idle("pollers gone")
    cycle("B-no-pollers", 1)
    cycle("B-no-pollers", 2)
    say("SET animations off: %s; now on: %s" % (set_anim(False), anim_on()))
    idle("animations off")
    cycle("C-no-anim", 1)
    cycle("C-no-anim", 2)
finally:
    if foot_running():
        hctl("eval", "hl.dispatch(hl.dsp.window.close())")
    restored = set_anim(original is not False)
    if anim_on() != original:
        restored += " | reload: " + hctl("reload")[0]
    subprocess.run(["sh", "-c", "rm -f /tmp/ab-typed-*.txt /tmp/ab-term-*.sh"])
    say("RESTORE animations -> %s: %s; now %s" % (original, restored, anim_on()))
    idle("end")

say("")
say("=== SUMMARY: mean per step, by phase (busy-for = seconds the CPU stayed at or above 25% after the action began)")
for phase in ("A-as-is", "B-no-pollers", "C-no-anim"):
    for kind, match in (("open terminal", lambda r: r["label"] == "open"), ("each isolated letter", lambda r: r["label"].startswith("letter")),
                        ("5-letter burst", lambda r: r["label"] == "burst"), ("Enter", lambda r: r["label"] == "enter")):
        sel = [r for r in rows if r["phase"] == phase and r["cyc"] >= 1 and match(r)]
        if sel:
            n = float(len(sel))
            say("%-13s %-21s busy-for %5.1f s | Hyprland %5.2f s | all CPU %5.2f s | (%d samples)" % (
                phase, kind, sum(r["busy_for"] for r in sel) / n, sum(r["hypr"] for r in sel) / n, sum(r["cpu"] for r in sel) / n, len(sel)))
say("typed counts (characters received, h count, expected %d): %s" % (EXPECT, "; ".join("%s c%d: %d/%d" % (p, c, n, h) for p, c, n, h in typed)))
