#!/bin/bash
# host-run.sh [OWNER]: build job 049's stage one in the workspace Arch VM through tools/vm-job.sh under
# the "vm" lock (run.sh; a few minutes with warm package caches). First, on the Mac, out/stage2/
# ramroot.cpio.zst becomes an APFS clone (no copy) of stage two, job 045's image
# (STAGE2_SRC=... for another file), unless it is already there at the pinned size; run.sh checks its
# SHA-256 against stage two's pin (native/boot/omarchy-root-manifest.json, or the record that out/job.env's
# MANIFEST names). WAIT=1 waits for a busy lock (POLL seconds
# between tries, default 30) instead of failing. Then boot it on the Mac: run-qemu.sh (no lock).
set -eu
cd "$(dirname "$0")/../../.."
OWNER=${1:-twostage-049}
J=virtualization/jobs/049-two-stage-boot
SRC=${STAGE2_SRC:-virtualization/jobs/045-omarchy-installer-root/out/ramroot.cpio.zst}
# Stage two's pin: native/boot/omarchy-root-manifest.json, or MANIFEST=/mnt/ilinux/... in out/job.env
MANIFEST=$(sed -n 's|^MANIFEST=/mnt/ilinux/||p' "$J/out/job.env" 2> /dev/null | tail -n 1)
MANIFEST=${MANIFEST:-native/boot/omarchy-root-manifest.json}
size=$(python3 -I -c 'import json, sys; print(json.load(open(sys.argv[1]))["size"])' "$MANIFEST")
mkdir -p "$J/out/stage2"
if [ "$(stat -f %z "$J/out/stage2/ramroot.cpio.zst" 2> /dev/null)" != "$size" ]; then
    if [ "$(stat -f %z "$SRC" 2> /dev/null)" != "$size" ]; then
        # Job 045's output moves on before the pin does (a rebuild waits for its handoff to be
        # re-pinned); its earlier images are kept in out/runs/.
        echo "$SRC is not the image $MANIFEST pins ($size bytes)"
        for f in virtualization/jobs/045-omarchy-installer-root/out/runs/*/ramroot.cpio.zst; do
            if [ "$(stat -f %z "$f" 2> /dev/null)" = "$size" ]; then echo "  the pinned size: STAGE2_SRC=$f $0"; fi
        done
        exit 1
    fi
    rm -f "$J/out/stage2/ramroot.cpio.zst"
    cp -c "$SRC" "$J/out/stage2/ramroot.cpio.zst"
    echo "stage two: cloned $SRC ($size bytes)"
fi
until tools/lock.sh acquire vm "$OWNER" "job 049 two-stage boot: stage one build" 60 2> /dev/null; do
    [ "${WAIT:-0}" = 1 ] || { tools/lock.sh status; exit 1; }
    [ -n "${told:-}" ] || { echo "waiting for the vm lock: $(tools/lock.sh status)"; told=1; }
    sleep "${POLL:-30}"
done
exec caffeinate -i tools/vm-job.sh "$J" "$OWNER"
