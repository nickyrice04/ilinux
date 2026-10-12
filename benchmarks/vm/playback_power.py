#!/usr/bin/env python3
"""Real-time video playback cost in the Omarchy VM: VideoToolbox-backed VA-API
decode vs guest software decode vs an idle desktop.

For each case the guest helper (guest/pb.sh + guest/stats.lua, pushed to
/var/tmp/vt) loops a clip fullscreen in mpv inside the Hyprland session.  After
a warm-up, one fixed window is measured:
  host   SoC energy per block (benchmarks/bin/powermon, IOReport, no root)
         and QEMU process CPU time
  guest  busy vCPU time (/proc/stat), player CPU time, mpv drop/delay counters
The dec-* cases decode with FFmpeg paced at the clip's frame rate and display
nothing, which separates decode cost from presentation cost.  The VM window
must be on screen (checked per case with benchmarks/bin/winvis); a hidden
window is never drawn or composited, so presentation would go unmeasured.
Cases run forward, then reversed (ABBA), to cancel slow drift.

Usage: playback_power.py OUTDIR [--window S] [--warmup S] [--reps N] [--cases a,b,...]
Output: OUTDIR/playback-power.jsonl (one record per case and rep) plus the raw
powermon output per case, and a summary table on stdout."""
import argparse, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOCK = os.path.join(ROOT, "virtualization/run/console.sock")
POWERMON = os.path.join(ROOT, "benchmarks/bin/powermon")
WINVIS = os.path.join(ROOT, "benchmarks/bin/winvis")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from power_summary import summarize  # noqa: E402

CASES = [("idle", None, None), ("hw-2160", "hw", "r2160.mp4"), ("sw-2160", "sw", "r2160.mp4"),
         ("hw-1080", "hw", "r1080.mp4"), ("sw-1080", "sw", "r1080.mp4"),
         # decode only (FFmpeg -re, nothing displayed): separates decode from display cost
         ("dec-hw-2160", "dec-hw", "r2160.mp4"), ("dec-sw-2160", "dec-sw", "r2160.mp4"),
         # display chain only: vfill fullscreen at 60 fps / unpaced FIFO; -ds with
         # Hyprland direct scanout
         ("vfill-60", "vfill-60", "-"), ("vfill-60-ds", "vfill-60-ds", "-"),
         ("vfill-fifo", "vfill-0", "-"),
         # mpv render paths for the same hardware decode
         ("hw-fast-2160", "hw-fast", "r2160.mp4"), ("hw-next-2160", "hw-next", "r2160.mp4"),
         ("hw-next-fast-2160", "hw-next-fast", "r2160.mp4"),
         ("hw-dmabuf-2160", "hw-dmabuf", "r2160.mp4")]
COUNTERS = ["frame-drop-count", "decoder-frame-drop-count", "vo-delayed-frame-count"]


def guest(cmd, timeout=30):
    return subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools/vmconsole.py"), SOCK,
                           cmd, str(timeout)], capture_output=True, text=True).stdout


def snap():
    m = re.search(r"^SNAP (.*)$", guest("/var/tmp/vt/pb.sh snap"), re.M)
    if not m:
        raise RuntimeError("guest snapshot failed")
    return dict(kv.split("=", 1) for kv in m.group(1).split())


def qemu_cpu_s(pid):
    # ps TIME is [[dd-]hh:]mm:ss.ss of user+system CPU for the whole process
    t = subprocess.run(["ps", "-o", "time=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    days, _, t = t.rpartition("-")
    secs = 0.0
    for part in t.split(":"):
        secs = secs * 60 + float(part)
    return secs + (int(days) * 86400 if days else 0)


def vm_window_on_screen(pid):
    # A VM window that is not on screen is never drawn or composited, so the
    # host side of presentation would go unmeasured (benchmarks/src/winvis.m).
    out = subprocess.run([WINVIS, str(pid)], capture_output=True, text=True).stdout
    try:
        return json.loads(out)["on_screen_windows"] > 0
    except (ValueError, KeyError):
        return None


def num(d, k):
    try:
        return float(d.get(k, "nan"))
    except ValueError:
        return float("nan")


def run_case(name, mode, clip, rep, a, pid):
    guest("/var/tmp/vt/pb.sh stop")
    if mode:
        guest(f"/var/tmp/vt/pb.sh start {mode} {clip}")
    time.sleep(a.warmup)
    vis0 = vm_window_on_screen(pid)
    s0, q0, t0 = snap(), qemu_cpu_s(pid), time.time()
    pm = subprocess.run([POWERMON, "-i", "250", "--", "sleep", str(a.window)], capture_output=True, text=True).stdout
    s1, q1, t1 = snap(), qemu_cpu_s(pid), time.time()
    vis1 = vm_window_on_screen(pid)
    guest("/var/tmp/vt/pb.sh stop")
    with open(os.path.join(a.outdir, f"powermon-{name}-r{rep}.jsonl"), "w") as f:
        f.write(pm)
    line = next(l for l in pm.splitlines() if l.startswith('{"bench":"power"'))
    hz, dt = num(s1, "hz"), num(s1, "up") - num(s0, "up")
    rec = {"case": name, "rep": rep, "clip": clip, "decode": mode, "window_s": round(t1 - t0, 2),
           "vm_window_on_screen": vis0 if vis0 == vis1 else "changed",
           **{k: v for k, v in summarize(line).items() if k != "seconds"},
           "qemu_cores": round((q1 - q0) / (t1 - t0), 3),
           "guest_vcpus_busy": round((num(s1, "busy") - num(s0, "busy")) / hz / dt, 3),
           "player_cores": round((num(s1, "mpv") - num(s0, "mpv")) / hz / dt, 3)}
    if mode and mode.startswith("vfill"):
        rec["vfill_fps"] = round((num(s1, "vfill_frames") - num(s0, "vfill_frames")) / dt, 2)
    if mode and mode.startswith(("hw", "sw")):
        rec.update({"hwdec": s1.get("hwdec-current"), "est_fps": num(s1, "estimated-vf-fps"),
                    "display_fps": num(s1, "display-fps"),
                    **{c.replace("-count", ""): num(s1, c) - num(s0, c) for c in COUNTERS}})
    return rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument("outdir")
    p.add_argument("--window", type=float, default=25)
    p.add_argument("--warmup", type=float, default=6)
    p.add_argument("--reps", type=int, default=2)
    p.add_argument("--cases", help="comma-separated subset of: " + ",".join(c[0] for c in CASES))
    p.add_argument("--allow-hidden", action="store_true",
                   help="run even if the VM window is not on screen (presentation then goes unmeasured)")
    a = p.parse_args()
    cases = [c for c in CASES if not a.cases or c[0] in a.cases.split(",")]
    os.makedirs(a.outdir, exist_ok=True)
    pid = int(subprocess.run(["pgrep", "-n", "-f", "qemu-system-aarch64"], capture_output=True,
                             text=True).stdout.split()[0])
    if not vm_window_on_screen(pid) and not a.allow_hidden:
        sys.exit("the VM window is not on screen: macOS would not draw it, so presentation would go "
                 "unmeasured (bring it into view, or pass --allow-hidden)")
    meta = {"power_source": subprocess.run(["pmset", "-g", "batt"], capture_output=True,
                                           text=True).stdout.splitlines()[0],
            "window_s": a.window, "warmup_s": a.warmup, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out = open(os.path.join(a.outdir, "playback-power.jsonl"), "a")
    out.write(json.dumps({"meta": meta}) + "\n")
    order = []
    for rep in range(a.reps):
        order += [(c, rep) for c in (cases if rep % 2 == 0 else cases[::-1])]
    recs = []
    for (name, mode, clip), rep in order:
        rec = run_case(name, mode, clip, rep, a, pid)
        recs.append(rec)
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(json.dumps(rec), flush=True)
        time.sleep(3)
    print("\ncase          soc_W  cpu_W  gpu_W  dram_W  qemu_cores  guest_vcpus  player_cores  drops")
    for name, _, _ in cases:
        rs = [r for r in recs if r["case"] == name]
        mean = lambda k: sum(r.get(k, 0) for r in rs) / len(rs)
        print(f"{name:12} {mean('soc_W'):6.2f} {mean('cpu_W'):6.2f} {mean('gpu_W'):6.2f} {mean('dram_W'):7.2f}"
              f" {mean('qemu_cores'):11.2f} {mean('guest_vcpus_busy'):12.2f} {mean('player_cores'):13.2f}"
              f" {mean('frame-drop'):6.1f}")


if __name__ == "__main__":
    main()
