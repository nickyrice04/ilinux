#!/bin/sh
OUT=/mnt/job/out
sed -n '1,60p' /usr/share/omarchy/bin/omarchy-setup-direct-boot > $OUT/setup-direct-boot.txt
sed -n '1,30p' /usr/share/omarchy/bin/omarchy-provision-user > $OUT/provision-user-head.txt
export OMARCHY_PATH=/usr/share/omarchy PATH=/usr/share/omarchy/bin:/usr/local/sbin:/usr/local/bin:/usr/bin
bash -x /usr/share/omarchy/bin/omarchy-apply-system --install-user omarchy --first-install > $OUT/apply-system.log 2>&1
echo "apply system exit=$?"
grep -nE 'command not found|No such file|: line [0-9]+:' $OUT/apply-system.log | head -20
