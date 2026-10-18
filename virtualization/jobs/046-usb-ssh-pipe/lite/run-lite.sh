#!/bin/bash
# The lite test: no VM job, no vm lock. Boots job 041's test Image under Virtualization.framework with
# job 041's busybox/dropbear Stage-B initramfs, its dbclient overlay and a small overlay of ours
# (make-lite-overlay.py): the RAM root's real usb-gadget.sh, the static Linux usb-pipe that job 046's
# first VM run built, and dropbear in place of sshd. See lite-init.sh for what runs.
#   run-lite.sh          boot and judge (about 1 minute)
#   run-lite.sh check    judge the last log again
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/../../../.."
B41=virtualization/jobs/041-usb-gadget/out
OUT=$HERE/../out/vz
USBPIPE=${USBPIPE:-$HERE/../out/build/usb-pipe}
VZ=$PWD/../apple-silicon-linux-research/virtualization/bin/vzrun
LOG=$OUT/lite.log
ARGS='console=hvc0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=5 printk.time=1 panic=0 initcall_blacklist=clk_debug_init'
[ -z "${KILL_NOW:-}" ] || ARGS="$ARGS lite.kill=now"   # KILL_NOW=1: the harshest case for the M5's input drain
mkdir -p "$OUT"
if [ "${1:-boot}" = boot ]; then
    for f in "$B41/export/initramfs-stage-b.cpio.gz" "$B41/build/selftest-overlay.cpio.gz" "$B41/build/Image-test" "$USBPIPE"; do
        [ -f "$f" ] || { echo "missing $f (job 041's outputs, and the Linux usb-pipe from job 046's VM run)"; exit 1; }
    done
    python3 -I "$HERE/make-lite-overlay.py" --usb-pipe "$USBPIPE" --out "$OUT/lite-overlay.cpio"
    { cat "$B41/export/initramfs-stage-b.cpio.gz" "$B41/build/selftest-overlay.cpio.gz"; } > "$OUT/lite-base.cpio.gz"
    pad=$(( (4 - $(stat -f %z "$OUT/lite-base.cpio.gz") % 4) % 4 ))
    { cat "$OUT/lite-base.cpio.gz"; [ "$pad" -eq 0 ] || head -c "$pad" /dev/zero; cat "$OUT/lite-overlay.cpio"; } > "$OUT/lite-initrd"   # BSD head refuses -c 0
    caffeinate -i "$VZ" --cpus 1 --mem 2 --no-net --kernel "$B41/build/Image-test" --initrd "$OUT/lite-initrd" \
        --cmdline "$ARGS" > "$LOG" 2>&1 &
    pid=$!
    for _ in $(seq 120); do   # at most 4 min
        sleep 2
        if grep -q '^\[lite\] END' "$LOG" 2>/dev/null; then break; fi
        kill -0 "$pid" 2> /dev/null || break
    done
    kill "$pid" 2> /dev/null || true
    wait "$pid" 2> /dev/null || true
    echo "boot: $(wc -l < "$LOG") console lines in $LOG"
fi
grep -a '^\[lite\]' "$LOG" | cut -c1-200
status=0
for pattern in "M5 side: gadget bound to dummy_udc.0, UDC configured, gser.log on ttyGS0, gser.ssh on ttyGS1" \
        "host sees 1d6b:0104 bcdDevice 0039" "session 1 (.* s): SSH-OK uid=0" "usb-pipe: banner after" \
        "sessions 2 to 7 in a row: ok" "transfer: 2 MiB up in .* s and 2 MiB down in .* s, digests equal" \
        "session after the refused login: STILL-FINE" "^\[lite\] PASS"; do
    if grep -a -q -- "$pattern" "$LOG"; then echo "  found: $pattern"; else echo "  MISSING: $pattern"; status=1; fi
done
grep -a -q '\[lite\] FAIL' "$LOG" && { echo "  UNEXPECTED: [lite] FAIL"; status=1; }
[ $status = 0 ] && echo "run-lite.sh: PASS" || echo "run-lite.sh: FAIL (see $LOG)"
exit $status
