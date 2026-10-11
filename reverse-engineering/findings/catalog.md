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
