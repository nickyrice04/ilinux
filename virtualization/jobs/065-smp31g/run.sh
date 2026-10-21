#!/bin/bash
# Original offline validation only; no physical USB or Apple device access.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out W=/run/smp31g
mkdir -p "$I" "$O" "$W"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
exec > "$O/validation.log" 2>&1
mkdir -p /mnt/m1n1-source
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
test "$(git -c safe.directory=/mnt/m1n1-source -C /mnt/m1n1-source rev-parse HEAD)" = 57a9339ffd1876e78297b17d34dece8cff8fa1ba
test -z "$(git -c safe.directory=/mnt/m1n1-source -C /mnt/m1n1-source status --porcelain --untracked-files=all)"
python3 -I "$I/tools/m1n1-client/attempt31g-offline.py" \
  --image "$O/boot021.bin" --symbols "$O/m1n1-symbols.txt" > "$O/intake.json"
python3 -I "$I/kernel/experiments/smp31f-entry/audit.py" \
  --image "$O/boot021.bin" --symbols "$O/m1n1-symbols.txt" > "$O/entry-audit.json"
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
    root/'kernel/experiments/smp31f-entry/builder.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
plan, body, entry = builder.build((out/'boot021.bin').read_bytes(),
                                 (out/'m1n1-symbols.txt').read_bytes())
(out/'recorder-python.bin').write_bytes(body)
(out/'entry-branch.bin').write_bytes(entry)
(out/'recorder-plan.json').write_text(json.dumps(plan, indent=2)+'\n')
assert hashlib.sha256(body).hexdigest() == '52f9d1b312725cdc9261e0fbf1c31991e9078a663827734b9ba54c9d171106bc'
PY
as -march=armv8.2-a "$I/kernel/experiments/smp31f-entry/recorder.S" -o "$W/recorder-gas.o"
clang -c -march=armv8.2-a "$I/kernel/experiments/smp31f-entry/recorder.S" -o "$W/recorder-clang.o"
ld -Ttext=0xa00 --entry=smp31f_recorder --defsym=smp31f_record=0x90a40 --defsym=smp31f_resume=0x4 "$W/recorder-gas.o" -o "$W/recorder-gas.elf"
ld -Ttext=0xa00 --entry=smp31f_recorder --defsym=smp31f_record=0x90a40 --defsym=smp31f_resume=0x4 "$W/recorder-clang.o" -o "$W/recorder-clang.elf"
objcopy -O binary --only-section=.text "$W/recorder-gas.elf" "$O/recorder-gas.bin"
objcopy -O binary --only-section=.text "$W/recorder-clang.elf" "$O/recorder-clang.bin"
cmp "$O/recorder-python.bin" "$O/recorder-gas.bin"
cmp "$O/recorder-python.bin" "$O/recorder-clang.bin"
echo RECORDER-ASSEMBLER-BYTE-MATCH-PASS
{ gcc --version | head -1; clang --version | head -1; python3 --version; uname -srm; } > "$O/toolchain.txt"
echo RETAINED31F-OFFLINE-PASS
python3 -I "$I/native/boot/test_smp31g.py" --real-parser /mnt/m1n1-source/proxyclient
python3 -I "$I/kernel/experiments/smp31/test_client31g_vm.py" /mnt/m1n1-source/proxyclient
python3 -I - "$I" "$O" <<'PY'
import hashlib,importlib.util,sys
from pathlib import Path
root,out=map(Path,sys.argv[1:])
sys.path.insert(0,str(root/'native/boot'))
import smp31f
(out/'permission-python.bin').write_bytes(smp31f.permissions.HELPER_TAIL)
(out/'start-python.bin').write_bytes(smp31f.START_HELPER)
print('PERMISSION_TAIL',hashlib.sha256(smp31f.permissions.HELPER_TAIL).hexdigest())
print('START_HELPER',hashlib.sha256(smp31f.START_HELPER).hexdigest())
PY
for helper in permission start; do
  source="$I/kernel/experiments/smp31e-entry/${helper}_helper.S"
  as -march=armv8.2-a "$source" -o "$W/$helper-gas.o"
  clang -c -march=armv8.2-a "$source" -o "$W/$helper-clang.o"
  objcopy -O binary --only-section=.text "$W/$helper-gas.o" "$O/$helper-gas.bin"
  objcopy -O binary --only-section=.text "$W/$helper-clang.o" "$O/$helper-clang.bin"
  cmp "$O/$helper-python.bin" "$O/$helper-gas.bin"
  cmp "$O/$helper-python.bin" "$O/$helper-clang.bin"
done
echo PERMISSION-AND-START-ASSEMBLER-MATCH-PASS
echo RETAINED31F-CONTROLLER-OFFLINE-PASS
python3 -I "$I/kernel/experiments/cpu-topology31f/audit.py" --dtb "$O/t6050-j716c.dtb" --dtb "$O/t6050-j716c-stage-b.dtb" > "$O/topology-audit.json"
echo RETAINED31F-ALL-OFFLINE-PASS

python3 -I "$I/kernel/experiments/smp31g-observation/test_binding_vm.py" /mnt/m1n1-source/proxyclient
python3 -I "$I/kernel/experiments/smp31g-publication/audit.py" --image "$O/boot021.bin" > "$O/publication-audit.json"
python3 -I - "$I" "$O" <<'PYTHON'
import sys
from pathlib import Path
root,out=map(Path,sys.argv[1:]);sys.path.insert(0,str(root/'native/boot'))
import smp31g
(out/'read32-python.bin').write_bytes(smp31g.READ32_HELPER)
PYTHON
as -march=armv8.2-a "$I/kernel/experiments/smp31g-observation/read32.S" -o "$W/read32-gas.o"
clang -c -march=armv8.2-a "$I/kernel/experiments/smp31g-observation/read32.S" -o "$W/read32-clang.o"
for compiler in gas clang; do
  objcopy -O binary --only-section=.text "$W/read32-$compiler.o" "$O/read32-$compiler.bin"
  cmp "$O/read32-python.bin" "$O/read32-$compiler.bin"
done
for compiler in gcc clang; do
  "$compiler" -O2 -std=c11 -Wall -Wextra -Werror "$I/kernel/experiments/smp31g-observation/read32.S" "$I/kernel/experiments/smp31g-observation/test_read32.c" -o "$W/read32-$compiler"
  timeout -k 1 5 "$W/read32-$compiler"
done
python3 -I "$I/tools/m1n1-client/attempt31g-offline.py" --image "$O/boot021.bin" > "$O/intake-image-only.json"
echo SMP31G-ALL-OFFLINE-PASS
