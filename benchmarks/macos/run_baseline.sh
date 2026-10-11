#!/bin/bash
# Reproducible macOS reference baseline.  Non-destructive: writes only to the
# results directory and one temporary file in $TMPDIR_BENCH (deleted at end).
#
#   benchmarks/macos/run_baseline.sh [all|cpu|mem|storage|gpu|ai] [results_dir]
#
# Runs under `caffeinate -i` so idle sleep cannot interrupt a measurement.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BIN="$ROOT/benchmarks/bin"
SUITE="${1:-all}"
OUT="${2:-$ROOT/benchmarks/results/macos-$(date +%Y%m%d-%H%M%S)}"
TMPDIR_BENCH="${TMPDIR_BENCH:-${TMPDIR:-/tmp}}"
STOR_MIB="${STOR_MIB:-8192}"
MODEL_DIR="$ROOT/benchmarks/ai/models"
mkdir -p "$OUT"

if [ -z "${CAFFEINATED:-}" ]; then
  export CAFFEINATED=1
  exec caffeinate -i "$0" "$SUITE" "$OUT"
fi

build() {
  mkdir -p "$BIN"
  clang -O3 -mcpu=native -pthread "$ROOT/benchmarks/src/cpubench.c" -o "$BIN/cpubench"
  clang -O3 -mcpu=native -pthread "$ROOT/benchmarks/src/membench.c" -o "$BIN/membench"
  clang -O2 -mcpu=native -pthread "$ROOT/benchmarks/src/storbench.c" -o "$BIN/storbench"
  swiftc -O -module-cache-path "$TMPDIR_BENCH/swift-module-cache" \
    "$ROOT/benchmarks/src/gpubench.swift" -o "$BIN/gpubench"
}

state() {  # environment snapshot (no identifiers)
  local f="$OUT/env-$1.txt"
  {
    echo "phase=$1 date=$(date -u +%FT%TZ)"
    sw_vers | tr '\n' ' '; echo
    echo "model=$(sysctl -n hw.model) chip=$(sysctl -n machdep.cpu.brand_string) mem=$(sysctl -n hw.memsize)"
    echo "loadavg=$(sysctl -n vm.loadavg)"
    pmset -g batt | sed -n '1,2p' | sed -E 's/\(id=[0-9]+\)//'
    system_profiler SPPowerDataType 2>/dev/null | grep -E 'Power:|Low Power Mode|High Power Mode|Current Power Source' | tr -s ' ' | tr '\n' ' '; echo
    pmset -g therm 2>/dev/null | grep -v '^$' || true
    pmset -g | grep -iE 'lowpowermode|powermode' || true
    clang --version | head -1
    swiftc --version 2>&1 | head -1
  } > "$f" 2>&1
}

cool() { sleep "${1:-15}"; }

run_cpu() {
  local o="$OUT/cpu.jsonl"
  for q in ui default utility bg; do
    for k in fma intmix sort sgemm sme_f32; do "$BIN/cpubench" $k -t 1 -q $q -r 5 >> "$o"; done
  done
  cool
  for t in 6 12 18; do
    for k in fma intmix sort sgemm; do "$BIN/cpubench" $k -t $t -q ui -r 5 >> "$o"; cool 5; done
  done
  # SME unit sharing: one unit per cluster expected
  for t in 1 2 3 6 12 18; do
    for k in sme_f32 sme_bf16 sme_i8; do "$BIN/cpubench" $k -t $t -q ui -r 5 >> "$o"; done
    cool 5
  done
  "$BIN/cpubench" pingpong -r 7 -q ui >> "$o"
  "$BIN/cpubench" pingpong -r 7 -q bg >> "$o"
  "$BIN/cpubench" syscall -r 7 >> "$o"
}

run_mem() {
  local o="$OUT/mem.jsonl"
  for t in 1 2 4 6 12 18; do "$BIN/membench" stream -t $t -m 1024 -r 10 >> "$o"; cool 5; done
  "$BIN/membench" latency -m 2048 >> "$o"
  "$BIN/membench" fault -m 4096 -r 5 >> "$o"
}

run_storage() {
  local o="$OUT/storage.jsonl" f="$TMPDIR_BENCH/storbench.$$.dat"
  trap 'rm -f "$f"' RETURN
  "$BIN/storbench" seqwrite "$f" -m "$STOR_MIB" >> "$o"
  cool 10
  for t in 1 4; do "$BIN/storbench" seqread "$f" -t $t >> "$o"; done
  for t in 1 8 32; do "$BIN/storbench" randread "$f" -t $t -s 8 >> "$o"; done
  for t in 1 8; do "$BIN/storbench" randwrite "$f" -t $t -s 5 >> "$o"; done
  rm -f "$f"
}

run_gpu() {
  "$BIN/gpubench" all >> "$OUT/gpu.jsonl"
}

run_ai() {
  local o="$OUT/ai-llamacpp.jsonl"
  for q in q4_k_m q4_0; do
    local m="$MODEL_DIR/synth-llama3-8b-$q.gguf"
    [ -f "$m" ] || /usr/bin/python3 -I "$ROOT/tools/synth_gguf.py" --preset llama3-8b --quant $q --out "$m"
    # GPU (Metal) offload
    llama-bench -m "$m" -ngl 99 -p 512,2048 -n 128 -r 5 -o jsonl >> "$o" 2> "$OUT/ai-llamacpp-$q-metal.log"
    cool 10
    # CPU only, by thread count
    llama-bench -m "$m" -ngl 0 -t 6,12,18 -p 512 -n 64 -r 3 -o jsonl >> "$o" 2> "$OUT/ai-llamacpp-$q-cpu.log"
    cool 10
  done
}

build
state start
case "$SUITE" in
  all) run_cpu; state after-cpu; cool 30; run_mem; state after-mem; cool;
       run_storage; state after-storage; run_gpu; state after-gpu; cool 30; run_ai ;;
  cpu) run_cpu ;; mem) run_mem ;; storage) run_storage ;; gpu) run_gpu ;; ai) run_ai ;;
  *) echo "unknown suite $SUITE" >&2; exit 2 ;;
esac
state end
echo "results in $OUT"
