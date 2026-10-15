#!/usr/bin/env python3
"""Offline check of patches/0002 (MTP ring transport) on top of the pinned driver.

usage: python3 -I check_driver.py --repo PATH_TO_ASAHI_LINUX_CLONE [--mutate] [--cc clang]

Reads the pinned source as data (git show), applies 0001 and 0002 in a temporary
directory, then (1) syntax-checks the result against kshim.h, (2) builds the
behaviour harness with ASan/UBSan and runs it, (3) optionally runs the driver
mutation check. Nothing is installed, committed or booted; the kernel build
itself is not part of this check (that is VM job 042).
Stdlib only.
"""
import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver_build  # noqa: E402

BASE = "77cb8f24c2381a8abb7272d7bbdec548d6426a8a"
PATH = "drivers/hid/dockchannel-hid/dockchannel-hid.c"
RING_PATH = "drivers/hid/dockchannel-hid/dchid-ring.h"
BASE_SHA256 = "15c1186c3bbb87dddb75c1f1053ab3a2c3a2a1128bba6718bd88977f4b7beb2f"
P0001_SHA256 = "e888ddaefc7d05f582b1db831ec9f2bd2e9858f4503242edf7c369866c45605c"
PATCH_0001 = HERE.parent.parent / "driver-contracts" / "dockchannel-hid" / \
    "0001-dockchannel-hid-validate-input-bounds.patch"
PATCH_0002 = HERE.parent / "patches" / "0002-dockchannel-hid-mtp-ring-transport.patch"
RING_SOURCE = HERE.parent / "ring" / "dchid_ring.h"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def step(name):
    print("== " + name, flush=True)


def need(ok, message):
    if not ok:
        print("FAIL: " + message)
        sys.exit(1)
    print("   ok: " + message)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--cc", default="clang")
    ap.add_argument("--mutate", action="store_true")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        step("pinned source")
        base = subprocess.check_output(["git", "-C", str(args.repo.resolve()), "show", BASE + ":" + PATH])
        need(sha(base) == BASE_SHA256, "base digest " + BASE_SHA256[:12])
        tree = work / "patched"
        (tree / PATH).parent.mkdir(parents=True)
        (tree / PATH).write_bytes(base)

        step("apply 0001, then 0002")
        subprocess.run(["patch", "-p1", "-s", "-i", str(PATCH_0001)], cwd=tree, check=True)
        need(sha((tree / PATH).read_bytes()) == P0001_SHA256, "after 0001 digest " + P0001_SHA256[:12])
        dry = subprocess.run(["patch", "-p1", "--dry-run", "-s", "-i", str(PATCH_0002)], cwd=tree)
        need(dry.returncode == 0, "0002 applies cleanly (dry run)")
        subprocess.run(["patch", "-p1", "-s", "-i", str(PATCH_0002)], cwd=tree, check=True)
        patched = (tree / PATH).read_bytes()
        ring = (tree / RING_PATH).read_bytes()
        need(ring == RING_SOURCE.read_bytes(), "dchid-ring.h in the patch equals ring/dchid_ring.h")
        print("   patched driver sha256 " + sha(patched))
        print("   dchid-ring.h   sha256 " + sha(ring))

        step("syntax check against kshim.h")
        tdir, inc = driver_build.prepare_tree(work / "syn", tree / PATH, tree / RING_PATH)
        code, _, err = driver_build.run(driver_build.compile_cmd(
            args.cc, tdir, inc, tdir / "dockchannel-hid.c", None, syntax_only=True))
        need(code == 0, "no errors" + ("" if code == 0 else "\n" + err[:2000]))

        step("behaviour harness (ASan + UBSan)")
        tdir, inc = driver_build.prepare_tree(work / "run", tree / PATH, tree / RING_PATH)
        exe = work / "test_driver"
        code, _, err = driver_build.run(driver_build.compile_cmd(
            args.cc, tdir, inc, HERE / "test_driver.c", exe))
        need(code == 0, "harness builds" + ("" if code == 0 else "\n" + err[:2000]))
        code, out, err = driver_build.run([str(exe)], 300)
        last = (out + err).strip().splitlines()
        print("   " + (last[-1] if last else "(no output)"))
        need(code == 0, "harness passes")

        if args.mutate:
            step("driver mutation check")
            r = subprocess.run([sys.executable, "-I", str(HERE / "mutate_driver.py"),
                                str(tree / PATH), str(tree / RING_PATH), args.cc])
            need(r.returncode == 0, "every mutant caught")

    print("check_driver: PASS (the kernel-side build is VM job 042)")


if __name__ == "__main__":
    main()
