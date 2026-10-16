#!/bin/bash
# tools/vm-job.sh JOB_DIR [OWNER]: run one scripted job in the workspace Arch VM.
# Takes the shared "vm" lock (tools/lock.sh), shares the job dir as /mnt/job, the
# repository (read-only) as /mnt/ilinux and the pinned m1n1 clone as /mnt/m1n1-source.
# The job's run.sh writes out/run.log; the last lines are printed here.
# Optional VZRUN_EXTRA: more vzrun arguments, whitespace-separated (no spaces inside
# one argument), e.g. VZRUN_EXTRA="--nested --share /abs/dir:tag:ro". Unset = default VM.
set -u
cd "$(dirname "$0")/.." || exit 1
JOB="${1:?usage: tools/vm-job.sh virtualization/jobs/NNN-name [owner]}"
OWNER="${2:-vmjob}"
A="$PWD/../apple-silicon-linux-research"
IMG="$A/virtualization/images/alarm"
read -r -a EXTRA <<< "${VZRUN_EXTRA:-}"
[ -x "$JOB/run.sh" ] || { echo "no executable $JOB/run.sh" >&2; exit 1; }
tools/lock.sh acquire vm "$OWNER" "vm-job $JOB" | tail -1
[ "${PIPESTATUS[0]}" = 0 ] || exit 1   # held by someone else: never a second VM on the same disk
trap 'tools/lock.sh release vm "$OWNER" | tail -1' EXIT
"$A/virtualization/bin/vzrun" --cpus 12 --mem 24 \
  --kernel "$IMG/Image-7.1.6-vzrun2-pkg" \
  --cmdline 'console=hvc0 root=/dev/vda rootflags=subvol=@ rw rootwait quiet loglevel=3' \
  --disk "$IMG/root-btrfs.img" \
  --share "$PWD/$JOB:job" --share "$PWD:ilinux:ro" --share "$A/third_party/m1n1:m1n1-source:ro" \
  ${EXTRA[@]+"${EXTRA[@]}"} \
  < /dev/null > "${TMPDIR:-/tmp}/vm-job-$$.console" 2>&1
rc=$?
echo "vzrun exit $rc"
tail -5 "$JOB/out/run.log" 2>/dev/null
exit $rc
