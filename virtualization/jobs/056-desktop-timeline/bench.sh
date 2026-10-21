#!/bin/bash
# VM-only diagnostic. No native image, hardware node or boot policy is changed.
set -euo pipefail
mkdir -p /mnt/ilinux
mountpoint -q /mnt/ilinux || mount -t virtiofs ilinux /mnt/ilinux
I=/mnt/ilinux O=/mnt/job/out W=/run/timeline31 R=/run/timeline31/root
exec > "$O/bench.log" 2>&1
. "$I/virtualization/jobs/045-omarchy-installer-root/lib.sh"
cleanup() {
  set +e
  [ -z "${HP:-}" ] || kill "$HP" 2>/dev/null
  [ -z "${SP:-}" ] || kill "$SP" 2>/dev/null
  chroot_down "$R"
  mountpoint -q "$W" && { umount "$W" || umount -R -l "$W"; }
}
trap cleanup EXIT
systemctl stop display-manager.service 2>/dev/null || true
if [ ! -f "$O/linux-vm/result.json" ]; then
  python3 -I "$I/kernel/experiments/latency31/baseline.py" "$O/linux-vm" --context linux-vm
fi
mkdir -p "$W"
mount -t tmpfs -o size=16G,mode=0755 tmpfs "$W"
mkdir -p "$R"
echo '59a7383e4b6cd47712e5dc05998ab34a58d511edc0b7ee016b267a15d4fb2b78  '"$I/build/attempt28-transfer/ramroot.cpio.zst" | sha256sum -c -
bsdtar -xpf "$I/build/attempt28-transfer/ramroot.cpio.zst" -C "$R"
[ -d "$O/shell-source" ] || cp -a "$R/usr/share/omarchy/shell" "$O/shell-source"
cp "$O/Hyprland-timeline31" "$R/usr/bin/Hyprland"
chmod a+rw /dev/dri/card0 /dev/dri/renderD128
chroot_up "$R"
mkdir -p "$R/run/user/1000" "$R/run/t31"
chmod 700 "$R/run/user/1000"
chown 1000:1000 "$R/run/user/1000"
cp "$I/virtualization/jobs/054-desktop-latency/out/frameprobe" "$R/run/t31/"
cp "$I/kernel/experiments/desktop30/collect.py" "$R/run/t31/collect30.py"
cp /mnt/job/workload.py "$R/run/t31/"
sha256sum "$R/usr/bin/Hyprland" | cut -d' ' -f1 > "$R/run/t31/hypr.sha256"
chroot "$R" pacman -Q hyprland mesa llvm-libs aquamarine quickshell foot > "$O/packages.txt"
T=$R/home/omarchy/.local/state/omarchy/toggles/hypr
printf '%s\n' 'hl.monitor({output="Virtual-1",mode="3456x2160@60",position="0x0",scale=1})' > "$T/zz-vm31.lua"
chown 1000:1000 "$T/zz-vm31.lua"
chroot "$R" env SEATD_VTBOUND=0 seatd -g wheel > "$O/seatd.log" 2>&1 &
SP=$!
sleep 1
cases=${ILINUX_VM_CASES:-'0 1 2'}
case "$cases" in '0 1 2'|4|5) ;; *) exit 2 ;; esac
for mode in $cases; do
  trace=1; drain=0
  render_threads=0; render_cpus=0
  profile=normal
  if [ "$mode" = 5 ]; then trace=0; profile=blur; fi
  [ "$mode" != 0 ] || trace=0
  [ "$mode" != 2 ] || drain=1
  if [ "$mode" = 4 ]; then render_threads=4; render_cpus=0-5; fi
  timeout -k 5 200 chroot "$R" setpriv --reuid=omarchy --regid=omarchy --init-groups env HOME=/home/omarchy USER=omarchy LOGNAME=omarchy XDG_RUNTIME_DIR=/run/user/1000 XDG_SESSION_TYPE=wayland LIBSEAT_BACKEND=seatd SEATD_SOCK=/run/seatd.sock AQ_DRM_DEVICES=/dev/dri/card0 LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS="$render_threads" OMARCHY_PATH=/usr/share/omarchy PATH=/usr/local/bin:/usr/bin:/usr/share/omarchy/bin ILINUX_LATENCY_TRACE="$trace" ILINUX_LATENCY_DRAIN="$drain" taskset -c "$render_cpus" dbus-run-session -- start-hyprland > "$O/hypr-$mode.log" 2>&1 &
  HP=$!
  chroot "$R" env ILINUX_VM_PROFILE="$profile" python3 -I /run/t31/workload.py > "$O/actions-$mode.jsonl" 2> "$O/actions-$mode.err"
  cp "$R/run/t31/shell.log" "$O/shell-$mode.log"
  # This is a disposable VM. End only the RAM-root uid1000 session.
  chroot "$R" pkill -TERM -u 1000 || true
  wait "$HP" || true
  HP=
  sleep 2
  if [ "$mode" != 0 ] && [ "$mode" != 5 ]; then
    cp "$R/run/user/1000/ilinux-timeline31.log" "$O/timeline-$mode.csv"
    python3 -I "$I/kernel/experiments/latency31/analyze.py" "$O/timeline-$mode.csv" "$O/actions-$mode.jsonl" > "$O/summary-$mode.json"
    rm "$R/run/user/1000/ilinux-timeline31.log"
  fi
  # Old IPC sockets are in this disposable runtime only.
  rm -rf "$R/run/user/1000/hypr" "$R/run/user/1000/wayland-"*
done
echo TIMELINE-BENCH-PASS
[ "$cases" = '0 1 2' ] || exit 0
# Separate logger-cost control: fixed scene with no Omarchy shell, not used
# as a representation of real menu latency. Keep both results distinct.
cp /mnt/job/observer.py "$R/run/t31/"
for mode in 0 1; do
  timeout -k 5 90 chroot "$R" setpriv --reuid=omarchy --regid=omarchy --init-groups env HOME=/home/omarchy USER=omarchy LOGNAME=omarchy XDG_RUNTIME_DIR=/run/user/1000 XDG_SESSION_TYPE=wayland LIBSEAT_BACKEND=seatd SEATD_SOCK=/run/seatd.sock AQ_DRM_DEVICES=/dev/dri/card0 LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=0 OMARCHY_PATH=/usr/share/omarchy PATH=/usr/local/bin:/usr/bin:/usr/share/omarchy/bin ILINUX_LATENCY_TRACE="$mode" ILINUX_LATENCY_DRAIN=0 taskset -c 0 dbus-run-session -- start-hyprland > "$O/observer-hypr-$mode.log" 2>&1 &
  HP=$!
  chroot "$R" python3 -I /run/t31/observer.py > "$O/observer-$mode.jsonl" 2> "$O/observer-$mode.err"
  chroot "$R" pkill -TERM -u 1000 || true
  wait "$HP" || true
  HP=
  sleep 1
  if [ "$mode" = 1 ]; then cp "$R/run/user/1000/ilinux-timeline31.log" "$O/observer-timeline.csv"; fi
  rm -rf "$R/run/user/1000/hypr" "$R/run/user/1000/wayland-"*
done
echo OBSERVER-CONTROL-PASS
