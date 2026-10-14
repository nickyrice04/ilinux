#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
SRC=/var/tmp/ilinux-boot027-v3/linux
WORK=/var/tmp/ilinux-boot028/linux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/schedule-boundary
mkdir -p "$OUT/export" /var/tmp/ilinux-boot028
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = 5a5ca64eaf2c3389e9fca226d7244150edbc8975738fe11a9304c0c996e29b64
test ! -e "$WORK"
cp -a --reflink=auto "$SRC" "$WORK"
python3 -I "$EXP/apply.py" "$WORK"
sed '/^#include /d' "$EXP/ilinux_probe_diag.h" > "$OUT/tested-diag.h"
gcc -std=gnu11 -O1 -g -Wall -Wextra -Werror -Wno-unused-function -fsanitize=address,undefined -fno-omit-frame-pointer -I"$OUT" "$EXP/test_diag.c" -o "$OUT/test-diag"
"$OUT/test-diag"
gcc -std=gnu11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -I"$EXP" "$EXP/test_strip.c" -o "$OUT/test-strip"
"$OUT/test-strip"
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot027/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
cmp "$SRC/.config" "$WORK/.config"
objcopy -O binary "$WORK/vmlinux" "$OUT/roundtrip.bin"
cmp "$OUT/export/Image" "$OUT/roundtrip.bin"
nm -S -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
for f in deferred_probe_initcall ilinux_probe_sched_mark ilinux_probe_fb_mark __schedule; do objdump -d --disassemble="$f" "$WORK/vmlinux" > "$OUT/$f.txt"; done
cp "$WORK/kernel/sched/core.c" "$OUT/patched-core.c"
cp "$WORK/drivers/firmware/efi/ilinux_earlycon.c" "$OUT/patched-earlycon.c"
{ uname -srm; gcc --version | head -1; ld --version | head -1; } > "$OUT/toolchain.txt"
echo 'PASS: boot027 preserved; boot028 full Image and ELF roundtrip pass'
