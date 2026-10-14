#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
SRC=/var/tmp/ilinux-boot032/linux
WORK=/var/tmp/ilinux-boot033/linux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/scheduler-ram-only
mkdir -p "$OUT/export" /var/tmp/ilinux-boot033
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = 589c33577d1bc2ddeb2f96e544f87b9ead6bc52e774410567170a7235dd70bcb
test ! -e "$WORK"
cp -a --reflink=auto "$SRC" "$WORK"
python3 -I "$EXP/apply.py" "$WORK"
python3 -I - "$SRC" "$WORK" "$OUT" <<'TEST'
from pathlib import Path
import sys
old,new,out=map(Path,sys.argv[1:])
for r,n in [(old,'old'),(new,'new')]:
 s=(r/'drivers/base/ilinux_probe_diag.h').read_text();a=s.index('void ilinux_probe_sched_mark(unsigned int phase, int prev, int next)\n{');b=s.index('\n}',a)+2;f=s[a:b]
 if n=='old':f=f.replace('ilinux_probe_sched_mark','old_sched_mark')
 (out/(n+'-hook.h')).write_text(f)
s=(new/'drivers/base/ilinux_probe_diag.h').read_text();a=s.index('static void ilinux_probe_watchdog(');s=s[a:]
assert s.index('ilinux_probe_fb_mark(1, READ_ONCE(ilinux_sched_phase))')<s.index('ilinux_probe_fb_mark(3, ilinux_probe_heartbeats + 1)')<s.index('pr_info(')
(out/'new-diag.h').write_bytes((new/'drivers/base/ilinux_probe_diag.h').read_bytes())
TEST
gcc -std=gnu11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -I"$OUT" "$EXP/test_hook.c" -o "$OUT/test-hook"
"$OUT/test-hook"
make -C "$WORK" -j2 Image > "$OUT/build.log" 2>&1
cp -a /mnt/ilinux/build/native-boot032/verified/. "$OUT/export/"
cp "$WORK/arch/arm64/boot/Image" "$OUT/export/Image"
cmp "$SRC/.config" "$WORK/.config"
objcopy -O binary "$WORK/vmlinux" "$OUT/roundtrip.bin"
cmp "$OUT/export/Image" "$OUT/roundtrip.bin"
objdump -d --disassemble=ilinux_probe_sched_mark "$WORK/vmlinux" > "$OUT/sched-mark.txt"
objdump -dr "$WORK/drivers/base/dd.o" > "$OUT/dd-object.txt"
nm -S -n "$WORK/vmlinux" > "$OUT/kernel-symbols.txt"
cp "$WORK/drivers/base/dd.o" "$OUT/dd.o"
echo 'PASS: full Image, identical config, ELF/Image roundtrip and scheduler-hook sanitizer regression'
