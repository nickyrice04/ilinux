#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux O=/mnt/job/out
exec > "$O/checks.log" 2>&1
python3 -I "$I/kernel/experiments/desktop31/test_desktop31.py"
python3 -I "$I/tools/m1n1-client/test_attempt31_collect.py"
ILINUX_BOOT042="$I/build/native-boot042/verified" /var/tmp/ilinux-cpu28-controller-venv/bin/python -I "$I/native/boot/test_cpu_observe.py"
python3 -I "$I/native/boot/test_ramroot.py"
{ cc --version | head -1; cmake --version | head -1; uname -srm;
  pacman -Q mesa llvm-libs wayland hyprutils aquamarine hyprwayland-scanner;
  git -C /var/tmp/ilinux-desktop31/build/_deps/glaze-src rev-parse HEAD;
} > "$O/toolchain.txt"
# Confirm ExecStopPost executes after a timeout independently of the main process.
rm -f /run/copy31-stop-marker
rc=0
systemd-run --unit=copy31-timeout-test --wait --collect --pipe --property=RuntimeMaxSec=1 \
  --property=TimeoutStopSec=5 --property=KillMode=control-group \
  '--property=ExecStopPost=/usr/bin/touch /run/copy31-stop-marker' /usr/bin/sleep 10 || rc=$?
test "$rc" != 0
test -f /run/copy31-stop-marker
echo 'SUPERVISOR-TIMEOUT-CLEANUP-PASS'
cc -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
  "$I/kernel/experiments/desktop31/copybench.c" -lEGL -lGLESv2 -o "$O/copybench-san"
ASAN_OPTIONS=detect_leaks=0 LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=0 taskset -c 0 \
  "$O/copybench-san" > "$O/copybench-san.jsonl"
echo 'CHECKS-PASS'
