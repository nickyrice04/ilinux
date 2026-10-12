#!/bin/sh
# Job 013: migrate the ext4 root (/dev/vda) to Omarchy's btrfs layout on
# /dev/vdb: subvolumes @ @home @log @pkg, zstd:1 compression, noatime.
set -ex
OUT=/mnt/job/out
pacman -S --needed --noconfirm rsync btrfs-progs > /dev/null
mkfs.btrfs -f -L omarchy /dev/vdb > $OUT/mkfs.log
mkdir -p /target && mount -o compress=zstd:1,noatime /dev/vdb /target
for sv in @ @home @log @pkg; do btrfs subvolume create /target/$sv; done
rsync -aAXH --numeric-ids --info=stats1 \
  --exclude=/proc/ --exclude=/sys/ --exclude=/dev/ --exclude=/run/ --exclude=/tmp/ --exclude=/mnt/ \
  --exclude=/target/ --exclude=/home/ --exclude=/var/log/ --exclude=/var/cache/pacman/pkg/ \
  / /target/@/ > $OUT/rsync-root.log
rsync -aAXH --numeric-ids /home/ /target/@home/
rsync -aAXH --numeric-ids /var/log/ /target/@log/
rsync -aAXH --numeric-ids /var/cache/pacman/pkg/ /target/@pkg/
mkdir -p /target/@/proc /target/@/sys /target/@/dev /target/@/run /target/@/tmp /target/@/mnt \
         /target/@/home /target/@/var/log /target/@/var/cache/pacman/pkg
U=$(blkid -s UUID -o value /dev/vdb)
O=rw,noatime,compress=zstd:1,space_cache=v2
cat > /target/@/etc/fstab <<FSTAB
UUID=$U  /                      btrfs  $O,subvol=/@     0 0
UUID=$U  /home                  btrfs  $O,subvol=/@home 0 0
UUID=$U  /var/log               btrfs  $O,subvol=/@log  0 0
UUID=$U  /var/cache/pacman/pkg  btrfs  $O,subvol=/@pkg  0 0
FSTAB
btrfs filesystem df /target > $OUT/btrfs-df.txt
du -sh /target/@ > $OUT/du.txt 2>&1
sync; umount /target
