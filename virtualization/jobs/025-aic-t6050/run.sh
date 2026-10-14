#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
SRC=/var/tmp/ilinux-boot024/linux
WORK=/var/tmp/ilinux-boot025/linux
EXP=/mnt/ilinux/kernel/experiments/aic-t6050
mkdir -p "$OUT/export" /var/tmp/ilinux-boot025
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = 6b683a2f52e769d1a23474b6807d009da8ad2e19d2168e62caba6cbbae240f7d
test "$(sha256sum "$SRC/drivers/irqchip/irq-apple-aic.c" | cut -d' ' -f1)" = d52ff497371f81b94af730792c9ea9fb2bf24d99cf7df6e8985351dd331c2287
if [ ! -e "$WORK" ]; then
 cp -a --reflink=auto "$SRC" "$WORK"
fi
cp "$SRC/drivers/irqchip/irq-apple-aic.c" "$WORK/drivers/irqchip/irq-apple-aic.c"
git -C "$WORK" apply --check "$EXP/t6050-bringup.patch"
git -C "$WORK" apply "$EXP/t6050-bringup.patch"
python3 -I "$EXP/extract-test.py" "$WORK/drivers/irqchip/irq-apple-aic.c" "$OUT/tested-aic.c"
gcc -std=gnu11 -O1 -g -Wall -Wextra -Wno-unused-parameter -Wno-unused-value -Wno-sign-compare -Werror \
 -fsanitize=address,undefined -fno-omit-frame-pointer -I"$OUT" \
 "$EXP/test_aic.c" -o "$OUT/test-aic"
"$OUT/test-aic"
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot024/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
cmp "$SRC/.config" "$WORK/.config"
nm -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
objdump -d --disassemble=aic_init_cpu "$WORK/vmlinux" > "$OUT/aic-init-cpu.txt"
objdump -d --disassemble=aic_handle_fiq "$WORK/vmlinux" > "$OUT/aic-handle-fiq.txt"
objdump -d --disassemble=aic_of_ic_init "$WORK/vmlinux" > "$OUT/aic-of-init.txt"
cp "$WORK/drivers/irqchip/irq-apple-aic.c" "$OUT/patched-aic.c"
git -C "$WORK" diff > "$OUT/kernel-tracked.patch"
{ uname -srm; gcc --version | head -1; ld --version | head -1; } > "$OUT/toolchain.txt"
echo 'PASS: boot024 preserved; restricted t6050 AIC path linked in boot025'
