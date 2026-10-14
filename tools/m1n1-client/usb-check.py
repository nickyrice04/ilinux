"""Identify the macOS m1n1 primary interface, or send one bounded P_NOP.

No m1n1.setup import, feature negotiation, register/memory access or boot.
Opening a USB serial port can interrupt target autoboot into proxy mode.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from usb_identity import discover, select_primary


def handshake(device):
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "third_party/m1n1/proxyclient"))
    from m1n1.proxy import M1N1Proxy, UartInterface, Serial

    def deadline(*_):
        raise TimeoutError("USB handshake exceeded 10 seconds")

    old_handler = signal.signal(signal.SIGALRM, deadline)
    signal.alarm(10)
    transport = None
    try:
        # Own the serial object so it also closes if UartInterface init fails.
        transport = Serial(device, UartInterface.DEFAULT_BAUD_RATE)
        iface = UartInterface(device=transport)
        iface.tty_enable = False  # Do not print incidental target logs/identifiers.
        M1N1Proxy(iface).nop()  # P_NOP only; unlike iface.nop(), no feature change.
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        if transport is not None:
            transport.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connect", nargs="?", const="auto", metavar="PRIMARY_DEVICE",
                        help="identify exactly one primary interface and send one P_NOP")
    args = parser.parse_args(argv)
    try:
        ports = discover()
        print("USB discovery: %d primary candidate(s), %d modem interface(s); paths redacted." % (
            sum(port.primary for port in ports), len(ports)))
        device = select_primary(ports, args.connect or "auto")
    except Exception as exc:
        print("Discovery STOP: no unique verified primary available (%s); no port opened." %
              type(exc).__name__, file=sys.stderr)
        return 2
    print("Primary verified: VID:PID 1209:316d, CDC data interface 1.")
    if args.connect is None:
        print("Discovery only: no port opened, no target commands sent.")
        return 0
    print("Handshake start UTC:", datetime.now(timezone.utc).isoformat(), flush=True)
    start = time.monotonic()
    status = 0
    try:
        handshake(device)
    except Exception as exc:
        print("Handshake FAILED:", type(exc).__name__, file=sys.stderr)
        status = 1
    else:
        print("Handshake PASS: proxy P_NOP replied; no memory/register/boot requests sent.")
    finally:
        print("Handshake end UTC:", datetime.now(timezone.utc).isoformat())
        print("Handshake elapsed: %.3f seconds" % (time.monotonic() - start))
    return status


if __name__ == "__main__":
    sys.exit(main())
