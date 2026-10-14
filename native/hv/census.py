#!/usr/bin/env python3
"""H1 v2: read-only register census on the installed boot021 proxy (private).

Reads each register the hv002 start, exception and FIQ paths touch (rules in
hv_regs.py), through ProxyUtils.mrs under m1n1's exception guard. No register
writes, no chainload, no hypervisor start (ProxyUtils still sets up its RAM
heap, as in launch.py). Prints a sanitized table: register, readable or
trapped, value class only. m1n1's own console text is not echoed.
"""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hv_launch  # noqa: E402
from hv_regs import REGS, INFORMATIONAL, census, verdict  # noqa: E402,F401

CONFIRM = "CENSUS-J716C-READ-ONLY"


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
    for name, access, cls in rows:
        note = " (informational)" if name in INFORMATIONAL else ""
        print("| %s | %s | %s%s |" % (name, access, cls, note))
    blockers = verdict(rows)
    print("VERDICT:", "PASS for hv002" if not blockers else "BLOCKED: " + "; ".join(blockers))
    return 0 if not blockers else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("STOP:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
