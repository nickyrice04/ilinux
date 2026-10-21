#!/bin/bash
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out W=/run/smp31
mkdir -p "$I"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mkdir -p /mnt/m1n1-source
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
mkdir -p "$O" "$W"
if [ "$(cat "$O/mode" 2>/dev/null || echo build)" = parser ]; then
  exec > "$O/parser.log" 2>&1
  python3 -I "$I/kernel/experiments/smp31/test_parser_vm.py" /mnt/m1n1-source/proxyclient
  python3 -I "$I/native/boot/test_smp31_census.py"
  echo SMP31-PARSER-PASS
  exit 0
fi
exec > "$O/build.log" 2>&1
trap 'cd /; umount "$W"' EXIT
mount -t tmpfs -o size=4G tmpfs "$W"
python3 -I "$I/kernel/experiments/smp31/prepare.py" /mnt/m1n1-source "$W/m1n1"
cp "$I/kernel/experiments/smp31/test_start.c" "$W/"
cp "$I/kernel/experiments/smp31/layout31.h" "$W/"
python3 -I - "$W" <<'PY'
import re, sys
from pathlib import Path
w=Path(sys.argv[1]); s=(w/'m1n1/src/smp.c').read_text()
out=[]
for name in ('smp31_start_mask', 'smp_start_cpu', 'smp31_start_one'):
 m=re.search(r'^(?:static )?(?:u32|void|int) '+name+r'\([^;]*?\n\{.*?^}\n',s,re.M|re.S)
 if m is None: raise ValueError('function absent: '+name)
 out.append(m.group())
(w/'startup.inc').write_text('\n'.join(out))
PY
gcc -O2 -Wall -Wextra -Werror -o "$W/test-start" "$W/test_start.c"
gcc -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -o "$W/test-asan" "$W/test_start.c"
for test in bad-chip bad-layout bad-core bad-impl bad-primary-impl bad-start-base unlocked primary-mismatch secondary-mismatch lock-clear already-alive retry timeout match; do
  "$W/test-start" "$test"
  "$W/test-asan" "$test"
done
gcc -O2 -std=c11 -Wall -Wextra -Werror -pthread -o "$O/coherence" "$I/kernel/experiments/smp31/coherence.c"
timeout -k 1 8 taskset -c 0,1 "$O/coherence" > "$O/coherence.json"
set +e
timeout -k 1 8 taskset -c 0 "$O/coherence" > "$O/coherence-single.json"
rc=$?
set -e
test "$rc" = 77
python3 -I "$I/kernel/experiments/smp31/test_renderer.py"
python3 -I "$I/native/boot/test_smp31_census.py"
for cpus in 0 0-1 0-5; do
  taskset -c "$cpus" python3 -I "$I/kernel/experiments/smp31/renderer.py" -- python3 -c 'import os; print(os.environ["LP_NUM_THREADS"], sorted(os.sched_getaffinity(0)))'
done
cd "$W/m1n1"
export M1N1_VERSION_TAG=ilinux-smp31-OFFLINE
make -j6 ARCH= BUILDSTD=1 > "$O/m1n1-build.log" 2>&1
nm -an build/m1n1-raw.elf > "$O/symbols.txt"
grep -q ' T smp31_start_one$' "$O/symbols.txt"
cp build/m1n1.bin "$O/m1n1-OFFLINE.bin"
cp src/smp.c "$O/smp.c"
sha256sum "$O/m1n1-OFFLINE.bin" "$O/coherence" "$O/smp.c" > "$O/artifacts.sha256"
{ gcc --version | head -1; rustc --version; uname -srm; } > "$O/toolchain.txt"
echo SMP31-OFFLINE-PASS
