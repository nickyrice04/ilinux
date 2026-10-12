# Engineering Summary: Session 2 (2026-10-12)

## Bottom line

* **Omarchy 4 runs as a GPU-accelerated desktop on this Mac today**, in a
  QEMU/HVF VM built entirely in the workspace (`virtualization/qemu/`,
  `Omarchy.app`). Native Linux on t6050 is still blocked (see session 1);
  a draft native patch series compile-tests clean.
* **GPU:** Hyprland runs through VirGL into macOS OpenGL 4.1 (Metal) at
  Retina resolution and 120 Hz. Against macOS's own GL:

  | Test | Parity |
  |---|---|
  | Shader ALU | 99.7–100% |
  | Blended fill | 74% (was 17%) |
  | Readback | 61% (was 23%) |
  | Draw calls | 50% |
  | Texture upload | 28% |

  The fill and readback gains came from replacing 1 ms fence polling with
  event-driven fences. LLM compute from Linux goes through ggml RPC: 81–89%
  of native Metal.
* **CPU:**
  * Foreground single-thread is 99% of native.
  * Heterogeneous vCPUs mirror the M5 Max (Super + M clusters). Guest
    background work runs on host M cores and gets 1.84–2.25× the work per
    joule (`omarchy-qos` tiers map onto them automatically).
  * App Nap `auto` keeps a hidden VM fast when it's busy and napping when
    it's idle.
* **Battery:**
  * An idle Omarchy desktop costs +0.09 W of SoC power.
  * Idle QEMU CPU is down 45% (adaptive display refresh).
  * The guest shows the Mac's battery, and its clock stays right after the
    Mac sleeps.
* **Storage:** warm small reads at native latency. Random-I/O scaling
  doubled with an iothread. Cold sequential reads reach 100% with the new
  F_NOCACHE mode. fsync-heavy writes are still 22% (btrfs dependent-I/O
  chains in a VM).
* **Experience:**
  * clipboard shared both ways;
  * microphone capture added to QEMU's CoreAudio backend;
  * Mac time zone followed;
  * full-screen Space and full keyboard grab available;
  * fixed an upstream Omarchy/Qt 6.12 bug that left the bar black;
  * kernel packaged for pacman, so updates are clean.

## Needs the user

* **First launch of `Omarchy.app`:** right-click → Open (it's locally
  built and ad-hoc signed).
* **Optional permissions:** microphone (first recording), and Accessibility
  for `--full-grab`.
* **Next large step:** Vulkan in the guest (Venus with MoltenVK or
  KosmicKrisp). This needs new third-party source downloads and builds.

---

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
* **The VM's costs are in exits.** Thread wakeups run at 7%, syscalls at 77%
  and page faults at 35% of native.
* **VM storage is tunable.** The best durable mode (virtio + fsync) reads at
  51–65% of native. The initial 3% write figure was sparse-image first-write
  allocation (F-018).
* **llama.cpp CPU inference in the Linux VM matches or beats macOS's
  Homebrew build.** Q4_0 generation runs at 92–100%. Q4_K_M prefill is
  ≈ 2.1× faster, because macOS routes it through Accelerate (F-017).
  CPU-side LLM parity is achievable on Linux.
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

1. Make `fsync` the default root-disk mode in `vzrun`, plus a pre-allocation
   option. Re-measure the VM storage parity.
2. Guest kernel with uclamp and 16K pages, to test omarchy-qos clamps and
   reduce stage-2 overheads.
3. Omarchy VM install with the `omarchy-arm64-vm` integration package.
4. GPU-in-VM (krunkit/Venus, llama.cpp API remoting). **Needs approval** for
   host installs.
5. PMGR table decoding for DT power domains (local research). Track m1n1
   T6050 SMP progress upstream.
