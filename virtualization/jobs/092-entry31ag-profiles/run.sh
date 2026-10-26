#!/bin/bash
# SPDX-License-Identifier: MIT
# Existing isolated Linux VM; no Apple firmware or physical devices.
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
tools={name:subprocess.check_output([name,'--version'],text=True).splitlines()[0]
       for name in ['cc','ld','objcopy','/usr/bin/qemu-system-aarch64']}
print(json.dumps({'interfaces':interfaces,'physical_usb':False,
 'kernel':platform.release(),'python':platform.python_version(),'tools':tools}))
CHECK
python3 -I "$I/kernel/experiments/entry31ag/test_classify.py"
python3 -I "$I/kernel/experiments/entry31ag/run.py" \
 --payload "$I/build/research31af/job/out/link/payload.bin" \
 --layout "$I/native/boot/attempt31af/layout.json" \
 --output "$O/entry" --qemu /usr/bin/qemu-system-aarch64
printf '%s\n' 'ILINUX31AG_ENTRY_PROFILES_PASS'
