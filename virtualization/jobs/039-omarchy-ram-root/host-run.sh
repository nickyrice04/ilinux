#!/bin/bash
# host-run.sh [OWNER]: run job 039 in the workspace Arch VM through tools/vm-job.sh under the
# "vm" lock, with a read-only share of the pinned Omarchy clone. NESTED=1 also enables nested
# virtualization, for VM_ACCEL=kvm in out/job.env (the default boot test uses TCG).
set -eu
cd "$(dirname "$0")/../../.."
A="$PWD/../apple-silicon-linux-research"
OWNER=${1:-ramroot-039}
tools/lock.sh acquire vm "$OWNER" "job 039 omarchy RAM root" 120 || exit 1
export VZRUN_EXTRA="--share $A/research/omarchy/upstream-omarchy:omarchy:ro"
[ "${NESTED:-0}" = 1 ] && VZRUN_EXTRA="--nested $VZRUN_EXTRA"
exec caffeinate -i tools/vm-job.sh virtualization/jobs/039-omarchy-ram-root "$OWNER"
