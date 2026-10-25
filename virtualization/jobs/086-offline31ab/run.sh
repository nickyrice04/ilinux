#!/bin/bash
# SPDX-License-Identifier: MIT
# Original code only, with no network or physical-device passthrough.
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
python3 -I "$I/kernel/experiments/sptm31ab-host/run.py" \
  --output "$O/host" --cc cc --ld ld
python3 -I "$I/kernel/experiments/bootimage31ab/test_image.py"
mkdir "$O/bootstrap"
for base in 40000000 41000000; do
  for mode in normal vhe; do
    extra=() suffix=""
    if [ "$mode" = vhe ]; then extra=(-DTEST_VHE=1); suffix=-vhe; fi
    name="bootstrap-$base$suffix"
    cc -ffreestanding -DTEST_IMAGE_BASE="0x$base" "${extra[@]}" \
      -c /mnt/job/bootstrap.S -o "$O/bootstrap/$name.o"
    ld --no-undefined --build-id=none -e test_bootstrap -Ttext=0x42000000 \
      "$O/bootstrap/$name.o" -o "$O/bootstrap/$name.elf"
    objcopy -O binary -j .text "$O/bootstrap/$name.elf" "$O/bootstrap/$name.bin"
  done
done
uname -srm > "$O/kernel.txt"
echo OFFLINE31AB_LINK_AND_PACKAGING_PASS_NATIVE_NOT_RUN
