#!/bin/bash
# SPDX-License-Identifier: MIT
# No network, global installation, physical GPU or firmware access.
set -euo pipefail
test "$(uname -s)/$(uname -m)" = Linux/aarch64
test "$#" = 6
mesa=$(realpath "$1") translator=$(realpath "$2") work=$(realpath -m "$3") out=$(realpath -m "$4") prefix=$(realpath "$5") headers=$(realpath "$6")
mkdir -p "$work" "$out"
jobs=${ILINUX_BUILD_JOBS:-8}
[[ "$jobs" =~ ^[1-8]$ ]]
export SOURCE_DATE_EPOCH=1794338095
cmake -G Ninja -S "$translator" -B "$work/translator-build" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$work/translator-prefix" \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
    -DLLVM_DIR="$prefix/usr/lib/llvm22/lib/cmake/llvm" \
    -DLLVM_EXTERNAL_SPIRV_HEADERS_SOURCE_DIR="$headers" \
    -DLLVM_SPIRV_INCLUDE_TESTS=OFF -DLLVM_SPIRV_ENABLE_LIBSPIRV_DIS=ON \
    -DLLVM_LINK_LLVM_DYLIB=ON -DBUILD_SHARED_LIBS=ON \
    -DFETCHCONTENT_FULLY_DISCONNECTED=ON > "$out/translator-configure.log" 2>&1
ninja -C "$work/translator-build" -j"$jobs" > "$out/translator-build.log" 2>&1
ninja -C "$work/translator-build" install > "$out/translator-install.log" 2>&1
export PATH="$work/translator-prefix/bin:$PATH"
export LD_LIBRARY_PATH="$work/translator-prefix/lib:${LD_LIBRARY_PATH:-}"
export PKG_CONFIG_PATH="$work/translator-prefix/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
# A generated original kernel verifies both directions of the newly built tool.
cat > "$work/translator-smoke.cl" <<'CL'
__kernel void ilinux097_store(__global int *output) { output[0] = 42; }
CL
clang -cc1 -triple spir64 -emit-llvm-bc -x cl -cl-std=CL1.2 \
    "$work/translator-smoke.cl" -o "$work/translator-smoke.bc"
llvm-spirv --spirv-max-version=1.0 "$work/translator-smoke.bc" -o "$work/translator-smoke.spv"
spirv-val --target-env opencl1.2 "$work/translator-smoke.spv"
llvm-spirv -r "$work/translator-smoke.spv" -o "$work/translator-reversed.bc"
llvm-dis "$work/translator-reversed.bc" -o "$out/translator-reversed.ll"
grep -q 'define.*spir_kernel.*ilinux097_store' "$out/translator-reversed.ll"
{
    llvm-config --version
    pkg-config --modversion LLVMSPIRVLib SPIRV-Tools libdrm
    clang --version | head -1
    meson --version
    ninja --version
} > "$out/toolchain.txt"
B="$work/mesa-build"
MESON=(meson setup "$B" "$mesa" --prefix=/usr --libdir=lib --wrap-mode=nodownload \
    --buildtype=debugoptimized -Db_ndebug=false -Dgallium-drivers=asahi -Dvulkan-drivers=asahi \
    -Dplatforms=wayland -Dglx=disabled -Degl=enabled -Dgbm=enabled \
    -Dgles1=disabled -Dgles2=enabled -Dopengl=true -Dglvnd=disabled \
    -Dbuild-tests=true -Dtools=drm-shim -Dllvm=enabled -Dshared-llvm=enabled \
    -Dmesa-clc=enabled -Dgallium-va=disabled -Dvideo-codecs= \
    -Dvalgrind=disabled -Dlibunwind=disabled -Dlmsensors=disabled \
    -Dperfetto=false -Dallow-fallback-for=)
printf '%q ' "${MESON[@]}" > "$out/configure-command.txt"
printf '\n' >> "$out/configure-command.txt"
"${MESON[@]}" > "$out/mesa-configure.log" 2>&1
ninja -C "$B" -j"$jobs" > "$out/mesa-build.log" 2>&1
printf '%s\n' MESA_FULL_SOURCE_BUILD_PASS > "$out/compilation-result.txt"
set +e
meson test -C "$B" --print-errorlogs --suite asahi --num-processes="$jobs" \
    > "$out/mesa-tests.log" 2>&1
TRC=$?
set -e
cp "$B/meson-logs/testlog.json" "$out/mesa-testlog.json"
cp "$B/meson-logs/testlog.txt" "$out/mesa-testlog.txt"
cp "$B/meson-info/intro-buildoptions.json" "$out/mesa-buildoptions.json"
meson install -C "$B" --no-rebuild --destdir "$work/mesa-destdir" \
    > "$out/mesa-destdir.log" 2>&1
# Preserve the complete isolated output before validating its individual roles.
# Mesa26 installs one versioned Gallium library instead of old per-driver DRI
# aliases. Do not impose the packaging layout of the old job075 source.
tar -czf "$out/mesa-destdir.tar.gz" -C "$work/mesa-destdir" .
test -f "$work/mesa-destdir/usr/lib/libvulkan_asahi.so"
test -e "$work/mesa-destdir/usr/lib/libEGL.so"
test -e "$work/mesa-destdir/usr/lib/libgbm.so"
test -e "$work/mesa-destdir/usr/lib/libGLESv2.so"
test -f "$work/mesa-destdir/usr/lib/libgallium-26.3.0-devel.so"
llvm-readelf --dynamic "$work/mesa-destdir/usr/lib/libvulkan_asahi.so" \
    > "$out/vulkan-installed-dynamic.txt"
cp "$mesa/VERSION" "$out/mesa-version.txt"
cp -a "$mesa/licenses" "$out/mesa-licenses"
cp "$mesa/docs/license.rst" "$out/mesa-license.rst"
for name in LICENSE.txt LICENSE.TXT LICENSE; do
    if test -f "$translator/$name"; then cp "$translator/$name" "$out/translator-$name"; fi
done
# The baseline archive and full179-test receipts above are retained unchanged.
# A separate derivative tests the actual CPU transfer policy without enabling
# the unqualified AGX3 GPU conversion path or changing any shipping driver.
probe="$(dirname "$0")/blit-contract"
testcase="$mesa/src/gallium/drivers/asahi/tests/test-agx-g17p-blit.c"
cp "$testcase" "$work/blit-original.c"
rm -f "$B/meson-logs/testlog.json"
set +e
(
    set -e
    trap 'cp "$work/blit-original.c" "$testcase"' EXIT
    python3 -I "$probe/test_prepare.py" --source-root "$mesa" > "$out/blit-transform-tests.log" 2>&1
    python3 -I "$probe/prepare_test.py" --source-root "$mesa" \
        --output "$work/blit-test-derivative.c" > "$out/blit-derivative-source.json"
    cp "$work/blit-test-derivative.c" "$testcase"
    meson test -C "$B" --print-errorlogs --suite asahi --num-processes="$jobs"
) > "$out/blit-derivative-tests.log" 2>&1
DRC=$?
set -e
if test -f "$B/meson-logs/testlog.json"; then
    cp "$B/meson-logs/testlog.json" "$out/blit-derivative-testlog.json"
    cp "$B/meson-logs/testlog.txt" "$out/blit-derivative-testlog.txt"
fi
cmp "$testcase" "$work/blit-original.c"
printf '%s\n' "$DRC" > "$out/blit-derivative-exit.txt"
python3 -I - "$TRC" "$out" "$work/mesa-destdir" <<'PY'
from collections import Counter
import hashlib,json,sys
from pathlib import Path
rc=int(sys.argv[1]);out=Path(sys.argv[2]);dest=Path(sys.argv[3])
tests=[json.loads(line) for line in (out/'mesa-testlog.json').read_text().splitlines() if line.strip()]
results=Counter(t['result'] for t in tests)
artifacts={}
for name in ('usr/lib/libvulkan_asahi.so','usr/lib/libEGL.so','usr/lib/libgbm.so','usr/lib/libGLESv2.so','usr/lib/libgallium-26.3.0-devel.so'):
    p=dest/name;data=p.read_bytes();artifacts[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
tar=out/'mesa-destdir.tar.gz';h=hashlib.sha256()
with tar.open('rb') as stream:
    for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
result={'schema':'ilinux097-mesa-build-v1','source_commit':'10161a78e60e4057257e116d404a92bd9b78bb3c',
 'source_build':'PASS','tests':{'exit':rc,'counts':dict(results),'registered':len(tests),
                            'failed_names':[t['name'] for t in tests if t['result'] not in ('OK','SKIP')]},
 'libraries':artifacts,'destdir_tar':{'bytes':tar.stat().st_size,'sha256':h.hexdigest()},
 'shipping_source_modified':False,'native_gpu_tested':False,'package_installed':False,'restart_ready':False}
derivative=out/'blit-derivative-testlog.json'
result['test_only_derivative']={'exit':int((out/'blit-derivative-exit.txt').read_text()),
  'testlog_present':derivative.is_file(),'shipping_driver_changed':False,
  'baseline_result_unchanged':True,'native_gpu_tested':False}
if derivative.is_file():
    derived=[json.loads(line) for line in derivative.read_text().splitlines() if line.strip()]
    result['test_only_derivative'].update({'counts':dict(Counter(t['result'] for t in derived)),
      'registered':len(derived),'failed_names':[t['name'] for t in derived if t['result'] not in ('OK','SKIP')]})
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
PY
printf '%s\n' MESA_SOURCE_BUILD_PASS_TEST_RESULTS_RETAINED_NATIVE_NOT_RUN > "$out/result.txt"
exit "$TRC"
