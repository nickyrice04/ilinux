#!/usr/bin/env python3
"""Build the boot036 Stage-B DT from boot035's, or boot041's from boot036's, and check it.

usage: python3 -I make_stage_b_dt.py [--both-darts] DTC INPUT_DTB OUT_DTB [OUT_DTS]

Default (boot036): INPUT is the boot035 Stage-B DT; decompiles it with dtc, appends
native/boot/usb_dt.amendment(), recompiles (ePAPR phandles only) and fails unless
usb_dt.check_delta and the launcher's fdt.check_stage_b both pass.
--both-darts (boot041): INPUT is the boot036 Stage-B DT (boot036-040 ship it); appends
usb_dt.both_darts_amendment() instead (each dwc3 core gets both DART instances of its
port, as Asahi wires them) and fails unless usb_dt.check_both_darts_delta and
check_stage_b pass. Runs the same on the Mac (workspace dtc) and in the VM (job 041).
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
BOOT036_DTB = "a676087bda3cffa178604ca0cf128558d9ab2a620073314d054c79a685ecefa5"   # = boot037-040's


def header(blob):
    fields = struct.unpack_from(">10I", blob)   # magic .. size_dt_struct
    rsvmap = blob[fields[4]:]
    entries = 0
    while struct.unpack_from(">QQ", rsvmap, 16 * entries) != (0, 0):
        entries += 1
    return {"version": fields[5], "last_comp_version": fields[6],
            "boot_cpuid_phys": fields[7], "memreserve_entries": entries}


def main(argv):
    both = len(argv) > 1 and argv[1] == "--both-darts"
    if both:
        argv = argv[:1] + argv[2:]
    if len(argv) not in (4, 5):
        raise SystemExit(__doc__)
    dtc, source, out = argv[1], Path(argv[2]), Path(argv[3])
    blob = source.read_bytes()
    if hashlib.sha256(blob).hexdigest() != (BOOT036_DTB if both else BOOT035_DTB):
        raise SystemExit("input is not the %s Stage-B DT" % ("boot036" if both else "boot035"))
    before = properties(blob)
    dts = subprocess.run([dtc, "-q", "-I", "dtb", "-O", "dts", str(source)],
                         check=True, capture_output=True, text=True).stdout
    dts += usb_dt.both_darts_amendment(before) if both else usb_dt.amendment(before)
    if len(argv) == 5:
        Path(argv[4]).write_text(dts)
    built = subprocess.run([dtc, "-q", "-H", "epapr", "-I", "dts", "-O", "dtb", "-o", str(out), "-"],
                           input=dts, capture_output=True, text=True)
    if built.returncode:
        raise SystemExit("dtc failed:\n" + built.stderr)
    after_blob = out.read_bytes()
    if both:
        usb_dt.check_both_darts_delta(before, properties(after_blob))
    else:
        usb_dt.check_delta(before, properties(after_blob))
    check_stage_b(after_blob)
    if header(after_blob) != header(blob):
        raise SystemExit("FDT header fields changed: %s -> %s" % (header(blob), header(after_blob)))
    print("PASS: %s; %d bytes; SHA-256 %s"
          % ("boot041 Stage-B DT = boot036 + both DART instances per dwc3" if both
             else "boot036 Stage-B DT = boot035 + USB contract",
             len(after_blob), hashlib.sha256(after_blob).hexdigest()))


if __name__ == "__main__":
    main(sys.argv)
