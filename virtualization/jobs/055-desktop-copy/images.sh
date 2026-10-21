#!/bin/bash
# Build a new matched pair from the exact working images. VM only.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux O=/mnt/job/out T=/run/copy31-image
exec > "$O/images.log" 2>&1
mkdir -p "$T" "$O/images"
mount -t tmpfs -o size=16G,mode=0755 tmpfs "$T"
trap 'umount "$T"' EXIT
mkdir -p "$T/root" "$T/stage1"
R=$T/root
echo '59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78  '"$I/build/attempt28-transfer/ramroot.cpio.zst" | sha256sum -c -
echo '65ea381524f266c78da0f98d42451f46fd48c94455d0734f1f6022c1d8f08c39  '"$I/build/attempt28-transfer/stage1.cpio.zst" | sha256sum -c -
bsdtar -xpf "$I/build/attempt28-transfer/ramroot.cpio.zst" -C "$R"
echo 'a9e57097798b2e815c8e91a0a4472d287573c4f7ce177b72a5b0907562a68da9  '"$R/usr/bin/Hyprland" | sha256sum -c -
A=$R/usr/local/lib/ilinux-desktop31
mkdir -p "$A"
install -m 0755 "$O/Hyprland-copy31" "$A/Hyprland-copy31"
install -m 0755 "$O/Hyprland-copy31" "$R/usr/bin/Hyprland"
install -m 0755 "$I/virtualization/jobs/054-desktop-latency/out/frameprobe" "$I/virtualization/jobs/054-desktop-latency/out/samplecpu" "$A/"
install -m 0644 "$I/kernel/experiments/desktop31/collect.py" "$I/kernel/experiments/desktop31/restore.py" "$A/"
install -m 0644 "$I/kernel/experiments/desktop30/collect.py" "$A/baseline.py"
python3 -I - "$A" "$O/images" <<'PY'
import hashlib,json,sys
from pathlib import Path
a=Path(sys.argv[1]); out=Path(sys.argv[2])
r={'attempt':31,'default_enabled':False,'frequency_writes':False,
   'base_hyprland_sha256':'a9e57097798b2e815c8e91a0a4472d287573c4f7ce177b72a5b0907562a68da9',
   'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.iterdir())}}
for p in (a/'assets.json',out/'assets.json'):p.write_text(json.dumps(r,indent=2)+'\n')
PY
test ! -e "$R/etc/ssh/ssh_host_ed25519_key"
test ! -e "$R/etc/pacman.d/gnupg"
test "$(find "$R/usr/lib/modules" -type f -name '*.ko*' | wc -l)" = 4
ENTRIES=$(find "$R" -mindepth 1 -printf . | wc -c)
USED=$(df -B1 --output=used "$T" | tail -1 | tr -d ' ')
(cd "$R" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort | cpio --quiet -o -H newc --reproducible) |
    zstd -q -T4 -19 --long=27 -c > "$O/images/ramroot.cpio.zst"
python3 -I - "$O/images" "$ENTRIES" "$USED" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]);p=out/'ramroot.cpio.zst';h=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
r={'schema':1,'profile':'omarchy','file':p.name,'size':p.stat().st_size,'sha256':h,
'image_sha256':'0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c',
'source':'Attempt28 root plus job055 opt-in original compositor final-copy experiment and collection assets',
'build':'No package upgrade; same login/config/kernel/modules; replaced Hyprland, added reviewed assets; zstd -19 --long=27',
'native_tested':False,'entries':int(sys.argv[2]),'unpacked_bytes_16k':int(sys.argv[3])}
(out/'omarchy-root-manifest.json').write_text(json.dumps(r,indent=2)+'\n')
keys=('size','sha256','image_sha256','entries','unpacked_bytes_16k')
(out/'stage2-pin.txt').write_text(''.join(f'{k}={r[k]}\n' for k in keys)+'source='+r['source']+'\n')
PY
bsdtar -xpf "$I/build/attempt28-transfer/stage1.cpio.zst" -C "$T/stage1"
cp "$O/images/stage2-pin.txt" "$T/stage1/etc/ilinux/stage2-pin"
(cd "$T/stage1" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort | cpio --quiet -o -H newc --reproducible) |
    zstd -q -T4 -19 --long=27 -c > "$O/images/stage1.cpio.zst"
python3 -I - "$O/images" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]);p=out/'stage1.cpio.zst';second=json.loads((out/'omarchy-root-manifest.json').read_text())
r={'schema':1,'profile':'ramroot','file':'ramroot.cpio.zst','size':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),
'image_sha256':second['image_sha256'],'source':'Attempt28 stage one; only the root pairing pin changes for attempt31',
'stage2':{k:second[k] for k in ('size','sha256','image_sha256','entries','unpacked_bytes_16k')},'native_tested':False}
(out/'ramroot-manifest.json').write_text(json.dumps(r,indent=2)+'\n')
PY
echo 'IMAGE-BUILD-PASS; native NOT RUN'
