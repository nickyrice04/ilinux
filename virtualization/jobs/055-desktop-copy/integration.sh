#!/bin/bash
# Exact packed candidate userspace, RAM copy only, inside the existing VZ VM.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux O=/mnt/job/out W=/run/d31
R=$W/root
exec > "$O/integration.log" 2>&1
. "$I/virtualization/jobs/045-omarchy-installer-root/lib.sh"
cleanup() {
    set +e
    for f in "$R"/run/user/1000/hypr/*/hyprland.log; do [ ! -f "$f" ] || cp "$f" "$O/integration-internal.log"; done
    [ ! -f "$R/run/user/1000/ilinux-copy31.log" ] || cp "$R/run/user/1000/ilinux-copy31.log" "$O/copy31-path.log"
    [ -z "${HP:-}" ] || kill "$HP" 2>/dev/null || true
    [ -z "${SP:-}" ] || kill "$SP" 2>/dev/null || true
    chroot_down "$R" || true
    if mountpoint -q "$W"; then umount "$W" || umount -R -l "$W"; fi
}
trap cleanup EXIT
mkdir -p "$W"
mount -t tmpfs -o size=16G,mode=0755 tmpfs "$W"
mkdir -p "$R"
python3 -I - "$I" "$O" <<'PY'
import hashlib, json, pathlib, sys
i,o=map(pathlib.Path,sys.argv[1:])
record=json.loads((i/'native/boot/attempt31/omarchy-root-manifest.json').read_text())
p=o/'images/ramroot.cpio.zst'
assert p.stat().st_size==record['size']
with p.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==record['sha256']
PY
bsdtar -xpf "$O/images/ramroot.cpio.zst" -C "$R"
cmp "$R/usr/bin/Hyprland" "$O/Hyprland-copy31"
cmp "$R/usr/local/lib/ilinux-desktop31/assets.json" "$I/native/boot/attempt31/assets.json"

systemctl stop display-manager.service 2>/dev/null || true
chmod a+rw /dev/dri/card0 /dev/dri/renderD128
chroot_up "$R"
# The actual shipping collector must refuse generic VM identity before marking
# an attempt consumed or altering the desktop.
rc=0
chroot "$R" python3 -I /usr/local/lib/ilinux-desktop31/collect.py > "$O/native-guard.txt" 2>&1 || rc=$?
test "$rc" = 3
test ! -e "$R/run/ilinux-desktop31.started"
grep -q '"event": "stop"' "$O/native-guard.txt"
echo 'SHIPPING-NATIVE-GUARD-PASS'
mkdir -p "$R/run/user/1000" "$R/run/d31"
chmod 700 "$R/run/user/1000"
chown 1000:1000 "$R/run/user/1000"
cp "$I/virtualization/jobs/054-desktop-latency/out/frameprobe" "$I/virtualization/jobs/054-desktop-latency/out/samplecpu" "$R/run/d31/"
cp "$I/kernel/experiments/desktop30/collect.py" "$R/run/d31/collect30.py"
cp /mnt/job/vmcheck.py "$R/run/d31/"
sha256sum "$R/usr/bin/Hyprland" | cut -d' ' -f1 > "$R/run/d31/new.sha256"
chroot "$R" env XDG_RUNTIME_DIR=/run/user/1000 Hyprland --version > "$O/new-version.txt"
T=$R/home/omarchy/.local/state/omarchy/toggles/hypr
printf '%s\n' 'hl.monitor({output="Virtual-1",mode="3456x2160@60",position="0x0",scale=1})' > "$T/zz-vm31.lua"
chown 1000:1000 "$T/zz-vm31.lua"
chroot "$R" env SEATD_VTBOUND=0 seatd -g wheel > "$O/seatd.log" 2>&1 &
SP=$!
sleep 1
timeout -k 5 240 chroot "$R" setpriv --reuid=omarchy --regid=omarchy --init-groups env HOME=/home/omarchy USER=omarchy LOGNAME=omarchy XDG_RUNTIME_DIR=/run/user/1000 XDG_SESSION_TYPE=wayland LIBSEAT_BACKEND=seatd SEATD_SOCK=/run/seatd.sock AQ_DRM_DEVICES=/dev/dri/card0 LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=0 OMARCHY_PATH=/usr/share/omarchy PATH=/usr/local/bin:/usr/bin:/usr/share/omarchy/bin taskset -c 0 dbus-run-session -- start-hyprland > "$O/hypr31.log" 2>&1 &
HP=$!
chroot "$R" python3 -I /run/d31/vmcheck.py > "$O/integration-result.txt" 2>&1
# Exercise the shipped independent reset through real systemd ExecStopPost,
# retaining its stdout framing for the M1 parser test.
systemd-run --unit=copy31-reset-test --wait --collect --pipe \
  --property=RuntimeMaxSec=15 --property=TimeoutStopSec=10 \
  "--property=ExecStopPost=/usr/sbin/chroot $R /usr/bin/python3 -I /usr/local/lib/ilinux-desktop31/restore.py" \
  /usr/bin/true > "$O/reset-stdout.txt" 2> "$O/reset-stderr.txt"
grep -q '^COPY31_REFERENCE_PATH_RESTORED$' "$O/reset-stdout.txt"
echo 'SHIPPING-INDEPENDENT-RESET-PASS'
