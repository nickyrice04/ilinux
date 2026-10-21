#!/bin/bash
# Reuse the pinned diagnostic/root and workload; change only the CPU policy.
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out
mkdir -p "$I" "$O"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
exec > "$O/policy.log" 2>&1
python3 -I - "$I" "$O" <<'PY'
import hashlib, sys
from pathlib import Path
i,o=map(Path,sys.argv[1:]); src=i/'virtualization/jobs/056-desktop-timeline'
h=src/'out/Hyprland-timeline31'
if hashlib.sha256(h.read_bytes()).hexdigest()!='b22fedff2f75a7a955bb881aa5c314d6e7028570f98204d981eb0012bf920c6e':
 raise ValueError('diagnostic compositor mismatch')
script=(src/'bench.sh').read_text()
def change(old,new):
 global script
 if script.count(old)!=1: raise ValueError('bench anchor mismatch')
 script=script.replace(old,new)
change('cp /mnt/job/workload.py "$R/run/t31/"',
       'cp "$I/virtualization/jobs/056-desktop-timeline/workload.py" "$R/run/t31/"\n'
       'cp "$I/kernel/experiments/smp31/renderer.py" "$R/run/t31/"')
change('case "$cases" in \'0 1 2\'|4|5)', 'case "$cases" in \'6 7 8\')')
change('  profile=normal', '''  profile=normal
  runner=()
  render_cpus=0-1
  if [ "$mode" = 7 ] || [ "$mode" = 8 ]; then
    runner=(python3 -I /run/t31/renderer.py --)
  fi
  if [ "$mode" = 8 ]; then render_cpus=0-5; fi''')
change('taskset -c "$render_cpus" dbus-run-session -- start-hyprland',
       'taskset -c "$render_cpus" "${runner[@]}" dbus-run-session -- start-hyprland')
change('cp "$O/Hyprland-timeline31"', 'cp "$I/virtualization/jobs/056-desktop-timeline/out/Hyprland-timeline31"')
# Baseline throughput is already recorded; this run isolates the policy.
start=script.index('if [ ! -f "$O/linux-vm/result.json" ]; then')
end=script.index('\nfi',start)+3
script=script[:start]+script[end:]
(o/'bench.sh').write_text(script)
PY
ILINUX_VM_CASES='6 7 8' /bin/bash "$O/bench.sh"
echo RENDERER-POLICY-PASS
