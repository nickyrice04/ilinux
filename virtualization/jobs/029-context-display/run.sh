#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
SRC=/var/tmp/ilinux-boot028/linux
WORK=/var/tmp/ilinux-boot029/linux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/context-display
mkdir -p "$OUT/export" /var/tmp/ilinux-boot029
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = 514dde0c48c17d77d1979fb98b13f5ecb45096839e8b10a72d24adcf9df0778f
test ! -e "$WORK"
cp -a --reflink=auto "$SRC" "$WORK"
python3 -I "$EXP/apply.py" "$WORK"
python3 -I - "$SRC" "$WORK" "$OUT" <<'PY'
from pathlib import Path
import sys
src,work,out=map(Path,sys.argv[1:])
s=(src/'drivers/firmware/efi/ilinux_earlycon.c').read_text()
(out/'baseline-map.h').write_text(s[s.index('static int __init fb_remap(void)'):s.index('early_initcall(fb_remap);')])
s=(work/'drivers/firmware/efi/ilinux_earlycon.c').read_text()
(out/'tested-parser.h').write_text(s[s.index('static const void * __init prop('):s.index('static __ref void *map_row(')])
PY
sed '/^#include /d' "$EXP/ilinux_probe_diag.h" > "$OUT/tested-diag.h"
FLAGS=(-std=gnu11 -O1 -g -Wall -Wextra -Werror -Wno-unused-function -fsanitize=address,undefined -fno-omit-frame-pointer)
gcc "${FLAGS[@]}" -I"$OUT" "$EXP/test_diag.c" -o "$OUT/test-diag"
"$OUT/test-diag"
gcc "${FLAGS[@]}" -I"$EXP" "$EXP/test_strip.c" -o "$OUT/test-strip"
"$OUT/test-strip"
# Use the retained kernel's libfdt source, not a host-installed backend.
FDT="$WORK/scripts/dtc/libfdt"
gcc "${FLAGS[@]}" -I"$OUT" -I"$EXP" -I"$FDT" "$EXP/test_map.c" "$FDT/fdt.c" "$FDT/fdt_ro.c" "$FDT/fdt_rw.c" "$FDT/fdt_wip.c" "$FDT/fdt_sw.c" "$FDT/fdt_empty_tree.c" "$FDT/fdt_strerror.c" -o "$OUT/test-map"
"$OUT/test-map"
gcc "${FLAGS[@]}" -DTEST_BASELINE -I"$OUT" -I"$EXP" -I"$FDT" "$EXP/test_map.c" "$FDT/fdt.c" "$FDT/fdt_ro.c" "$FDT/fdt_rw.c" "$FDT/fdt_wip.c" "$FDT/fdt_sw.c" "$FDT/fdt_empty_tree.c" "$FDT/fdt_strerror.c" -o "$OUT/test-baseline"
"$OUT/test-baseline"
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot028/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
cmp "$SRC/.config" "$WORK/.config"
objcopy -O binary "$WORK/vmlinux" "$OUT/roundtrip.bin"
cmp "$OUT/export/Image" "$OUT/roundtrip.bin"
nm -S -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
for f in deferred_probe_initcall ilinux_probe_sched_mark ilinux_probe_fb_mark __schedule __switch_to fb_remap; do objdump -d --disassemble="$f" "$WORK/vmlinux" > "$OUT/$f.txt"; done
cp "$WORK/kernel/sched/core.c" "$OUT/patched-core.c"
cp "$WORK/arch/arm64/kernel/process.c" "$OUT/patched-process.c"
cp "$WORK/drivers/firmware/efi/ilinux_earlycon.c" "$OUT/patched-earlycon.c"
{ uname -srm; gcc --version | head -1; ld --version | head -1; } > "$OUT/toolchain.txt"
echo 'PASS: boot028 preserved; boot029 full Image and ELF roundtrip pass'
