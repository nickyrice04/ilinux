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
python3 -I "$I/tools/m1n1-client/attempt31j-offline.py" --image "$O/boot021.bin" --symbols "$O/m1n1-symbols.txt" > "$O/intake.json"
python3 -I "$I/kernel/experiments/smp31/test_client31j_vm.py" /mnt/m1n1-source/proxyclient
python3 -I "$I/tools/m1n1-client/attempt31j-offline.py" --image "$O/boot021.bin" > "$O/intake-image-only.json"
python3 --version > "$O/toolchain.txt"
uname -srm >> "$O/toolchain.txt"
echo SMP31J-ALL-OFFLINE-PASS
