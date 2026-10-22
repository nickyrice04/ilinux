#!/bin/bash
# Original offline evidence/parser tests. No network, USB or native operations.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O" /mnt/private-firmware
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/private-firmware || mount -t virtiofs private-firmware /mnt/private-firmware
exec > "$O/run.log" 2>&1
IMAGE="$I/virtualization/jobs/069-smp31k/out/boot021.bin"
SYMBOLS="$I/virtualization/jobs/069-smp31k/out/m1n1-symbols.txt"
DATA=/mnt/private-firmware/iBootData.bin
python3 -I "$I/tools/m1n1-client/attempt31o-offline.py" --image "$IMAGE" --symbols "$SYMBOLS" --ibootdata "$DATA" > "$O/review-full.json"
python3 -I "$I/tools/m1n1-client/attempt31o-offline.py" --image "$IMAGE" > "$O/review-image.json"
python3 --version > "$O/toolchain.txt"
uname -srm >> "$O/toolchain.txt"
echo SMP31O-OFFLINE-REVIEW-PASS
