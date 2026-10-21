#!/bin/bash
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" /mnt/m1n1-source "$O"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
exec > "$O/validation.log" 2>&1
python3 -I "$I/native/boot/smp31c.py" --image "$O/boot021.bin"
python3 -I "$I/native/boot/test_smp31c.py" --real-parser /mnt/m1n1-source/proxyclient
python3 -I "$I/kernel/experiments/smp31/test_client31c_vm.py" /mnt/m1n1-source/proxyclient
python3 -I "$I/tools/m1n1-client/test_attempt31c_supervise.py"
python3 -I "$I/native/boot/test_smp31b.py"
python3 -I "$I/tools/m1n1-client/test_attempt31b_supervise.py"
python3 -I "$I/native/boot/test_smp31_census.py"
python3 -I "$I/kernel/experiments/smp31/test_audit_boot021.py"
python3 -I "$I/kernel/experiments/smp31/test_renderer.py"
python3 --version
uname -srm
echo SMP31C-OFFLINE-PASS
