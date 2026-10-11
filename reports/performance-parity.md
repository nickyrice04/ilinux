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
| Neural Engine | Core ML on ANE | not yet measured (needs coremltools; approval pending) | n/a | n/a | Unsupported, exclave-mediated |
| SSD | sequential read 1 / 4 threads | 11.0 / 13.3 GB/s | n/a | n/a | Unsupported (no ANS3 driver) |
| | sequential write (with full flush) | 11.2 GB/s | n/a | n/a | |
| | 4K random read QD1 / QD8 / QD32 | 17.4 K / 133 K / 253 K IOPS | n/a | n/a | |
| | 4K random read QD1 latency p50 / p99 | 56 / 72 µs | n/a | n/a | lower is better |
| | 4K random write QD1 / QD8 | 12.5 K / 48.9 K IOPS | n/a | n/a | |
| LLM inference (GPU) | llama.cpp Metal, synthetic Llama-3-8B Q4_K_M, pp512 / pp2048 / tg128 | 2909 / 2649 / 98.6 t/s | n/a | n/a | Unsupported (no GPU) |
| LLM inference (CPU) | llama.cpp `-ngl 0` (uses Accelerate BLAS + op offload; see note) | see results JSON | n/a | n/a | Portable pure-CPU rerun planned |
| Power efficiency | — | not measured (powermetrics needs sudo) | n/a | n/a | Blocked (B-008) |

## Notes and limitations

* **"CPU-only" llama.cpp on macOS isn't portable.** With `-ngl 0`, large
  matrix multiplies run in Apple's **Accelerate** (BLAS device "Accelerate",
  which uses the matrix hardware), and op-offload may still use Metal. A
  Linux comparison needs both a "best available" figure (Accelerate) and a
  portable `ggml-cpu` figure (`-dev none -nopo 1`). The second is the
  apples-to-apples one.
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
