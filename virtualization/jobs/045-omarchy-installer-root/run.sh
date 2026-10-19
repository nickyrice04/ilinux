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
#  4. boot-test.sh: QEMU TCG, one vCPU, the exact Image the root is for (boot035 unless KERNEL says
#     otherwise), a DT simple-framebuffer for simpledrm and the M5's root compatible; Omarchy's
#     session, first run, menu, Chromium and the Electron apps; time to desktop and memory. With
#     LINK=1 also the USB link over dummy_hcd (link-test.sh), job 046's way.
# Host side: host-run.sh in this directory (vm lock, the work disk, the read-only Omarchy share).
# Optional out/job.env: REINSTALL=1, CONVERT=0 (stop after the install), TEST=0 (no boot test),
# FAST=1 (one quick zstd level), ZSTD_FINAL="-19 --long=27" (that level only), VARIANTS=0 (no
# delivery-size variant), TIMEOUT=seconds (the boot test's bound), RETEST=1 (stage 4 alone, on
# out/ramroot.cpio.zst as stage 3 packed it, digest-checked: stage 2 writes the build time into
# the root, so a rebuild always changes the image's digest; this keeps it through a change to the
# test alone). Read-only modes, each instead of the stages: INSPECT=1 (the installed runtime's
# installer and the edge repository's other runtime, unpacked into out/inspect/), QPROBE=1 (the
# largest -initrd QEMU accepts here), ELFCHECK=1 (every ELF in the RAM root against 16 KiB pages,
# the Chromium-based files, the agent wrappers, the package cache), LINKCHECK=1 (the facts the
# link build depends on: PAM, sudoers, sshd, mise, the work disk, KTREE).
# Build options (link.sh): LINK=1 (the USB link: gadget, sshd on its byte pipe for the user, the
# M1's proxy in the environment, the clock helper; stage 4 tests it and needs KTREE), CLAUDE=1
# (Claude Code through Omarchy's own mise wrapper, signed out), NOPASSWD=1 (Omarchy's permanent
# passwordless-sudo grant for the user; stage 4 tests it). Another kernel: KERNEL_NAME,
# KERNEL, IMAGE_SHA and KTREE (e.g. boot040: build/native-boot040/verified/Image).
# MODULES=<job 050's export/modules> (with LINK=1; attempt 26): boot042's keyboard modules under
# /usr/lib/modules, blacklisted from loading at boot, and ilinux-keyboard, which loads them over SSH;
# link.sh's stage_link also carries attempt 25's four fixes (see its comments).
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
# The kernel the root is for: by default boot035 (its Image is byte-identical to boot034's).
# out/job.env may name another package's: KERNEL_NAME, KERNEL (its verified Image), IMAGE_SHA, and
# for the link test's VM-only modules KTREE, the read-only tree that built it (job 039's way).
KERNEL_NAME=${KERNEL_NAME:-boot035}
KERNEL=${KERNEL:-/mnt/ilinux/build/native-boot035/verified/Image}
IMAGE_SHA=${IMAGE_SHA:-1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579}
KTREE=${KTREE:-}
# LINK=1: the USB link (link.sh: the gadget with the journal and SSH byte pipe, sshd on the pipe
# for the user, the M1's web proxy in the environment, the clock helper), tested in stage 4 over
# dummy_hcd. CLAUDE=1: Claude Code installed through Omarchy's own mise wrapper, signed out.
LINK=${LINK:-0}
CLAUDE=${CLAUDE:-0}
# NOPASSWD=1 (user-approved 2026-10-18 for the attempt-24 image): Omarchy's own permanent
# passwordless-sudo grant for the user, as omarchy-sudo-passwordless permanent writes it.
NOPASSWD=${NOPASSWD:-0}
# MODULES (attempt 26): the directory of job 050's module sets (its manifest.json and keyboard-root/).
MODULES=${MODULES:-}
[ -z "$MODULES" ] || [ "$LINK" = 1 ] || { echo "MODULES needs LINK=1 (the modules are loaded over the link)"; exit 1; }
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
if [ "${LINKCHECK:-0}" = 1 ]; then . "$J/linkcheck.sh"; stage_linkcheck; exit 0; fi
if [ "${RETEST:-0}" = 1 ]; then
    # the packed image, unchanged; the Electron app list still comes from its snapshot ($C)
    rm -rf "$OUT/test"
    log "retest: out/ramroot.cpio.zst as packed"
    (cd "$OUT" && sha256sum -c ramroot.cpio.zst.sha256)
    echo "$IMAGE_SHA  $KERNEL" | sha256sum -c -
    [ -d "$C" ] || { echo "no RAM root snapshot at $C"; exit 1; }
    cat "$C/usr/share/ilinux/build-info.txt"
    T=/run/ilinux-045
    mkdir -p "$T"
    mountpoint -q "$T" || mount -t tmpfs -o size=9G,mode=0755 tmpfs "$T"
    . "$J/boot-test.sh"
    stage_boot_test
    exit
fi
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
