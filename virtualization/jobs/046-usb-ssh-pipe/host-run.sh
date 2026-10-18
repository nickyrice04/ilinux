#!/bin/bash
# host-run.sh [OWNER]: run job 046 in the workspace Arch VM through tools/vm-job.sh under the
# "vm" lock. WAIT=1 waits for a busy lock (POLL seconds between tries, default 30) instead of
# failing. Then boot the result on the Mac: virtualization/jobs/046-usb-ssh-pipe/run-vz.sh.
set -eu
cd "$(dirname "$0")/../../.."
OWNER=${1:-usb-pipe-046}
until tools/lock.sh acquire vm "$OWNER" "job 046 USB SSH byte pipe test build" 60 2> /dev/null; do
    [ "${WAIT:-0}" = 1 ] || { tools/lock.sh status; exit 1; }
    [ -n "${told:-}" ] || { echo "waiting for the vm lock: $(tools/lock.sh status)"; told=1; }
    sleep "${POLL:-30}"
done
exec caffeinate -i tools/vm-job.sh virtualization/jobs/046-usb-ssh-pipe "$OWNER"
