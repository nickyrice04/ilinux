#!/bin/bash
# Boot job 041's outputs on the Mac under Virtualization.framework: no disk, no network,
# one CPU, the launcher's fixed arguments with console=hvc0 (as for earlier liveness runs).
#   liveness   shipped Image + shipped initramfs, 95 s: PID 1, one CPU, "no UDC",
#              dropbear started, 60-second heartbeat.
#   selftest   test Image (+ dummy_hcd, usbnet, cdc_eem) + shipped initramfs + overlay,
#              120 s: gadget bound, EEM host interface, ping, SSH with and without the
#              key, 8 MiB copy, "[selftest] PASS".
# Logs go to the job's out/vz/. The VM is killed at the end; nothing persists.
set -euo pipefail
cd "$(dirname "$0")/../../../.."
OUT=$PWD/virtualization/jobs/041-usb-gadget/out
VZ=$PWD/../apple-silicon-linux-research/virtualization/bin/vzrun
ARGS='console=hvc0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init ilinux_probe_diag=1'
mkdir -p "$OUT/vz"

boot() {  # boot NAME IMAGE INITRD SECONDS
    local log=$OUT/vz/$1.log
    caffeinate -i "$VZ" --cpus 1 --mem 4 --no-net --kernel "$2" --initrd "$3" --cmdline "$ARGS" \
        > "$log" 2>&1 &
    local pid=$!
    sleep "$4"
    kill "$pid" 2> /dev/null || true
    wait "$pid" 2> /dev/null || true
    echo "$1: $(wc -l < "$log") console lines in $log"
}

expect() {  # expect NAME PATTERN...: every pattern must appear in the log
    local name=$1 missing=0; shift
    for pattern in "$@"; do
        if grep -q -- "$pattern" "$OUT/vz/$name.log"; then echo "  found: $pattern"
        else echo "  MISSING: $pattern"; missing=1; fi
    done
    return $missing
}

which="${1:-both}"   # liveness | selftest | both | check (re-read the last logs, no boot)
status=0
if [ "$which" = liveness ] || [ "$which" = both ]; then
    boot liveness "$OUT/export/Image" "$OUT/export/initramfs-stage-b.cpio.gz" 95
fi
if [ "$which" = selftest ] || [ "$which" = both ]; then
    cat "$OUT/export/initramfs-stage-b.cpio.gz" "$OUT/build/selftest-overlay.cpio.gz" > "$OUT/vz/selftest-initrd.cpio.gz"
    boot selftest "$OUT/build/Image-test" "$OUT/vz/selftest-initrd.cpio.gz" 120
fi
if [ "$which" != selftest ]; then
    expect liveness "PID 1 reached" "online_cpus=1" "\[ctl\] USB control channel" \
        "\[ctl\] no UDC yet" "\[ctl\] dropbear start 1" "60s elapsed; still alive" || status=1
fi
if [ "$which" != liveness ]; then
    # dbclient prints its host-key note before the command output, so match SSH-OK alone.
    expect selftest "UDC dummy_udc.0 bound, EEM 1d6b:0104" "\[ctl\] dropbear start 1" \
        "SSH-OK .* ilinux-j716c uid=0" "Pubkey auth succeeded for 'root'" \
        "Exit before auth .*(user 'root', 0 fails)" "login without the key refused" \
        "8 MiB through ssh intact" "\[selftest\] PASS" "selftest exit=0" || status=1
fi
exit $status
