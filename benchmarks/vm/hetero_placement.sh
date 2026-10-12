#!/bin/bash
# CPU placement vs host energy for the heterogeneous-vCPU VM (--hetero):
# runs guest cpubench under different placements while host powermon records
# per-cluster energy.  Needs the VM up with --console-socket and cpubench in
# the guest (/usr/local/bin/cpubench).
#   benchmarks/vm/hetero_placement.sh OUT_DIR [kernel] [threads]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:?out dir}"; K="${2:-intmix}"; T="${3:-1}"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
SOCK="$ROOT/virtualization/run/console.sock"
QOSRUN="sudo -u omarchy XDG_RUNTIME_DIR=/run/user/1002 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1002/bus omarchy-qos run"
fg="0-$((T - 1))"; bg="12-$((12 + T - 1))"   # vCPUs 0-11 normal, 12-17 background
cases=(
  "fg-pinned|taskset -c $fg cpubench $K -t $T -s 2 -r 3"
  "bg-pinned|taskset -c $bg cpubench $K -t $T -s 2 -r 3"
  "unpinned|cpubench $K -t $T -s 2 -r 3"
  "tier-background|$QOSRUN background -- cpubench $K -t $T -s 2 -r 3"
  "tier-interactive|$QOSRUN interactive -- cpubench $K -t $T -s 2 -r 3"
)
tmp="$OUT/.powermon.tmp"
for c in "${cases[@]}"; do
  label=${c%%|*}; cmd=${c#*|}
  sleep 5
  "$ROOT/benchmarks/bin/powermon" -i 200 -- /usr/bin/python3 -I "$ROOT/tools/vmconsole.py" "$SOCK" "$cmd" 300 > "$tmp" 2>/dev/null || true
  perf=$(grep -o '{"bench":"cpu"[^}]*}' "$tmp" | head -1 || true)
  pw=$(grep '^{"bench":"power"' "$tmp" | head -1 || true)
  [[ -n $perf && -n $pw ]] || { echo "$label: no result" >&2; continue; }
  echo "{\"label\":\"$label\",\"kernel\":\"$K\",\"threads\":$T,\"guest\":$perf,\"host\":$pw}" >> "$OUT/placement.jsonl"
  /usr/bin/python3 -I - "$OUT/placement.jsonl" <<'PY'
import json, sys
d = json.loads(open(sys.argv[1]).readlines()[-1]); g, h = d["guest"], d["host"]
w = h["avgW:CPU Energy"]; perf = g["aggregate_median"]
print(f"{d['label']:17s} {perf:7.2f} {g['unit']:6s} cpus {g['cpus_last_rep']:7s} host CPU {w:5.2f} W "
      f"(P {h.get('avgW:PCPU', 0):.2f} M0 {h.get('avgW:MCPU0', 0):.2f} M1 {h.get('avgW:MCPU1', 0):.2f}) "
      f"{h['seconds']:5.1f}s  ->  {perf / max(w, 1e-3):.2f} {g['unit']}/W")
PY
done
rm -f "$tmp"
