#!/bin/bash
# Job 041: boot036, the USB control channel candidate (kernel/experiments/usb-gadget).
#  1. Image: the boot034 tree (its Image is boot035's) with USB_LIBCOMPOSITE=y and
#     USB_CONFIGFS=y; the config delta is checked by native/boot/control_channel.py.
#  2. Test Image, never shipped: the same plus USB_DUMMY_HCD, USB_USBNET and USB_NET_CDC_EEM,
#     so one kernel is both the EEM gadget and its host for the self-test.
#  3. Stage-B DT: boot035's plus the native/boot/usb_dt.py contract, rebuilt with this VM's
#     dtc and schema-checked before and after.
#  4. Stage-B initramfs: /init from init.c (static), dropbear and busybox from signed Arch
#     Linux ARM packages with their libraries, root's authorized key; every ELF checked for
#     16 KiB pages; reproducible cpio.
#  5. Self-test overlay, never shipped: test key, selftest script, dbclient, ip, unshare,
#     nsenter and ping. The boots themselves run on the Mac (selftest/run-vz.sh).
# The boot034 tree and every earlier package stay untouched.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
EXP=/mnt/ilinux/kernel/experiments/usb-gadget
NB=/mnt/ilinux/native/boot
B35=/mnt/ilinux/build/native-boot035/verified
SRC=/var/tmp/ilinux-boot034/linux
WORK=/var/tmp/ilinux-boot036/linux
TEST=/var/tmp/ilinux-boot036/linux-test
W=/var/tmp/ilinux-boot036/pkg        # pacman roots, cache and keyring (kept between runs)
STAGE=/var/tmp/ilinux-boot036/initramfs
OVL=/var/tmp/ilinux-boot036/overlay
MIRROR='https://fl.us.mirror.archlinuxarm.org/$arch/$repo'   # official ALARM mirror
BOOT035_IMAGE=1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579
EPOCH=1760486400                     # 2025-10-15 00:00 UTC: fixed cpio mtimes
JOBS=$(nproc)
log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
rm -rf "$OUT/export" "$OUT/build"
mkdir -p "$OUT/export" "$OUT/build" "$OUT/keys" /var/tmp/ilinux-boot036
cd /var/tmp/ilinux-boot036

log "inputs"
test "$(sha256sum "$SRC/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$BOOT035_IMAGE"
(cd "$B35" && sha256sum -c --quiet SHA256SUMS)
# The packaged kernel.config is job 020's; this tree re-detected the toolchain since (rustc).
# Record that drift and stop if it touches anything but toolchain-detection symbols.
diff "$B35/kernel.config" "$SRC/.config" > "$OUT/build/package-vs-tree-config.diff" || test "$?" = 1
python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import control_channel as c
names = c.toolchain_differences(open(sys.argv[2]).read(), open(sys.argv[3]).read())
print("packaged kernel.config vs the tree that built boot035: toolchain detection only:", " ".join(names) or "none")' \
    "$NB" "$B35/kernel.config" "$SRC/.config" | tee "$OUT/build/package-vs-tree-config.txt"
{ uname -srm; gcc --version | head -1; ld --version | head -1; dtc --version; python3 --version
  pacman -V | sed -n 2p; } > "$OUT/build/vm-tools.txt"

log "1. boot036 Image"
rm -rf "$WORK"
cp -a --reflink=auto "$SRC" "$WORK"
"$WORK/scripts/config" --file "$WORK/.config" --enable USB_LIBCOMPOSITE --enable USB_CONFIGFS
make -C "$WORK" olddefconfig > "$OUT/build/olddefconfig.log" 2>&1
python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import control_channel as c
c.check_config(open(sys.argv[2]).read(), open(sys.argv[3]).read()); print("config delta PASS (exactly the gadget stack, m to y)")' \
    "$NB" "$SRC/.config" "$WORK/.config" | tee "$OUT/build/config-check.txt"
diff "$SRC/.config" "$WORK/.config" > "$OUT/build/config.diff" || test "$?" = 1
make -C "$WORK" -j"$JOBS" Image > "$OUT/build/build.log" 2>&1
objcopy -O binary "$WORK/vmlinux" "$OUT/build/roundtrip.bin"
cmp "$WORK/arch/arm64/boot/Image" "$OUT/build/roundtrip.bin"
rm "$OUT/build/roundtrip.bin"
nm "$WORK/vmlinux" > "$OUT/build/symbols.txt"
for sym in eem_alloc_inst gether_connect usb_composite_probe configfs_composite_bind \
           dwc3_gadget_init ilinux_genpd_ladder_fn; do
    grep -q " $sym$" "$OUT/build/symbols.txt" || { echo "missing symbol $sym"; exit 1; }
done
echo "gadget, configfs, dwc3 gadget and genpd ladder symbols present" > "$OUT/build/symbols-check.txt"
cp "$WORK/arch/arm64/boot/Image" "$WORK/.config" "$OUT/build/"

log "2. test Image (not shipped)"
rm -rf "$TEST"
cp -a --reflink=auto "$WORK" "$TEST"
"$TEST/scripts/config" --file "$TEST/.config" --enable USB_DUMMY_HCD --enable USB_USBNET \
    --enable USB_NET_CDC_EEM
make -C "$TEST" olddefconfig > /dev/null 2>&1
diff "$WORK/.config" "$TEST/.config" > "$OUT/build/test-config.diff" || test "$?" = 1
make -C "$TEST" -j"$JOBS" Image > "$OUT/build/test-build.log" 2>&1
cp "$TEST/arch/arm64/boot/Image" "$OUT/build/Image-test"

log "3. Stage-B DT"
python3 -I "$EXP/make_stage_b_dt.py" dtc "$B35/t6050-j716c-stage-b.dtb" \
    "$OUT/build/t6050-j716c-stage-b.dtb" "$OUT/build/stage-b-036.dts" | tee "$OUT/build/dt-check.txt"
export PATH=/var/tmp/t6050-build/dtvenv/bin:$PATH
SCHEMA=$SRC/Documentation/devicetree/bindings/processed-schema.json
dt-validate -s "$SCHEMA" "$B35/t6050-j716c-stage-b.dtb" > "$OUT/build/dt-validate-035.log" 2>&1 || true
dt-validate -s "$SCHEMA" "$OUT/build/t6050-j716c-stage-b.dtb" > "$OUT/build/dt-validate-036.log" 2>&1 || true
dt-validate -l snps,dwc3 -s "$SCHEMA" "$OUT/build/t6050-j716c-stage-b.dtb" > "$OUT/build/dt-validate-dwc3.log" 2>&1 || true
dtc -q -I dtb -O dts -s "$B35/t6050-j716c-stage-b.dtb" > "$OUT/build/before.dts"
dtc -q -I dtb -O dts -s "$OUT/build/t6050-j716c-stage-b.dtb" > "$OUT/build/after.dts"
diff -u "$OUT/build/before.dts" "$OUT/build/after.dts" > "$OUT/build/dt.diff" || test "$?" = 1

log "4. packages (signed, official mirror)"
if [ ! -s "$W/gnupg/trustdb.gpg" ]; then
    mkdir -p "$W/gnupg"
    pacman-key --gpgdir "$W/gnupg" --init > /dev/null
    pacman-key --gpgdir "$W/gnupg" --populate archlinuxarm > /dev/null
fi
cat > "$W/pacman.conf" <<EOF
[options]
Architecture = aarch64
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Required
[core]
Server = $MIRROR
[extra]
Server = $MIRROR
[alarm]
Server = $MIRROR
EOF
pac() {  # pac ROOT ARGS...: pacman on another root with this job's config, cache and keyring
    local root=$1; shift
    mkdir -p "$root/var/lib/pacman" "$root/var/log"
    pacman --root "$root" --dbpath "$root/var/lib/pacman" --config "$W/pacman.conf" \
        --cachedir "$W/cache" --gpgdir "$W/gnupg" --hookdir "$W/no-hooks" \
        --logfile "$root/var/log/pacman.log" "$@"
}
# --hookdir only adds a directory: hooks shipped inside a target root still run (the test
# root's ca-certificates rebuild), which is harmless. pacman needs the cache to exist.
mkdir -p "$W/no-hooks" "$W/cache"
rm -rf "$W/ship" "$W/test"
pac "$W/ship" -Sy --noconfirm --noscriptlet dropbear busybox > "$OUT/build/pacman-ship.log" 2>&1
pac "$W/test" -Sy --noconfirm --noscriptlet dropbear iproute2 util-linux iputils > "$OUT/build/pacman-test.log" 2>&1
pac "$W/ship" -Q > "$OUT/build/packages-ship.txt"
pac "$W/test" -Q > "$OUT/build/packages-test.txt"
for root in ship test; do
    for pkg in $(pac "$W/$root" -Qq); do
        pac "$W/$root" -Qi "$pkg" | grep -E '^(Name|Version|Packager|Build Date|Validated By)'
    done > "$OUT/build/provenance-$root.txt"
done
grep -c 'Validated By *:.*Signature' "$OUT/build/provenance-ship.txt" > "$OUT/build/signed-ship.txt" || true
test "$(grep -c '^Name' "$OUT/build/provenance-ship.txt")" = "$(cat "$OUT/build/signed-ship.txt")"

log "keys"
DBKEY=$W/ship/usr/bin/dropbearkey
LD=$W/ship/usr/lib/ld-linux-aarch64.so.1
run_ship() { "$LD" --library-path "$W/ship/usr/lib" "$@"; }   # packaged tools, packaged libraries
if [ ! -s "$OUT/keys/test-key" ]; then
    run_ship "$DBKEY" -t ed25519 -f "$OUT/keys/test-key" > /dev/null
fi
run_ship "$DBKEY" -y -f "$OUT/keys/test-key" | grep '^ssh-ed25519 ' | cut -d' ' -f1,2 \
    | sed 's/$/ ilinux-boot036-test-key/' > "$OUT/keys/test-key.pub"
AUTH=$EXP/authorized_keys
if [ -s "$AUTH" ]; then KEYSRC="committed $AUTH"; else AUTH=$OUT/keys/test-key.pub; KEYSRC="TEST KEY (job 041)"; fi
cp "$AUTH" "$OUT/build/authorized_keys"
echo "$KEYSRC: $(ssh-keygen -l -f "$AUTH" 2>/dev/null || cut -c1-40 "$AUTH")" > "$OUT/build/authorized-key.txt"

log "5. init and Stage-B initramfs"
gcc -static -O2 -Wall -Wextra -Wno-unused-result -o "$OUT/build/init" "$EXP/init.c" 2> "$OUT/build/init-build.log"
cp "$EXP/init.c" "$OUT/build/diag-init.c"
python3 -I "$EXP/stage_initramfs.py" ship "$W/ship" "$OUT/build/init" "$OUT/build/authorized_keys" \
    "$STAGE" > "$OUT/build/initramfs-contents.txt"
python3 -I "$EXP/stage_initramfs.py" overlay "$W/test" "$EXP/selftest/selftest.sh" "$OUT/keys/test-key" \
    "$OVL" > "$OUT/build/overlay-contents.txt"
python3 -I "$EXP/elf_pages.py" "$STAGE" "$OVL" > "$OUT/build/elf-16k-check.txt"
pack() {  # pack DIR OUT.cpio.gz: sorted names, root:root, fixed mtimes, no gzip name or time
    find "$1" -exec touch -h -d "@$EPOCH" {} +
    (cd "$1" && find . -mindepth 1 | LC_ALL=C sort | cpio --reproducible -o -H newc -R 0:0 --quiet) \
        | gzip -9 -n > "$2"
}
pack "$STAGE" "$OUT/build/initramfs-stage-b.cpio.gz"
pack "$OVL" "$OUT/build/selftest-overlay.cpio.gz"
python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import control_channel as c
c.check_initramfs(open(sys.argv[2], "rb").read(), open(sys.argv[3], "rb").read()); print("initramfs contract PASS")' \
    "$NB" "$OUT/build/initramfs-stage-b.cpio.gz" "$OUT/build/authorized_keys" | tee "$OUT/build/initramfs-check.txt"

log "export"
cp -a "$B35/." "$OUT/export/"
rm -f "$OUT/export/SHA256SUMS" "$OUT/export/package-manifest.json"
cp "$OUT/build/Image" "$OUT/build/.config" "$OUT/build/t6050-j716c-stage-b.dtb" \
   "$OUT/build/initramfs-stage-b.cpio.gz" "$OUT/build/diag-init.c" "$OUT/export/"
mv "$OUT/export/.config" "$OUT/export/kernel.config"
{ uname -srm; gcc --version | head -1; ld --version | head -1
  rustc --version 2>/dev/null || true; cargo --version 2>/dev/null || true; python3 --version; dtc --version
  echo "initramfs packages: $(tr '\n' ' ' < "$OUT/build/packages-ship.txt")"; } > "$OUT/export/toolchain.txt"
(cd "$OUT/export" && sha256sum Image kernel.config t6050-j716c-stage-b.dtb initramfs-stage-b.cpio.gz \
    diag-init.c toolchain.txt) | tee "$OUT/export-sha256.txt"
(cd "$OUT/build" && sha256sum Image-test selftest-overlay.cpio.gz) >> "$OUT/export-sha256.txt"
echo "PASS: boot036 Image, test Image, Stage-B DT, initramfs and self-test overlay built and checked"
