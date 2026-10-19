#!/bin/bash
# make_test_disk.sh IMG: the storage set's 64 MiB virtual disk for ro_test (job 050, as root in the job VM).
# GPT with three partitions, laid out so that ro_test's write attempts (8-14 MiB) land in the first:
#   p1  1-17 MiB  APFS type GUID, random bytes (like the M5's containers: nothing Linux can mount)
#   p2 17-41 MiB  ext4 with a file, its superblock marked needs_recovery, so a mount wants to replay
#                 the journal, which is a write
#   p3 41-57 MiB  EFI System type, FAT with a file (when mkfs.fat is installed; else left empty)
# Prints the layout and the image's SHA-256. Test data only: no identifier of any machine.
set -euo pipefail
img=$1
rm -f "$img"
truncate -s 64M "$img"
sfdisk -q "$img" <<'EOF'
label: gpt
start=2048, size=32768, type=7C3457EF-0000-11AA-AA11-00306543ECAC, name="ro-test-apfs-like"
start=34816, size=49152, type=0FC63DAF-8483-4772-8E79-3D69D8477DE4, name="ro-test-ext4"
start=83968, size=32768, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B, name="ro-test-fat"
EOF
dd if=/dev/urandom of="$img" bs=1M seek=1 count=16 conv=notrunc status=none
loop=$(losetup --show -f -P "$img")
trap 'umount /tmp/ro-test-mnt 2> /dev/null || true; losetup -d "$loop" 2> /dev/null || true' EXIT
udevadm settle 2> /dev/null || true
for _ in $(seq 50); do [ -b "${loop}p3" ] && break; sleep 0.1; done
mkfs.ext4 -q -F -L ro-test "${loop}p2"
mkdir -p /tmp/ro-test-mnt
mount "${loop}p2" /tmp/ro-test-mnt
echo "ro_test ext4 file" > /tmp/ro-test-mnt/hello.txt
umount /tmp/ro-test-mnt
debugfs -w -R "feature needs_recovery" "${loop}p2" > /dev/null 2>&1
dumpe2fs -h "${loop}p2" 2> /dev/null | grep -E '^Filesystem features' | sed 's/^/p2 /'
if command -v mkfs.fat > /dev/null 2>&1; then
    mkfs.fat -n ROTEST "${loop}p3" > /dev/null
    mount "${loop}p3" /tmp/ro-test-mnt
    echo "ro_test fat file" > /tmp/ro-test-mnt/hello.txt
    umount /tmp/ro-test-mnt
    echo "p3 FAT with hello.txt"
else
    echo "p3 empty: no mkfs.fat in this VM"
fi
sync
losetup -d "$loop"
trap - EXIT
sfdisk -d "$img" | grep -E '^(label|start|/)' | sed -E 's/, uuid=[0-9A-Fa-f-]+//; /^label-id/d'
echo "test disk $(stat -c %s "$img") bytes, sha256 $(sha256sum < "$img" | cut -d' ' -f1)"
