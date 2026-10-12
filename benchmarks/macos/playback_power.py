#!/usr/bin/env python3
"""macOS-native counterpart of benchmarks/vm/playback_power.py: SoC power while
AVFoundation (hardware decode) loops the same clips in a window the size of the
VM window (benchmarks/bin/avplay), against an idle baseline.  Run it with the
VM shut down.  Cases run forward, then reversed (ABBA).

Usage: playback_power.py CLIPDIR OUTDIR [--window S] [--warmup S] [--reps N]"""
import argparse, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POWERMON = os.path.join(ROOT, "benchmarks/bin/powermon")
AVPLAY = os.path.join(ROOT, "benchmarks/bin/avplay")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from power_summary import summarize  # noqa: E402

CASES = [("idle", None), ("native-2160", "r2160.mp4"), ("native-1080", "r1080.mp4")]


def run_case(name, clip, rep, a):
    player = None
    if clip:
        player = subprocess.Popen([AVPLAY, os.path.join(a.clipdir, clip), str(a.warmup + a.window + 2)],
                                  stdout=subprocess.PIPE, text=True)
    time.sleep(a.warmup)
    pm = subprocess.run([POWERMON, "-i", "250", "--", "sleep", str(a.window)],
                        capture_output=True, text=True).stdout
    av = {}
    if player:
        out, _ = player.communicate(timeout=60)
        av = json.loads(next((l for l in out.splitlines() if l.startswith("{")), "{}"))
    with open(os.path.join(a.outdir, f"powermon-{name}-r{rep}.jsonl"), "w") as f:
        f.write(pm)
    line = next(l for l in pm.splitlines() if l.startswith('{"bench":"power"'))
    return {"case": name, "rep": rep, "clip": clip,
            **{k: v for k, v in summarize(line).items() if k != "seconds"},
            **({"dropped_frames": av.get("dropped_frames"), "loops": av.get("loops")} if clip else {})}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("clipdir")
    p.add_argument("outdir")
    p.add_argument("--window", type=float, default=25)
    p.add_argument("--warmup", type=float, default=6)
    p.add_argument("--reps", type=int, default=2)
    a = p.parse_args()
    if subprocess.run(["pgrep", "-f", "qemu-system-aarch64"], capture_output=True).returncode == 0:
        sys.exit("shut the VM down first: this is the native baseline")
    os.makedirs(a.outdir, exist_ok=True)
    meta = {"power_source": subprocess.run(["pmset", "-g", "batt"], capture_output=True,
                                           text=True).stdout.splitlines()[0],
            "window_s": a.window, "warmup_s": a.warmup, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out = open(os.path.join(a.outdir, "playback-power-native.jsonl"), "a")
    out.write(json.dumps({"meta": meta}) + "\n")
    order = []
    for rep in range(a.reps):
        order += [(c, rep) for c in (CASES if rep % 2 == 0 else CASES[::-1])]
    recs = []
    for (name, clip), rep in order:
        rec = run_case(name, clip, rep, a)
        recs.append(rec)
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(json.dumps(rec), flush=True)
        time.sleep(3)
    print("\ncase          soc_W  cpu_W  gpu_W  dram_W  memctl_W  media_W")
    for name, _ in CASES:
        rs = [r for r in recs if r["case"] == name]
        mean = lambda k: sum(r[k] for r in rs) / len(rs)
        print(f"{name:12} {mean('soc_W'):6.2f} {mean('cpu_W'):6.2f} {mean('gpu_W'):6.2f} {mean('dram_W'):7.2f}"
              f" {mean('memctl_W'):9.2f} {mean('media_W'):8.2f}")


if __name__ == "__main__":
    main()
