"""Read-only look at the M5's desktop load (written for attempt 26), run as the omarchy user over SSH from the M1:

    ssh -F tools/m1n1-client/m5-ssh-config m5o 'python3 -I -' < tools/m1n1-client/m5-probes/inspect_desktop.py

Prints, for an idle desktop: the load, six seconds of CPU use by process, the processes with the most CPU time since they started,
the `omarchy-menu*` processes, Hyprland's threads and mapped graphics libraries (Mesa's LLVM rasterizer shows up as libLLVM and
libgallium), its current options, the monitor, the open windows and the config lines about animations, blur and so on.
It only reads /proc and asks Hyprland for options with `hyprctl getoption/monitors/clients`; it changes nothing."""
import json
import os
import subprocess
import time


def run(argv, env=None, limit=40):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=30, env=env)
        out = (r.stdout or "") + (r.stderr or "")
    except Exception as e:                      # noqa: BLE001 - report and carry on
        out = "error: %r" % (e,)
    return "\n".join(l[:200] for l in out.strip("\n").splitlines()[:limit])


def section(title):
    print("\n== " + title, flush=True)


def procs():
    out = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            s = open("/proc/" + d + "/stat").read()
        except OSError:
            continue
        a, b = s.find("("), s.rfind(")")
        rest = s[b + 2:].split()
        try:
            out[d] = (s[a + 1:b], int(rest[11]) + int(rest[12]), int(rest[13]) + int(rest[14]))
        except (IndexError, ValueError):
            pass
    return out


def cpu():
    f = [int(x) for x in open("/proc/stat").readline().split()[1:9]]
    return sum(f), f[3] + f[4]


rt = "/run/user/%d" % os.getuid()
try:
    sig = sorted(os.listdir(rt + "/hypr"))[0]
except (OSError, IndexError):
    sig = ""
env = dict(os.environ, XDG_RUNTIME_DIR=rt, HYPRLAND_INSTANCE_SIGNATURE=sig)

section("uptime and load")
print(run(["uptime"]))
print(open("/proc/loadavg").read().strip())

section("CPU over the next 6 s (idle desktop, nothing touched): busy share and who used it")
t0, p0, c0 = time.time(), procs(), cpu()
time.sleep(6)
t1, p1, c1 = time.time(), procs(), cpu()
busy = 100.0 * ((c1[0] - c0[0]) - (c1[1] - c0[1])) / max(1, c1[0] - c0[0])
use = {}
for pid, (comm, own, kids) in p1.items():
    b = p0.get(pid)
    for label, d in ((comm, own - (b[1] if b else 0)), (comm + " (children)", kids - (b[2] if b else 0))):
        if d > 0:
            use[label] = use.get(label, 0.0) + d / 100.0
print("busy %.0f%% over %.1f s; by process: %s" % (
    busy, t1 - t0, ", ".join("%s %.2fs" % kv for kv in sorted(use.items(), key=lambda kv: -kv[1])[:8])))

section("processes by cumulative CPU time since they started (pid ppid elapsed-s cpu-time stat comm)")
print(run(["ps", "-eo", "pid,ppid,etimes,time,stat,comm", "--sort=-time"], limit=14))

section("omarchy-menu processes (pid ppid elapsed-s cpu-time stat args)")
lines = run(["ps", "-eo", "pid,ppid,etimes,time,stat,args"], limit=3000).splitlines()
print("\n".join(l for l in lines if "omarchy-menu" in l) or "none")

hp = run(["pgrep", "-x", "Hyprland"]).split()
hp = hp[0] if hp else ""
section("Hyprland pid %s: threads (tid comm cpu-time)" % (hp or "none"))
if hp:
    print(run(["ps", "-L", "-p", hp, "-o", "tid,comm,time"], limit=16))
    section("Hyprland: graphics libraries mapped")
    libs = set()
    try:
        for l in open("/proc/%s/maps" % hp):
            name = l.split()[-1] if len(l.split()) >= 6 else ""
            if any(k in name for k in ("LLVM", "swrast", "gallium", "_dri", "libEGL", "libGLES", "vulkan", "lvp", "pixman")):
                libs.add(os.path.basename(name))
    except OSError as e:
        libs.add("unreadable: %r" % (e,))
    print(", ".join(sorted(libs)) or "none of the usual names")

section("Hyprland options now")
for opt in ("animations:enabled", "misc:vfr", "decoration:blur:enabled", "decoration:shadow:enabled", "decoration:rounding",
            "render:direct_scanout", "general:allow_tearing", "input:repeat_rate", "input:repeat_delay", "cursor:no_hardware_cursors"):
    print("%-28s %s" % (opt, run(["hyprctl", "getoption", opt, "-j"], env=env).replace("\n", " ")[:110]))

section("monitors (name width height refresh scale format)")
try:
    for m in json.loads(run(["hyprctl", "monitors", "-j"], env=env, limit=400)):
        print(m.get("name"), m.get("width"), m.get("height"), m.get("refreshRate"), m.get("scale"), m.get("currentFormat"))
except Exception as e:                          # noqa: BLE001
    print("error: %r" % (e,))

section("windows open now (class and size only)")
try:
    for c in json.loads(run(["hyprctl", "clients", "-j"], env=env, limit=2000)):
        print(c.get("class"), c.get("size"))
except Exception as e:                          # noqa: BLE001
    print("error: %r" % (e,))

section("Hyprland config lines about animations, blur, shadow, vfr, monitor, render")
print(run(["grep", "-rn", "-E", r"^\s*(animations|animation|blur|shadow|rounding|monitor|vfr|enabled|direct_scanout|no_hardware_cursors)\b",
           os.path.expanduser("~/.config/hypr"), "/usr/share/omarchy/default/hypr"], limit=60))

section("which omarchy-menu* scripts exist")
print(run(["sh", "-c", "ls -1 /usr/local/bin /usr/bin ~/.local/share/omarchy/bin 2>/dev/null | grep -i 'omarchy-menu' | sort -u"], limit=40))
