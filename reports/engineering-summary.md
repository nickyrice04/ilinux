# Engineering Summary: Session 1 (2026-10-11)

## Bottom line

* **Native Linux on this M5 Max (t6050) is not possible today.**
  * m1n1 has initial T6050 support, but secondary CPUs never start.
  * No device tree or kernel bring-up exists.
  * The GPU (G17), Neural Engine (exclave-mediated, H16), NVMe (ANS3 with
    CoastGuard/SARTv4) and the Apple N1 wireless chip have no Linux drivers.
  * Native parity is therefore **unsupported, not slow**.
* **Linux in a VM on the same machine is close to native for CPU work.**
  With identical code and flags, CPU compute runs at 97–101% and the SME
  matrix unit at 97–100% (SME2 is passed through to guests). Memory
  bandwidth is 93–100%.
* **The VM's costs are in exits.** Thread wakeups run at 7%, syscalls at 77%,
  page faults at 35%, and virtio storage at 3–57% of native.
* **The VM has no GPU.** Virtualization.framework gives Linux 2D graphics
  only.
* **macOS's advantages are now quantified:**
  * GPU matrix units: FP16 GEMM 64 TFLOP/s vs 17.6 TFLOP/s scalar FP16.
  * The ANE: 14 TFLOP/s at ≈ 3.6 W.
  * QoS-driven placement: background work on M cores at ≈ 4× better energy
    per FLOP.

  Closing these gaps on Linux needs drivers that don't exist yet: AGX G17,
  ANE, cpufreq/EAS for t6050.
* **Omarchy:** upstream already supports aarch64 (edge channel). The full
  default package set resolves on Arch Linux ARM plus Omarchy's repo
  (842 packages, 0 unresolved, verified with real pacman in our VM).

## Deliverables

| Area | Deliverable | State |
|---|---|---|
| Hardware | Inventory; sanitized ADT (656 nodes); driver and kext maps | Done |
| Benchmarks | Portable CPU/SME/memory/storage suite; Metal GPU; synthetic GGUF/MLX models; parity comparator | Done; macOS baseline and VM run complete |
| Energy | `powermon`: no-root IOReport energy and DVFS sampler | Done; perf-per-watt measured |
| AI | llama.cpp, MLX and Core ML (ANE/GPU/CPU) baselines with energy | Done |
| VM | `vzrun` + verified ALARM image + job runner | Done; 6 jobs run |
| Scheduling | `omarchy-qos` (macOS-style QoS tiers) | VM functional test 5/5; uclamp needs a kernel config change |
| Kernel | Draft minimal t6050 DT, `dtc`-checked | Draft. Local only (Asahi AI policy) |
| Omarchy | ARM64 analysis, real resolution test, patch plan | Analysis done; patches planned |
| Research | Asahi status, REA analysis, Omarchy analysis, findings catalog (F-001 to F-016) | Done |
| REA | Installed project-locally (metadata tools; no decompiler) | Ready; MCP tools load in the next session |

## Key decisions

* **D-007:** no Asahi contributions from this AI-driven project.
* **D-008:** VM approach (vzrun + ALARM via Docker build).
* **D-009:** identical compiler targets. F-016 showed why the compiler
  version also matters.

## Recommended next priorities

1. VZ storage-mode matrix (job 005) to close the virtio storage gap.
2. Guest kernel with uclamp and 16K pages, to test omarchy-qos clamps and
   reduce stage-2 overheads.
3. Omarchy VM install with the `omarchy-arm64-vm` integration package.
4. GPU-in-VM (krunkit/Venus, llama.cpp API remoting). **Needs approval** for
   host installs.
5. PMGR table decoding for DT power domains (local research). Track m1n1
   T6050 SMP progress upstream.
