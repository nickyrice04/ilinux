#!/bin/bash
# Original offline validation only; no physical USB or Apple device access.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out W=/run/smp31e
mkdir -p "$I" "$O" "$W"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
exec > "$O/validation.log" 2>&1
python3 -I "$I/tools/m1n1-client/attempt31e-offline.py" \
  --image "$O/boot021.bin" --symbols "$O/m1n1-symbols.txt" > "$O/intake.json"
python3 -I "$I/kernel/experiments/smp31e-entry/audit.py" \
  --image "$O/boot021.bin" --symbols "$O/m1n1-symbols.txt" > "$O/entry-audit.json"
cmp "$O/entry-audit.json" "$I/kernel/experiments/smp31e-entry/audit.json"
cp "$I/kernel/experiments/smp31e-emulator/first_frame.S" "$W/"
cp "$I/kernel/experiments/smp31e-emulator/test_first_frame.c" "$W/"
gcc -O2 -std=c11 -Wall -Wextra -Werror "$W/first_frame.S" "$W/test_first_frame.c" -o "$W/frame-gcc"
clang -O2 -std=c11 -Wall -Wextra -Werror "$W/first_frame.S" "$W/test_first_frame.c" -o "$W/frame-clang"
gcc -O1 -g -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -fno-omit-frame-pointer "$W/first_frame.S" "$W/test_first_frame.c" -o "$W/frame-sanitized"
timeout -k 1 5 "$W/frame-gcc"
timeout -k 1 5 "$W/frame-clang"
timeout -k 1 5 "$W/frame-sanitized"
python3 -I - "$I" "$O" <<'PY'
import hashlib, importlib.util, json, sys
from pathlib import Path
root, out = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('recorder_builder',
    root/'kernel/experiments/smp31e-entry/build_recorder.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
plan, body, entry = builder.build((out/'boot021.bin').read_bytes(),
                                 (out/'m1n1-symbols.txt').read_bytes())
(out/'recorder-python.bin').write_bytes(body)
(out/'entry-branch.bin').write_bytes(entry)
(out/'recorder-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
assert hashlib.sha256(body).hexdigest() == '9fa1f68b849a7049481cb1a83e645ccd43ca61a0d5df11d6bf7ca76dffd00335'
PY
as -march=armv8.2-a "$I/kernel/experiments/smp31e-entry/recorder.S" -o "$W/recorder-gas.o"
clang -c -march=armv8.2-a "$I/kernel/experiments/smp31e-entry/recorder.S" -o "$W/recorder-clang.o"
ld -Ttext=0xa00 --entry=smp31e_recorder --defsym=smp31e_record=0x90a40 --defsym=smp31e_resume=0x900 "$W/recorder-gas.o" -o "$W/recorder-gas.elf"
ld -Ttext=0xa00 --entry=smp31e_recorder --defsym=smp31e_record=0x90a40 --defsym=smp31e_resume=0x900 "$W/recorder-clang.o" -o "$W/recorder-clang.elf"
objcopy -O binary --only-section=.text "$W/recorder-gas.elf" "$O/recorder-gas.bin"
objcopy -O binary --only-section=.text "$W/recorder-clang.elf" "$O/recorder-clang.bin"
cmp "$O/recorder-python.bin" "$O/recorder-gas.bin"
cmp "$O/recorder-python.bin" "$O/recorder-clang.bin"
echo RECORDER-ASSEMBLER-BYTE-MATCH-PASS
{ gcc --version | head -1; clang --version | head -1; python3 --version; uname -srm; } > "$O/toolchain.txt"
echo SMP31E-OFFLINE-PASS
