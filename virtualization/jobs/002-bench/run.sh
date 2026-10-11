#!/bin/sh
# Job 002: toolchain + identical portable benchmarks inside the VM.
set -x
OUT=/mnt/job/out
pacman-key --init >/dev/null 2>&1
pacman-key --populate archlinuxarm >/dev/null 2>&1
pacman -Sy --noconfirm --needed clang make util-linux 2>&1 | tail -3
clang --version | head -1 > $OUT/toolchain.txt
mkdir -p /root/bench && cp /mnt/job/src/*.c /root/bench/ && cd /root/bench || exit 1
F="-O3 -mcpu=apple-m4 -pthread"
clang $F cpubench.c -o cpubench && clang $F membench.c -o membench && clang -O2 -mcpu=apple-m4 -pthread storbench.c -o storbench || exit 1
set +x
for k in freq fma intmix sort sgemm sme_f32 sme_bf16 sme_i8; do ./cpubench $k -t 1 -r 5 >> $OUT/cpu.jsonl; done
for t in 6 12 18; do for k in freq fma intmix sort sgemm; do ./cpubench $k -t $t -r 5 >> $OUT/cpu.jsonl; done; done
for t in 2 3 6 12 18; do for k in sme_f32 sme_i8; do ./cpubench $k -t $t -r 3 >> $OUT/cpu.jsonl; done; done
./cpubench pingpong -r 7 >> $OUT/cpu.jsonl
./cpubench syscall -r 7 >> $OUT/cpu.jsonl
for t in 1 2 4 6 12 18; do ./membench stream -t $t -m 1024 -r 10 >> $OUT/mem.jsonl; done
./membench latency -m 2048 >> $OUT/mem.jsonl
./membench latency -m 256 -d >> $OUT/mem.jsonl
./membench fault -m 4096 -r 5 >> $OUT/mem.jsonl
./storbench seqwrite /root/stor.dat -m 8192 >> $OUT/storage.jsonl
for t in 1 4; do ./storbench seqread /root/stor.dat -t $t >> $OUT/storage.jsonl; done
for t in 1 8 32; do ./storbench randread /root/stor.dat -t $t -s 8 >> $OUT/storage.jsonl; done
for t in 1 8; do ./storbench randwrite /root/stor.dat -t $t -s 5 >> $OUT/storage.jsonl; done
rm -f /root/stor.dat; fstrim -v / 2>&1 || true
uptime
