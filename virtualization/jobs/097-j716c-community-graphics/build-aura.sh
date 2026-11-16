#!/bin/bash
# SPDX-License-Identifier: MIT
# Public source executes only inside the offline ARM64 Linux VM.
set -euo pipefail
test "$(uname -s)/$(uname -m)" = Linux/aarch64
test "$#" = 4
source_tree=$(realpath "$1") work=$(realpath -m "$2") out=$(realpath -m "$3") helpers=$(realpath "$4")
test ! -e "$work"
mkdir -p "$work" "$out"
export SOURCE_DATE_EPOCH=1794338095 CARGO_NET_OFFLINE=true RUSTC_BOOTSTRAP=1
jobs=${ILINUX_BUILD_JOBS:-8}
[[ "$jobs" =~ ^[1-8]$ ]]
for variant in stage1 graphics-stage2; do
    cp -a "$source_tree" "$work/$variant"
    dest="$out/$variant"; mkdir -p "$dest"
    export AURA_VERSION_TAG="$(cat "$source_tree/VERSION")-g9da61857f9d9-ilinux097-$variant"
    flags=(USE_CLANG=1 BUILDSTD=1 CHAINLOADING=1 OBJCOPY=objcopy
           'CARGO_FLAGS=-Z build-std=alloc,core --locked --offline --features chainload')
    if test "$variant" = stage1; then
        flags+=(RELEASE=1 ESP_STAGE2=0)
    else
        flags+=(ESP_STAGE2=1 DEBUGUSB_PROXY=1)
    fi
    printf '%q ' make -j"$jobs" "${flags[@]}" all > "$dest/command.txt"
    printf '\n' >> "$dest/command.txt"
    make -C "$work/$variant" -j"$jobs" "${flags[@]}" all > "$dest/build.log" 2>&1
    for name in aura.macho aura.bin aura-boot.macho aura.elf aura-raw.elf build_cfg.h build_tag.h; do
        cp "$work/$variant/build/$name" "$dest/"
    done
    llvm-readelf -h -s "$dest/aura-raw.elf" > "$dest/elf-metadata.txt"
    if test "$variant" = stage1; then
        python3 -I "$helpers/pad_boot.py" "$dest/aura-boot.macho" \
            "$dest/aura-boot-128m.macho" > "$dest/padding.json"
    fi
done
python3 -I "$helpers/test_pad_boot.py" --wrapper "$source_tree/tools/macho_boot_object.py" \
    > "$out/padding-tests.log" 2>&1
mkdir -p "$out/licenses"
cp "$source_tree/LICENSE" "$out/licenses/Aura-LICENSE"
cp -a "$source_tree/LICENSES" "$source_tree/3rdparty_licenses" "$out/licenses/"
cp "$source_tree/docs/licensing.md" "$out/licenses/Aura-licensing.md"
cargo metadata --manifest-path "$work/stage1/rust/Cargo.toml" --features chainload \
    --format-version 1 --filter-platform aarch64-unknown-none-softfloat --locked --offline \
    > "$work/cargo-metadata.private.json"
python3 -I "$helpers/collect_cargo_licenses.py" "$work/cargo-metadata.private.json" \
    "$out/licenses/cargo" > "$out/cargo-notices.json"
python3 -I "$(dirname "$0")/collect_rust_notices.py" /mnt/kernel-inputs "$out/licenses/rust-build-std" \
    > "$out/rust-notices.json"
python3 -I - "$out" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]); variants={}
for variant in ('stage1','graphics-stage2'):
    variants[variant]={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                       for p in (out/variant).iterdir() if p.is_file() and p.suffix in ('.bin','.macho','.elf','.h')}
result={'schema':'ilinux097-aura-build-v1','revision':'9da61857f9d9262bd64c023fbc1b18315b12d0af',
 'source_date_epoch':1794338095,'variants':variants,
 'toolchain':{x:subprocess.check_output([x,'--version'],text=True).splitlines()[0]
              for x in ('clang','ld.lld','rustc','cargo','objcopy')},
 'stage1_identity':'NEW_GENERIC_CANDIDATE_NOT_PUBLISHER_INSTALLED_IDENTITY',
 'enrolled':False,'native_tested':False,'restart_ready':False}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
PY
