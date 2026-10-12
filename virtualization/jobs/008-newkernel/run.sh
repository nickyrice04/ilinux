#!/bin/sh
# Job 008: validate the custom 7.1.6-vzrun kernel (16K pages + uclamp).
OUT=/mnt/job/out
echo "== kernel"; uname -r; getconf PAGESIZE; grep -o 'sme2\|sme ' /proc/cpuinfo | sort -u | tr '\n' ' '; echo
echo "== uclamp files"; ls /sys/fs/cgroup/cpu.uclamp.* 2>&1; cat /proc/sys/kernel/sched_util_clamp_max 2>&1
mkdir -p /mnt/qos && mount -t virtiofs qos /mnt/qos && sh /mnt/qos/install.sh / > $OUT/qos-install.log 2>&1
systemctl daemon-reload; id tester >/dev/null 2>&1 || useradd -m tester; loginctl enable-linger tester; sleep 3
U=$(id -u tester)
runuser -u tester -- env XDG_RUNTIME_DIR=/run/user/$U DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$U/bus \
  sh -c 'systemctl --user daemon-reload; /mnt/qos/tests/test-qos.sh' > $OUT/qos-test.log 2>&1
echo "qos test exit=$?"; grep -E 'PASS|FAIL|SKIP|passed' $OUT/qos-test.log
cd /root && mkdir -p b && cp /mnt/job/src/*.c b/ && cd b
clang -O3 -mcpu=apple-m4 -pthread cpubench.c -o cpubench && clang -O3 -mcpu=apple-m4 -pthread membench.c -o membench
./membench latency -m 2048 >> $OUT/mem.jsonl
./membench fault -m 4096 -r 5 >> $OUT/mem.jsonl
for t in 1 6 18; do ./membench stream -t $t -m 1024 -r 10 >> $OUT/mem.jsonl; done
./cpubench syscall -r 7 >> $OUT/cpu.jsonl
./cpubench pingpong -r 3 -n 2000 >> $OUT/cpu.jsonl
./cpubench fma_asm -t 1 -r 3 >> $OUT/cpu.jsonl
echo "== idle for power measurement (60 s)"; date -u +%T; sleep 60; date -u +%T
