#!/bin/bash
set -euo pipefail
O=/mnt/job/out
mkdir -p "$O" /mnt/ilinux
exec > "$O/detail.log" 2>&1
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
systemctl mask --runtime docker.service docker.socket
systemctl stop docker.service docker.socket
if ip link show docker0 >/dev/null 2>&1; then ip link delete docker0; fi
python3 -I /mnt/job/check_wrapper.py
printf '%s\n' ILINUX_NOV12_SYNTHETIC_FORMAT_CHECK_PASS
