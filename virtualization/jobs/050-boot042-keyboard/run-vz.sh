#!/bin/bash
# run-vz.sh liveness|storage|script|both: boot job 050's outputs on the Mac under Virtualization.framework (no lock,
# no network, nothing persists beyond the scratch disks under out/vz/).
#   liveness  boot042's Image with boot041's Stage-B initramfs (the package's, unchanged), one CPU, the
#             launcher's fixed arguments with console=hvc0, 95 s: what job 041's liveness run expects (PID 1,
#             one CPU, debugfs, no UDC, dropbear, the 60 s heartbeat). No keyboard or storage module exists
#             in that initramfs, so this is boot042's built-in part alone.
#   storage   the storage set's read-only test (kernel/experiments/nvme-ans3/storage-ro): boot042's Image with
#             ro_test as PID 1 and a writable virtual NVMe disk (vzrun --nvme), twice:
#               guarded  the storage set's nvme-core, which first refuses to load with ilinux_read_only=0
#                        (EPERM), then loads as built, on a copy of the test disk: every write attempt
#                        refused, "RO-TEST-RESULT PASS guarded", the copy's SHA-256 unchanged;
#               control  nvme-core's VM control build (ILINUX_RO_CONTROL, test initramfs only) with
#                        ilinux_read_only=0, on another copy: the data-path attempts write,
#                        "RO-TEST-RESULT PASS control", the copy's SHA-256 changed (so the guarded run's
#                        refusals are the guard's, not a disk that could not be written).
#   script    the storage set's load script, ilinux-storage-ro --transport pci, in a small userland (job 050's
#             storage-script initramfs) against another copy: every step passes, a second run stops at its
#             first check, the copy's SHA-256 unchanged and no UUID printed.
#   both      all three (the default).
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=$PWD/virtualization/jobs/050-boot042-keyboard/out
VZ=$PWD/../apple-silicon-linux-research/virtualization/bin/vzrun
IMAGE=$OUT/export/Image
STAGEB=$PWD/build/native-boot041/verified/initramfs-stage-b.cpio.gz
ARGS='console=hvc0 fbcon=nodefer rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 idle=nop arm64.nowfxt pd_ignore_unused clk_ignore_unused loglevel=8 ignore_loglevel printk.time=1 panic=0 earlycon=ilinuxfb initcall_debug initcall_blacklist=clk_debug_init ilinux_probe_diag=1'
mkdir -p "$OUT/vz"
(cd "$OUT/export" && shasum -a 256 -c --quiet ../export-sha256.txt) || { echo "job 050's export does not match its digests"; exit 1; }

expect() {  # expect LOG PATTERN...
    local log=$1 missing=0; shift
    for p in "$@"; do
        if grep -a -q -- "$p" "$log"; then echo "  found: $p"; else echo "  MISSING: $p"; missing=1; fi
    done
    return $missing
}
reject() {  # reject LOG PATTERN...
    local log=$1 found=0; shift
    for p in "$@"; do
        if grep -a -q -- "$p" "$log"; then echo "  UNEXPECTED: $p"; found=1; else echo "  absent: $p"; fi
    done
    return $found
}

status=0
which=${1:-both}
if [ "$which" = liveness ] || [ "$which" = both ]; then
    log=$OUT/vz/liveness.log
    caffeinate -i "$VZ" --cpus 1 --mem 4 --no-net --kernel "$IMAGE" --initrd "$STAGEB" --cmdline "$ARGS" > "$log" 2>&1 &
    pid=$!; sleep 95; kill "$pid" 2> /dev/null || true; wait "$pid" 2> /dev/null || true
    echo "liveness: $(wc -l < "$log") console lines in $log"
    # initcall_debug names every built-in driver's init, from about 0.04 s on (the console's replay starts
    # there): the DART stays built in; the storage drivers and dockchannel-hid, whose inits boot041's own
    # log shows at 0.043-0.071 s, must not run at boot at all (job 050's symbol check covers the rest).
    expect "$log" "Linux version .*(ilinux@boot042)" "PID 1 reached" "online_cpus=1" "\[ctl\] debugfs on /sys/kernel/debug" \
        "\[ctl\] no UDC yet" "\[ctl\] dropbear start 1" "60s elapsed; still alive" \
        "calling  apple_dart_driver_init" || status=1
    reject "$log" "Attempted to kill init" "Kernel panic" "Oops" "Call trace" "debugfs mount failed" \
        "calling  nvme_core_init" "calling  apple_nvme" "calling  apple_sart" "calling  dockchannel" \
        "calling  apple_rtkit_helper" "calling  dockchannel_hid" "calling  apple_driver_init" || status=1
fi
if [ "$which" = storage ] || [ "$which" = both ]; then
    S=$OUT/export/storage-set
    for mode in guarded control; do
        disk=$OUT/vz/disk-$mode.img root=$OUT/vz/root-$mode.img log=$OUT/vz/storage-$mode.log
        cp "$S/test-disk.img" "$disk"
        rm -f "$root"; mkfile -n 1m "$root"
        before=$(shasum -a 256 "$disk" | cut -d' ' -f1)
        caffeinate -i "$VZ" --cpus 2 --mem 2 --no-net --kernel "$IMAGE" --initrd "$S/ro-test-initramfs.cpio.gz" \
            --cmdline "console=hvc0 rdinit=/init loglevel=6 ilinux.rotest=$mode" --disk "$root" --disk "$disk" --nvme \
            > "$log" 2>&1 &
        pid=$!
        for _ in $(seq 240); do kill -0 "$pid" 2> /dev/null || break; grep -a -q 'RO-TEST-RESULT' "$log" && break; sleep 1; done
        for _ in $(seq 20); do kill -0 "$pid" 2> /dev/null || break; sleep 1; done
        kill "$pid" 2> /dev/null || true; wait "$pid" 2> /dev/null || true
        after=$(shasum -a 256 "$disk" | cut -d' ' -f1)
        echo "storage $mode: $(grep -a -c '^RO-TEST ' "$log") checks; disk $before -> $after"
        grep -a -E '^RO-TEST(-RESULT)? ' "$log" | sed 's/^/  /'
        expect "$log" "RO-TEST-RESULT PASS $mode" || status=1
        if [ "$mode" = guarded ]; then
            [ "$before" = "$after" ] && echo "  disk unchanged: PASS" || { echo "  disk CHANGED: FAIL"; status=1; }
            expect "$log" "iLinux read-only mode cannot be turned off" "iLinux read-only mode:" "iLinux read-only: refused" ||
                status=1
        else
            [ "$before" != "$after" ] && echo "  disk changed (the attempts reach it without the guard): PASS" ||
                { echo "  control disk unchanged: FAIL (the test would not see a write)"; status=1; }
        fi
        rm -f "$root"
    done
fi
if [ "$which" = script ] || [ "$which" = both ]; then
    # the storage set's load script (ilinux-storage-ro --transport pci) in a small userland, against a copy of
    # the test disk: the first run passes every step, the second stops at its first check (nvme-core is
    # loaded already), and the disk does not change
    S=$OUT/export/storage-set
    disk=$OUT/vz/disk-script.img root=$OUT/vz/root-script.img log=$OUT/vz/storage-script.log
    cp "$S/test-disk.img" "$disk"
    rm -f "$root"; mkfile -n 1m "$root"
    before=$(shasum -a 256 "$disk" | cut -d' ' -f1)
    caffeinate -i "$VZ" --cpus 2 --mem 2 --no-net --kernel "$IMAGE" --initrd "$S/storage-script-initramfs.cpio.gz" \
        --cmdline "console=hvc0 rdinit=/init loglevel=6" --disk "$root" --disk "$disk" --nvme > "$log" 2>&1 &
    pid=$!
    for _ in $(seq 240); do kill -0 "$pid" 2> /dev/null || break; grep -a -q 'STORAGE-SCRIPT-TEST second run exit' "$log" && break; sleep 1; done
    for _ in $(seq 20); do kill -0 "$pid" 2> /dev/null || break; sleep 1; done
    kill "$pid" 2> /dev/null || true; wait "$pid" 2> /dev/null || true
    after=$(shasum -a 256 "$disk" | cut -d' ' -f1)
    echo "storage script: disk $before -> $after"
    sed -n '/STORAGE-SCRIPT-TEST start/,/STORAGE-SCRIPT-TEST second run exit/p' "$log" | grep -a -v '^\[' | sed 's/^/  /'
    expect "$log" "RESULT: PASS: the internal SSD is up read-only (pci transport)" "STORAGE-SCRIPT-TEST first run exit 0" \
        "RESULT: FAIL at step 0: nvme-core is loaded already" "STORAGE-SCRIPT-TEST second run exit 1" || status=1
    reject "$log" "Kernel panic" "Oops" "Call trace" "uuid=" || status=1
    [ "$before" = "$after" ] && echo "  disk unchanged: PASS" || { echo "  disk CHANGED: FAIL"; status=1; }
    rm -f "$root"
fi
[ "$status" = 0 ] && echo "run-vz.sh $which: PASS" || echo "run-vz.sh $which: FAIL"
exit $status
