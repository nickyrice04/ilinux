#!/bin/bash
# SPDX-License-Identifier: MIT
# VM-only public source build. Start with --no-net and public-only read-only shares.
# Never install a native kernel, load a GPU module, or access Apple hardware.
set -euo pipefail
J=/mnt/job S=/mnt/gpu31p-sources I=/mnt/ilinux O=/mnt/job/out W=/var/tmp/ilinux-gpu31p
mkdir -p "$S" "$I" "$O" "$W"
exec > "$O/run-detail.log" 2>&1
mountpoint -q "$S" || mount -t virtiofs gpu31p-sources "$S"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = aarch64 ]
# Require the requested offline VM rather than relying on launch notes.
python3 -I - > "$O/network-preflight.json" <<'PYNET'
import json
from pathlib import Path
names = sorted(p.name for p in Path("/sys/class/net").iterdir())
if names != ["lo"]:
    raise SystemExit("refusing VM with a non-loopback network interface")
print(json.dumps({"interfaces": names, "network_enabled": False}))
PYNET
df -B1 /var/tmp > "$O/guest-free-space.txt"
python3 -I "$J/verify-inputs.py" "$J" "$S" > "$O/input-hashes.json"
python3 -I "$J/test_package_space.py" > "$O/package-space-tests.log" 2>&1
python3 -I "$J/test_isolation.py" > "$O/isolation-tests.log" 2>&1
# Build in dedicated guest RAM, retaining the full prior disk build history.
# Reject an unexpected pre-existing mount or contents instead of hiding them.
python3 -I - "$W" > "$O/memory-preflight.json" <<'PYMEM'
import json,sys
from pathlib import Path
values = {}
for line in Path("/proc/meminfo").read_text().splitlines():
    name, value = line.split(":",1)
    values[name] = int(value.split()[0]) * 1024
if values["MemTotal"] < 11 * 1024**3 or values["MemAvailable"] < 9 * 1024**3:
    raise SystemExit("refusing insufficient guest RAM for six GiB build tmpfs")
work = Path(sys.argv[1])
if work.is_symlink() or any(work.iterdir()):
    raise SystemExit("refusing unexpected existing job work contents")
print(json.dumps({"mem_total_bytes": values["MemTotal"],
                  "mem_available_bytes": values["MemAvailable"],
                  "tmpfs_limit_bytes": 6 * 1024**3}))
PYMEM
if mountpoint -q "$W"; then echo UNEXPECTED_WORK_MOUNT; exit 3; fi
mount -t tmpfs -o size=6G,nodev,nosuid,mode=0700 gpu31p-build "$W"
[ "$(findmnt --noheadings --output FSTYPE --target "$W")" = tmpfs ]
# Temporary compiler files also stay in this bounded RAM filesystem.
mkdir -p "$W/tmp"
export TMPDIR="$W/tmp"
pacman -Q > "$O/packages-before.txt"
T=$W/toolchain
python3 -I "$J/isolate-toolchain.py" "$J" "$S" "$T" "$O/toolchain-verification.json"
# Existing Rust has exact runtime dependencies. Never mutate or bypass them.
# Tool/package files are used only from this authenticated, disposable prefix.
export GPU31P_TOOLCHAIN="$T"
mkdir -p "$W/bin"
cp "$J/llvm-config-relocated.py" "$W/bin/llvm-config"
chmod 0755 "$W/bin/llvm-config"
export PATH="$W/bin:$T/usr/bin:$PATH"
export LD_LIBRARY_PATH="$T/usr/lib"
export PKG_CONFIG_PATH="$T/usr/lib/pkgconfig:$T/usr/share/pkgconfig"
unset PKG_CONFIG_SYSROOT_DIR
export LLVM_CONFIG="$W/bin/llvm-config" CC=gcc CXX=g++
[ "$(llvm-config --prefix)" = "$T/usr" ]
[ "$(llvm-config --includedir)" = "$T/usr/include" ]
[ "$(llvm-config --libdir)" = "$T/usr/lib" ]
{
  llvm-config --prefix --includedir --libdir
  pkg-config --variable=prefix LLVMSPIRVLib
} > "$O/toolchain-paths.txt"
pacman -Q > "$O/packages-after.txt"
cmp "$O/packages-before.txt" "$O/packages-after.txt"
{
  uname -srm
  gcc --version | head -1
  g++ --version | head -1
  clang --version | head -1
  llvm-config --version
  env -u LD_LIBRARY_PATH /usr/bin/rustc --version
  bindgen --version
  meson --version
  ninja --version
  pkg-config --modversion LLVMSPIRVLib SPIRV-Tools gtest
} > "$O/toolchain.txt"
M=$W/mesa-87ac51d B=$W/mesa-build
# These are dedicated job075 guest directories; discard prior build inputs.
rm -rf -- "$M" "$B"
mkdir -p "$M"
tar --extract --gzip --file "$S/mesa-87ac51d.tar.gz" --directory "$M" --strip-components=1 --no-same-owner --no-same-permissions
# Every run starts from verified archives and records its exact configure flags.
MESON=(meson setup "$B" "$M" --wrap-mode=nodownload --buildtype=debugoptimized
  -Dgallium-drivers=asahi -Dvulkan-drivers= -Dplatforms=
  -Dglx=disabled -Degl=disabled -Dgbm=disabled -Dgles1=disabled -Dgles2=disabled
  -Dopengl=false -Dbuild-tests=true -Dtools= -Dllvm=enabled -Dshared-llvm=enabled
  -Dgallium-va=disabled -Dvideo-codecs= -Dvalgrind=disabled -Dlibunwind=disabled
  -Dlmsensors=disabled -Dperfetto=false -Dallow-fallback-for=)
printf '%q ' "${MESON[@]}" > "$O/configure-command.txt"
printf '\n' >> "$O/configure-command.txt"
"${MESON[@]}" > "$O/mesa-configure.log" 2>&1
ninja -C "$B" -j4 src/asahi/compiler/agx_tests src/asahi/compiler/agx_apple9_tiny_tool \
  src/asahi/layout/asahi_layout_tests src/asahi/lib/libasahi_tests > "$O/mesa-build.log" 2>&1
meson test -C "$B" --no-rebuild --print-errorlogs agx_tests asahi_layout_tests libasahi_tests > "$O/mesa-tests.log" 2>&1
cp "$B/meson-logs/testlog.json" "$O/mesa-testlog.json"
cp "$B/meson-info/intro-buildoptions.json" "$O/mesa-buildoptions.json"
cp "$B/src/asahi/compiler/agx_apple9_tiny_tool" "$O/"
sha256sum "$B/src/asahi/compiler/agx_tests" "$B/src/asahi/layout/asahi_layout_tests" \
  "$B/src/asahi/lib/libasahi_tests" "$B/src/asahi/compiler/libasahi_compiler.a" \
  "$O/agx_apple9_tiny_tool" > "$O/mesa-artifact-hashes.txt"
echo MESA_APPLE_GPU_COMPILER_AND_LAYOUT_TESTS_PASS_NATIVE_NOT_RUN
# Kernel compilation is a separately reported foundation check, never a claim
# that its T8132 device matching supports this machine's T6050/G17C hardware.
# An isolated LLVM prefix cannot qualify this guest's exact-version Rust
# toolchain. Do not compile a kernel with a silently mixed runtime family.
echo KERNEL_BUILD_SKIPPED_ISOLATED_MESA_TOOLCHAIN > "$O/kernel-build.log"
KRC=77
printf '%s\n' "$KRC" > "$O/kernel-exit.txt"
python3 -I - "$KRC" > "$O/summary.json" <<'PY'
import json,sys
print(json.dumps({'result':'MESA_BUILD_AND_TESTS_PASS', 'kernel_object_exit':int(sys.argv[1]),
 'kernel_status':('SKIPPED_ISOLATED_MESA_TOOLCHAIN' if int(sys.argv[1])==77 else 'PASS' if int(sys.argv[1])==0 else 'BLOCKED_OR_FAILED'),
 'native_operations':0,'native_gpu':'NOT_RUN','g17c_driver':'UNSUPPORTED_UNVERIFIED',
 'firmware_emulator':False,'installed_native_changes':False,
 'guest_package_changes':False,'compiler_location':'DEDICATED_TMPFS'},sort_keys=True))
PY
echo GPU31P_BUILD_COMPLETE
