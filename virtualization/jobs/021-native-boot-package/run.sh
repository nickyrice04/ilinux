#!/bin/bash
# Export the existing job-020 outputs; do not rebuild or replace that tree.
set -euo pipefail
SRC=/var/tmp/t6050-build
OUT=/mnt/job/out
mkdir -p "$OUT/export"
for tool in gcc ld make rustc cargo dtc fdtget fdtput python3; do
    command -v "$tool" || true
done
for f in "$SRC/linux/arch/arm64/boot/Image" \
         "$SRC/linux/arch/arm64/boot/dts/apple/t6050-j716c.dtb" \
         "$SRC/initramfs.cpio.gz"; do
    test -f "$f"
    cp "$f" "$OUT/export/"
done
cp "$SRC/out/kernel.config" "$OUT/export/"
sha256sum "$OUT/export/"* > "$OUT/export-sha256.txt"
mkdir -p /mnt/m1n1-source /mnt/ilinux
mount -t virtiofs m1n1-source /mnt/m1n1-source
mount -t virtiofs ilinux /mnt/ilinux
echo 'EXPORT PASS; controller console ready for isolated build/tests.'
