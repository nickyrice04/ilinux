# Benchmark Methodology

Goal: produce **comparable** measurements of the same hardware under macOS
and, later, under Linux (native or VM), so parity can be computed per
subsystem. Every run is reproducible from this repository.

## Principles

1. **Same code on both OSes.** CPU, memory and storage benchmarks are
   self-contained C (`benchmarks/src/{cpubench,membench,storbench}.c`).
   Their hot loops make no libc calls, so the comparison is hardware plus
   kernel, not libc. They build unchanged with clang or gcc on aarch64 Linux.
2. **Same LLM workload on both OSes.** llama.cpp runs a bit-identical
   synthetic-weight GGUF produced by `tools/synth_gguf.py` (real
   architecture shapes, random weights). Throughput depends only on shapes and
   quant types.
3. **Environment captured per phase.** `env-<phase>.txt` records the OS
   version, model, load average, power source, energy mode (`pmset`
   `powermode` plus the `system_profiler` description), `pmset -g therm`,
   and compiler versions. No machine identifiers are captured.
4. **Robust statistics.** *Parity tables use medians.* In VMs, preemption of
   the timing thread's vCPU produced impossible STREAM "best" values
   (e.g. 1163 GB/s against a ≈ 370 GB/s median), so best-of-N is unsafe there.
   Original wording: Each test repeats (5–10 runs). We report median
   and min/max (CPU), or best/median/worst (STREAM convention: best). The
   first repetition is dropped where warm-up matters (GPU, STREAM).
5. **Bounded, non-destructive load.** Each test lasts about 1 s per
   repetition, with cooldowns between phases. Storage writes one 8 GiB
   temporary file plus short random-write bursts, then deletes it. Runs
   execute under `caffeinate -i`.
6. **No cross-workload claims.** Results from different benchmark programs
   are not compared, e.g. Metal vs Vulkan GEMM are not compared as "GPU
   parity" unless the kernel and precision match. Where they cannot match,
   the scorecard says so.

## Test catalogue

### CPU (`cpubench`)

| Kernel | What it stresses | Unit |
|---|---|---|
| `fma` | FP32 NEON FMA, C intrinsics: 24 independent 4-wide chains. **Compiler-sensitive** (F-016) | GFLOP/s |
| `fma_asm` | FP32 NEON FMA in fixed inline assembly with rotated source registers. Compiler-independent peak | GFLOP/s |
| `freq` | Dependent 1-cycle ADD chain, so its rate is the core clock in GHz (estimate) | GHz |
| `intmix` | Integer ALU: 8 independent mul/xorshift/rotate chains | Gop/s |
| `sort` | Branchy integer: own quicksort of 256 K uint32 (L2-resident) | Melem/s |
| `sgemm` | Cache-blocked 256³ SGEMM, compiler auto-vectorized | GFLOP/s |
| `sme_f32` / `sme_bf16` / `sme_i8` | SME outer products (FMOPA/BFMOPA/SMOPA) into the 4 ZA tiles; measures the matrix unit | GFLOP/s or Gop/s |
| `pingpong` | Pipe round trip between two threads (wakeup plus 2 context switches) | µs |
| `syscall` | `getppid()` round trip | ns |

**Placement.** On macOS, core-type placement is requested via QoS classes
(`-q ui|default|utility|bg`), the only supported mechanism, and the CPU
number before and after each thread is sampled with `pthread_cpu_number_np`.
CPU numbering: cpu0–11 are "Performance" (ADT cluster type M), cpu12–17 are
"Super" (cluster type P). On Linux, use explicit affinity (`-c` CPU list) and
the same CPU numbering from the device tree.

### Memory (`membench`)

* `stream`: copy/scale/add/triad on 3 × 1 GiB arrays, 1–18 threads, STREAM
  byte counting, best of 9 after warm-up.
* `latency`: random single-cycle pointer chase over 128 B lines, 16 KiB → 2
  GiB. It includes TLB effects of 16 KiB base pages. Linux with 4 KiB vs 16
  KiB pages will differ here, which is itself a finding.
* `fault`: anonymous `mmap` plus first touch of 4 GiB. This measures
  page-fault plus zero-fill throughput and `munmap` cost, which are
  OS-specific.

### Storage (`storbench`)

* Sequential write of 8 GiB in 8 MiB blocks, cache bypassed (`F_NOCACHE` /
  `O_DIRECT`), followed by a full flush (`F_FULLFSYNC` / `fsync`).
* Sequential read with 1 and 4 threads.
* Random 4 KiB read with 1, 8 and 32 threads (≈ QD1/8/32 with synchronous
  I/O): IOPS plus p50/p99/p99.9 latency.
* Random 4 KiB write with 1 and 8 threads for 5 s.

Limitations: macOS has no `io_uring`/libaio equivalent in this harness, so
queue depth equals thread count. FileVault/inline encryption is always active
on macOS. A Linux comparison must state its filesystem (ext4/btrfs) and
encryption (LUKS or none).

### GPU (`gpubench`, Metal)

* FP32 and FP16 FMA peak (8 independent chains per thread, 2.6 M threads).
* Device copy and read bandwidth on 1 GiB buffers, shared vs private storage.
* `MPSMatrixMultiplication` GEMM FP32/FP16, n = 2048/4096/8192.
* `MPSGraph` matmul FP16/BF16/FP32, n = 4096. This is wall time and
  includes submit and sync.
* Empty-dispatch round-trip latency (commit to `waitUntilCompleted`).
* Unified memory: single-thread `memset` into a shared buffer, and the cost of
  the blit that zero-copy avoids.

The Linux counterpart must be a Vulkan compute benchmark with the same
kernels (FMA chains, copy/read bandwidth, GEMM via cooperative matrix where
available). It is planned in `benchmarks/linux/`.

### AI (llama.cpp)

* `llama-bench` with synthetic Llama-3-8B-shaped models at Q4_K_M and Q4_0.
* Metal (`-ngl 99`): pp512, pp2048, tg128. CPU only (`-ngl 0`): 6/12/18
  threads, pp512 and tg64.
* Planned after approval: MLX (`mlx_lm.benchmark`) with real models from the
  user's Hugging Face cache, and Core ML Neural Engine tests (needs
  `coremltools`).

The **Neural Engine is never inferred from GPU or CPU results.** Core ML
runs must pin `computeUnits = .cpuAndNeuralEngine` and still verify ANE
residency (e.g. via `powermetrics`, which needs sudo, or Instruments).
Otherwise the result is labelled "Core ML (unverified unit)".

## Parity computation

Higher is better: `parity = linux / macos × 100%`. Lower is better (latency,
energy): `parity = macos / linux × 100%`. Parity is computed only when the
same benchmark binary or source, the same model file, and the same precision
were used. VM results are reported separately and never counted as native
parity.
