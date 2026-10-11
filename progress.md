# Progress Log

Newest first. Each milestone lists: discovered, implemented, tested,
measured, still unsupported, and next.

---

## 2026-10-11 · Session 1: foundations, baseline, enablement research

### Discovered

* **Exact hardware:** MacBook Pro Mac17,6 (J716c), **Apple M5 Max = t6050**
  (`chip-id` 0x6050, SoC generation tag "H17", CPU family SOTRA).
  * 18 cores: 6 P ("Super", 16 MiB L2) + 12 M ("Performance", 2 × 8 MiB L2).
    No E cores. The new ADT cluster type is `M`.
  * 40-core G17X GPU, 128 GiB, 2 TB SSD (ANS3).
  * macOS 26.6.2, firmware 18000.161.10.
  * Details: `hardware/hardware-inventory.md`.
* **ISA:** SME/SME2/SME2p1 with SVL 512 but **no non-streaming SVE**
  (`-march=armv9` binaries SIGILL). MTE/MTE2/MTE4 present.
* **Linux support for t6050: none.**
  * Mainline DTs stop at M3. Asahi has a *minimal* M4 (t8132) DT from
    2026-07, and nothing for M4 Pro/Max or M5.
  * Driver-level checks against source code:
    * AIC3 and DART t8110 drivers exist and are likely compatible.
    * NVMe ANS3 and SART "CoastGuard" are unsupported.
    * The GPU driver stops at M2 (G14). The M5 GPU is G17.
    * The ANE is exclave-mediated (`ane,t8132exclave`).
  * Matrix: `reports/compatibility-matrix.md`.
* **Linux kernel already supports "SME-only" CPUs** (SME without SVE), which
  is what M4/M5 are, per mainline commits from 2023–2026.
* **macOS QoS behaviour (measured):**
  * Background QoS runs on the M cores at ≈ 23–36% of P-core throughput
    (≈ 9% for SME).
  * ui, default and utility QoS run on P cores.
* **SME units are per cluster.** One P-cluster engine gives ≈ 2.17 TFLOP/s
  FP32. The whole chip saturates at ≈ 3.23 TFLOP/s FP32 or ≈ 6.46 TOPS INT8.
* **GPU matrix hardware:** Metal FP16 GEMM ≈ 64 TFLOP/s vs 17.6 TFLOP/s
  scalar FP16 FMA peak. A Linux driver lacking the matrix units would be
  ~3.6× slower on prefill-type work even with everything else working.
* **REA** (`morluto/rea`, npm `rea-agents` 6.4.0): its setup writes
  *global* Claude config. A project-scoped plan is ready
  (`research/rea/rea-analysis.md`) and awaits approval.

### Implemented

* Workspace, continuity docs, `.gitignore`.
* Portable benchmarks: `cpubench` (FMA, int, sort, SGEMM, SME
  f32/bf16/i8, pipe ping-pong, syscall, clock estimate), `membench`
  (STREAM, latency incl. DIT/DMP-off mode, page faults), `storbench`
  (cache-bypassed sequential/random I/O).
* Metal `gpubench` (FMA, bandwidth, MPS/MPSGraph GEMM, dispatch latency,
  unified memory).
* `tools/synth_gguf.py`: synthetic-weight GGUF models (validated: loads and
  runs in llama.cpp b10280).
* `hardware/scripts/adt_extract.py` (sanitized ADT) and
  `ioreg_driver_map.py`.
* `virtualization/vzrun`: Virtualization.framework VM runner (EFI or direct
  kernel boot, virtiofs, NAT, GUI or serial).
* `omarchy-arm64/configuration/qos-tiers`: **omarchy-qos**, macOS-style QoS
  tiers for Linux (uclamp, cpuset, systemd slices), with a VM test.
* `kernel/experiments/t6050-dt`: generator plus **draft minimal t6050 DT**
  (CPUs, AIC3, timer, WDT, pinctrl ×3, I2C ×9, UART).

### Tested

* All benchmarks built and smoke-tested on macOS. Full baseline run
  `benchmarks/results/macos-2026-10-11-ac-lpm/`, on AC with macOS reporting
  "Low Power Mode: Yes" for AC.
* The ADT sanitizer was verified to leak no identifier values (an early
  `die-id` leak was caught and fixed).
* `omarchy-qos` and the installer pass `bash -n` only. The VM functional test
  is pending.
* The DT draft compile check with `dtc` is pending.

### Measured (macOS reference, highlights; full table in `reports/performance-parity.md`)

| Metric | Value |
|---|---|
| FP32 FMA, 1 P core / 18 cores | 124.6 / 1623 GFLOP/s |
| SME FP32, 1 thread / chip | 2.17 / 3.23 TFLOP/s |
| STREAM copy, 1 thread / 18 threads | 140 / 377 GB/s |
| DRAM latency (2 GiB chase, DMP on) | ≈ 112 ns |
| GPU FP32 FMA / FP16 GEMM | 14.8 / 63.9 TFLOP/s |
| GPU copy bandwidth | ≈ 537 GB/s |
| SSD sequential read / write | 11.0 (13.3 with 4 threads) / 11.2 GB/s |
| SSD 4K random read QD1 / QD32 | 17.4 K / 253 K IOPS |
| llama.cpp synthetic Llama-3-8B Q4_K_M (Metal) | pp512 ≈ 2909 t/s, tg128 ≈ 98.6 t/s |

### Still unsupported or blocked

* Native Linux of any kind on t6050 (B-001).
* GPU (B-002) and ANE (B-003).
* Power measurement needs sudo (B-008).
* Approvals pending: VM images and Docker (B-005), REA (B-006), MLX and
  coremltools (B-007).

### Next

1. Get the approvals listed in `blockers.md`.
2. Build the Arch Linux ARM VM. Run the same benchmarks in it for VM overhead
   and check SME exposure and MIDR.
3. Port Omarchy installer to ARM64 per `research/omarchy/` and test package
   resolution and Hyprland in the VM.
4. Compile-check the t6050 DT with `dtc`. Decode PMGR power-domain tables.
5. Install REA project-locally (if approved) and run interface-level
   research on ANS3, SART, AIC rev 11 and GPU firmware interfaces, within the
   clean-room policy.
