#!/bin/bash
# Original CPU/GPU integration tests; curated public tree, no networking/hardware.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O" /mnt/retained-image
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/retained-image || mount -t virtiofs retained-image /mnt/retained-image
exec > "$O/run-detail.log" 2>&1
# The curated sources stay read-only; original tests use an ephemeral build tree.
test -d "$I/build"
if mountpoint -q "$I/build"; then echo UNEXPECTED_BUILD_MOUNT; exit 2; fi
mount -t tmpfs -o size=256M,nodev,nosuid,mode=0700 offline31p-tests "$I/build"
python3 -I - > "$O/network-preflight.json" <<'PY'
import json
from pathlib import Path
interfaces = sorted(p.name for p in Path('/sys/class/net').iterdir())
assert interfaces == ['lo'], 'network_device_present'
print(json.dumps(dict(interfaces=interfaces, network_enabled=False)))
PY
# Retain individual suite diagnostics without exposing them in public intake JSON.
for suite in \
  kernel/experiments/smp31o-evidence/test_evidence.py \
  kernel/experiments/smp31o-evidence/test_rcfg.py \
  tools/m1n1-client/test_attempt31o_offline.py \
  kernel/experiments/gpu31p/test_contract.py \
  virtualization/jobs/075-gpu31p/test_package_space.py \
  virtualization/jobs/075-gpu31p/test_isolation.py \
  tools/m1n1-client/test_attempt31p_offline.py; do
  python3 -I "$I/$suite" > "$O/$(basename "$suite").log" 2>&1
done
python3 -I "$I/tools/m1n1-client/attempt31o-offline.py" \
  --image /mnt/retained-image/boot021.bin > "$O/prior-review.json"
python3 -I "$I/tools/m1n1-client/attempt31p-offline.py" \
  --image /mnt/retained-image/boot021.bin > "$O/review.json"
cc -std=c11 -Wall -Wextra -Werror -pedantic -O1 -g \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  "$I/kernel/experiments/gpu31p/segments.c" \
  "$I/kernel/experiments/gpu31p/test_segments.c" -o "$O/test-gpu31p-segments"
ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1 \
  "$O/test-gpu31p-segments" > "$O/sanitizers.txt" 2>&1
{
  python3 --version
  uname -srm
  cc --version | head -1
} > "$O/toolchain.txt"
echo OFFLINE31P_INTEGRATION_PASS_NATIVE_NOT_RUN
