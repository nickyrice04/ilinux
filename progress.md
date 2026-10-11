# Progress Log

Newest first. Each milestone lists: discovered, implemented, tested,
measured, still unsupported, and next.

---

## 2026-10-11 · Session 1: foundations, baselines, VM track, energy

### Discovered

* **Exact hardware:** MacBook Pro Mac17,6 (J716c), **Apple M5 Max = t6050**
  (`chip-id` 0x6050, SoC generation tag "H17", CPU family SOTRA).
  * 6 P ("Super", 16 MiB L2) + 12 M ("Performance", 2 × 8 MiB L2) cores;
    the ADT cluster type is `M`.
  * 40-core G17X GPU, H16-generation ANE (exclave-mediated), 128 GiB,
    2 TB ANS3 SSD.
* **ISA:** SME/SME2/SME2p1 (SVL 512) without non-streaming SVE. MTE present.
* **Linux status for t6050:**
  * No DT and no kernel bring-up. m1n1 has initial T6050 support with no SMP.
    GPU (G17), ANE, ANS3 NVMe, the N1 Wi-Fi chip, DCP and others have no
    Linux drivers.
  * **Asahi forbids generative-AI contributions** (2026-09-08), so this
    project's outputs stay local (D-007).
* **macOS QoS:** background work runs on M cores at ≈ 25% of P-core
  throughput, at **≈ 4× better energy per FLOP**.
* **SME:** one engine per cluster. The P-cluster engine gives 2.17 TFLOP/s
  FP32 (rail `PCPM` ≈ 9.8 W); the chip saturates at 3.23 TFLOP/s.
* **GPU:** FP16 GEMM ≈ 64 TFLOP/s (matrix units) vs 17.6 scalar. Core ML's
  planner prefers the GPU over the ANE on M5 Max.
* **ANE:** 14.0 TFLOP/s FP16 on a 1×1-conv stack at ≈ 3.6 W. Proven by the
  ANE energy counter and MLComputePlan.
* **Microarchitecture:** M5 P-core FMA throughput drops ≈ 11% when all FMLAs
  read the same two source registers (F-016). This explained a fake "112%
  VM parity".
* **Omarchy 4 already supports aarch64 upstream** (edge). Real `pacman` in
  our VM resolves the full default set: 842 packages, 0 unresolved.
* **VM facts:** SME2 is passed through. MIDR is masked. Wakeups cost 21–52 µs
  vs 3.8 µs native. Virtio storage reaches 3–30% of native.

### Implemented

* Benchmarks:
  * `cpubench` (freq, fma, **fma_asm**, intmix, sort, sgemm, SME f32/bf16/i8,
    pingpong, syscall);
  * `membench` (STREAM, latency incl. DIT/DMP-off, faults);
  * `storbench`;
  * Metal `gpubench`;
  * **`powermon`** (no-root IOReport energy and DVFS sampler).
* Model generators: `tools/synth_gguf.py` and `tools/synth_mlx.py`
  (synthetic models with identical shapes for llama.cpp and MLX).
* Analysis helpers: `tools/compare_results.py` (parity tables);
  `hardware/scripts/{adt_extract,ioreg_driver_map,kext_personalities}.py`.
* **VM track:**
  * `virtualization/vzrun` (Virtualization.framework runner: direct kernel or
    EFI boot, virtiofs, NAT, nested, NVMe and disk-mode options);
  * GPG-verified Arch Linux ARM image build;
  * the scripted job runner.
* **omarchy-qos** (QoS tiers via systemd slices, cpuset, uclamp), VM-tested
  and with one bug fixed.
* **Draft t6050 DT** (CPUs, AIC3, timer, WDT, 3 × pinctrl, 9 × I2C, UART),
  compile-checked with a workspace-built `dtc` 1.8.1. Local only.
* REA 6.4.0, project-local (`tools/rea`, `.mcp.json` and deny-list settings in
  `~/Documents/iLinux`). MLX, mlx-lm and coremltools in `tools/venv`.

### Tested and measured (highlights; see `reports/performance-parity.md`)

| What | Result |
|---|---|
| macOS CPU, 1 P core / 18 cores (asm FMA) | 140.8 GFLOP/s / 1.89 TFLOP/s |
| macOS SME f32, 1 thread / chip | 2.17 / 3.23 TFLOP/s |
| macOS STREAM, 18 threads (median) | ≈ 369 GB/s copy |
| macOS GPU FP16 GEMM / copy bandwidth | 64 TFLOP/s / 537 GB/s |
| macOS SSD seq read / write | 11.0 (13.3 at 4 threads) / 11.2 GB/s |
| llama.cpp Metal 8B Q4_0 | pp512 3090 t/s, tg128 105 t/s, ≈ 0.56 J/token |
| MLX 8B 4-bit / Gemma-3-12B bf16 | tg 100.8 / 21.7 t/s |
| ANE (Core ML conv stack) | 14.0 TFLOP/s at ≈ 3.6 W |
| **Linux VM vs macOS** (identical code and flags) | CPU compute 97–101%, SME 97–100%, STREAM 93–100%, DRAM latency 72–84%, syscalls 77%, wakeups 7%, storage 3–57% |
| omarchy-qos in VM | 5/5 pass; uclamp skipped (no `CONFIG_UCLAMP_TASK_GROUP` in the ALARM kernel) |

### Still unsupported or blocked

* Native Linux on t6050 (B-001), GPU (B-002), ANE (B-003), NVMe (B-004),
  Wi-Fi (B-012).
* GPU acceleration inside VMs needs host installs such as krunkit (new
  approval).
* No Linux-side energy counters yet.
* Strict BLAS-free llama.cpp prefill comparison on macOS needs `cmake`
  (not installed).

### Next

1. Finish the VM llama.cpp CPU comparison (job 003) and the VZ storage-mode
   matrix (job 005, `virtualization/scripts/run-storage-matrix.sh`).
2. Build a guest kernel config with `CONFIG_UCLAMP_TASK_GROUP` (and possibly
   16K pages) to test omarchy-qos clamps and the VM memory overheads.
3. Omarchy VM install: keyring, `omarchy-arm64-vm` integration package,
   Hyprland on llvmpipe smoke test.
4. Propose GPU-in-VM experiments (krunkit/Venus; llama.cpp API remoting) to
   the user for approval.
5. Decode the PMGR `devices`/`ps-regs` tables to extend the DT draft with
   power domains (local research).
