#!/usr/bin/env python3
"""H1: read-only register census on the installed boot021 proxy (private).

Reads each register the hv001 start path touches, through ProxyUtils.mrs
under m1n1's exception guard. No register writes, no chainload, no
hypervisor start (ProxyUtils still sets up its RAM heap, as in launch.py).
Prints a sanitized table: register, readable or trapped, value class only.
m1n1's own console text is not echoed.
"""
import argparse
from pathlib import Path
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hv_launch  # noqa: E402

CONFIRM = "CENSUS-J716C-READ-ONLY"
# (name, encoding, classifier); classifiers reveal only what the gates need.
# hv_start() (C) reads AMX/APVMKEY/APSTS, ACTLR_EL2, ACTLR_EL12 (arch: t6050
# has actlr_el2), CNTHCTL, SPRR/GXF config without an exception guard.
REGS = (
    ("ID_AA64MMFR0_EL1", (3, 0, 0, 7, 0), lambda v: "ECV=%d" % (v >> 60)),
    ("VM_TMR_FIQ_ENA_EL2", (3, 5, 15, 1, 3), lambda v: "ENA_V=%d ENA_P=%d" % (v & 1, v >> 1 & 1)),
    ("HACR_EL2", (3, 4, 1, 1, 7), None),
    ("AMX_CTL_EL2", (3, 4, 15, 4, 7), None),
    ("APVMKEYLO_EL2", (3, 6, 15, 14, 4), None),
    ("APVMKEYHI_EL2", (3, 6, 15, 14, 5), None),
    ("APSTS_EL12", (3, 6, 15, 14, 7), None),
    ("ACTLR_EL2", (3, 4, 1, 0, 1), None),
    ("ACTLR_EL12", (3, 5, 1, 0, 1), None),
    ("IMP_APL_ACTLR_EL12", (3, 6, 15, 14, 6), None),
    ("SPRR_CONFIG_EL1", (3, 6, 15, 1, 0), None),
    ("GXF_CONFIG_EL1", (3, 6, 15, 1, 2), None),
    ("CNTHCTL_EL2", (3, 4, 14, 1, 0), None),
    ("CNTV_CTL_EL02", (3, 5, 14, 3, 1), lambda v: "ctl=%d" % (v & 7)),
    ("CNTP_CTL_EL02", (3, 5, 14, 2, 1), lambda v: "ctl=%d" % (v & 7)),
)


def classify(value, fn):
    if fn:
        return fn(value)
    return "zero" if value == 0 else "nonzero"


def census(utils, errors):
    rows = []
    for name, enc, fn in REGS:
        try:
            rows.append((name, "readable", classify(utils.mrs(enc), fn)))
        except errors as exc:
            rows.append((name, "trapped", type(exc).__name__))
    return rows


# Read for the record only: on t6050 (actlr_el2 = true, MIDR part >= 0x30)
# neither m1n1 nor the Python HV touches the pre-spec Apple ACTLR_EL12.
INFORMATIONAL = {"IMP_APL_ACTLR_EL12"}


def verdict(rows):
    get = {n: (s, c) for n, s, c in rows}
    blockers = [n for n, s, _ in rows if s != "readable" and n not in INFORMATIONAL]
    if get["VM_TMR_FIQ_ENA_EL2"] != ("readable", "ENA_V=0 ENA_P=0"):
        blockers.append("VM_TMR_FIQ_ENA_EL2 not readable as disabled (hv001 refuses)")
    return blockers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--m1n1", type=Path, default=HERE.parents[1] / "third_party/m1n1")
    args = parser.parse_args(argv)
    if args.confirm != CONFIRM:
        parser.error("requires --confirm " + CONFIRM)
    pin = subprocess.check_output(["git", "-C", str(args.m1n1), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(args.m1n1), "status", "--porcelain",
                                     "--untracked-files=no"], text=True)
    if pin != hv_launch.launch.M1N1_COMMIT or dirty:
        raise ValueError("client must be the clean pinned m1n1 checkout")
    sys.path.insert(0, str(args.m1n1 / "proxyclient"))
    from m1n1.proxy import M1N1Proxy, ProxyError
    from m1n1.proxyutils import ProxyUtils
    import json

    def timeout(*_):
        raise TimeoutError("census exceeded 120 seconds; power off")

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(120)
    transport, iface = hv_launch.open_primary(args.device)
    iface.tty_enable = False  # discard raw target console text, as launch.py does
    try:
        proxy = M1N1Proxy(iface)
        boot_m = json.loads((hv_launch.BOOT / "package-manifest.json").read_text())
        hv_launch.check_target(iface, proxy, proxy.get_base(), boot_m["m1n1_version_marker"],
                               boot_m["m1n1_version_offset"])
        rows = census(ProxyUtils(proxy), (ProxyError,))
    finally:
        signal.alarm(0)
        transport.close()
    print("| Register | Access | Class |\n|---|---|---|")
    for row in rows:
        print("| %s | %s | %s |" % row)
    blockers = verdict(rows)
    print("VERDICT:", "PASS for hv001" if not blockers else "BLOCKED: " + "; ".join(blockers))
    return 0 if not blockers else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("STOP:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
