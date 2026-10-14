"""Read-only macOS USB identity shared by Stage A and the native launcher.

No serial imports, device opens or target requests. Registry data stays in memory.
"""
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import sys
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
