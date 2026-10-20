#!/bin/bash
# Offline tests only, in the existing VM. No target USB is passed through.
set -euo pipefail
mkdir -p /mnt/ilinux /mnt/m1n1-source /mnt/job/out
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
exec > /mnt/job/out/detail.log 2>&1
export M1N1_SOURCE=/mnt/m1n1-source
export ILINUX_BOOT042=/mnt/ilinux/build/native-boot042/verified
export GIT_CONFIG_COUNT=2 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/mnt/ilinux
export GIT_CONFIG_KEY_1=safe.directory GIT_CONFIG_VALUE_1=/mnt/m1n1-source
cd /mnt/ilinux
test "$(git -C "$M1N1_SOURCE" rev-parse HEAD)" = 57a9339ffd1876e78297b17d34dece8cff8fa1ba
P=/var/tmp/ilinux-cpu28-controller-venv
python3 -m venv "$P"
"$P/bin/python" -I -m pip install --disable-pip-version-check -r "$M1N1_SOURCE/requirements.txt"
"$P/bin/python" -I -m pip freeze
python3 -I - <<'PY'
import hashlib, json
from pathlib import Path
a = json.loads(Path('/mnt/ilinux/native/boot/attempt28/assets.json').read_text())
p = Path('/var/tmp/ilinux-cpu28-build/chase_short')
assert hashlib.sha256(p.read_bytes()).hexdigest() == a['sha256']['chase_short']
PY
/var/tmp/ilinux-cpu28-build/chase_short > /mnt/job/out/chase-optimized.jsonl
objdump -d /var/tmp/ilinux-cpu28-build/chase_short > /mnt/job/out/chase-optimized.asm
python3 -I - <<'PY'
import json
from pathlib import Path
r = [json.loads(s) for s in Path('/mnt/job/out/chase-optimized.jsonl').read_text().splitlines()]
assert len(r) == 12 and all(x['ns_per_load'] > 0 for x in r)
print('PASS exact shipping optimized pointer chase: 12 VM samples; not native results')
PY
"$P/bin/python" -I - <<'PY'
import sys, unittest
sys.path.insert(0, '/mnt/ilinux/native/boot')
names = ['test_launcher', 'test_launcher_adt', 'test_hardware',
         'test_dapf_guard', 'test_dapf_guard_adt', 'test_entry_guard',
         'test_framebuffer', 'test_gpio_guard', 'test_protocol',
         'test_ramroot', 'test_cpu_observe', 'test_usb_dt',
         'test_mtp_input', 'test_control_channel']
r = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
sys.exit(not r.wasSuccessful())
PY
python3 -I kernel/experiments/cpufreq-t6050/test_observe28.py
python3 -I tools/m1n1-client/test_attempt28_collect.py
echo 'PASS offline controller tests; no native hardware accessed'
