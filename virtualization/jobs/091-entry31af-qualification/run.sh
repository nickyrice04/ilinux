#!/bin/bash
# SPDX-License-Identifier: MIT
# Run the frozen 31AF payload under additional synthetic memory permissions.
# Existing isolated Linux VM only; no Apple firmware or physical hardware.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
exec > "$O/detail.log" 2>&1
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
systemctl mask --runtime docker.service docker.socket
systemctl stop docker.service docker.socket
if ip link show docker0 >/dev/null 2>&1; then ip link delete docker0; fi
python3 -I - > "$O/environment.json" <<'CHECK'
from pathlib import Path
import json,platform,subprocess
interfaces=sorted(p.name for p in Path('/sys/class/net').iterdir())
assert interfaces==['lo'],interfaces
print(json.dumps({'interfaces':interfaces,'physical_usb':False,
 'kernel':platform.release(),'python':platform.python_version(),
 'qemu':subprocess.check_output(['/usr/bin/qemu-system-aarch64','--version'],text=True)}))
CHECK
python3 -I "$I/kernel/experiments/entry31af-qualification/run.py" \
 --payload "$I/build/research31af/job/out/link/payload.bin" \
 --layout "$I/native/boot/attempt31af/layout.json" \
 --output "$O/execution" --qemu /usr/bin/qemu-system-aarch64
printf '%s\n' 'ILINUX31AF_ENTRY_QUALIFICATION_PASS'
