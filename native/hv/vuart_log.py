#!/usr/bin/env python3
"""Log the m1n1 HV virtual UART (USB CDC data interface 3) to a local file.

Start this before hv_launch.py. It never touches the primary proxy port.
With --interactive, typed lines are sent to the guest console (Linux shell);
otherwise the port is only read. Logs may contain target identifiers: keep
them under ignored build/ paths, never commit them.
"""
import argparse
from pathlib import Path
import select
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools/m1n1-client"))
import usb_identity  # noqa: E402


def is_vuart(port):
    return (port.vid, port.pid, port.number, port.interface_class) == (0x1209, 0x316D, 3, 0x0A)


def select_vuart(ports):
    found = [p for p in ports if is_vuart(p)]
    if len(found) != 1:
        raise ValueError("need exactly one m1n1 virtual UART interface")
    return found[0].path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--wait", type=float, default=600.0,
                        help="seconds to wait for the interface to appear")
    args = parser.parse_args(argv)
    import serial
    deadline = time.monotonic() + args.wait
    while True:
        try:
            path = select_vuart(usb_identity.discover())
            break
        except ValueError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)
    port = serial.Serial(path, 115200, timeout=0.1)
    print("vUART open (interface 3); Ctrl-C to stop logging.", file=sys.stderr)
    with args.log.open("ab") as log:
        try:
            while True:
                data = port.read(4096)
                if data:
                    log.write(data)
                    log.flush()
                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()
                if args.interactive and select.select([sys.stdin], [], [], 0)[0]:
                    line = sys.stdin.buffer.readline()
                    if line:
                        port.write(line.replace(b"\n", b"\r"))
        except KeyboardInterrupt:
            pass
        finally:
            port.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
