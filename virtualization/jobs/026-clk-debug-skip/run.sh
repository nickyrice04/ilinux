#!/bin/bash
set -euo pipefail
mkdir -p /mnt/ilinux
mount -t virtiofs ilinux /mnt/ilinux
export M1N1_SOURCE=/var/tmp/ilinux-boot021/m1n1
python3 -I /mnt/ilinux/native/boot/test_launcher.py
python3 -I /mnt/ilinux/native/boot/test_entry_guard.py
python3 -I /mnt/ilinux/native/boot/test_dapf_guard.py
python3 -I /mnt/ilinux/native/boot/test_dapf_guard_adt.py
python3 -I /mnt/ilinux/native/boot/test_launcher_adt.py
python3 -I /mnt/ilinux/native/boot/test_protocol.py
python3 -I /mnt/ilinux/native/boot/test_framebuffer.py
python3 -I /mnt/ilinux/native/boot/launch.py --package /mnt/ilinux/build/native-boot025/verified
