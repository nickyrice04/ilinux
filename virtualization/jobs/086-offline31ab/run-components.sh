#!/bin/bash
# SPDX-License-Identifier: MIT
# Isolated ARM64 Linux VM only, with existing compilers and QEMU/TCG.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
exec > "$O/component-tests.log" 2>&1
python3 -I - > "$O/component-network.json" <<'PY'
import json
from pathlib import Path
interfaces = sorted(p.name for p in Path('/sys/class/net').iterdir())
assert interfaces == ['lo'], interfaces
print(json.dumps({'interfaces': interfaces, 'physical_usb': False}))
PY
python3 -I "$I/kernel/experiments/observer31ab/run.py" \
  --output "$O/observer" --cc cc --sanitize --freestanding --clang clang
python3 -I "$I/kernel/experiments/translation31ab/run.py" \
  --output "$O/translation" --cc cc --ld ld --qemu /usr/bin/qemu-system-aarch64
echo OBSERVER_TRANSLATION31AB_PASS_NATIVE_NOT_RUN
