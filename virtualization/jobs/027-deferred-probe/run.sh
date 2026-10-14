#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
SRC=/var/tmp/ilinux-boot025/linux
WORK=/var/tmp/ilinux-boot027-v3/linux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/deferred-probe
mkdir -p "$OUT/export" /var/tmp/ilinux-boot027-v3
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = 8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea
test ! -e "$WORK"
cp -a --reflink=auto "$SRC" "$WORK"
python3 -I "$EXP/apply.py" "$WORK"
sed '/^#include /d' "$EXP/ilinux_probe_diag.h" > "$OUT/tested-diag.h"
gcc -std=gnu11 -O1 -g -Wall -Wextra -Werror -Wno-unused-function -fsanitize=address,undefined -fno-omit-frame-pointer -I"$OUT" "$EXP/test_diag.c" -o "$OUT/test-diag"
"$OUT/test-diag"
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot025/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
cmp "$SRC/.config" "$WORK/.config"
objcopy -O binary "$WORK/vmlinux" "$OUT/roundtrip.bin"
cmp "$OUT/export/Image" "$OUT/roundtrip.bin"
nm -S -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
objdump -d --disassemble=deferred_probe_initcall "$WORK/vmlinux" > "$OUT/deferred-probe-initcall.txt"
cp "$WORK/drivers/base/dd.c" "$OUT/patched-dd.c"
{ uname -srm; gcc --version | head -1; ld --version | head -1; } > "$OUT/toolchain.txt"
echo 'PASS: boot025 preserved; boot027 full Image and ELF roundtrip pass'
