#!/bin/sh
# Job 009: install Omarchy 4 (edge, aarch64 platform) into the VM disk, driving
# the same phases the Omarchy ISO runs: packages -> omarchy apply system ->
# user finalize.  Test credentials for this local, NAT-only VM: user
# "omarchy" / password "omarchy" (documented in virtualization/README.md).
set -x
OUT=/mnt/job/out
mkdir -p /mnt/omarchy && mount -t virtiofs omarchy /mnt/omarchy || exit 1
rm -f /var/lib/pacman/db.lck   # stale lock from an interrupted run
# 1. pacman: Omarchy edge aarch64 templates + Omarchy's pinned signing key
cp /mnt/omarchy/default/pacman/aarch64/pacman-edge.conf /etc/pacman.conf
cp /mnt/omarchy/default/pacman/aarch64/mirrorlist-edge /etc/pacman.d/mirrorlist
pacman-key --init >/dev/null 2>&1; pacman-key --populate archlinuxarm >/dev/null 2>&1
pacman-key --recv-keys 40DFB630FF42BCFFB047046CF0134EE680CAC571 --keyserver hkps://keys.openpgp.org
pacman-key --lsign-key 40DFB630FF42BCFFB047046CF0134EE680CAC571
pacman -Syy --noconfirm omarchy-keyring 2>&1 | tail -3
# 2. full upgrade, then the aarch64 default set + runtime (+ VM GL/Vulkan fallbacks)
# --ask=4: auto-confirm conflict removals; --noconfirm: default provider choices
pacman -Syu --noconfirm --ask=4 2>&1 | tail -5
PKGS=$(OMARCHY_PATH=/mnt/omarchy bash /mnt/omarchy/bin/omarchy-pkg-defaults aarch64)
pacman -S --needed --noconfirm --ask=4 $PKGS omarchy omarchy-settings vulkan-swrast mesa-utils pipewire-jack > $OUT/pacman-install.log 2>&1
echo "pacman install exit=$?"; tail -15 $OUT/pacman-install.log
pacman -Q | wc -l
# 3. install user
id omarchy >/dev/null 2>&1 || useradd -m -G wheel -s /bin/bash omarchy
echo 'omarchy:omarchy' | chpasswd
echo '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers.d/10-wheel; chmod 440 /etc/sudoers.d/10-wheel
# 4. Omarchy system phase (config, hardware, login, post-install)
export OMARCHY_PATH=/usr/share/omarchy PATH=/usr/share/omarchy/bin:$PATH
omarchy apply system --install-user omarchy --first-install > $OUT/apply-system.log 2>&1
echo "apply system exit=$?"; tail -20 $OUT/apply-system.log
# 5. Omarchy user phase
loginctl enable-linger omarchy; sleep 3
U=$(id -u omarchy)
runuser -u omarchy -- env XDG_RUNTIME_DIR=/run/user/$U DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$U/bus \
  OMARCHY_PATH=/usr/share/omarchy PATH=/usr/share/omarchy/bin:/usr/bin \
  bash -lc 'omarchy finalize user --first-install' > $OUT/finalize-user.log 2>&1
echo "finalize user exit=$?"; tail -20 $OUT/finalize-user.log
loginctl disable-linger omarchy
systemctl list-unit-files --state=enabled > $OUT/enabled-units.txt
df -h / > $OUT/df.txt
