#!/bin/bash
# SPDX-License-Identifier: MIT
# VM only. Build the matched unmodified public source, never boot its output.
set -euo pipefail
O=/mnt/job/out
R=/mnt/recipe
S=/mnt/inputs
M=/mnt/community096
W=$M/work
mkdir -p "$O" "$R" "$S" "$M"
mountpoint -q "$R" || mount -t virtiofs recipe "$R" -o ro
mountpoint -q "$S" || mount -t virtiofs inputs "$S" -o ro
exec > "$O/build.log" 2>&1
trap 'rc=$?; printf "{\"exit\":%s,\"native_ready\":false}\n" "$rc" > "$O/exit.json"' EXIT
test "$(ls /sys/class/net)" = lo
pacman -Q > "$O/packages-before.txt"
mount -t tmpfs -o size=32G,mode=0700 tmpfs "$M"
export TMPDIR=$M/tmp
mkdir -p "$TMPDIR"
python3 -I - "$M" "$O/resource-preflight.json" <<'PY'
import json,os,sys,tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(dir=sys.argv[1]) as d:
 a=Path(d)/'case';b=Path(d)/'CASE';a.write_bytes(b'lower');b.write_bytes(b'upper')
 assert a.stat().st_ino!=b.stat().st_ino and a.read_bytes()==b'lower'
v=os.statvfs(sys.argv[1]);assert v.f_bavail*v.f_frsize>=30*1024**3
Path(sys.argv[2]).write_text(json.dumps({'case_sensitive':True,'tmpfs_bytes':v.f_blocks*v.f_frsize,'network_interfaces':['lo'],'source_build_on_host_share':False},indent=2)+'\n')
PY
python3 -I "$R/prepare.py" "$S" "$W" "$O"
. "$W/environment.sh"
export ARCH=arm64 LLVM=1 LC_ALL=C
export SOURCE_DATE_EPOCH=1794338095
export KBUILD_BUILD_USER=j716c KBUILD_BUILD_HOST=bringup KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP="$(date -u -d "@$SOURCE_DATE_EPOCH")"
export RUSTC="$W/toolchain/bin/rustc" BINDGEN="$W/toolchain/bin/bindgen"
K=$W/linux
cd "$K"
make LLVM=1 LOCALVERSION= rustavailable > "$O/rustavailable.log" 2>&1
make LLVM=1 LOCALVERSION= olddefconfig > "$O/olddefconfig.log" 2>&1
cp .config "$O/kernel.config"
python3 -I "$R/check_config.py" "$S/kernel.config" .config > "$O/full-config-comparison.json"
printf '%s\n' 'J716C_MATCHED_BUILD_START'
start=$(date +%s)
make -j6 LLVM=1 LOCALVERSION= Image.gz modules apple/t6050-j716c.dtb > "$O/make.log" 2>&1
printf '{"build_seconds":%s,"native_ready":false}\n' "$(( $(date +%s)-start ))" > "$O/build-time.json"
cp arch/arm64/boot/Image.gz "$O/Image.gz"
cp arch/arm64/boot/Image "$O/Image"
cp arch/arm64/boot/dts/apple/t6050-j716c.dtb "$O/t6050-j716c.PRIVATE.dtb"
cp System.map "$O/System.map"
make LLVM=1 LOCALVERSION= kernelrelease > "$O/kernelrelease.txt"
make LLVM=1 LOCALVERSION= INSTALL_MOD_PATH="$W/modules" INSTALL_MOD_STRIP=1 modules_install > "$O/modules-install.log" 2>&1
python3 -I - "$W/modules" <<'PY'
from pathlib import Path
import sys
for directory in (Path(sys.argv[1])/'lib/modules').iterdir():
 for name in ('build','source'):
  link=directory/name
  if link.is_symlink():link.unlink()
PY
tar -C "$W/modules" --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner -cf - lib | gzip -n > "$O/modules.PRIVATE.tar.gz"
python3 -I "$R/check_artifacts.py" "$O" "$W/modules" > "$O/artifact-validation.json"
pacman -Q > "$O/packages-after.txt"
cmp "$O/packages-before.txt" "$O/packages-after.txt"
sha256sum "$O/Image.gz" "$O/Image" "$O/kernel.config" "$O/t6050-j716c.PRIVATE.dtb" "$O/modules.PRIVATE.tar.gz" > "$O/artifacts.sha256"
printf '%s\n' 'J716C_MATCHED_BUILD_PASS_OFFLINE_ONLY'
