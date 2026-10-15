#!/bin/bash
# host-run.sh [OWNER]: run job 042 (MTP ring transport kernel-side checks) in the workspace Arch VM
# through tools/vm-job.sh under the "vm" lock. WAIT=1 waits for a busy lock (30 s polls).
# Offline: no M5, no boot. Prepared by the MTP input session; run only with the user's go-ahead.
set -eu
cd "$(dirname "$0")/../../.."
OWNER=${1:-mtp-input}
until tools/lock.sh acquire vm "$OWNER" "job 042 mtp-input kernel checks" 90 2> /dev/null; do
    [ "${WAIT:-0}" = 1 ] || { tools/lock.sh status; exit 1; }
    [ -n "${told:-}" ] || { echo "waiting for the vm lock: $(tools/lock.sh status)"; told=1; }
    sleep 30
done
exec caffeinate -i tools/vm-job.sh virtualization/jobs/042-mtp-input "$OWNER"
