#!/usr/bin/env python3
"""boot040: two patches on drivers/iommu/apple-dart.c.

1. dart-diag.patch: the t8110 fault handler reports an interrupt it does not recognise
   (raw ERROR, ERROR_MASK, ERROR_STREAMS, ERROR_ADDR, TLB_CMD; rate-limited by count),
   acknowledges what is pending and names each DART instance at probe.
2. dart-diag-2-gen22.patch: for a DART whose PARAMS3 reports version 2.2 or later, the
   fault state is read, reported and acknowledged in that version's layout (pending
   bitmap 0x4000, per-stream error blocks 0x8000 + 0x40*SID, mask 0x4060, protection
   status 0x704/0x4204, flush-unlock when 0x210 bit 1 asks), with a bound of 256
   acknowledged interrupts per instance; inert on a DART below 2.2
   (rea-dart-2026-10-18.md).

Apply to a Linux tree: apply.py <tree>. Digest-gated on drivers/iommu/apple-dart.c:
the file must be the asahi@77cb8f24 one (BEFORE), the part-1 one (MID) or the final one
(AFTER); each missing patch is applied in order. Private iLinux experiment; not an
upstream submission.
"""
import hashlib
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TARGET = "drivers/iommu/apple-dart.c"
BEFORE = "f48a05cf9ae17cc1871211cfd7a634f75d3bcdc131c0d7e896a8c8a80451a845"
MID = "1ed5acf9588650cf9fb7dbba950433c60bbf30d8d0aa3c54f6a4345484db6f29"
AFTER = "b3eb0da83235164e2d514c106ec134d6e24c335ba6e36e0124534fb60ca9b288"
PATCHES = (("dart-diag.patch", BEFORE, MID), ("dart-diag-2-gen22.patch", MID, AFTER))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__)
    tree = Path(argv[1])
    target = tree / TARGET
    if digest(target) == AFTER:
        print("apple-dart.c already carries both boot040 patches")
        return
    if digest(target) not in (BEFORE, MID):
        raise SystemExit("%s is neither the asahi@77cb8f24 file nor the part-1 one (sha256 %s)"
                         % (target, digest(target)))
    for name, before, after in PATCHES:
        if digest(target) != before:
            continue
        run = subprocess.run(["patch", "-p1", "--forward", "--no-backup-if-mismatch", "-i",
                              str(HERE / name)], cwd=tree, capture_output=True, text=True)
        if run.returncode:
            raise SystemExit("%s failed:\n%s%s" % (name, run.stdout, run.stderr))
        if digest(target) != after:
            raise SystemExit("%s left apple-dart.c with an unexpected digest %s" % (name, digest(target)))
        print("apple-dart.c: %s applied (sha256 %s)" % (name, after))


if __name__ == "__main__":
    main(sys.argv)
