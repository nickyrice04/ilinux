# Performance Parity Scorecard

Reference: macOS 26.6.2 on MacBook Pro Mac17,6 (M5 Max), run
`benchmarks/results/macos-2026-10-11-ac-lpm/`. The run was on AC power, and
macOS reported "Low Power Mode: Yes" for AC (see `env-*.txt`).

Linux status: **no native Linux boots on t6050**. Every native-Linux cell is
therefore "Unsupported", which is distinct from "slow", and parity is not
computed. VM results will be added in a separate section and never counted
as native parity.

Parity formula: higher-is-better `linux/macos × 100%`; lower-is-better
`macos/linux × 100%`. It's computed only with identical benchmark code,
model files and precision.

## Scorecard

| Subsystem | Metric (same code on both OSes) | macOS baseline | Native Linux | Parity | Status / confidence |
|---|---|---|---|---|---|
| CPU single-core | `cpubench fma` 1 thread, P core | 124.6 GFLOP/s | n/a | n/a | Unsupported (no boot) |
| | `cpubench intmix` / `sort` / `sgemm` 1 thread | 21.0 Gop/s / 23.3 Melem/s / 60.2 GFLOP/s | n/a | n/a | Unsupported |
| CPU multicore | `cpubench fma` 18 threads | 1623 GFLOP/s | n/a | n/a | Unsupported |
| | `intmix` / `sort` / `sgemm` 18 threads | 258.6 Gop/s / 373 Melem/s / 641 GFLOP/s | n/a | n/a | Unsupported |
| CPU P vs M placement | QoS background vs ui (FMA, 1 thread) | 33.0 vs 124.6 GFLOP/s (26%) | n/a | n/a | Linux design ready (`omarchy-qos`) |
| Matrix unit (SME) | `sme_f32` 1 thread / 18 threads | 2.17 / 3.23 TFLOP/s | n/a | n/a | Kernel supports SME-only CPUs; untested here |
| | `sme_i8` 1 thread / 18 threads | 4.34 / 6.46 TOPS | n/a | n/a | |
| OS overheads | `getppid` syscall | 85.4 ns | n/a | n/a | lower is better |
| | pipe ping-pong round trip (ui / bg) | 3.69 / 9.84 µs | n/a | n/a | lower is better |
| Unified memory, CPU | STREAM copy 1 / 18 threads | 140 / 377 GB/s | n/a | n/a | Unsupported |
| | STREAM triad 18 threads | 351 GB/s | n/a | n/a | |
| | DRAM latency, 2 GiB random chase (DMP active) | 112 ns | n/a | n/a | lower is better |
| | anon page first-touch (16 KiB pages) | 31.5 GB/s, 1.92 M faults/s | n/a | n/a | |
| GPU compute | FP32 / FP16 FMA peak | 14.8 / 17.6 TFLOP/s | n/a | n/a | Unsupported (no G17 driver) |
| GPU matrix | MPS GEMM FP16 n=4096 | 63.9 TFLOP/s | n/a | n/a | Unsupported (matrix units undocumented) |
| | MPS GEMM FP32 n=4096 | 14.8 TFLOP/s | n/a | n/a | |
| GPU memory | copy bandwidth (shared buffers) | 537 GB/s | n/a | n/a | |
| GPU latency | empty dispatch round trip (median) | 149 µs | n/a | n/a | lower is better |
| GPU graphics | not yet measured (Metal render benchmark TBD) | — | n/a | n/a | |
| Neural Engine | Core ML FP16, 1×1-conv stack / FFN stack (all ops planned on ANE via MLComputePlan) | **14.0 / 7.1 TFLOP/s** at ANE ≈ 3.6 W | n/a | n/a | Unsupported (no Linux driver; exclave-mediated) |
| SSD | sequential read 1 / 4 threads | 11.0 / 13.3 GB/s | n/a | n/a | Unsupported (no ANS3 driver) |
| | sequential write (with full flush) | 11.2 GB/s | n/a | n/a | |
| | 4K random read QD1 / QD8 / QD32 | 17.4 K / 133 K / 253 K IOPS | n/a | n/a | |
| | 4K random read QD1 latency p50 / p99 | 56 / 72 µs | n/a | n/a | lower is better |
| | 4K random write QD1 / QD8 | 12.5 K / 48.9 K IOPS | n/a | n/a | |
| LLM inference (GPU) | llama.cpp Metal, synthetic Llama-3-8B Q4_K_M, pp512 / pp2048 / tg128 | 2909 / 2649 / 98.6 t/s | n/a | n/a | Unsupported (no GPU) |
| LLM inference (CPU) | llama.cpp `-ngl 0` (uses Accelerate BLAS + op offload; see note) | see results JSON | n/a | n/a | Portable pure-CPU rerun planned |
| Power efficiency | `powermon` (IOReport, no root): idle CPU / DRAM / GPU | 0.65 / 0.32 / 0.15 W | n/a | n/a | macOS measurable; no Linux equivalent yet |



## AI and energy baselines (macOS, 2026-10-11)

Sources: `benchmarks/results/macos-2026-10-11-{mlx,coreml,power}/` and
`macos-2026-10-11-ac-lpm/ai-llamacpp.jsonl`.

### LLM inference (GPU)

| Framework / model | Prefill (pp512) | Generation (tg128) | Notes |
|---|---|---|---|
| llama.cpp Metal, synthetic Llama-3-8B Q4_0 (4.65 GB) | 3090 t/s | 105.2 t/s | Same GGUF can run on Linux later |
| llama.cpp Metal, synthetic Llama-3-8B Q4_K_M (4.91 GB) | 2909 t/s | 98.6 t/s | pp2048: 2649 t/s |
| MLX 0.32.3, synthetic Llama-3-8B 4-bit g32 | 3104 t/s | 100.8 t/s | peak 5.6 GB |
| MLX, Gemma-3-12B-it bf16 (real, from user's HF cache) | 1672 t/s | 21.7 t/s | ≈ 521 GB/s of weights streamed, ≈ 97% of the measured GPU copy bandwidth |
| MLX, Qwen3.5-0.8B bf16 (real) | 18982 t/s | 267.7 t/s | |

### Compute units (Core ML FP16, `benchmarks/ai/coreml_ane_bench.py`)

| Model | ANE | GPU | CPU (uses SME) | "All" picks |
|---|---|---|---|---|
| 1×1 conv stack (C=2048, S=512, 16 layers) | **14.0 TFLOP/s** | 29.9 | 3.85 | GPU |
| FFN stack (D=2048, F=8192, S=512, 8 layers) | 7.1 | 50.3 | 3.74 | GPU |

On M5 Max, Core ML's planner prefers the GPU, whose matrix units beat the ANE
on raw throughput. The ANE remains the efficiency leader.

### Energy (IOReport via `powermon`, average W over each run, includes idle floor)

| Workload | Throughput | Block power | Efficiency |
|---|---|---|---|
| FMA, 1 thread, QoS ui (P core) | 125 GFLOP/s | P cluster 7.41 W | 17 GFLOP/J (incremental ≈ 18) |
| FMA, 1 thread, QoS background (M core) | 32 GFLOP/s | M cluster 0.77 W | incremental ≈ 70 GFLOP/J (**≈ 4× P**) |
| FMA, 18 threads | 1641 GFLOP/s | CPU 58.9 W | 28 GFLOP/J |
| SME f32, 1 thread, P cluster | 2.17 TFLOP/s | CPU 14.0 W (`PCPM` rail 9.8 W) | 155 GFLOP/J |
| SME f32, 1 thread, background (M) | 0.20 TFLOP/s | CPU 1.2 W | 169 GFLOP/J |
| STREAM 18 threads | 362 GB/s | CPU 42.8 W, DRAM 11.1 W | |
| Core ML FFN on ANE | 7.1 TFLOP/s | **ANE 3.6 W** | ≈ 2.0 TFLOP/s per W |
| Core ML FFN on GPU | 48.6 TFLOP/s | GPU 56.5 W | ≈ 0.86 TFLOP/s per W |
| Core ML FFN on CPU | 3.7 TFLOP/s | CPU 14.9 W | ≈ 0.25 TFLOP/s per W |
| llama.cpp Metal tg128, 8B Q4_0 | 105.6 t/s | GPU 35.4 W + DRAM 20.2 W + CPU 3.4 W | ≈ 0.56 J/token |

Linux parity for energy needs a Linux-side energy source (PMGR/SMC counters).
That doesn't exist yet (B-008).

## Linux in a VM on the same machine (separate track, not native parity)

Arch Linux ARM 7.1.6 guest under Virtualization.framework (`vzrun`, 18
vCPUs, 32 GiB). Both sides ran the same C sources with `-O3 -mcpu=apple-m4`
(Apple clang 21 on macOS, clang 23 in the guest). Parity uses medians. Full
table: [`vm-vs-macos-parity.md`](vm-vs-macos-parity.md). Raw data:
`benchmarks/results/vm-alarm-2026-10-11/` vs
`benchmarks/results/macos-2026-10-11-parity-applem4/`.

| Area | Result (VM as % of macOS) | Notes |
|---|---|---|
| CPU compute (clock estimate, integer, sort, SGEMM; 1–18 threads) | **97–101%** | Same clocks (4.46 vs 4.51 GHz single-core estimate) |
| CPU FMA, identical asm | **99%** (124.3 vs 125.4 GFLOP/s) | The C-kernel gap (112%) was compiler codegen (F-016) |
| SME matrix unit (f32, i8; 1–18 threads) | **97–100%** | SME2 is passed through to the guest |
| Thread wakeup (pipe ping-pong) | **7%** (52 µs vs 3.8 µs) | Hypervisor exit cost per cross-vCPU wakeup |
| Syscall (`getppid`) | **77%** (113 vs 87 ns) | |
| Memory bandwidth (STREAM, 6–18 threads) | **93–100%** | 1 thread copy 81% |
| DRAM latency (256 MiB / 2 GiB chase) | **84% / 72%** | Two-stage translation with 4K guest pages |
| Page-fault/zero-fill throughput | **35%** | Stage-2 faults |
| Storage seq read 1 / 4 threads | **13% / 26%** | virtio-blk on sparse file, sync=full |
| Storage seq write | **3%** first write into a sparse image (0.34 GB/s); **28%** on allocated blocks (3.2 GB/s) | Job 005 (F-018) |
| Storage seq read, best durable mode (virtio + fsync), 1 / 4 threads | **51% / 65%** (5.6 / 8.6 GB/s) | Cached mode (24–50 GB/s) is host RAM and not counted |
| Storage 4K random read QD1 / QD32 | **57% / 30%** | |
| llama.cpp CPU, 8B Q4_0, tg64 / pp512 (6–18 threads) | **92–100% / 104–117%** | VM: same llama.cpp commit, CPU-only ggml (SME), no BLAS. macOS: Homebrew build with Accelerate (F-017) |
| llama.cpp CPU, 8B Q4_K_M, tg64 / pp512 | **111–124% / 207–223%** | macOS Accelerate path dequantizes k-quants to FP32. Build config dominates, not the OS |
| GPU in this initial VZ test | **not available** (2D virtio-gpu only) | Superseded for the working desktop by QEMU/VirGL/Venus; see the current VM report |

### Later QEMU video improvement (2026-10-12)

The installed `mesa-virgl-video-ilinux` package provides lossless tested
4:2:0 downloads and optional NV12 H.264 decode. Two ABBA blocks measured
0.296200 → 0.173850 QEMU cores for paced 4K60 decode: **41.3% less CPU time**.
This comparison is between two guest decode formats, not against macOS.
It excludes presentation; noisy whole-SoC power cannot establish an energy
gain. See [implementation and validation](video-download-and-nv12-2026-10-12.md).

## Notes and limitations

* **"CPU-only" llama.cpp on macOS isn't portable.** With `-ngl 0`, large
  matrix multiplies run in Apple's **Accelerate** (BLAS device "Accelerate",
  which uses the matrix hardware), and op-offload may still use Metal. A
  Linux comparison needs both a "best available" figure (Accelerate) and a
  portable `ggml-cpu` figure (`-dev none -nopo 1`). The second is the
  apples-to-apples one.
* **Core placement matters for latency on macOS.** Without a QoS hint, a
  single-threaded chase may run on an M core: 1 MiB latency was 2.8 ns in
  one run and 4.3 ns in another. Future latency runs pin to the P cluster
  (`-q ui` on macOS, `taskset` natively on Linux).
* **DMP effect.** Apple's data memory-dependent prefetcher lowers apparent
  pointer-chase latency in the cache range. The `-d` (DIT) variant measures
  with DMP disabled. Linux's default DMP state must be checked natively.
* **Energy mode.** "Low Power Mode: Yes" on AC was active. Single-core peak
  was the same as on battery, but sustained multi-core and GPU limits may be
  below High Power mode. A rerun under High Power or Automatic is pending
  user action (B-009).
* **Neural Engine** results must come from Core ML runs pinned to
  `.cpuAndNeuralEngine` with verified residency. Nothing here is inferred
  from GPU results.
