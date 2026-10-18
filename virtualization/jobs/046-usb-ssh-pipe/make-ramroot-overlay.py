#!/usr/bin/env python3
"""The extras the partial test adds to the job 039 RAM root: the Linux usb-pipe, an ephemeral test key
pair (made on this Mac for this test only, never shipped) and root's authorized_keys.d entry.
usage: make-ramroot-overlay.py --usb-pipe BINARY --keys DIR --out FILE"""
import argparse
import importlib.util
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("make_overlay", HERE / "make-overlay.py")
mo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mo)

parser = argparse.ArgumentParser()
parser.add_argument("--usb-pipe", required=True)
parser.add_argument("--keys", required=True, help="directory with test-key, test-key.pub and wrong-key")
parser.add_argument("--cert", help="test TLS certificate (public)")
parser.add_argument("--key", help="its test-only private key")
parser.add_argument("--out", required=True)
args = parser.parse_args()
keys = Path(args.keys)
files = {
    "usr/local/bin/usb-pipe": (stat.S_IFREG | 0o755, Path(args.usb_pipe).read_bytes()),
    "usr/local/lib/ilinux-test/test-key": (stat.S_IFREG | 0o600, (keys / "test-key").read_bytes()),
    "usr/local/lib/ilinux-test/wrong-key": (stat.S_IFREG | 0o600, (keys / "wrong-key").read_bytes()),
    "etc/ssh/authorized_keys.d/root": (stat.S_IFREG | 0o600, (keys / "test-key.pub").read_bytes()),
}
if args.cert and args.key:
    files["usr/local/lib/ilinux-test/cert.pem"] = (stat.S_IFREG | 0o644, Path(args.cert).read_bytes())
    files["usr/local/lib/ilinux-test/key.pem"] = (stat.S_IFREG | 0o600, Path(args.key).read_bytes())
entries = [(d, stat.S_IFDIR | 0o755, b"") for d in mo.directories(files)]
entries += [(path, mode, data) for path, (mode, data) in sorted(files.items())]
Path(args.out).write_bytes(mo.newc(entries))
print("ram-root extras: %d entries, %d bytes" % (len(entries), Path(args.out).stat().st_size))
