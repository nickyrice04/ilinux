#!/usr/bin/env python3
"""Build the boot036 Stage-B DT from boot035's and check it against the contract.

usage: python3 -I make_stage_b_dt.py DTC BOOT035_STAGE_B_DTB OUT_DTB [OUT_DTS]

Decompiles the boot035 DT with dtc, appends native/boot/usb_dt.amendment(),
recompiles (ePAPR phandles only) and fails unless usb_dt.check_delta and the
launcher's fdt.check_stage_b both pass. Runs the same on the Mac (workspace
dtc) and in the VM (job 041).
"""
import hashlib
from pathlib import Path
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "native/boot"))
from fdt import check_stage_b, properties  # noqa: E402
import usb_dt  # noqa: E402

BOOT035_DTB = "b1105bbf2c207c8c816c4b9cc0231ecc1d49543e05fe4b772bcb153019e186db"


def header(blob):
    fields = struct.unpack_from(">10I", blob)   # magic .. size_dt_struct
    rsvmap = blob[fields[4]:]
    entries = 0
    while struct.unpack_from(">QQ", rsvmap, 16 * entries) != (0, 0):
        entries += 1
    return {"version": fields[5], "last_comp_version": fields[6],
            "boot_cpuid_phys": fields[7], "memreserve_entries": entries}


def main(argv):
    if len(argv) not in (4, 5):
        raise SystemExit(__doc__)
    dtc, source, out = argv[1], Path(argv[2]), Path(argv[3])
    blob = source.read_bytes()
    if hashlib.sha256(blob).hexdigest() != BOOT035_DTB:
        raise SystemExit("input is not the boot035 Stage-B DT")
    before = properties(blob)
    dts = subprocess.run([dtc, "-q", "-I", "dtb", "-O", "dts", str(source)],
                         check=True, capture_output=True, text=True).stdout
    dts += usb_dt.amendment(before)
    if len(argv) == 5:
        Path(argv[4]).write_text(dts)
    built = subprocess.run([dtc, "-q", "-H", "epapr", "-I", "dts", "-O", "dtb", "-o", str(out), "-"],
                           input=dts, capture_output=True, text=True)
    if built.returncode:
        raise SystemExit("dtc failed:\n" + built.stderr)
    after_blob = out.read_bytes()
    usb_dt.check_delta(before, properties(after_blob))
    check_stage_b(after_blob)
    if header(after_blob) != header(blob):
        raise SystemExit("FDT header fields changed: %s -> %s" % (header(blob), header(after_blob)))
    print("PASS: boot036 Stage-B DT = boot035 + USB contract; %d bytes; SHA-256 %s"
          % (len(after_blob), hashlib.sha256(after_blob).hexdigest()))


if __name__ == "__main__":
    main(sys.argv)
