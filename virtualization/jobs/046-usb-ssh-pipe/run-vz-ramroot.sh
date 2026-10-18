#!/bin/bash
# The partial test, on this Mac with no VM and no lock: job 039's RAM root image (systemd, udev,
# OpenSSH, curl, the journal; zstd) plus job 046's overlay (the new gadget script, units, sshd drop-in,
# /etc/environment, the self-test) and a few extras (the Linux usb-pipe from a full build, an ephemeral
# test key pair), booted under Virtualization.framework with job 041's test Image (dummy_hcd,
# usb-serial generic). It runs the real systemd/udev start of the gadget, the real OpenSSH `sshd -i` on
# the raw serial port, the real ssh client with usb-pipe as its ProxyCommand, the reverse forward's
# listener, transfers, a refused key and recovery after a vanished client. The RAM root has no Python,
# so the proxy and the HTTPS fetch are left to the full test (run-vz.sh on job 046's own base root).
#   run-vz-ramroot.sh          boot and judge (about 4 minutes)
#   run-vz-ramroot.sh check    judge the last log again
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/../../.."
OUT=$HERE/out/vz
IMAGE=$PWD/virtualization/jobs/041-usb-gadget/out/build/Image-test
RAMROOT=$PWD/virtualization/jobs/039-omarchy-ram-root/out/ramroot.cpio.zst
USBPIPE=${USBPIPE:-$HERE/out/build/usb-pipe}
VZ=$PWD/../apple-silicon-linux-research/virtualization/bin/vzrun
LOG=$OUT/ramroot.log
ARGS='console=hvc0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=5 printk.time=1 panic=0 initcall_blacklist=clk_debug_init systemd.show_status=1'
[ -z "${DRAINPROBE:-}" ] || ARGS="$ARGS ilinux.drainprobe=1"
[ -z "${STRESS:-}" ] || ARGS="$ARGS ilinux.stress=$STRESS"   # STRESS=N: N more sessions back to back with a CPU hog
mkdir -p "$OUT/partial-keys"
if [ "${1:-boot}" = boot ]; then
    for f in "$IMAGE" "$RAMROOT" "$USBPIPE"; do
        [ -f "$f" ] || { echo "missing $f (job 041's test Image, job 039's RAM root, the Linux usb-pipe from a full build)"; exit 1; }
    done
    [ -f "$OUT/partial-keys/test-key" ] || ssh-keygen -q -t ed25519 -N '' -C ilinux-job046-partial-test -f "$OUT/partial-keys/test-key"
    [ -f "$OUT/partial-keys/wrong-key" ] || ssh-keygen -q -t ed25519 -N '' -C ilinux-job046-partial-wrong -f "$OUT/partial-keys/wrong-key"
    if [ ! -f "$OUT/partial-keys/cert.pem" ]; then   # a test-only TLS certificate for 127.0.0.1, for the TLS fetch through the forward
        printf '%s\n' '[req]' 'distinguished_name = dn' 'x509_extensions = v3' 'prompt = no' '[dn]' 'CN = ilinux-test-tls' \
            '[v3]' 'subjectAltName = IP:127.0.0.1' 'basicConstraints = critical, CA:TRUE' > "$OUT/partial-keys/cert.cnf"
        openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout "$OUT/partial-keys/key.pem" \
            -out "$OUT/partial-keys/cert.pem" -days 30 -config "$OUT/partial-keys/cert.cnf" > /dev/null 2>&1
    fi
    python3 -I "$HERE/test_make_overlay.py" 2>&1 | tail -3
    python3 -I "$HERE/make-overlay.py" --out "$OUT/ramroot-overlay.cpio" | tee "$OUT/ramroot-overlay.txt"
    python3 -I "$HERE/make-ramroot-overlay.py" --usb-pipe "$USBPIPE" --keys "$OUT/partial-keys" \
        --cert "$OUT/partial-keys/cert.pem" --key "$OUT/partial-keys/key.pem" --out "$OUT/ramroot-extras.cpio"
    pad=$(( (4 - $(stat -f %z "$RAMROOT") % 4) % 4 ))   # the kernel takes an uncompressed cpio at a 4-byte offset only
    { cat "$RAMROOT"; [ "$pad" -eq 0 ] || head -c "$pad" /dev/zero; cat "$OUT/ramroot-overlay.cpio" "$OUT/ramroot-extras.cpio"; } > "$OUT/ramroot-initrd"
    shasum -a 256 "$IMAGE" "$RAMROOT" "$OUT/ramroot-overlay.cpio" "$OUT/ramroot-extras.cpio" | tee "$OUT/ramroot-inputs-sha256.txt"
    caffeinate -i "$VZ" --cpus 1 --mem 4 --no-net --kernel "$IMAGE" --initrd "$OUT/ramroot-initrd" \
        --cmdline "$ARGS" > "$LOG" 2>&1 &
    pid=$!
    for _ in $(seq 300); do   # at most 10 min
        sleep 2
        if grep -a -q '^\[selftest\] END' "$LOG" 2>/dev/null; then break; fi
        kill -0 "$pid" 2> /dev/null || break
    done
    kill "$pid" 2> /dev/null || true
    wait "$pid" 2> /dev/null || true
    rm -f "$OUT/ramroot-initrd"   # 190 MB, rebuilt every time
    echo "boot: $(wc -l < "$LOG") console lines in $LOG"
fi
grep -a '^\[selftest\]' "$LOG" | cut -c1-230
expect() {  # every pattern must appear in the log
    local missing=0
    for pattern in "$@"; do
        if grep -a -q -- "$pattern" "$LOG"; then echo "  found: $pattern"
        else echo "  MISSING: $pattern"; missing=1; fi
    done
    return $missing
}
status=0
expect "mode: partial" \
    "M5 side: ilinux-usb-gadget@dummy_udc.0.service active; gser.log on ttyGS0 (interface 0), gser.ssh on ttyGS1 (interface 1); UDC configured" \
    "M5 side: ilinux-sshd-tty@ttyGS1.service active" "private network namespace; LoginGraceTime 45 ClientAlive 15x3" \
    "host sees 1d6b:0104 bcdDevice 0039 \"iLinux J716c control channel, port 4\", Bulk-only kernel log port + SSH byte pipe: two vendor interfaces (ff), each bulk IN + bulk OUT" \
    "no interrupt endpoint" "host side: interface 0 -> /dev/ttyUSB[0-9] (log), interface 1 -> /dev/ttyUSB[0-9] (SSH pipe), driver usbserial_generic" \
    "log port: [1-9][0-9]* journal lines over /dev/ttyUSB[0-9]" \
    "ssh 1 (.* s): SSH-OK root@ilinux-m5 http://127.0.0.1:3128 http://127.0.0.1:3128 NO_PROXY=localhost,127.0.0.1,::1 FORWARD-LISTENING" \
    "usb-pipe: banner after [0-9]* ms: SSH-2.0-OpenSSH" \
    "tls forward: 1 MiB fetched over TLS through the reverse forward, certificate verified, digest equal" \
    "transfer: 2 MiB up in .* s and 2 MiB down in .* s, digests equal" "wrong key refused: .*Permission denied" \
    "killed a client mid-session" "recovered from the abandoned handshake on try [1-6]" "recovered from the vanished client on try [1-6]" "no failed ilinux units" "^\[selftest\] PASS" || status=1
if grep -a -q -E '\[selftest\] FAIL|Kernel panic' "$LOG"; then echo "  UNEXPECTED: FAIL or panic"; status=1; fi
[ $status = 0 ] && echo "run-vz-ramroot.sh: PASS" || echo "run-vz-ramroot.sh: FAIL (see $LOG)"
exit $status
