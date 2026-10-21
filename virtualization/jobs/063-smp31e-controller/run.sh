#!/bin/bash
# Offline original code and pinned public client only; no physical USB/device.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out W=/run/smp31e-controller
mkdir -p "$I" "$O" "$W" /mnt/m1n1-source
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
exec > "$O/controller-validation.log" 2>&1
bash "$I/virtualization/jobs/062-smp31e/run.sh"
python3 -I "$I/native/boot/test_smp31e.py" --real-parser /mnt/m1n1-source/proxyclient
python3 -I "$I/kernel/experiments/smp31/test_client31e_vm.py" /mnt/m1n1-source/proxyclient
python3 -I - "$I" "$O" <<'PY'
import hashlib,importlib.util,sys
from pathlib import Path
root,out=map(Path,sys.argv[1:])
sys.path.insert(0,str(root/'native/boot'))
import smp31e
(out/'permission-python.bin').write_bytes(smp31e.permissions.HELPER_TAIL)
(out/'start-python.bin').write_bytes(smp31e.START_HELPER)
print('PERMISSION_TAIL',hashlib.sha256(smp31e.permissions.HELPER_TAIL).hexdigest())
print('START_HELPER',hashlib.sha256(smp31e.START_HELPER).hexdigest())
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
echo SMP31E-CONTROLLER-OFFLINE-PASS
