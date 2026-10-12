#!/bin/sh
OUT=/mnt/job/out
cp /var/log/omarchy-install.log $OUT/ 2>/dev/null
grep -nE 'Failed|exit code|Starting|Completed' /var/log/omarchy-install.log | tail -25
