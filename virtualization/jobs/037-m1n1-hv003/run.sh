#!/bin/bash
# Build the private iLinux hv003 m1n1: pinned 57a9339 + native/hv 0001 (hv002) + 0002 (crumbs).
# Exports System.map for both guest kernels (boot033, boot034). Touches no source tree.
set -euo pipefail
PIN=57a9339ffd1876e78297b17d34dece8cff8fa1ba
OUT=/mnt/job/out
WORK=/var/tmp/ilinux-hv003
P1=/mnt/ilinux/native/hv/0001-ilinux-hv-t6050-hv002.patch
P2=/mnt/ilinux/native/hv/0002-ilinux-hv-t6050-hv003-crumbs.patch
mkdir -p /mnt/ilinux /mnt/m1n1-source "$OUT/export"
mount -t virtiofs ilinux /mnt/ilinux
mount -t virtiofs m1n1-source /mnt/m1n1-source
test "$(git -C /mnt/m1n1-source rev-parse HEAD)" = "$PIN"
test -z "$(git -C /mnt/m1n1-source status --porcelain --untracked-files=no)"
case "$WORK" in /var/tmp/ilinux-hv003) rm -rf "$WORK" ;; *) exit 1 ;; esac
mkdir -p "$WORK"
git clone -q /mnt/m1n1-source "$WORK/m1n1"
git -C "$WORK/m1n1" checkout -q "$PIN"
git -C "$WORK/m1n1" apply --check "$P1"
git -C "$WORK/m1n1" apply "$P1"
git -C "$WORK/m1n1" apply --check "$P2"
git -C "$WORK/m1n1" apply "$P2"
(
    cd "$WORK/m1n1"
    export M1N1_VERSION_TAG=ilinux-57a9339-hv003
    make clean
    make -j6 ARCH= BUILDSTD=1
) > "$OUT/m1n1-build.log" 2>&1
grep -c "warning:" "$OUT/m1n1-build.log" > "$OUT/m1n1-warnings.txt" || true
cp "$WORK/m1n1/build/m1n1.bin" "$OUT/export/m1n1-hv.bin"
cp "$WORK/m1n1/build/build_cfg.h" "$OUT/export/m1n1-hv-build-config.h"
nm -an "$WORK/m1n1/build/m1n1-raw.elf" > "$OUT/export/m1n1-hv-symbols.txt"
for sym in ' T kboot_prepare_hv_guest' ' T hv_ilinux_timers_reset' ' hv_ilinux_single_cpu' ' hv_ilinux_init_failed' ' T ilinux_crumb'; do
    grep -q "$sym\$" "$OUT/export/m1n1-hv-symbols.txt" || { echo "missing symbol:$sym"; exit 1; }
done
objdump -d "$(find "$WORK/m1n1/build" -name startup.o | head -1)" > "$OUT/startup.dis"
objdump -d "$(find "$WORK/m1n1/build" -name main.o | head -1)" > "$OUT/main.dis"

B33=/var/tmp/ilinux-boot033/linux
B34=/var/tmp/ilinux-boot034/linux
test "$(sha256sum "$B33/arch/arm64/boot/Image" | cut -d' ' -f1)" = 250d9ff58e5f5397e1bb54682f2bd8a7a679f44f2863629ef7b89ec45ad1eb15
test "$(sha256sum "$B34/arch/arm64/boot/Image" | cut -d' ' -f1)" = 1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579
cp "$B33/System.map" "$OUT/export/System.map"
cp "$B34/System.map" "$OUT/export/System.map-boot034"
{
    uname -srm
    gcc --version | head -1
    ld --version | head -1
    printf 'm1n1 %s + %s + %s\n' "$PIN" "$(sha256sum "$P1" | cut -d' ' -f1)" "$(sha256sum "$P2" | cut -d' ' -f1)"
} > "$OUT/export/toolchain.txt"
(cd "$OUT/export" && sha256sum * > ../SHA256SUMS)
echo 'JOB 037 PASS'
