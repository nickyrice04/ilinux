#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
SRC=/var/tmp/ilinux-boot030/linux
WORK=/var/tmp/ilinux-boot031/linux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/gpio-handoff
mkdir -p "$OUT/export" /var/tmp/ilinux-boot031
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = 190cd86d5f823326f5a44277f5efb96cc01c85b3a3f9ffbde16d9cb7abe35067
test ! -e "$WORK"
cp -a --reflink=auto "$SRC" "$WORK"
python3 -I "$EXP/apply.py" "$WORK"
python3 -I - "$WORK" "$OUT" <<'PY'
from pathlib import Path
import sys
w,o=map(Path,sys.argv[1:]);s=(w/'drivers/pinctrl/pinctrl-apple-gpio.c').read_text()
a=s.index('\tif (t6050) {');b=s.index('\n\tpins = devm_kmalloc_array',a)
(o/'tested-geometry.h').write_text('static int geometry(bool t6050,unsigned int npins,unsigned int nirqs,struct platform_device *pdev,struct regmap_config *result) {\nstruct regmap_config config={2048,512};\n'+s[a:b]+'\n*result=config;return 0;\n}\n')
# The hook must remain before parent registration in the retained framework.
g=(w/'drivers/gpio/gpiolib.c').read_text()
a=g.index('int gpiochip_add_data_with_key(');b=g.index('EXPORT_SYMBOL_GPL(gpiochip_add_data_with_key)',a)
sn=g[a:b];assert sn.index('gpiochip_irqchip_init_hw(gc)')<sn.index('gpiochip_add_irqchip(gc,')
assert 'girq->init_hw = apple_gpio_t6050_irq_init_hw;' in s
(o/'patched-pinctrl-apple-gpio.c').write_text(s)
old=(Path('/var/tmp/ilinux-boot030/linux')/'drivers/pinctrl/pinctrl-apple-gpio.c').read_text();a=old.index('static void apple_gpio_irq_handler(');b=old.index('\n}\n',a)+3
(o/'tested-old-handler.h').write_text(old[a:b])
PY
FLAGS=(-std=gnu11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer)
for name in irq geometry; do
 gcc "${FLAGS[@]}" -I"$OUT" -I"$EXP" "$EXP/test_$name.c" -o "$OUT/test-$name"
 "$OUT/test-$name"
done
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot030/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
cmp "$SRC/.config" "$WORK/.config"
objcopy -O binary "$WORK/vmlinux" "$OUT/roundtrip.bin"
cmp "$OUT/export/Image" "$OUT/roundtrip.bin"
nm -S -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
objdump -dr "$WORK/drivers/pinctrl/pinctrl-apple-gpio.o" > "$OUT/patched-object.txt"
for f in apple_gpio_pinctrl_probe apple_gpio_t6050_irq_init_hw; do objdump -d --disassemble="$f" "$WORK/vmlinux" > "$OUT/$f.txt"; done
{ uname -srm; gcc --version | head -1; ld --version | head -1; } > "$OUT/toolchain.txt"
sha256sum "$WORK/vmlinux" "$WORK/drivers/pinctrl/pinctrl-apple-gpio.o" > "$OUT/sha256.txt"
echo 'PASS: boot030 preserved; boot031 full Image/ELF roundtrip; actual helper/geometry tests'
