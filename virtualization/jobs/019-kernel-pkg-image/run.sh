#!/bin/sh
# Job 019: copy the packaged VM kernel (linux-ilinux-vm) out of the guest so
# the host boots exactly the Image whose modules pacman now owns.
set -x
OUT=/mnt/job/out
pacman -Qi linux-ilinux-vm | grep -E '^(Name|Version|Install Date)' > $OUT/package.txt
for f in /usr/share/linux-ilinux-vm/Image-*; do
  cp "$f" $OUT/ && sha256sum "$f" >> $OUT/image-sha256.txt
done
uname -r > $OUT/running-kernel.txt
