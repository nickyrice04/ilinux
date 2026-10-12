#!/bin/bash
# Host SoC power (IOReport via benchmarks/bin/powermon, no root) for the
# Omarchy VM in different states.  Repeats each state R times (median taken
# by tools/power_summary.py consumers) to ride out host background noise.
#
#   benchmarks/vm/vm_power_states.sh OUT_DIR vm      # VM running (console socket)
#   benchmarks/vm/vm_power_states.sh OUT_DIR host    # VM stopped: host baseline
#
# VM states: desktop-idle (Hyprland on, display lit, nothing animating),
# dpms-off (Hyprland display powered off: what Omarchy's idle chain ends in).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:?out dir}"; MODE="${2:?vm|host}"; R="${R:-3}"; SECS="${SECS:-30}"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
SOCK="$ROOT/virtualization/run/console.sock"
vm() { /usr/bin/python3 -I "$ROOT/tools/vmconsole.py" "$SOCK" "$1" 20 >/dev/null; }
HYPR='sudo -u omarchy XDG_RUNTIME_DIR=/run/user/1002 HYPRLAND_INSTANCE_SIGNATURE=$(ls -t /run/user/1002/hypr/ | head -1) hyprctl dispatch'
measure() {  # label
  for i in $(seq 1 "$R"); do
    sleep 5
    "$ROOT/benchmarks/bin/powermon" -i 250 -- sleep "$SECS" 2>/dev/null | grep '^{"bench":"power"' |
      sed "s/^{/{\"label\":\"$1\",\"rep\":$i,/" >> "$OUT/power.jsonl"
  done
}
if [[ $MODE == host ]]; then
  pgrep -q -f qemu-system-aarch64 && { echo "stop the VM first" >&2; exit 1; }
  measure host-idle-vm-off
else
  vm "$HYPR 'hl.dsp.dpms({ action = \"enable\" })'"; sleep 3
  measure vm-desktop-idle
  vm "$HYPR 'hl.dsp.dpms({ action = \"disable\" })'"; sleep 3
  measure vm-dpms-off
  vm "$HYPR 'hl.dsp.dpms({ action = \"enable\" })'"
fi
echo "done: $OUT/power.jsonl"
