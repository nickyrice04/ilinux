#!/bin/bash
# Offline original models and pinned client serialization; no physical target.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O" /mnt/m1n1-source
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
exec > "$O/run.log" 2>&1
test "$(git -c safe.directory=/mnt/m1n1-source -C /mnt/m1n1-source rev-parse HEAD)" = 57a9339ffd1876e78297b17d34dece8cff8fa1ba
test -z "$(git -c safe.directory=/mnt/m1n1-source -C /mnt/m1n1-source status --porcelain --untracked-files=all)"
IMAGE="$I/virtualization/jobs/069-smp31k/out/boot021.bin"
SYMBOLS="$I/virtualization/jobs/069-smp31k/out/m1n1-symbols.txt"
as -o "$O/start_pair.o" "$I/kernel/experiments/smp31n-startpair/start_pair.S"
python3 -I "$I/kernel/experiments/smp31n-startpair/audit.py" --object "$O/start_pair.o" > "$O/assembly.json"
python3 -I "$I/kernel/experiments/smp31n-startpair/test_plan.py"
python3 -I "$I/kernel/experiments/smp31n-startpair/test_prior_gap.py"
python3 -I "$I/native/boot/test_smp31n.py"
python3 -I "$I/tools/m1n1-client/test_attempt31n_offline.py"
python3 -I "$I/tools/m1n1-client/test_attempt31n_supervisor.py"
python3 -I "$I/kernel/experiments/smp31/test_client31n_vm.py" /mnt/m1n1-source/proxyclient > "$O/wire.log"
test -f "$I/native/boot/attempt31n/source-sha256.txt"
 python3 -I "$I/tools/m1n1-client/attempt31n-offline.py" --image "$IMAGE" --symbols "$SYMBOLS" > "$O/intake-full.json"
 python3 -I "$I/tools/m1n1-client/attempt31n-offline.py" --image "$IMAGE" > "$O/intake-image.json"
python3 --version > "$O/toolchain.txt"
uname -srm >> "$O/toolchain.txt"
as --version | head -1 >> "$O/toolchain.txt"
echo SMP31N-OFFLINE-PASS
