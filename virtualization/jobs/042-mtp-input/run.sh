#!/bin/bash
# job 042: kernel-side checks for the MTP ring transport (kernel/experiments/mtp-input).
# Offline: nothing here boots, touches the M5 or changes any package. The exact tree that
# built the boot034 = boot035 Image is only read; every build happens in a private copy.
#  1. inputs: the tree (boot036's if present, else boot035's), its Image and its dockchannel-hid.c are
#     the ones we expect;
#  2. 0001 (if the tree lacks it) and 0002 applied to the copy; config delta; olddefconfig;
#  3. the patched driver compiled with the kernel's own flags (W=1), warnings of OUR files kept;
#  4. checkpatch on the two files (informational), full Image link, symbol check;
#  5. the userspace driver harness again, here with gcc and glibc;
#  6. the candidate DT through dtc and dt-validate (informational: no schema covers dockchannel).
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/mtp-input
DRV=drivers/hid/dockchannel-hid/dockchannel-hid.c
K34=/var/tmp/ilinux-boot034/linux
K36=/var/tmp/ilinux-boot036/linux       # job 041's tree: boot035 + the USB gadget stack built in
WORK=/var/tmp/ilinux-mtp-input/linux
IMAGE_SHA=1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579   # boot035's Image
IMAGE36_SHA=$(awk '$2 == "Image" {print $1}' /mnt/ilinux/build/native-boot036/verified/SHA256SUMS 2> /dev/null || true)
BASE_SHA=15c1186c3bbb87dddb75c1f1053ab3a2c3a2a1128bba6718bd88977f4b7beb2f      # pinned 77cb8f24
P0001_SHA=e888ddaefc7d05f582b1db831ec9f2bd2e9858f4503242edf7c369866c45605c    # + 0001
P0001=/mnt/ilinux/kernel/experiments/driver-contracts/dockchannel-hid/0001-dockchannel-hid-validate-input-bounds.patch
P0002=$EXP/patches/0002-dockchannel-hid-mtp-ring-transport.patch
EPOCH=1760486400                     # 2025-10-15 00:00 UTC, as job 041
# the Image embeds its build time, user and host: pin them so a rebuild gives the same Image
export KBUILD_BUILD_TIMESTAMP="@$EPOCH" KBUILD_BUILD_USER=ilinux KBUILD_BUILD_HOST=job042
JOBS=$(nproc)
log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
rm -rf "$OUT"/*; mkdir -p "$OUT/build" /var/tmp/ilinux-mtp-input
exec > "$OUT/script.log" 2>&1     # run.log only gets the runner's own lines

log "1. inputs"
# boot036 (the USB control channel, needed for input verification over SSH) when its tree is
# there and is the one that built the packaged Image; otherwise the boot035 tree.
if [ -n "$IMAGE36_SHA" ] && [ -f "$K36/arch/arm64/boot/Image" ] &&
   [ "$(sha256sum < "$K36/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$IMAGE36_SHA" ]; then
    KTREE=$K36; LABEL=boot036; BASEDIR=/mnt/ilinux/build/native-boot036/verified
else
    KTREE=$K34; LABEL=boot035; BASEDIR=/mnt/ilinux/build/native-boot035/verified
    test "$(sha256sum < "$KTREE/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$IMAGE_SHA"
fi
echo "base tree: $LABEL ($KTREE)" | tee "$OUT/build/base-tree.txt"
{ uname -srm; gcc --version | head -1; ld --version | head -1; dtc --version; python3 --version; } > "$OUT/toolchain.txt"
have=$(sha256sum < "$KTREE/$DRV" | cut -d' ' -f1)
echo "tree driver sha256 $have" | tee "$OUT/build/tree-driver.txt"

log "2. copy, patches, config"
rm -rf "$WORK"
cp -a --reflink=auto "$KTREE" "$WORK"
cd "$WORK"
case "$have" in
    "$BASE_SHA")  patch -p1 -s -i "$P0001"; echo "0001 applied (tree had the pinned file)" ;;
    "$P0001_SHA") echo "tree already carries 0001" ;;
    *) echo "unexpected dockchannel-hid.c in the tree ($have); stop" >&2; exit 1 ;;
esac | tee -a "$OUT/build/patches.txt"
test "$(sha256sum < "$DRV" | cut -d' ' -f1)" = "$P0001_SHA"
patch -p1 --dry-run -s -i "$P0002"
patch -p1 -s -i "$P0002"
sha256sum "$DRV" drivers/hid/dockchannel-hid/dchid-ring.h | tee -a "$OUT/build/patches.txt"
cmp drivers/hid/dockchannel-hid/dchid-ring.h "$EXP/ring/dchid_ring.h"
cp .config "$OUT/build/config-before"
for sym in APPLE_RTKIT_HELPER HID_APPLE HID_MAGICMOUSE HIDRAW; do
    scripts/config --file .config --enable "$sym"
done
make olddefconfig > "$OUT/build/olddefconfig.log" 2>&1
diff "$OUT/build/config-before" .config > "$OUT/build/config.diff" || test "$?" = 1
python3 -I "$EXP/check_config.py" .config | tee "$OUT/build/check-config.txt"
grep -E '^CONFIG_(APPLE_RTKIT_HELPER|HID_APPLE|HID_MAGICMOUSE|HIDRAW|HID_DOCKCHANNEL|APPLE_DOCKCHANNEL)=' .config \
    | tee "$OUT/build/config-symbols.txt"

log "3. driver object with W=1"
make -j"$JOBS" W=1 drivers/hid/dockchannel-hid/ > "$OUT/build/driver-build.log" 2>&1 \
    || { tail -40 "$OUT/build/driver-build.log"; exit 1; }
grep -E 'dockchannel-hid\.c|dchid-ring\.h' "$OUT/build/driver-build.log" > "$OUT/build/driver-warnings.txt" || true
echo "warnings/notes in our two files: $(wc -l < "$OUT/build/driver-warnings.txt")"
cp "$OUT/build/driver-warnings.txt" "$OUT/build/driver-warnings-keep.txt"

log "4. checkpatch, Image link, symbols"
for f in drivers/hid/dockchannel-hid/dockchannel-hid.c drivers/hid/dockchannel-hid/dchid-ring.h; do
    perl scripts/checkpatch.pl --no-tree --strict --terse -f "$f" || true
done > "$OUT/build/checkpatch.txt" 2>&1
tail -3 "$OUT/build/checkpatch.txt" || true
make -j"$JOBS" Image > "$OUT/build/image-build.log" 2>&1 || { tail -40 "$OUT/build/image-build.log"; exit 1; }
nm vmlinux > "$OUT/build/symbols.txt"
for sym in dchid_ring_drain dchid_handshake_work dchid_dispatch dchid_stm_fallback_work \
           dockchannel_hid_driver dchid_cfg_ring; do
    grep -q " $sym$" "$OUT/build/symbols.txt" || grep -q " $sym\.[0-9a-z]*$" "$OUT/build/symbols.txt" \
        || { echo "missing symbol $sym"; exit 1; }
done
echo "ring transport symbols present in the linked kernel" | tee "$OUT/build/symbols-check.txt"
cp arch/arm64/boot/Image "$OUT/build/Image-mtp-input-$LABEL"
sha256sum "$OUT/build/Image-mtp-input-$LABEL" | tee "$OUT/build/image-sha256.txt"

log "5. userspace harness with gcc/glibc"
T=$(mktemp -d)
python3 -I - "$EXP/driver-test" "$WORK/$DRV" "$WORK/drivers/hid/dockchannel-hid/dchid-ring.h" "$T" <<'PY'
import subprocess, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import driver_build as D
tree, inc = D.prepare_tree(Path(sys.argv[4]), Path(sys.argv[2]), Path(sys.argv[3]))
exe = Path(sys.argv[4]) / "test_driver"
cmd = D.compile_cmd("gcc", tree, inc, Path(sys.argv[1]) / "test_driver.c", exe)
print(" ".join(cmd))
subprocess.run(cmd, check=True)
r = subprocess.run([str(exe)], capture_output=True, text=True)
print((r.stdout + r.stderr).strip().splitlines()[-1])
sys.exit(r.returncode)
PY
echo "gcc harness exit $?" | tee "$OUT/build/harness-gcc.txt"

log "6. DT candidate"
export PATH=/var/tmp/t6050-build/dtvenv/bin:$PATH
B36=$BASEDIR
if [ -f "$B36/t6050-j716c-stage-b.dtb" ]; then
    python3 -I "$EXP/make_mtp_dt.py" "$B36/t6050-j716c-stage-b.dtb" /mnt/ilinux/hardware/adt/adt-sanitized.json \
        "$OUT/build/mtp.dtb" "$OUT/build/mtp-delta.json" --dts "$OUT/build/mtp-new.dts" > "$OUT/build/make-mtp-dt.log"
    dtc -I dtb -O dts -s "$B36/t6050-j716c-stage-b.dtb" > "$OUT/build/before.dts" 2> "$OUT/build/dtc-before.log"
    dtc -I dtb -O dts -s "$OUT/build/mtp.dtb" > "$OUT/build/after.dts" 2> "$OUT/build/dtc-after.log"
    diff -u "$OUT/build/before.dts" "$OUT/build/after.dts" > "$OUT/build/dt.diff" || test "$?" = 1
    SCHEMA=$WORK/Documentation/devicetree/bindings/processed-schema.json
    dt-validate -s "$SCHEMA" "$B36/t6050-j716c-stage-b.dtb" > "$OUT/build/dt-validate-before.log" 2>&1 || true
    dt-validate -s "$SCHEMA" "$OUT/build/mtp.dtb" > "$OUT/build/dt-validate-after.log" 2>&1 || true
    wc -l "$OUT/build/dt-validate-before.log" "$OUT/build/dt-validate-after.log" | tee "$OUT/build/dt-validate-summary.txt"
else
    echo "no $LABEL Stage-B DTB under build/; DT step skipped" | tee "$OUT/build/dt-skipped.txt"
fi
log "done"
echo PASS > "$OUT/job.status"
echo "PASS ($LABEL tree): 0002 applies, compiles (W=1), links, symbols present, harness (gcc) passes" > "$OUT/summary.txt"
