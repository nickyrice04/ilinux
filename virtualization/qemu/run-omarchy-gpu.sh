#!/bin/bash
# Launch the Omarchy VM disk under the workspace-built QEMU with GPU
# acceleration: HVF CPU virtualization + in-hypervisor GICv3, virtio-gpu-gl
# (VirGL -> native macOS OpenGL 4.1 core) in a Cocoa window.
#
# Settings follow try-omarchy's tuned launcher (MIT; see third_party/try-omarchy):
# kernel-irqchip=on cuts idle CPU, balloon free-page reporting returns freed
# guest memory to macOS, discard=unmap returns trimmed blocks to the sparse
# disk image.  Host integration channels (virtio-serial):
#   org.ilinux.battery  <- tools/bin/mac-battery-feed (Mac battery -> guest BAT)
# HMP monitor: virtualization/run/monitor.sock (e.g. "screendump shot.ppm").
#
# Display: the guest resolution follows the window's Retina backing pixels
# (Hyprland scale 2).  --fullscreen gives Omarchy its own macOS Space at the
# panel's native 3456x2160 safe area, menu bar and Dock hidden ("immersive").
# --full-grab sends system chords (Cmd-Space, Cmd-Tab...) to Hyprland while the
# window is focused; macOS asks once to allow Accessibility for QEMU (a
# rebuilt, ad-hoc-signed binary needs the grant again).
#
#   virtualization/qemu/run-omarchy-gpu.sh [--fullscreen] [--full-grab] [--headless]
#                                         [--console-socket] [--job DIR]
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
# One VM per run directory: a second launch would unlink the running VM's
# console/monitor sockets (QEMU's disk lock only stops it after that).
if [[ -f $RUNDIR/qemu.pid ]] && kill -0 "$(cat "$RUNDIR/qemu.pid")" 2>/dev/null; then
  echo "a VM is already running (pid $(cat "$RUNDIR/qemu.pid")); stop it first" >&2; exit 1
fi
rm -f "$RUNDIR"/{console,monitor,battery}.sock
fullscreen=off; fullgrab=off; headless=0
job=()
CONSOLE="stdio,id=hvc0,signal=off"
while (($#)); do
  case "$1" in
    --fullscreen) fullscreen=on; shift ;;
    --full-grab) fullgrab=on; shift ;;
    --headless) headless=1; shift ;;
    --console-socket) CONSOLE="socket,id=hvc0,path=$RUNDIR/console.sock,server=on,wait=off"; shift ;;
    --job) job=(-fsdev "local,id=job,path=$2,security_model=none"
                -device "virtio-9p-pci,fsdev=job,mount_tag=job"); shift 2 ;;
    *) echo "usage: $0 [--fullscreen] [--full-grab] [--headless] [--console-socket] [--job DIR]" >&2; exit 2 ;;
  esac
done
if ((headless)); then
  display=(-display none)
else
  display=(-device "virtio-gpu-gl-pci,max_outputs=1,xres=$XRES,yres=$YRES"
           -display "cocoa,gl=on,show-cursor=on,zoom-to-fit=on,full-screen=$fullscreen,immersive=$fullscreen,full-grab=$fullgrab,swap-opt-cmd=off")
fi

exec "$QEMU" -name Omarchy \
  -machine virt,gic-version=3 -accel hvf,kernel-irqchip=on -cpu host,pmu=off \
  -smp "$CPUS,sockets=1,cores=$CPUS,threads=1" -m "${MEM_MIB}M" \
  -kernel "$KERNEL" -append "${APPEND:-root=/dev/vda rootflags=subvol=@ rw rootwait console=hvc0 quiet loglevel=3}" \
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
  -chardev "socket,id=battery,path=$RUNDIR/battery.sock,server=on,wait=off" \
  -device virtserialport,bus=vser.0,nr=1,chardev=battery,name=org.ilinux.battery \
  ${job[@]+"${job[@]}"} \
  -monitor "unix:$RUNDIR/monitor.sock,server=on,wait=off" \
  -pidfile "$RUNDIR/qemu.pid" \
  -serial none
