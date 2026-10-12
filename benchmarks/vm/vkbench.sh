#!/bin/bash
# vkbench.sh FRAMES PRESENT_MODE [VAR=value...]: run vkcube on Venus/Wayland in the
# guest session; report frames/s over the whole run (incl. ~0.3 s startup) and the
# CPU use of vkcube sampled over 2 s mid-run. PRESENT_MODE: 0 immediate, 1 mailbox, 2 fifo.
N=${1:-1200}; PM=${2:-2}; shift 2
export XDG_RUNTIME_DIR=/run/user/1002 WAYLAND_DISPLAY=wayland-1 VK_DRIVER_FILES=/usr/share/vulkan/icd.d/virtio_icd.json
END=$(mktemp); t0=$(date +%s%N)
( env "$@" vkcube --wsi wayland --c "$N" --present_mode "$PM" > /tmp/vkbench.log 2>&1; echo "$? $(date +%s%N)" > "$END" ) &
sleep 1; P=$(pgrep -n -x vkcube)
read -r u1 s1 < <(awk '{print $14, $15}' /proc/$P/stat 2>/dev/null); t1=$(date +%s%N)
sleep 2
read -r u2 s2 < <(awk '{print $14, $15}' /proc/$P/stat 2>/dev/null); t2=$(date +%s%N)
wait
read -r rc t3 < "$END"; rm -f "$END"
awk -v n=$N -v t0=$t0 -v t1=$t1 -v t2=$t2 -v t3=$t3 -v u1=${u1:-0} -v s1=${s1:-0} -v u2=${u2:-0} -v s2=${s2:-0} \
    -v hz=$(getconf CLK_TCK) -v pm=$PM -v rc=$rc 'BEGIN {
  win = (t2 - t1) / 1e9; wall = (t3 - t0) / 1e9
  printf "present_mode=%s frames=%d wall=%.2fs fps=%.1f cpu_user=%.0f%% cpu_sys=%.0f%% rc=%s%s\n", pm, n, wall, n / wall,
         100 * (u2 - u1) / hz / win, 100 * (s2 - s1) / hz / win, rc, (wall < 3.2 ? " (cpu sample may postdate exit)" : "") }'
