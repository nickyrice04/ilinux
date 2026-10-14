#!/bin/bash
# Run only inside the existing isolated ARM64 job VM. No native device access.
set -euo pipefail
mkdir -p /mnt/ilinux /mnt/m1n1-source /mnt/boot021
mount -t virtiofs ilinux /mnt/ilinux
mount -t virtiofs m1n1-source /mnt/m1n1-source
mount -t virtiofs boot021 /mnt/boot021
OUT=/mnt/job/out
test ! -e "$OUT/export"
mkdir "$OUT/export"
python3 -I - <<'PY'
import hashlib,json
from pathlib import Path
base=Path('/mnt/boot021')
manifest=json.loads(Path('/mnt/ilinux/native/boot/boot021-package-manifest.json').read_text())
for name,info in manifest['files'].items():
    b=(base/name).read_bytes()
    assert len(b)==info['size'] and hashlib.sha256(b).hexdigest()==info['sha256'], name
    (Path('/mnt/job/out/export')/name).write_bytes(b)
print('Boot021 baseline validated; copied only allowlisted payloads')
PY
DT="$OUT/export/t6050-j716c-stage-b.dtb"
fdtput -c "$DT" /chosen/framebuffer@0
fdtput -t s "$DT" /chosen/framebuffer@0 compatible apple,simple-framebuffer simple-framebuffer
fdtput -t x "$DT" /chosen/framebuffer@0 reg 0 0 0 0
fdtput -t s "$DT" /chosen/framebuffer@0 status disabled
dtc -I dtb -O dts "$DT" > "$OUT/stage-b.dts" 2> "$OUT/dtc.log"
python3 -I /mnt/ilinux/native/boot/test_framebuffer_fixup.py \
  --m1n1 /mnt/m1n1-source --baseline /mnt/boot021/t6050-j716c-stage-b.dtb \
  --corrected "$DT" --out "$OUT/regression"
python3 -I /mnt/ilinux/native/boot/test_launcher.py
M1N1_SOURCE=/mnt/m1n1-source python3 -I /mnt/ilinux/native/boot/test_protocol.py
{ uname -srm; gcc --version | head -1; dtc --version; python3 --version; } > "$OUT/test-toolchain.txt"
echo 'PASS: DT-only fix and real pinned framebuffer function tested in Linux VM'
