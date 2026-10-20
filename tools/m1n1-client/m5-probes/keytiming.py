"""Read-only key and CPU timing on the M5 (written for attempt 26), run as root over SSH from the M1:

    ssh -F tools/m1n1-client/m5-ssh-config m5o 'sudo -n python3 -I - /dev/input/event0 600' \
        < tools/m1n1-client/m5-probes/keytiming.py > build/native-intake/keytiming.txt

(this file on stdin; the second argument is the time limit in seconds; see README.md in this directory).

It reads the keyboard's evdev node without grabbing it (the typing still reaches Hyprland) and /proc, and writes nothing.
For every key event: the time, the key (letters, Enter, Space and the modifiers by name, others as k<code>), the value
(1 press, 0 release, 2 kernel autorepeat) and how long after the kernel stamped it this program read it. Ten times a second:
how busy the one CPU is. Four times a second: which processes used it (a process that exits between two samples shows only as
"<parent> (children)"). At the end (Enter pressed without Super held, then 4 s more, or the time limit): the key events, the
key presses in order, one row per key press (how long it was held, kernel repeats, how long the CPU stayed busy right after it,
who used it), the busy stretches of 0.3 s or more, and totals including CPU seconds by thread. `--selftest` runs the report on
made-up data (no device needed). Its own cost on the M5 was about 1% of the CPU. The M5's kernel had no /proc/pressure/cpu, so the
"scheduler wait" column reads 0 there.
"""
import os
import select
import struct
import sys
import time

EV = "llHHi"
ESZ = struct.calcsize(EV)
KEYS = {1: "ESC", 14: "BKSP", 15: "TAB", 28: "ENTER", 29: "CTRL", 42: "SHIFT", 54: "SHIFT", 56: "ALT", 57: "SPACE",
        97: "CTRL", 100: "ALT", 125: "SUPER", 126: "SUPER"}
for row, first in (("qwertyuiop", 16), ("asdfghjkl", 30), ("zxcvbnm", 44)):
    for i, ch in enumerate(row):
        KEYS[first + i] = ch
BUSY = 50.0          # percent: a 0.1 s sample at or above this counts as busy
ENTER = 28
PSI = "/proc/pressure/cpu"


def key_name(code):
    return KEYS.get(code, "k%d" % code)


def read_cpu():
    with open("/proc/stat") as fh:
        return [int(x) for x in fh.readline().split()[1:9]]


def read_procs():
    out = {}
    try:
        names = os.listdir("/proc")
    except OSError:
        return out
    for d in names:
        if not d.isdigit():
            continue
        try:
            with open("/proc/" + d + "/stat") as fh:
                s = fh.read()
        except OSError:
            continue
        a, b = s.find("("), s.rfind(")")
        if a < 0 or b < a:
            continue
        rest = s[b + 2:].split()
        try:
            out[d] = (s[a + 1:b], int(rest[11]) + int(rest[12]), int(rest[13]) + int(rest[14]))   # own ticks, reaped children's ticks
        except (IndexError, ValueError):
            continue
    return out


def read_psi():
    try:
        with open(PSI) as fh:
            for line in fh:
                if line.startswith("some"):
                    return int(line.split("total=")[1].split()[0])
    except (OSError, IndexError, ValueError):
        pass
    return None


def delta_use(prev, cur, tick):
    """CPU seconds used between two snapshots by process name. The baseline is the same pid, whatever its name now (a
    kernel worker renames itself after the last work item), and a pid not seen before counts in full. Time of children
    that exited and were reaped in between is credited to the parent as "<name> (children)"."""
    use = {}
    for pid, (comm, own, kids) in cur.items():
        before = prev.get(pid)
        dj = own - (before[1] if before else 0)
        dc = kids - (before[2] if before else 0)
        if dj > 0:
            use[comm] = use.get(comm, 0.0) + dj / tick
        if dc > 0:
            use[comm + " (children)"] = use.get(comm + " (children)", 0.0) + dc / tick
    return use


def thread_ticks():
    """{(pid, tid): (process name, thread name, ticks)} for every thread; read once at the start and once at the end."""
    out = {}
    try:
        names = os.listdir("/proc")
    except OSError:
        return out
    for d in names:
        if not d.isdigit():
            continue
        try:
            with open("/proc/" + d + "/stat") as fh:
                s = fh.read()
            tids = os.listdir("/proc/" + d + "/task")
        except OSError:
            continue
        pcomm = s[s.find("(") + 1:s.rfind(")")]
        for tid in tids:
            try:
                with open("/proc/%s/task/%s/stat" % (d, tid)) as fh:
                    ts = fh.read()
            except OSError:
                continue
            tr = ts[ts.rfind(")") + 2:].split()
            try:
                out[(d, tid)] = (pcomm, ts[ts.find("(") + 1:ts.rfind(")")], int(tr[11]) + int(tr[12]))
            except (IndexError, ValueError):
                continue
    return out


def thread_delta(start, end, tick):
    use = {}
    for key, (pcomm, tcomm, ticks) in end.items():
        before = start.get(key)
        dj = ticks - (before[2] if before else 0)
        if dj > 0:
            name = "%s/%s" % (pcomm, tcomm) if tcomm != pcomm else pcomm
            use[name] = use.get(name, 0.0) + dj / tick
    return use


def collect(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    tick = float(os.sysconf("SC_CLK_TCK"))
    t0 = time.time()
    events, cpu, procs = [], [], []     # events (t, code, value, lag_ms); cpu (t_end, dt, busy, usr, sys, irq, wait_ms)
    prev_c, prev_t, prev_w = read_cpu(), time.time(), read_psi()      # procs (t_end, dt, {comm: seconds})
    prev_p, prev_pt = read_procs(), prev_t
    mono = time.monotonic()
    deadline, next_c, next_p, end_at = mono + limit, mono + 0.1, mono + 0.25, None
    super_down, th0 = set(), thread_ticks()
    print("ARMED: reading %s for up to %d s; press Enter (without Super) to finish (PSI %s)"
          % (path, limit, "present" if prev_w is not None else "absent"), flush=True)
    while True:
        mono = time.monotonic()
        if mono >= deadline or (end_at is not None and mono >= end_at):
            break
        if select.select([fd], [], [], max(0.0, min(next_c, next_p) - mono))[0]:
            now = time.time()
            data = os.read(fd, ESZ * 64)
            for i in range(0, len(data) - ESZ + 1, ESZ):
                sec, usec, etype, code, value = struct.unpack_from(EV, data, i)
                if etype != 1:
                    continue
                ts = sec + usec / 1e6
                events.append((ts - t0, code, value, (now - ts) * 1000.0))
                if code in (125, 126):
                    (super_down.add if value else super_down.discard)(code)
                if code == ENTER and value == 1 and not super_down and end_at is None:
                    end_at = time.monotonic() + 4.0           # Enter without Super held: keep sampling 4 s, then finish
        mono = time.monotonic()
        if mono >= next_c:
            c, t, w = read_cpu(), time.time(), read_psi()
            d = [x - y for x, y in zip(c, prev_c)]
            tot = float(sum(d))
            if tot > 0:
                busy = 100.0 * (tot - d[3] - d[4]) / tot
                cpu.append((t - t0, t - prev_t, busy, 100.0 * (d[0] + d[1]) / tot, 100.0 * d[2] / tot,
                            100.0 * (d[5] + d[6]) / tot, (w - prev_w) / 1000.0 if w is not None and prev_w is not None else None))
            prev_c, prev_t, prev_w = c, t, w
            next_c = max(next_c + 0.1, mono + 0.02)
        if mono >= next_p:
            p, t = read_procs(), time.time()
            procs.append((t - t0, t - prev_pt, delta_use(prev_p, p, tick)))
            prev_p, prev_pt = p, t
            next_p = max(next_p + 0.25, mono + 0.05)
    return events, cpu, procs, thread_delta(th0, thread_ticks(), tick)


def top(use, n=3):
    items = sorted(use.items(), key=lambda kv: -kv[1])[:n]
    return ", ".join("%s %.2fs" % (k, v) for k, v in items if v >= 0.01) or "-"


def window_use(procs, t0, t1):
    use = {}
    for te, dt, u in procs:
        if t0 < te <= t1 + 0.25:
            for k, v in u.items():
                use[k] = use.get(k, 0.0) + v
    return use


def busy_run(cpu, t):
    """Seconds of consecutive busy samples that start within 0.4 s after t (0.0 if none), and where that run ends."""
    run_start = run_end = None
    for te, dt, busy, *_ in cpu:
        if te <= t:
            continue
        if run_start is None:
            if te - dt > t + 0.4:
                break
            if busy >= BUSY:
                run_start, run_end = max(te - dt, t), te
        elif busy >= BUSY:
            run_end = te
        else:
            break
    return (run_end - run_start, run_end) if run_start is not None else (0.0, None)


def report(events, cpu, procs, threads=None):
    out = []
    p = out.append
    p("")
    p("=== key events (t seconds since start; value 1 press, 0 release, 2 kernel repeat; lag = read minus kernel stamp)")
    for t, code, value, lag in events:
        p("  %8.3f  %-6s %d   lag %6.1f ms" % (t, key_name(code), value, lag))
    typed = [key_name(c) for t, c, v, lag in events if v == 1 and (len(key_name(c)) == 1 or key_name(c) == "SPACE")]
    p("")
    p("=== key presses in order (letters and Space): %s" % (" ".join("_" if k == "SPACE" else k for k in typed) or "none"))
    p("")
    p("=== one row per key press")
    p("      t  key     held ms  repeats  idle before  CPU busy right after  who used the CPU (to the end of that stretch)")
    open_p, rows, last_t = {}, [], None
    for t, code, value, lag in events:
        if value == 1:
            open_p[code] = {"t": t, "code": code, "held": None, "rep": 0, "idle": (t - last_t) if last_t is not None else None}
            rows.append(open_p[code])
            last_t = t
        elif value == 2 and code in open_p:
            open_p[code]["rep"] += 1
            last_t = t
        elif value == 0 and code in open_p:
            open_p[code]["held"] = (t - open_p[code]["t"]) * 1000.0
            del open_p[code]
            last_t = t
    for r in rows:
        length, end = busy_run(cpu, r["t"])
        who = top(window_use(procs, r["t"], end), 3) if end else "-"
        p("  %6.2f  %-6s %8s  %7d  %11s  %20s  %s" % (
            r["t"], key_name(r["code"]), ("%.0f" % r["held"]) if r["held"] is not None else "open", r["rep"],
            ("%.2f s" % r["idle"]) if r["idle"] is not None else "-", ("%.1f s" % length) if length else "none", who))
    p("")
    p("=== busy stretches of 0.3 s or more (CPU at or above %d%% in 0.1 s samples)" % BUSY)
    seg, segs = None, []
    for te, dt, busy, usr, sy, irq, wait in cpu:
        if busy >= BUSY:
            seg = seg or {"s": te - dt, "e": te, "n": 0, "b": 0.0, "u": 0.0, "y": 0.0, "i": 0.0, "w": 0.0}
            seg["e"] = te
            seg["n"] += 1
            seg["b"] += busy
            seg["u"] += usr
            seg["y"] += sy
            seg["i"] += irq
            seg["w"] += wait or 0.0
        elif seg:
            segs.append(seg)
            seg = None
    if seg:
        segs.append(seg)
    for s in segs:
        if s["e"] - s["s"] >= 0.3:
            n = float(s["n"])
            p("  %8.2f  %5.1f s  busy %3.0f%% (user %3.0f sys %3.0f irq %2.0f)  scheduler wait %6.0f ms  %s" % (
                s["s"], s["e"] - s["s"], s["b"] / n, s["u"] / n, s["y"] / n, s["i"] / n, s["w"],
                top(window_use(procs, s["s"], s["e"] - 0.5), 4)))
    p("")
    allb = sorted(c[2] for c in cpu)
    if allb:
        p("=== totals: %d samples of 0.1 s over %.1f s; CPU busy median %.0f%%, 90th percentile %.0f%%, at or above %d%%: %.1f%% of the time"
          % (len(allb), cpu[-1][0], allb[len(allb) // 2], allb[int(len(allb) * 0.9)], BUSY,
             100.0 * sum(1 for b in allb if b >= BUSY) / len(allb)))
    use = window_use(procs, 0.0, cpu[-1][0] if cpu else 0.0)
    p("    CPU seconds by process over the whole run: %s" % top(use, 8))
    if threads:
        p("    CPU seconds by thread over the whole run: %s" % top(threads, 8))
    lags = sorted(e[3] for e in events)
    if lags:
        p("    read lag of key events: min %.1f median %.1f max %.1f ms (%d events); kernel repeats: %d; presses: %d"
          % (lags[0], lags[len(lags) // 2], lags[-1], len(lags), sum(1 for e in events if e[2] == 2), sum(1 for e in events if e[2] == 1)))
    else:
        p("    no key events")
    return "\n".join(out)


def selftest():
    # Super at 1.0 s with 2 s of full CPU after it (Hyprland, walker), slow letters, a held key with kernel repeats.
    ev = [(1.0, 125, 1, 0.5), (1.1, 57, 1, 0.4), (1.2, 57, 0, 0.4), (1.25, 125, 0, 0.3),
          (6.0, 35, 1, 0.5), (6.09, 35, 0, 0.4), (7.0, 24, 1, 0.6), (7.5, 24, 2, 0.6), (7.53, 24, 2, 0.6), (7.9, 24, 0, 0.5),
          (9.0, 28, 1, 0.4), (9.07, 28, 0, 0.4)]
    cpu = []
    for i in range(1, 140):
        t = i * 0.1
        b = 100.0 if 1.1 <= t <= 3.1 or 7.0 <= t <= 7.35 else 4.0
        cpu.append((t, 0.1, b, b * 0.7, b * 0.3, 0.0, 30.0 if b > 50 else 0.0))
    procs = [(i * 0.5, 0.5, {"Hyprland": 0.30, "walker": 0.15, "sh": 0.0} if 1.1 <= i * 0.5 <= 3.6 else {"foot": 0.05}) for i in range(1, 29)]
    text = report(ev, cpu, procs)
    print(text)
    assert "2.0 s" in text or "2.1 s" in text, text          # the run after Super
    assert "Hyprland" in text and "walker" in text
    assert "repeats" in text and "       2  " in text.replace("\t", " ") or " 2 " in text
    assert busy_run(cpu, 6.0)[0] == 0.0                         # the plain letter at 6.0 s has no busy run
    prev = {"7": ("kworker/u4:0-events_unbound", 79, 0), "9": ("sh", 1, 0)}
    cur = {"7": ("kworker/u4:0-dchid-keyboard", 80, 0), "9": ("sh", 1, 30), "11": ("new", 5, 0)}
    use = delta_use(prev, cur, 100.0)
    assert abs(use["kworker/u4:0-dchid-keyboard"] - 0.01) < 1e-9, use      # a renamed worker is not re-counted from zero
    assert abs(use["sh (children)"] - 0.30) < 1e-9 and abs(use["new"] - 0.05) < 1e-9, use
    th = thread_delta({("1", "1"): ("Hyprland", "Hyprland", 100), ("1", "2"): ("Hyprland", "llvmpipe-0", 50)},
                      {("1", "1"): ("Hyprland", "Hyprland", 110), ("1", "2"): ("Hyprland", "llvmpipe-0", 250), ("1", "3"): ("Hyprland", "new", 7)}, 100.0)
    assert th == {"Hyprland": 0.10, "Hyprland/llvmpipe-0": 2.0, "Hyprland/new": 0.07}, th
    print("\nselftest OK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
    else:
        ev, cpu, procs, threads = collect(sys.argv[1], float(sys.argv[2]))
        print(report(ev, cpu, procs, threads), flush=True)
