#!/bin/sh
# Job 010: kernel v2 = Arch Linux ARM's FULL module config (extracted from the
# stock 7.1.6-1 Image via IKCONFIG) + 16K pages + uclamp + 9p +
# test_power, no debug info.  localmodconfig was dropped: trimming modules
# broke Omarchy's ufw (missing ip6 netfilter) and with it all networking.
set -x
OUT=/mnt/job/out
V=7.1.6
uname -r
mkdir -p /mnt/integ && mount -t virtiofs integ /mnt/integ || exit 1
# Arch's "Clean up modules from old kernels" service deletes /usr/lib/modules
# dirs no package owns - it removed our custom kernel's modules (and with them
# the NIC driver).  Mask it until the kernel is packaged.
systemctl list-unit-files | grep -iE 'modules.*clean|clean.*modules' > $OUT/cleanup-units.txt
for u in $(awk '{print $1}' $OUT/cleanup-units.txt); do systemctl mask "$u"; done
ls /usr/lib/modules > $OUT/modules-before.txt
# Offline build from the cached tarball, verified against kernel.org's
# published SHA-256 (fetched by the host over HTTPS into the job dir).
cd /root/kbuild || exit 1
echo "$(cat /mnt/job/kernel-sha256.txt)" | sha256sum -c - || { echo "TARBALL HASH MISMATCH"; exit 1; }
rm -rf linux-$V && tar -xf linux-$V.tar.xz && cd linux-$V
./scripts/extract-ikconfig /mnt/integ/virtualization/images/alarm/Image > .config || exit 1
grep -c '=m' .config > $OUT/module-count-stock.txt
scripts/config --set-str LOCALVERSION "-vzrun2" \
  -e UCLAMP_TASK -e UCLAMP_TASK_GROUP --set-val UCLAMP_BUCKETS_COUNT 20 \
  -d ARM64_4K_PAGES -e ARM64_16K_PAGES -e CPU_FREQ_DEFAULT_GOV_SCHEDUTIL \
  -d DEBUG_INFO -d DEBUG_INFO_DWARF5 -d DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT -e DEBUG_INFO_NONE -d DEBUG_INFO_BTF \
  -e VIRTIO_VSOCKETS -e VSOCKETS -m NET_9P -m NET_9P_VIRTIO -m 9P_FS -e 9P_FS_POSIX_ACL \
  -m TEST_POWER -m SND_HDA_CODEC_GENERIC -m DRM_VIRTIO_GPU -m VIRTIO_INPUT -m VIRTIO_BALLOON \
  -e VIRTIO_NET -e VIRTIO_FS -e FUSE_FS -e NET_9P -e NET_9P_VIRTIO -e 9P_FS -e VIRTIO_CONSOLE -e VIRTIO_BLK
make olddefconfig > /dev/null 2>&1
grep -E 'CONFIG_(UCLAMP_TASK_GROUP|ARM64_16K_PAGES|9P_FS|TEST_POWER|IP6_NF_FILTER|NFT_COMPAT|DRM_VIRTIO_GPU|DEBUG_INFO_NONE)=' .config > $OUT/config-summary.txt
cp .config $OUT/config-7.1.6-vzrun2
start=$(date +%s)
make -j18 Image modules > $OUT/build.log 2>&1 || { tail -40 $OUT/build.log; exit 1; }
echo "build seconds: $(( $(date +%s) - start ))" | tee $OUT/build-time.txt
make modules_install > $OUT/modules_install.log 2>&1
cp arch/arm64/boot/Image $OUT/Image-$V-vzrun2-16k
cd /root/kbuild && rm -rf linux-$V
# --- guest integration: battery bridge, 9p-capable job runner, VM DNS
{
  install -m 755 /mnt/integ/omarchy-arm64/configuration/vm-integration/bin/ilinux-battery-bridge /usr/local/bin/
  install -m 644 /mnt/integ/omarchy-arm64/configuration/vm-integration/systemd/ilinux-battery-bridge.service /etc/systemd/system/
  install -m 755 /mnt/integ/virtualization/guest/vzjob /usr/local/sbin/vzjob
  systemctl enable ilinux-battery-bridge.service
}
df -h / > $OUT/df.txt
