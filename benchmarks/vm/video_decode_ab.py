#!/usr/bin/env python3
"""Bounded decode-only ABBA experiment, same guest driver with NV12 off/on.

No frames are downloaded or displayed. Records completed FFmpeg frames, host
QEMU CPU seconds and read-only IOReport energy. The guest process is bounded
and waited for; no unrelated players are stopped. This is not a display test.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("power_summary", ROOT / "tools/power_summary.py")
power = importlib.util.module_from_spec(spec)
spec.loader.exec_module(power)


def guest(command):
    return subprocess.check_output([sys.executable, "-I", str(ROOT / "tools/vmconsole.py"),
                                    str(ROOT / "virtualization/run/console.sock"), command, "15"],
                                   text=True)


def cpu_seconds(pid):
    raw = subprocess.check_output(["ps", "-p", str(pid), "-o", "time="], text=True).strip()
    values = raw.replace("-", ":").split(":")
    total = 0.0
    for part in values:
        total = total * 60 + float(part)
    return total


def stop_owned_decode(prefix):
    # Signal only the timeout process recorded by this run, and only while
    # its argument list still contains our unique progress-file name.
    guest(f'if [ -f {prefix}.pid ] && [ ! -f {prefix}.rc ]; then '
          f'read -r decode_pid < {prefix}.pid; '
          'case "$(ps -p "$decode_pid" -o args=)" in '
          f'*{shlex.quote(prefix + ".progress")}*) '
          'kill -TERM "$decode_pid" 2>/dev/null || :;; esac; fi')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out", type=Path)
    p.add_argument("--driver", default="/var/tmp/mesa-video/patched")
    p.add_argument("--clip", default="/var/tmp/vt/r2160.mp4")
    p.add_argument("--window", type=int, default=10)
    p.add_argument("--reps", type=int, default=2, help="ABBA blocks")
    a = p.parse_args()
    if not 2 <= a.window <= 30 or not 1 <= a.reps <= 4:
        p.error("window must be 2..30 seconds and reps 1..4")
    a.out.mkdir(parents=True, exist_ok=False)
    pid = int((ROOT / "virtualization/run/qemu.pid").read_text())
    meta = {"kind": "decode_only", "window_s": a.window, "driver": a.driver,
            "clip": a.clip, "host_os": subprocess.check_output(["sw_vers"], text=True),
            "power": subprocess.check_output(["pmset", "-g", "batt"], text=True).splitlines()[0],
            "power_settings": subprocess.check_output(["pmset", "-g", "custom"], text=True),
            "guest": guest("uname -r; pacman -Q ffmpeg mesa libva; cc --version | head -1"),
            "started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (a.out / "environment.json").write_text(json.dumps(meta, indent=2) + "\n")
    results = []
    for index, enabled in enumerate([0, 1, 1, 0] * a.reps):
        prefix = f"/var/tmp/mesa-video/ab-{os.getpid()}-{index}"
        # 4 seconds warm-up, then measurement, then enough slack for collection.
        duration = a.window + 8
        cmd = ["env", "LIBVA_DRIVERS_PATH=" + a.driver,
               "VIRGL_VIDEO_DECODE_NV12=" + str(enabled),
               "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-re",
               "-stream_loop", "-1", "-hwaccel", "vaapi", "-hwaccel_device",
               "/dev/dri/renderD128", "-hwaccel_output_format", "vaapi", "-i", a.clip,
               "-t", str(duration), "-progress", prefix + ".progress", "-f", "null", "-"]
        wall_limit = duration + 15
        start = (f"(timeout --signal=TERM --kill-after=2s {wall_limit}s "
                 f"{' '.join(map(shlex.quote, cmd))} > {prefix}.log 2>&1 & "
                 f'decode_pid=$!; echo "$decode_pid" > {prefix}.pid; '
                 f'wait "$decode_pid"; echo $? > {prefix}.rc) & echo started')
        try:
            guest(start)
            time.sleep(4)
            q0, t0 = cpu_seconds(pid), time.monotonic()
            pm = subprocess.run([str(ROOT / "benchmarks/bin/powermon"), "-i", "250", "--",
                                 "sleep", str(a.window)], capture_output=True, text=True,
                                check=True, timeout=a.window + 15)
            q1, t1 = cpu_seconds(pid), time.monotonic()
            (a.out / f"power-{index}-nv12-{enabled}.jsonl").write_text(pm.stdout)
            sample = next(line for line in pm.stdout.splitlines() if line.startswith('{"bench":"power"'))
            time.sleep(5)
            done = guest(f"cat {prefix}.rc; tail -12 {prefix}.progress; cat {prefix}.log")
            (a.out / f"guest-{index}.txt").write_text(done)
            rc = re.search(r"(?m)^0$", done)
            frames = re.findall(r"(?m)^frame=(\d+)$", done)
            if not rc or "progress=end" not in done or not frames or int(frames[-1]) == 0:
                raise RuntimeError("decode did not complete successfully: " + done)
        finally:
            stop_owned_decode(prefix)
        rec = {"index": index, "nv12": bool(enabled), "frames": int(frames[-1]),
               "qemu_cores": round((q1 - q0) / (t1 - t0), 4), **power.summarize(sample)}
        results.append(rec)
        (a.out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(rec), flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main()
