#!/bin/sh
# Job 007: build a guest kernel = Linux 7.1.6 (GPG-verified kernel.org tarball)
# with the running ALARM config plus:
#   - CONFIG_UCLAMP_TASK / UCLAMP_TASK_GROUP (omarchy-qos clamps)
#   - 16K pages (matches native Apple Silicon Linux; fewer stage-2 faults)
#   - schedutil default governor, no debug info (faster build)
# Modules: localmodconfig after loading the modules a desktop VM needs.
set -x
OUT=/mnt/job/out
V=7.1.6
# Install the improved job runner (waits for DNS) into the guest for future jobs.
sed -i 's|^  mkdir -p /mnt/job/out$|  mkdir -p /mnt/job/out\n  for i in $(seq 1 60); do getent hosts arm-mirror.omarchy.org >/dev/null 2>\&1 \&\& break; sleep 1; done|' /usr/local/sbin/vzjob
for i in $(seq 1 60); do getent hosts arm-mirror.omarchy.org >/dev/null 2>&1 && break; sleep 1; done
pacman -Sy --noconfirm --needed base-devel bc cpio kmod libelf pahole perl python xz gnupg flex bison 2>&1 | tail -2
mkdir -p /root/kbuild && cd /root/kbuild
[ -f linux-$V.tar.xz ] || curl -fsSLO https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-$V.tar.xz
curl -fsSLO https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-$V.tar.sign
export GNUPGHOME=$(mktemp -d)
gpg --batch --auto-key-locate clear,wkd --locate-keys torvalds@kernel.org gregkh@kernel.org > $OUT/gpg-keys.log 2>&1
if xz -cd linux-$V.tar.xz | gpg --batch --status-fd 1 --verify linux-$V.tar.sign - 2>/dev/null | grep -q 'GOODSIG'; then
  echo "kernel tarball signature OK" | tee $OUT/signature.txt
else
  echo "SIGNATURE FAILED" | tee $OUT/signature.txt; exit 1
fi
rm -rf linux-$V && tar -xf linux-$V.tar.xz && cd linux-$V
zcat /proc/config.gz > .config
# make sure modules a desktop VM may need are loaded before localmodconfig
for m in virtiofs fuse virtio_net virtio_gpu virtio_input virtio_snd snd_hda_intel hid_generic usbhid xhci_pci uinput overlay \
         br_netfilter veth tun nf_tables nft_chain_nat nf_nat btrfs vfat nls_iso8859_1 nls_cp437 loop dm_crypt dm_mod \
         snd_seq snd_timer joydev evdev zram zstd lz4 af_packet vsock vmw_vsock_virtio_transport virtio_vsock; do
  modprobe $m 2>/dev/null
done
lsmod > $OUT/lsmod.txt
yes '' | make localmodconfig > $OUT/localmodconfig.log 2>&1
scripts/config --set-str LOCALVERSION "-vzrun" \
  -e UCLAMP_TASK -e UCLAMP_TASK_GROUP --set-val UCLAMP_BUCKETS_COUNT 20 \
  -d ARM64_4K_PAGES -e ARM64_16K_PAGES \
  -e CPU_FREQ_DEFAULT_GOV_SCHEDUTIL \
  -d DEBUG_INFO -d DEBUG_INFO_DWARF5 -d DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT -e DEBUG_INFO_NONE -d DEBUG_INFO_BTF \
  -e VIRTIO_VSOCKETS -e VSOCKETS -e VIRTIO_FS -e FUSE_FS \
  -e ZRAM -e CGROUP_SCHED -e FAIR_GROUP_SCHED -e CPUSETS -e SCHED_AUTOGROUP
make olddefconfig > /dev/null 2>&1
grep -E 'CONFIG_(UCLAMP_TASK|UCLAMP_TASK_GROUP|ARM64_16K_PAGES|ARM64_4K_PAGES|ARM64_VA_BITS|LOCALVERSION|VIRTIO_VSOCKETS|DEBUG_INFO_NONE|HZ)=' .config > $OUT/config-summary.txt
cp .config $OUT/config-7.1.6-vzrun
start=$(date +%s)
make -j18 Image modules > $OUT/build.log 2>&1 || { tail -40 $OUT/build.log; exit 1; }
echo "build seconds: $(( $(date +%s) - start ))" | tee $OUT/build-time.txt
make modules_install > $OUT/modules_install.log 2>&1
cp arch/arm64/boot/Image $OUT/Image-$V-vzrun-16k
ls -la /usr/lib/modules/ > $OUT/modules-dirs.txt
cd /root/kbuild && rm -rf linux-$V          # keep tarball, drop the build tree
df -h / > $OUT/df.txt
