#!/bin/bash
# Job 039: Omarchy-style RAM root for the native M5 (roadmap Phase 3, steps 3 and 4).
#  1. Install an Arch Linux ARM userspace from the official ALARM mirror into a tmpfs, with
#     pacman's signature checks against a keyring populated from the VM's
#     archlinuxarm-keyring (omarchy-arm64/ram-root/packages.txt).
#  2. Add Omarchy's configuration (pinned upstream commit, Tokyo Night rendered by Omarchy's
#     own template script), the RAM-root layer (omarchy-arm64/ram-root), the kernel modules
#     for the USB link (whatever gadget functions the tree builds as modules) and the
#     repository's portable C benchmarks (built here, run by the status screen); prune; check
#     every ELF for 16 KiB pages; pack a zstd-compressed cpio
#     (out/ramroot.cpio.zst).
#  3. Boot it with the exact native boot035 Image in a one-vCPU QEMU guest (TCG; see below),
#     the way m1n1 boots the M5: direct kernel entry with a device tree whose
#     /chosen/framebuffer is a simple-framebuffer (3456x2234 x2r10g10b10, the 16-inch panel)
#     in reserved RAM, which simpledrm drives. No firmware, no virtio-gpu. Wait for the
#     desktop, read the framebuffer out of guest RAM twice (the status screen's counter must
#     advance), wait for the status screen's benchmark run, read it again, then collect the
#     journal and measurements over SSH on usb0 (QEMU usb-net). The run fails without the
#     desktop, the wallpaper, a session under start-hyprland or the benchmark results.
# Host side: host-run.sh in this directory (vm lock, read-only Omarchy share).
# Optional out/job.env: FAST=1 (one quick zstd level, no level comparison), TEST=0 (no boot),
# DEBUG=1 (boot without quiet, journal on the console, framebuffer and vCPU PC every 30 s),
# VM_ACCEL=kvm (nested KVM instead of TCG; needs NESTED=1 host-run.sh, see below),
# KTREE, KERNEL, IMAGE_SHA (another Image: the read-only tree that built it, the Image, its
# sha256; e.g. boot036, whose gadget stack is built in), CMDLINE_EXTRA (more kernel arguments
# for the boot test only, e.g. audit=1 so seccomp kills are logged).
set -euo pipefail
J=/mnt/job
OUT=$J/out
[ -f "$OUT/job.env" ] && . "$OUT/job.env"
FAST=${FAST:-0}
TEST=${TEST:-1}
DEBUG=${DEBUG:-0}
VM_ACCEL=${VM_ACCEL:-tcg}
OMARCHY_COMMIT=9480d1b6a98156314dbabe6bfef08f39f8b9cd07
# The kernel this RAM root is for: by default boot035 (its Image is byte-identical to boot034's).
KTREE=${KTREE:-/var/tmp/ilinux-boot034/linux}   # read only: the tree that built the Image
KERNEL=${KERNEL:-/mnt/ilinux/build/native-boot035/verified/Image}
IMAGE_SHA=${IMAGE_SHA:-1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579}
MIRROR='https://fl.us.mirror.archlinuxarm.org/$arch/$repo'                  # official ALARM mirror
W=/var/tmp/ilinux-ramroot            # kept between runs: package cache, keyring, tools root, keys
T=/run/ilinux-ramroot                # tmpfs: root, cpio, images, test files
R=$T/root
TOOLS=$W/tools
L=/mnt/ilinux/omarchy-arm64/ram-root

log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
calc() { awk "BEGIN { printf \"%.${2:-1}f\", $1 }"; }   # calc EXPR [DECIMALS]
share() { mkdir -p "/mnt/$1"; mountpoint -q "/mnt/$1" || mount -t virtiofs "$1" "/mnt/$1"; }
chroot_up() {  # the API filesystems pacman hooks and QEMU need, as pacstrap sets them up
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
    for m in tmp run dev sys proc work; do
        mountpoint -q "$1/$m" && umount -R "$1/$m"
    done
    return 0
}
pac() {  # pac ROOT ARGS...: pacman on another root with the job's config, cache and keyring
    local root=$1; shift
    pacman --root "$root" --dbpath "$root/var/lib/pacman" --config "$W/pacman.conf" \
        --cachedir "$W/cache" --gpgdir "$W/gnupg" --hookdir "$root/etc/pacman.d/hooks" \
        --logfile "$root/var/log/pacman.log" "$@"
}
QPID=
cleanup() {
    [ -n "$QPID" ] && kill "$QPID" 2>/dev/null
    chroot_down "$R" 2>/dev/null
    chroot_down "$TOOLS" 2>/dev/null
    return 0
}
trap cleanup EXIT

# ---- inputs -------------------------------------------------------------------------
share ilinux
share omarchy
mkdir -p "$OUT" "$W/cache" "$T"
mountpoint -q "$T" || mount -t tmpfs -o size=14G,mode=0755 tmpfs "$T"
rm -rf "$OUT/test" "$OUT/build"
mkdir -p "$OUT/build" "$OUT/test"
log "inputs"
echo "$IMAGE_SHA  $KERNEL" | sha256sum -c -
test "$(git -c safe.directory='*' -C /mnt/omarchy rev-parse HEAD)" = "$OMARCHY_COMMIT"
test "$(sha256sum < "$KTREE/arch/arm64/boot/Image" | cut -d' ' -f1)" = "$IMAGE_SHA"
KREL=$(cat "$KTREE/include/config/kernel.release")
{ uname -srm; nproc; free -m | sed -n 2p; df -h /var/tmp | tail -1; pacman -V | sed -n 2p
  echo "kernel release $KREL"; } > "$OUT/build/vm-environment.txt"

# ---- keyring and pacman configuration ----------------------------------------------------
if [ ! -s "$W/gnupg/trustdb.gpg" ]; then
    rm -rf "$W/gnupg"
    pacman-key --gpgdir "$W/gnupg" --init
    pacman-key --gpgdir "$W/gnupg" --populate archlinuxarm
fi
{ pacman -Q archlinuxarm-keyring
  gpg --homedir "$W/gnupg" --list-keys --keyid-format long 2>/dev/null | grep -E '^(pub|uid)'
} > "$OUT/build/keyring.txt"
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

# ---- root filesystem ----------------------------------------------------------------------
log "install packages"
chroot_down "$R"
rm -rf "$R"
mkdir -p "$R/var/lib/pacman" "$R/var/log" "$R/etc/pacman.d/hooks"
chroot_up "$R"
start=$(date +%s)
pac "$R" -Sy --noconfirm --needed $(grep -v -E '^[[:space:]]*(#|$)' "$L/packages.txt") \
    > "$OUT/build/pacman-install.log" 2>&1 || { tail -40 "$OUT/build/pacman-install.log"; exit 1; }
echo "install seconds $(( $(date +%s) - start ))" > "$OUT/build/timings.txt"
grep -i -E 'provider|warning|error' "$OUT/build/pacman-install.log" || true
pac "$R" -Ql hyprland | grep -E '/usr/bin/.+' > "$OUT/build/hyprland-binaries.txt"
test -x "$R/usr/bin/Hyprland"
pac "$R" -Q > "$OUT/packages.txt"
pac "$R" -Qe > "$OUT/packages-explicit.txt"
pac "$R" -Qi | awk -F': ' '/^Name/ {n=$2} /^Installed Size/ {print $2 "\t" n}' |
    awk '{v=$1; u=$2; m=(u=="KiB")?v/1024:(u=="GiB")?v*1024:(u=="B")?v/1048576:v;
          printf "%9.2f MiB  %s\n", m, $3}' | sort -rn > "$OUT/build/package-sizes.txt"
log "$(wc -l < "$OUT/packages.txt") packages installed"

pac "$R" -Qi python perl gperftools libasan | grep -E '^(Name|Required By)' > "$OUT/build/why-installed.txt"

# Kernel modules for the USB network link, built for this exact Image: the host-side USB NIC
# drivers (the VM test's usb-net) and the gadget stack. Only what the tree has as =m is built;
# from boot036 the gadget stack is built in. The tree's own .ko files are no use: in the
# boot034/035 tree they predate its "-dirty" release string, so their vermagic does not match.
# The sources are copied to tmpfs and built as external modules against the read-only tree.
log "kernel modules ($KREL)"
KM=$T/kmods
MD=usr/lib/modules/$KREL
rm -rf "$KM"
mkdir -p "$KM/drivers/net/usb" "$KM/drivers/usb/gadget/function"
: > "$OUT/build/modules.txt"
want() {  # want CONFIG_SYMBOL: true if the tree builds it as a module; logs the state
    local state
    state=$(grep -E "^CONFIG_$1=" "$KTREE/.config" | cut -d= -f2 || true)
    echo "CONFIG_$1=${state:-n}" >> "$OUT/build/modules.txt"
    [ "$state" = m ]
}
net= core= func=
want USB_USBNET && net="$net usbnet.o"
want USB_NET_CDCETHER && net="$net cdc_ether.o"
want USB_NET_CDC_NCM && net="$net cdc_ncm.o"
want USB_LIBCOMPOSITE && core=libcomposite.o
want USB_U_ETHER && func="$func u_ether.o"
want USB_F_EEM && func="$func usb_f_eem.o"
want USB_F_NCM && func="$func usb_f_ncm.o"
want USB_F_ECM && func="$func usb_f_ecm.o"
want USB_U_SERIAL && func="$func u_serial.o"   # the ACM journal port
want USB_F_ACM && func="$func usb_f_acm.o"
want USB_F_SERIAL && func="$func usb_f_serial.o"   # gser: the bulk-only log port and the SSH byte pipe
cp "$KTREE"/drivers/net/usb/{usbnet,cdc_ether,cdc_ncm}.c "$KM/drivers/net/usb/"
echo "obj-m :=$net" > "$KM/drivers/net/usb/Kbuild"
cp "$KTREE"/drivers/usb/gadget/*.[ch] "$KM/drivers/usb/gadget/"
cp "$KTREE"/drivers/usb/gadget/function/*.[ch] "$KM/drivers/usb/gadget/function/"
cat > "$KM/drivers/usb/gadget/Kbuild" <<EOF
ccflags-y := -I\$(srctree)/drivers/usb/gadget/udc
obj-m := $core${func:+ function/}
libcomposite-y := usbstring.o config.o epautoconf.o composite.o functions.o configfs.o u_f.o
EOF
cat > "$KM/drivers/usb/gadget/function/Kbuild" <<EOF
ccflags-y := -I\$(src)/.. -I\$(srctree)/drivers/usb/gadget/udc -I\$(src)
obj-m :=$func
usb_f_eem-y := f_eem.o
usb_f_ncm-y := f_ncm.o
usb_f_ecm-y := f_ecm.o
usb_f_acm-y := f_acm.o
usb_f_serial-y := f_serial.o
EOF
dirs=
[ -n "$net" ] && dirs="drivers/net/usb"
[ -n "$core$func" ] && dirs="$dirs drivers/usb/gadget"
for d in $dirs; do
    make -C "$KTREE" M="$KM/$d" -j"$(nproc)" modules >> "$OUT/build/modules-build.log" 2>&1 ||
        { tail -30 "$OUT/build/modules-build.log"; exit 1; }
done
( cd "$KM" && find drivers -name '*.ko' ) | while read -r m; do
    install -D -m 0644 "$KM/$m" "$R/$MD/kernel/$m"
    strip --strip-debug "$R/$MD/kernel/$m"
done
mkdir -p "$R/$MD"
cp "$KTREE/modules.builtin" "$KTREE/modules.builtin.modinfo" "$R/$MD/"
( cd "$R/$MD" && find kernel -name '*.ko' 2>/dev/null | sort ) > "$R/$MD/modules.order"
depmod -b "$R" "$KREL"
cat "$R/$MD/modules.order" >> "$OUT/build/modules.txt"
first=$(head -n 1 "$R/$MD/modules.order")
if [ -n "$first" ]; then   # the Image carries the same vermagic string
    vermagic=$(modinfo -F vermagic "$R/$MD/$first")
    echo "vermagic $vermagic" >> "$OUT/build/modules.txt"
    strings -n 20 "$KERNEL" | grep -qxF "$vermagic"
fi

# Omarchy: the pinned tree at OMARCHY_PATH, its user configuration, Tokyo Night.
log "omarchy configuration"
OM=$R/usr/share/omarchy
mkdir -p "$OM"
git -c safe.directory='*' -C /mnt/omarchy archive --format=tar "$OMARCHY_COMMIT" \
    bin config default themes/tokyo-night version LICENSE | tar -x -C "$OM"
first_bg=$(ls "$OM/themes/tokyo-night/backgrounds" | sort | awk 'NR == 1')
find "$OM/themes/tokyo-night/backgrounds" -type f ! -name "$first_bg" -delete
chroot "$R" getent group seat > /dev/null || chroot "$R" groupadd -r seat
# systemd-journal: the status screen follows the kernel log with journalctl -k as this user.
chroot "$R" useradd -m -u 1000 -U -G seat,video,input,systemd-journal -s /bin/bash omarchy
chroot "$R" passwd -l root > /dev/null
H=$R/home/omarchy
mkdir -p "$H/.config" "$H/.cache"   # Hyprland's crash reporter writes to ~/.cache/hyprland
cp -R "$OM/config/." "$H/.config/"
cp "$OM/default/bashrc" "$H/.bashrc"
cp -R --preserve=mode "$L/home/.config/." "$H/.config/"
chroot "$R" chown -R omarchy:omarchy /home/omarchy
chroot "$R" setpriv --reuid=1000 --regid=1000 --init-groups env -i HOME=/home/omarchy \
    USER=omarchy LANG=C.UTF-8 OMARCHY_PATH=/usr/share/omarchy \
    PATH=/usr/share/omarchy/bin:/usr/local/bin:/usr/bin BG="$first_bg" bash -euc '
        s=$HOME/.local/state/omarchy/current
        mkdir -p "$s"
        cp -R "$OMARCHY_PATH/themes/tokyo-night" "$s/next-theme"
        omarchy-theme-set-templates
        mv "$s/next-theme" "$s/theme"
        echo tokyo-night > "$s/theme.name"
        ln -snf "$s/theme/backgrounds/$BG" "$s/background"' \
    > "$OUT/build/theme.log" 2>&1 || { cat "$OUT/build/theme.log"; exit 1; }
ls "$H/.local/state/omarchy/current/theme" > "$OUT/build/theme-files.txt"
if [ "${DIAG:-0}" = 1 ]; then   # one-off investigations (out/job.env DIAG=1)
    { ls "$R"/usr/lib/gdk-pixbuf-2.0/2.10.0/loaders/
      grep -a -o -h -E 'GLYCIN_[A-Z_]+|GDK_PIXBUF_[A-Z_]+' "$R"/usr/lib/libglycin-2.so.0 \
          "$R"/usr/lib/libgdk_pixbuf-2.0.so.0 "$R"/usr/lib/glycin-loaders/2+/glycin-image-rs | sort -u
    } > "$OUT/build/image-loaders.txt" 2>&1 || true
    python3 -I "$J/abort_site.py" "$R/usr/bin/Hyprland" _ZN6Render2GL15CHyprOpenGLImplC1Ev 0x2380 \
        > "$OUT/build/hyprland-abort-site.txt" 2>&1 || true
fi

# The RAM-root layer and system settings.
log "ram-root layer"
cp -R --preserve=mode "$L/overlay/." "$R/"
chmod 0755 "$R/init" "$R"/usr/local/bin/* "$R"/usr/local/lib/ilinux/*.sh
echo ilinux-m5 > "$R/etc/hostname"
echo LANG=C.UTF-8 > "$R/etc/locale.conf"
ln -sf /usr/share/zoneinfo/UTC "$R/etc/localtime"
: > "$R/etc/machine-id"
systemctl --root="$R" enable seatd.service systemd-networkd.service ilinux-desktop.service ilinux-sshd.socket \
    > "$OUT/build/systemctl.log" 2>&1
systemctl --root="$R" mask systemd-firstboot.service getty@tty1.service \
    systemd-networkd-wait-online.service >> "$OUT/build/systemctl.log" 2>&1
systemctl --root="$R" set-default graphical.target >> "$OUT/build/systemctl.log" 2>&1
grep -q '^Include /etc/ssh/sshd_config.d/\*.conf' "$R/etc/ssh/sshd_config" ||
    sed -i '1i Include /etc/ssh/sshd_config.d/*.conf' "$R/etc/ssh/sshd_config"
mkdir -p "$W/hostkey"
if [ ! -f "$W/hostkey/ssh_host_ed25519_key" ]; then   # one host identity for every rebuild
    chroot "$R" ssh-keygen -q -t ed25519 -N '' -C ilinux-ram-root -f /tmp/hostkey
    cp "$R/tmp/hostkey" "$W/hostkey/ssh_host_ed25519_key"
    cp "$R/tmp/hostkey.pub" "$W/hostkey/ssh_host_ed25519_key.pub"
fi
install -m 0600 "$W/hostkey/ssh_host_ed25519_key" "$R/etc/ssh/"
install -m 0644 "$W/hostkey/ssh_host_ed25519_key.pub" "$R/etc/ssh/"
ssh-keygen -lf "$W/hostkey/ssh_host_ed25519_key.pub" > "$OUT/ssh-host-key-fingerprint.txt"
# Operator public keys for the native image: out/authorized_keys (gitignored) when present, else
# the M1's own public key, which job 041 ships in the Stage-B initramfs the same way. root and
# omarchy get the same keys (sshd reads /etc/ssh/authorized_keys.d/<user>); public keys only.
# sshd opens that file with the uid of the user logging in, so the files are 0644 and root-owned
# (at 0600 every omarchy login was refused: VM job 046). root's too: it holds the same keys as
# omarchy's, so 0600 would hide nothing.
AUTH=$OUT/authorized_keys
[ -s "$AUTH" ] || AUTH=/mnt/ilinux/kernel/experiments/usb-gadget/authorized_keys
if [ -s "$AUTH" ]; then
    for u in root omarchy; do install -D -m 0644 "$AUTH" "$R/etc/ssh/authorized_keys.d/$u"; done
    ssh-keygen -lf "$AUTH" > "$OUT/authorized-keys-fingerprints.txt"
fi
chroot "$R" sshd -t
mkdir -p "$R/usr/share/ilinux"
cp "$OUT/packages.txt" "$R/usr/share/ilinux/packages.txt"
printf 'built %s\nomarchy %s\nkernel %s (sha256 %s)\n' "$(date -u +%FT%TZ)" \
    "$OMARCHY_COMMIT" "$KREL" "$IMAGE_SHA" > "$R/usr/share/ilinux/build-info.txt"

# The repository's portable C benchmarks, built here for the image (the image has no compiler):
# single-thread cpubench and membench, which ilinux-bench runs once at the desktop and the
# status screen prints. -march=armv8.4-a is a fixed target that both the M5 and QEMU's "max"
# CPU (sve=off, sme=off, pauth=off in the boot test) run; no SME kernel is compiled in. Static
# when the VM's glibc provides libc.a, else dynamic against the image's libraries; either way
# both binaries are run once inside the image root with a tiny, bounded workload.
log "benchmarks"
BB=$T/bench
rm -rf "$BB"
mkdir -p "$BB"
cp /mnt/ilinux/benchmarks/src/cpubench.c /mnt/ilinux/benchmarks/src/membench.c "$BB/"
BFLAGS="-O3 -march=armv8.4-a -pthread"
: > "$OUT/build/bench-build.log"
blink=static
for b in cpubench membench; do
    if ! gcc $BFLAGS -static -o "$BB/$b" "$BB/$b.c" >> "$OUT/build/bench-build.log" 2>&1; then
        blink=dynamic
        gcc $BFLAGS -o "$BB/$b" "$BB/$b.c" >> "$OUT/build/bench-build.log" 2>&1 ||
            { tail -20 "$OUT/build/bench-build.log"; exit 1; }
    fi
    install -m 0755 "$BB/$b" "$R/usr/local/bin/$b"
done
{ echo "compiler $(gcc --version | head -1)"
  echo "flags $BFLAGS ($blink)"
  echo "sources benchmarks/src at ilinux $(git -c safe.directory='*' -C /mnt/ilinux rev-parse --short HEAD 2>/dev/null || echo unknown)"
  (cd /mnt/ilinux/benchmarks/src && sha256sum cpubench.c membench.c)
  file "$BB/cpubench" "$BB/membench" 2>/dev/null | sed "s|$BB/||" || true; } > "$R/usr/share/ilinux/bench-build.txt"
cp "$R/usr/share/ilinux/bench-build.txt" "$OUT/build/bench-build.txt"
{ timeout 120 chroot "$R" /usr/local/bin/cpubench freq -r 1 -s 0.05
  timeout 120 chroot "$R" /usr/local/bin/membench fault -m 16 -r 3; } > "$OUT/build/bench-smoke.txt" 2>&1 ||
    { echo "benchmark smoke test failed:"; cat "$OUT/build/bench-smoke.txt"; exit 1; }
for key in '"kernel":"freq"' '"test":"anon_first_touch"'; do
    grep -q "$key" "$OUT/build/bench-smoke.txt" || { echo "benchmark smoke test printed no $key:"; cat "$OUT/build/bench-smoke.txt"; exit 1; }
done
cat "$OUT/build/bench-build.txt" "$OUT/build/bench-smoke.txt"

log "prune"
chroot_down "$R"
python3 -I "$J/elf_page_check.py" "$R" > "$OUT/build/elf-check-before-prune.txt"
bash "$L/prune.sh" "$R" | tee "$OUT/build/prune.txt"
chroot "$R" fc-cache -f > /dev/null
chroot "$R" ldconfig
python3 -I "$J/elf_page_check.py" "$R" > "$OUT/elf-16k-check.txt"
# Pruning must not leave a binary without a library it had before.
missing() { sed -n '/^needs_missing_library/,$p' "$1" | tail -n +2 | sort; }
comm -13 <(missing "$OUT/build/elf-check-before-prune.txt") <(missing "$OUT/elf-16k-check.txt") \
    > "$OUT/build/prune-broke.txt"
if [ -s "$OUT/build/prune-broke.txt" ]; then
    echo "pruning removed needed libraries:"
    cat "$OUT/build/prune-broke.txt"
    exit 1
fi
head -4 "$OUT/elf-16k-check.txt"
find "$R" -type f -size +1M -printf '%s %P\n' | sort -rn | awk 'NR <= 40' > "$OUT/build/largest-files.txt"
du -sm --apparent-size "$R"/usr/lib/* "$R"/usr/share/* "$R"/usr/bin 2>/dev/null | sort -rn | awk 'NR <= 40' \
    > "$OUT/build/size-top-dirs.txt"
# The same CPU-bound work the boot test repeats inside the TCG guest (guest-measure.sh).
for t in gzip zstd; do
    t0=$(date +%s.%N)
    case $t in
    gzip) gzip -6 -c "$R/usr/lib/libLLVM.so.23.1" > /dev/null ;;
    zstd) zstd -q -3 -T1 -c "$R/usr/lib/libLLVM.so.23.1" > /dev/null ;;
    esac
    echo "bench_${t}_llvm_s_vm $(calc "$(date +%s.%N) - $t0" 3)"
done > "$OUT/build/bench-vm.txt"
# A RAM root always looks freshly installed to systemd's ConditionNeedsUpdate, which would rerun
# ldconfig, the journal catalog and the other update units on every boot. Stamp it as
# systemd-update-done would (after pruning, which changes /usr's mtime).
usr_ns=$(stat -c %.9Y "$R/usr" | tr -d .)
for d in etc var; do
    printf '# Written by job 039, as systemd-update-done would.\nTIMESTAMP_NSEC=%s\n' "$usr_ns" > "$R/$d/.updated"
done
{ echo "root_bytes $(du -sb --apparent-size "$R" | cut -f1)"
  echo "root_files $(find "$R" -mindepth 1 | wc -l)"; } > "$OUT/sizes.txt"

# ---- pack and compress ------------------------------------------------------------------
log "pack"
( cd "$R" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort |
  cpio --quiet -o -H newc --reproducible ) > "$T/ramroot.cpio"
echo "cpio_bytes $(stat -c %s "$T/ramroot.cpio")" >> "$OUT/sizes.txt"
compress() {  # compress NAME ZSTD-ARGS...: size, time with all threads, 1-thread decode time
    local name=$1; shift
    local t0 t1 t2
    t0=$(date +%s.%N)
    zstd -q -T0 "$@" -c "$T/ramroot.cpio" > "$T/$name.zst"
    t1=$(date +%s.%N)
    zstd -q -d -T1 --long=31 -c "$T/$name.zst" > /dev/null
    t2=$(date +%s.%N)
    printf 'zstd %-28s bytes %11d  compress_s %7s  decompress_1thread_s %5s\n' "$*" \
        "$(stat -c %s "$T/$name.zst")" "$(calc "$t1 - $t0")" "$(calc "$t2 - $t1" 2)" \
        >> "$OUT/compression.txt"
}
: > "$OUT/compression.txt"
if [ "$FAST" = 1 ]; then
    FINAL_ARGS="-3"
else
    compress l3 -3
    compress l19 -19
    compress l19long -19 --long=27
    FINAL_ARGS="--ultra -22 --long=27"
fi
compress final $FINAL_ARGS
cat "$OUT/compression.txt"
mv "$T/final.zst" "$OUT/ramroot.cpio.zst"
rm -f "$T"/l*.zst
(cd "$OUT" && sha256sum ramroot.cpio.zst > ramroot.cpio.zst.sha256)
size=$(stat -c %s "$OUT/ramroot.cpio.zst")
{ echo "zst_bytes $size"
  echo "zst_args $FINAL_ARGS"
  echo "transfer_s_at_4MBps $(calc "$size / 4000000")"
  echo "transfer_s_at_5MBps $(calc "$size / 5000000")"; } >> "$OUT/sizes.txt"
cat "$OUT/sizes.txt"
[ "$TEST" = 1 ] || exit 0


# ---- boot test: QEMU (TCG), one vCPU, DT simple-framebuffer -> simpledrm -----------------
FB_ADDR=0x220000000                 # top of the guest's 8 GiB, reserved (no-map)
FB_W=3456 FB_H=2234 FB_FMT=x2r10g10b10
FB_STRIDE=$((FB_W * 4))
FB_SIZE=$((FB_STRIDE * FB_H))
log "test tools"
if [ ! -x "$TOOLS/usr/bin/qemu-system-aarch64" ]; then
    rm -rf "$TOOLS"
    mkdir -p "$TOOLS/var/lib/pacman" "$TOOLS/var/log" "$TOOLS/etc/pacman.d/hooks"
    chroot_up "$TOOLS"
    pac "$TOOLS" -Sy --noconfirm --needed qemu-system-aarch64 openssh \
        > "$OUT/test/tools-install.log" 2>&1 || { tail -30 "$OUT/test/tools-install.log"; exit 1; }
    chroot_down "$TOOLS"
fi
X=$T/test
rm -rf "$X"
mkdir -p "$X"
cp "$KERNEL" "$X/Image"
chroot_up "$TOOLS"
mkdir -p "$TOOLS/work"
mount --bind "$X" "$TOOLS/work"
pac "$TOOLS" -Q jemalloc > /dev/null 2>&1 || pac "$TOOLS" -S --noconfirm --needed jemalloc > /dev/null
pac "$TOOLS" -Q qemu-system-aarch64 openssh jemalloc > "$OUT/test/tools.txt"
# Quickshell, Omarchy 4's shell (not in this image), links jemalloc, whose page size is fixed
# when it is built: one built for 4 KiB pages refuses to start on a 16 KiB kernel. This build
# VM runs a 16 KiB-page kernel, so preloading ALARM's jemalloc into ssh -V is the test.
{ pac "$TOOLS" -Q jemalloc
  grep -o -E -- "--with-lg-page=[0-9]+" "$TOOLS/usr/bin/jemalloc-config" || echo "configure options: no --with-lg-page"
  echo "build VM page size: $(getconf PAGESIZE)"
  if chroot "$TOOLS" /usr/bin/env LD_PRELOAD=/usr/lib/libjemalloc.so.2 MALLOC_CONF=abort:true \
        /usr/bin/ssh -V; then
      echo "jemalloc initialised with 16 KiB pages"
  else
      echo "jemalloc failed with 16 KiB pages (exit $?)"
  fi; } > "$OUT/jemalloc-page-size.txt" 2>&1
mkdir -p "$W/testkey"
if [ ! -f "$W/testkey/id_ed25519" ]; then   # VM-test key; stays on this VM's disk
    chroot "$TOOLS" ssh-keygen -q -t ed25519 -N '' -C ilinux-vm-test -f /work/id_ed25519
    cp "$X/id_ed25519" "$X/id_ed25519.pub" "$W/testkey/"
fi
install -m 0600 "$W/testkey/id_ed25519" "$X/id_ed25519"
# Test-only additions in a second, uncompressed cpio that the kernel unpacks over the first.
# The kernel recognises an uncompressed cpio only at a 4-byte boundary, so pad the first.
O=$T/test-overlay
rm -rf "$O"
cp -R "$J/test-overlay" "$O"
chmod 0755 "$O"/usr/local/bin/*
install -D -m 0600 "$W/testkey/id_ed25519.pub" "$O/etc/ssh/authorized_keys.d/root"
( cd "$O" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort |
  cpio --quiet -o -H newc --reproducible -R 0:0 ) > "$X/test-overlay.cpio"
cp "$OUT/ramroot.cpio.zst" "$X/initrd"
head -c $(( (4 - $(stat -c %s "$X/initrd") % 4) % 4 )) /dev/zero >> "$X/initrd"
cat "$X/test-overlay.cpio" >> "$X/initrd"
# TCG by default. Under nested KVM (this VM started with --nested) the guest's timer
# interrupts were almost never delivered: jiffies stopped 204 ticks (0.8 s) after boot while
# the clock read 8.3 s, and every boot stalled the first time the guest waited (runs 1-8).
# TCG is slow, so its timings are emulation timings, but timers work and idle=nop (the
# native M5 setting) can stay. No SVE/SME/pointer authentication: they only slow TCG down.
if [ "$VM_ACCEL" = kvm ] && [ -c /dev/kvm ]; then
    ACCEL=kvm CPU=host TIMEOUT=420 IDLE=
else
    ACCEL=tcg,thread=multi,tb-size=1024 CPU=max,sve=off,sme=off,pauth=off TIMEOUT=2700 IDLE=idle=nop
fi
# /dev/console is a virtio console (hvc0); the harness reads the test markers from it.
CMDLINE="console=tty0 console=hvc0 quiet maxcpus=1 nr_cpus=1 $IDLE arm64.nowfxt cpufreq.off=1"
[ "$DEBUG" = 1 ] && CMDLINE="console=hvc0 loglevel=7 nokaslr systemd.show_status=1 systemd.journald.forward_to_console=1 maxcpus=1 nr_cpus=1 $IDLE arm64.nowfxt cpufreq.off=1"
CMDLINE="$CMDLINE${CMDLINE_EXTRA:+ $CMDLINE_EXTRA}"
JIFFIES=$(awk '$3 == "jiffies_64" {print $1}' "$KTREE/System.map")   # nokaslr address
MACHINE=virt,gic-version=3
QARGS=(-accel "$ACCEL" -cpu "$CPU" -smp 1 -m 8G
       -device virtio-serial-pci,id=vser -chardev file,id=hvc0,path=/work/console.log
       -device virtconsole,chardev=hvc0,bus=vser.0
       -device qemu-xhci,id=xhci -device usb-net,bus=xhci.0,netdev=u0,mac=02:69:6c:69:6e:01
       -netdev "user,id=u0,net=10.66.0.0/24,host=10.66.0.1,dhcpstart=10.66.0.10,hostfwd=tcp:127.0.0.1:2222-10.66.0.2:22")
# The machine's own device tree plus what m1n1 adds on the M5: a reserved framebuffer region
# and a /chosen simple-framebuffer node that points at it.
chroot "$TOOLS" qemu-system-aarch64 -machine "$MACHINE,dumpdtb=/work/virt.dtb" "${QARGS[@]}" \
    -display none > "$X/dumpdtb.log" 2>&1
hi=$(printf '0x%x' $((FB_ADDR >> 32))) lo=$(printf '0x%08x' $((FB_ADDR & 0xffffffff)))
{ dtc -q -I dtb -O dts "$X/virt.dtb"
  cat <<DTS

/ {
	reserved-memory {
		#address-cells = <2>;
		#size-cells = <2>;
		ranges;
		fbmem: framebuffer@${FB_ADDR#0x} {
			reg = <$hi $lo 0x0 0x2000000>;
			no-map;
		};
	};
	chosen {
		framebuffer@${FB_ADDR#0x} {
			compatible = "simple-framebuffer";
			reg = <$hi $lo 0x0 $(printf '0x%x' $FB_SIZE)>;
			memory-region = <&fbmem>;
			width = <$FB_W>;
			height = <$FB_H>;
			stride = <$FB_STRIDE>;
			format = "$FB_FMT";
			status = "okay";
		};
	};
};
DTS
} > "$X/virt-fb.dts"
dtc -q -I dts -O dtb -o "$X/virt-fb.dtb" "$X/virt-fb.dts"
cp "$X/virt-fb.dts" "$OUT/test/"
{ echo "accel $ACCEL; cpu $CPU; machine $MACHINE; 1 vCPU; 8 GiB"
  echo "framebuffer ${FB_W}x${FB_H} $FB_FMT stride $FB_STRIDE at $FB_ADDR (DT simple-framebuffer)"
  echo "cmdline $CMDLINE"; } > "$OUT/test/qemu-setup.txt"
log "boot (${ACCEL%%,*}, 1 vCPU, ${FB_W}x${FB_H} $FB_FMT)"
t0=$(date +%s.%N)
chroot "$TOOLS" qemu-system-aarch64 -name ilinux-ramroot -machine "$MACHINE" "${QARGS[@]}" \
    -dtb /work/virt-fb.dtb -kernel /work/Image -initrd /work/initrd -append "$CMDLINE" \
    -serial file:/work/serial.log -display none -monitor unix:/work/hmp.sock,server,nowait \
    -no-reboot > "$X/qemu.log" 2>&1 &
QPID=$!
hmp() { python3 -I /mnt/ilinux/tools/qemumon.py "$X/hmp.sock" "$@"; }
fbshot() {  # fbshot NAME: the simple-framebuffer bytes in guest RAM, i.e. what the panel shows
    rm -f "$X/fb.raw"
    hmp "pmemsave $FB_ADDR $FB_SIZE \"/work/fb.raw\"" >> "$OUT/test/hmp.log" 2>&1 || true
    for _ in $(seq 20); do [ "$(stat -c %s "$X/fb.raw" 2>/dev/null)" = "$FB_SIZE" ] && break; sleep 0.5; done
    python3 -I "$J/fb2png.py" "$X/fb.raw" $FB_W $FB_H $FB_STRIDE $FB_FMT "$OUT/test/$1.png" "${2:-1}" ||
        echo "fbshot $1 failed" >&2
}
ready= seen= shot=0 memdone=
SECONDS=0
while [ "$SECONDS" -lt "$TIMEOUT" ] && kill -0 "$QPID" 2>/dev/null; do
    every=120; [ "$DEBUG" = 1 ] && every=30
    if [ "$SECONDS" -ge $((shot * every + every)) ]; then   # progress frames, quarter scale
        shot=$((shot + 1)); fbshot "progress-$((shot * every))s" 4
        if [ "$DEBUG" = 1 ]; then
            for _ in 1 2 3; do hmp "info registers" | tr -d '\r' | grep -E 'PC=|X30=' >> "$X/regs.log"; sleep 0.2; done
            echo "t=$SECONDS $(hmp "x /1gx 0x$JIFFIES" | tr -d '\r' | grep -a -o -E '^[0-9a-f]+: 0x[0-9a-f]+' | tail -1)" >> "$OUT/test/jiffies.log"
        fi
    fi
    cp "$X/console.log" "$OUT/test/console.log" 2>/dev/null || true   # visible on the host
    if grep -q 'ILINUX-BENCH-END' "$X/console.log" 2>/dev/null; then
        ready=1
        echo "wall_s_qemu_start_to_bench_end_marker $(calc "$(date +%s.%N) - $t0")" >> "$OUT/test/wall.txt"
        break
    fi
    if grep -q 'ILINUX-DEBUG-END' "$X/console.log" 2>/dev/null; then break; fi
    if [ -z "$memdone" ] && grep -q 'ILINUX-MEMINFO-END' "$X/console.log" 2>/dev/null; then ready=1; memdone=$SECONDS; fi
    # The guest waits up to 900 s for the benchmark itself; this is the harness's own bound.
    if [ -n "$memdone" ] && [ $((SECONDS - memdone)) -gt 1000 ]; then break; fi
    if [ -z "$seen" ] && grep -q 'ILINUX-DESKTOP-READY' "$X/console.log" 2>/dev/null; then
        seen=1
        echo "wall_s_qemu_start_to_ready_marker $(calc "$(date +%s.%N) - $t0")" > "$OUT/test/wall.txt"
        # Two half-size frames 30 s apart: the status screen's counter must differ between them
        # (under TCG the compositor's llvmpipe frames lag the screen by up to about 20 s).
        fbshot ready-1 2; sleep 30; fbshot ready-2 2
    fi
    sleep 0.5
done
gssh() {   # bounded, so a step that hangs in the guest cannot hold the vm lock (run 27 did)
    timeout --kill-after=10 900 chroot "$TOOLS" ssh -i /work/id_ed25519 -p 2222 -o BatchMode=yes \
        -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/work/known_hosts \
        root@127.0.0.1 "$@"
}
# Under TCG the compositor's frames lag the status screen by up to about 20 s (runs 31-32);
# give it time to show the finished benchmark table before the final capture.
[ -n "$ready" ] && sleep 30
fbshot framebuffer
python3 -I "$J/fb2png.py" "$X/fb.raw" $FB_W $FB_H $FB_STRIDE $FB_FMT "$OUT/test/framebuffer-half.png" 2 || true
[ -n "$ready" ] && log "desktop ready" || log "NO desktop-ready marker (timeout ${TIMEOUT}s, diagnostics or QEMU exit)"
gssh bash -s < "$J/guest-measure.sh" > "$OUT/test/guest-measure.txt" 2>&1 || true
gssh journalctl -b -o short-monotonic --no-pager > "$OUT/test/journal.txt" 2>&1 || true
gssh dmesg > "$OUT/test/dmesg.txt" 2>&1 || true
gssh 'for d in /run/user/1000/hypr/*/; do echo "=== $d"; cat "$d/hyprland.log"; done' \
    > "$OUT/test/hyprland.log" 2>&1 || true
gssh cat /run/ilinux/bench/results.jsonl > "$OUT/test/bench-results.jsonl" 2>/dev/null || true
gssh 'cat /run/ilinux/bench/env.txt /run/ilinux/bench/steps.txt /run/ilinux/bench/status; echo; echo "--- errors"; cat /run/ilinux/bench/errors.txt' \
    > "$OUT/test/bench-run.txt" 2>&1 || true
gssh 'cat /run/ilinux/status.log; echo "--- kernel log follower"; cat /run/ilinux/kmsg.txt' > "$OUT/test/status-screen.txt" 2>&1 || true
gssh 'd=$(cd /run/user/1000 && ls -d wayland-[0-9]* | grep -v lock | head -1);
      setpriv --reuid=1000 --regid=1000 --init-groups env XDG_RUNTIME_DIR=/run/user/1000 \
      WAYLAND_DISPLAY=$d grim /tmp/grim.png && cat /tmp/grim.png' > "$OUT/test/grim.png" 2>/dev/null || true
gssh systemctl poweroff > /dev/null 2>&1 || true
for _ in $(seq 60); do kill -0 "$QPID" 2>/dev/null || break; sleep 1; done
kill "$QPID" 2>/dev/null || true
wait "$QPID" 2>/dev/null || true
QPID=
cp "$X/console.log" "$X/serial.log" "$X/qemu.log" "$X/dumpdtb.log" "$OUT/test/" 2>/dev/null || true
[ -s "$X/regs.log" ] && python3 -I "$J/pc2sym.py" "$KTREE/System.map" < "$X/regs.log" > "$OUT/test/vcpu-pc.txt"
python3 -I "$J/summarize.py" "$OUT" > "$OUT/results.json" || true
cat "$OUT/results.json"
[ -n "$ready" ] || { echo "FAIL: desktop not reached"; exit 1; }
# swaybg decodes the wallpaper through glycin, which runs its loader in bubblewrap: this also
# checks that bubblewrap works in the session (it refused while the session held a capability).
if grep -q 'Failed to load background image' "$OUT/test/journal.txt"; then
    echo "FAIL: desktop reached, but swaybg could not load the wallpaper (glycin/bubblewrap)"
    exit 1
fi
# Attempt 19 showed Hyprland's "started without start-hyprland" notice for 15 s: the session
# must run under the supervisor, and the status screen's benchmark run must have finished.
if grep -q -i 'without start-hyprland' "$OUT/test/journal.txt" "$OUT/test/hyprland.log"; then
    echo "FAIL: Hyprland was started without start-hyprland"
    exit 1
fi
if grep -q 'ILINUX-BENCH-TIMEOUT' "$OUT/test/console.log" || ! grep -q 'ILINUX-BENCH-END' "$OUT/test/console.log"; then
    echo "FAIL: the status screen's benchmark run did not finish within the wait"
    exit 1
fi
for key in '"kernel":"fma_asm"' '"kernel":"syscall_getppid"' '"test":"stream_copy"' '"test":"latency_random_chase"' '"test":"anon_first_touch"'; do
    grep -q "$key" "$OUT/test/bench-results.jsonl" || { echo "FAIL: no benchmark result for $key"; exit 1; }
done
# The status screen logs "tick N at T s" once a minute: its loop must have kept going at
# roughly its period (1 s at the desktop, 2 s before it) from its first tick to its last.
read -r t1 n1 tn nn < <(awk '/^\[[0-9.]+\] tick [0-9]+ at [0-9.]+ s$/ {if (!f) {f = 1; t1 = $5; n1 = $3} tn = $5; nn = $3}
                             END {print t1 + 0, n1 + 0, tn + 0, nn + 0}' "$OUT/test/status-screen.txt")
if [ "${nn:-0}" -lt 2 ] || ! awk -v t1="$t1" -v n1="$n1" -v tn="$tn" -v nn="$nn" \
        'BEGIN {exit !(tn - t1 > 0 && (nn - n1) / (tn - t1) >= 0.4)}'; then
    echo "FAIL: the status screen's loop stopped or ran far below its period (ticks $n1..$nn over ${t1}-${tn} s)"
    exit 1
fi
cmp -s "$OUT/test/ready-1.png" "$OUT/test/ready-2.png" && echo "note: the two counter frames 30 s apart are identical (compositor lag under TCG?)"
steps=$(grep -c ' exit ' "$OUT/test/bench-run.txt" 2>/dev/null || echo 0)
failed=$(grep -c ' exit [1-9]' "$OUT/test/bench-run.txt" 2>/dev/null || echo 0)
echo "PASS: RAM root reached the Hyprland desktop with its wallpaper under start-hyprland; the status screen ticked $nn times in $(awk -v a="$t1" -v b="$tn" 'BEGIN {printf "%.0f", b - a}') s and ran $steps benchmark steps, $failed failed (1 vCPU, ${ACCEL%%,*}, simpledrm ${FB_W}x${FB_H})"
