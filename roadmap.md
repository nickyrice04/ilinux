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

Update, 2026-10-13: REA/Ghidra is operational in the isolated Linux lab
(F-070–F-077). CPU startup/idle and driver-interface findings already exist.
Use them against a specific observed native failure; broad repeated binary
survey is not the next dependency. No proprietary code is copied into Linux.

## Phase 3 — Native deployment (separate explicit authorization required)

The dedicated lab entry and Stage A handshake/return are established.
Attempt 5 reached native early Linux and identified an AIC guest-timer register
write failure. Boot025 implements a restricted t6050 path, with full build,
actual-driver tests and generic VM liveness passed. Native boot025 remains
NOT RUN. Fresh post-attempt-5 policy JSON keeps original Full/lab Permissive.

| Order | Next experiment | Evidence required before advancing |
|---|---|---|
| 1 | One human-started attempt 6 with boot025 restricted AIC handling; installed m1n1 stays boot021, single core, Linux NVMe/cpufreq disabled | Record the screen before launch: AIC profile/final Initialized, timer progress, PID 1, one CPU, 60-second liveness, then original macOS return. Use `tools/m1n1-client/stage-b-instructions.md` |
| 2 | Diagnose the earliest actual failure, or improve logging if screen output is absent | A reproducible checkpoint and tested patch; no blind retry or guessed driver diagnosis |
| 3 | Establish Linux-side USB/input and an observable control channel | Linux USB enumeration and tested input/network access. The working m1n1 USB proxy does not survive Linux handoff |
| 4 | Separate bounded SMP/idle/DVFS experiments, informed by existing REA startup findings | Correct core identities/topology, stable incremental secondary startup, validated idle/wake and frequency transitions; no assumed masks or OPP values |
| 5 | Storage access and persistent Linux environment under a separately approved storage plan | Read-only identification first; stable storage/input/access and preservation of macOS volumes. Only then configure native Omarchy via `native/handoff/` |
| 6 | G17 GPU/DCP, media, N1 wireless, audio/camera/ANE enablement | Per-device transport/firmware evidence and isolated driver tests, followed by measured physical behavior |

Orders 3–4 can share offline research while physical tests remain separate.
Stage A approval covered only that completed session; Stage B and later
experiments require their own scope. No new boot-policy change is needed for
the proposed Stage B test. The configuration agent can prepare packages now,
but cannot run inside the current shell-less/network-less RAM diagnostic.

## Phase 4 — Performance engineering on native Linux

Iterate per subsystem with the Observe → Investigate → Compare → Design →
Implement → Test → Benchmark → Iterate loop, scored in
`reports/performance-parity.md`.

For this exact M5, the largest remaining native gaps are (1) stable Linux
userspace and usable access, (2) all-core operation plus safe idle/DVFS and
thermal control, and (3) native G17 graphics/display/media acceleration.
Stage B deliberately uses `idle=nop`, one CPU and no cpufreq: it tests liveness,
not efficiency. Removing those restrictions requires independent evidence.
The [current Asahi M5 table](https://asahilinux.org/docs/platform/feature-support/m5/)
still lists t6050 GPU, cpufreq, cpuidle, DCP and USB support TBA (checked
2026-10-13); our private prototypes need physical validation, not an installer toggle.

Before claiming parity, repeat matched macOS/native Linux workloads on the
same machine, with recorded build/compiler/kernel/DT, power mode/source,
brightness/resolution, thermal starting state and run count. Report throughput
and latency together with energy per completed task, idle watts and sustained
thermal behavior. Keep measurement boundaries comparable (whole-machine power
versus modeled component counters are different quantities). Record uncertainty
and missing devices explicitly. VM results and a successful boot cannot stand
in for native performance or battery-life results.
