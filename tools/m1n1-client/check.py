"""Offline imports and device-path discovery; never opens a serial device."""
import glob
import importlib
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "third_party/m1n1/proxyclient"))
for module in ("serial", "construct", "readline", "m1n1.proxy",
               "m1n1.proxyutils", "m1n1.shell", "m1n1.hv"):
    importlib.import_module(module)
print("Offline client imports: PASS")
ports = sorted(glob.glob("/dev/cu.usbmodem*"))
print("USB modem paths:", ", ".join(ports) if ports else "none detected")
print("No serial device opened; no target communication attempted.")
