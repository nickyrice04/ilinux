#!/bin/sh
OUT=/mnt/job/out
findmnt / /home /var/log > $OUT/mounts.txt
export OMARCHY_PATH=/usr/share/omarchy PATH=/usr/share/omarchy/bin:/usr/local/sbin:/usr/local/bin:/usr/bin
bash /usr/share/omarchy/bin/omarchy-apply-system --install-user omarchy --first-install > $OUT/apply-system.log 2>&1
echo "apply system exit=$?"; grep -E 'Failed|Error|error' $OUT/apply-system.log | head -10
loginctl enable-linger omarchy; sleep 3; U=$(id -u omarchy)
runuser -u omarchy -- env XDG_RUNTIME_DIR=/run/user/$U DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$U/bus \
  OMARCHY_PATH=/usr/share/omarchy PATH=/usr/share/omarchy/bin:/usr/bin \
  bash -lc 'omarchy provision user' > $OUT/provision-user.log 2>&1
echo "provision user exit=$?"; tail -8 $OUT/provision-user.log
loginctl disable-linger omarchy
systemctl is-enabled sddm 2>&1; ls /etc/sddm.conf.d 2>&1; cat /etc/sddm.conf.d/* 2>/dev/null | head -20
snapper list-configs 2>&1 | head
