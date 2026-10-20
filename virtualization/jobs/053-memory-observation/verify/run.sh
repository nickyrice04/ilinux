#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux /mnt/job/out
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
exec > /mnt/job/out/detail.log 2>&1
S=/mnt/ilinux/kernel/experiments/memory29
B=/mnt/ilinux/virtualization/jobs/053-memory-observation/out
W=/var/tmp/ilinux-memory29-verify
mkdir -p "$W/root" /usr/local/lib/ilinux-cpu28
mkdir -p "$W/control"
cp "$S/Makefile" "$W/control/"
python3 -I - <<'PY'
from pathlib import Path
s=Path('/mnt/ilinux/kernel/experiments/memory29/ilinux_mem29.c').read_text()
a=s.index('\tif (!of_machine_is_compatible');b=s.index('\tsctlr = read_sysreg',a)
s=s[:a]+'''\tif (num_online_cpus() != 1)
\t\treturn -ENODEV;
\tcpu = get_cpu();
\tmidr = read_sysreg(midr_el1);
\tmpidr = read_sysreg(mpidr_el1);
\t(void)cpu; (void)midr; (void)mpidr;
'''+s[b:]
Path('/var/tmp/ilinux-memory29-verify/control/ilinux_mem29.c').write_text(s)
PY
make -C /var/tmp/ilinux-boot042/linux M="$W/control" W=1 modules
cp "$W/control/ilinux_mem29.ko" "$W/root/control.ko"
cp /mnt/ilinux/kernel/experiments/cpufreq-t6050/observe28.py /mnt/ilinux/kernel/experiments/cpufreq-t6050/measurement.py /usr/local/lib/ilinux-cpu28/
cc -static -Os -Wall -Wextra -Werror "$S/vm_refusal.c" -o "$W/root/init"
cp "$B/ilinux_mem29.ko" "$W/root/"
(cd "$W/root" && find . -print0 | cpio --null -o -H newc --quiet | gzip -n -9) > /mnt/job/out/refusal.cpio.gz
python3 -I - <<'PY'
import hashlib, json, subprocess
from pathlib import Path
b=Path('/mnt/ilinux/virtualization/jobs/053-memory-observation/out/memory29.tar').read_bytes()
command=['python3','-I','/mnt/ilinux/kernel/experiments/memory29/receive.py',str(len(b)),hashlib.sha256(b).hexdigest()]
r=subprocess.run(command,input=b,capture_output=True,timeout=15)
Path('/mnt/job/out/receiver.stdout').write_bytes(r.stdout)
Path('/mnt/job/out/receiver.stderr').write_bytes(r.stderr)
assert r.returncode==3,(r.returncode,r.stderr)
last=json.loads(r.stdout.splitlines()[-1]);assert last['event']=='stop',last
if Path('/sys/firmware/devicetree/base/compatible').exists():
 assert last['reason']=='not this J716c/t6050',last
else:
 assert last['reason']=="[Errno 2] No such file or directory: '/sys/firmware/devicetree/base/compatible'",last
assert not Path('/sys/module/ilinux_mem29').exists()
assert hashlib.sha256(Path('/run/ilinux-memory29/memory29').read_bytes()).hexdigest()==json.loads(Path('/mnt/ilinux/native/boot/attempt29/assets.json').read_text())['sha256']['memory29']
r2=subprocess.run(command,input=b,capture_output=True,timeout=15)
assert r2.returncode!=0 and b'FileExistsError' in r2.stderr
print('PASS real bundle receiver/extraction/exec; collector refuses virtual board before module; repeated extraction refused')
PY
P=/var/tmp/ilinux-cpu28-controller-venv
M1N1_SOURCE=/mnt/m1n1-source
mountpoint -q "$M1N1_SOURCE" || mount -t virtiofs m1n1-source "$M1N1_SOURCE"
export M1N1_SOURCE ILINUX_BOOT042=/mnt/ilinux/build/native-boot042/verified
"$P/bin/python" -I - <<'PY'
import sys,unittest
sys.path.insert(0,'/mnt/ilinux/native/boot')
names=['test_launcher','test_launcher_adt','test_hardware','test_dapf_guard','test_dapf_guard_adt','test_entry_guard','test_framebuffer','test_gpio_guard','test_protocol','test_ramroot','test_cpu_observe','test_usb_dt','test_mtp_input','test_control_channel']
r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names));sys.exit(not r.wasSuccessful())
PY
python3 -I /mnt/ilinux/tools/m1n1-client/test_attempt29_collect.py
echo 'PASS memory29 integration and controller tests; native NOT RUN'
