#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux
O=/mnt/job/out
exec > "$O/detail.log" 2>&1
cc -O2 -Wall -Wextra -Werror "$I/kernel/experiments/desktop31/copybench.c" -lEGL -lGLESv2 -o "$O/copybench"
LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=0 taskset -c 0 "$O/copybench" > "$O/copybench.jsonl"
