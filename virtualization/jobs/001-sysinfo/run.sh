#!/bin/sh
# Job 001: guest system facts relevant to parity work (read-only in guest).
echo "== uname"; uname -a
echo "== cpus"; nproc; grep -m1 -E '^Features' /proc/cpuinfo
echo "== cpuinfo per-cpu implementer/part (unique lines)"
grep -E 'CPU (implementer|architecture|variant|part|revision)' /proc/cpuinfo | sort | uniq -c
echo "== MIDR_EL1 per cpu (sysfs)"
for f in /sys/devices/system/cpu/cpu*/regs/identification/midr_el1; do echo "$(basename $(dirname $(dirname $(dirname $f)))) $(cat $f)"; done | sort -V | uniq -f1 -c
echo "== hwcap2 SME bits"; LD_SHOW_AUXV=1 /bin/true | grep -E 'AT_HWCAP2?|AT_PAGESZ'
echo "== cpu capacity"; cat /sys/devices/system/cpu/cpu*/cpu_capacity 2>/dev/null | sort | uniq -c
echo "== cpufreq"; ls /sys/devices/system/cpu/cpu0/cpufreq 2>&1 | head -3
echo "== memory"; free -g; getconf PAGESIZE
echo "== kernel config (uclamp/sme/eas/virtiofs)"
zcat /proc/config.gz 2>/dev/null | grep -E 'CONFIG_(UCLAMP_TASK|UCLAMP_TASK_GROUP|ARM64_SME|ARM64_SVE|ENERGY_MODEL|SCHED_MC|CPU_FREQ_GOV_SCHEDUTIL|VIRTIO_FS|ARM64_MTE|ARM64_16K_PAGES|ARM64_4K_PAGES|ARM64_64K_PAGES|TRANSPARENT_HUGEPAGE)=' 
echo "== sched_energy_aware"; cat /proc/sys/kernel/sched_energy_aware 2>&1
echo "== cgroup controllers"; cat /sys/fs/cgroup/cgroup.controllers
echo "== block devices"; lsblk -o NAME,SIZE,ROTA,SCHED,LOG-SEC,PHY-SEC 2>/dev/null
echo "== network"; ip -br addr; resolvectl status 2>/dev/null | head -5
echo "== dmesg (virt platform, gic, timer, errors)"
dmesg | grep -iE 'Machine model|GIC|arch_timer|psci|sme|sve|mte|error|fail' | head -40
