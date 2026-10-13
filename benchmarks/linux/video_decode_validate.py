#!/usr/bin/env python3
"""Compare VA-API downloads against software decode, without displaying video.

Run in Linux. Each clip is decoded with the default surface selection and with
the NV12 opt-in, downloading both planar and NV12 images. All hashes represent
the same packed yuv420p bytes. A failed command, empty output, missing frame,
timestamp difference, or checksum mismatch is a failure, never a pass.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def rows(path):
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.startswith("#")]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out", type=Path)
    p.add_argument("clips", nargs="+", type=Path)
    p.add_argument("--driver", type=Path, required=True)
    p.add_argument("--frames", type=int, default=180)
    p.add_argument("--report-only", action="store_true",
                   help="record expected baseline failures without a failing exit status")
    a = p.parse_args()
    if a.frames < 1:
        p.error("--frames must be positive")
    a.out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, LIBVA_DRIVERS_PATH=str(a.driver.resolve()))
    results = []
    for index, clip in enumerate(a.clips):
        prefix = f"{index}-{clip.stem}"
        identity = {"clip": str(clip.resolve()),
                    "clip_sha256": hashlib.file_digest(clip.open("rb"), "sha256").hexdigest()}
        reference = None
        for name, nv12, fmt in [("software", None, None),
                                ("default-planar", 0, "yuv420p"),
                                ("default-nv12", 0, "nv12"),
                                ("nv12-planar", 1, "yuv420p"),
                                ("nv12-nv12", 1, "nv12")]:
            output = a.out / f"{prefix}-{name}.md5"
            cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-v", "verbose"]
            if nv12 is not None:
                cmd += ["-hwaccel", "vaapi", "-hwaccel_device", "/dev/dri/renderD128",
                        "-hwaccel_output_format", "vaapi"]
            cmd += ["-i", str(clip), "-map", "0:v:0", "-frames:v", str(a.frames)]
            cmd += (["-vf", f"hwdownload,format={fmt},format=yuv420p"] if fmt
                    else ["-pix_fmt", "yuv420p"])
            cmd += ["-f", "framemd5", str(output)]
            started = time.monotonic()
            proc = subprocess.run(cmd, env=dict(env, VIRGL_VIDEO_DECODE_NV12=str(nv12 or 0)),
                                  capture_output=True, text=True, timeout=180)
            (a.out / f"{prefix}-{name}.log").write_text(proc.stderr)
            actual = rows(output) if output.exists() else []
            if nv12 is None:
                reference = actual
            mismatch = sum(x != y for x, y in zip(reference, actual))
            mismatch += abs(len(reference) - len(actual))
            rec = {**identity, "case": name, "command": cmd, "returncode": proc.returncode,
                   "seconds": round(time.monotonic() - started, 4), "frames": len(actual),
                   "mismatched_frames": mismatch,
                   "pass": proc.returncode == 0 and len(actual) == a.frames and mismatch == 0}
            results.append(rec)
            print(json.dumps(rec), flush=True)
    (a.out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return int(not a.report_only and any(not r["pass"] for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
