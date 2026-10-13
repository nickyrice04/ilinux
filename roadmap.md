# Roadmap

Ordered by the mission's prioritization rules: enablement dependencies first,
then feasibility, impact, evidence, safe testability, reuse and
maintainability. Status: ✅ done · 🔄 in progress · ⏳ blocked or awaiting
approval · ⬜ not started.

## Phase 0 — Foundations (session 1)

| # | Item | Status |
|---|---|---|
| 0.1 | Exact hardware inventory plus sanitized device-tree capture | ✅ |
| 0.2 | Workspace, continuity docs, git repo | ✅ |
| 0.3 | Portable benchmark suite (CPU/SME, memory, storage) plus Metal GPU benchmark plus synthetic GGUF tool | ✅ |
| 0.4 | macOS baseline run (AC; energy mode recorded) | ✅ |
| 0.5 | Research: Asahi status for t6050, REA analysis, Omarchy ARM64 analysis | ✅ |
| 0.6 | Compatibility matrix v1 (ADT block → mainline/Asahi driver → status) | ✅ |

## Phase 1 — Linux in isolated environments (approved 2026-10-11: vzrun VM, REA project-local, MLX venv)

| # | Item | Why |
|---|---|---|
| 1.1 | ✅ `vzrun` built (ad-hoc signed) and booting a GPG-verified Arch Linux ARM image with scripted jobs | Layer 3 test bed without host installs |
| 1.2 | Run the identical C benchmarks in the VM | Quantify VM overhead (CPU, memory, storage) vs macOS. Expected near-native CPU; VM results are never "native parity" |
| 1.3 | ✅ SME2 is exposed to VZ guests (SVL 512). In-guest `sme_*` throughput ≈ 98–99% of macOS | Matrix-unit parity for CPU inference on Linux |
| 1.4 | Arch Linux ARM container or VM: resolve Omarchy package set on aarch64 (`pacman -Sp`) | Ground-truth package availability |
| 1.5 | Omarchy-arm64 installer branch: arch guards, package substitutions, bootloader abstraction | Target userspace |
| 1.6 | Hyprland in VM (virtio-gpu, software GL) smoke test | Desktop integration without GPU acceleration |
| 1.7 | ✅ QEMU/VirGL graphics, Venus/MoltenVK compute and ggml RPC implemented in the existing workspace/VM | Measured results in `reports/vm-vs-macos-parity.md`; no new host install needed for this path |
| 1.8 | ✅ Separate Mesa VA package: lossless NV12/I420/YV12 downloads and optional NV12 H.264 decode | 18 image cases pass; QEMU decode CPU cost reduced 41.3%; see `reports/video-download-and-nv12-2026-10-12.md` |

## Phase 2 — Native enablement research for t6050 (no hardware writes)

| # | Item | Notes |
|---|---|---|
| 2.1 | Per-block gap analysis: AIC3, DART t8110, ANS3 NVMe and SART "coastguard", ASC wrapper v6 / mailbox, PMGR, cpufreq, ATC/USB, DCP, MTP | Builds on compatibility matrix v1 |
| 2.2 | Draft `t6050.dtsi` / `t6050-j716c.dts` skeleton from the sanitized ADT (CPU topology, AIC3, DARTs, PMGR, UART, WDT, I2C, GPIO) | Static, reviewable; boot-testing needs native hardware and m1n1 support |
| 2.3 | CPU scheduling design for M+P clusters: EAS capacities from measured per-cluster throughput, uclamp/cgroup "QoS tiers" that mimic macOS placement | Measured macOS behaviour: background QoS → M cores at about 25% speed |
| 2.4 | GPU: track Asahi AGX (G13–G15 supported; G16/G17 not). Document the G17 matrix-unit gap | Metal FP16 GEMM ≈ 64 TFLOPS vs ≈ 17.6 TFLOPS scalar FP16 FMA |
| 2.5 | ANE: document the exclave-mediated design (`ane,t8132exclave`) and what Linux would need | Likely the hardest block |
| 2.6 | 🔄 User-authorized local REA/binary analysis for focused implementation questions; artifact identity, confidence and independent experiments recorded | Metadata and supplemental LLVM ARM64 analysis completed; REA decompilation backend unavailable. Original local implementations; no proprietary code copied |

## Phase 3 — Native deployment (separate explicit authorization required)

Only after the independently maintained boot chain and kernel patches pass
the required pre-boot checks; upstream acceptance is not a prerequisite.
A deployment plan covering backup, APFS resize, stub
macOS, boot policy, recovery and rollback will be written first. **Nothing
here proceeds without explicit user approval.**

## Phase 4 — Performance engineering on native Linux

Iterate per subsystem with the Observe → Investigate → Compare → Design →
Implement → Test → Benchmark → Iterate loop, scored in
`reports/performance-parity.md`.
