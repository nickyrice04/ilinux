#!/bin/bash
# Original offline tests; no USB or physical target access.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O" /mnt/m1n1-source
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
exec > "$O/validation.log" 2>&1
test "$(git -c safe.directory=/mnt/m1n1-source -C /mnt/m1n1-source rev-parse HEAD)" = 57a9339ffd1876e78297b17d34dece8cff8fa1ba
test -z "$(git -c safe.directory=/mnt/m1n1-source -C /mnt/m1n1-source status --porcelain --untracked-files=all)"
as -o "$O/control.o" "$I/kernel/experiments/smp31k-control/control.S"
python3 -I "$I/kernel/experiments/smp31k-control/audit.py" --image "$O/boot021.bin" --object "$O/control.o" > "$O/control-assembly.json"
as -o "$O/tripwire.o" "$I/kernel/experiments/smp31k-entry/tripwire.S"
ld -T "$I/kernel/experiments/smp31k-entry/tripwire.ld" -o "$O/tripwire.elf" "$O/tripwire.o"
objcopy -O binary -j .text "$O/tripwire.elf" "$O/tripwire.bin"
python3 -I - "$I" "$O" <<'CHECK'
import importlib.util, pathlib, sys
root, out = map(pathlib.Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('original_tripwire', root/'kernel/experiments/smp31k-entry/builder.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert (out/'tripwire.bin').read_bytes() == m.program()[0], 'tripwire assembly differs'
print('TRIPWIRE-ASSEMBLY-ENCODER-MATCH')
CHECK
as --version | head -1 > "$O/assembler.txt"
python3 -I "$I/tools/m1n1-client/attempt31k-offline.py" --image "$O/boot021.bin" --symbols "$O/m1n1-symbols.txt" > "$O/intake.json"
python3 -I "$I/kernel/experiments/smp31/test_client31k_vm.py" /mnt/m1n1-source/proxyclient
python3 -I "$I/tools/m1n1-client/attempt31k-offline.py" --image "$O/boot021.bin" > "$O/intake-image-only.json"
python3 --version > "$O/toolchain.txt"
uname -srm >> "$O/toolchain.txt"
echo SMP31K-ALL-OFFLINE-PASS
