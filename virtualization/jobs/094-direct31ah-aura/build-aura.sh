#!/bin/bash
# SPDX-License-Identifier: MIT
# Run only inside the existing isolated Linux VM. Sources are immutable input.
set -euo pipefail
[[ $(uname -s) == Linux ]] || { echo 'Linux VM required' >&2; exit 2; }
[[ $# == 3 ]] || { echo 'usage: build-aura.sh SOURCE_TREE WORK_DIRECTORY OUTPUT_DIRECTORY' >&2; exit 2; }
source_tree=$(realpath "$1")
work=$(realpath -m "$2")
output=$(realpath -m "$3")
here=$(cd "$(dirname "$0")" && pwd)
project=$(cd "$here/../../.." && pwd)
experiment="$project/kernel/experiments/direct31ah/aura"
[[ -f "$source_tree/Makefile" && -f "$source_tree/rust/Cargo.lock" ]] || exit 2
[[ ! -e "$work/baseline" && ! -e "$work/j716c-proxy" ]] || {
    echo 'Refusing to reuse build trees' >&2; exit 2;
}
mkdir -p "$work/tmp" "$output"
export TMPDIR="$work/tmp" CARGO_NET_OFFLINE=true SOURCE_DATE_EPOCH=1794340013
jobs=${ILINUX_BUILD_JOBS:-4}
[[ "$jobs" =~ ^[1-9][0-9]?$ && "$jobs" -le 32 ]] || exit 2

python3 -I - "$source_tree" "$output/source-check.json" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1])
pins={'src/main.c':'85adae8f4179474b6c4d2ec18b9eab67a54f6651',
      'Makefile':'6b14c5164ea7e36dfbd85cd011feefd70ffe65a6',
      'rust/Cargo.toml':'f6977b7418bbfc2ea4a54f22df7f5085e98842d3',
      'rust/Cargo.lock':'b4abe322fa0d66b16ed47f2d4f491bc3979d7fea'}
for name,want in pins.items():
 b=(root/name).read_bytes()
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==want,name
Path(sys.argv[2]).write_text(json.dumps({'commit':'bd9f3e8273dc79ae9095c19c2c4f32218446ad4e',
 'selected_git_blobs':pins,'scope':'SELECTED_INPUT_PINS'},indent=2)+'\n')
PY

cp -a "$source_tree" "$work/baseline"
cp -a "$source_tree" "$work/j716c-proxy"
patch --batch --fuzz=0 -d "$work/j716c-proxy" -p1 < "$experiment/j716c-proxy-usb2.patch"
cp "$experiment/proxy_policy.h" "$work/j716c-proxy/src/ilinux_proxy_policy.h"

for variant in baseline j716c-proxy; do
    dest="$output/$variant"
    mkdir -p "$dest"
    flags=()
    [[ "$variant" != j716c-proxy ]] || flags+=(EXTRA_CFLAGS=-DILINUX_J716C_PROXY_USB2)
    release=$(cat "$work/$variant/VERSION")
    [[ "$release" =~ ^[A-Za-z0-9._-]+$ ]] || exit 2
    export AURA_VERSION_TAG="$release-gbd9f3e8273dc-direct31ah-$variant"
    # Plain development/proxy image. No ESP configuration, installed Stage 1,
    # SPTM hypervisor or experimental monitor flags are selected.
    # Arch's native GNU objcopy handles AArch64 ELF/binary inputs. LLVM's
    # compiler/linker packages do not necessarily ship llvm-objcopy.
    make -C "$work/$variant" -j"$jobs" USE_CLANG=1 ARCH=aarch64-linux-gnu BUILDSTD=1 OBJCOPY=objcopy \
        CARGO_FLAGS='-Z build-std=alloc,core --locked --offline' \
        "${flags[@]}" all > "$dest/build.log" 2>&1
    for file in aura.bin aura-boot.macho aura-raw.elf aura.elf build_cfg.h build_tag.h; do
        cp "$work/$variant/build/$file" "$dest/$file"
    done
    python3 -I "$experiment/pad_boot.py" "$dest/aura-boot.macho" \
        "$dest/aura-boot-128m.macho" > "$dest/padding.json"
done
mkdir -p "$output/licenses"
cp "$source_tree/LICENSE" "$output/licenses/Aura-LICENSE"
cp -a "$source_tree/LICENSES" "$output/licenses/"
cp -a "$source_tree/3rdparty_licenses" "$output/licenses/"
cp "$source_tree/docs/licensing.md" "$output/licenses/Aura-licensing.md"
cp "$experiment/pad_boot.py" "$output/licenses/pad_boot.py"
cp "$experiment/proxy_policy.h" "$output/licenses/proxy_policy.h"
cp "$experiment/j716c-proxy-usb2.patch" "$output/licenses/j716c-proxy-usb2.patch"
cp "$experiment/collect_cargo_licenses.py" "$output/licenses/collect_cargo_licenses.py"
cp "$experiment/collect_buildstd_licenses.py" "$output/licenses/collect_buildstd_licenses.py"
# Keep Cargo's absolute cache paths private. Export only notices and a sanitized
# active-graph index; optional dependencies absent from this build are excluded.
cargo metadata --manifest-path "$work/baseline/rust/Cargo.toml" --format-version 1 \
    --filter-platform aarch64-unknown-none-softfloat --locked --offline \
    > "$work/cargo-metadata.private.json"
python3 -I "$experiment/collect_cargo_licenses.py" "$work/cargo-metadata.private.json" \
    "$output/licenses/cargo" > "$output/cargo-notices-result.json"
python3 -I "$experiment/collect_buildstd_licenses.py" "$output/licenses/rust-build-std" \
    > "$output/rust-buildstd-notices-result.json"

cc -std=c11 -O2 -Wall -Wextra -Werror "$experiment/test_proxy_policy.c" \
   -o "$output/test-proxy-policy"
"$output/test-proxy-policy"
python3 -I "$experiment/test_pad_boot.py" --wrapper "$source_tree/tools/macho_boot_object.py" \
    > "$output/padding-tests.log" 2>&1
python3 -I - "$output" <<'PY'
from pathlib import Path
import hashlib,json,platform,subprocess,sys
out=Path(sys.argv[1]);variants={}
for variant in ('baseline','j716c-proxy'):
 p=out/variant
 variants[variant]={f.name:{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
                    for f in p.iterdir() if f.is_file() and f.suffix not in ('.log','.json')}
report={'schema':'ilinux-direct31ah-aura-build-v1','kernel':platform.release(),
 'source_commit':'bd9f3e8273dc79ae9095c19c2c4f32218446ad4e',
 'toolchain':{x:subprocess.check_output([x,'--version'],text=True).splitlines()[0]
              for x in ('clang','ld.lld','objcopy','rustc','cargo','python3')},
 'make_variables':{'USE_CLANG':'1','ARCH':'aarch64-linux-gnu','BUILDSTD':'1',
                   'OBJCOPY':'objcopy','CARGO_FLAGS':'-Z build-std=alloc,core --locked --offline'},
 'source_date_epoch':1794340013,
 'variants':variants,'native_tested':False,'enrolled':False,'restart_ready':False}
(out/'build-result.json').write_text(json.dumps(report,indent=2)+'\n')
PY
