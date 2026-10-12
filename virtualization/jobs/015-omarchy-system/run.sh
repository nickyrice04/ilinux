#!/bin/sh
OUT=/mnt/job/out
ls /usr/share/omarchy/install/config/ /usr/share/omarchy/install/login/ /usr/share/omarchy/install/post-install/ > $OUT/phase-scripts.txt
# ISO "boot set" tools the system phase expects (snapshots etc.)
pacman -S --needed --noconfirm --ask=4 snapper limine limine-snapper-sync limine-mkinitcpio-hook efibootmgr plymouth > $OUT/pacman-bootset.log 2>&1
echo "bootset install exit=$?"; tail -3 $OUT/pacman-bootset.log
export OMARCHY_PATH=/usr/share/omarchy PATH=/usr/share/omarchy/bin:/usr/local/sbin:/usr/local/bin:/usr/bin
bash /usr/share/omarchy/bin/omarchy-apply-system --install-user omarchy --first-install > $OUT/apply-system.log 2>&1
echo "apply system exit=$?"; grep -E 'Failed|Error|error:' $OUT/apply-system.log | head -15
systemctl is-enabled sddm 2>&1; snapper list-configs 2>&1 | head -5
