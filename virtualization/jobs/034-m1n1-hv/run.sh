#!/bin/bash
# Build the private iLinux hypervisor m1n1 (pinned 57a9339 + native/hv patch)
# and export boot033's System.map for symbolized hypervisor backtraces.
# Never touches the pinned clone or the boot033 tree.
set -euo pipefail
PIN=57a9339ffd1876e78297b17d34dece8cff8fa1ba
IMAGE_SHA=250d9ff58e5f5397e1bb54682f2bd8a7a679f44f2863629ef7b89ec45ad1eb15
OUT=/mnt/job/out
WORK=/var/tmp/ilinux-hv001
mkdir -p /mnt/ilinux /mnt/m1n1-source "$OUT/export"
mount -t virtiofs ilinux /mnt/ilinux
mount -t virtiofs m1n1-source /mnt/m1n1-source
test "$(git -C /mnt/m1n1-source rev-parse HEAD)" = "$PIN"
test -z "$(git -C /mnt/m1n1-source status --porcelain --untracked-files=no)"
rm -rf "$WORK" && mkdir -p "$WORK"
git clone -q /mnt/m1n1-source "$WORK/m1n1"
git -C "$WORK/m1n1" checkout -q "$PIN"
git -C "$WORK/m1n1" apply --check /mnt/ilinux/native/hv/0001-ilinux-hv-t6050-single-cpu.patch
git -C "$WORK/m1n1" apply /mnt/ilinux/native/hv/0001-ilinux-hv-t6050-single-cpu.patch
(
    cd "$WORK/m1n1"
    export M1N1_VERSION_TAG=ilinux-57a9339-hv001
    make clean
    make -j6 ARCH= BUILDSTD=1
) > "$OUT/m1n1-build.log" 2>&1
grep -c "warning:" "$OUT/m1n1-build.log" > "$OUT/m1n1-warnings.txt" || true
cp "$WORK/m1n1/build/m1n1.bin" "$OUT/export/m1n1-hv.bin"
cp "$WORK/m1n1/build/build_cfg.h" "$OUT/export/m1n1-hv-build-config.h"
nm -an "$WORK/m1n1/build/m1n1-raw.elf" > "$OUT/export/m1n1-hv-symbols.txt"
# Confirm the private symbols linked in.
grep -q ' T kboot_prepare_hv_guest$' "$OUT/export/m1n1-hv-symbols.txt"
grep -q ' hv_ilinux_single_cpu$' "$OUT/export/m1n1-hv-symbols.txt"

KTREE=/var/tmp/ilinux-boot033/linux
test "$(sha256sum "$KTREE/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$IMAGE_SHA"
cp "$KTREE/System.map" "$OUT/export/System.map"
{
    uname -srm
    gcc --version | head -1
    ld --version | head -1
    printf 'm1n1 %s + %s\n' "$PIN" "$(sha256sum /mnt/ilinux/native/hv/0001-ilinux-hv-t6050-single-cpu.patch | cut -d' ' -f1)"
} > "$OUT/export/toolchain.txt"
(cd "$OUT/export" && sha256sum * > ../SHA256SUMS)
echo 'JOB 034 PASS'
