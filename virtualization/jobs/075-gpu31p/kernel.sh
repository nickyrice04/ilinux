#!/bin/bash
# SPDX-License-Identifier: MIT
# Optional upstream M4 object compilation only; no Image, install or module load.
set -euo pipefail
S=/mnt/gpu31p-sources W=/var/tmp/ilinux-gpu31p-kernel O=/mnt/job/out
K=$W/linux-4fc326f B=$W/kernel-build
# Dedicated job075 guest directories; never reuse a modified source tree.
rm -rf -- "$K" "$B"
mkdir -p "$K" "$B"
tar --extract --gzip --file "$S/linux-4fc326f.tar.gz" --directory "$K" --strip-components=1 --no-same-owner --no-same-permissions
export KBUILD_BUILD_TIMESTAMP='@0' KBUILD_BUILD_USER=ilinux KBUILD_BUILD_HOST=gpu31p
make -C "$K" O="$B" LLVM=1 ARCH=arm64 defconfig
"$K/scripts/config" --file "$B/.config" --disable ARM64_4K_PAGES --enable ARM64_16K_PAGES \
  --enable ARCH_APPLE --enable PM --enable DRM --enable RUST --enable DRM_ASAHI_M4 \
  --disable WERROR --disable DEBUG_INFO_BTF --disable MODVERSIONS
make -C "$K" O="$B" LLVM=1 ARCH=arm64 olddefconfig
cp "$B/.config" "$O/kernel.config"
make -C "$K" O="$B" LLVM=1 ARCH=arm64 rustavailable
if ! grep -q '^CONFIG_RUST=y$' "$B/.config" || ! grep -q '^CONFIG_DRM_ASAHI_M4=y$' "$B/.config"; then
  echo 'KERNEL_OBJECT_BLOCKED: required Rust/M4 Kconfig prerequisite unavailable'
  exit 2
fi
make -C "$K" O="$B" LLVM=1 ARCH=arm64 -j4 drivers/gpu/drm/asahi/asahi_m4.o
cp "$B/drivers/gpu/drm/asahi/asahi_m4.o" "$O/"
sha256sum "$O/asahi_m4.o"
echo KERNEL_M4_OBJECT_BUILD_PASS_NATIVE_NOT_RUN
