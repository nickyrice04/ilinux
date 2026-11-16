#!/bin/bash
# SPDX-License-Identifier: MIT
# Guest entrypoint. The retained VM's existing job service owns shutdown.
set -euo pipefail
J=/mnt/job O=/mnt/job/out W=/var/tmp/ilinux-j716c097
for share in inputs kernel-inputs cargo-crates fatfs-packs gpu-support; do
    mkdir -p "/mnt/$share"
    mountpoint -q "/mnt/$share" || mount -t virtiofs "$share" "/mnt/$share"
done
mkdir -p "$O" "$W"
exec > "$O/run-detail.log" 2>&1
test "$(uname -s)/$(uname -m)" = Linux/aarch64
test "$(ls /sys/class/net)" = lo
test ! -L "$W"
test -z "$(ls -A "$W")"
if mountpoint -q "$W"; then exit 3; fi
python3 -I - "$O/environment.json" <<'PY'
import json,os,platform,sys
from pathlib import Path
values={line.split(':')[0]:int(line.split(':')[1].split()[0])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line}
if values['MemTotal']<47*1024**3 or values['MemAvailable']<43*1024**3:
    raise SystemExit('INSUFFICIENT_VM_MEMORY')
Path(sys.argv[1]).write_text(json.dumps({'schema':'ilinux097-build-environment-v1',
 'os':platform.system(),'kernel':platform.release(),'arch':platform.machine(),'virtual_cpus':os.cpu_count(),
 'memory_total_bytes':values['MemTotal'],'memory_available_bytes':values['MemAvailable'],
 'tmpfs_limit_bytes':32*1024**3,'network_interfaces':['lo'],'native_gpu_exposed':False},indent=2)+'\n')
PY
mount -t tmpfs -o size=32G,nodev,nosuid,mode=0700 ilinux097-build "$W"
cleanup() {
    code=$?
    pacman -Q > "$O/packages-after.txt"
    if ! cmp "$O/packages-before.txt" "$O/packages-after.txt"; then code=96; fi
    sync
    umount "$W" || code=97
    printf '%s\n' "$code" > "$O/guest-exit.txt"
    exit "$code"
}
pacman -Q > "$O/packages-before.txt"
trap cleanup EXIT
mkdir "$W/tmp"
export TMPDIR="$W/tmp" ILINUX_BUILD_JOBS=8
python3 -I "$J/test_sources.py" > "$O/archive-boundary-tests.log" 2>&1
python3 -I "$J/test_tree.py" > "$O/source-tree-tests.log" 2>&1
python3 -I "$J/stack-guards/test_validate.py" > "$O/stack-validation-tests.log" 2>&1
python3 -I "$J/stack-guards/test_package_guard.py" > "$O/stack-package-guard-tests.log" 2>&1
python3 -I "$J/stack-guards/test_lease.py" > "$O/stack-lease-tests.log" 2>&1
python3 -I - "$J" > "$O/source-tree-proof.json" <<'PY'
import importlib.util,json,sys
from pathlib import Path
j=Path(sys.argv[1]);s=importlib.util.spec_from_file_location('tree',j/'source_tree.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
pins=json.loads((j/'sources.json').read_text())['sources']
print(json.dumps({p['name']:m.verify(Path('/mnt/inputs')/p['filename'],p['git_tree'],p['name']=='mesa') for p in pins},sort_keys=True))
PY
python3 -I "$J/validate_sources.py" "$J/sources.json" /mnt/inputs \
    --extract "$W/source" > "$O/source-admission.json"
# Reuse the exact authenticated kernel lane preparer; it also unpacks the
# retained public kernel source as data, which is not built by this job.
python3 -I "$J/kernel-prepare.py" /mnt/kernel-inputs "$W/prepared" "$O"
source "$W/prepared/environment.sh"
T="$W/prepared/toolchain"
python3 -I - "$J" "$T" <<'PY'
import hashlib,importlib.util,json,sys,tarfile,tomllib
from pathlib import Path
j,t=map(Path,sys.argv[1:]);pin=json.loads((j/'cargo-inputs.json').read_text())['cargo_component']
manifest=tomllib.loads(Path('/mnt/kernel-inputs/channel-rust-1.96.1.toml').read_text())
entry=manifest['pkg']['cargo']['target']['aarch64-unknown-linux-gnu']
if entry['xz_url']!=pin['xz_url'] or entry['xz_hash']!=pin['xz_hash']:raise ValueError('CARGO_SIGNED_MANIFEST_BINDING')
p=Path('/mnt/inputs')/pin['filename']
if p.stat().st_size!=pin['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=pin['xz_hash']:raise ValueError('CARGO_COMPONENT_HASH')
spec=importlib.util.spec_from_file_location('prepare',j/'kernel-prepare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.extract(p,t/'rust','cargo')
wrapper=t/'bin/cargo';wrapper.write_text('#!/bin/sh\nunset LD_LIBRARY_PATH\nexec '+str(t/'rust/bin/cargo')+' "$@"\n');wrapper.chmod(0o700)
PY
python3 -I "$J/seed_cargo.py" "$J/cargo-inputs.json" /mnt/cargo-crates \
    /mnt/inputs/crates /mnt/fatfs-packs "$W/cargo" > "$O/cargo-vendor.json"
export CARGO_HOME="$W/cargo/cargo-home"
export PATH="$T/bin:$T/usr/lib/llvm22/bin:$T/rust/bin:/usr/bin:/bin"
export LIBCLANG_PATH="$T/usr/lib/llvm22/lib"
# clang++ and LLVM-linked tools not wrapped by the kernel lane use this
# isolated loader scope. Its rustc/cargo wrappers explicitly unset it.
export LD_LIBRARY_PATH="$T/usr/lib/llvm22/lib:$T/usr/lib"
{
    clang --version | head -1
    rustc --version
    cargo --version
    llvm-config --version
} > "$O/graphics-toolchain.txt"
test "$(cargo --version | cut -d' ' -f2)" = 1.96.1
set +e
bash "$J/build-aura.sh" "$W/source/aura-9da61857f9d9262bd64c023fbc1b18315b12d0af" \
    "$W/aura-work" "$O/aura" "$J/aura-helpers" > "$O/aura-phase.log" 2>&1
ARC=$?
set -e
printf '%s\n' "$ARC" > "$O/aura-exit.txt"
python3 -I "$J/prepare_support.py" "$J" /mnt/gpu-support "$W/prepared/alarm-verification" \
    "$W/support" "$O/support-authentication.json"
export PKG_CONFIG_PATH="$W/support/usr/lib/pkgconfig:$W/support/usr/share/pkgconfig"
export LD_LIBRARY_PATH="$W/support/usr/lib:$LD_LIBRARY_PATH"
export PATH="$W/support/usr/bin:$PATH"
export CC=clang CXX=clang++ LLVM_CONFIG="$T/bin/llvm-config"
set +e
bash "$J/build-mesa.sh" "$W/source/mesa-10161a78e60e4057257e116d404a92bd9b78bb3c" \
    "$W/source/SPIRV-LLVM-Translator-ae707ecba4b0c64d85f4f7bdcabeb1fa152c0ab2" \
    "$W/mesa-work" "$O/mesa" "$T" \
    "$W/source/SPIRV-Headers-cb42dec3830d3ac67fa449ecdc0c0f73d5e74498" > "$O/mesa-phase.log" 2>&1
MRC=$?
set -e
printf '%s\n' "$MRC" > "$O/mesa-exit.txt"
python3 -I - "$ARC" "$MRC" "$O/summary.json" <<'PY'
import json,sys
from pathlib import Path
result={'schema':'ilinux097-offline-build-v1','aura_exit':int(sys.argv[1]),'mesa_exit':int(sys.argv[2]),
 'aura_build':'PASS' if sys.argv[1]=='0' else 'FAILED_OR_BLOCKED',
 'mesa_build':'PASS' if sys.argv[2]=='0' else 'FAILED_OR_BLOCKED',
 'case_sensitive_tmpfs':True,'network':False,'package_installations':0,
 'native_gpu_tested':False,'stage1_enrolled':False,'performance_parity_measured':False,'restart_ready':False}
mesa_result=Path(sys.argv[3]).parent/'mesa/result.json'
if (mesa_result.parent/'compilation-result.txt').is_file():
    result['mesa_build']='PASS'
if mesa_result.is_file():
    actual=json.loads(mesa_result.read_text())
    result['mesa_build']=actual['source_build']
    result['mesa_tests']=actual['tests']
    result['mesa_artifacts_retained']=True
Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')
PY
if test "$ARC" != 0 || test "$MRC" != 0; then exit 1; fi
