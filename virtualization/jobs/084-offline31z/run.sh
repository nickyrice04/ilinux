#!/bin/bash
# SPDX-License-Identifier: MIT
# Original adapter tests only; no network or physical device passthrough.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
exec > "$O/run-detail.log" 2>&1
python3 -I - > "$O/network-preflight.json" <<'PY'
import json
from pathlib import Path
interfaces = sorted(p.name for p in Path('/sys/class/net').iterdir())
assert interfaces == ['lo'], 'network_device_present'
print(json.dumps(dict(interfaces=interfaces, network_enabled=False)))
PY
python3 -I "$I/kernel/experiments/sptm31z-adapter/run.py" \
  --output "$O/adapter" --sanitize
uname -srm > "$O/kernel.txt"
echo OFFLINE31Z_ADAPTER_PASS_NATIVE_NOT_RUN
