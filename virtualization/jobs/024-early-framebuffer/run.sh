#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
SRC=/var/tmp/t6050-build/linux
WORK=/var/tmp/ilinux-boot024/linux
mkdir -p "$OUT/export" /var/tmp/ilinux-boot024
test -z "$(git -C "$SRC" status --porcelain --untracked-files=no)"
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = f9cf7c0046712cdf60e686e7a13d998b3e4d1b55a1d64de5dba997aa9a77f704
if [ ! -e "$WORK" ]; then
 cp -a --reflink=auto "$SRC" "$WORK"
else
 test "$(git -C "$WORK" rev-parse HEAD)" = "$(git -C "$SRC" rev-parse HEAD)"
 # Only reset the two files this isolated job modifies, from the verified baseline.
 cp "$SRC/arch/arm64/kernel/head.S" "$WORK/arch/arm64/kernel/head.S"
 cp "$SRC/drivers/firmware/efi/Makefile" "$WORK/drivers/firmware/efi/Makefile"
fi
EXP=/mnt/ilinux/kernel/experiments/early-framebuffer
python3 -I "$EXP/apply.py" "$WORK"
sed '/^#include /d' "$EXP/ilinux_earlycon.c" > "$OUT/tested-earlycon.c"
gcc -std=gnu11 -O1 -g -Wall -Wextra -Wno-unused-parameter -Werror \
 -fsanitize=address,undefined -fno-omit-frame-pointer -I"$OUT" \
 "$EXP/test_earlycon.c" -lfdt -o "$OUT/test-earlycon"
"$OUT/test-earlycon"
gcc -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
 "$EXP/test_markers.c" "$EXP/test_markers.S" -o "$OUT/test-markers"
"$OUT/test-markers"
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot022/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
nm -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
objdump -d --disassemble=primary_entry "$WORK/vmlinux" > "$OUT/primary-entry.txt"
objdump -d --disassemble=fb_setup "$WORK/vmlinux" > "$OUT/earlycon-setup.txt"
git -C "$WORK" diff > "$OUT/kernel-tracked.patch"
python3 -I /mnt/ilinux/native/boot/test_launcher.py
python3 -I /mnt/ilinux/native/boot/test_entry_guard.py
python3 -I /mnt/ilinux/native/boot/test_dapf_guard.py
export M1N1_SOURCE=/var/tmp/ilinux-boot021/m1n1
python3 -I /mnt/ilinux/native/boot/test_dapf_guard_adt.py
python3 -I /mnt/ilinux/native/boot/test_launcher_adt.py
python3 -I /mnt/ilinux/native/boot/test_protocol.py
python3 -I /mnt/ilinux/native/boot/test_framebuffer.py
{ uname -srm; gcc --version | head -1; ld --version | head -1; } > "$OUT/toolchain.txt"
echo 'PASS: original image preserved; boot024 instrumentation linked'
