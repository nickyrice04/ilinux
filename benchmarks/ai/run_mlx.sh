#!/bin/bash
# MLX (GPU) LLM baseline on macOS using the project venv.
#  1. synthetic Llama-3-8B shape, 4-bit (group 32) - same shape as the GGUF runs
#  2. real models already present in the user's Hugging Face cache (read-only,
#     offline; nothing is downloaded)
#   benchmarks/ai/run_mlx.sh OUT_DIR
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:?out dir}"; mkdir -p "$OUT"
PY="$ROOT/tools/venv/bin/python"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
HF=~/.cache/huggingface/hub
TOK=$(ls -d $HF/models--Qwen--Qwen2.5-0.5B/snapshots/*/ | head -1)
SYN="$ROOT/benchmarks/ai/models/mlx-synth-llama3-8b-4bit-g32"
[ -f "$SYN/config.json" ] || "$PY" "$ROOT/tools/synth_mlx.py" --preset llama3-8b --bits 4 \
    --group-size 32 --tokenizer-from "$TOK" --out "$SYN"
"$PY" -c "import mlx.core as mx, mlx_lm; print('mlx', mx.__version__, 'mlx_lm', mlx_lm.__version__)" > "$OUT/mlx-versions.txt"
bench() {  # name model_dir
  echo "== $1" >> "$OUT/mlx.log"
  "$ROOT/tools/venv/bin/mlx_lm.benchmark" --model "$2" -p 512 -g 128 -n 5 >> "$OUT/mlx.log" 2>&1 || echo "FAILED $1" >> "$OUT/mlx.log"
}
caffeinate -i true
bench synth-llama3-8b-4bit-g32 "$SYN"
for m in mlx-community--gemma-3-12b-it-bf16 mlx-community--Qwen3.5-0.8B-bf16; do
  d=$(ls -d $HF/models--$m/snapshots/*/ 2>/dev/null | head -1)
  [ -n "$d" ] && bench "$m" "$d"
done
echo "done: $OUT"
