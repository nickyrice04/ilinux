#!/bin/bash
# Build a disposable Arch Linux ARM VM disk for vzrun, entirely inside the
# workspace.  Docker Desktop is used only as a Linux userland for gpg, bsdtar
# and mkfs.ext4; nothing is installed on the macOS host.
#
#   virtualization/scripts/build-alarm-image.sh [size, default 32g]
#
# Inputs:  virtualization/images/downloads/ArchLinuxARM-aarch64-latest.tar.gz{,.sig}
# Outputs: virtualization/images/alarm/{root.img (sparse), Image, cmdline}
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DL="$ROOT/virtualization/images/downloads"
OUT="$ROOT/virtualization/images/alarm"
SIZE="${1:-32g}"
# Arch Linux ARM Build System key (also pinned by Omarchy's arm64 work).
ALARM_KEY=68B3537F39A313B3E574D06777193F152BDBE6A6

mkdir -p "$OUT"
rm -f "$OUT/root.img"
mkfile -n "$SIZE" "$OUT/root.img"          # sparse on APFS

docker run --rm --platform linux/arm64 \
  -v "$DL:/dl:ro" -v "$OUT:/out" -v "$ROOT/virtualization/guest:/guest:ro" \
  alpine:3.22 sh -euc "
    apk add --no-cache gnupg gnupg-dirmngr e2fsprogs libarchive-tools >/dev/null
    export GNUPGHOME=\$(mktemp -d)
    gpg --batch --quiet --keyserver hkps://keyserver.ubuntu.com --recv-keys $ALARM_KEY
    gpg --batch --status-fd 1 --verify /dl/ArchLinuxARM-aarch64-latest.tar.gz.sig \
        /dl/ArchLinuxARM-aarch64-latest.tar.gz | grep VALIDSIG | grep -q '$ALARM_KEY' \
      || { echo 'SIGNATURE CHECK FAILED' >&2; exit 1; }
    echo 'signature OK ($ALARM_KEY)'
    mkdir /rootfs
    bsdtar -xpf /dl/ArchLinuxARM-aarch64-latest.tar.gz -C /rootfs
    sh /guest/customize.sh /rootfs
    cp /rootfs/boot/Image /out/Image
    ls /rootfs/usr/lib/modules > /out/kernel-version
    mkfs.ext4 -q -F -E nodiscard -L alarm-root -d /rootfs /out/root.img
    echo 'filesystem built'
  "
echo "console=hvc0 root=/dev/vda rw rootwait" > "$OUT/cmdline"
ls -lhs "$OUT"
