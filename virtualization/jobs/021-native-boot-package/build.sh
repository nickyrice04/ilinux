#!/bin/bash
# Runs only inside the existing isolated ARM64 job VM, after run.sh export.
set -euo pipefail
JOB=/mnt/job
OUT=$JOB/out
WORK=/var/tmp/ilinux-boot021
REPO=/mnt/ilinux
PIN=57a9339ffd1876e78297b17d34dece8cff8fa1ba
export M1N1_VERSION_TAG=ilinux-57a9339-boot021
test "$(git -C /mnt/m1n1-source rev-parse HEAD)" = "$PIN"
test -z "$(git -C /mnt/m1n1-source status --porcelain --untracked-files=no)"
mkdir -p "$WORK" "$OUT/export"
if [ ! -d "$WORK/m1n1" ]; then cp -a /mnt/m1n1-source "$WORK/m1n1"; fi
test "$(git -C "$WORK/m1n1" rev-parse HEAD)" = "$PIN"
test -z "$(git -C "$WORK/m1n1" status --porcelain --untracked-files=no)"
(
    cd "$WORK/m1n1"
    make clean
    make -j6 ARCH= BUILDSTD=1
) > "$OUT/m1n1-build.log" 2>&1
test -z "$(git -C "$WORK/m1n1" status --porcelain --untracked-files=no)"
cp "$WORK/m1n1/build/m1n1.bin" "$OUT/export/"
nm -an "$WORK/m1n1/build/m1n1-raw.elf" > "$OUT/m1n1-symbols.txt"
readelf -h "$WORK/m1n1/build/m1n1-raw.elf" > "$OUT/m1n1-elf.txt"
cp "$WORK/m1n1/build/build_cfg.h" "$OUT/export/m1n1-build-config.h"
cp "$WORK/m1n1/LICENSE" "$OUT/export/m1n1-LICENSE"

# Original job-020 DT already disables NVMe. Reassert it and also leave
# unvalidated frequency controllers disabled for the first diagnostic boot.
DT="$OUT/export/t6050-j716c-stage-b.dtb"
cp "$OUT/export/t6050-j716c.dtb" "$DT"
for node in /soc/nvme@45dcc0000 \
    /soc/performance-controller@210e20000 \
    /soc/performance-controller@211e20000 \
    /soc/performance-controller@212e20000; do
    fdtget "$DT" "$node" compatible
    fdtput -t s "$DT" "$node" status disabled
done > "$OUT/stage-b-dt.log"
fdtput -d "$DT" /chosen stdout-path
dtc -I dtb -O dts "$DT" > "$OUT/stage-b.dts" 2> "$OUT/stage-b-dtc.log"

# Preserve job-020's original initramfs. Build a separate Stage-B variant
# whose success message does not promise a native USB console.
mkdir -p "$WORK/initramfs"/{dev,proc,sys}
gcc -static -O2 -Wall -Wextra -Werror -o "$WORK/initramfs/init" \
    "$REPO/native/boot/diag-init.c"
(
    cd "$WORK/initramfs"
    find . -exec touch -h -d @0 {} +
    find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --reproducible --owner=0:0 | gzip -n -9
) > "$OUT/export/initramfs-stage-b.cpio.gz" 2> "$OUT/initramfs-build.log"
cp "$REPO/native/boot/diag-init.c" "$OUT/export/diag-init.c"
{
    uname -srm
    gcc --version | head -1
    ld --version | head -1
    rustc --version
    cargo --version
    python3 --version
    dtc --version
} > "$OUT/export/toolchain.txt"
sha256sum "$OUT/export/"* > "$OUT/export-sha256.txt"
echo 'BUILD PASS: native images prepared, not executed.'
