#!/bin/bash
# launcher-check.sh RECORD PACKAGE STAGE1: the committed launcher, offline, with a stage-one pin record that
# is not native/boot/ramroot-manifest.json yet (one in build/ that waits for its handoff). native/boot/ and
# tools/m1n1-client/usb_identity.py are copied byte for byte into a scratch directory, the record replaces
# the copy's ramroot-manifest.json, and that copy runs --profile ramroot with no USB opened; the
# repository's files are never written. The launcher's digest is printed for both, and they must be equal.
#   launcher-check.sh build/two-stage/records/ramroot-manifest.json build/native-boot042/verified \
#       virtualization/jobs/049-two-stage-boot/out/stage1.cpio.zst
set -euo pipefail
[ $# = 3 ] || { echo "usage: $0 RECORD PACKAGE STAGE1" >&2; exit 2; }
RECORD=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
PACKAGE=$(cd "$2" && pwd)
STAGE1=$(cd "$(dirname "$3")" && pwd)/$(basename "$3")
cd "$(dirname "$0")/../../.."
T=$(mktemp -d "${TMPDIR:-/tmp}/ilinux049-launcher.XXXXXX")
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/native/boot" "$T/tools/m1n1-client"
mkdir -p "$T/kernel/experiments/usb-gadget-dt"
cp kernel/experiments/usb-gadget-dt/fdtedit.py "$T/kernel/experiments/usb-gadget-dt/"
cp native/boot/*.py native/boot/*.json "$T/native/boot/"
cp tools/m1n1-client/usb_identity.py "$T/tools/m1n1-client/"
cp "$RECORD" "$T/native/boot/ramroot-manifest.json"
a=$(shasum -a 256 < native/boot/launch.py | cut -d' ' -f1)
b=$(shasum -a 256 < "$T/native/boot/launch.py" | cut -d' ' -f1)
echo "launch.py: repository $a, scratch copy $b"
[ "$a" = "$b" ] || { echo "the scratch launcher differs"; exit 1; }
python3 -I "$T/native/boot/launch.py" --package "$PACKAGE" --profile ramroot --ramroot "$STAGE1"
