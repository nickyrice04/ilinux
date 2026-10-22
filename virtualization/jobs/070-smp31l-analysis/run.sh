#!/bin/bash
# Original offline analysis only. No USB, MMIO, target or boot operation.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
exec > "$O/run.log" 2>&1
IMAGE="$I/virtualization/jobs/069-smp31k/out/boot021.bin"
SYMBOLS="$I/virtualization/jobs/069-smp31k/out/m1n1-symbols.txt"
REPORT="$I/native/boot/attempt31k-controller-2026-10-22.json"
CHECKER="$I/kernel/experiments/smp31l-analysis"
python3 -I "$CHECKER/test_entry_contract.py" --image "$IMAGE" --symbols "$SYMBOLS" --report "$REPORT"
python3 -I "$CHECKER/entry_contract.py" --image "$IMAGE" --symbols "$SYMBOLS" --report "$REPORT" > "$O/entry-full-symbols.json"
python3 -I "$CHECKER/entry_contract.py" --image "$IMAGE" --report "$REPORT" > "$O/entry-image-only.json"
python3 --version > "$O/toolchain.txt"
uname -srm >> "$O/toolchain.txt"
echo SMP31L-OFFLINE-ANALYSIS-PASS
