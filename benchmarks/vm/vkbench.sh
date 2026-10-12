#!/bin/bash
# vkbench.sh FRAMES PRESENT_MODE [extra env...]: run vkcube on Venus/Wayland, report fps and CPU
N=${1:-1200}; PM=${2:-2}; shift 2
export XDG_RUNTIME_DIR=/run/user/1002 WAYLAND_DISPLAY=wayland-1 VK_DRIVER_FILES=/usr/share/vulkan/icd.d/virtio_icd.json
t0=$(date +%s%N)
env "$@" vkcube --wsi wayland --c "$N" --present_mode "$PM" > /tmp/vkbench.log 2>&1 &
P=$!
sleep 3
read -r u1 s1 < <(awk '{print $14, $15}' /proc/$P/stat 2>/dev/null)
t1=$(date +%s%N)
sleep 3
read -r u2 s2 < <(awk '{print $14, $15}' /proc/$P/stat 2>/dev/null)
t2=$(date +%s%N)
wait $P; rc=$?
t3=$(date +%s%N)
hz=$(getconf CLK_TCK)
awk -v n=$N -v t0=$t0 -v t1=$t1 -v t2=$t2 -v t3=$t3 -v u1=$u1 -v s1=$s1 -v u2=$u2 -v s2=$s2 -v hz=$hz -v pm=$PM -v rc=$rc 'BEGIN {
  win = (t2 - t1) / 1e9
  printf "present_mode=%s frames=%d wall=%.2fs fps=%.1f cpu_user=%.0f%% cpu_sys=%.0f%% rc=%d\n", pm, n, (t3-t0)/1e9, n/((t3-t0)/1e9), 100*(u2-u1)/hz/win, 100*(s2-s1)/hz/win, rc }'
