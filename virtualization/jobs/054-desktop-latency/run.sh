#!/bin/bash
# Existing Linux build VM only: --gui --size 3456x2160. No physical hardware.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux
O=/mnt/job/out
S=$I/kernel/experiments/desktop30
W=/run/d30
R=$W/root
mkdir -p "$O" "$W"
exec > "$O/detail.log" 2>&1
. "$I/virtualization/jobs/045-omarchy-installer-root/lib.sh"
cleanup() {
    set +e
    for f in "$R"/run/user/1000/hypr/*/hyprland.log; do [ ! -f "$f" ] || cp "$f" "$O/exact-internal.log"; done
    [ -z "${HP:-}" ] || kill "$HP" 2>/dev/null || true
    [ -z "${SP:-}" ] || kill "$SP" 2>/dev/null || true
    mountpoint -q "$R/run/d30/results" && umount "$R/run/d30/results" || true
    chroot_down "$R" || true
    if mountpoint -q "$W"; then umount "$W" || umount -R -l "$W"; fi
}
trap cleanup EXIT
mount -t tmpfs -o size=16G,mode=0755 tmpfs "$W"
mkdir -p "$R" "$W/compile"
wayland-scanner client-header /usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml "$W/compile/xdg-shell-client-protocol.h"
wayland-scanner private-code /usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml "$W/compile/xdg-shell-protocol.c"
cc -O2 -Wall -Wextra -Werror -I"$W/compile" "$S/frameprobe.c" "$W/compile/xdg-shell-protocol.c" -lwayland-client -o "$O/frameprobe"
cc -O1 -g -fsanitize=address,undefined -Wall -Wextra -Werror -I"$W/compile" "$S/frameprobe.c" "$W/compile/xdg-shell-protocol.c" -lwayland-client -o "$O/frameprobe-san"
cc -O2 -Wall -Wextra -Werror "$S/samplecpu.c" -o "$O/samplecpu"
cc -O1 -g -fsanitize=address,undefined -Wall -Wextra -Werror "$S/test_sampler.c" -o "$O/test-sampler"
"$O/test-sampler" > "$O/sampler-tests.txt"
{ cc --version | head -1; pacman -Q wayland wayland-protocols; sha256sum /usr/share/wayland-protocols/stable/xdg-shell/xdg-shell.xml; } > "$O/compiler.txt"
echo '59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78  '"$I/build/attempt28-transfer/ramroot.cpio.zst" | sha256sum -c -
bsdtar -xpf "$I/build/attempt28-transfer/ramroot.cpio.zst" -C "$R"
sha256sum "$R/usr/bin/Hyprland" | cut -d' ' -f1 > "$O/root-hyprland.sha256"
grep -qx a9e57097798b2e815c8e91a0a4472d287573c4f7ce177b72a5b0907562a68da9 "$O/root-hyprland.sha256"
systemctl stop display-manager.service 2>/dev/null || true
chmod a+rw /dev/dri/card0 /dev/dri/renderD128
chroot_up "$R"
mkdir -p "$R/run/user/1000" "$R/run/d30" "$R/run/d30/results"
chmod 700 "$R/run/user/1000"
chown 1000:1000 "$R/run/user/1000"
mount --bind "$O" "$R/run/d30/results"
cp "$O/frameprobe" "$O/samplecpu" "$O/frameprobe-san" "$S/collect.py" "$S/receive.py" /mnt/job/vmcheck.py /mnt/job/receivercheck.py "$R/run/d30/"
chmod 755 "$R/run/d30/frameprobe" "$R/run/d30/samplecpu" "$R/run/d30/frameprobe-san"
chroot "$R" pacman -Q hyprland mesa wayland aquamarine > "$O/root-versions.txt"
chroot "$R" env XDG_RUNTIME_DIR=/run/user/1000 Hyprland --version > "$O/root-hyprland-version.txt"
# Only the VM copy: match native's scale1 with the VM's Virtual-1 output.
T=$R/home/omarchy/.local/state/omarchy/toggles/hypr
printf '%s\n' 'hl.monitor({output="Virtual-1",mode="3456x2160@60",position="0x0",scale=1})' > "$T/zz-vm30.lua"
chown 1000:1000 "$T/zz-vm30.lua"
chroot "$R" env SEATD_VTBOUND=0 seatd -g wheel > "$O/seatd.log" 2>&1 &
SP=$!
sleep 1
timeout -k 5 180 chroot "$R" setpriv --reuid=omarchy --regid=omarchy --init-groups env HOME=/home/omarchy USER=omarchy LOGNAME=omarchy XDG_RUNTIME_DIR=/run/user/1000 XDG_SESSION_TYPE=wayland LIBSEAT_BACKEND=seatd SEATD_SOCK=/run/seatd.sock AQ_DRM_DEVICES=/dev/dri/card0 LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=0 OMARCHY_PATH=/usr/share/omarchy PATH=/usr/local/bin:/usr/bin:/usr/share/omarchy/bin taskset -c 0 dbus-run-session -- start-hyprland > "$O/hypr.log" 2>&1 &
HP=$!
chroot "$R" id omarchy > "$O/identity-vm-user.txt"
ls -l "$R/run/seatd.sock" > "$O/seat-socket.txt"
chroot "$R" env ILINUX_VM_STARTPID="$HP" python3 -I /run/d30/vmcheck.py
python3 -I "$S/test_desktop30.py"
python3 -I "$I/tools/m1n1-client/test_attempt30_collect.py"
ILINUX_BOOT042="$I/build/native-boot042/verified" /var/tmp/ilinux-cpu28-controller-venv/bin/python -I "$I/native/boot/test_cpu_observe.py"
python3 -I "$I/native/boot/test_ramroot.py"
cp "$S/collect.py" "$O/"
python3 -I /mnt/job/package.py
chroot "$R" python3 -I /run/d30/receivercheck.py
umount "$R/run/d30/results"
