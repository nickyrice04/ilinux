#!/usr/bin/env python3
"""Prepare pinned public m1n1 source as data; build/run it only inside Linux."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

BASE = "57a9339ffd1876e78297b17d34dece8cff8fa1ba"
DIGESTS = {
    "baseline": "4b000be8d4e6437fc24351a57db5277785cc2e427045fb45d1750b158f2b8766",
    "patched": "e4b93c02dd051cf7f72c36f4e8d019133b5793d1b64165a265fa7912c9b4cc45",
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    repo = args.repo.resolve()
    out = args.output.resolve()
    here = Path(__file__).resolve().parent
    # A pinned disposable header tree is copied as data, never executed on host.
    if subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() != BASE:
        raise ValueError("unexpected m1n1 snapshot")
    if subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain", "--", "src", "sysinc", "config.h"]):
        raise ValueError("m1n1 source has local changes")
    source = subprocess.check_output(["git", "-C", str(repo), "show", BASE + ":src/smp.c"])
    if hashlib.sha256(source).hexdigest() != DIGESTS["baseline"]:
        raise ValueError("source digest mismatch")
    out.mkdir(parents=True, exist_ok=False)
    for variant in DIGESTS:
        target = out / variant / "src/smp.c"
        target.parent.mkdir(parents=True)
        target.write_bytes(source)
    patch = here / "0001-smp-stop-on-locked-rvbar-mismatch.patch"
    subprocess.run(["patch", "-p1", "-i", str(patch)], cwd=out / "patched", check=True)
    for variant, digest in DIGESTS.items():
        data = (out / variant / "src/smp.c").read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("patched source digest mismatch")
        match = re.search(r"^static void smp_start_cpu\([^;]*?\n\{.*?^}\n", data.decode(), re.M | re.S)
        if match is None:
            raise ValueError("cannot extract actual startup function")
        (out / variant / "startup.inc").write_text(match.group())
    for directory in ("src", "sysinc"):
        shutil.copytree(repo / directory, out / "object" / directory, symlinks=True)
    shutil.copyfile(repo / "config.h", out / "object/config.h")
    shutil.copyfile(out / "patched/src/smp.c", out / "object/src/smp.c")
    for name in ("test_startup.c", "run-linux.sh"):
        shutil.copyfile(here / name, out / name)
    (out / "manifest.json").write_text(json.dumps({
        "base_commit": BASE, "source_path": "src/smp.c", "source_sha256": DIGESTS,
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "scope": "actual startup function with synthetic CPU/register hooks; full smp.o compile",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
