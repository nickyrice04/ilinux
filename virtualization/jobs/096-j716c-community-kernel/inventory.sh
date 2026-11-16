#!/bin/bash
# SPDX-License-Identifier: MIT
# Existing isolated Linux VM only. No install, source build, network or hardware.
set -euo pipefail
O=/mnt/job/out
mkdir -p "$O"
exec > "$O/inventory.log" 2>&1
test "$(ls /sys/class/net)" = lo
uname -srm
for tool in gcc clang ld.lld llvm-config rustc cargo bindgen make dtc python3; do
  if command -v "$tool" >/dev/null; then
    command -v "$tool"
    "$tool" --version 2>&1 | head -3 || true
  else
    printf 'MISSING %s\n' "$tool"
  fi
done
rustc -vV 2>/dev/null || true
pacman -Q gcc clang llvm llvm-libs lld rust rust-src rust-bindgen glibc linux-api-headers 2>&1 || true
python3 -I - "$O/inventory.json" <<'PY'
import json,os,subprocess,sys,tempfile
from pathlib import Path

def space(path):
 v=os.statvfs(path)
 return {'available_bytes':v.f_bavail*v.f_frsize,'total_bytes':v.f_blocks*v.f_frsize}

def case_probe(parent):
 with tempfile.TemporaryDirectory(prefix='ilinux096-case-',dir=parent) as directory:
  lower=Path(directory)/'caseprobe';upper=Path(directory)/'CASEPROBE'
  lower.write_bytes(b'lower');upper.write_bytes(b'upper')
  return lower.stat().st_ino!=upper.stat().st_ino and lower.read_bytes()==b'lower' and upper.read_bytes()==b'upper'

result={'schema':'ilinux096-guest-inventory-v1','scope':'EXISTING_LINUX_BUILD_VM_ONLY',
 'interfaces':sorted(p.name for p in Path('/sys/class/net').iterdir()),
 'root':space('/'),'job':space('/mnt/job'),'tmp':space('/tmp'),
 'root_case_sensitive':case_probe('/tmp'),'job_case_sensitive':case_probe('/mnt/job'),
 'memory':{},'package_cache':[],'rustup_toolchains':[],'native_hardware_tested':False,
 'package_installations':0,'source_builds':0}
for line in Path('/proc/meminfo').read_text().splitlines():
 key,_,value=line.partition(':')
 if key in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):result['memory'][key]=value.strip()
cache=Path('/var/cache/pacman/pkg')
if cache.exists():
 for p in cache.iterdir():
  if p.is_file() and p.name.startswith(('clang-','llvm-','llvm-libs-','lld-','rust-','rust-src-','rust-bindgen-')):
   result['package_cache'].append({'name':p.name,'bytes':p.stat().st_size})
toolchains=Path('/root/.rustup/toolchains')
if toolchains.is_dir():result['rustup_toolchains']=sorted(p.name for p in toolchains.iterdir() if p.is_dir())
Path(sys.argv[1]).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
PY
findmnt -no TARGET,FSTYPE,OPTIONS / /mnt/job /tmp 2>/dev/null || true
printf '%s\n' 'ILINUX096_INVENTORY_COMPLETE_NO_BUILD'
