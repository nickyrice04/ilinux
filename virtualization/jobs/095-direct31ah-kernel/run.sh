#!/bin/bash
# SPDX-License-Identifier: MIT
# Offline only. Run inside the existing isolated arm64 Linux build VM.
set -euo pipefail
I=/mnt/ilinux
O=/mnt/job/out
W=/mnt/job/work/direct31ah-kernel
K=$W/linux
JOBS=${JOBS:-6}
mkdir -p "$I" "$O" "$W"
mkdir -p /mnt/job/work/tmp
export TMPDIR=/mnt/job/work/tmp
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
exec > "$O/build.log" 2>&1
export KBUILD_BUILD_TIMESTAMP='@1794355200'
export KBUILD_BUILD_USER=ilinux KBUILD_BUILD_HOST=direct31ah
export ARCH=arm64
export LC_ALL=C
printf '%s\n' 'DIRECT31AH_KERNEL_BUILD_START'
python3 -I "$I/kernel/experiments/direct31ah/linux/bind_sources.py" "$I" "$O/input-source-files.json"
{ uname -srm; gcc --version | head -1; ld --version | head -1; make --version | head -1; python3 --version; } > "$O/toolchain.txt"
python3 -I - "$O/inputs.json" "$K" <<'PY'
import hashlib,json,sys,tarfile
from pathlib import Path
meta=json.loads(Path(sys.argv[1]).read_text())
assert meta['source_commit']=='dc8f6f77934b471a13c91e7780e2d91ebc904b3d'
p=Path(meta['archive'])
assert p.is_file() and not p.is_symlink()
h=hashlib.sha256()
with p.open('rb') as f:
 for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
assert h.hexdigest()==meta['archive_sha256']
dest=Path(sys.argv[2])
if not dest.exists():
 dest.mkdir()
 with tarfile.open(p) as tar:
  members=tar.getmembers(); tops={m.name.split('/')[0] for m in members}
  assert len(tops)==1
  prefix=next(iter(tops))+'/'
  for m in members:
   if not m.name.startswith(prefix):continue
   m.name=m.name[len(prefix):]
   if not m.name:continue
   tar.extract(m,dest,filter='data')
 (dest/'.ilinux-input-sha256').write_text(h.hexdigest()+'\n')
else:
 assert (dest/'.ilinux-input-sha256').read_text().strip()==h.hexdigest()
print('PINNED_ARCHIVE_VERIFIED')
PY
cd "$K"
make defconfig > "$O/configure.log" 2>&1
scripts/kconfig/merge_config.sh -m .config arch/arm64/configs/asahi.config \
 "$I/virtualization/jobs/095-direct31ah-kernel/diagnostic.config" >> "$O/configure.log" 2>&1
make olddefconfig >> "$O/configure.log" 2>&1
python3 -I "$I/kernel/experiments/direct31ah/linux/check_config.py" .config > "$O/config-check.json"
python3 -I "$I/kernel/experiments/direct31ah/linux/test_offline.py" > "$O/offline-tests.log" 2>&1
cp .config "$O/kernel.config"
start=$(date +%s)
make -j"$JOBS" Image modules apple/t6050-j716c.dtb > "$O/make.log" 2>&1
echo "build_seconds=$(( $(date +%s)-start ))" > "$O/build-time.txt"
cp arch/arm64/boot/Image "$O/Image"
cp arch/arm64/boot/dts/apple/t6050-j716c.dtb "$O/t6050-j716c-upstream.dtb"
dtc -I dtb -O dts -o "$O/t6050-j716c-upstream.dts" "$O/t6050-j716c-upstream.dtb" 2> "$O/dtc.log"
python3 -I "$I/kernel/experiments/direct31ah/linux/check_dtb.py" \
 "$O/t6050-j716c-upstream.dtb" > "$O/dt-check.json"
# A separate diagnostic derivative removes the publisher's per-unit DROM and
# disables unqualified SEP, ISP and USB4 controller nodes.
python3 -I "$I/kernel/experiments/direct31ah/linux/make_diag_dt.py" \
 "$O/t6050-j716c-upstream.dtb" "$O/t6050-j716c-diagnostic.dtb" > "$O/dt-derivative.json"
python3 -I "$I/kernel/experiments/direct31ah/linux/check_dtb.py" \
 "$O/t6050-j716c-diagnostic.dtb" > "$O/diag-dt-check.json"
dtc -I dtb -O dts -o "$O/t6050-j716c-diagnostic.dts" "$O/t6050-j716c-diagnostic.dtb" 2>> "$O/dtc.log"
mkdir -p "$W/modules"
make INSTALL_MOD_PATH="$W/modules" INSTALL_MOD_STRIP=1 modules_install > "$O/modules-install.log" 2>&1
tar -C "$W/modules" --sort=name --mtime='@1794355200' --owner=0 --group=0 --numeric-owner \
 -czf "$O/modules-OFFLINE-REVIEW.tar.gz" lib
gcc -static -O2 -std=c11 -Wall -Wextra -Werror -pthread \
 "$I/kernel/experiments/direct31ah/linux/diag_init.c" -o "$O/diag-init"
python3 -I "$I/kernel/experiments/direct31ah/linux/make_initramfs.py" \
 "$O/diag-init" "$O/initramfs-direct31ah.cpio.gz"
"$O/diag-init" --selftest > "$O/collector-selftest.json"
"$O/diag-init" --selftest-timeout > "$O/collector-timeout-selftest.json"
python3 -I "$I/kernel/experiments/direct31ah/linux/bind_sources.py" "$I" "$O/input-source-files.json" --verify
python3 -I "$I/kernel/experiments/direct31ah/linux/check_artifacts.py" "$O" > "$O/artifacts.json"
sha256sum "$O/Image" "$O/kernel.config" "$O/t6050-j716c-upstream.dtb" \
 "$O/t6050-j716c-diagnostic.dtb" "$O/initramfs-direct31ah.cpio.gz" \
 "$O/modules-OFFLINE-REVIEW.tar.gz" "$O/diag-init" "$O/input-source-files.json" > "$O/artifacts.sha256"
printf '%s\n' 'DIRECT31AH_KERNEL_BUILD_PASS_OFFLINE_ONLY'
