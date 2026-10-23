#!/bin/bash
# SPDX-License-Identifier: MIT
# Original CPU/GPU tests only, curated sources, no network or native device.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O" /mnt/retained-image
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/retained-image || mount -t virtiofs retained-image /mnt/retained-image
exec > "$O/run-detail.log" 2>&1
test -d "$I/build"
if mountpoint -q "$I/build"; then echo UNEXPECTED_BUILD_MOUNT; exit 2; fi
mount -t tmpfs -o size=256M,nodev,nosuid,mode=0700 offline31t-tests "$I/build"
python3 -I - > "$O/network-preflight.json" <<'PY'
import json
from pathlib import Path
interfaces = sorted(p.name for p in Path('/sys/class/net').iterdir())
assert interfaces == ['lo'], 'network_device_present'
print(json.dumps(dict(interfaces=interfaces, network_enabled=False)))
PY
for suite in tools/m1n1-client/test_attempt31t_offline.py; do
  python3 -I "$I/$suite" > "$O/$(basename "$suite").log" 2>&1
done
python3 -I "$I/tools/m1n1-client/attempt31t-offline.py" \
 --image /mnt/retained-image/boot021.bin > "$O/review.json"
for component in leases; do
 cc -std=c11 -Wall -Wextra -Werror -pedantic -O1 -g \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  "$I/kernel/experiments/gpu31t/$component.c" \
  "$I/kernel/experiments/gpu31t/test_$component.c" -o "$O/test-$component"
 ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 \
  "$O/test-$component" > "$O/sanitizers-$component.txt" 2>&1
done
{
 python3 --version
 uname -srm
 cc --version | head -1
} > "$O/toolchain.txt"
echo OFFLINE31T_INTEGRATION_PASS_NATIVE_NOT_RUN
