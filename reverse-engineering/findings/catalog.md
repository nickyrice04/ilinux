# Research Findings Catalog

The mission's REA research database. One entry per engineering-relevant
finding.

Confidence: **Confirmed / Likely / Hypothesis / Unknown**.

Method tags:
* `ADT`: sanitized Apple Device Tree from `ioreg`
* `IOReg`: IORegistry class names
* `SRC`: open-source code (Linux, Asahi, XNU)
* `BENCH`: our measurements
* `REA`: REA tool output: metadata only (`inspect-plist` over driver bundles and launchd plists), no decompilation

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

## F-019 · CPU · Real MPIDR encoding on M5 (resolves F-001)

| Field | Value |
|---|---|
| Question | Which `reg` values must the Linux DT use for the t6050 CPUs? |
| Source | `SRC` m1n1 `5d84c4c34d3f` and `c4c4d575e12c` (MPIDR examples `0x80000X0Y` E, `0x80010X0Y` P, `0x80040X0Y` M), m1n1 `src/kboot.c` `dt_set_cpus()`; `ADT` `/cpus/*` reg |
| Observation | Aff2 carries a core-type bit: P = 1, M = 4. m1n1 compares each DT `cpu@` `reg` with `MPIDR & 0xffffff` and **prunes** the nodes that don't match, including the boot CPU's. The first draft DT used ADT `reg` (0x000…), so every CPU node would have been pruned. |
| Inference | t6050: M cores `0x40000–0x40005`, `0x40100–0x40105`; P cores `0x10200–0x10205`. |
| Confidence | Encoding **Likely** (m1n1 tested it on M5 Pro; our unit unverified). The pruning behaviour is **Confirmed** (code). |
| Linux mapping | `t6050.dtsi` CPU nodes |
| Implementation | `kernel/experiments/t6050-dt/gen_t6050_dt.py` (`mpidr_of()`) |
| Validation | Native: m1n1 log "FDT: CPU n MPIDR=…" |

## F-020 · SMP · t6050 secondary start: what is known

| Field | Value |
|---|---|
| Question | Why don't t6050 secondaries run m1n1 code? |
| Source | `SRC` m1n1 PR #610 (`b2d3f5eba7ce`) and its review; `src/smp.c` (`CPU_START_OFF_T6031` 0x88000); m1n1 RVBAR handling `7339546899ce` and `48d388bc5151`; the hypervisor CPUSTART table, which lacks 0x6050. `ADT` per CPU: `function-enable_core = <pmgr 'Core' BIT(cpu-id)>`, `function-cpu_idle = <pmgr 'cpuI'>`; P cores have `cluster-power-down = 1`. PMGR per-core PS registers `MCPU0_0…PCPU_5` sit at pmgr reg[0] + 0x00…0x88 (F-021). |
| Observation | The cores power on (seen in PMGR) but never set their spin-table flag. RVBAR can't be written on M4+. The `+0x4` start/status register uses 4 bits per cluster, which aliases with 6-core clusters. m1n1 has no fix as of `57a9339` (2026-10-11). |
| Inference | Ranked hypotheses: H1 locked RVBAR not pointing at m1n1; H2 a different start protocol (PMGR "Core" function); H3 cache attributes, possibly already fixed by `d16a2f4`; H4 an early locked-sysreg fault. Each has a cheap read-only proxy test (`kernel/native-enablement/plan.md` §1.2). |
| Confidence | Facts **Confirmed**; cause **Unknown** |
| Linux mapping | None until m1n1 starts the cores. Then spin-table, later PSCI-via-EFI. |
| Validation | Native m1n1 proxy session (needs user authorization) |

## F-021 · Power · PMGR device table decodes with m1n1's format

| Field | Value |
|---|---|
| Question | Can the t6050 power domains be generated from the ADT? |
| Source | `ADT` `/arm-io/pmgr` `devices` (31728 B), `ps-groups` (72 B); `SRC` m1n1 `proxyclient/m1n1/adt.py` (`PMGRDevices`, `PMGRPSRegs`), `src/pmgr.c`, `tools/pmgr_adt2dt.py` |
| Observation | 661 records of 48 bytes, with u16 ids (`id1` is 0 everywhere). No `ps-regs`: 6 `ps-groups` (reg, offset 0, mask 0) → pmgr reg[0], [1], [9], [51], [46], [49]. Flags: 338 `no_ps` (virtual), 199 critical, and others. Ids are unique, and no two real devices share an address. ANS, MTP and SMC have *empty* `clock-gates` (M4+ style). AOP, SMC, MTP, audio and GPU-firmware domains are virtual (coprocessor-managed). |
| Inference | Generated 188 domains (CPU, fabric, die-bridge and memory-controller domains skipped, as in Asahi t8132), with parents resolved through virtual nodes. |
| Confidence | Format **Confirmed** (self-consistent decode); runtime semantics **Likely** |
| Linux mapping | `apple-pmgr-pwrstate`; `t6050-pmgr.dtsi` |
| Implementation | `gen_t6050_dt.py` (`decode_pmgr`, `Pmgr`) → `out/t6050-pmgr.dtsi` |
| Validation | `validate.sh`: 0 dtc warnings. Native first boots should use `pd_ignore_unused`. |

## F-022 · DVFS · CPU p-state tables in the ADT (cpufreq + energy model)

| Field | Value |
|---|---|
| Question | Where are t6050's CPU frequency and voltage states? |
| Source | `ADT` pmgr `acc-clusters` = (0x16, 0x117, 0x205) → cluster 0 → `voltage-states22`, cluster 1 → 23, cluster 2 → 5; `voltage-statesN` = (65535e6/f_kHz, core mV), `-sram` = (f_kHz, SRAM mV). `BENCH` `cpubench freq` 1 thread = 4.512 GHz; IOReport residency names `V0P14…V14P0` |
| Observation | M clusters: 15 states, 1344–4380 MHz, 600–1025 mV. P cluster: 20 states, 1308–4608 MHz, 625–1090 mV. The period field × frequency = 65535e6 for every entry. The measured 4.512 GHz single thread equals P state index 18; macOS AC "Low Power Mode" may explain why 4.608 GHz isn't reached (B-009). PMGR reg holds per-cluster blocks at 0x2_1{0,1,2}e20000 (+0x12e8), the M1–M3 DVFS address pattern. |
| Inference | Linux OPP tables with `opp-microvolt`, plus an energy model, are possible from ADT data alone. Hypotheses: `opp-level` = index+1, t8112-style 5-bit p-state field. EM coefficients from macOS energy are P ≈ 1054, M ≈ 550 uW/MHz/V² (includes leakage). |
| Confidence | Tables **Confirmed**; register interface **Likely**; EM numbers **Hypothesis** |
| Linux mapping | `apple-soc-cpufreq`, OPP v2, EAS (`dynamic-power-coefficient`, `capacity-dmips-mhz`), `omarchy-qos` |
| Implementation | `gen_t6050_dt.py` (`dvfs_tables`) |
| Validation | Native: set a p-state, then measure with `cpubench freq` |

## F-023 · Storage · SARTv4 and the M4+ NVMe register split on t6050

| Field | Value |
|---|---|
| Question | What does Linux need for the internal SSD on t6050? |
| Source | `ADT` `sart-ans`: `sart,coastguard`, `sart-version = 4`, `sart-power-reg-offset = 0x13e8`; `ans`: `nvme-secure-bar`, `nvme-linear-sq`, `nvme-interrupt-idx = 4`, 10 reg entries (reg[3] 0x21dcc0000 +0x60010, reg[9] 0x25dcc0000 +0x10000), `iommu-parent` = SART (no ANS DART). `SRC` m1n1 `9bfdf8aeca30` and `53f8ee9b54ba`; AsahiLinux/linux `asahi`, `asahi-wip`, `apple-soc/drivers-7.4`, `b4/nvme-fwabi` |
| Observation | The firmware-ABI fixes (`b4/nvme-fwabi`) are already in `asahi`. **No** Asahi branch has SARTv4 or the NVMMU/NVMe split and I/O-queue base registers. |
| Inference | The Linux gap is small and well defined. |
| Confidence | **Confirmed** (data and code reading) |
| Linux mapping | `drivers/soc/apple/sart.c`, `drivers/nvme/host/apple.c`, bindings |
| Implementation | `kernel/patches/t6050/0001`–`0005` (local, untested) |
| Validation | VM compile test; native read-only probe |

## F-024 · Platform · t6050 has a second die at +0x21_0000_0000

| Field | Value |
|---|---|
| Question | Is the M5 Max a single die from the OS's point of view? |
| Source | `ADT` `/arm-io` `die-count = 1`; `aic` `aic-numdies-per-die = 2`, `aic-die-offset-stride = 0x21_0000_0000`; pmgr `ps-groups` 4/5 → reg[46]/[49] at child 0x21_80600000 / 0x21_88300000 (= reg[0]/reg[9] + 0x21_0000_0000), holding `AIC_GFX`, `NUB_GFX_GPIO`, `AMCC0–31`, media (VENC, AVD, JPG, PRORES); GPU, scaler, AVE and AVD MMIO at 0x20xx/0x21xx child addresses |
| Observation | macOS treats it as one die (`die-count = 1`), but PMGR and AIC each have a second instance at the same 0x21_0000_0000 stride. Interrupt numbers in the ADT are flat (< 4096). |
| Inference | M5 Max = a CPU/SoC die plus a GPU/media/memory-controller die in one package. Linux DT: PMGR blocks on die 1 are separate nodes (done). Whether AIC needs 4-cell specifiers for die-1 interrupts is **Unknown**. |
| Confidence | Data **Confirmed**; two-die interpretation **Likely** |
| Linux mapping | AIC (`nr_die`), PMGR, all GPU/media drivers |

## F-025 · Debug · Laptop console on M4+/M5 is the dockchannel UART over "debugusb"

| Field | Value |
|---|---|
| Source | `SRC` m1n1 `e3b42cbdd55d` (dockchannel UART fallback), `1a0e81f9dcd9` and `5130a9a` (debugusb enabled by disabled authenticated-root); `ADT` `/arm-io/dockchannel-uart` (`aapl,dock-channels`, IRQ 360) |
| Observation | The SoC UART0 isn't wired to a connector on laptops. m1n1's console goes through the dockchannel UART, exported over USB when debugusb is on. m1n1 notes that Linux and u-boot have no dockchannel-uart driver yet. |
| Inference | For a serial console on t6050 Linux, write a small dockchannel-uart tty driver (register layout in m1n1, MIT at v1.9.9). Until then, use the framebuffer console. |
| Confidence | **Confirmed** |
| Linux mapping | new `drivers/tty/serial/apple-dockchannel-uart.c` (to be written) |

## F-026 · Idle · M4+ Linux runs with `idle=nop arm64.nowfxt`

| Field | Value |
|---|---|
| Source | `SRC` m1n1 `3a69c73f5933` and `9095a5ee70bf` (`src/kboot.c`): for `!apple_sysregs_unlocked` (all of M4/M5) m1n1 appends ` idle=nop arm64.nowfxt`. mBoot locks the chicken bits, so WFI loses state (Asahi 7.2 report). |
| Observation | Idle CPUs on t6050 Linux would spin instead of executing WFI. |
| Inference | Expect much higher idle power than macOS until a state-saving idle path exists: a cpuidle driver, or PSCI-via-EFI `CPU_SUSPEND` into m1n1 `deep_wfi` (branch `psci-via-efi`). This is a major item for performance per watt. |
| Confidence | Mechanism **Confirmed**; power impact **Likely** (not measured) |
| Linux mapping | cpuidle, PSCI-via-EFI (`efi-psci` branch), `omarchy-qos` |

## F-027 · VM · App Nap throttles a hidden QEMU VM to background priority

| Field | Value |
|---|---|
| Question | Why did guest CPU work run far below native in QEMU/HVF but not in Virtualization.framework? |
| Source | `MEAS`. `ps -M` on the QEMU process: all threads at PRI 4 while the Cocoa window was on another Space. Guest `cpubench intmix` (GCC build): 3.5 Gop/s napped vs 14.3 un-napped. Host `powermon`: the work ran on M cores. |
| Observation | QEMU owns its Cocoa window, so macOS App Nap applies to the whole process, vCPUs included, whenever the window is not visible. Virtualization.framework guests run in a launchd XPC service and are not affected. |
| Inference | A hidden VM needs an App Nap policy. The workspace `app-nap=auto` option holds `NSActivityUserInitiatedAllowingIdleSystemSleep` only while non-background vCPUs are busy. Verified: napped at idle (PRI 4); about 1 s after foreground load, PRI is 28–31 and the 6 background vCPUs stay at 4. |
| Confidence | **Confirmed** |
| Linux mapping | VM only (`virtualization/qemu/patches/qemu/0003-cocoa-app-nap.patch`) |

## F-028 · Scheduling · macOS QoS placement on M5 Max (Super vs M cores)

| Field | Value |
|---|---|
| Source | `MEAS` `cpubench intmix -t 1 -q {ui,default,utility,bg}` under `powermon`, on AC power |
| Observation | `ui`, `default` and `utility` all run on a Super (P) core at full speed: about 21 Gop/s, about 7.2 W per CPU. Only `background` moves to an M core: 4.46 Gop/s at 0.65 W (6.9 vs 2.9 Gop/s/W). |
| Inference | On this machine, `utility` is not an efficiency hint. Only background QoS buys efficiency, at about 4.7× lower speed (2.4× better work per joule). |
| Confidence | **Confirmed** (AC power; battery and Low Power Mode not yet measured) |
| Linux mapping | `omarchy-qos` tier ratios; VM `bg-vcpus` capacity (220/1024) |

## F-029 · VM · Heterogeneous vCPUs mirror Super/M scheduling for Linux guests

| Field | Value |
|---|---|
| Source | `MEAS` `benchmarks/vm/hetero_placement.sh` (QEMU `--hetero`: 18 vCPUs in 3 clusters; vCPUs 12–17 at host background QoS, `capacity-dmips-mhz` 220). Guest `cpubench` built with clang `-mcpu=apple-m4`. |
| Observation | Guest `cpu_capacity` reads 1024×12 / 220×6, and `omarchy-qos` fences `background.slice` to 12–17 automatically. Single-thread intmix on a foreground vCPU: 20.79 Gop/s (**99%** of native). Background tier: 4.51 Gop/s at 0.77 W, **1.84×** the foreground's Gop/s/W. With 6 threads: 111 vs 21.8 Gop/s, 7.0 vs 15.9 Gop/s/W (**2.25×**). Without reservation, unpinned tasks could start on a slow vCPU; `RESERVE_EFFICIENT_CPUS=auto` keeps system, session, app and utility slices on 0–11. |
| Inference | Guest background work gets macOS-like efficiency, and the guest scheduler sees an honest capacity map. |
| Confidence | **Confirmed** |
| Linux mapping | `patches/qemu/0002-hvf-heterogeneous-vcpus.patch`, `omarchy-qos` |

## F-030 · VM GPU · VirGL fence latency on macOS: 1 ms polling → event-driven

| Field | Value |
|---|---|
| Source | `MEAS` `benchmarks/src/glbench.c`: the same GL 4.1 core code on macOS CGL and in the guest (Mesa virgl). Three reps each, 2592×1458. |
| Observation | QEMU only enabled virglrenderer's sync thread on EGL, and virglrenderer needs eventfd, which macOS lacks. So fences retired on a 1 ms timer, about 1.5 ms per guest GL sync. With async fences (pipe-backed eventfd, CGL path): ALU 92→**99.7%** of native, blended fill 17→**74%**, readback 23→**61%**. Draw calls stayed at 46→50% (command encoding bound), and texture upload at 25→28% (copy bound, 13.4 vs 48 GB/s). Native GL ALU is 12.35 TFLOPS, 84% of the Metal compute peak (14.75). |
| Inference | GPU-bound work is at parity. The remaining gaps are per-draw encode/decode and the guest→host copy; zero-copy blob resources or Venus are the next levers. |
| Confidence | **Confirmed** |
| Linux mapping | `patches/qemu/0004-virgl-macos-async-fences.patch`, `patches/virglrenderer/0001-macos-thread-sync.patch` |

## F-031 · Omarchy · Qt 6.12 `QtQuick/Color` shadows the Omarchy shell's `Color` singleton

| Field | Value |
|---|---|
| Source | `MEAS` Quickshell log (`Cannot read property 'bar' of undefined`). Minimal QML reproduction with Qt's `qml` tool. `QtQuick/plugins.qmltypes` exports `"QtQuick/Color 6.12"`. |
| Observation | With an unversioned `import QtQuick`, Qt's type wins over `qs.Commons`' singleton even when that import comes later, so every theme colour is undefined: black, empty bar and unthemed popups. `import QtQuick 6.11` restores it. |
| Inference | This is an upstream Omarchy bug on Qt ≥ 6.12, independent of ARM, Apple or the VM. It's fixed locally by an idempotent pin plus a pacman hook (D-017), and worth reporting upstream. |
| Confidence | **Confirmed** |
| Linux mapping | `omarchy-arm64/configuration/compat/qt612-color-shadowing` |

## F-032 · VM power · An idle Omarchy VM costs under 0.1 W

| Field | Value |
|---|---|
| Source | `MEAS` `benchmarks/vm/vm_power_states.sh`, back-to-back A/B, 3 × 30 s each, IOReport SoC sum. VM: desktop session up, display on, window hidden. |
| Observation | Host only: 1.713 W. VM idle with `app-nap=auto`: 1.799 W (**+0.09 W**). VM idle with `app-nap=off`: 1.855 W (+0.14 W). DPMS off vs on made no difference with the window hidden. An earlier +0.38 W reading included post-login churn and a lingering test user manager. |
| Inference | An idle guest isn't a battery problem. Busy-guest efficiency (F-029) and the rendering path (F-030) matter more. Panel and backlight power aren't in the IOReport SoC sum. |
| Confidence | **Confirmed** for the SoC sum |
| Linux mapping | VM launcher defaults |

## F-033 · VM storage · QEMU on macOS: main-loop disk I/O, O_DSYNC for cache=none, btrfs fsync chains

| Field | Value |
|---|---|
| Source | `MEAS` `storbench` in the guest (configurations as in `reports/vm-vs-macos-parity.md`). `SRC` QEMU `block/file-posix.c` (`#define O_DIRECT O_DSYNC` when O_DIRECT is missing) and `meson.build` (fdatasync probe requires `_POSIX_SYNCHRONIZED_IO`). Native `syncmode` test. |
| Observation | (1) Without an iothread, virtio-blk ran in the main loop, which also runs VirGL. A dedicated iothread with 4 queues doubled random-I/O scaling: 8 threads 42→73K IOPS, 32 threads 55→113K. (2) On macOS, `cache=none` meant O_DSYNC on every write. With F_NOCACHE (workspace patch 0005) it gives 4.0 GB/s writes and 13.2 GB/s cold reads (100%), but 176 µs QD1 random reads. (3) QEMU flushes with fsync because the fdatasync probe fails on macOS, but APFS fsync and fdatasync cost the same here (about 22 µs). (4) Guest write+fsync runs at 22% of native, and 4 writers on one file collapse to about 0.8K IOPS (btrfs log and inode serialization amplified by about 50 µs virtio round trips). |
| Inference | Keep writeback plus iothread as the default (small-I/O latency at parity once data is warm). Offer F_NOCACHE for streaming and memory efficiency. The remaining gap is per-I/O virtualization latency times btrfs's dependent I/O chain. Levers: an ext4 data subvolume for fsync-heavy databases, or lower notify latency. |
| Confidence | **Confirmed** (measurements); the btrfs-chain attribution is **Likely** |
| Linux mapping | launcher defaults; `patches/qemu/0005-file-posix-macos-f-nocache.patch` |

## F-034 · VM display · A hidden QEMU window caused a redraw-request storm

| Field | Value |
|---|---|
| Source | `MEAS` `COCOA_GL_TRACE=1`. Per-thread CPU via `ps -M`. QEMU CPU time over 60 s idle, `APP_NAP=off`, window hidden. |
| Observation | The GUI timer ticks at the display rate (about 8 ms at 120 Hz). While the window is hidden, Core Animation never draws the layer, so `gl_dirty` never clears, and every tick re-dispatched `setNeedsDisplay` to the Cocoa main thread: 1832 requests vs 1 guest frame in 20 s. A first adaptive-refresh attempt didn't help for exactly that reason (2.35 s CPU/min vs 2.26 s). The final patch requests one draw per frame, ticks every 100 ms after a second of no frames, and redraws on unhide. QEMU idle CPU went to **1.24 s/min, 45% less**, with trace logging still on. |
| Inference | A real saving in wakeups and CPU. The SoC power effect (estimated tens of mW) is below the resolution of non-interleaved 30 s IOReport runs (±0.1 W run-to-run). |
| Confidence | CPU reduction **Confirmed**; power effect **Likely** (not resolved) |
| Linux mapping | VM only (`patches/qemu/0006-cocoa-adaptive-refresh.patch`) |

## F-035 · VM GPU · Venus (guest Vulkan) on a macOS host needs six host-side fixes

| Field | Value |
|---|---|
| Source | `MEAS` guest `vulkaninfo`, QEMU logs, guest `strace`. `SRC` virglrenderer 1.3.0 proxy/render-server code, QEMU `hw/display/virtio-gpu-virgl.c`. |
| Observation | In order of discovery: (1) the proxy initialised only with `VIRGL_RENDERER_RENDER_SERVER`, so Venus had no capset ("Unsupported wire format version 0"); QEMU now asks for Venus only, served by an in-process render-server thread. (2) macOS has no `AF_UNIX`/`SOCK_SEQPACKET`; the stream replacement needed partial-read handling, and the existing check had an operator-precedence bug. (3) The pipe-based eventfd emulation broke once the fd crossed `SCM_RIGHTS` (vulkaninfo hung in `drm_syncobj` waits); an anonymous FIFO opened `O_RDWR` survives it. (4) HVF keeps the pages `hv_vm_map()` saw, so a `MAP_FIXED` remap over the hostmem BAR was invisible to the guest ("stuck in ring seqno wait"). (5) `VK_EXT_external_memory_metal` was missing from the sorted Venus extension table, so `vkGetMemoryMetalHandleEXT` stayed NULL and QEMU crashed on the first blob export. (6) The loader is found via `VIRGL_VULKAN_LIBRARY`. Result: `Virtio-GPU Venus (Apple M5 Max)`, Vulkan 1.4.334; `vkcompute` FMA 10.76 TFLOPS vs 11.24 native MoltenVK (95.7%), bit-exact; submit+wait 318–375 µs vs 204 µs native. |
| Inference | Every blocker was a host-platform assumption (Linux sockets, eventfd, mmap-over-mapped-RAM, a generated table), not a Venus design limit. Venus on MoltenVK gives the VM near-native Vulkan compute. |
| Confidence | **Confirmed** |
| Linux mapping | VM only: `patches/virglrenderer/0001`–`0006`, `patches/qemu/0008`–`0009`, launcher default (D-027) |

## F-036 · VM GPU · HVF maps guest memory in 16 KiB host pages; a sub-page blob hangs the writer forever

| Field | Value |
|---|---|
| Source | `MEAS` `eu-stack` on the guest vkcube (three samples, same `memcpy` PC), `strace` (no syscalls), `/proc` (100% user time), QEMU `info mtree -f` (a blob region of size 0x1000). `SRC` QEMU `hvf_set_phys_mem()` (skips sections not aligned to the host page) and the HVF data-abort handler (a write fault on a RAM region is "retried with page writes enabled"). |
| Observation | Venus allocations below 16 KiB (vkcube's uniform buffers, feedback slots) became 4 KiB RAM subregions. HVF never mapped them, so each guest store trapped, and QEMU returned to the same instruction: vkcube spun at 100% CPU and never presented. The guest already uses 16 KiB pages, so the BAR reserves whole pages. Rounding the subregion up to the host page (QEMU 0010) took vkcube from 99% to 0.8% CPU, and it now renders. |
| Inference | Applies to any HVF guest mapping sub-page host memory as RAM. Reads would instead hit `assert(isv)` for SIMD loads. 16 KiB guest pages, already the native Asahi page size, are what make the rounding safe. |
| Confidence | **Confirmed** |
| Linux mapping | `patches/qemu/0010-hvf-map-venus-blobs-in-host-pages.patch`; VM kernel stays on 16 KiB pages |

## F-037 · VM GPU · Apple's GL binds IOSurfaces only as rectangle textures; Metal→GL IOSurface access is ordered by submission

| Field | Value |
|---|---|
| Source | `MEAS` host probes (scratch programs, CGL 4.1 core on "GL 4.1 Metal - 90.5"). |
| Observation | (1) `CGLTexImageIOSurface2D` on `GL_TEXTURE_2D` returns `kCGLBadValue` (10008); `GL_TEXTURE_RECTANGLE` works. (2) Accepted IOSurface formats: `BGRA`/BGRA+`8_8_8_8_REV`, `l10r`/`2_10_10_10_REV`, `RGhA`/half, `L008`, `2C08`. `RGBA` is rejected. (3) A 6.9 MB heap→IOSurface blit is 140 µs of GPU time, but `waitUntilCompleted` returns after 0.89–0.96 ms, and spinning on an `MTLSharedEvent` is no faster (0.83 ms). `waitUntilScheduled` takes 0.19 ms. (4) GL work submitted after a *scheduled* Metal pass on the same IOSurface never read stale data (0/300 frames, Metal passes of 0.5–60 ms). After `commit` alone, 1 of 60 was stale. |
| Inference | vrend imported Venus images through `GL_EXT_memory_object_fd`, which CGL lacks, so the compositor's context went into error. The workable path: a Metal blit (or swizzle pass) into an IOSurface, then a GL blit from the rectangle into the 2D texture, waiting only for scheduling. In the VM this costs 0.12 ms per update. Zero-copy would need IOSurface-backed Venus memory plus rectangle sampling in vrend. The cross-API ordering is observed behaviour, not documented API. |
| Confidence | (1)–(3) **Confirmed**; (4) **Confirmed** on this machine and OS, **Likely** in general |
| Linux mapping | `patches/virglrenderer/0007-vrend-cgl-iosurface-mirror-for-venus-images.patch` |

## F-038 · VM GPU · Vulkan FIFO lost a quarter of frames to Mesa's commit-timing targets

| Field | Value |
|---|---|
| Source | `MEAS` `benchmarks/vm/vkbench.sh`, `es2gears_wayland`, `WAYLAND_DEBUG=client` on vkcube. |
| Observation | On the 2592×1458@120 output, vkcube FIFO ran at 92.9 fps, while GL FIFO (es2gears) held 119.98 fps and vkcube mailbox ran at about 2,700 fps. The client was not the limit. Mesa 26 drives Wayland FIFO with `wp_fifo_v1` barriers, a `wp_commit_timer_v1` timestamp on every commit, and `wp_presentation` feedback. With `MESA_VK_WSI_DEBUG=nowlts` (no timestamps), FIFO reached **119.5 fps**. |
| Inference | The VM's presentation feedback has no real vblank behind it, so timestamps derived from it miss the compositor's latch about one time in four. Short term: `nowlts` in the VM session. Root fix: paced virtual vblank and presentation times from QEMU, which would also help GL frame pacing. |
| Confidence | Measurements **Confirmed**; cause **Likely** |
| Linux mapping | VM only: `omarchy-arm64/configuration/vm-integration/etc/environment.d/60-ilinux-vm-vulkan.conf` |

## F-039 · Tooling · gdb cannot attach in the M5 guest (SME without SVE)

| Field | Value |
|---|---|
| Source | `MEAS` guest gdb 17: "Unable to fetch SVE/SSVE vector length: Invalid argument" on every attach. |
| Observation | HVF exposes SME (streaming SVE) on the M5 but not SVE. gdb then asks for the SVE register set, which the kernel refuses. `eu-stack` (general registers only) and `strace` work. |
| Inference | It's a gdb assumption about SME-only CPUs, and it will affect native Linux on M4/M5 too (Apple implements SME without SVE). Workarounds: `eu-stack`/`strace`, or a debug VM launched with SME hidden. Worth reporting to gdb. |
| Confidence | **Confirmed** (symptom); gdb root cause **Likely** |
| Linux mapping | Upstream gdb (report); our debugging uses `eu-stack` |

## F-040 · Power · macOS's efficiency comes from an SoC policy layer with no Linux counterpart

| Field | Value |
|---|---|
| Source | `REA` `inspect-plist` over all driver bundles, joined with the live IORegistry (`hardware/macos/block-map.tsv`). Launchd job names. |
| Observation | Next to PMGR, this machine runs four policy drivers: `AppleT6050CLPC` (closed-loop performance controller), `AppleT6050SOCTuner`, `ApplePassthroughPPM` (peak power manager) and `ApplePTD`. The PPM is paired with `peakpowermanagerd`, and `powerd`, `thermalmonitord`, `perfpowermetricd` and `PerfPowerServices` sit above them. CLPC exists as a separate bundle for every SoC from T8103 to T8150. |
| Inference | Battery efficiency on macOS isn't a property of individual device drivers: one closed loop joins CPU/GPU performance states, QoS, thermal and peak-power limits. Linux has the parts (cpufreq + EAS + uclamp + thermal governors + SMC hwmon) but nothing joining them. A Linux-native governor layer is original work that needs no Apple code: EAS capacities, QoS tiers (as `omarchy-qos` does in the VM), and battery- and thermal-aware limits. |
| Confidence | Inventory **Confirmed**; component roles **Likely** (from names and daemon pairing) |
| Linux mapping | Native track: governor and policy service. VM: `omarchy-qos`, host QoS mapping (D-019) |

## F-041 · Coprocessors · Most M5 Max blocks are RTKit firmware coprocessors

| Field | Value |
|---|---|
| Source | `REA` bundle dependencies (`OSBundleLibraries` contains `com.apple.driver.RTBuddy`) for the drivers live on this machine. ADT `iop` nodes (`ascwrap-v6`, `mxwrap`, `rtbuddy-v2`). |
| Observation | These blocks are driven through RTKit coprocessors: GPU (`AGXG17X`), Neural Engine (`AppleH11/H16ANEInterface`), display (8 DCP-family bundles), camera ISP (`AppleH16CameraInterface`), AOP/SPU sensors (`AppleSPU`), SMC, NVMe and the keyboard/trackpad MTP. The wrappers are `AppleA7IOP-ASCWrap-v6` and `MXWrap` (Thunderbolt). |
| Inference | The base for any native M5 bring-up is Linux's `apple-rtkit` and mailbox layer, which must be checked against ASCWrap v6 / `rtbuddy-v2`. Then each block needs its own firmware-ABI work, and macOS 26 firmware already changed the DCP and NVMe ABIs. |
| Confidence | **Confirmed** (metadata); ABI-change scope **Likely** |
| Linux mapping | `apple-rtkit`, `apple-mailbox`; per-block drivers (gap matrix) |

## F-042 · VM video · Mesa 26's virgl video requests use shifted profile values, and FFmpeg picks planar surfaces

| Field | Value |
|---|---|
| Source | `MEAS` host-side log of the guest's requests (`VIRGL_VIDEO_PROBE_PROFILES` advertises every value); `SRC` Mesa 26.2.4 `gallium/drivers/virgl/virgl_video.c`, `frontends/va/surface.c`, `virgl_screen.c`. |
| Observation | The guest (Mesa 26.2.4) sends `pipe_video_profile` values from its own, newer enum: AVC Constrained Baseline 8, Main 9, High 11, High10 12, HEVC Main 15, VP9 profile 0 24, profile 2 25. virglrenderer 1.3.0's copy numbers them differently. Buffer formats arrive in virgl numbering (NV12 166, IYUV 165, YV12 163). The VA frontend lists NV12, YV12 and IYUV whenever the plane formats are sampleable (`vl_video_buffer_is_format_supported`), and the host's `PREFERED_FORMAT` cap is not consulted. FFmpeg then picks IYUV, an exact match for yuv420p. |
| Inference | The virgl video protocol carries Gallium-internal enums, so it isn't stable across Mesa and virglrenderer versions. The host must accept the values guests actually send (the VideoToolbox backend maps 8/9/11 to H.264) and must support 3-plane targets. Steering FFmpeg to NV12 needs a guest Mesa change: offer only NV12/P010 for decode, as radeonsi does. |
| Confidence | **Confirmed** |
| Linux mapping | VM: virgl patch 0008; a later guest Mesa patch. Native: not applicable (AVD through V4L2) |

## F-043 · VM video · Rebuilding an H.264 PPS from VA-API needs reference-index defaults that VA does not carry

| Field | Value |
|---|---|
| Source | `MEAS` host harness (`scratchpad vt/vtharness.m`, modes real/synth/learn) on a 1080p60 High-profile clip with B-frames; VideoToolbox status codes. |
| Observation | VA-API's H.264 picture parameters omit the PPS `num_ref_idx_l0/l1_default_active_minus1`. A PPS rebuilt with guessed defaults made VideoToolbox reject every slice that relied on them: `-12909`, then the codec closed after 11 frames with 396 errors. Learning the defaults from the first P/B slice that does not override them, then swapping the format description (or prepending an in-band PPS when the session refuses the swap), decoded 600/600 frames with 0 errors. |
| Inference | Any stateless→stateful bridge has to recover these fields from slice headers: VA→VideoToolbox here, and V4L2 stateless→stateful the same way. `max_num_ref_frames` must come from the descriptor's `num_ref_frames`. |
| Confidence | **Confirmed** |
| Linux mapping | VM: virgl patch 0008 (`slice_uses_default_refs`) |

## F-044 · VM video · Requesting GL-compatible pixel buffers changes VideoToolbox's decoded samples

| Field | Value |
|---|---|
| Source | `MEAS` per-frame MD5 of the decoded picture (`VIRGL_VIDEO_MD5`, and the host harness) against FFmpeg's software `framemd5`. |
| Observation | With `kCVPixelBufferOpenGLCompatibilityKey` in the destination attributes, decoded frames differed from FFmpeg's reference (first frame `aaead822…` vs `d660200e…`). With IOSurface-only attributes, 600/600 frames matched bit for bit. `VTPixelTransferSession` NV12→planar 4:2:0 is lossless. |
| Inference | Ask VideoToolbox for IOSurface-backed output only and bind the IOSurface to GL directly (`CGLTexImageIOSurface2D`); the GL-compatibility attribute buys nothing here and costs exactness. Why VideoToolbox's output path changes is not known. |
| Confidence | **Confirmed** (exactness); cause **Unknown** |
| Linux mapping | VM: virgl patch 0008 |

## F-045 · VM video · Mesa's virgl driver never marks decode targets dirty, and has no decode fence

| Field | Value |
|---|---|
| Source | `MEAS` `hwdownload`, `vaGetImage` and `vaapi-copy` return an all-zero picture (MD5 `327aa874…`) while mpv's zero-copy path shows correct video; `SRC` Mesa 26.2.4 `virgl_video_end_frame`, `virgl_resource` transfer logic, `frontends/va/surface.c` `_vlVaSyncSurface`. |
| Observation | Decode targets' plane resources are written only by the host, but the guest driver never clears their "clean" state, so a guest map reads its own stale copy without a host readback. The plane resources are staging-backed with a token 16 KiB guest backing, so a host-side refresh of the backing can't help. `virgl_video_end_frame` also sets no output fence: `vaSyncSurface` returns at once, and correctness depends on the host completing END_FRAME before later commands. |
| Inference | Copy-back needs a small guest Mesa fix: mark the target's planes dirty in `end_frame`. The missing fence means the host decode must stay synchronous in command order; an asynchronous host decode would first need per-resource completion tracking in vrend. |
| Confidence | **Confirmed** (symptom, source); fix **Likely** |
| Linux mapping | VM: guest Mesa patch (planned) |

## F-046 · VM video · Hardware decode costs about native's whole playback increment; the rest was mpv's scaling (corrected)

| Field | Value |
|---|---|
| Source | `BENCH` `benchmarks/vm/playback_power.py` (sessions `fencepoll`, `mpv-render`, ABBA) and `benchmarks/macos/playback_power.py` (4 reps, VM off), SoC energy from IOReport, on AC; `MEAS` `sample` of QEMU during playback; window visibility from `benchmarks/bin/winvis` (F-049). |
| Observation | 4K60 H.264: VM hardware decode alone (FFmpeg `-re`, frames kept on the GPU, nothing shown) is 3.0 W, about +1.1 W over idle, as much as native AVFoundation's whole playback increment (+1.0 W, 2.91 W total). VM playback in mpv: 7.0–7.3 W with mpv's default scaling, 3.9 W with `profile=fast` (F-048). On QEMU's main thread, VideoToolbox decode blocks 20% of the time, the I420 conversion is 5% CPU, and the GPU copies 1%. |
| Inference | This entry first attributed the ~4 W between decode-only and mpv playback to presentation. That was wrong: it is mpv's own rendering (F-048). Host-side presentation (QEMU's draw and WindowServer's compositing) has not been measured yet. The VM window was not on screen during the VM runs, so it was never drawn, while the native player's window was (F-049). Until the VM runs are repeated with the window on screen, VM-vs-native playback ratios are not like for like. |
| Confidence | **Confirmed** (measurements, the correction); host presentation cost **Unknown** |
| Linux mapping | VM: mpv defaults (`omarchy-arm64/configuration/vm-integration/etc/mpv/mpv.conf`). Native: an AVD V4L2 driver plus DCP planes |

## F-047 · VM GPU · Apple's `glClientWaitSync` busy-polls for its whole timeout

| Field | Value |
|---|---|
| Source | `MEAS` `sample` of QEMU during 4K60 hardware-decoded playback: the `vrend-sync` thread had 630 of 3,631 samples in `glClientWaitSync_Exec`, 390 of them in `mach_absolute_time`, the rest in `gleTestSync`/`testFence` and `cthread_yield`. |
| Observation | Apple's GL (GLEngine over AppleMetalOpenGLRenderer) implements a blocking fence wait as a poll loop. virglrenderer's fence thread waited with a 1 s timeout, so it spun while each awaited GPU job ran. How much depends on the workload: 17% of the thread's samples during 4K60 playback, but only 3% under GPU-bound GL (glmark2 terrain, 528 fps), where it mostly had no fence pending. |
| Inference | On macOS, wait on GL fences with a zero timeout and sleep between polls (virgl patch 0010: 50 µs doubling to 1 ms). Fences are flushed at creation, so the poll sees them complete. The same applies to any host GL code that blocks on fences. Measured A/B (`benchmarks/results/vm-video-2026-10-12/fence-ab/`, ABBA, fresh boot per session): 4K60 hardware playback 7.41 W blocking vs 7.00–7.12 W polling, QEMU 0.49 vs 0.41–0.44 cores. The first blocking session read 9.47 W on an elevated 2.82 W idle and is left out. Software playback is unchanged within noise. glmark2 terrain runs at 528 fps either way, so the sleeps cost no throughput there. |
| Confidence | **Confirmed** (profile, A/B); saving is small: about 0.3–0.4 W in 4K60 playback |
| Linux mapping | VM: virgl patch 0010 |

## F-048 · VM video · mpv's default scaling, not decode or the display chain, dominated VM playback power

| Field | Value |
|---|---|
| Source | `BENCH` `benchmarks/vm/playback_power.py` session `mpv-render` (4K60 hardware decode, fullscreen 2592×1458, 2 reps ABBA); `benchmarks/linux/vfill.c`, a client that only clears the screen, for the display chain. |
| Observation | SoC power for the same decoded 4K60 stream: mpv `vo=gpu` with default scaling 7.28 W; `gpu-next` default 5.92 W; `vo=gpu` with `profile=fast` 3.88 W; `gpu-next` fast 3.85 W; decode alone 3.03 W (session idle 2.76 W). The defaults cost +0.5 W of GPU and +1.9 W of DRAM and memory-controller power over fast. They downscale in linear light at source resolution, with a wide filter and dithering. A 60 fps fullscreen client that only clears the screen costs the whole guest chain about +0.8 W over idle (Hyprland compositing plus virtio-gpu flushes). Hyprland direct scanout gave no saving: every flip becomes a scanout switch in QEMU. mpv `--vo=dmabuf-wayland` doesn't work: the compositor can't import the VA-API surfaces through virgl, so mpv falls back to software decode and fails. |
| Inference | For battery life in the VM, the player's scaling settings matter more than any copy in the display chain: `profile=fast` saves about 3.4 W at 4K60. The VM ships `profile=fast` and `vo=gpu` with VA-API (`vo=gpu` dropped fewer frames than `gpu-next` with the same profile). Quality-minded users can opt back into `profile=high-quality`. Keep Hyprland direct scanout off in the VM. |
| Confidence | **Confirmed** (guest-side costs do not depend on the host window state) |
| Linux mapping | VM integration `etc/mpv/mpv.conf`; natively the same mpv trade-off applies, on the native GPU |

## F-049 · Methodology · macOS never draws a window that is not on screen, so its presentation goes unmeasured

| Field | Value |
|---|---|
| Source | `MEAS` QEMU `COCOA_GL_LATENCY=1` logged no draws at all during 32 s of 60–120 fps guest output; `benchmarks/bin/winvis` (CGWindowList, by PID): the VM had 0 on-screen windows, while the native player `avplay` had its 1296×729 window on screen. |
| Observation | QEMU's display is a `CAOpenGLLayer`, and Core Animation calls its draw only while the window is on screen, which here means on the current Space. The VM window sat on another Space during the benchmark sessions, so QEMU drew nothing and WindowServer composited nothing. The `COCOA_GL_NOPRESENT` A/B therefore compared two non-presenting runs. Its "no difference" result says nothing about presentation cost. |
| Inference | Any VM display or power benchmark must record whether the VM window is on screen. `playback_power.py` now refuses to run without it (`--allow-hidden` overrides and labels the data). Earlier VM display-path numbers are hidden-window numbers. Guest-side work is unaffected. |
| Confidence | **Confirmed** |
| Linux mapping | Methodology (benchmarks) |

## F-050 · VM display · Intermittent vsync collapse to about 10 fps (open)

| Field | Value |
|---|---|
| Source | `BENCH` `vfill -f 0` (unpaced, swap interval 1): 3 of 6 fresh-boot sessions ran at 7–14 fps for the client's whole life, and one lasted 200 s. Warm sessions and 6 targeted reproductions ran at 120 fps. |
| Observation | During a collapse the guest is nearly idle (0.03–0.04 vCPUs) and Hyprland has the client mapped, fullscreen and visible. Ruled out by measurement: Omarchy's idle screensaver (no idle events in those boots' journals); toggling direct scanout (3 replays); the notification overlay layer (present in healthy runs too); CPU placement and cgroups; background CPU load; App Nap with the window hidden (60 s napped test at 120 fps). Mesa 26.2.4's EGL Wayland swap waits only on the compositor's frame callback (no fifo or commit-timing protocol), so the callbacks themselves arrived at about 10 Hz. |
| Inference | Something in the first minutes of some boots slows Hyprland's frame callbacks for an already-running client. Next: Hyprland debug logs (frame scheduling, `misc:render_unfocused_fps`) and QEMU fence timing captured during a collapse. Benchmarks record `vfill` fps, so a collapsed case is visible in the data. |
| Confidence | **Confirmed** (occurs); cause **Unknown** |
| Linux mapping | VM display path |
