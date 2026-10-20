# Roadmap

Ordered by the mission's prioritization rules: enablement dependencies first,
then feasibility, impact, evidence, safe testability, reuse and
maintainability. Status: ✅ done · 🔄 in progress · ⏳ blocked or awaiting
approval · ⬜ not started.

## Current direction — after native attempt 27, 2026-10-20

**Omarchy boots natively with USB/SSH and automatic keyboard startup.**
Two-stage delivery works; the user can type without extra letters but menus
and applications remain slow. One CPU, software graphics and a RAM root remain.
The current [workstation plan](native/boot/post-attempt27-plan-2026-10-20.md)
supersedes the historical attempt assignments below.

1. Prepare the separate CPU baseline/bounded-frequency experiment, proposed
   for attempt 28. The module passed offline tests; integration, exact paired
   images, measurement runner and independent M1 intake still precede a restart.
2. Resolve one-secondary entry, then cross-cluster/all-18-core operation,
   scheduling, telemetry and idle/thermal behavior. Measure desktop latency
   alongside CPU progress; CPU count is not a substitute for graphics work.
3. Continue N1 PCIe/DART/ACIPC research toward independent Wi-Fi and a browser,
   and rebase the read-only ANS experiment for two-stage delivery. Later native
   ordering follows readiness/results; do not hold ready work for full CPU parity.
4. Establish persistent Linux storage and matched CPU, networking, SSD and
   energy measurements before moving the user's main REA workflow into Omarchy.
   Access to existing encrypted macOS files is a separate dependency.

No new live attempt or launcher allowance is ready/authorized by this plan.
Attempt 27 is consumed. Keep the current entry and routine policy-check waiver.

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

Historical path, recorded 2026-10-15 after attempt 15; the current direction
above supersedes its attempt/status assignments. Native Linux reached diagnostic PID 1 on
one CPU (attempts 14–15). Attempt 14 reset 5.6 s after genpd's bulk power-off;
boot034 removed that and ran ≥ 27.6 s, then reset 5.7 s after releasing the
last of the SMC-owned `smc_i2cm` domains, which no Asahi device tree exposes.
Boot035 drops those seven domains from the Stage-B DT (one variable). See
`native/boot/attempt15-review-2026-10-15.md`. Each step below is a separate,
human-started RAM session.

### Path to a native Omarchy boot

| Order | Milestone | What it needs | Evidence to advance | Status |
|---|---|---|---|---|
| 1 | **Stable native baseline** (boot035 / attempt 16) | DT without SMC domains; the boot034 ladder releases the other 145 unclaimed domains | `ladder complete` and heartbeats to 180 s | ✅ attempt 16: ladder complete (74 domains), alive past 108 s |
| 2 | **Control channel into Linux** | USB device-mode networking over the M1 cable. boot036 (`kernel/experiments/usb-gadget/`): gadget stack built in; three dwc3 device-mode cores on the PHY state m1n1 leaves (ATC 0–2 domains disabled); a CDC-EEM gadget (bulk only; the ports flag `ncm-interrupt-ep-disabled`) with IPv6 link-local and key-only SSH | The M1 sees a USB network interface; ping and SSH into Linux | 🔄 attempt 17: Linux USB works on the M5, macOS lacks EEM; attempt 18 (ACM + ECM): control-endpoint timeouts; attempt 21 (boot039, bulk-only `gser`): EP0 healthy for 10 min, macOS publishes the interface, the M1's reader streams 36,909 bytes, then a dwc3 `BUSERR` and an unhandled DART interrupt stall it; attempt 23 (boot040): the DART is v2.4 and the fault sits on the instance the DT left out; ✅ **attempt 24 (boot041)**: both DART instances per controller, the USB log streams from the M5 to the M1 for ten minutes with no fault; 🔄 the M1 to M5 direction and SSH in attempt 25; SSH + web over the bulk pipe VM-proven (job 046) |
| 3 | **RAM root with a real Arch userspace** | Arch Linux ARM packages in a zstd initramfs delivered by the proxy (≈ 4–5 MB/s observed; 126 GiB RAM), init that starts sshd on the USB link; 16K-page-safe packages | Login and the Linux-side agent reachable over the link | 🔄 attempt 25 handoff ready: Omarchy's own root with the SSH link, the clock step and the M1's web relay |
| 4 | **Visual Omarchy boot.** *Omarchy* means: built by Omarchy's own installer from Omarchy's repositories and running Omarchy's own session (SDDM → uwsm → Hyprland → Quickshell, its menu and first run), with deviations only where the M5's hardware forces them (our kernel and DT instead of Omarchy's, no bootloader, packages for absent hardware). Anything less is *Omarchy-style* | Hyprland on `simpledrm` (built in) with Mesa llvmpipe, one CPU, in a RAM root; proven first in the VM. For Omarchy itself: the edge aarch64 ISO's runtime installed phase by phase (VM job 045, a 2.34 GB image) and a way to deliver it (a larger launcher heap and deadline, or two stages over the USB link) | Omarchy's own desktop on the M5 screen | 🔄 Omarchy-style ✅ attempt 19 (2026-10-16): desktop up, view-only, one CPU, software rendering; ✅ attempt 20: ten stable minutes with a live status screen and on-screen benchmarks (job 039: hand-picked packages, our own session). Omarchy ✅ VM only (job 045, 2026-10-17: Omarchy's session, first run, menu, Chromium and Obsidian on the boot035 Image; `omarchy-arm64/omarchy-root-report-2026-10-17.md`); ✅ **native, attempt 22 (2026-10-18)**: the job 045 root on boot035 with the launcher's `omarchy` profile, desktop about 40 s after the handoff, ten stable minutes, view-only; 🔄 attempt 25: the same root with the link, Claude Code and passwordless sudo, so agents run inside it |
| 5 | SMP, idle/DVFS, thermal | Existing REA startup findings; secondary bring-up; cpuidle/cpufreq | Stable all-core operation | ⬜ |
| 6 | Input, storage, wireless, GPU | MTP keyboard/trackpad (DockChannel): 🔄 keyboard, attempt 26 (boot042, 2026-10-19) loads the keyboard path as modules from the SSH session (NOT RUN); NVMe (patches 0004–0005): read-only storage is attempt 27, behind a reviewed launcher change; Wi-Fi, G17 GPU (no Linux driver) | Per device, measured | ⬜ |

Parallel tracks that need no Linux boot: the PMGR probe can confirm the SMC
mechanism per domain in minutes (`tools/m1n1-client/pmgr-probe-instructions.md`),
and the hv003 ladder (`tools/m1n1-client/hv-instructions.md`) is the tracing
tool if a reset ever needs register-level evidence.

## Phase 4 — Performance engineering on native Linux

Iterate per subsystem with the Observe → Investigate → Compare → Design →
Implement → Test → Benchmark → Iterate loop, scored in
`reports/performance-parity.md`.

For this exact M5, native userspace and the USB/SSH control channel now work.
Current priorities are full CPU capability/efficiency, independent built-in
Wi-Fi and persistent SSD access, with graphics latency measured alongside them.
G17 graphics/display acceleration remains important to interactive performance
and energy. Other hardware follows the user's workstation acceptance targets.
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
