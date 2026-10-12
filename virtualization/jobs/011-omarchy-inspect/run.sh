#!/bin/sh
OUT=/mnt/job/out
pacman -Ql omarchy | grep -E '/bin/|/usr/share/omarchy/[^/]+/$' | head -40 > $OUT/omarchy-files.txt
pacman -Qi omarchy omarchy-settings | grep -E '^(Name|Version|Install Date)' > $OUT/omarchy-version.txt
ls /usr/share/omarchy/bin | grep -E 'apply|finalize|provision|setup|install' > $OUT/omarchy-setup-cmds.txt
command -v omarchy > $OUT/which.txt 2>&1
/usr/bin/omarchy commands --all > $OUT/commands.txt 2>&1 || ls -la /usr/bin/omarchy* >> $OUT/which.txt 2>&1
ls /usr/share/omarchy/install /usr/share/omarchy/install/* -d > $OUT/install-tree.txt 2>&1
