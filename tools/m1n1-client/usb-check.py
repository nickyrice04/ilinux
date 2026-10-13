"""Discover USB paths, or perform one bounded proxy P_NOP handshake.

No m1n1.setup import, feature negotiation, register/memory access or boot.
Opening a USB serial port can interrupt target autoboot into proxy mode.
"""
import argparse
import glob
from pathlib import Path
import signal
import sys


def handshake(device):
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "third_party/m1n1/proxyclient"))
    from m1n1.proxy import M1N1Proxy, UartInterface

    def deadline(*_):
        raise TimeoutError("USB handshake exceeded 10 seconds")

    old_handler = signal.signal(signal.SIGALRM, deadline)
    signal.alarm(10)
    iface = None
    try:
        iface = UartInterface(device=device)
        iface.tty_enable = False  # Do not print incidental target logs/identifiers.
        M1N1Proxy(iface).nop()  # P_NOP only; unlike iface.nop(), no feature change.
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        if iface is not None:
            iface.dev.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connect", metavar="PRIMARY_DEVICE",
                        help="open this primary USB port and send one P_NOP")
    args = parser.parse_args()
    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not args.connect:
        print("USB modem paths:", ", ".join(ports) if ports else "none detected")
        print("Discovery only: no port opened, no target commands sent.")
        return 0
    if args.connect not in ports or not args.connect.endswith("P_01"):
        parser.error("choose a currently present primary /dev/cu.usbmodem*P_01 port")
    try:
        handshake(args.connect)
    except Exception as exc:
        print("Handshake FAILED:", type(exc).__name__, file=sys.stderr)
        return 1
    print("Handshake PASS: proxy P_NOP replied; no memory/register/boot requests sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
