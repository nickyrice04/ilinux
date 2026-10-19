#!/bin/bash
# Job 050: the boot042 kernel. boot041's tree (a copy of job 041's, checked to be the one that built
# boot041's Image) plus the MTP keyboard transport,
# with the keyboard path and the storage drivers as loadable modules, so that nothing of either binds
# while the kernel boots (attempt 26 loads the keyboard modules over SSH, one at a time).
#  1. inputs; the copy of job 041's tree holds boot041's Image, kernel.config and patched apple-dart.c;
#  2. the storage drivers brought to the current kernel/patches/t6050 0002-0005 (a clean worktree of the
#     pinned base with the series applied by git am; only sart.c and apple.c are C files), and the
#     iLinux read-only patch for nvme-core (kernel/experiments/nvme-ans3/storage-ro/0001);
#  3. dockchannel-hid 0001 (input bounds) and 0002 (the MTP ring transport), as job 042 applied them;
#  4. config: the keyboard path and the storage drivers m, HIDRAW y (check_config_delta.py: exactly that);
#  5. the changed objects with W=1 (no warning in our files), Image and modules, symbol checks: no
#     keyboard or storage driver left in vmlinux, the gadget stack and the DART diagnostics still in it;
#  6. the kernel facts the attempt-26 checklist relies on (boot042-modules/check_facts.py);
#  7. boot042's Stage-B DT rebuilt here from boot041's with make_mtp_dt.py (streams 0-4), equal to
#     the one the Mac builds; dtc and dt-validate;
#  8. the module sets (keyboard: shipped in the attempt-26 root; trackpad and storage: kept apart, never
#     in the attempt-26 root), each with its dependencies, digests and a manifest;
#  9. the storage set's VM test pieces: ro_test (static, PID 1), its initramfs with nvme-core, nvme (PCI)
#     and nvme-core's VM control build (ILINUX_RO_CONTROL, the one build whose read-only mode can be
#     turned off, never in a module set), and a 64 MiB test disk (GPT: random bytes, ext4 asking for
#     journal recovery, FAT).
# The boots run on the Mac (no lock): liveness and the storage test (run-vz-*.sh in this directory).
# Nothing here touches the M5, an earlier tree or package; every build is in /var/tmp/ilinux-boot042.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
I=/mnt/ilinux
X=$I/kernel/experiments
K41=/var/tmp/ilinux-boot036/linux          # job 041's tree: built boot041's Image; copied, never changed
DART041_C=b3eb0da83235164e2d514c106ec134d6e24c335ba6e36e0124534fb60ca9b288   # job 041's patched apple-dart.c
B41=$I/build/native-boot041/verified
V=/var/tmp/ilinux-boot042
WORK=$V/linux
SERIES=$V/series
BASE=/var/tmp/t6050-build/linux            # job 020's clone of the pinned Asahi tree
BASE_COMMIT=77cb8f24c2381a8abb7272d7bbdec548d6426a8a
BOOT041_IMAGE=a53d1d47467480d4b56d87c7b1365e9a5c28fd9ee9e5f0164a3e734f85526ad9
DRV=drivers/hid/dockchannel-hid/dockchannel-hid.c
PIN_SHA=15c1186c3bbb87dddb75c1f1053ab3a2c3a2a1128bba6718bd88977f4b7beb2f      # pinned dockchannel-hid.c
P0001_SHA=e888ddaefc7d05f582b1db831ec9f2bd2e9858f4503242edf7c369866c45605c    # + 0001
P0002_SHA=01c56449                                                            # + 0002 (job 042's prefix)
EPOCH=1760486400                                                              # job 041's fixed build time
JOBS=$(nproc)
log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
rm -rf "$OUT/build" "$OUT/export"
mkdir -p "$OUT/build" "$OUT/export" "$V"
exec > "$OUT/script.log" 2>&1     # run.log only gets the runner's own lines
B=$OUT/build

log "1. inputs and the baseline"
(cd "$B41" && sha256sum -c --quiet SHA256SUMS)
{ uname -srm; gcc --version | head -1; ld --version | head -1; dtc --version; python3 --version
  pacman -V | sed -n 2p; } > "$B/vm-tools.txt"
# The base is job 041's own tree, copied (it is never built in or changed here). It is boot041's: the
# Image it built is boot041's, its .config is boot041's kernel.config and its apple-dart.c is the patched
# file job 041 recorded. A rebuild cannot show more: the build ID in the Image's notes hashes the debug
# information, which names the tree's directory, so the same sources give other bytes at another path
# (job 047 found the same). boot042's Image is reproducible at this job's own path instead.
test "$(sha256sum < "$K41/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$BOOT041_IMAGE"
cmp "$K41/.config" "$B41/kernel.config"
test "$(sha256sum < "$K41/drivers/iommu/apple-dart.c" | cut -d' ' -f1)" = "$DART041_C"
rm -rf "$WORK"
cp -a --reflink=auto "$K41" "$WORK"
cd "$WORK"
test "$(sha256sum < arch/arm64/boot/Image | cut -d' ' -f1)" = "$BOOT041_IMAGE"
cmp .config "$B41/kernel.config"
echo "baseline: a copy of job 041's tree: its Image is boot041's ($BOOT041_IMAGE), its .config boot041's kernel.config, its apple-dart.c job 041's ($DART041_C)" | tee "$B/baseline.txt"
# boot042's own build identity (/proc/version names ilinux@boot042)
export KBUILD_BUILD_TIMESTAMP="@$EPOCH" KBUILD_BUILD_USER=ilinux KBUILD_BUILD_HOST=boot042

log "2. storage drivers: the current kernel/patches/t6050 series and the read-only patch"
[ -d "$BASE/.git" ] || { echo "no base tree at $BASE (job 020's): stopping, no fetch"; exit 1; }
git -C "$BASE" worktree remove --force "$SERIES" 2> /dev/null || true
rm -rf "$SERIES"; git -C "$BASE" worktree prune
git -C "$BASE" worktree add --detach "$SERIES" "$BASE_COMMIT" > /dev/null 2>&1
git -C "$SERIES" -c user.name=ilinux -c user.email=ilinux@localhost am -q "$I"/kernel/patches/t6050/000*.patch
git -C "$SERIES" log --oneline -8 > "$B/series.txt"
: > "$B/storage-sources.txt"
for f in drivers/soc/apple/sart.c drivers/nvme/host/apple.c; do
    if cmp -s "$WORK/$f" "$SERIES/$f"; then
        echo "$f: the tree already has the current series' file ($(sha256sum < "$f" | cut -c1-16))" >> "$B/storage-sources.txt"
    else
        diff -u "$WORK/$f" "$SERIES/$f" > "$B/$(basename "$f").tree-to-series.diff" || true
        cp "$SERIES/$f" "$WORK/$f"
        echo "$f: updated to the current series ($(sha256sum < "$f" | cut -c1-16)); diff in out/build/$(basename "$f").tree-to-series.diff" >> "$B/storage-sources.txt"
    fi
done
patch -p1 --dry-run -s -i "$X/nvme-ans3/storage-ro/0001-nvme-core-ilinux-read-only.patch"
patch -p1 -s -i "$X/nvme-ans3/storage-ro/0001-nvme-core-ilinux-read-only.patch"
echo "drivers/nvme/host/core.c: iLinux read-only patch applied ($(sha256sum < drivers/nvme/host/core.c | cut -c1-16))" >> "$B/storage-sources.txt"
cat "$B/storage-sources.txt"

log "3. dockchannel-hid 0001 and 0002"
have=$(sha256sum < "$DRV" | cut -d' ' -f1)
case "$have" in
    "$PIN_SHA") patch -p1 -s -i "$X/driver-contracts/dockchannel-hid/0001-dockchannel-hid-validate-input-bounds.patch"
                echo "0001 applied (the tree had the pinned file)" ;;
    "$P0001_SHA") echo "the tree already carries 0001" ;;
    *) echo "unexpected $DRV in the tree ($have)"; exit 1 ;;
esac | tee "$B/patches.txt"
test "$(sha256sum < "$DRV" | cut -d' ' -f1)" = "$P0001_SHA"
patch -p1 --dry-run -s -i "$X/mtp-input/patches/0002-dockchannel-hid-mtp-ring-transport.patch"
patch -p1 -s -i "$X/mtp-input/patches/0002-dockchannel-hid-mtp-ring-transport.patch"
case "$(sha256sum < "$DRV")" in "$P0002_SHA"*) ;; *) echo "patched $DRV is not job 042's"; exit 1 ;; esac
cmp drivers/hid/dockchannel-hid/dchid-ring.h "$X/mtp-input/ring/dchid_ring.h"
sha256sum "$DRV" drivers/hid/dockchannel-hid/dchid-ring.h | tee -a "$B/patches.txt"

log "4. config"
cp .config "$B/config-boot041"
for s in APPLE_DOCKCHANNEL HID_DOCKCHANNEL APPLE_RTKIT_HELPER HID_APPLE HID_MAGICMOUSE NVME_APPLE APPLE_SART; do
    scripts/config --file .config --module "$s"
done
scripts/config --file .config --enable HIDRAW
make olddefconfig > "$B/olddefconfig.log" 2>&1
diff "$B/config-boot041" .config > "$B/config.diff" || test "$?" = 1
python3 -I "$X/boot042-modules/check_config_delta.py" "$B/config-boot041" .config | tee "$B/config-check.txt"
python3 -I "$X/mtp-input/check_config.py" .config > "$B/check-config-mtp.txt" 2>&1 || true

log "5. W=1 objects, Image, modules, symbols"
make -j"$JOBS" W=1 drivers/hid/dockchannel-hid/ drivers/nvme/host/core.o drivers/nvme/host/apple.o \
    drivers/soc/apple/sart.o > "$B/w1.log" 2>&1 || { tail -40 "$B/w1.log"; exit 1; }
grep -E '(dockchannel-hid\.c|dchid-ring\.h|nvme/host/core\.c|nvme/host/apple\.c|soc/apple/sart\.c).*(warning|error)' \
    "$B/w1.log" > "$B/w1-ours.txt" || true
[ ! -s "$B/w1-ours.txt" ] || { cat "$B/w1-ours.txt"; echo "W=1 warnings in our files"; exit 1; }
echo "W=1: no warning in dockchannel-hid.c, dchid-ring.h, nvme core.c, apple.c, sart.c" > "$B/w1-check.txt"
make -j"$JOBS" Image modules > "$B/build.log" 2>&1 || { tail -40 "$B/build.log"; exit 1; }
objcopy -O binary vmlinux "$B/roundtrip.bin"; cmp arch/arm64/boot/Image "$B/roundtrip.bin"; rm "$B/roundtrip.bin"
nm vmlinux > "$B/symbols.txt"
for sym in gser_alloc_inst gserial_connect configfs_composite_bind dwc3_gadget_init apple_dart_t8110_irq \
           ilinux_genpd_ladder_fn hidraw_connect hid_input_report; do
    grep -q " $sym$" "$B/symbols.txt" || { echo "vmlinux lacks $sym"; exit 1; }
done
for sym in apple_nvme_probe apple_sart_probe dockchannel_probe dockchannel_hid_driver dchid_ring_drain \
           apple_rtkit_helper_probe nvme_setup_cmd; do
    if grep -q " $sym\(\.[0-9a-z.]*\)\?$" "$B/symbols.txt"; then echo "vmlinux still has $sym"; exit 1; fi
done
grep -q " apple_mbox_probe$" "$B/symbols.txt" || { echo "the mailbox driver left vmlinux"; exit 1; }
grep -q " apple_rtkit_init$\| devm_apple_rtkit_init$" "$B/symbols.txt" || { echo "RTKit left vmlinux"; exit 1; }
echo "vmlinux: gadget stack, DART diagnostics, HID core with hidraw, mailbox and RTKit built in; no NVMe, SART, DockChannel, dockchannel-hid or RTKit helper code" \
    | tee "$B/symbols-check.txt"
KREL=$(cat include/config/kernel.release)
strings -a arch/arm64/boot/Image | grep -m1 -F "Linux version $KREL" > "$B/linux-version.txt"
grep -q "ilinux@boot042" "$B/linux-version.txt"
cp arch/arm64/boot/Image .config System.map "$B/"

log "6. kernel facts"
python3 -I "$X/boot042-modules/check_facts.py" "$WORK" | tee "$B/facts.txt"

log "7. Stage-B DT"
python3 -I "$X/mtp-input/make_mtp_dt.py" "$B41/t6050-j716c-stage-b.dtb" "$I/hardware/adt/adt-sanitized.json" \
    "$B/t6050-j716c-stage-b.dtb" "$B/mtp-delta.json" --sids 0,1,2,3,4 --dts "$B/mtp-new.dtsi" > "$B/make-mtp-dt.log"
dtc -I dtb -O dts -s "$B41/t6050-j716c-stage-b.dtb" > "$B/before.dts" 2> "$B/dtc-before.log"
dtc -I dtb -O dts -s "$B/t6050-j716c-stage-b.dtb" > "$B/after.dts" 2> "$B/dtc-after.log"
diff -u "$B/before.dts" "$B/after.dts" > "$B/dt.diff" || test "$?" = 1
export PATH=/var/tmp/t6050-build/dtvenv/bin:$PATH
SCHEMA=/var/tmp/ilinux-boot034/linux/Documentation/devicetree/bindings/processed-schema.json
dt-validate -s "$SCHEMA" "$B41/t6050-j716c-stage-b.dtb" > "$B/dt-validate-041.log" 2>&1 || true
dt-validate -s "$SCHEMA" "$B/t6050-j716c-stage-b.dtb" > "$B/dt-validate-042.log" 2>&1 || true
wc -l "$B/dt-validate-041.log" "$B/dt-validate-042.log" > "$B/dt-validate-summary.txt"

log "8. module sets"
S=$V/modules-install
rm -rf "$S"
make -j"$JOBS" INSTALL_MOD_PATH="$S" INSTALL_MOD_STRIP=1 modules_install > "$B/modules-install.log" 2>&1
M=$S/lib/modules/$KREL
python3 -I "$X/boot042-modules/module_sets.py" "$M" "$KREL" "$OUT/export/modules" "$B/Image" | tee "$B/module-sets.txt"

log "9. storage set: VM test pieces"
T=$OUT/export/storage-set
mkdir -p "$T"
gcc -static -O2 -Wall -Wextra -o "$B/ro_test" "$X/nvme-ans3/storage-ro/ro_test.c" > "$B/ro_test-build.log" 2>&1 ||
    { cat "$B/ro_test-build.log"; exit 1; }
[ ! -s "$B/ro_test-build.log" ] || { cat "$B/ro_test-build.log"; echo "ro_test.c builds with warnings"; exit 1; }
R=$V/ro-initramfs
rm -rf "$R"; mkdir -p "$R/lib/modules" "$R/dev" "$R/proc" "$R/sys" "$R/mnt"
install -m 0755 "$B/ro_test" "$R/init"
cp "$OUT/export/modules/storage/nvme-core.ko" "$OUT/export/modules/storage/nvme.ko" "$R/lib/modules/"
# nvme-core's VM control build: the same core.c with ILINUX_RO_CONTROL, the one build that accepts
# ilinux_read_only=0, so the control run can show that the guarded run's refusals are the mode's. Built
# in a copy of the tree (this tree, its objects and the storage set's module stay as built), stripped as
# modules_install strips, and put only into this test initramfs.
CT=$V/control-tree
rm -rf "$CT"
cp -a --reflink=auto "$WORK" "$CT"
(cd "$CT" && make -j"$JOBS" KCFLAGS=-DILINUX_RO_CONTROL drivers/nvme/host/nvme-core.ko) > "$B/control-build.log" 2>&1 ||
    { tail -30 "$B/control-build.log"; exit 1; }
strip --strip-debug -o "$R/lib/modules/nvme-core-control.ko" "$CT/drivers/nvme/host/nvme-core.ko"
rm -rf "$CT"
modinfo -F parm "$R/lib/modules/nvme-core-control.ko" | grep -q 'VM control build, never shipped' ||
    { echo "nvme-core's control build lacks its marker"; exit 1; }
modinfo -F parm "$R/lib/modules/nvme-core.ko" | grep -q 'always on: a load that asks for 0 fails' ||
    { echo "the storage set's nvme-core is not the always-on build"; exit 1; }
echo "nvme-core: storage set $(sha256sum < "$R/lib/modules/nvme-core.ko" | cut -c1-16) (always on), VM control build $(sha256sum < "$R/lib/modules/nvme-core-control.ko" | cut -c1-16) (test initramfs only)" | tee "$B/nvme-core-builds.txt"
find "$R" -exec touch -h -d "@$EPOCH" {} +
(cd "$R" && find . -mindepth 1 | LC_ALL=C sort | cpio --reproducible -o -H newc -R 0:0 --quiet) | gzip -9 -n > "$T/ro-test-initramfs.cpio.gz"
bash "$X/nvme-ans3/storage-ro/make_test_disk.sh" "$T/test-disk.img" > "$B/test-disk.txt" 2>&1 || { cat "$B/test-disk.txt"; exit 1; }
cat "$B/test-disk.txt"
# The storage set itself (modules + SHA256SUMS, the load script, the udev rule) and, for the load script's
# own VM run, a small userland: this VM's bash, coreutils, util-linux, kmod, procps, gawk, sed and grep
# with their libraries, /init running ilinux-storage-ro --transport pci twice (the second run must stop
# at its first check) and powering off.
cp -a "$OUT/export/modules/storage" "$T/modules"
install -m 0755 "$X/nvme-ans3/storage-ro/ilinux-storage-ro" "$T/ilinux-storage-ro"
install -m 0644 "$X/nvme-ans3/storage-ro/60-ilinux-nvme-readonly.rules" "$T/60-ilinux-nvme-readonly.rules"
U=$V/storage-userland
rm -rf "$U"; mkdir -p "$U"/{usr/bin,usr/lib,usr/local/bin,lib/storage-set,dev,proc,sys,run,tmp,etc}
ln -s usr/bin "$U/bin"; ln -s usr/bin "$U/sbin"; ln -s usr/lib "$U/lib64"
copy_bin() {  # copy_bin PATH...: binaries and every library they load, under the same paths
    local f l real
    for f in "$@"; do
        real=$(readlink -f "$f")
        install -D -m 0755 "$real" "$U$real"
        [ "$real" = "$f" ] || [ -e "$U$f" ] || ln -s "$real" "$U$f"   # the name the scripts call
        f=$real
        for l in $(ldd "$f" 2> /dev/null | grep -o '/[^ ]*' | sort -u); do
            [ -e "$U$l" ] || install -D -m 0755 "$(readlink -f "$l")" "$U$l"
        done
    done
}
copy_bin /usr/bin/{bash,cat,ls,date,sed,grep,tr,cut,sleep,seq,readlink,basename,wc,tail,head,dd,sha256sum,id,mkdir,sync,uname} \
    /usr/bin/{gawk,sfdisk,blockdev,findmnt,dmesg,mount,umount,pidof,kmod}
ln -s gawk "$U/usr/bin/awk"
for t in insmod rmmod modinfo lsmod modprobe; do ln -s kmod "$U/usr/bin/$t"; done
cp -a "$T/modules/." "$U/lib/storage-set/"
install -m 0755 "$T/ilinux-storage-ro" "$U/usr/local/bin/ilinux-storage-ro"
cat > "$U/init" <<'INIT'
#!/bin/bash
mount -t proc proc /proc; mount -t sysfs sysfs /sys; mount -t devtmpfs dev /dev
exec > /dev/console 2>&1
echo "STORAGE-SCRIPT-TEST start"
/usr/local/bin/ilinux-storage-ro --transport pci --modules /lib/storage-set
echo "STORAGE-SCRIPT-TEST first run exit $?"
/usr/local/bin/ilinux-storage-ro --transport pci --modules /lib/storage-set
echo "STORAGE-SCRIPT-TEST second run exit $?"
sync
echo o > /proc/sysrq-trigger
sleep 30
INIT
chmod 0755 "$U/init"
find "$U" -exec touch -h -d "@$EPOCH" {} +
(cd "$U" && find . -mindepth 1 | LC_ALL=C sort | cpio --reproducible -o -H newc -R 0:0 --quiet) | gzip -9 -n > "$T/storage-script-initramfs.cpio.gz"
echo "storage-script userland: $(find "$U" -type f | wc -l) files, $(du -sh "$U" | cut -f1)" | tee "$B/storage-userland.txt"

log "export"
cp "$B/Image" "$B/t6050-j716c-stage-b.dtb" "$OUT/export/"
cp "$B/.config" "$OUT/export/kernel.config"
{ uname -srm; gcc --version | head -1; ld --version | head -1; python3 --version; dtc --version
  echo "kernel release $KREL"; cat "$B/linux-version.txt"; } > "$OUT/export/toolchain.txt"
(cd "$OUT/export" && sha256sum Image kernel.config t6050-j716c-stage-b.dtb storage-set/ro-test-initramfs.cpio.gz \
    storage-set/storage-script-initramfs.cpio.gz storage-set/test-disk.img storage-set/ilinux-storage-ro \
    storage-set/60-ilinux-nvme-readonly.rules storage-set/modules/SHA256SUMS modules/manifest.json) | tee "$OUT/export-sha256.txt"
echo PASS > "$OUT/job.status"
echo "PASS: boot042 = boot041's tree + the MTP transport (0001, 0002), keyboard path and storage drivers as modules, HIDRAW; config delta exact; W=1 clean; facts; Stage-B DT; module sets; storage test pieces (nvme-core always read-only; a control build for the VM only)" | tee "$OUT/summary.txt"
