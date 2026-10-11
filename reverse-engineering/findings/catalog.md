# Research Findings Catalog

The mission's REA research database. One entry per engineering-relevant
finding.

Confidence: **Confirmed / Likely / Hypothesis / Unknown**.

Method tags:
* `ADT`: sanitized Apple Device Tree from `ioreg`
* `IOReg`: IORegistry class names
* `SRC`: open-source code (Linux, Asahi, XNU)
* `BENCH`: our measurements
* `REA`: REA tool output (none yet; REA is not installed)

No entry is based on decompiled Apple code.

---

## F-001 · CPU · Cluster topology and core types (t6050)

| Field | Value |
|---|---|
| Question | What CPU topology must a Linux DT describe? |
| Source | `ADT` `/cpus/*`; `sysctl hw.perflevel*` |
| Observation | 3 clusters × 6 cores. Clusters 0 and 1 have `cluster-type` **M** (`apple,sawtooth`, MPIDR aff 0x000–0x005 and 0x100–0x105, 8 MiB L2 each). Cluster 2 has type **P** (`apple,everest`, 0x200–0x205, 16 MiB L2). macOS names them "Performance" and "Super". |
| Inference | A new third core class letter `M` appears where earlier SoCs had `E`. ADT `reg` holds affinity bits. The true MPIDR may carry extra Aff2 bits, as Asahi's M4 DT uses `cpu@10100` for P cores. m1n1 must read the real MPIDR. |
| Confidence | Observation **Confirmed**; MPIDR encoding **Hypothesis** |
| Linux mapping | `cpus` and `cpu-map` DT nodes, `capacity-dmips-mhz`, `apple-soc-cpufreq` cluster nodes |
| Implementation | Draft `t6050.dtsi` CPU section from the ADT (see `kernel/experiments/`) |
| Validation | Native boot only. A VM can't present this topology. |
| Result | n/a |

## F-002 · CPU scheduling · QoS class determines core type *and* frequency

| Field | Value |
|---|---|
| Question | How does macOS place work on M vs P cores? |
| Source | `BENCH` `cpubench -q {ui,default,utility,bg}` with `pthread_cpu_number_np` sampling |
| Observation | Single-threaded `ui`, `default` and `utility` threads ran on CPUs 12–17 (P/"Super"). `background` threads ran on CPUs 6–10 (M) at **≈26% FMA, ≈24% integer, ≈36% sort, ≈23% SGEMM and ≈9% SME** of the P-core result. |
| Inference | XNU and CLPC tie `background` QoS both to the M clusters and to a low frequency or power cap. This isn't a plain "small core" effect, because M cores at full clock are far faster (see multi-thread data). |
| Confidence | **Confirmed** (measured, 5 reps, AC power). Frequency-cap mechanism **Likely**, since cycle counters can't be read without root. |
| Linux mapping | EAS plus `schedutil`; per-task `uclamp.max` (`sched_setattr`); cgroup v2 `cpu.uclamp.max` and `cpuset.cpus` |
| Implementation | "QoS tiers" for Omarchy: systemd slices for background, utility and interactive, with `AllowedCPUs` and uclamp caps, plus a small CLI to tag processes |
| Validation | Functional test in a VM (cgroup and uclamp semantics). Placement and energy effects need native hardware. |
| Result | Pending |

## F-003 · CPU / AI · SME units are shared per cluster

| Field | Value |
|---|---|
| Question | How does matrix (SME) throughput scale with threads? |
| Source | `BENCH` `cpubench sme_{f32,bf16,i8} -t N` |
| Observation | FP32 FMOPA: 1 thread ≈ **2.17 TFLOP/s**, 6 threads ≈ 3.17, 12 threads ≈ 3.22. BF16 widening gives the same FLOP rate as FP32. INT8 gives about 2× (≈4.3 TOPS single thread, ≈6.3 TOPS with 6 threads). |
| Inference | One SME engine per cluster, shared by its cores. Extra threads mostly time-slice. The P-cluster engine is much stronger than the M-cluster engines. |
| Confidence | **Confirmed** scaling; per-cluster attribution **Likely** |
| Linux mapping | Mainline arm64 supports "SME-only" systems (commits `0269680e5eb8`, `472800cd5e38`, kselftests 2025–2026). Userspace: llama.cpp KleidiAI SME2 kernels, OpenBLAS/ArmPL SME. |
| Implementation | Thread placement for SME-heavy work: one thread per cluster |
| Validation | Run `cpubench sme_*` inside a Linux VM: does Hypervisor.framework expose SME? Natively later. |
| Result | macOS baseline recorded |

## F-004 · GPU · Matrix ("Neural Accelerator") throughput

| Field | Value |
|---|---|
| Question | How large is the GPU matrix-unit advantage that Linux must match? |
| Source | `BENCH` `gpubench` (MPSMatrixMultiplication, MPSGraph, FMA kernels); `IOReg` `AGXAcceleratorG17X`; llama.cpp Metal reports "has tensor = true" |
| Observation | FP16 GEMM **≈63.7 TFLOP/s** vs FP16 scalar FMA peak ≈17.6 and FP32 GEMM ≈14.8 TFLOP/s. |
| Inference | The FP16 matrix path uses dedicated per-core matrix hardware exposed through Metal 4 tensor APIs and MPS. |
| Confidence | Throughput **Confirmed**; hardware attribution **Likely** |
| Linux mapping | Asahi DRM driver plus Mesa (`asahi` / Honeykrisp). No G15+ support (driver matches t8103/t8112/t600x/t602x only). Vulkan exposure would be `VK_KHR_cooperative_matrix`. |
| Implementation | None possible yet; needs ISA documentation from reverse engineering under the clean-room policy. |
| Validation | Native only |
| Result | Gap = unsupported (not "slow") |

## F-005 · ANE · Exclave-mediated Neural Engine

| Field | Value |
|---|---|
| Question | Can a Linux kernel drive the M5 Max ANE? |
| Source | `ADT` `ane0` `compatible = ane,t8132exclave` with `dart-ane0` and `exclave-sid` property; `IOReg` `ANEExclaveProxy`, `H11ANEIn`, `AppleT6050ANEHAL` |
| Observation | macOS routes ANE control through an exclave proxy. The DART has an `exclave-sid` property. |
| Inference | On macOS, a secure domain owns the ANE command path. Whether the MMIO is reachable from a normal-world kernel booted by m1n1 is unknown. |
| Confidence | Observation **Confirmed**; feasibility **Unknown** |
| Linux mapping | No upstream driver. Asahi's experimental ANE work targeted older generations (see the Asahi report). |
| Implementation | None now |
| Validation | Native only |
| Result | n/a |

## F-006 · IRQ · AIC v3

| Field | Value |
|---|---|
| Source | `ADT` `aic` `compatible = aic,3`, reg size `0x1cc000`; `IOReg` `AppleInterruptControllerV3`; `SRC` mainline `irq-apple-aic.c` supports `apple,t8122-aic3`; Asahi's t8132 DT uses `apple,t8132-aic3` with fallback `apple,t8122-aic3` and the **same core reg size 0x1cc000** |
| Inference | The existing AIC3 driver likely works with a t6050 compatible plus fallback, but the event-register offset is unverified. |
| Confidence | **Likely** |
| Validation | Native boot via m1n1 |

## F-007 · IOMMU · DART t8110

| Field | Value |
|---|---|
| Source | `ADT` all `dart-*` = `dart,t8110`; `IOReg` `AppleT8110DART`; `SRC` `apple-dart.c` matches `apple,t8110-dart` |
| Inference | Driver support exists. New per-instance options (`dart-options`, `exclave-sid`, `avoid-tlbi-in-map`) need review. |
| Confidence | **Likely** |

## F-008 · Storage · ANS3 NVMe and "coastguard" SART

| Field | Value |
|---|---|
| Source | `IOReg` `AppleANS3CGv2Controller`; `ADT` `ans` `iop,ascwrap-v6`, `role = ANS2`, properties `nvme-linear-sq`, `nvme-secure-bar`; `sart-ans` = `sart,coastguard`; `SRC` `nvme-apple` matches only `*-nvme-ans2`; `apple-sart` matches t6000/t8103/t8015 only |
| Inference | The NVMe front end may stay ANS2-like (the `role` string), while "linear SQ" and "secure BAR" are new features. The SART revision is new. |
| Confidence | **Unknown** (both) |
| Validation | Native only. Static next step: diff the ADT property sets against an M2/M3 ADT, from public Asahi ADT dumps if available. |

## F-009 · Coprocessors · ASC wrapper v6

| Field | Value |
|---|---|
| Source | `ADT`: every IOP (ans, smc, sio, dcp, dcpext*, gfx-asc, gfx1-asc, aop, mtp, pmp0, sep) is `iop,ascwrap-v6`; `SRC` the Linux mailbox driver knows `apple,asc-mailbox-v4`, `apple,t8015-asc-mailbox`, `apple,m3-mailbox-v2` |
| Inference | RTKit-based coprocessors remain. The wrapper revision changed, and the mailbox register layout compatibility is unknown. |
| Confidence | **Unknown** |

## F-010 · GPU · Two GPU firmware coprocessors

| Field | Value |
|---|---|
| Source | `ADT` `gfx-asc` and `gfx1-asc`; `sgx` node carries both `gfx-data-*` and `gfx1-data-*` region properties; `IOReg` 2 × `AGXFirmwareKextG17RTBuddy` |
| Inference | G17X runs two GPU firmware instances, so a Linux AGX driver would have to manage both. |
| Confidence | **Hypothesis** |

## F-011 · Exclaves across the SoC

| Field | Value |
|---|---|
| Source | `ADT` `esm` (`iop,exclave-sep-manager`), `aop-exclave-mailbox`, `isp-exclave-proxy`, `isp-exclave-s-proxy`, `audio-*-proxy` (`iisaudio,isolated-stream-proxy`), `exclaves-test` root node, `ane,t8132exclave` |
| Inference | Camera ISP, microphone streams, ANE and parts of AOP are mediated by exclaves on macOS. Linux has no exclave runtime, so each block's accessibility from the normal world is an open enablement question. |
| Confidence | Observation **Confirmed**; impact **Unknown** |

## F-012 · Platform · Which Apple driver claims each ADT compatible

| Field | Value |
|---|---|
| Source | `hardware/scripts/kext_personalities.py` joins kext `Info.plist` IOKitPersonalities (`IONameMatch`) with the sanitized ADT. Result: `hardware/adt/kext-personalities.tsv` (108 of 155 compatibles matched). Metadata only: on Apple Silicon, kext binaries are not on disk (only in the sealed boot kernel collection), so there's nothing to disassemble. |
| Observation | `ane,t8132exclave` → `AppleH16ANEInterface` (H16-generation ANE). `sart,coastguard` → `AppleSART` / `IOCoastGuardSARTMapper`. `disp0,t605x` → `AppleMobileDispT605X-DCP`. `gpu,t6050` → `AGXG17X`. `iop,ascwrap-v6` → `AppleA7IOP-ASCWrap-v6`. `admac-evolution,t6050` → `AudioDMAController-T605x`. `error-handler,t6050` → `AppleT6050` (SoC error handler). |
| Inference | It names the hardware IP generation for each block, which tells Linux which existing driver family is closest (e.g. ANE = H16 = M4-era IP). |
| Confidence | **Confirmed** (direct metadata) |
| REA note | REA 6.4.0 `inspect-plist` rejects binary-less kext bundles (`target_unavailable`). Plain `plistlib` was used instead. |

## F-013 · Virtualization · What a Virtualization.framework Linux guest gets on M5 Max

| Field | Value |
|---|---|
| Source | `BENCH` / VM jobs 001, 002, 002b (`benchmarks/results/vm-alarm-2026-10-11/`) |
| Observation | **SME2 is exposed to the guest** (`CPU features: detected: SME2`, SVL 64 bytes), and in-guest SME throughput is 96–101% of macOS. **MIDR is masked** (`0x610f0000`, part 0x000). GICv3 (988 SPIs), PSCI 1.1, 24 MHz timer. Pipe ping-pong round trip **21–52 µs vs 3.7 µs** native. `getppid` 113 vs 85 ns. Page-fault/zero-fill throughput 10.5 vs 31.5 GB/s. Large-buffer latency 128 vs 108 ns (256 MiB). **Storage via virtio-blk on a sparse file: seq write 0.34 GB/s, seq read 1.45 GB/s (vs 11.2 / 11.0 native)**, QD32 random read 31% of native. |
| Inference | The hypervisor passes the matrix unit through, so CPU-side AI on Linux in a VM keeps SME. Costs concentrate in exits: wakeups/IPIs, stage-2 faults, and virtual I/O. |
| Confidence | **Confirmed** (measured) |
| Linux mapping | Guest kernel tuning (idle polling, `haltpoll`), 16K/64K guest pages (fewer stage-2 faults), and VZ disk options (NVMe controller, caching/sync modes). The matrix is in job 005. |
| Validation | `virtualization/scripts/run-storage-matrix.sh` (VZ storage configurations). Guest-kernel variants are planned. |

## F-014 · Power · No-root energy and DVFS telemetry via IOReport

| Field | Value |
|---|---|
| Source | `benchmarks/src/powermon.c` (read-only IOReport client, the same interface open-source monitors use) |
| Observation | "Energy Model" channels without root: per-core energy (`MCPU0_0..5`, `MCPU1_0..5`, `PACC_0..5`); cluster totals (`MCPU0`, `MCPU1`, `PCPU`) plus `MCPM0/1`/`PCPM` and SRAM rails; `CPU Energy`; `GPU`/`GPU Energy`; **`ANE`**; `DRAM`; `AMCC`; `DCS`; `DISP`; `ISP`; `AVE`; `FAB`; PCIe/Thunderbolt ports. DVFS residency: 17 states per M core, 22 per P core, 16 for the GPU. |
| Inference | Performance-per-watt and ANE-execution evidence are measurable on macOS without `powermetrics`/sudo. `PCPM`/`MCPMx` are likely the per-cluster SME ("CPM") rails (Hypothesis). |
| Confidence | Channels **Confirmed**; rail semantics **Hypothesis** |
| Linux mapping | No equivalent yet. On Linux the same PMGR/SMC energy counters would need a driver (hwmon/powercap). This is a research item for native enablement. |

## F-015 · Omarchy · aarch64 package set resolves fully on ALARM + Omarchy repo

| Field | Value |
|---|---|
| Source | VM job 004 (real `pacman -Sp` in a throwaway DB against live repos) |
| Observation | Omarchy edge aarch64 templates resolve 161 default names plus extras to **842 packages, 0 unresolved**. ALARM alone leaves **33 unresolved** (Omarchy-built packages). |
| Confidence | **Confirmed** |

## F-016 · CPU microarchitecture · FMA throughput depends on source-register reuse

| Field | Value |
|---|---|
| Source | `BENCH`: `benchmarks/src/fma_asm.c` vs `fma_asm_varied.c`, both fixed inline assembly with 24 independent FMLA chains and the same instruction count |
| Observation | Every FMLA reading the same two source registers gives **125.4 GFLOP/s** (27.8 FLOP/cycle at 4.51 GHz). Multiplicands rotated over 4×4 registers give **141.1 GFLOP/s** (31.3 FLOP/cycle, about the 4-pipe peak). Identical results inside the Linux VM (124.3 vs 141), so this isn't OS-dependent. 18 cores: 1.89 TFLOP/s with the asm kernel. |
| Inference | M5 P cores have a per-cycle limit on reads of the same physical register (rename or bypass). Apple clang 21 emits the same-register pattern for our C kernel; LLVM clang 23 doesn't. That explained an apparent "112% VM parity" for FMA. |
| Confidence | **Confirmed** throughput; mechanism **Likely** |
| Consequence | Cross-OS CPU comparisons must use compiler-independent kernels (`cpubench fma_asm`) or the same compiler version. This is now in the methodology. |

## F-017 · AI / CPU · llama.cpp CPU inference: build configuration dominates the OS

| Field | Value |
|---|---|
| Source | `BENCH`: macOS Homebrew llama.cpp b10280 / ggml 0.18.1 (`-dev none -nopo 1`; BLAS = Accelerate attached) vs Linux VM build of the same llama.cpp commit `61881b1f7` with its bundled ggml (CPU only, `armv8.6-a+dotprod+i8mm+sme`, no BLAS, LTO). Both run the same synthetic 8B GGUF files. |
| Observation | Q4_0: tg64 92–100%, pp512 104–117% (VM vs macOS). **Q4_K_M: pp512 ≈ 2.1× faster in the VM**, tg64 +11–24%. |
| Inference | macOS's Homebrew build sends large-batch k-quant matmuls through Accelerate BLAS (dequantize to FP32, then SGEMM), which is slower than ggml's native quantized kernels. Generation differences come from ggml version and compiler. The OS isn't the limiting factor for CPU LLM inference. |
| Confidence | Measurements **Confirmed**; attribution **Likely** (builds not identical; a strict comparison needs a BLAS-free macOS build of the same commit, which needs `cmake`) |
| Consequence | CPU-side LLM parity on Linux is achievable. On macOS, a BLAS-free build would speed up CPU-only k-quant prefill. That's irrelevant when using Metal. |

## F-018 · Virtualization · VZ storage modes: what closes the virtio gap

| Field | Value |
|---|---|
| Source | VM job 005 via `virtualization/scripts/run-storage-matrix.sh`: 16 GB data disk, 4 GiB file, ext4, blocks pre-allocated. Results in `benchmarks/results/vm-alarm-2026-10-11/storage-matrix/` |
| Observation | virtio automatic/full: write 3.17 GB/s, read 3.08 GB/s (1 thread). **virtio automatic/fsync: read 5.6 GB/s (1 thread) and 8.6 GB/s (4 threads), random QD1 10.1 K IOPS.** virtio cached/none: read 24–50 GB/s, served from the host page cache (not crash-safe). NVMe automatic/full: write 0.86 GB/s, read 1.6 GB/s. NVMe cached/none: write 19.5 GB/s, also cached. |
| Inference | The earlier 0.34 GB/s VM write was mostly **first-write allocation of the sparse image** on APFS, not virtio overhead. `fsync` sync mode is the best durable setting. VZ's NVMe emulation is slower than virtio-blk here. |
| Confidence | **Confirmed** (measured); single run per configuration |
| Recommendation | Root disk: virtio, `--disk-sync fsync`. Disposable scratch or build disks: `--disk-cache cached --disk-sync none`. Pre-allocate images used for storage benchmarks. Never report cached-mode numbers as storage parity. |
