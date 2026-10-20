#!/bin/bash
# Job 049's boot test, on this Mac with no VM lock: QEMU (the workspace build) with Apple's
# Hypervisor.framework, one vCPU, boots stage one exactly as built (out/stage1.cpio.zst) on job 041's
# test Image (boot041's Image with the host-side test drivers built in: dummy_hcd, usb-serial generic),
# the way m1n1 boots the M5: direct kernel entry, the launcher's RAM-root arguments plus m1n1's append,
# a device tree with the M5's root compatible and a /chosen simple-framebuffer (3456x2234 x2r10g10b10)
# that simpledrm drives. dummy_hcd makes the kernel the host of its own gadget (job 046's approach), so
# the M1's part runs in the same boot: the test overlay's m1-stage1.sh plays the M1 with the M1's own
# files from the working tree (m5-stage2.py, m5-ssh-config, the manifest) and stage two on a read-only
# virtio disk. It makes three attempts stage one must refuse and survive, then the real transfer; stage
# one verifies, unpacks and soft-reboots into stage two; the test hook's probe follows Omarchy to the
# desktop and checks stage two's own link. The harness captures the panel when asked, reads the markers
# from the virtio console and judges. What it expects of stage two (size, SHA-256, entry count, build-info)
# comes from the build: stage one's pin (out/stage2-pin.txt) and stage two's build-info as run.sh unpacked
# it (out/build/stage2-unpacked.txt); a boot keeps copies in out/vm/, which "check" reads.
#   run-qemu.sh          assemble, boot, judge (about 10 to 20 minutes)
#   run-qemu.sh check    judge the last run again
# Environment: MEM (default 32G), ACCEL (default hvf,kernel-irqchip=on), TIMEOUT seconds (default 3600),
# KERNEL_TEST (another test Image), NEGATIVES=0 (the timing run: no refusal tests, the real image is
# sent as soon as the link is up; the kernel gets ilinux049.negatives=0, which only the test reads),
# FAILED_UNITS (stage two's failed units after the switch; default: those job 045's VM test of the
# pinned image found).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/../../.."
OUT=${JOB_OUT:-$HERE/out}
V=$OUT/vm
QEMU=${QEMU:-$PWD/../apple-silicon-linux-research/virtualization/qemu/runtime/bin/qemu-system-aarch64}
IMAGE=${KERNEL_TEST:-$PWD/virtualization/jobs/041-usb-gadget/out/build/Image-test}
STAGE1=$OUT/stage1.cpio.zst
TESTBASE=$OUT/build/test-base.cpio.zst
STAGE2=$OUT/stage2/ramroot.cpio.zst
FB2PNG=$PWD/virtualization/jobs/039-omarchy-ram-root/fb2png.py
FB_ADDR=0x220000000 FB_W=3456 FB_H=2234
FB_STRIDE=$((FB_W * 4))
FB_SIZE=$((FB_STRIDE * FB_H))
# The launcher's RAM-root arguments, then what the pinned m1n1 appends on M4 and later; the VM adds
# console=hvc0 for the markers (job 045's boot test does the same).
CMDLINE="console=tty0 console=hvc0 rdinit=/init ro maxcpus=1 nr_cpus=1 cpufreq.off=1 pd_ignore_unused clk_ignore_unused quiet idle=nop arm64.nowfxt"
# An explicit CPU-observation test uses the actual experiment governor argument.
# This VM has no Apple DVFS controller; its MMIO behavior remains untested.
if [ "${CPU_OBSERVE_TEST:-0}" = 1 ]; then
    CMDLINE=${CMDLINE/cpufreq.off=1/cpufreq.default_governor=userspace}
fi
NEGATIVES=${NEGATIVES:-1}
[ "$NEGATIVES" = 1 ] || CMDLINE="$CMDLINE ilinux049.negatives=0"
MEM=${MEM:-32G}
ACCEL=${ACCEL:-hvf,kernel-irqchip=on}
TIMEOUT=${TIMEOUT:-3600}
# Stage two's pin, as the build had it: native/boot/omarchy-root-manifest.json, or out/job.env's MANIFEST
MANIFEST=$(sed -n 's|^MANIFEST=/mnt/ilinux/||p' "$OUT/job.env" 2> /dev/null | tail -n 1)
MANIFEST=${MANIFEST:-native/boot/omarchy-root-manifest.json}
LOG=$V/console.log
SOCK=$V/q.sock   # AF_UNIX paths are limited to 104 bytes
mkdir -p "$V"

if [ "${1:-boot}" = boot ]; then
    for f in "$QEMU" "$IMAGE" "$STAGE1" "$TESTBASE" "$STAGE2" "$FB2PNG"; do
        [ -e "$f" ] || { echo "missing $f (host-run.sh builds stage one and the test base; job 041 the test Image)"; exit 1; }
    done
    (cd "$OUT" && shasum -a 256 -c stage1.cpio.zst.sha256)
    read -r size sha < <(python3 -I -c 'import json, sys; r = json.load(open(sys.argv[1])); print(r["size"], r["sha256"])' "$MANIFEST")
    [ "$(stat -f %z "$STAGE2")" = "$size" ] || { echo "$STAGE2 is not the pinned $size bytes"; exit 1; }
    # The M1's half reads the manifest, stage one its own pin: they must name the same stage two.
    grep -q -x "sha256=$sha" "$OUT/stage2-pin.txt" ||
        { echo "stage one is pinned to another stage two than $MANIFEST ($sha): rebuild it (host-run.sh)"; exit 1; }
    # What the judge expects of stage two, kept with this run
    cp "$OUT/stage2-pin.txt" "$V/stage2-pin.txt"
    awk '/^init:$/ { exit } f && sub(/^  /, "") { print } /^build-info:$/ { f = 1 }' "$OUT/build/stage2-unpacked.txt" > "$V/stage2-build-info.txt"
    [ -s "$V/stage2-build-info.txt" ] || { echo "no build-info in $OUT/build/stage2-unpacked.txt"; exit 1; }
    # Stage two on a read-only virtio disk: an APFS clone, padded to whole sectors (the guest reads the
    # pinned size); only the padding takes space.
    pad=$(( (512 - size % 512) % 512 ))
    if [ "$(stat -f %z "$V/stage2.img" 2> /dev/null)" != $((size + pad)) ]; then
        rm -f "$V/stage2.img"
        cp -c "$STAGE2" "$V/stage2.img"
        [ "$pad" -eq 0 ] || head -c "$pad" /dev/zero >> "$V/stage2.img"
    fi
    rm -rf "$V/results" "$V"/shot-*.png "$V/fb.raw"
    mkdir -p "$V/results"
    # the VM key's public half, from the VM-built test base, also authorized for omarchy (job 039's layout)
    tar -xOf "$TESTBASE" usr/local/lib/ilinux-test/keys/id_ed25519.pub > "$V/test-key.pub"
    python3 -I "$HERE/make-test-overlay.py" --out "$V/test-overlay.cpio" --omarchy-key "$V/test-key.pub" \
        --manifest "$MANIFEST" | tee "$V/test-overlay.txt"
    # stage one as built, then the VM-built test base (zstd), then the overlay, each at a 4-byte offset
    { cat "$STAGE1"
      n=$(stat -f %z "$STAGE1"); [ $((n % 4)) -eq 0 ] || head -c $((4 - n % 4)) /dev/zero
      cat "$TESTBASE"
      n=$(( n + (4 - n % 4) % 4 + $(stat -f %z "$TESTBASE") )); [ $((n % 4)) -eq 0 ] || head -c $((4 - n % 4)) /dev/zero
      cat "$V/test-overlay.cpio"; } > "$V/initrd"
    QARGS=(-machine virt,gic-version=3 -accel "$ACCEL" -cpu host,pmu=off -smp 1 -m "$MEM" -nic none
           -device virtio-serial-pci,id=vser -chardev "file,id=hvc0,path=$LOG" -device virtconsole,chardev=hvc0,bus=vser.0
           -drive "if=none,id=stage2,file=$V/stage2.img,format=raw,readonly=on" -device virtio-blk-pci,drive=stage2
           -fsdev "local,id=results,path=$V/results,security_model=none" -device virtio-9p-pci,fsdev=results,mount_tag=results)
    "$QEMU" "${QARGS[@]}" -machine "virt,gic-version=3,dumpdtb=$V/virt.dtb" -display none > "$V/dumpdtb.log" 2>&1
    python3 -I "$HERE/fdt-fb.py" "$V/virt.dtb" "$V/virt-fb.dtb" "$FB_ADDR" "$FB_W" "$FB_H"
    shasum -a 256 "$IMAGE" "$STAGE1" "$TESTBASE" "$V/test-overlay.cpio" "$V/initrd" "$V/virt-fb.dtb" | tee "$V/inputs-sha256.txt"
    { echo "qemu $("$QEMU" --version | head -1); accel $ACCEL; cpu host (pmu off); machine virt gic-version=3; 1 vCPU; $MEM"
      echo "framebuffer ${FB_W}x${FB_H} x2r10g10b10 stride $FB_STRIDE at $FB_ADDR (DT simple-framebuffer); root compatible: the M5's"
      echo "initrd: stage1.cpio.zst + test-base.cpio.zst + test-overlay.cpio, $(stat -f %z "$V/initrd") bytes"
      echo "stage two: virtio-blk, read-only, $(stat -f %z "$V/stage2.img") bytes (the pinned $size + padding)"
      echo "cmdline $CMDLINE"; } > "$V/qemu-setup.txt"
    cat "$V/qemu-setup.txt"
    rm -f "$SOCK" "$LOG"
    hmp() { python3 -I tools/qemumon.py "$SOCK" "$@"; }
    fbshot() {  # fbshot NAME [SCALE]: the simple-framebuffer bytes in guest RAM, what the panel shows
        rm -f "$V/fb.raw"
        hmp "pmemsave $FB_ADDR $FB_SIZE \"$V/fb.raw\"" >> "$V/hmp.log" 2>&1 || true
        for _ in $(seq 40); do [ "$(stat -f %z "$V/fb.raw" 2> /dev/null)" = "$FB_SIZE" ] && break; sleep 0.25; done
        python3 -I "$FB2PNG" "$V/fb.raw" $FB_W $FB_H $FB_STRIDE x2r10g10b10 "$V/shot-$1.png" "${2:-2}" ||
            echo "fbshot $1 failed" >&2
    }
    t0=$(python3 -I -c 'import time; print(time.time())')
    caffeinate -i "$QEMU" "${QARGS[@]}" -dtb "$V/virt-fb.dtb" -kernel "$IMAGE" -initrd "$V/initrd" \
        -append "$CMDLINE" -serial "file:$V/serial.log" -display none -monitor "unix:$SOCK,server,nowait" \
        -no-reboot > "$V/qemu.log" 2>&1 &
    qpid=$!
    shots_done=0 every=120 progress=0 end=
    SECONDS=0
    while [ "$SECONDS" -lt "$TIMEOUT" ] && kill -0 "$qpid" 2> /dev/null; do
        if [ "$SECONDS" -ge $(( (progress + 1) * every )) ]; then   # a quarter-scale frame every two minutes
            progress=$((progress + 1)); fbshot "progress-$((progress * every))s" 4
        fi
        # captures the test asks for, in order (a marker can start mid-line: no anchor)
        # (the Mac's /bin/bash is 3.2: no mapfile)
        n=0
        while read -r name; do
            n=$((n + 1))
            [ "$n" -gt "$shots_done" ] || continue
            fbshot "$name" 2
            shots_done=$n
        done < <(grep -a -o -E 'ILINUX049-SHOT [0-9.]+ [A-Za-z0-9_-]+' "$LOG" 2> /dev/null | awk '{print $3}')
        if grep -a -q -E 'ILINUX049-(DONE|FAIL)' "$LOG" 2> /dev/null; then end=1; sleep 3; break; fi
        sleep 1
    done
    python3 -I -c "import time; print('wall_s %.1f' % (time.time() - $t0))" > "$V/wall.txt"
    fbshot final 2
    hmp "info status" "quit" > /dev/null 2>&1 || true
    for _ in $(seq 20); do kill -0 "$qpid" 2> /dev/null || break; sleep 1; done
    kill "$qpid" 2> /dev/null || true
    wait "$qpid" 2> /dev/null || true
    [ -n "$end" ] || echo "the test did not finish (timeout ${TIMEOUT}s or QEMU exit; see $V/qemu.log)"
    rm -f "$V/initrd" "$V/fb.raw"
fi

# ---- judge -------------------------------------------------------------------------------------------------------
echo "--- markers (seconds since kernel start)"
grep -a -o -E 'ILINUX049-[A-Z0-9-]+ [0-9.]+.*' "$LOG" | tr -d '\r' | tee "$V/markers.txt" | cut -c1-260
expect() {  # every pattern must appear among the markers
    local missing=0
    for pattern in "$@"; do
        if grep -a -q -E -- "$pattern" "$V/markers.txt"; then echo "  found: $pattern"
        else echo "  MISSING: $pattern"; missing=1; fi
    done
    return $missing
}
# Stage two as this run's stage one was pinned to it: the copies the boot kept (out/ for a run from before)
PIN=$V/stage2-pin.txt
[ -f "$PIN" ] || PIN=$OUT/stage2-pin.txt
binfo() {
    if [ -f "$V/stage2-build-info.txt" ]; then cat "$V/stage2-build-info.txt"
    else awk '/^init:$/ { exit } f && sub(/^  /, "") { print } /^build-info:$/ { f = 1 }' "$OUT/build/stage2-unpacked.txt"; fi
}
commas() { python3 -I -c 'import sys; print(f"{int(sys.argv[1]):,}")' "$1"; }
ere() { printf '%s' "$1" | sed 's/[][\.*^$+?(){}|]/\\&/g'; }   # a literal for grep -E
S2_SIZE=$(sed -n 's/^size=//p' "$PIN")
S2_SHA=$(sed -n 's/^sha256=//p' "$PIN")
S2_ENTRIES=$(sed -n 's/^entries=//p' "$PIN")
S2_ID=$(binfo | sed -n 1,3p | tr '\n' ' ')   # built, omarchy, kernel (Image sha256)
S2_BUILT=$(binfo | sed -n 1p)
S2_OPTIONS=$(binfo | grep '^options ' || true)
# Attempt 26's root (job 045 for boot042): Omarchy's deferred hardware step and ufw, as job 045's VM test
# found; linux-modules-cleanup now keeps the root's modules for the running release, which job 041's test
# Image shares with boot042 (7.1.9-g863199d8b4a3-dirty). Attempt 25's root also had linux-modules-cleanup.
FAILED_UNITS=${FAILED_UNITS:-omarchy-provision-hardware.service ufw.service}
echo "--- stage two: $S2_SIZE bytes, $S2_SHA, $S2_ENTRIES entries; ${S2_ID}"
status=0
negatives=1
grep -a -q 'ilinux049.negatives=0' "$V/qemu-setup.txt" && negatives=0
if [ "$negatives" = 1 ]; then
    expect "^ILINUX049-NEG-OTHER-IMAGE [0-9.]+ exit 1 .*stage one refused: the M1 offers 1,048,576 bytes" \
        "^ILINUX049-NEG-SHORT [0-9.]+ exit 4 .*failed: the transfer ended after 67,108,864 of $(commas "$S2_SIZE") bytes" \
        "^ILINUX049-NEG-CORRUPT [0-9.]+ exit 4 " || status=1
fi
expect "^ILINUX049-LINK-UP [0-9.]+ udc dummy_udc.0 configured; ilinux-sshd-tty@ttyGS1.service active; host key SHA256:" \
    "^ILINUX049-HOST-SIDE [0-9.]+ iLinux J716c control channel, port 4; interface 0 /dev/ttyUSB[0-9], interface 1 /dev/ttyUSB[0-9]" \
    "^ILINUX049-IMAGE-READY [0-9.]+ $S2_SIZE bytes" \
    "^ILINUX049-STAGE1-OMARCHY [0-9.]+ ssh as omarchy: omarchy, /etc/ssh/authorized_keys.d/omarchy root:root 644" \
    "^ILINUX049-M1-SAYS [0-9.]+ m5-stage2: stage one: verified $S2_SHA" \
    "^ILINUX049-M1-SAYS [0-9.]+ m5-stage2: stage one: switching: soft-reboot into stage two: $(commas "$S2_ENTRIES") entries" \
    "^ILINUX049-M1-SENT [0-9.]+ exit 0" \
    "^ILINUX049-S2-START [0-9.]+ omarchy; root ilinux-stage2-root tmpfs; soft-reboots 1; $(ere "$S2_ID")" \
    "^ILINUX049-READY [0-9.]+ layers: " \
    "^ILINUX049-LINK2-UP [0-9.]+ udc dummy_udc.0" \
    "^ILINUX049-LINK2 [0-9.]+ ssh m5o in [0-9.]+ s: SSH-OK omarchy@omarchy sudo-uid=0; root ilinux-stage2-root tmpfs; soft-reboots 1; $(ere "$S2_BUILT, $S2_OPTIONS")" \
    "^ILINUX049-IMAGE-FIXES [0-9.]+ repeat_delay=1000; runtime weather absent; keyboard enabled and skipped without MTP; online CPU 0$" \
    "^ILINUX049-FAILED-UNITS [0-9.]+ $(ere "$FAILED_UNITS") \$" \
    "^ILINUX049-DONE [0-9.]+ pass" || status=1
if grep -a -q -E 'ILINUX049-FAIL |Kernel panic' "$LOG"; then echo "  UNEXPECTED: FAIL or panic"; status=1; fi
if grep -q 'cpufreq.default_governor=userspace' "$V/qemu-setup.txt"; then
    expect '^ILINUX049-CPU28-ASSETS [0-9.]+ verified; virtual hardware refused; no module load or DVFS writes$' || status=1
fi
shots="receiving desktop"
[ "$negatives" = 1 ] && shots="neg1-other-image neg2-short neg3-corrupt $shots"
for s in $shots; do
    [ -s "$V/shot-$s.png" ] && echo "  capture: shot-$s.png" || { echo "  MISSING capture: shot-$s.png"; status=1; }
done
# The timeline, from the markers and both stages' journal (seconds since kernel start = since the VM's handoff)
t() { grep -a -o -E "^ILINUX049-$1 [0-9.]+" "$V/markers.txt" | head -1 | awk '{print $2}'; }
j() { grep -a -E "$1" "$V/results/journal.txt" 2> /dev/null | head -1 | sed -E 's/^\[ *([0-9.]+)\].*/\1/'; }
{ echo "link up (stage one: gadget configured, sshd on the pipe): $(t LINK-UP)"
  echo "the real transfer started (stage one's last 'receiving stage two'): $(grep -a -E 'ilinux-stage2\[[0-9]+\]: receiving stage two' "$V/results/journal.txt" 2> /dev/null | tail -1 | sed -E 's/^\[ *([0-9.]+)\].*/\1/')"
  echo "received and verified: $(grep -a -E 'ilinux-stage2\[[0-9]+\]: verified' "$V/results/journal.txt" 2> /dev/null | tail -1 | sed -E 's/^\[ *([0-9.]+)\].*/\1/') ($(grep -a -o -E 'received [0-9,]+ bytes in [0-9.]+ s \([0-9.]+ MB/s\)' "$V/results/journal.txt" 2> /dev/null | tail -1))"
  echo "unpacked: $(j 'ilinux-stage2\[[0-9]+\]: unpacked:') ($(grep -a -o -E 'unpacked: .*' "$V/results/journal.txt" 2> /dev/null | head -1))"
  echo "switching (stage one's last word; the soft-reboot follows 2 s later): $(j 'ilinux-stage2\[[0-9]+\]: switching to stage two')"
  echo "stage two's systemd: $(grep -a -o 'UserspaceTimestampMonotonic=[0-9]*' "$V/results/stage2-identity.txt" 2> /dev/null | awk -F= '{printf "%.2f", $2 / 1e6}') ($(j 'Soft-reboot finished' | head -1): $(grep -a -o 'Soft-reboot finished in [0-9.]*s' "$V/results/journal.txt" 2> /dev/null | head -1))"
  echo "stage two's gadget: $(j '\] omarchy usb-gadget.sh\[[0-9]+\]: gadget .* bound')"
  echo "SDDM / Hyprland / desktop ready: $(t SDDM) / $(t HYPRLAND) / $(t READY)"
  echo "stage two's link checked by the M1 (ssh m5o): $(t LINK2)"; } | tee "$V/timeline-summary.txt"
[ $status = 0 ] && echo "run-qemu.sh: PASS" || echo "run-qemu.sh: FAIL (see $V)"
exit $status
