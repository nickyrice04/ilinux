#!/bin/sh
cd /root && clang -O2 -mcpu=apple-m4 /mnt/job/fma_asm.c -o fma_asm && ./fma_asm > /mnt/job/out/fma_asm.txt 2>&1
taskset -c 3 ./fma_asm >> /mnt/job/out/fma_asm.txt 2>&1
