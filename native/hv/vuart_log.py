#!/usr/bin/env python3
"""Log the m1n1 HV virtual UART (USB CDC data interface 3) to a local file.

Start this before hv_launch.py. It never touches the primary proxy port.
Interface 3 already exists under boot021 and may disappear briefly when the
launcher chainloads hv001, so the logger reopens it whenever it returns.
With --interactive, typed lines are sent to the guest serial port.
Logs may contain target identifiers: keep them under ignored build/ paths,
never commit them.
"""
import argparse
import contextlib
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


def wait_for_vuart(wait, discover=None, sleep=time.sleep, clock=time.monotonic):
    discover = discover or usb_identity.discover
    deadline = clock() + wait
    while True:
        try:
            return select_vuart(discover())
        except ValueError:
            if clock() > deadline:
                raise
            sleep(0.5)


def pump(port, log, out, interactive=False, stdin=None):
    """Copy target output to the log and terminal until the port fails."""
    while True:
        data = port.read(4096)
        if data:
            log.write(data)
            log.flush()
            out.write(data)
            out.flush()
        if interactive and select.select([stdin], [], [], 0)[0]:
            line = stdin.buffer.readline()
            if line:
                port.write(line.replace(b"\n", b"\r"))


def serve(log, out, find_path, open_port, errors, interactive=False, stdin=None,
          sleep=time.sleep, notify=lambda msg: print(msg, file=sys.stderr)):
    """Reopen the vUART after every disconnect until interrupted."""
    while True:
        path = find_path()
        try:
            port = open_port(path)
        except errors:
            sleep(0.5)
            continue
        notify("vUART open (interface 3); Ctrl-C to stop logging.")
        try:
            pump(port, log, out, interactive, stdin)
        except errors:
            notify("vUART disconnected; waiting for it to return.")
        finally:
            with contextlib.suppress(Exception):
                port.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--wait", type=float, default=600.0,
                        help="seconds to wait each time the interface is absent")
    args = parser.parse_args(argv)
    import serial
    with args.log.open("ab") as log:
        try:
            serve(log, sys.stdout.buffer, lambda: wait_for_vuart(args.wait),
                  lambda path: serial.Serial(path, 115200, timeout=0.1),
                  (serial.SerialException, OSError), args.interactive, sys.stdin)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
