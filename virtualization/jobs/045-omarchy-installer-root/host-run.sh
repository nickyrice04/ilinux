#!/bin/bash
# host-run.sh [OWNER]: run job 045 in the workspace Arch VM through tools/vm-job.sh under the
# "vm" lock, with a read-only share of the Omarchy checkout (bootstrap pacman templates) and
# the job's own work disk: a sparse 10 GiB raw image, created on first use (the user approved
# about 1.8 GB of downloads and a VM disk of about 10 GB for this job).
set -eu
cd "$(dirname "$0")/../../.."
A="$PWD/../apple-silicon-linux-research"
OWNER=${1:-omarchy-045}
DISK="$A/virtualization/images/job045/work.img"
if [ ! -f "$DISK" ]; then
    mkdir -p "$(dirname "$DISK")"
    /usr/sbin/mkfile -n 10g "$DISK"
fi
tools/lock.sh acquire vm "$OWNER" "job 045 Omarchy installer RAM root" 240 || exit 1
# 48 GiB (vm-job.sh's default is 24): the boot test's guest needs 32 GiB, since the root
# unpacks into a tmpfs that may use half of the guest's memory.
export VZRUN_EXTRA="--share $A/research/omarchy/upstream-omarchy:omarchy:ro --disk $DISK --mem 48"
exec caffeinate -i tools/vm-job.sh virtualization/jobs/045-omarchy-installer-root "$OWNER"
