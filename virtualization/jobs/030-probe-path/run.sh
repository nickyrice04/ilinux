#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
SRC=/var/tmp/ilinux-boot029/linux
WORK=/var/tmp/ilinux-boot030/linux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/probe-path
mkdir -p "$OUT/export" /var/tmp/ilinux-boot030
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = 53f5f2c5a7a2d9d0d2ae92961222090c97f0c266bb4066408acd577660e7cc32
test ! -e "$WORK"
cp -a --reflink=auto "$SRC" "$WORK"
python3 -I "$EXP/apply.py" "$WORK"
python3 -I - "$WORK" "$OUT" <<'PY'
from pathlib import Path
import sys
work,out=map(Path,sys.argv[1:])
s=(work/'drivers/firmware/efi/ilinux_earlycon.c').read_text()
(out/'tested-parser.h').write_text(s[s.index('static const void * __init prop('):s.index('static __ref void *map_row(')])
s=(work/'drivers/base/platform.c').read_text();a=s.index('static int platform_probe(struct device *_dev)');b=s.index('\n}\n',a)+3
(out/'tested-platform.h').write_text(s[a:b])
PY
sed '/^#include </d' "$WORK/drivers/base/ilinux_probe_diag.h" > "$OUT/tested-diag.h"
cp "$WORK/drivers/base/ilinux-path-state.h" "$WORK/drivers/base/ilinux-device-identities.h" "$OUT/"
cp "$WORK/drivers/firmware/efi/ilinux-fb-map.h" "$OUT/fb-map.h"
FLAGS=(-std=gnu11 -O1 -g -Wall -Wextra -Werror -Wno-unused-function -fsanitize=address,undefined -fno-omit-frame-pointer)
for name in diag panel path platform; do
 gcc "${FLAGS[@]}" -I"$OUT" -I"$EXP" "$EXP/test_$name.c" -o "$OUT/test-$name"
 "$OUT/test-$name"
done
FDT="$WORK/scripts/dtc/libfdt"
gcc "${FLAGS[@]}" -I"$OUT" -I"$EXP" -I"$FDT" "$EXP/test_map.c" "$FDT/fdt.c" "$FDT/fdt_ro.c" "$FDT/fdt_rw.c" "$FDT/fdt_wip.c" "$FDT/fdt_sw.c" "$FDT/fdt_empty_tree.c" "$FDT/fdt_strerror.c" -o "$OUT/test-map"
"$OUT/test-map"
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot029/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
cmp "$SRC/.config" "$WORK/.config"
objcopy -O binary "$WORK/vmlinux" "$OUT/roundtrip.bin"
cmp "$OUT/export/Image" "$OUT/roundtrip.bin"
nm -S -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
for f in bus_probe_device platform_probe ilinux_probe_path_mark ilinux_probe_fb_mark; do objdump -d --disassemble="$f" "$WORK/vmlinux" > "$OUT/$f.txt"; done
for f in dd.c bus.c platform.c ilinux_probe_diag.h; do cp "$WORK/drivers/base/$f" "$OUT/patched-$f"; done
{ uname -srm; gcc --version | head -1; ld --version | head -1; } > "$OUT/toolchain.txt"
echo 'PASS: boot029 preserved; boot030 full Image and ELF roundtrip pass'
