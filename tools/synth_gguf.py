#!/usr/bin/env python3
"""Generate a synthetic-weight GGUF model for hardware-only LLM benchmarking.

Why: token-generation and prompt-processing throughput in llama.cpp depend on
tensor shapes and quantization types, not on weight values.  A synthetic model
with real architecture dimensions lets us benchmark the *same* workload on
macOS (Metal/CPU) and Linux (Vulkan/CPU) without downloading model weights and
with a bit-identical file on both sides.  Output quality is meaningless by
design; only llama-bench style throughput measurements are valid.

Pure standard library (Python >= 3.8).  Usage:
  synth_gguf.py --preset llama3-8b --quant q4_k_m --out model.gguf
Presets: llama3.2-1b, llama3-8b, llama3-70b.  Quants: f16, q8_0, q4_0, q4_k_m.

Block layouts follow ggml's documented quantization structs
(ggml-common.h): each block's fp16 scale fields are set to a small finite
value so activations stay finite; all other bytes are pseudo-random.
"""
import argparse
import os
import struct
import sys

# ggml_type ids and (block_elems, block_bytes, scale_offsets) per type.
# scale_offsets: byte offsets of fp16 scale fields inside one block.
GGML = {
    "f32": (0, 1, 4, ()),
    "f16": (1, 1, 2, ()),
    "q4_0": (2, 32, 18, (0,)),            # half d; u8 qs[16]
    "q8_0": (8, 32, 34, (0,)),            # half d; i8 qs[32]
    "q4_k": (12, 256, 144, (0, 2)),       # half d, dmin; u8 scales[12]; u8 qs[128]
    "q6_k": (14, 256, 210, (208,)),       # u8 ql[128]; u8 qh[64]; i8 scales[16]; half d
}
FTYPE = {"f16": 1, "q4_0": 2, "q8_0": 7, "q4_k_m": 15}

PRESETS = {
    # name: n_embd, n_layer, n_head, n_head_kv, n_ff, n_vocab, ctx, rope_base
    "llama3.2-1b": (2048, 16, 32, 8, 8192, 128256, 8192, 500000.0),
    "llama3-8b": (4096, 32, 32, 8, 14336, 128256, 8192, 500000.0),
    "llama3-70b": (8192, 80, 64, 8, 28672, 128256, 8192, 500000.0),
}

T_UINT32, T_INT32, T_FLOAT32, T_BOOL, T_STRING, T_ARRAY = 4, 5, 6, 7, 8, 9


def gstr(s):
    b = s.encode("utf-8")
    return struct.pack("<Q", len(b)) + b


def kv(key, vtype, value):
    out = gstr(key) + struct.pack("<I", vtype)
    if vtype == T_UINT32:
        out += struct.pack("<I", value)
    elif vtype == T_INT32:
        out += struct.pack("<i", value)
    elif vtype == T_FLOAT32:
        out += struct.pack("<f", value)
    elif vtype == T_BOOL:
        out += struct.pack("<B", 1 if value else 0)
    elif vtype == T_STRING:
        out += gstr(value)
    else:
        raise ValueError(vtype)
    return out


def kv_array(key, etype, values):
    out = gstr(key) + struct.pack("<IIQ", T_ARRAY, etype, len(values))
    if etype == T_STRING:
        out += b"".join(gstr(v) for v in values)
    elif etype == T_FLOAT32:
        out += struct.pack("<%df" % len(values), *values)
    elif etype == T_INT32:
        out += struct.pack("<%di" % len(values), *values)
    return out


def tensor_types(quant, n_layer):
    """Per-tensor quant types, mimicking llama.cpp's choices for each ftype."""
    def more_bits(i):  # llama.cpp use_more_bits() for Q4_K_M
        return i < n_layer // 8 or i >= 7 * n_layer // 8 or (i - n_layer // 8) % 3 == 2

    def pick(name, layer):
        if quant == "f16":
            return "f16"
        if quant == "q8_0":
            return "q8_0"
        if quant == "q4_0":
            return "q6_k" if name == "output" else "q4_0"
        # q4_k_m
        if name == "output":
            return "q6_k"
        if name in ("attn_v", "ffn_down") and more_bits(layer):
            return "q6_k"
        return "q4_k"
    return pick


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preset", default="llama3-8b", choices=sorted(PRESETS))
    ap.add_argument("--quant", default="q4_k_m", choices=sorted(FTYPE))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    n_embd, n_layer, n_head, n_head_kv, n_ff, n_vocab, ctx, rope = PRESETS[args.preset]
    head_dim = n_embd // n_head
    pick = tensor_types(args.quant, n_layer)

    tensors = [("token_embd.weight", (n_embd, n_vocab), pick("token_embd", -1))]
    for i in range(n_layer):
        p = "blk.%d." % i
        tensors += [
            (p + "attn_norm.weight", (n_embd,), "f32"),
            (p + "attn_q.weight", (n_embd, n_head * head_dim), pick("attn_q", i)),
            (p + "attn_k.weight", (n_embd, n_head_kv * head_dim), pick("attn_k", i)),
            (p + "attn_v.weight", (n_embd, n_head_kv * head_dim), pick("attn_v", i)),
            (p + "attn_output.weight", (n_head * head_dim, n_embd), pick("attn_output", i)),
            (p + "ffn_norm.weight", (n_embd,), "f32"),
            (p + "ffn_gate.weight", (n_embd, n_ff), pick("ffn_gate", i)),
            (p + "ffn_up.weight", (n_embd, n_ff), pick("ffn_up", i)),
            (p + "ffn_down.weight", (n_ff, n_embd), pick("ffn_down", i)),
        ]
    tensors += [("output_norm.weight", (n_embd,), "f32"),
                ("output.weight", (n_embd, n_vocab), pick("output", -1))]

    # Tokenizer: SentencePiece-style vocab of placeholder tokens plus the 256
    # byte tokens llama.cpp expects for SPM vocabularies.
    toks, scores, ttypes = ["<unk>", "<s>", "</s>"], [0.0, 0.0, 0.0], [2, 3, 3]
    toks += ["<0x%02X>" % b for b in range(256)]
    scores += [0.0] * 256
    ttypes += [6] * 256
    for i in range(len(toks), n_vocab):
        toks.append("▁t%d" % i)
        scores.append(-float(i))
        ttypes.append(1)

    meta = [
        kv("general.architecture", T_STRING, "llama"),
        kv("general.name", T_STRING, "synthetic-%s-%s" % (args.preset, args.quant)),
        kv("general.file_type", T_UINT32, FTYPE[args.quant]),
        kv("general.quantization_version", T_UINT32, 2),
        kv("llama.context_length", T_UINT32, ctx),
        kv("llama.embedding_length", T_UINT32, n_embd),
        kv("llama.block_count", T_UINT32, n_layer),
        kv("llama.feed_forward_length", T_UINT32, n_ff),
        kv("llama.attention.head_count", T_UINT32, n_head),
        kv("llama.attention.head_count_kv", T_UINT32, n_head_kv),
        kv("llama.attention.layer_norm_rms_epsilon", T_FLOAT32, 1e-5),
        kv("llama.rope.freq_base", T_FLOAT32, rope),
        kv("llama.rope.dimension_count", T_UINT32, head_dim),
        kv("llama.vocab_size", T_UINT32, n_vocab),
        kv("tokenizer.ggml.model", T_STRING, "llama"),
        kv_array("tokenizer.ggml.tokens", T_STRING, toks),
        kv_array("tokenizer.ggml.scores", T_FLOAT32, scores),
        kv_array("tokenizer.ggml.token_type", T_INT32, ttypes),
        kv("tokenizer.ggml.bos_token_id", T_UINT32, 1),
        kv("tokenizer.ggml.eos_token_id", T_UINT32, 2),
        kv("tokenizer.ggml.unknown_token_id", T_UINT32, 0),
        kv("tokenizer.ggml.add_bos_token", T_BOOL, True),
        kv("tokenizer.ggml.add_eos_token", T_BOOL, False),
    ]

    align = 32
    infos, offset, sizes = [], 0, []
    for name, shape, ty in tensors:
        tid, be, bb, _ = GGML[ty]
        nel = 1
        for d in shape:
            nel *= d
        assert shape[0] % be == 0, (name, shape, ty)
        nbytes = nel // be * bb
        infos.append(gstr(name) + struct.pack("<I", len(shape)) +
                     struct.pack("<%dQ" % len(shape), *shape) + struct.pack("<IQ", tid, offset))
        sizes.append(nbytes)
        offset += (nbytes + align - 1) // align * align

    header = b"GGUF" + struct.pack("<IQQ", 3, len(tensors), len(meta))
    head = header + b"".join(meta) + b"".join(infos)
    head += b"\0" * ((-len(head)) % align)

    pool = os.urandom(64 << 20)
    d_scale = struct.pack("<e", 0.0005)  # small finite fp16 block scale
    one_f32 = struct.pack("<f", 1.0)
    written = 0
    with open(args.out, "wb") as f:
        f.write(head)
        for (name, shape, ty), nbytes in zip(tensors, sizes):
            _, be, bb, scale_offs = GGML[ty]
            if ty == "f32":  # norm weights
                f.write(one_f32 * (nbytes // 4))
            else:
                chunk = (8 << 20) // bb * bb
                pos = 0
                while pos < nbytes:
                    n = min(chunk, nbytes - pos)
                    start = (written + pos) % (len(pool) - chunk)
                    buf = bytearray(pool[start:start + n])
                    if ty == "f16":  # keep fp16 values finite and small
                        buf[1::2] = bytes([0x10]) * (n // 2)
                    nblk = n // bb
                    for so in scale_offs:
                        buf[so::bb] = d_scale[0:1] * nblk
                        buf[so + 1::bb] = d_scale[1:2] * nblk
                    f.write(buf)
                    pos += n
            pad = (-nbytes) % align
            if pad:
                f.write(b"\0" * pad)
            written += nbytes
    total = os.path.getsize(args.out)
    print("wrote %s: %d tensors, %.2f GiB, quant=%s" %
          (args.out, len(tensors), total / 2**30, args.quant), file=sys.stderr)


if __name__ == "__main__":
    main()
