#!/bin/bash
# Job 046: the base root for the USB SSH byte pipe and web proxy test (dummy_hcd), built in the
# workspace Arch VM (tools/vm-job.sh; host-run.sh takes the vm lock).
#  0. Run the Python unit tests of tools/m1n1-client/connect-proxy.py and usb-pipe here (another
#     Python and compiler than the Mac's); recorded, not fatal.
#  1. Build the Linux usb-pipe (the M1 stand-in's ProxyCommand, the same relay.c as on macOS).
#  2. Install a systemd root from signed Arch Linux ARM packages the way job 039 does (API
#     filesystems mounted, scriptlets and hooks run): the RAM root's own base plus python, curl and
#     certificates.
#  3-4. Put the RAM root's overlay (omarchy-arm64/ram-root/overlay) and the test overlay on it, so the
#     checks here (sshd -t, systemd-analyze verify) read the real files, add the test keys and
#     certificate (never shipped), lock root, prune, stamp, and pack out/build/base-initramfs.cpio.gz.
#  The boot is on the Mac: run-vz.sh appends a freshly built overlay cpio (make-overlay.py: the
#  same overlay files, from the working tree) and boots job 041's test Image under
#  Virtualization.framework. So edits to the files under test need no VM and no lock; only a new
#  package set, a new usb-pipe binary or new keys do.
set -euo pipefail
trap 'echo "run.sh: line $LINENO: $BASH_COMMAND (exit $?)" >&2' ERR
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
OUT=/mnt/job/out
I=/mnt/ilinux
L=$I/omarchy-arm64/ram-root/overlay
TO=$I/virtualization/jobs/046-usb-ssh-pipe/test-overlay
W=/var/tmp/ilinux-usb-pipe           # kept between runs: keyring, package cache, test keys
R=$W/root
MIRROR='https://fl.us.mirror.archlinuxarm.org/$arch/$repo'   # official ALARM mirror
# The RAM root's own base (omarchy-arm64/ram-root/packages.txt: systemd, openssh, the shell tools)
# and what the test adds: python (the proxy and the HTTPS server), curl, certificates.
PACKAGES="filesystem systemd systemd-sysvcompat dbus-broker-units bash coreutils util-linux procps-ng iproute2 shadow sed grep gawk findutils kmod openssh python curl ca-certificates"
log() { printf '[%s] %s\n' "$(date +%T)" "$*"; }
chroot_up() {  # the API filesystems pacman hooks and the scripts need, as pacstrap sets them up (job 039)
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
pac() {  # pac ARGS...: pacman on the test root with the job's config, cache, keyring and the root's own hooks
    pacman --root "$R" --dbpath "$R/var/lib/pacman" --config "$W/pacman.conf" --cachedir "$W/cache" \
        --gpgdir "$W/gnupg" --hookdir "$R/etc/pacman.d/hooks" --logfile "$R/var/log/pacman.log" "$@"
}
trap 'chroot_down "$R" 2> /dev/null' EXIT
rm -rf "$OUT/build"
mkdir -p "$OUT/build" "$W/cache"
cd "$W"

log "0. unit tests on Linux ($(python3 --version), $(gcc --version | head -1)); recorded, not fatal: the boot test is the verdict"
for t in test_connect_proxy test_usb_pipe; do
    if python3 -I "$I/tools/m1n1-client/$t.py" > "$OUT/build/$t.txt" 2>&1; then echo "$t: PASS"; else echo "$t: FAIL (see out/build/$t.txt)"; fi
    tail -3 "$OUT/build/$t.txt"
done | tee "$OUT/build/unit-tests.txt"
python3 -I "$I/virtualization/jobs/046-usb-ssh-pipe/test_make_overlay.py" > "$OUT/build/test_make_overlay.txt" 2>&1 || true
tail -2 "$OUT/build/test_make_overlay.txt"

log "1. usb-pipe for Linux (the M1 stand-in's ProxyCommand; the same relay as on macOS)"
S=$I/tools/m1n1-client/usb-pipe
if ! gcc -O2 -Wall -Wextra -pthread -static -o "$OUT/build/usb-pipe" "$S/usb-pipe.c" "$S/relay.c" > "$OUT/build/usb-pipe-build.log" 2>&1; then
    gcc -O2 -Wall -Wextra -pthread -o "$OUT/build/usb-pipe" "$S/usb-pipe.c" "$S/relay.c" >> "$OUT/build/usb-pipe-build.log" 2>&1 ||
        { cat "$OUT/build/usb-pipe-build.log"; exit 1; }
fi
cat "$OUT/build/usb-pipe-build.log"
"$OUT/build/usb-pipe" --version
"$OUT/build/usb-pipe" --dry-run > "$OUT/build/usb-pipe-no-backend.txt" 2>&1 && exit 1   # Linux: no USB backend, exit 6
grep -q 'macOS only' "$OUT/build/usb-pipe-no-backend.txt"

log "2. packages (signed, official mirror)"
if [ ! -s "$W/gnupg/trustdb.gpg" ]; then
    rm -rf "$W/gnupg"
    mkdir -p "$W/gnupg"
    pacman-key --gpgdir "$W/gnupg" --init > /dev/null
    pacman-key --gpgdir "$W/gnupg" --populate archlinuxarm > /dev/null
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
chroot_down "$R"
rm -rf "$R"
mkdir -p "$R/var/lib/pacman" "$R/var/log" "$R/etc/pacman.d/hooks"
chroot_up "$R"
pac -Sy --noconfirm --needed $PACKAGES > "$OUT/build/pacman.log" 2>&1 || { tail -30 "$OUT/build/pacman.log"; exit 1; }
pac -Q > "$OUT/build/packages.txt"
log "$(wc -l < "$OUT/build/packages.txt") packages"

log "3. keys and certificate (test only; the VM's disk keeps the test keys between runs)"
mkdir -p "$W/keys"
[ -f "$W/keys/test-key" ] || ssh-keygen -q -t ed25519 -N '' -C ilinux-job046-test -f "$W/keys/test-key"
[ -f "$W/keys/wrong-key" ] || ssh-keygen -q -t ed25519 -N '' -C ilinux-job046-wrong -f "$W/keys/wrong-key"
ssh-keygen -q -t ed25519 -N '' -C ilinux-job046-host -f "$OUT/build/host-key" < /dev/null
cat > "$OUT/build/cert.cnf" <<'EOF'
[req]
distinguished_name = dn
x509_extensions = v3
prompt = no
[dn]
CN = ilinux-test-web
[v3]
subjectAltName = DNS:web.test, IP:127.0.0.1
basicConstraints = critical, CA:TRUE
EOF
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout "$OUT/build/key.pem" \
    -out "$OUT/build/cert.pem" -days 30 -config "$OUT/build/cert.cnf" > "$OUT/build/openssl.log" 2>&1

log "4. the root: RAM-root overlay, test overlay, keys, tools"
cp -R --preserve=mode "$L/." "$R/"
chmod 0755 "$R/init" "$R"/usr/local/bin/* "$R"/usr/local/lib/ilinux/*.sh
cp -R --preserve=mode "$TO/." "$R/"
chmod 0755 "$R"/usr/local/lib/ilinux-test/*.sh "$R"/usr/local/lib/ilinux-test/*.py
install -m 0755 "$OUT/build/usb-pipe" "$R/usr/local/bin/usb-pipe"
install -m 0644 "$I/tools/m1n1-client/connect-proxy.py" "$R/usr/local/lib/ilinux-test/connect-proxy.py"
install -m 0600 "$W/keys/test-key" "$R/usr/local/lib/ilinux-test/test-key"
install -m 0600 "$W/keys/wrong-key" "$R/usr/local/lib/ilinux-test/wrong-key"
install -m 0644 "$W/keys/test-key.pub" "$R/usr/local/lib/ilinux-test/test-key.pub"
install -m 0644 "$OUT/build/cert.pem" "$R/usr/local/lib/ilinux-test/cert.pem"
install -m 0600 "$OUT/build/key.pem" "$R/usr/local/lib/ilinux-test/key.pem"
for u in root omarchy; do install -D -m 0644 "$W/keys/test-key.pub" "$R/etc/ssh/authorized_keys.d/$u"; done   # as job 039 installs the operator's keys
install -m 0600 "$OUT/build/host-key" "$R/etc/ssh/ssh_host_ed25519_key"
install -m 0644 "$OUT/build/host-key.pub" "$R/etc/ssh/ssh_host_ed25519_key.pub"
grep -q '^Include /etc/ssh/sshd_config.d/\*.conf' "$R/etc/ssh/sshd_config" ||
    sed -i '1i Include /etc/ssh/sshd_config.d/*.conf' "$R/etc/ssh/sshd_config"
# Users and the machine's identity, as job 039 sets the root up. Root's password is locked as in the
# RAM root: logins are by key only. (The RAM root's desktop user is created the same way.)
chroot "$R" useradd -M -d /home/omarchy -u 1000 -U -s /bin/bash omarchy
mkdir -p "$R/home/omarchy"
chown 1000:1000 "$R/home/omarchy"
chroot "$R" passwd -l root > /dev/null
systemd-tmpfiles --root="$R" --create > "$OUT/build/tmpfiles.log" 2>&1 || true
echo ilinux-m5-test > "$R/etc/hostname"
printf '127.0.0.1 localhost\n::1 localhost\n127.0.0.1 web.test\n' > "$R/etc/hosts"   # only the M1 side's proxy has to find web.test
echo LANG=C.UTF-8 > "$R/etc/locale.conf"
ln -sf /usr/share/zoneinfo/UTC "$R/etc/localtime"
: > "$R/etc/machine-id"
systemctl --root="$R" enable ilinux-selftest.service > "$OUT/build/systemctl.log" 2>&1
systemctl --root="$R" mask systemd-firstboot.service getty@tty1.service serial-getty@hvc0.service \
    systemd-networkd-wait-online.service systemd-homed.service >> "$OUT/build/systemctl.log" 2>&1 || true
systemctl --root="$R" set-default multi-user.target >> "$OUT/build/systemctl.log" 2>&1
# Checks on the real files; none of these may stop the build, the boot test is the verdict.
if chroot "$R" /usr/bin/sshd -t > "$OUT/build/sshd-check.txt" 2>&1; then echo "sshd -t: ok"; else echo "sshd -t: FAILED: $(cat "$OUT/build/sshd-check.txt")"; fi   # file names that differ only by case collide on the Mac
if chroot "$R" /usr/bin/sshd -T > "$OUT/build/sshd-T.txt" 2> "$OUT/build/sshd-T.err"; then echo "sshd -T: ok"
else echo "sshd -T: FAILED: $(head -3 "$OUT/build/sshd-T.err" | tr '\n' ' ')"; fi
grep -i -E '^(logingracetime|clientaliveinterval|clientalivecountmax|setenv|permitrootlogin|passwordauthentication|authorizedkeysfile|usepam) ' \
    "$OUT/build/sshd-T.txt" > "$OUT/build/sshd-effective.txt" || true
cat "$OUT/build/sshd-effective.txt"
{ chroot "$R" /usr/local/bin/usb-pipe --version
  chroot "$R" python3 -I /usr/local/lib/ilinux-test/connect-proxy.py --help > /dev/null && echo "connect-proxy.py --help: ok"
  chroot "$R" id omarchy
  chroot "$R" getent passwd root omarchy sshd
  ls -ld "$R/usr/share/empty.sshd" "$R/etc/ssh/sshd_config" "$R/usr/lib/systemd/systemd" "$R"/etc/ssh/authorized_keys.d/*; } > "$OUT/build/root-facts.txt" 2>&1 || true
cat "$OUT/build/root-facts.txt"
chroot_down "$R"
# What the boot never reads (as prune.sh does for the RAM root): the image is unpacked into the
# Mac VM's memory and written to the shared folder.
rm -rf "$R"/usr/share/{doc,man,info,gtk-doc,help,i18n} "$R"/usr/include "$R"/usr/lib/pkgconfig \
       "$R"/var/cache/pacman "$R"/var/lib/pacman/sync
find "$R"/usr/share/locale -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2> /dev/null || true
du -sm --apparent-size "$R" | awk '{print "root size " $1 " MiB"}' | tee "$OUT/build/root-size.txt"
# A RAM root always looks freshly installed to systemd's ConditionNeedsUpdate, which would rerun
# ldconfig, the journal catalog and the other update units at boot (job 039 stamps it the same way).
usr_ns=$(stat -c %.9Y "$R/usr" | tr -d .)
for d in etc var; do
    printf '# Written by job 046, as systemd-update-done would.\nTIMESTAMP_NSEC=%s\n' "$usr_ns" > "$R/$d/.updated"
done
# The units as systemd will read them.
systemd-analyze --root="$R" verify "$R/etc/systemd/system/ilinux-usb-gadget@.service" \
    "$R/etc/systemd/system/ilinux-sshd-tty@.service" "$R/etc/systemd/system/ilinux-selftest.service" \
    > "$OUT/build/systemd-verify.txt" 2>&1 || true
cat "$OUT/build/systemd-verify.txt"

log "5. pack"
( cd "$R" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort | cpio --quiet -o -H newc --reproducible ) |
    gzip -6 -n > "$OUT/build/base-initramfs.cpio.gz"
( cd "$OUT/build" && sha256sum base-initramfs.cpio.gz usb-pipe cert.pem ) | tee "$OUT/build/sha256.txt"
ls -l "$OUT/build/base-initramfs.cpio.gz"
echo "PASS: usb-pipe (Linux) and the base root built ($(grep -c ': PASS' "$OUT/build/unit-tests.txt") of 2 Linux unit-test files passed); boot it with run-vz.sh on the Mac"
