#!/bin/bash
# SPDX-License-Identifier: MIT
# Isolated Linux VM only, existing GNU AArch64 tools and QEMU/TCG.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
exec > "$O/detail.log" 2>&1
python3 -I - > "$O/network.json" <<'PY'
from pathlib import Path
import json
interfaces=sorted(p.name for p in Path('/sys/class/net').iterdir())
assert interfaces==['lo'],interfaces
print(json.dumps({'interfaces':interfaces,'physical_usb':False}))
PY
python3 -I "$I/kernel/experiments/visible31ac/run.py" --output "$O/visible" --cc cc --ld ld
python3 -I "$I/kernel/experiments/bootimage31ac/test_image.py"
python3 -I "$I/kernel/experiments/visible31ac-test/run.py" \
 --payload "$O/visible/payload.bin" --layout "$O/visible/layout.json" \
 --output "$O/execution" --qemu /usr/bin/qemu-system-aarch64
