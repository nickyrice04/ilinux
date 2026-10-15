#!/bin/bash
# host-run.sh [OWNER]: run job 041 in the workspace Arch VM through tools/vm-job.sh under the
# "vm" lock. WAIT=1 waits for a busy lock (30 s polls) instead of failing.
# The boots then run on the Mac: kernel/experiments/usb-gadget/selftest/run-vz.sh.
set -eu
cd "$(dirname "$0")/../../.."
OWNER=${1:-boot036}
until tools/lock.sh acquire vm "$OWNER" "job 041 boot036 USB control channel" 90 2> /dev/null; do
    [ "${WAIT:-0}" = 1 ] || { tools/lock.sh status; exit 1; }
    [ -n "${told:-}" ] || { echo "waiting for the vm lock: $(tools/lock.sh status)"; told=1; }
    sleep 30
done
exec caffeinate -i tools/vm-job.sh virtualization/jobs/041-usb-gadget "$OWNER"
