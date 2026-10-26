#!/bin/bash
# SPDX-License-Identifier: MIT
# Existing isolated ARM64 Linux VM; no network or physical devices.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
exec > "$O/detail.log" 2>&1
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
systemctl mask --runtime docker.service docker.socket
systemctl stop docker.service docker.socket
if ip link show docker0 >/dev/null 2>&1; then ip link delete docker0; fi
python3 -I - > "$O/network.json" <<'CHECK'
from pathlib import Path
import json
interfaces=sorted(p.name for p in Path('/sys/class/net').iterdir())
assert interfaces==['lo'],interfaces
print(json.dumps({'interfaces':interfaces,'physical_usb':False}))
CHECK
python3 -I "$I/kernel/experiments/immutable31af/run.py" --output "$O/link" --cc cc --ld ld
python3 -I "$I/kernel/experiments/immutable31af-test/run.py" --payload "$O/link/payload.bin" --layout "$O/link/layout.json" --output "$O/execution" --qemu /usr/bin/qemu-system-aarch64 --old-payload "$I/build/research31ae/job/out/link/payload.bin"
printf '%s\n' 'ILINUX31AF_IMMUTABLE_LINK_AND_RUNTIME_PASS'
