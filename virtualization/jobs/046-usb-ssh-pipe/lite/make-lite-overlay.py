#!/usr/bin/env python3
"""The lite test's overlay cpio: /init, the RAM root's gadget script and defaults (from the working
tree), the sshd stand-in and the static Linux usb-pipe built by the VM job.
usage: make-lite-overlay.py --usb-pipe BINARY --out FILE"""
import argparse
import importlib.util
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
spec = importlib.util.spec_from_file_location("make_overlay", HERE.parent / "make-overlay.py")
mo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mo)

parser = argparse.ArgumentParser()
parser.add_argument("--usb-pipe", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()
product = REPO / "omarchy-arm64/ram-root/overlay"
files = {
    "init": (stat.S_IFREG | 0o755, (HERE / "lite-init.sh").read_bytes()),
    "usr/bin/sshd": (stat.S_IFREG | 0o755, (HERE / "sshd-shim.sh").read_bytes()),
    "usr/local/bin/usb-pipe": (stat.S_IFREG | 0o755, Path(args.usb_pipe).read_bytes()),
    "usr/local/lib/ilinux/usb-gadget.sh": (stat.S_IFREG | 0o755, (product / "usr/local/lib/ilinux/usb-gadget.sh").read_bytes()),
    "etc/default/ilinux-usb-gadget": (stat.S_IFREG | 0o644, (product / "etc/default/ilinux-usb-gadget").read_bytes()),
}
entries = [(d, stat.S_IFDIR | 0o755, b"") for d in mo.directories(files)]
entries += [(path, mode, data) for path, (mode, data) in sorted(files.items())]
Path(args.out).write_bytes(mo.newc(entries))
print("lite overlay: %d entries, %d bytes" % (len(entries), Path(args.out).stat().st_size))
