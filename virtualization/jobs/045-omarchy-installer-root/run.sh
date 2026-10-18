#!/bin/bash
# Job 045: Omarchy, built by Omarchy's own installer from Omarchy's repositories, as a RAM root
# for the native M5 (roadmap Phase 3, row 4). Job 039 builds an Omarchy-style root from hand-
# picked packages; this job builds Omarchy itself and changes only what the M5 forces.
#  1. install.sh: Omarchy 4 from its edge aarch64 repositories into a btrfs subvolume, phase by
#     phase as the Omarchy ISO's orchestrator installs it, with the edge aarch64 ISO's runtime
#     (omarchy-dev) and the aarch64 platform (never aarch64-apple, whose omarchy-mac-boot
#     manages the Mac's boot chain): packages, omarchy-apply-system as an image build,
#     omarchy-provision-user (its mise agent wrappers and first-run hooks included), login.
#     Skipped while the work disk holds a finished install (installed.stamp), unless
#     REINSTALL=1.
#  2. ramroot.sh: a snapshot of the install, made bootable as the M5's RAM root; every change
#     is recorded in out/deviations.tsv with its reason.
#  3. pack.sh: newc cpio, zstd; sizes and upload times at the measured proxy rate.
#  4. boot-test.sh: QEMU TCG, one vCPU, the exact boot035 Image, a DT simple-framebuffer for
#     simpledrm and the M5's root compatible; Omarchy's session, first run, menu, Chromium and
#     the Electron apps; time to desktop and memory.
# Host side: host-run.sh in this directory (vm lock, the work disk, the read-only Omarchy share).
# Optional out/job.env: REINSTALL=1, CONVERT=0 (stop after the install), TEST=0 (no boot test),
# FAST=1 (one quick zstd level), ZSTD_FINAL="-19 --long=27" (that level only), VARIANTS=0 (no
# delivery-size variant), TIMEOUT=seconds (the boot test's bound). Read-only modes, each instead
# of the stages: INSPECT=1 (the installed runtime's installer and the edge repository's other
# runtime, unpacked into out/inspect/), QPROBE=1 (the largest -initrd QEMU accepts here),
# ELFCHECK=1 (every ELF in the RAM root against 16 KiB pages, the Chromium-based files, the
# agent wrappers, the package cache).
set -euo pipefail
J=/mnt/job
OUT=$J/out
IO=$OUT/install
[ -f "$OUT/job.env" ] && . "$OUT/job.env"
REINSTALL=${REINSTALL:-0}
CONVERT=${CONVERT:-1}
TEST=${TEST:-1}
FAST=${FAST:-0}
VARIANTS=${VARIANTS:-1}
# The kernel the root is for: boot035 (its Image is byte-identical to boot034's), unchanged.
KERNEL=/mnt/ilinux/build/native-boot035/verified/Image
IMAGE_SHA=1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579
W=/var/tmp/ilinux-045          # the work disk (/dev/vdb, btrfs): cache, keyrings, roots
R=$W/@root                     # the installed Omarchy (a subvolume, never changed after stage 1)
C=$W/@ramroot                  # its snapshot, made into the RAM root
. "$J/lib.sh"

# ---- the work disk -------------------------------------------------------------------------
# host-run.sh attaches a 10 GiB sparse image as the second disk. Format it only when it is
# blank and that size; otherwise it must be this job's (label ilinux045).
share ilinux
share omarchy
mkdir -p "$OUT" "$W"
if ! mountpoint -q "$W"; then
    dev=/dev/vdb
    size=$(blockdev --getsize64 "$dev")
    label=$(blkid -s LABEL -o value "$dev" || true)
    if [ -z "$(blkid -o value "$dev" || true)" ] && [ "$size" -ge $((9 * 1024**3)) ] && [ "$size" -le $((11 * 1024**3)) ]; then
        mkfs.btrfs -q -L ilinux045 "$dev"
        label=ilinux045
    fi
    [ "$label" = ilinux045 ] || { echo "$dev is not job 045's work disk (label '$label', $size bytes)"; exit 1; }
    mount -o compress=zstd:1,noatime "$dev" "$W"
fi
mountpoint -q "$W" || { echo "work disk not mounted"; exit 1; }
trap 'chroot_down "$R" 2>/dev/null; chroot_down "$C" 2>/dev/null; [ -n "${QPID:-}" ] && kill "$QPID" 2>/dev/null; true' EXIT
mkdir -p "$W/cache"
if [ "${INSPECT:-0}" = 1 ]; then . "$J/inspect.sh"; stage_inspect; exit 0; fi
if [ "${QPROBE:-0}" = 1 ]; then . "$J/qprobe.sh"; stage_qprobe; exit 0; fi
if [ "${ELFCHECK:-0}" = 1 ]; then . "$J/elfcheck.sh"; stage_elfcheck; exit 0; fi
rm -rf "$OUT/build" "$OUT/test"
mkdir -p "$OUT/build"
log "inputs"
echo "$IMAGE_SHA  $KERNEL" | sha256sum -c -
OMARCHY_SRC=$(git -c safe.directory='*' -C /mnt/omarchy rev-parse HEAD)
ILINUX_REV=$(git -c safe.directory='*' -C /mnt/ilinux rev-parse --short HEAD)
{ uname -srm; nproc; free -m | sed -n 2p; df -h "$W" | tail -1; pacman -V | sed -n 2p
  echo "upstream omarchy checkout (bootstrap pacman templates only) $OMARCHY_SRC"
  echo "ilinux $ILINUX_REV"
  printf 'build VM device-tree compatible: '; { tr '\0' ' ' < /proc/device-tree/compatible; } 2>/dev/null || echo none
  echo "build VM systemd-detect-virt: $(systemd-detect-virt 2>/dev/null || true)"
} > "$OUT/build/vm-environment.txt"
cat "$OUT/build/vm-environment.txt"

# ---- 1. install ----------------------------------------------------------------------------
if [ "$REINSTALL" = 1 ] || [ ! -f "$W/installed.stamp" ] || [ ! -d "$R" ]; then
    if [ -d "$R" ]; then
        chroot_down "$R"
        # nested subvolumes first (snapper's .snapshots), deepest first
        btrfs subvolume list -o "$R" | awk '{print $NF}' | sort -r |
            while read -r sv; do btrfs subvolume delete "$W/$sv" > /dev/null; done
        btrfs subvolume delete "$R" > /dev/null
    fi
    rm -f "$W/installed.stamp"
    btrfs subvolume create "$R" > /dev/null
    . "$J/install.sh"
    stage_install
else
    log "install: reusing the installed root from $(cat "$W/installed.stamp") (REINSTALL=1 rebuilds it)"
fi
[ "$CONVERT" = 1 ] || exit 0

# ---- 2. RAM root ------------------------------------------------------------------------------
. "$J/ramroot.sh"
stage_ramroot
cat "$W/deviations-install.tsv" "$W/deviations-ramroot.tsv" > "$OUT/deviations.tsv"

# ---- 3. pack -------------------------------------------------------------------------------
. "$J/pack.sh"
stage_pack
[ "$TEST" = 1 ] || exit 0

# ---- 4. boot test --------------------------------------------------------------------------
. "$J/boot-test.sh"
stage_boot_test
