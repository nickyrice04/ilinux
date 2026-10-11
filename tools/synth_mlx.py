#!/usr/bin/env python3
"""Create a synthetic-weight MLX model (Llama-3 shapes) for MLX throughput
benchmarks, the MLX counterpart of tools/synth_gguf.py.

Weights are random (MLX default initialisers), quantized with MLX affine
quantization.  Throughput depends on shapes and quantization, not values, so
`mlx_lm.benchmark` numbers are meaningful while outputs are not.

A tokenizer is required by mlx_lm.load(); it is copied (read-only source) from
a local Hugging Face cache snapshot passed with --tokenizer-from.  Its vocab
must be >= the model vocab so generated ids decode.

Usage:
  tools/venv/bin/python tools/synth_mlx.py --preset llama3-8b --bits 4 \
      --group-size 32 --tokenizer-from <hf snapshot dir> --out DIR
"""
import argparse
import json
import shutil
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
from mlx_lm.models import llama
from mlx_lm.utils import save_model

PRESETS = {
    # n_embd, n_layer, n_head, n_head_kv, n_ff, vocab
    "llama3.2-1b": (2048, 16, 32, 8, 8192, 128256),
    "llama3-8b": (4096, 32, 32, 8, 14336, 128256),
}
TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "vocab.json",
                   "merges.txt", "special_tokens_map.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="llama3-8b", choices=sorted(PRESETS))
    ap.add_argument("--bits", type=int, default=4)
    ap.add_argument("--group-size", type=int, default=32)
    ap.add_argument("--tokenizer-from", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    n_embd, n_layer, n_head, n_kv, n_ff, vocab = PRESETS[a.preset]
    config = {
        "model_type": "llama",
        "hidden_size": n_embd,
        "num_hidden_layers": n_layer,
        "intermediate_size": n_ff,
        "num_attention_heads": n_head,
        "num_key_value_heads": n_kv,
        "rms_norm_eps": 1e-5,
        "vocab_size": vocab,
        "rope_theta": 500000.0,
        "max_position_embeddings": 8192,
        "tie_word_embeddings": False,
        "torch_dtype": "bfloat16",
    }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    mx.random.seed(0)
    model = llama.Model(llama.ModelArgs.from_dict(config))
    model.set_dtype(mx.bfloat16)
    # Keep values small and finite: scale the random init down.
    model.update(nn.utils.tree_map(lambda p: p * 0.02, model.parameters()))
    if a.bits:
        nn.quantize(model, group_size=a.group_size, bits=a.bits)
        config["quantization"] = {"group_size": a.group_size, "bits": a.bits}
    mx.eval(model.parameters())
    save_model(out, model, donate_model=True)
    (out / "config.json").write_text(json.dumps(config, indent=2))

    src = Path(a.tokenizer_from)
    copied = [f for f in TOKENIZER_FILES if (src / f).exists()]
    for f in copied:
        shutil.copyfile(src / f, out / f)  # resolves HF cache symlinks
    print("wrote", out, "tokenizer files:", copied)


if __name__ == "__main__":
    main()
