#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
SRC=/var/tmp/ilinux-boot031/linux
WORK=/var/tmp/ilinux-boot032/linux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/gpio-reserved
mkdir -p "$OUT/export" /var/tmp/ilinux-boot032
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = 09d3cc302da20ef53c41bec3324d702b249a729a55e3799b5676618034bff37d
test ! -e "$WORK"
cp -a --reflink=auto "$SRC" "$WORK"
python3 -I "$EXP/apply.py" "$WORK"
python3 -I - "$WORK" "$OUT" <<'EXTRACT'
from pathlib import Path
import sys
w,o=map(Path,sys.argv[1:]);s=(w/'drivers/pinctrl/pinctrl-apple-gpio.c').read_text()
funcs=['apple_gpio_set_reg','apple_gpio_get_reg','apple_gpio_get_direction','apple_gpio_get','apple_gpio_set','apple_gpio_direction_input','apple_gpio_direction_output','apple_gpio_irq_handler']
parts=[]
for f in funcs:
 a=s.rfind('static ',0,s.index(f+'('));b=s.index('\n}',a)+2;parts.append(s[a:b])
(o/'tested-runtime.h').write_text('\n'.join(parts)+'\n')
(o/'patched-pinctrl-apple-gpio.c').write_text(s)
EXTRACT
FLAGS=(-std=gnu11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer)
for name in gpio panel; do
 gcc "${FLAGS[@]}" -I"$OUT" -I"$EXP" "$EXP/test_$name.c" -o "$OUT/test-$name"
 "$OUT/test-$name"
done
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot031/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
fdtput -t i "$OUT/export/t6050-j716c-stage-b.dtb" /soc/pinctrl@29c000000 gpio-reserved-ranges 5 3 112 1 141 1
cmp "$SRC/.config" "$WORK/.config"
objcopy -O binary "$WORK/vmlinux" "$OUT/roundtrip.bin"
cmp "$OUT/export/Image" "$OUT/roundtrip.bin"
nm -S -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
objdump -dr "$WORK/drivers/pinctrl/pinctrl-apple-gpio.o" > "$OUT/patched-object.txt"
for f in apple_gpio_pinctrl_probe apple_gpio_t6050_irq_init_hw; do objdump -d --disassemble="$f" "$WORK/vmlinux" > "$OUT/$f.txt"; done
{ uname -srm; gcc --version | head -1; ld --version | head -1; } > "$OUT/toolchain.txt"
sha256sum "$WORK/vmlinux" "$WORK/drivers/pinctrl/pinctrl-apple-gpio.o" > "$OUT/sha256.txt"
> "$OUT/boot031-to-boot032.patch"
for name in drivers/pinctrl/pinctrl-apple-gpio.c drivers/pinctrl/ilinux-gpio-irq-init.h drivers/firmware/efi/ilinux-fb-map.h Documentation/devicetree/bindings/pinctrl/apple,pinctrl.yaml; do
 diff -u --label "a/$name" --label "b/$name" "$SRC/$name" "$WORK/$name" >> "$OUT/boot031-to-boot032.patch" || test "$?" = 1
done
find /var/tmp -maxdepth 4 -name dt-validate -o -name dt-doc-validate > "$OUT/schema-tools.txt"
echo 'PASS: boot031 preserved; boot032 full Image/ELF roundtrip; actual GPIO/panel sanitizer tests'

export PATH=/var/tmp/t6050-build/dtvenv/bin:$PATH
make -C "$WORK" -j2 dt_binding_check DT_SCHEMA_FILES=pinctrl/apple,pinctrl.yaml > "$OUT/binding-check.log" 2>&1
dt-validate -l apple,pinctrl -s "$WORK/Documentation/devicetree/bindings/processed-schema.json" "$OUT/export/t6050-j716c-stage-b.dtb" > "$OUT/dt-check.log" 2>&1
test ! -s "$OUT/dt-check.log"
echo 'PASS: GPIO binding and Stage-B GPIO DT schema validation'
