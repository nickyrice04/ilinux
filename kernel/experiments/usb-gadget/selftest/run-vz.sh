#!/bin/bash
# Boot job 041's outputs on the Mac under Virtualization.framework: no disk, no network,
# one CPU, the launcher's fixed arguments with console=hvc0 (as for earlier liveness runs).
#   liveness   shipped Image + shipped initramfs, 95 s: PID 1, one CPU, debugfs, "no UDC",
#              dropbear started, 60-second heartbeat.
#   selftest   test Image (+ dummy_hcd and the host's generic usb-serial driver, besides
#              the earlier usbnet, cdc_ether and cdc-acm) + shipped initramfs + overlay,
#              120 s: the gser gadget bound, its descriptors (one vendor interface, two
#              bulk endpoints, no interrupt endpoint) as the host sees them, the kernel log
#              over the bulk-IN endpoint, no echo, no CDC function, the status line, SSH
#              with and without the key over loopback, "[selftest] PASS". boot040: the
#              short [usb4] line, the DART identity line without an iommu link (dummy_udc
#              has none) and no DART register read for the unknown UDC.
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

reject() {  # reject NAME PATTERN...: no pattern may appear in the log
    local name=$1 found=0; shift
    for pattern in "$@"; do
        if grep -q -- "$pattern" "$OUT/vz/$name.log"; then echo "  UNEXPECTED: $pattern"; found=1
        else echo "  absent: $pattern"; fi
    done
    return $found
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
    expect liveness "PID 1 reached" "online_cpus=1" "\[ctl\] debugfs on /sys/kernel/debug" \
        "\[ctl\] USB control channel: GSER bulk-only kernel log port" "\[ctl\] no UDC yet" \
        "\[ctl\] dropbear start 1" "^\[ctl\] no UDC[[:cntrl:]]*$" "60s elapsed; still alive" || status=1
    reject liveness "dwc3 status reader" "Attempted to kill init" "debugfs mount failed" "\[ctl\] write .* failed" \
        "^\[usb" "reading DART registers" || status=1
fi
if [ "$which" != liveness ]; then
    # dbclient prints its host-key note before the command output, so match SSH-OK alone.
    expect selftest "UDC dummy_udc.0 bound, GSER bulk-only 1d6b:0104 bcdDevice 0x0139, no interrupt endpoint" \
        "\[ctl\] debugfs on /sys/kernel/debug" "\[ctl\] dropbear start 1" \
        "host sees 1d6b:0104 bcdDevice 0139" \
        "descriptors: one vendor-specific interface (ff), two bulk endpoints" \
        "host side /dev/ttyUSB0 (driver usbserial_generic)" \
        "no CDC-ACM, ECM, EEM or NCM function on the host side" \
        "bulk log port: [1-9][0-9]* lines received over /dev/ttyUSB0" "no echo:" \
        "port4 configured log [1-9][0-9]*L [1-9][0-9]*B q[0-9]* dwc3 n/a" \
        "^\[usb4\] configured [1-9][0-9]*B q[0-9]* dwc3 n/a" \
        "^\[usb4\] dummy_udc.0 irq 0(-1) no iommu link in sysfs" \
        "^\[usb4\] dart regs not read (no confirmed DART bases for dummy_udc.0)" \
        "SSH-OK .* ilinux-j716c uid=0" "Pubkey auth succeeded for 'root'" \
        "Exit before auth .*(user 'root', 0 fails)" "login without the key refused" \
        "\[selftest\] PASS" "selftest exit=0" || status=1
    reject selftest "dwc3 status reader" "Attempted to kill init" "\[selftest\] FAIL" "\[ctl\] write .* failed" \
        "reading DART registers" "bus error" "STREAMER-STOPPED" "log streamer for port .* exited" || status=1
fi
exit $status
