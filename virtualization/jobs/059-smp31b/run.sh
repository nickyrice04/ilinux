#!/bin/bash
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out W=/run/smp31b
mkdir -p "$I" /mnt/m1n1-source "$O" "$W"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
exec > "$O/validation.log" 2>&1
gcc -c -march=armv8-a -o "$W/helper-gcc.o" "$I/kernel/experiments/smp31/helper31b.S"
clang -c --target=aarch64-linux-gnu -march=armv8-a -o "$W/helper-clang.o" "$I/kernel/experiments/smp31/helper31b.S"
objcopy -O binary -j .text "$W/helper-gcc.o" "$O/helper-gcc.bin"
objcopy -O binary -j .text "$W/helper-clang.o" "$O/helper-clang.bin"
cmp "$O/helper-gcc.bin" "$O/helper-clang.bin"
objdump -dr "$W/helper-gcc.o" > "$O/helper-disassembly.txt"
readelf -r "$W/helper-gcc.o" > "$O/helper-relocations.txt"
sha256sum "$O"/helper-*.bin
python3 -I - "$O/helper-gcc.bin" <<'PY'
import struct, sys
from pathlib import Path
b=Path(sys.argv[1]).read_bytes()
print('HELPER_BYTES',len(b))
print('HELPER_WORDS', ', '.join(hex(x) for x in struct.unpack('<'+'I'*(len(b)//4),b)))
PY
python3 -I "$I/native/boot/smp31b.py" --image "$O/boot021.bin" --helper-check "$O/helper-gcc.bin"
python3 -I "$I/native/boot/test_smp31b.py"
python3 -I "$I/tools/m1n1-client/test_attempt31b_supervise.py"
python3 -I "$I/kernel/experiments/smp31/test_parser_vm.py" /mnt/m1n1-source/proxyclient
python3 -I "$I/kernel/experiments/smp31/test_client31b_vm.py" /mnt/m1n1-source/proxyclient
gcc -O2 -Wall -Wextra -Werror -o "$W/test-helper" "$I/kernel/experiments/smp31/test_helper31b.c" "$W/helper-gcc.o"
timeout -k 1 5 "$W/test-helper"
python3 -I - "$W" <<'PY'
from pathlib import Path
import hashlib, re, sys
source=Path('/mnt/m1n1-source/src'); out=[]
for name, file, digest in [('smp_secondary_entry', 'smp.c', '4b000be8d4e6437fc24351a57db5277785cc2e427045fb45d1750b158f2b8766'),
        ('timeout_calculate', 'utils.c', '0361304388c7b42de38bc6be8717f25f48e59fb8c513712ee202c2d698a2ac5c')]:
    data=(source/file).read_bytes()
    assert hashlib.sha256(data).hexdigest()==digest
    match=re.search(r'^(?:void|u64) '+name+r'\([^;]*?\n\{.*?^}\n',data.decode(),re.M|re.S)
    assert match is not None
    out.append(match.group())
(Path(sys.argv[1])/'loop31b.inc').write_text('\n'.join(out))
PY
cp "$I/kernel/experiments/smp31/test_loop31b.c" "$W/"
gcc -O2 -std=gnu11 -Wall -Wextra -Werror -pthread -o "$W/test-loop" "$W/test_loop31b.c"
gcc -O1 -g -std=gnu11 -fsanitize=address,undefined -fno-omit-frame-pointer -pthread -o "$W/test-loop-san" "$W/test_loop31b.c"
timeout -k 1 8 "$W/test-loop"
timeout -k 1 8 "$W/test-loop-san"
{ gcc --version | head -1; clang --version | head -1; uname -srm; } > "$O/toolchain.txt"
echo SMP31B-OFFLINE-PASS
