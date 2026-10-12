#!/bin/bash
# Launch the Omarchy VM disk under the workspace-built QEMU with GPU
# acceleration: HVF CPU virtualization + in-hypervisor GICv3, virtio-gpu-gl
# (VirGL -> native macOS OpenGL 4.1 core) in a Cocoa window.
#
# Settings follow try-omarchy's tuned launcher (MIT; see third_party/try-omarchy):
# kernel-irqchip=on cuts idle CPU, balloon free-page reporting returns freed
# guest memory to macOS, discard=unmap returns trimmed blocks to the sparse
# disk image.  Host integration channel (virtio-serial):
#   org.ilinux.host  <- tools/bin/ilinux-host-agent (battery, clock after the
#                       Mac sleeps, time zone), started here and tied to QEMU
# HMP monitor: virtualization/run/monitor.sock (e.g. "screendump shot.ppm").
#
# Display: the guest resolution follows the window's Retina backing pixels
# (Hyprland scale 2).  --fullscreen gives Omarchy its own macOS Space at the
# panel's native 3456x2160 safe area, menu bar and Dock hidden ("immersive").
# --full-grab sends system chords (Cmd-Space, Cmd-Tab...) to Hyprland while the
# window is focused; macOS asks once to allow Accessibility for QEMU (a
# rebuilt, ad-hoc-signed binary needs the grant again).
#
# A hidden window no longer throttles a busy guest: app-nap=auto (see below).
# CPU: --hetero mirrors the M5 Max (1 Super + 2 M clusters of 6): 18 vCPUs in 3
# clusters; the last cluster runs at macOS background QoS (host M cores, low
# clocks) and is described to Linux as capacity 220/1024, so omarchy-qos fences
# background.slice onto it (workspace patch qemu-hvf-heterogeneous-vcpus).
#
#   virtualization/qemu/run-omarchy-gpu.sh [--fullscreen] [--full-grab] [--hetero]
#                                         [--headless] [--console-socket] [--job DIR]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QEMU="$ROOT/virtualization/qemu/runtime/bin/qemu-system-aarch64"
IMG="$ROOT/virtualization/images/alarm"
DISK="${DISK:-$IMG/root-btrfs.img}"
KERNEL="${KERNEL:-$IMG/Image-7.1.6-vzrun2-16k}"
CPUS="${CPUS:-12}"
MEM_MIB="${MEM_MIB:-16384}"
XRES="${XRES:-1728}"; YRES="${YRES:-1117}"   # half of the 3456x2234 panel; Hyprland scales
RUNDIR="$ROOT/virtualization/run"; mkdir -p "$RUNDIR"   # short path: AF_UNIX limit is 104 bytes
# The guest follows the Mac's time zone (ilinux-timezone-sync reads ilinux.tz=).
TZNAME=$(readlink /etc/localtime 2>/dev/null | sed -n 's|.*/zoneinfo/||p')
# One VM per run directory: a second launch would unlink the running VM's
# console/monitor sockets (QEMU's disk lock only stops it after that).
if [[ -f $RUNDIR/qemu.pid ]] && kill -0 "$(cat "$RUNDIR/qemu.pid")" 2>/dev/null; then
  echo "a VM is already running (pid $(cat "$RUNDIR/qemu.pid")); stop it first" >&2; exit 1
fi
rm -f "$RUNDIR"/{console,monitor,battery,host}.sock
fullscreen=off; fullgrab=off; headless=0
# App Nap: "auto" lets macOS nap a hidden, idle VM but not a busy one (workspace
# patch qemu-cocoa-app-nap); APP_NAP=on|off overrides.
appnap="${APP_NAP:-auto}"
smp="$CPUS,sockets=1,cores=$CPUS,threads=1"; machine="virt,gic-version=3"
job=()
CONSOLE="stdio,id=hvc0,signal=off"
while (($#)); do
  case "$1" in
    --fullscreen) fullscreen=on; shift ;;
    --full-grab) fullgrab=on; shift ;;
    --hetero) smp="18,sockets=1,clusters=3,cores=6,threads=1"
              machine="virt,gic-version=3,bg-vcpus=6"; shift ;;
    --headless) headless=1; shift ;;
    --console-socket) CONSOLE="socket,id=hvc0,path=$RUNDIR/console.sock,server=on,wait=off"; shift ;;
    --job) job=(-fsdev "local,id=job,path=$2,security_model=none"
                -device "virtio-9p-pci,fsdev=job,mount_tag=job"); shift 2 ;;
    *) echo "usage: $0 [--fullscreen] [--full-grab] [--hetero] [--headless] [--console-socket] [--job DIR]" >&2; exit 2 ;;
  esac
done
if ((headless)); then
  display=(-display none)
else
  display=(-device "virtio-gpu-gl-pci,max_outputs=1,xres=$XRES,yres=$YRES"
           -display "cocoa,gl=on,show-cursor=on,zoom-to-fit=on,full-screen=$fullscreen,immersive=$fullscreen,full-grab=$fullgrab,swap-opt-cmd=off,app-nap=$appnap")
fi

# Host agent: (re)build when the source is newer; exits when QEMU (this PID,
# after exec) is gone.
AGENT="$ROOT/tools/bin/ilinux-host-agent"; AGENT_SRC="$ROOT/tools/ilinux-host-agent.swift"
if [[ ! -x $AGENT || $AGENT_SRC -nt $AGENT ]]; then
  mkdir -p "$ROOT/tools/bin" && swiftc -O "$AGENT_SRC" -o "$AGENT"
fi
"$AGENT" --unix "$RUNDIR/host.sock" --parent $$ > "$RUNDIR/host-agent.log" 2>&1 &

exec "$QEMU" -name Omarchy \
  -machine "$machine" -accel hvf,kernel-irqchip=on -cpu host,pmu=off \
  -smp "$smp" -m "${MEM_MIB}M" \
  -kernel "$KERNEL" -append "${APPEND:-root=/dev/vda rootflags=subvol=@ rw rootwait console=hvc0 quiet loglevel=3}${TZNAME:+ ilinux.tz=$TZNAME}" \
  -drive "if=none,id=root,file=$DISK,format=raw,cache=writeback,discard=unmap" \
  -device virtio-blk-pci,drive=root \
  "${display[@]}" \
  -device virtio-keyboard-pci -device virtio-tablet-pci \
  -netdev user,id=net0 -device virtio-net-pci,netdev=net0 \
  -object rng-random,id=rng,filename=/dev/urandom -device virtio-rng-pci,rng=rng \
  -device virtio-balloon-pci,free-page-reporting=on \
  -audiodev coreaudio,id=snd -device intel-hda -device hda-micro,audiodev=snd \
  -device virtio-serial-pci,id=vser \
  -chardev "$CONSOLE" -device virtconsole,bus=vser.0,nr=0,chardev=hvc0 \
  -chardev "socket,id=host,path=$RUNDIR/host.sock,server=on,wait=off" \
  -device virtserialport,bus=vser.0,nr=1,chardev=host,name=org.ilinux.host \
  ${job[@]+"${job[@]}"} \
  -monitor "unix:$RUNDIR/monitor.sock,server=on,wait=off" \
  -pidfile "$RUNDIR/qemu.pid" \
  -serial none
