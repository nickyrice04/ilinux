#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
O=/mnt/job/out
S=/mnt/ilinux/kernel/experiments/memory29
K=/var/tmp/ilinux-boot042/linux
mkdir -p "$O"
exec > "$O/detail.log" 2>&1
test "$(sha256sum "$K/arch/arm64/boot/Image" | cut -d' ' -f1)" = 0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c
W=/var/tmp/ilinux-memory29-build
mkdir -p "$W"
cp "$K/arch/arm64/include/asm/pgtable.h" "$K/arch/arm64/include/asm/pgtable-prot.h" "$K/arch/arm64/include/asm/pgtable-hwdef.h" "$K/arch/arm64/mm/proc.S" "$O/"
cp "$S/Makefile" "$S/ilinux_mem29.c" "$W/"
make -C "$K" M="$W" W=1 modules
cc -O3 -march=armv8.4-a -Wall -Wextra -Werror "$S/memory29.c" -o "$W/memory29"
cc -O1 -g -fsanitize=address,undefined -Wall -Wextra -Werror "$S/memory29.c" -o "$W/memory29-san"
timeout -k 5 90 "$W/memory29-san" > "$O/sanitizer.jsonl"
timeout -k 5 90 "$W/memory29" > "$O/optimized.jsonl"
objdump -d "$W/memory29" > "$O/optimized.asm"
objdump -d "$W/ilinux_mem29.ko" > "$O/module.asm"
cp "$W/ilinux_mem29.ko" "$W/memory29" "$S/collect.py" "$O/"
cp "$K/arch/arm64/include/asm/pgtable-prot.h" "$K/arch/arm64/include/asm/pgtable-hwdef.h" "$K/arch/arm64/mm/proc.S" "$O/"
cc --version > "$O/compiler.txt"
modinfo "$W/ilinux_mem29.ko" > "$O/module-info.txt"
python3 -I "$S/test_memory29.py"
python3 -I - <<'PY'
import hashlib,json,tarfile
from pathlib import Path
o=Path('/mnt/job/out')
for name in ('sanitizer','optimized'):
 rows=[json.loads(s) for s in (o/(name+'.jsonl')).read_text().splitlines()]
 assert len(rows)==49 and all(x['ns_per_load']>0 and x['sink']==0 for x in rows[1:])
a={'attempt':29,'frequency_writes':False,'global_vm_writes':False,
   'sha256':{n:hashlib.sha256((o/n).read_bytes()).hexdigest() for n in ('ilinux_mem29.ko','memory29','collect.py')}}
(o/'assets.json').write_text(json.dumps(a,indent=2)+'\n')
with tarfile.open(o/'memory29.tar','w',format=tarfile.USTAR_FORMAT) as t:
 for n in sorted([*a['sha256'],'assets.json']):
  info=t.gettarinfo(str(o/n),arcname=n); info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
  with (o/n).open('rb') as f:t.addfile(info,f)
b=(o/'memory29.tar').read_bytes()
(o/'bundle.json').write_text(json.dumps({'attempt':29,'size_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},indent=2)+'\n')
print('PASS memory29 module build, sanitizer and optimized VM matrices; native NOT RUN')
PY
