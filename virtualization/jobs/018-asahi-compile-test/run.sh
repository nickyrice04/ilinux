#!/bin/sh
# Job 018: compile-test the local t6050 patch series against Asahi's kernel.
# (Local research only - Asahi's AI policy forbids submitting it, D-007.)
set -x
OUT=/mnt/job/out
mkdir -p /mnt/integ && mount -t virtiofs integ /mnt/integ || exit 1
cd /root && rm -rf asahi && mkdir asahi && cd asahi && git init -q && git remote add origin https://github.com/AsahiLinux/linux.git
git fetch -q --depth 1 origin 77cb8f24c2381a8abb7272d7bbdec548d6426a8a && git checkout -q FETCH_HEAD || exit 1
git log -1 --format='%H %ad' > $OUT/base.txt
git -c user.name=local -c user.email=local@localhost am /mnt/integ/kernel/patches/t6050/000*.patch > $OUT/am.log 2>&1
echo "git am exit=$?"; tail -3 $OUT/am.log
make ARCH=arm64 defconfig > /dev/null 2>&1
scripts/config -e ARCH_APPLE -e APPLE_SART -e NVME_APPLE -e APPLE_RTKIT -e APPLE_MAILBOX -e APPLE_DART
make olddefconfig > /dev/null 2>&1
grep -E 'CONFIG_(APPLE_SART|NVME_APPLE|ARCH_APPLE)=' .config > $OUT/config.txt
make -j18 drivers/soc/apple/sart.o drivers/nvme/host/apple.o > $OUT/compile.log 2>&1
echo "driver compile exit=$?"; grep -E 'error|warning' $OUT/compile.log | head -20
make -j18 dtbs > $OUT/dtbs.log 2>&1; echo "dtbs exit=$?"
ls -la arch/arm64/boot/dts/apple/t6050* > $OUT/dtb-files.txt 2>&1
grep -E 'error|warning.*t6050' $OUT/dtbs.log | head -20
