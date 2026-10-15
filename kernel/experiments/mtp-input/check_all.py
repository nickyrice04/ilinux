#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only OR MIT
"""Run every offline check of the MTP input experiment (nothing touches hardware).

usage: python3 -I check_all.py [--repo ASAHI_CLONE] [--base-dtb DTB] [--kernel-config CONFIG]
                               [--quick] [--cc clang]

Steps: DT delta tests and build, config delta, ring/framing core tests, ring
mutation check, driver patch (apply + syntax + behaviour harness), driver mutation
check, firmware converter tests and mutation check, probe tests and mutation check.
--quick skips the three mutation suites. A step whose input is missing is SKIPped
with the reason; the exit code is non-zero only if a step that ran failed.
Stdlib only. The kernel build itself is VM job 042, not part of this.
"""
import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PY = [sys.executable, "-I"]


def run(name, cmd, results, timeout=900, cwd=None):
    start = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        ok = r.returncode == 0
        tail = (r.stdout + r.stderr).strip().splitlines()
        detail = tail[-1] if tail else ""
    except subprocess.TimeoutExpired:
        ok, detail = False, "timeout"
    results.append((name, "PASS" if ok else "FAIL", detail, time.time() - start))
    return ok


def skip(name, reason, results):
    results.append((name, "SKIP", reason, 0.0))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, help="pinned asahi-linux clone (for the driver patch check)")
    ap.add_argument("--base-dtb", type=Path,
                    default=ROOT / "build" / "native-boot035" / "verified" / "t6050-j716c-stage-b.dtb")
    ap.add_argument("--kernel-config", type=Path,
                    default=ROOT / "build" / "native-boot035" / "verified" / "kernel.config")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--cc", default="clang")
    args = ap.parse_args()
    results = []

    adt = ROOT / "hardware" / "adt" / "adt-sanitized.json"
    fdtedit = HERE.parent / "usb-gadget-dt" / "fdtedit.py"
    if fdtedit.is_file():
        run("dt: unit tests", PY + [str(HERE / "test_mtp_dt.py")], results)
    else:
        skip("dt: unit tests", "usb-gadget-dt/fdtedit.py is not in this checkout (sibling experiment)", results)
    if not fdtedit.is_file():
        skip("dt: build + structural check", "usb-gadget-dt/fdtedit.py is not in this checkout", results)
    elif args.base_dtb.is_file() and adt.is_file():
        with tempfile.TemporaryDirectory() as d:
            run("dt: build + structural check", PY + [str(HERE / "make_mtp_dt.py"), str(args.base_dtb),
                                                      str(adt), str(Path(d) / "out.dtb"),
                                                      str(Path(d) / "delta.json")], results)
    else:
        skip("dt: build + structural check", "base DTB or ADT export not found", results)

    if args.kernel_config.is_file():
        run("config: delta against the boot kernel", PY + [str(HERE / "check_config.py"),
                                                         str(args.kernel_config)], results)
    else:
        skip("config: delta against the boot kernel", "kernel.config not found", results)

    with tempfile.TemporaryDirectory() as d:
        exe = Path(d) / "test_ring"
        built = run("ring: build tests (ASan/UBSan)",
                    [args.cc, "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                     "-fsanitize=address,undefined", "-fno-sanitize-recover=undefined",
                     "-I", str(HERE / "ring"), str(HERE / "ring" / "test_ring.c"), "-o", str(exe)],
                    results)
        if built:
            run("ring: tests", [str(exe)], results)
    if not args.quick:
        run("ring: mutation check", PY + [str(HERE / "ring" / "mutate_ring.py"), args.cc], results)

    if args.repo is not None:
        cmd = PY + [str(HERE / "driver-test" / "check_driver.py"), "--repo", str(args.repo),
                    "--cc", args.cc]
        if not args.quick:
            cmd.append("--mutate")
        run("driver: patch + syntax + behaviour" + ("" if args.quick else " + mutation"), cmd, results,
            timeout=1800)
    else:
        skip("driver: patch + syntax + behaviour", "pass --repo with the pinned asahi-linux clone", results)

    run("fw: converter tests", PY + [str(HERE / "fw" / "test_mtfw_convert.py")], results)
    if not args.quick:
        run("fw: mutation check", PY + [str(HERE / "fw" / "mutate_fw.py")], results)

    run("probe: tests", PY + [str(HERE / "probe" / "test_mtp_probe.py")], results)
    if not args.quick:
        run("probe: mutation check", PY + [str(HERE / "probe" / "mutate_probe.py")], results)

    width = max(len(r[0]) for r in results)
    failed = 0
    for name, status, detail, secs in results:
        print("%-*s  %-4s  %5.1fs  %s" % (width, name, status, secs, detail[:100]))
        failed += status == "FAIL"
    print("%d steps, %d failed (hardware NOT touched; the kernel-side build is VM job 042)" % (len(results), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
