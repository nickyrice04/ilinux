#!/bin/bash
# host-run.sh [OWNER]: run job 050 (the boot042 kernel) in the workspace Arch VM through tools/vm-job.sh
# under the "vm" lock. WAIT=1 waits for a busy lock (30 s polls) instead of failing.
# Offline: no M5, no boot. The boots run on the Mac afterwards, with no lock: run-vz.sh liveness, storage
# and script, in this directory.
set -eu
cd "$(dirname "$0")/../../.."
OWNER=${1:-boot042}
until tools/lock.sh acquire vm "$OWNER" "job 050 boot042 kernel (keyboard path and storage as modules)" 60 2> /dev/null; do
    [ "${WAIT:-0}" = 1 ] || { tools/lock.sh status; exit 1; }
    [ -n "${told:-}" ] || { echo "waiting for the vm lock: $(tools/lock.sh status)"; told=1; }
    sleep 30
done
exec caffeinate -i tools/vm-job.sh virtualization/jobs/050-boot042-keyboard "$OWNER"
