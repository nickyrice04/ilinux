#!/bin/bash
# tools/vm-restart.sh [launcher args]: power the workspace VM off from inside
# (Omarchy maps the ACPI power key to its menu), install the virglrenderer
# (and with INSTALL_QEMU=1 the QEMU) build, relaunch, and wait for Hyprland.
# A stalled shutdown is diagnosed (virtio-gpu queue state + a QEMU thread
# sample in virtualization/run/) and, unless FORCE_QUIT=0, ended with "quit".
# Env: NO_INSTALL=1, INSTALL_QEMU=1, POWEROFF_WAIT=seconds, FORCE_QUIT=0|1.
# Gracefully stop the workspace VM, install the freshly built virglrenderer,
# relaunch with Venus and wait for the console socket. Extra args go to the
# launcher. Env passes through (e.g. VIRGL_IOSURFACE_MIRROR_STATS=1).
set -u
cd "$(dirname "$0")/.." || exit 1
# Agents share this VM (coordination.md): never restart it while another
# agent holds the "vm" lock. Set AGENT_ID to your lock owner name.
holder=$(tools/lock.sh holder vm)
if [ -n "$holder" ] && [ "$holder" != "${AGENT_ID:-}" ]; then
  echo "vm lock held by '$holder' (tools/lock.sh status); not restarting" >&2
  exit 1
fi
C=virtualization/run/console.sock; M=virtualization/run/monitor.sock
if pgrep -f qemu-system-aarch64 >/dev/null; then
  # Omarchy maps the ACPI power key to its menu: power off from inside
  /usr/bin/python3 -I tools/vmconsole.py $C 'systemctl poweroff' 5 > /dev/null 2>&1
  for i in $(seq 1 ${POWEROFF_WAIT:-60}); do pgrep -f qemu-system-aarch64 >/dev/null || break; sleep 1; done
  if pgrep -f qemu-system-aarch64 >/dev/null; then
    echo "VM did not power off in ${i}s; virtio-gpu ctrl queue:"
    /usr/bin/python3 -I "$(dirname "$0")/qemumon.py" $M "info virtio-queue-status /machine/peripheral-anon/device[1]/virtio-backend 0" | grep -E "inuse|used_idx|last_avail"
    QP=$(pgrep -f qemu-system-aarch64 | head -1)
    [ -n "$QP" ] && sample "$QP" 2 -file "virtualization/run/qemu-stall-$(date +%H%M%S).txt" > /dev/null 2>&1 && echo "sampled QEMU threads"
    [ "${FORCE_QUIT:-1}" = 1 ] || exit 1
    /usr/bin/python3 -I "$(dirname "$0")/qemumon.py" $M quit > /dev/null
    for i in $(seq 1 20); do pgrep -f qemu-system-aarch64 >/dev/null || break; sleep 1; done
    echo "forced quit"
  else
    echo "VM powered off after ${i}s"
  fi
fi
pkill -f ilinux-host-agent 2>/dev/null
if [ "${NO_INSTALL:-0}" != 1 ]; then
  PATH="$PWD/tools/venv/bin:$PATH" MACOSX_DEPLOYMENT_TARGET=15.0 ninja -C virtualization/qemu/src/virglrenderer/build install > /dev/null 2>&1 || { echo "install failed"; exit 1; }
  if [ "${INSTALL_QEMU:-0}" = 1 ]; then
    PATH="$PWD/tools/venv/bin:$PATH" MACOSX_DEPLOYMENT_TARGET=15.0 ninja -C virtualization/qemu/src/qemu/build install > /dev/null 2>&1 || { echo "qemu install failed"; exit 1; }
    echo "installed qemu"
  fi
fi
(virtualization/qemu/run-omarchy-gpu.sh --console-socket --hetero --venus "$@" > virtualization/run/qemu-omarchy.log 2>&1 &)
for i in $(seq 1 60); do [ -S $C ] && break; sleep 1; done
# wait for the guest to answer on the console (boot + autologin)
for i in $(seq 1 120); do
  out=$(/usr/bin/python3 -I tools/vmconsole.py $C 'pgrep -x Hyprland >/dev/null && echo HYPR_UP' 10 2>/dev/null)
  case "$out" in *HYPR_UP*) echo "guest up, Hyprland running (${i} polls)"; exit 0;; esac
  sleep 2
done
echo "guest did not come up"; exit 1
