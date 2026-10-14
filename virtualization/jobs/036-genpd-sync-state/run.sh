#!/bin/bash
# boot034: build the boot033 tree plus the genpd sync_state experiment.
# Only Image changes; config, DT, initramfs and m1n1 stay byte-identical.
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
SRC=/var/tmp/ilinux-boot033/linux
WORK=/var/tmp/ilinux-boot034/linux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/genpd-sync-state
BOOT033_IMAGE=250d9ff58e5f5397e1bb54682f2bd8a7a679f44f2863629ef7b89ec45ad1eb15
mkdir -p "$OUT/export" /var/tmp/ilinux-boot034
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$BOOT033_IMAGE"
rm -rf "$WORK"   # boot034 scratch tree only; boot033 tree is never touched
cp -a --reflink=auto "$SRC" "$WORK"
python3 -I "$EXP/apply.py" "$WORK"
# Model regressions with this VM's GCC, and the patch against the exact boot033 file.
LINUX_TREE="$SRC" python3 -I "$EXP/test_genpd.py" -v > "$OUT/test-genpd.log" 2>&1
tail -3 "$OUT/test-genpd.log"
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot033/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
cmp "$SRC/.config" "$WORK/.config"
objcopy -O binary "$WORK/vmlinux" "$OUT/roundtrip.bin"
cmp "$OUT/export/Image" "$OUT/roundtrip.bin"
nm -S -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
grep -E ' (ilinux_genpd_ladder_fn|ilinux_genpd_ladder_init|of_genpd_sync_state|genpd_provider_sync_state)$' "$OUT/kernel-symbols.txt"
objdump -d --disassemble=ilinux_genpd_ladder_fn "$WORK/vmlinux" > "$OUT/ladder-fn.txt"
objdump -d --disassemble=of_genpd_sync_state "$WORK/vmlinux" > "$OUT/of-genpd-sync-state.txt"
objdump -d --disassemble=genpd_provider_sync_state "$WORK/vmlinux" > "$OUT/genpd-provider-sync-state.txt"
cp "$WORK/drivers/pmdomain/core.o" "$OUT/core.o"
# The string literals prove the patched object is what got linked.
strings -a "$OUT/export/Image" | grep -c 'ilinux-genpd:' > "$OUT/ilinux-genpd-strings.txt"
diff <(cd "$SRC" && git diff --no-index --stat /dev/null /dev/null 2>/dev/null; true) /dev/null || true
echo 'PASS: Image-only boot034 build, identical config, ELF/Image roundtrip, patched genpd object linked'
