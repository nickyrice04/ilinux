"""Identify the macOS m1n1 primary interface, or send one bounded P_NOP.

No m1n1.setup import, feature negotiation, register/memory access or boot.
Opening a USB serial port can interrupt target autoboot into proxy mode.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import plistlib
import re
import signal
import stat
import subprocess
import sys
import time
from typing import NamedTuple


class Port(NamedTuple):
    # Callout paths may contain serial numbers. Keep them in memory only.
    path: str
    vid: object
    pid: object
    number: object
    interface_class: object

    @property
    def primary(self):
        return (self.vid, self.pid, self.number, self.interface_class) == (
            0x1209, 0x316d, 1, 0x0a)


def registry_ports(roots):
    """Resolve serial children using their nearest USB device/interface parents.

    Pinned usb_dwc3.c: VID/PID 1209:316d, primary CDC data interface 1,
    secondary virtual UART data interface 3. Filename suffixes are not identity.
    No registry serial, name, location or other identifier is retained.
    """
    if not isinstance(roots, list):
        raise ValueError("Invalid USB registry")
    ports = {}

    def visit(node, device=(None, None), interface=(None, None)):
        if not isinstance(node, dict):
            raise ValueError("Invalid USB registry node")
        cls = node.get("IOObjectClass")
        if cls in ("IOUSBHostDevice", "IOUSBDevice") or "bDeviceClass" in node:
            device = (node.get("idVendor"), node.get("idProduct"))
            interface = (None, None)
        if cls in ("IOUSBHostInterface", "IOUSBInterface") or "bInterfaceNumber" in node:
            interface = (node.get("bInterfaceNumber"), node.get("bInterfaceClass"))
        if cls == "IOSerialBSDClient":
            path = node.get("IOCalloutDevice")
            if isinstance(path, str) and re.fullmatch(r"/dev/cu\.usbmodem[A-Za-z0-9_-]+", path):
                port = Port(path, *device, *interface)
                if path in ports and ports[path] != port:
                    raise ValueError("Conflicting USB interface metadata")
                ports[path] = port
        for child in node.get("IORegistryEntryChildren", []):
            visit(child, device, interface)

    for root in roots:
        visit(root)
    return list(ports.values())


def discover():
    if sys.platform != "darwin":
        raise RuntimeError("This checker requires macOS USB registry metadata")
    # Read cached IOService properties only, never open a USB/serial interface.
    # Capture privately in memory: never print or save the raw registry.
    result = subprocess.run(
        ["/usr/sbin/ioreg", "-a", "-l", "-p", "IOService", "-r", "-c", "IOUSBHostDevice"],
        capture_output=True, check=True, timeout=15)
    return registry_ports(plistlib.loads(result.stdout))


def select_primary(ports, requested="auto"):
    candidates = [port for port in ports if port.primary]
    if len(candidates) != 1:
        raise ValueError("Need exactly one m1n1 primary data interface; no port opened")
    port = candidates[0]
    if requested != "auto" and requested != port.path:
        raise ValueError("Requested path is not the verified primary; no port opened")
    # Reject stale paths, symlinks and ordinary files without opening anything.
    if not stat.S_ISCHR(Path(port.path).lstat().st_mode):
        raise ValueError("Primary callout is not a character device; no port opened")
    return port.path


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
