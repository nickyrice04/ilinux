#!/bin/bash
# SPDX-License-Identifier: MIT
# Run within the isolated ARM64 Linux VM, after run.sh produced the payload.
# Requires an existing QEMU system emulator with TCG; no package installation.
set -euo pipefail
I=/mnt/ilinux A=/mnt/artifacts O=/mnt/job/out
exec > "$O/instruction-tests.log" 2>&1
python3 -I - > "$O/instruction-network.json" <<'PY'
import json
from pathlib import Path
interfaces=sorted(p.name for p in Path('/sys/class/net').iterdir())
assert interfaces==['lo']
print(json.dumps({'interfaces':interfaces,'network':False,'physical_usb':False}))
PY
mkdir "$O/bootstrap-final"
for base in 40400000 41000000; do
  for mode in normal vhe; do
    extra=() suffix=""
    if [ "$mode" = vhe ]; then extra=(-DTEST_VHE=1); suffix=-vhe; fi
    name="bootstrap-$base$suffix"
    cc -ffreestanding -DTEST_IMAGE_BASE="0x$base" "${extra[@]}" \
      -c "$I/virtualization/jobs/086-offline31ab/bootstrap.S" -o "$O/bootstrap-final/$name.o"
    ld --no-undefined --build-id=none -e test_bootstrap -Ttext=0x42000000 \
      "$O/bootstrap-final/$name.o" -o "$O/bootstrap-final/$name.elf"
    objcopy -O binary -j .text "$O/bootstrap-final/$name.elf" "$O/bootstrap-final/$name.bin"
  done
done
park=$(python3 -I -c 'import json; print(hex(json.load(open("/mnt/artifacts/host/layout.json"))["symbols"]["host_park"]["offset"]))')
python3 -I "$I/kernel/experiments/bootimage31ab/emulate.py" \
  --qemu /usr/bin/qemu-system-aarch64 --payload "$A/host/payload.bin" \
  --bootstrap-dir "$O/bootstrap-final" --park-offset "$park" --output "$O/emulation"
echo ORIGINAL31AB_INSTRUCTION_TESTS_PASS_NATIVE_NOT_RUN
