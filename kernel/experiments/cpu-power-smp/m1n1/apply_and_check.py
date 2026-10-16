#!/usr/bin/env python3
"""Apply the two SMP patches to a scratch copy of the pinned public m1n1 tree and compile-check them.

Nothing in the given repository is modified.  Usage:
  python3 -I apply_and_check.py <pinned m1n1 clone> <new scratch dir> [--clang PATH]
Checks: pinned commit, clean source tree, baseline digests, patches apply, smp.c builds with m1n1's
C flags for aarch64 (clang, no linking), start.S assembles, and the new symbols exist.
"""
import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

BASE = "57a9339ffd1876e78297b17d34dece8cff8fa1ba"
BASELINE = {
    "src/smp.c": "4b000be8d4e6437fc24351a57db5277785cc2e427045fb45d1750b158f2b8766",
    "src/start.S": "91de75024c12f034a046171e88c8be9377bb09e4bfe95bf1ac5ba3cdd1e423ea",
    "src/smp_asm.h": "2afe4c4ac4cd696a2d020fcef5621aa1ac66c2e7edcaaaef11f17df17cc696bd",
}
PATCHES = [
    "0001-smp-route-late-entries-at-_start-through-cpu_reset.patch",
    "0002-smp-pack-t6050-start-bitmaps-from-ADT-clusters.patch",
]
CFLAGS = ("-O2 -Wall -g -Wundef -Werror=strict-prototypes -fno-common -fno-PIE "
          "-Werror=implicit-function-declaration -Werror=implicit-int -Wsign-compare "
          "-Wunused-parameter -Wno-multichar -ffreestanding -fpic -ffunction-sections "
          "-fdata-sections -nostdinc -isystem sysinc -Isrc -Isrc/hv -fno-stack-protector "
          "-mstrict-align -march=armv8.2-a -mgeneral-regs-only -Werror").split()
XCODE_CLANG = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--clang", default=XCODE_CLANG if Path(XCODE_CLANG).exists() else "clang")
    a = ap.parse_args()
    repo, out, here = a.repo.resolve(), a.out.resolve(), Path(__file__).resolve().parent
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if head != BASE:
        sys.exit("unexpected m1n1 commit %s" % head)
    if subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain", "--", "src", "sysinc", "config.h"]):
        sys.exit("m1n1 source tree has local changes")
    for rel, digest in BASELINE.items():
        if sha(repo / rel) != digest:
            sys.exit("baseline digest mismatch for " + rel)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(repo / "src", out / "src", symlinks=True)
    shutil.copytree(repo / "sysinc", out / "sysinc", symlinks=True)
    shutil.copyfile(repo / "config.h", out / "config.h")
    for name in PATCHES:
        subprocess.run(["patch", "-p1", "--no-backup-if-mismatch", "-i", str(here / name)], cwd=out, check=True)
    inc = subprocess.check_output([a.clang, "-print-file-name=include"], text=True).strip()
    target = ["--target=aarch64-linux-gnu"]
    subprocess.run([a.clang, *target, *CFLAGS, "-isystem", inc, "-c", "src/smp.c", "-o", "smp.o"], cwd=out, check=True)
    subprocess.run([a.clang, *target, "-DTARGET=T6050", "-Isrc", "-c", "src/start.S", "-o", "start.o"], cwd=out, check=True)
    nm = shutil.which("llvm-nm") or str(Path(a.clang).parent / "llvm-nm")
    nm_run = subprocess.run([nm, "smp.o", "start.o"], cwd=out, text=True, capture_output=True)
    if nm_run.returncode:
        sys.exit("llvm-nm failed: %s" % nm_run.stderr.strip())
    syms = nm_run.stdout
    for want in ("smp_entry_gate", "smp_entry_log", "smp_late_entry"):
        if want not in syms:
            sys.exit("missing symbol " + want)
    patched = (out / "src/smp.c").read_text()
    for want in ("cpu_start_bit", "smp_init_start_layout", "cpu_start_cluster_pos", "smp_entry_log_lookup"):
        if want not in patched:  # static helpers are inlined at -O2, so check the patched source
            sys.exit("missing helper " + want)
    (out / "result.txt").write_text("PASS: patches apply, smp.c and start.S build, symbols present\n")
    print("PASS", out)


if __name__ == "__main__":
    main()
