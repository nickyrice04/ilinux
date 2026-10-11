#!/bin/bash
# Energy-instrumented runs on macOS (no root): wraps workloads in powermon
# (IOReport "Energy Model" + DVFS residency) and records per-run energy, so
# performance-per-watt can be computed.  Output: OUT/power.jsonl where each
# workload's own result line(s) are followed by its power line, all tagged.
#   benchmarks/macos/run_power.sh OUT_DIR
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:?out dir}"; mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
BIN="$ROOT/benchmarks/bin"; PY="$ROOT/tools/venv/bin/python"
if [ -z "${CAFFEINATED:-}" ]; then export CAFFEINATED=1; exec caffeinate -i "$0" "$@"; fi
run() {  # label cmd...
  local label=$1; shift
  "$BIN/powermon" -i 200 -- "$@" 2>/dev/null | grep '^{' |
    sed "s/^{/{\"label\":\"$label\",/" >> "$OUT/power.jsonl"
  sleep 5
}
run idle-10s sleep 10
run fma-1t-ui "$BIN/cpubench" fma -t 1 -q ui -s 2 -r 3
run fma-1t-bg "$BIN/cpubench" fma -t 1 -q bg -s 2 -r 3
run fma-18t-ui "$BIN/cpubench" fma -t 18 -q ui -s 2 -r 3
run intmix-1t-ui "$BIN/cpubench" intmix -t 1 -q ui -s 2 -r 3
run intmix-1t-bg "$BIN/cpubench" intmix -t 1 -q bg -s 2 -r 3
run sme_f32-1t-ui "$BIN/cpubench" sme_f32 -t 1 -q ui -s 2 -r 3
run sme_f32-1t-bg "$BIN/cpubench" sme_f32 -t 1 -q bg -s 2 -r 3
run stream-18t "$BIN/membench" stream -t 18 -m 1024 -r 10
run gpu-fma "$BIN/gpubench" fma
run gpu-gemm "$BIN/gpubench" gemm
M="$ROOT/benchmarks/ai/models/synth-llama3-8b-q4_0.gguf"
[ -f "$M" ] && run llamacpp-metal-tg128 llama-bench -m "$M" -ngl 99 -p 0 -n 128 -r 3 -o jsonl
for u in cpu_and_ne cpu_and_gpu cpu_only; do
  run coreml-ffn-$u "$PY" "$ROOT/benchmarks/ai/coreml_ane_bench.py" "$OUT/coreml-pkgs" --only ffn --unit $u --seconds 10
done
echo "done: $OUT"
