#!/bin/bash
# Boot job 046's root on the Mac under Virtualization.framework with job 041's test Image (dummy_hcd,
# usb-serial generic, the gadget stack built in): no disk, no network, one CPU. The initramfs is the
# VM-built base (run.sh) plus an overlay cpio assembled here from the working tree (make-overlay.py:
# the RAM root's overlay, the test overlay, the proxy), so the files under test can change without
# the VM. systemd runs the RAM root's USB units for real (udev -> ilinux-usb-gadget@dummy_udc.0 with
# gser.log + gser.ssh -> ilinux-sshd-tty@ttyGS1), and the self-test plays the M1 on the host side:
# usb-pipe on the generic usb-serial port of interface 1 as ssh's ProxyCommand, the CONNECT proxy, an
# HTTPS fetch through the reverse forward, 2 MiB each way, a refused key, recovery after a killed
# client. The console log goes to out/vz/selftest.log; the verdict is "[selftest] PASS".
#   run-vz.sh          build the overlay, boot and judge (about 3 min)
#   run-vz.sh check    judge the last log again without booting
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/../../.."
OUT=$HERE/out
IMAGE=$PWD/virtualization/jobs/041-usb-gadget/out/build/Image-test
VZ=$PWD/../apple-silicon-linux-research/virtualization/bin/vzrun
BASE=$OUT/build/base-initramfs.cpio.gz
ARGS='console=hvc0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=5 printk.time=1 panic=0 initcall_blacklist=clk_debug_init systemd.show_status=1'
[ -z "${STRESS:-}" ] || ARGS="$ARGS ilinux.stress=$STRESS"   # STRESS=N: N more sessions back to back with a CPU hog
LOG=$OUT/vz/selftest.log
mkdir -p "$OUT/vz"
if [ "${1:-boot}" = boot ]; then
    [ -f "$IMAGE" ] || { echo "no $IMAGE: run job 041 first (it builds the test kernel)"; exit 1; }
    [ -f "$BASE" ] || { echo "no base initramfs: run host-run.sh first (it takes the vm lock)"; exit 1; }
    python3 -I "$HERE/test_make_overlay.py" 2>&1 | tail -3
    python3 -I "$HERE/make-overlay.py" --out "$OUT/vz/overlay.cpio" | tee "$OUT/vz/overlay.txt"
    pad=$(( (4 - $(stat -f %z "$BASE") % 4) % 4 ))   # the kernel takes an uncompressed cpio at a 4-byte offset only
    { cat "$BASE"; [ "$pad" -eq 0 ] || head -c "$pad" /dev/zero; cat "$OUT/vz/overlay.cpio"; } > "$OUT/vz/initrd"   # BSD head refuses -c 0
    shasum -a 256 "$IMAGE" "$BASE" "$OUT/vz/overlay.cpio" "$OUT/vz/initrd" | tee "$OUT/vz/inputs-sha256.txt"
    caffeinate -i "$VZ" --cpus 1 --mem 4 --no-net --kernel "$IMAGE" --initrd "$OUT/vz/initrd" \
        --cmdline "$ARGS" > "$LOG" 2>&1 &
    pid=$!
    for _ in $(seq 240); do   # at most 8 min; the self-test's recovery step alone can take 80 s
        sleep 2
        if grep -q '^\[selftest\] END' "$LOG" 2>/dev/null; then break; fi
        kill -0 "$pid" 2> /dev/null || break
    done
    kill "$pid" 2> /dev/null || true
    wait "$pid" 2> /dev/null || true
    echo "boot: $(wc -l < "$LOG") console lines in $LOG"
fi
expect() {  # every pattern must appear in the log
    local missing=0
    for pattern in "$@"; do
        if grep -q -- "$pattern" "$LOG"; then echo "  found: $pattern"
        else echo "  MISSING: $pattern"; missing=1; fi
    done
    return $missing
}
reject() {  # no pattern may appear in the log
    local found=0
    for pattern in "$@"; do
        if grep -q -- "$pattern" "$LOG"; then echo "  UNEXPECTED: $pattern"; found=1
        else echo "  absent: $pattern"; fi
    done
    return $found
}
status=0
expect "M5 side: ilinux-usb-gadget@dummy_udc.0.service active; gser.log on ttyGS0 (interface 0), gser.ssh on ttyGS1 (interface 1); UDC configured" \
    "M5 side: ilinux-sshd-tty@ttyGS1.service active" "private network namespace; LoginGraceTime 45 ClientAlive 15x3" \
    "host sees 1d6b:0104 bcdDevice 0039 \"iLinux J716c control channel, port 4\", Bulk-only kernel log port + SSH byte pipe: two vendor interfaces (ff), each bulk IN + bulk OUT" \
    "no interrupt endpoint" "host side: interface 0 -> /dev/ttyUSB[0-9] (log), interface 1 -> /dev/ttyUSB[0-9] (SSH pipe), driver usbserial_generic" \
    "log port: [1-9][0-9]* journal lines over /dev/ttyUSB[0-9]" \
    "ssh 1 (.* s): SSH-OK root@ilinux-m5-test http://127.0.0.1:3128 http://127.0.0.1:3128 NO_PROXY=localhost,127.0.0.1,::1 HELLO-FROM-THE-M1-SIDE direct: " \
    "proxy: .*CONNECT web.test:8443 -> 127.0.0.1:8443 .* ok" "usb-pipe: banner after [0-9]* ms: SSH-2.0-OpenSSH" \
    "transfer: 2 MiB up in .* s and 2 MiB down in .* s, digests equal" "wrong key refused: .*Permission denied" \
    "killed a client mid-session" "recovered from the abandoned handshake on try [1-6]" "recovered from the vanished client on try [1-6]" "no failed ilinux units" "^\[selftest\] PASS" || status=1
reject "\[selftest\] FAIL" "Kernel panic" "direct: HELLO" "usb-pipe: write to the device failed" || status=1
[ $status = 0 ] && echo "run-vz.sh: PASS" || echo "run-vz.sh: FAIL (see $LOG)"
exit $status
