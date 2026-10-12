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
