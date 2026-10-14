#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux /mnt/m1n1-source
mount -t virtiofs ilinux /mnt/ilinux
mount -t virtiofs m1n1-source /mnt/m1n1-source
OUT=/mnt/job/out
mkdir -p "$OUT"
BASE=/var/tmp/ilinux-boot021/m1n1
test "$(git -C "$BASE" rev-parse HEAD)" = 57a9339ffd1876e78297b17d34dece8cff8fa1ba
test -z "$(git -C "$BASE" status --porcelain --untracked-files=no)"
sha256sum "$BASE/build/m1n1.bin"
test "$(sha256sum "$BASE/build/m1n1.bin" | cut -d' ' -f1)" = ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664
cp "$BASE/build/m1n1-raw.elf" "$OUT/m1n1-raw.elf"
objcopy -O binary "$OUT/m1n1-raw.elf" "$OUT/elf-roundtrip.bin"
cmp "$BASE/build/m1n1.bin" "$OUT/elf-roundtrip.bin"
objdump -d --start-address=0x160e0 --stop-address=0x16620 "$OUT/m1n1-raw.elf" > "$OUT/dapf-disassembly.txt"
addr2line -fe "$OUT/m1n1-raw.elf" 0x16458 > "$OUT/pc-source.txt"
nm -an "$OUT/m1n1-raw.elf" > "$OUT/symbols.txt"
sha256sum "$OUT/m1n1-raw.elf" > "$OUT/elf-sha256.txt"
cat "$OUT/pc-source.txt"
echo 'PASS: retained ELF reproduces exact installed raw image'

WORK=$(mktemp -d /var/tmp/ilinux-boot023-dapf.XXXXXX)
cp -a "$BASE/." "$WORK/"
test -z "$(git -C "$WORK" status --porcelain --untracked-files=no)"
git -C "$WORK" apply /mnt/ilinux/kernel/experiments/dapf-handoff/m1n1-instance-guard.patch
cp /mnt/ilinux/kernel/experiments/dapf-handoff/ilinux_dapf_layout.h "$WORK/src/"
mkdir -p "$OUT/baseline" "$OUT/corrected"
for variant in baseline corrected; do
  if [ "$variant" = baseline ]; then SRC="$BASE"; else SRC="$WORK"; fi
  sed '/^#include /d' "$SRC/src/dapf.c" > "$OUT/$variant/tested-dapf.c"
  # The original helper is included separately because upstream includes are stubbed.
  if [ "$variant" = corrected ]; then
    cp "$WORK/src/ilinux_dapf_layout.h" "$OUT/$variant/"
    sed -i '1i#include "ilinux_dapf_layout.h"' "$OUT/$variant/tested-dapf.c"
  fi
  gcc -std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
    -fno-omit-frame-pointer -I"$OUT/$variant" \
    /mnt/ilinux/kernel/experiments/dapf-handoff/test_dapf.c -o "$OUT/$variant/test-dapf"
  "$OUT/$variant/test-dapf" "$variant" > "$OUT/$variant/tests.txt"
done
(
 cd "$WORK"
 M1N1_VERSION_TAG=ilinux-57a9339-dapf-guard make -j2 ARCH= BUILDSTD=1
) > "$OUT/patched-build.log" 2>&1
cp "$WORK/build/m1n1.bin" "$OUT/m1n1-source-guard.bin"
python3 -I /mnt/ilinux/native/boot/test_launcher.py
python3 -I /mnt/ilinux/native/boot/test_dapf_guard.py
M1N1_SOURCE=/mnt/m1n1-source python3 -I /mnt/ilinux/native/boot/test_dapf_guard_adt.py
M1N1_SOURCE=/mnt/m1n1-source python3 -I /mnt/ilinux/native/boot/test_launcher_adt.py
python3 -I /mnt/ilinux/native/boot/test_framebuffer.py
M1N1_SOURCE=/mnt/m1n1-source python3 -I /mnt/ilinux/native/boot/test_protocol.py
{ uname -srm; gcc --version | head -1; python3 --version; } > "$OUT/test-toolchain.txt"
echo 'PASS: exact binary, source guard, full m1n1 build and RAM workaround tests'
