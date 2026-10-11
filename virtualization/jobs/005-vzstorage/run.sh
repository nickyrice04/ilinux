#!/bin/sh
# Job 005: Virtualization.framework storage configurations.  The host writes
# config.txt (label) and boots vzrun with a second data disk using different
# --nvme / --disk-cache / --disk-sync settings; each boot appends its results.
OUT=/mnt/job/out; mkdir -p $OUT
LABEL=$(cat /mnt/job/config.txt)
DEV=/dev/vdb; [ -b /dev/nvme0n1 ] && DEV=/dev/nvme0n1
blkid $DEV >/dev/null 2>&1 || mkfs.ext4 -q -F $DEV
mkdir -p /data && mount -o noatime $DEV /data || exit 1
B=/root/bench/storbench
[ -f /data/stor.dat ] || $B seqwrite /data/stor.dat -m 4096 > /dev/null   # first-allocation pass
R=$OUT/storage-$LABEL.jsonl
$B seqwrite /data/stor.dat -m 4096 >> $R
$B seqread /data/stor.dat -t 1 >> $R
$B seqread /data/stor.dat -t 4 >> $R
$B randread /data/stor.dat -t 1 -s 5 >> $R
$B randread /data/stor.dat -t 32 -s 5 >> $R
$B randwrite /data/stor.dat -t 8 -s 3 >> $R
echo "$LABEL dev=$DEV $(cat /sys/block/$(basename $DEV)/queue/scheduler 2>/dev/null)" >> $OUT/devices.txt
umount /data
