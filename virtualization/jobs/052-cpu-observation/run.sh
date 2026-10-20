#!/bin/bash
# Build attempt 28 in the existing isolated VM. No downloads or native MMIO.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux
X=$I/kernel/experiments/cpufreq-t6050
OUT=/mnt/job/out
K=/var/tmp/ilinux-boot042/linux
B=/var/tmp/ilinux-cpu28-build
T=/run/ilinux-cpu28
mkdir -p "$OUT/build" "$OUT/stage2" "$B/drivers/cpufreq" "$T"
exec > "$OUT/build/detail.log" 2>&1
set -x
trap 'mountpoint -q "$T" && umount "$T" || true' EXIT
cmp "$K/.config" "$I/build/native-boot042/verified/kernel.config"
cmp "$K/arch/arm64/boot/Image" "$I/build/native-boot042/verified/Image"
grep -q '^CONFIG_CPU_FREQ_GOV_USERSPACE=y$' "$K/.config"
grep -n -E 'default_governor|module_param' "$K/drivers/cpufreq/cpufreq.c" > "$OUT/build/governor-source.txt"
grep -q 'module_param_string(default_governor,' "$OUT/build/governor-source.txt"
cp "$K/drivers/cpufreq/apple-soc-cpufreq.c" "$B/drivers/cpufreq/"
echo 'e4efe79b653dc07c18a2bacc607fe69f8144ead11bf10cd4ef9407396ca808d2  '"$B/drivers/cpufreq/apple-soc-cpufreq.c" | sha256sum -c -
patch --batch --fuzz=0 -d "$B" -p1 < "$X/patches/0001-cpufreq-apple-soc-cpufreq-t6050-M5-Max-cluster-DVFS.patch"
printf 'obj-m := apple-soc-cpufreq.o\n' > "$B/drivers/cpufreq/Makefile"
make -C "$K" M="$B/drivers/cpufreq" -j2 W=1 modules > "$OUT/build/module-build.log" 2>&1
! grep -E 'warning:|error:' "$OUT/build/module-build.log"
cp "$B/drivers/cpufreq/apple-soc-cpufreq.c" "$OUT/build/driver.c"
python3 -I "$X/test_driver.py" "$B/drivers/cpufreq/apple-soc-cpufreq.c" "$B/tests" > "$OUT/build/driver-tests.log" 2>&1
modinfo "$B/drivers/cpufreq/apple-soc-cpufreq.ko" > "$OUT/build/modinfo.txt"
objdump -dr "$B/drivers/cpufreq/apple-soc-cpufreq.ko" > "$OUT/build/module-disassembly.txt"
for n in cpubench membench; do
    gcc -O3 -march=armv8.4-a -pthread "$I/benchmarks/src/$n.c" -o "$B/$n" > "$OUT/build/$n-build.log" 2>&1
done
gcc -O3 -march=armv8.4-a -Wall -Wextra -Werror "$X/chase_short.c" -o "$B/chase_short"
gcc -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined "$X/chase_short.c" -o "$B/chase-sanitizer"
"$B/chase-sanitizer" > "$OUT/build/chase-sanitizer.jsonl"
for n in freq fma_asm intmix; do "$B/cpubench" "$n" -t 1 -r 3 -s 0.2 > "$OUT/build/$n-vm.jsonl"; done
"$B/membench" stream -t 1 -m 128 -r 3 > "$OUT/build/stream-vm.jsonl"
python3 -I "$X/test_observe28.py" > "$OUT/build/collector-tests.log" 2>&1
{ gcc --version | head -1; ld --version | head -1; python3 --version; zstd --version; uname -srm; } > "$OUT/build/toolchain.txt"
echo 'building root from the pinned attempt27 image'
echo '5eaa2fdb52dcbbaf20b4a9780f7d23e625535e3f5386f1659ed332fb7826d345  '"$I/build/attempt27-transfer/ramroot.cpio.zst" | sha256sum -c -
echo '84c01f536516b85939f6ead55e37d0a9fa4838414edb84e033aef221f6006ed3  '"$I/build/attempt27-transfer/stage1.cpio.zst" | sha256sum -c -
mount -t tmpfs -o size=15G,mode=0755 tmpfs "$T"
mkdir -p "$T/root" "$T/stage1"
bsdtar -x -p --numeric-owner -f "$I/build/attempt27-transfer/ramroot.cpio.zst" -C "$T/root"
R=$T/root
A=$R/usr/local/lib/ilinux-cpu28
mkdir -p "$A"
install -m 0644 "$B/drivers/cpufreq/apple-soc-cpufreq.ko" "$A/"
install -m 0755 "$B/cpubench" "$B/membench" "$B/chase_short" "$A/"
install -m 0644 "$X/measurement.py" "$X/observe28.py" "$A/"
python3 -I - "$A" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); names=sorted(x.name for x in p.iterdir())
r={'attempt':28,'frequency_writes':False,'kernel':'7.1.9-g863199d8b4a3-dirty',
   'compiler_flags':'-O3 -march=armv8.4-a; pthread for existing CPU/memory benchmarks',
   'sha256':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names}}
(p/'assets.json').write_text(json.dumps(r,indent=2)+'\n')
PY
cp "$A/assets.json" "$OUT/assets.json"
printf '\ncpu experiment attempt28: command-only observation; no DVFS writes; job052\n' >> "$R/usr/share/ilinux/build-info.txt"
# No new module alias/index: the collector alone loads the file by exact path.
test "$(find "$R/usr/lib/modules" -type f -name '*.ko*' | wc -l)" = 4
test ! -e "$R/etc/ssh/ssh_host_ed25519_key"
test ! -e "$R/etc/pacman.d/gnupg"
find "$A" -type f -name '*private*' > "$OUT/build/unexpected-private.txt"
test ! -s "$OUT/build/unexpected-private.txt"
python3 -I - "$R" "$OUT/build/root-content.json" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
p=Path(sys.argv[1]); assets=json.loads((p/'usr/local/lib/ilinux-cpu28/assets.json').read_text())
assert not any(p.glob('etc/ssh/ssh_host_*'))
assert all(line.split(':')[1].startswith(('!','*')) for line in (p/'etc/shadow').read_text().splitlines() if line.startswith(('root:','omarchy:')))
assert (p/'etc/systemd/system/multi-user.target.wants/ilinux-keyboard.service').is_symlink()
json.dump({'module_path':'/usr/local/lib/ilinux-cpu28/apple-soc-cpufreq.ko','module_auto_load':False,
           'host_keys':False,'locked_passwords':True,'base_root':'5eaa2fdb52dcbbaf20b4a9780f7d23e625535e3f5386f1659ed332fb7826d345',
           'assets':assets},open(sys.argv[2],'w'),indent=2)
PY
(cd "$R" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort | cpio --quiet -o -H newc --reproducible) |
    zstd -q -T4 -19 --long=27 -c > "$OUT/stage2/ramroot.cpio.zst"
ENTRIES=$(find "$R" -mindepth 1 -printf . | wc -c)
# Count the root alone on the 16-KiB tmpfs before unpacking stage one.
USED=$(df -B1 --output=used "$T" | tail -1 | tr -d ' ')
python3 -I - "$OUT" "$ENTRIES" "$USED" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]); p=out/'stage2/ramroot.cpio.zst'
h=hashlib.sha256()
with p.open('rb') as f:
 for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
r={'schema':1,'profile':'omarchy','file':'ramroot.cpio.zst','size':p.stat().st_size,'sha256':h.hexdigest(),
'image_sha256':'0b6df39566f12bcd5957e649946125a7bb0f42f31690933dc9896a2565b9b69c',
'source':'VM job045 attempt27 root plus job052 attempt28 CPU observation assets',
'build':'Pinned prior root, added explicit no-write collector/module/benchmarks; no package upgrade; zstd -19 --long=27',
'native_tested':False,'entries':int(sys.argv[2]),'unpacked_bytes_16k':int(sys.argv[3])}
(out/'omarchy-root-manifest.json').write_text(json.dumps(r,indent=2)+'\n')
pin={k:r[k] for k in ('size','sha256','image_sha256','entries','unpacked_bytes_16k')}
(out/'stage2-pin.txt').write_text(''.join(f'{k}={v}\n' for k,v in pin.items())+'source='+r['source']+'\n')
PY
bsdtar -x -p --numeric-owner -f "$I/build/attempt27-transfer/stage1.cpio.zst" -C "$T/stage1"
cp "$OUT/stage2-pin.txt" "$T/stage1/etc/ilinux/stage2-pin"
# Stage one's only runtime-content change is the pin; keep all other files.
(cd "$T/stage1" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort | cpio --quiet -o -H newc --reproducible) |
    zstd -q -T4 -19 --long=27 -c > "$OUT/stage1.cpio.zst"
python3 -I - "$OUT" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]); p=out/'stage1.cpio.zst'; second=json.loads((out/'omarchy-root-manifest.json').read_text())
r={'schema':1,'profile':'ramroot','file':'ramroot.cpio.zst','size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
'image_sha256':second['image_sha256'],'source':'VM job052 attempt28 stage one; attempt27 files with the new root pin',
'stage2':{k:second[k] for k in ('size','sha256','image_sha256','entries','unpacked_bytes_16k')},'native_tested':False}
(out/'ramroot-manifest.json').write_text(json.dumps(r,indent=2)+'\n')
PY
{ echo 'build-info:'; sed 's/^/  /' "$R/usr/share/ilinux/build-info.txt"; echo 'init:'; } > "$OUT/build/stage2-unpacked.txt"
cp "$I/virtualization/jobs/049-two-stage-boot/out/build/test-base.cpio.zst" "$OUT/build/"
(cd "$OUT" && sha256sum stage1.cpio.zst > stage1.cpio.zst.sha256)
cmp "$K/.config" "$I/build/native-boot042/verified/kernel.config"
cmp "$K/arch/arm64/boot/Image" "$I/build/native-boot042/verified/Image"
echo 'PASS build and offline tests; native NOT RUN' > "$OUT/build/summary.txt"
