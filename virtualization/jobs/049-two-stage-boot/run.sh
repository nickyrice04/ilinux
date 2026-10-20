#!/bin/bash
# Job 049: the two-stage boot's stage one (the Omarchy boot with about 2 minutes of transfer instead of
# 8 minutes of m1n1 upload). Runs in the workspace Arch VM through host-run.sh (tools/vm-job.sh, the vm
# lock); the boot test runs on the Mac without the lock (run-qemu.sh).
#  1. Inputs: the Image stage one is for (boot041's, boot040's byte for byte), stage two's pin
#     (native/boot/omarchy-root-manifest.json) and stage two itself (out/stage2/ramroot.cpio.zst, a clone
#     of job 045's image that host-run.sh makes on the Mac), checked against the pin. The pin must name
#     the same Image.
#  2. Stage two unpacked here once, exactly as stage one unpacks it (bsdtar into a tmpfs, 16 KiB
#     pages): its entry count and the RAM it takes become part of stage one's pin, and the time is
#     recorded.
#  3. Stage one's root: job 039's base and link packages without its desktop
#     (omarchy-arm64/two-stage/packages.txt) from the official ALARM mirror with signature checks; job
#     039's RAM-root layer unchanged (omarchy-arm64/ram-root/overlay: /init, the gadget script, its
#     units, sshd's drop-ins); the operator's public keys for root and omarchy, root-owned 0644, as job
#     039 installs them (sshd reads the file as the user who logs in); the two-stage layer
#     (omarchy-arm64/two-stage/overlay); the pin (/etc/ilinux/stage2-pin); no private key: the SSH host
#     key is made at each boot. Job 039's prune and 16 KiB ELF check; pack (zstd --ultra -22
#     --long=27) -> out/stage1.cpio.zst.
#  4. Test only, never in out/stage1.cpio.zst: python3 (the M1 stand-in runs tools/m1n1-client/
#     m5-stage2.py), the Linux usb-pipe, a VM key pair -> out/build/test-base.cpio.zst for run-qemu.sh.
# Optional out/job.env: KTREE, KERNEL, IMAGE_SHA (another Image: the read-only tree that built it, the
# Image, its sha256), MANIFEST (stage two's pin record, /mnt/ilinux/..., when it is not yet
# native/boot/omarchy-root-manifest.json, e.g. a record in build/ that waits for its handoff; host-run.sh
# and run-qemu.sh read the same line), FAST=1 (zstd -3 instead of --ultra -22 --long=27, for quick test builds).
set -euo pipefail
J=/mnt/job
OUT=$J/out
I=/mnt/ilinux
[ -f "$OUT/job.env" ] && . "$OUT/job.env"
FAST=${FAST:-0}
KTREE=${KTREE:-/var/tmp/ilinux-boot036/linux}   # read only: the tree that built boot040's Image
KERNEL=${KERNEL:-$I/build/native-boot041/verified/Image}
IMAGE_SHA=${IMAGE_SHA:-a53d1d47467480d4b56d87c7b1365e9a5c28fd9ee9e5f0164a3e734f85526ad9}
MANIFEST=${MANIFEST:-$I/native/boot/omarchy-root-manifest.json}
STAGE2=$OUT/stage2/ramroot.cpio.zst
MIRROR='https://fl.us.mirror.archlinuxarm.org/$arch/$repo'                  # official ALARM mirror
W=/var/tmp/ilinux-stage1             # kept between runs: keyring, package cache, VM test keys
T=/run/ilinux-stage1                 # tmpfs: the root, the cpio, the test root
U=/run/ilinux-stage1-unpack          # tmpfs: stage two unpacked once
R=$T/root
L039=$I/omarchy-arm64/ram-root
L=$I/omarchy-arm64/two-stage
J039=$I/virtualization/jobs/039-omarchy-ram-root

log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
calc() { awk "BEGIN { printf \"%.${2:-1}f\", $1 }"; }
share() { mkdir -p "/mnt/$1"; mountpoint -q "/mnt/$1" || mount -t virtiofs "$1" "/mnt/$1"; }
chroot_up() {  # the API filesystems pacman hooks need, as pacstrap sets them up (job 039)
    mkdir -p "$1"/{dev,proc,sys,run,tmp}
    mount -t proc proc "$1/proc"
    mount -t sysfs -o ro sys "$1/sys"
    mount --rbind /dev "$1/dev"
    mount --make-rslave "$1/dev"
    mount -t tmpfs -o mode=0755 run "$1/run"
    mount -t tmpfs -o mode=1777 tmp "$1/tmp"
}
chroot_down() {
    local m
    for m in tmp run dev sys proc; do
        mountpoint -q "$1/$m" && umount -R "$1/$m"
    done
    return 0
}
pac() {  # pac ROOT ARGS...: pacman on another root with the job's config, cache and keyring (job 039's
         # package cache is searched too, so its downloads are reused)
    local root=$1; shift
    local extra=()
    [ -d /var/tmp/ilinux-ramroot/cache ] && extra=(--cachedir /var/tmp/ilinux-ramroot/cache)
    pacman --root "$root" --dbpath "$root/var/lib/pacman" --config "$W/pacman.conf" \
        --cachedir "$W/cache" "${extra[@]}" --gpgdir "$W/gnupg" --hookdir "$root/etc/pacman.d/hooks" \
        --logfile "$root/var/log/pacman.log" "$@"
}
# private_keys DIR: text files under DIR that hold a PEM or OpenSSH private key (job 045's test)
private_keys() {
    grep -r -l -I -E -e '^-----BEGIN ([A-Z0-9]+ )*PRIVATE KEY-----$' "$1" 2> /dev/null | while read -r f; do
        awk '/^-----BEGIN ([A-Z0-9]+ )*PRIVATE KEY-----$/ { body = 4; next }
             body > 0 { if ($0 ~ /^[A-Za-z0-9+\/=]{40,}$/) { found = 1; exit } body-- }
             END { exit !found }' "$f" && echo "${f#"$1"}"
    done || true
}
cleanup() {
    chroot_down "$R" 2> /dev/null
    chroot_down "$T/testroot" 2> /dev/null
    mountpoint -q "$U" && umount "$U"
    return 0
}
trap cleanup EXIT

# ---- 1. inputs --------------------------------------------------------------------------------------
share ilinux
mkdir -p "$OUT" "$W/cache" "$T" "$U"
mountpoint -q "$T" || mount -t tmpfs -o size=6G,mode=0755 tmpfs "$T"
rm -rf "$OUT/build"
mkdir -p "$OUT/build"
log "1. inputs"
echo "$IMAGE_SHA  $KERNEL" | sha256sum -c -
test -f "$KTREE/include/config/kernel.release" || { echo "no kernel tree at $KTREE"; exit 1; }
test "$(sha256sum < "$KTREE/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$IMAGE_SHA"
KREL=$(cat "$KTREE/include/config/kernel.release")
strings -n 20 "$KERNEL" > "$T/image-strings.txt"   # not piped into grep -q: pipefail would see strings' SIGPIPE
grep -q -F "Linux version $KREL " "$T/image-strings.txt" || { echo "the Image does not name release $KREL"; exit 1; }
read -r P_SIZE P_SHA P_IMAGE P_SOURCE < <(python3 -I -c '
import json, sys
r = json.load(open(sys.argv[1]))
assert r["profile"] == "omarchy", r["profile"]
print(int(r["size"]), r["sha256"], r["image_sha256"], r["source"].replace("\n", " "))' "$MANIFEST")
[ "$P_IMAGE" = "$IMAGE_SHA" ] || { echo "stage two's pin is for Image $P_IMAGE, stage one is for $IMAGE_SHA"; exit 1; }
[ "$(stat -c %s "$STAGE2")" = "$P_SIZE" ] || { echo "$STAGE2 is not the pinned $P_SIZE bytes"; exit 1; }
t0=$(date +%s.%N)
echo "$P_SHA  $STAGE2" | sha256sum -c - > /dev/null || { echo "$STAGE2 differs from the pin $P_SHA"; exit 1; }
echo "stage2_sha256_s_vm $(calc "$(date +%s.%N) - $t0" 2)" > "$OUT/build/timings.txt"
{ uname -srm; nproc; free -m | sed -n 2p; pacman -V | sed -n 2p; bsdtar --version
  echo "kernel release $KREL (Image $IMAGE_SHA)"
  echo "stage two pin: $P_SIZE bytes, $P_SHA ($P_SOURCE)"; } > "$OUT/build/vm-environment.txt"

# ---- 2. stage two, unpacked once as stage one does it -------------------------------------------------
log "2. stage two unpacked once (bsdtar into a tmpfs, as ilinux-stage2 switch does)"
mountpoint -q "$U" || mount -t tmpfs -o size=14G,mode=0755 tmpfs "$U"
t0=$(date +%s.%N)
bsdtar -x -p --numeric-owner -f "$STAGE2" -C "$U"
echo "stage2_unpack_s_vm $(calc "$(date +%s.%N) - $t0" 2)" >> "$OUT/build/timings.txt"
P_ENTRIES=$(find "$U" -mindepth 1 -printf . | wc -c)
P_USED=$(df -B1 --output=used "$U" | tail -n 1 | tr -d ' ')
for f in init usr/lib/systemd/systemd; do test -x "$U/$f"; done
test -e "$U/etc/os-release" -o -e "$U/usr/lib/os-release"
{ echo "entries $P_ENTRIES"; echo "tmpfs_used_bytes $P_USED (page size $(getconf PAGESIZE))"
  echo "build-info:"; sed 's/^/  /' "$U/usr/share/ilinux/build-info.txt"
  echo "init:"; sed 's/^/  /' "$U/init"; } > "$OUT/build/stage2-unpacked.txt"
grep -q "Image sha256 $IMAGE_SHA" "$U/usr/share/ilinux/build-info.txt" ||
    { echo "stage two's own build-info names another Image"; exit 1; }
umount "$U"
head -n 3 "$OUT/build/stage2-unpacked.txt"

# ---- 3. stage one's root -----------------------------------------------------------------------------
log "3. stage one: keyring and packages"
if [ ! -s "$W/gnupg/trustdb.gpg" ]; then
    rm -rf "$W/gnupg"
    pacman-key --gpgdir "$W/gnupg" --init
    pacman-key --gpgdir "$W/gnupg" --populate archlinuxarm
fi
cat > "$W/pacman.conf" <<EOF
[options]
Architecture = aarch64
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Required
ParallelDownloads = 4
[core]
Server = $MIRROR
[extra]
Server = $MIRROR
[alarm]
Server = $MIRROR
EOF
cp "$W/pacman.conf" "$OUT/build/pacman.conf"
chroot_down "$R"
rm -rf "$R"
mkdir -p "$R/var/lib/pacman" "$R/var/log" "$R/etc/pacman.d/hooks"
chroot_up "$R"
t0=$(date +%s)
pac "$R" -Sy --noconfirm --needed $(grep -v -E '^[[:space:]]*(#|$)' "$L/packages.txt") \
    > "$OUT/build/pacman-install.log" 2>&1 || { tail -40 "$OUT/build/pacman-install.log"; exit 1; }
echo "install_s $(( $(date +%s) - t0 ))" >> "$OUT/build/timings.txt"
pac "$R" -Q > "$OUT/stage1-packages.txt"
log "$(wc -l < "$OUT/stage1-packages.txt") packages"
for f in bsdtar sshd setfont zstd flock; do test -x "$R/usr/bin/$f"; done

# The kernel's own module lists (the gadget stack is built in from boot036; nothing to build).
mkdir -p "$R/usr/lib/modules/$KREL"
cp "$KTREE/modules.builtin" "$KTREE/modules.builtin.modinfo" "$R/usr/lib/modules/$KREL/"
: > "$R/usr/lib/modules/$KREL/modules.order"
depmod -b "$R" "$KREL"

log "3. stage one: job 039's RAM-root layer, then the two-stage layer"
cp -R --preserve=mode "$L039/overlay/." "$R/"
cp -R --preserve=mode "$L/overlay/." "$R/"
chmod 0755 "$R/init" "$R"/usr/local/bin/* "$R"/usr/local/lib/ilinux/*
echo ilinux-m5-stage1 > "$R/etc/hostname"
echo LANG=C.UTF-8 > "$R/etc/locale.conf"
ln -sf /usr/share/zoneinfo/UTC "$R/etc/localtime"
: > "$R/etc/machine-id"
chroot "$R" useradd -m -u 1000 -U -G systemd-journal -s /bin/bash omarchy
chroot "$R" passwd -l root > /dev/null
systemctl --root="$R" enable ilinux-ssh-hostkey.service ilinux-stage1-screen.service ilinux-stage2-udev-cleanup.service \
    > "$OUT/build/systemctl.log" 2>&1
systemctl --root="$R" mask systemd-firstboot.service getty@tty1.service >> "$OUT/build/systemctl.log" 2>&1
systemctl --root="$R" set-default multi-user.target >> "$OUT/build/systemctl.log" 2>&1
grep -q '^Include /etc/ssh/sshd_config.d/\*.conf' "$R/etc/ssh/sshd_config" ||
    sed -i '1i Include /etc/ssh/sshd_config.d/*.conf' "$R/etc/ssh/sshd_config"
# Operator public keys, exactly as job 039 installs them: out/authorized_keys (gitignored) when present,
# else the M1's own public key from Git. sshd opens /etc/ssh/authorized_keys.d/<user> with the uid of
# the user logging in, so the files are 0644 and root-owned (job 039's fix; at 0600 omarchy's logins
# were refused in VM job 046). Public keys only.
AUTH=$OUT/authorized_keys
[ -s "$AUTH" ] || AUTH=$I/kernel/experiments/usb-gadget/authorized_keys
for u in root omarchy; do install -D -m 0644 "$AUTH" "$R/etc/ssh/authorized_keys.d/$u"; done
ssh-keygen -lf "$AUTH" > "$OUT/authorized-keys-fingerprints.txt"
# sshd's configuration test needs a host key: a throwaway one, deleted at once (the image has none).
chroot "$R" ssh-keygen -q -t ed25519 -N '' -f /tmp/sshd-t-key
chroot "$R" sshd -t -h /tmp/sshd-t-key
rm -f "$R/tmp/sshd-t-key" "$R/tmp/sshd-t-key.pub"
# The pin: stage two as its record ($MANIFEST) has it, with what step 2 measured.
mkdir -p "$R/etc/ilinux"
cat > "$R/etc/ilinux/stage2-pin" <<EOF
# Stage two for this stage one (VM job 049): ${MANIFEST#"$I"/} at build time, plus
# the entry count and the RAM it takes in 16 KiB pages, measured by unpacking it in the build VM.
size=$P_SIZE
sha256=$P_SHA
image_sha256=$P_IMAGE
entries=$P_ENTRIES
unpacked_bytes_16k=$P_USED
source=$P_SOURCE
EOF
chmod 0644 "$R/etc/ilinux/stage2-pin"
cp "$R/etc/ilinux/stage2-pin" "$OUT/stage2-pin.txt"
mkdir -p "$R/usr/share/ilinux"
cp "$OUT/stage1-packages.txt" "$R/usr/share/ilinux/packages.txt"
printf 'built %s\nstage one of the two-stage boot (VM job 049), ilinux %s\nkernel %s (Image sha256 %s)\nstage two pin %s bytes, sha256 %s\n' \
    "$(date -u +%FT%TZ)" "$(git -c safe.directory='*' -C "$I" rev-parse --short HEAD 2> /dev/null || echo unknown)" \
    "$KREL" "$IMAGE_SHA" "$P_SIZE" "$P_SHA" > "$R/usr/share/ilinux/build-info.txt"

log "3. stage one: prune, checks, pack"
chroot_down "$R"
cp -a "$R/var/lib/pacman" "$T/pacman-db"          # for the test-only root in step 4
python3 -I "$J039/elf_page_check.py" "$R" > "$OUT/build/elf-check-before-prune.txt"
mkdir -p "$R/usr/share/fonts/TTF"                  # job 039's prune.sh trims fonts there
bash "$L039/prune.sh" "$R" | tee "$OUT/build/prune.txt"
rmdir "$R/usr/share/fonts/TTF" "$R/usr/share/fonts" 2> /dev/null || true
chroot "$R" ldconfig
python3 -I "$J039/elf_page_check.py" "$R" > "$OUT/elf-16k-check.txt"
missing() { sed -n '/^needs_missing_library/,$p' "$1" | tail -n +2 | sort; }
comm -13 <(missing "$OUT/build/elf-check-before-prune.txt") <(missing "$OUT/elf-16k-check.txt") > "$OUT/build/prune-broke.txt"
[ ! -s "$OUT/build/prune-broke.txt" ] || { echo "pruning removed needed libraries:"; cat "$OUT/build/prune-broke.txt"; exit 1; }
head -4 "$OUT/elf-16k-check.txt"
# No private key, no host key, no password in the image
keys=$(private_keys "$R")
[ -z "$keys" ] || { echo "private keys in stage one: $keys"; exit 1; }
[ -z "$(ls "$R"/etc/ssh/ssh_host_* 2> /dev/null)" ] || { echo "a host key is in stage one"; exit 1; }
[ -z "$(find "$R" -name 'id_*' ! -name '*.pub' -type f)" ] || { echo "an id_* file is in stage one"; exit 1; }
{ echo "private keys (PEM or OpenSSH, text files anywhere in the root): none"
  echo "ssh host keys: none (made at each boot by ilinux-ssh-hostkey.service)"
  echo "authorized keys (public): $(cd "$R/etc/ssh/authorized_keys.d" && stat -c '%n %U:%G %a' * | tr '\n' ' ')"
  echo "shadow: $(chroot "$R" getent shadow root omarchy | cut -d: -f1,2 | sed 's/:\(.\).*/:\1.../' | tr '\n' ' ')"
  echo "machine-id: $(wc -c < "$R/etc/machine-id") bytes (made at each boot)"; } > "$OUT/private-contents.txt"
cat "$OUT/private-contents.txt"
# A RAM root looks freshly installed to ConditionNeedsUpdate at every boot: stamp it as job 039 does.
usr_ns=$(stat -c %.9Y "$R/usr" | tr -d .)
for d in etc var; do
    printf '# Written by job 049, as systemd-update-done would.\nTIMESTAMP_NSEC=%s\n' "$usr_ns" > "$R/$d/.updated"
done
{ echo "root_bytes $(du -sb --apparent-size "$R" | cut -f1)"
  echo "root_files $(find "$R" -mindepth 1 | wc -l)"; } > "$OUT/sizes.txt"
( cd "$R" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort |
  cpio --quiet -o -H newc --reproducible ) > "$T/stage1.cpio"
echo "cpio_bytes $(stat -c %s "$T/stage1.cpio")" >> "$OUT/sizes.txt"
ZARGS="--ultra -22 --long=27"
[ "$FAST" = 1 ] && ZARGS="-3"
t0=$(date +%s.%N)
zstd -q -T0 $ZARGS -c "$T/stage1.cpio" > "$OUT/stage1.cpio.zst"
echo "zstd_s $(calc "$(date +%s.%N) - $t0")" >> "$OUT/build/timings.txt"
(cd "$OUT" && sha256sum stage1.cpio.zst > stage1.cpio.zst.sha256)
size=$(stat -c %s "$OUT/stage1.cpio.zst")
image=$(stat -c %s "$KERNEL")
dtb=$(stat -c %s "$(dirname "$KERNEL")/t6050-j716c-stage-b.dtb")
total=$((image + size + dtb))
{ echo "zst_bytes $size"; echo "zst_args $ZARGS"
  echo "upload_bytes $total (Image $image + stage one $size + DT $dtb)"
  echo "upload_s_at_5.24MBps $(calc "$total / 5240000")"
  echo "upload_s_at_4MBps $(calc "$total / 4000000")"; } >> "$OUT/sizes.txt"
cat "$OUT/sizes.txt" "$OUT/stage1.cpio.zst.sha256"

# ---- 4. test only: the M1 stand-in's python3, the Linux usb-pipe, VM keys -----------------------------
log "4. test-only base (never in stage1.cpio.zst)"
TR=$T/testroot
rm -rf "$TR"
cp -a "$R" "$TR"
rm -rf "$TR/var/lib/pacman"
cp -a "$T/pacman-db" "$TR/var/lib/pacman"
mkdir -p "$TR/etc/pacman.d/hooks"
( cd "$TR" && find . -mindepth 1 | LC_ALL=C sort ) > "$T/before.txt"
chroot_up "$TR"
pac "$TR" -S --noconfirm --needed python > "$OUT/build/test-pacman.log" 2>&1 || { tail -20 "$OUT/build/test-pacman.log"; exit 1; }
chroot_down "$TR"
rm -rf "$TR"/usr/lib/python3.*/{test,idlelib,tkinter,turtledemo,ensurepip,lib2to3} "$TR/var/lib/pacman" "$TR/var/cache/pacman"
find "$TR/usr/lib" -path '*/python3.*' -name __pycache__ -type d -prune -exec rm -rf {} +
S=$I/tools/m1n1-client/usb-pipe
gcc -O2 -Wall -Wextra -pthread -static -o "$OUT/build/usb-pipe" "$S/usb-pipe.c" "$S/relay.c" > "$OUT/build/usb-pipe-build.log" 2>&1 ||
    { cat "$OUT/build/usb-pipe-build.log"; exit 1; }
"$OUT/build/usb-pipe" --version
install -D -m 0755 "$OUT/build/usb-pipe" "$TR/usr/local/lib/ilinux-test/usb-pipe"
mkdir -p "$W/testkey"
[ -f "$W/testkey/id_ed25519" ] || ssh-keygen -q -t ed25519 -N '' -C ilinux049-vm-test -f "$W/testkey/id_ed25519"
install -D -m 0600 "$W/testkey/id_ed25519" "$TR/usr/local/lib/ilinux-test/keys/id_ed25519"
install -m 0644 "$W/testkey/id_ed25519.pub" "$TR/usr/local/lib/ilinux-test/keys/id_ed25519.pub"
install -m 0644 "$W/testkey/id_ed25519.pub" "$TR/etc/ssh/authorized_keys.d/root"   # the VM's key for root
ssh-keygen -lf "$W/testkey/id_ed25519.pub" > "$OUT/build/test-key-fingerprint.txt"
( cd "$TR" && find . -mindepth 1 | LC_ALL=C sort ) > "$T/after.txt"
{ comm -13 "$T/before.txt" "$T/after.txt"; echo ./etc/ssh/authorized_keys.d/root; } | sed 's|^\./||' | LC_ALL=C sort -u > "$OUT/build/test-base-files.txt"
( cd "$TR" && cpio --quiet -o -H newc --reproducible -R 0:0 < "$OUT/build/test-base-files.txt" ) | zstd -q -T0 -19 > "$OUT/build/test-base.cpio.zst"
{ echo "files $(wc -l < "$OUT/build/test-base-files.txt")"
  echo "zst_bytes $(stat -c %s "$OUT/build/test-base.cpio.zst")"
  grep -E '^usr/bin/python3$|^usr/local/lib/ilinux-test/' "$OUT/build/test-base-files.txt"; } > "$OUT/build/test-base.txt"
cat "$OUT/build/test-base.txt"
(cd "$OUT/build" && sha256sum test-base.cpio.zst usb-pipe > test-base.sha256)
cat "$OUT/build/timings.txt"
log "PASS: stage one $(stat -c %s "$OUT/stage1.cpio.zst") bytes ($(cut -d' ' -f1 "$OUT/stage1.cpio.zst.sha256")), pin of stage two $P_SIZE bytes / $P_ENTRIES entries / $P_USED bytes in RAM; boot test: run-qemu.sh on the Mac"
