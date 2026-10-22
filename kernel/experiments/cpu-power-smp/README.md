# CPU power on t6050: SMP start, idle, DVFS and the PMGR↔PMP path, from this Mac's macOS 26.6.2 drivers

> Historical October15 research. This repository is now public. The broad
> claims below about PMGR-only startup, reset entry and unconditional WFI
> power-down were superseded by later bounded evidence; do not use its old
> native-test recipe. See the [October19 correction](../../../reverse-engineering/findings/cpu-startup-2026-10-19/README.md),
> [31L firmware review](../../../research/native31l-first-fetch.md), and
> [platform preparation review](../../../research/native31l-platform-prepare.md).
> Only the current M1 handoff authorizes the next experiment.

2026-10-15, M5 REA session. **Offline analysis only: nothing here has run on the M5.** Every
proprietary input (kernel-collection members, pseudocode, disassembly, live-registry dumps) stays
in the ignored `build/macos-drivers/`; this directory holds original code, tests and prose.
Private project: no upstream contribution, no code copied from Apple binaries, from
`betizzel/omarchy-m5` or from GravityLinux PR #1.

| | |
|---|---|
| Binaries | `com.apple.driver.AppleT6050PMGR` (derived member sha256 `45e8d9c2…143e`), `com.apple.driver.ApplePMGR` (`a74c641b…b0f`), `com.apple.driver.AppleARMPlatform` (`f8cba090…6932`), all from the decoded Preboot kernelcache of macOS 26.6.2 (25G83), payload sha256 `26ddfbe9…b093`; `kernel.release.t6050` (standalone XNU, same build) for the reset-vector and WFI code |
| Method | REA 6.4.0 + Ghidra 12.1.4 pseudocode, re-read in raw assembly (`procedure_assembly`, `llvm-objdump`) wherever a claim below is Confirmed; vtable slots resolved with the format-8 chained-pointer parser (`evidence/vtable-*.txt`); sanitized ADT (`hardware/adt/adt-sanitized.json`) plus read-only `ioreg` for the few PMGR/PTD properties the sanitizer dropped |
| Labels | **Confirmed** = pseudocode *and* an independent check (assembly, ADT value, live registry or public source); **Likely** = one strong source; **Hypothesis**; **Unknown** |
| Public references (not copied) | m1n1 `57a9339` (`src/smp.c`, `src/start.S`, `src/cpufreq.c`, `src/cpu_regs.h`), AsahiLinux `77cb8f24` (`drivers/cpufreq/apple-soc-cpufreq.c`, `drivers/cpuidle/cpuidle-apple.c`, `arch/arm64/boot/dts/apple/t8112.dtsi`) |

Addresses are kernelcache virtual addresses with the `0xfffffe00` prefix dropped
(`09880a64` = `0xfffffe0009880a64`). Evidence files: `build/macos-drivers/evidence/notes-pmgr.md`
(running notes), `ApplePMGR-batch1.txt`, `vtable-ApplePMGR.txt`, `vtable-AppleT6050PMGR.txt`,
`kernel-text.asm`.

## 1. Summary

1. **Secondary start is PMGR-only.** macOS starts a core by writing two PMGR registers and nothing
   else: no RVBAR write anywhere in `AppleARMPlatform`, `ApplePMGR` or the kernel. The reset vector
   of a secondary is the *boot object's entry point*; XNU's `__TEXT_BOOT_EXEC.__bootcode` entry
   dispatches on the arrival reason in `x0`. m1n1's entry point is `_start`, which is not prepared
   for that. Patch `m1n1/0001` makes it so and records how a core arrived. (§2)
2. **m1n1's start-bitmap packing is wrong for t6050.** The per-die start/stop bitmaps use one
   field per cluster whose width and position come from the ADT `clusters` descriptor,
   `(6,0) (6,6) (6,12)` here, i.e. bit = `6*cluster + core`. m1n1 uses `4*cluster + core`, which
   aliases four core pairs. Patch `m1n1/0002` reads the descriptor. (§2.2)
3. **WFI is a power-down on this SoC.** The kernel has exactly one idle/sleep WFI routine; it never
   returns and the core resumes only through the reset vector. XNU does not touch `CYC_OVRD` at
   all. Linux's `idle=nop` stays until a reset-vector-aware idle path exists. (§3)
4. **CPU DVFS is the M2/M3 register interface, with the p-state index shifted by two.** The cluster
   command register is at `0x2_1Xe20020`; macOS writes `DESIRED1 = 2 + state` with `SET` (bit 25).
   Our draft DT's `opp-level = index + 1` is therefore one too low (patch `dt/0001`, Likely). (§4)
5. **PMGR talks to the PMP coprocessor through the PTD block**, not through the mailbox:
   device power-state requests are bits in PTD entries, acknowledged by the PMP. Linux's
   `pmgr-pwrstate` has no such path. Which domains need it is the ADT `notify_pmp` flag. (§5)

## 2. SMP: how macOS starts and stops a core

### 2.1 Call chain (Confirmed, pseudocode + vtable + ADT)

| Step | Where | What |
|---|---|---|
| `AppleARMCPU::startCPU` | AppleARMPlatform `08a51100` | calls the ADT platform function `function-enable_core` (`ApplePMGRFunctionEnableCPUCore`, this+0xd8) with argument 1. Nothing else. `quiesceCPU` (`08a51094`) calls it with 0. |
| `ApplePMGRFunctionEnableCPUCore::callFunction` | ApplePMGR `094bc62c` | `pmgr->enableCPUCores(mask, enable)` (vtable slot 0xa88); `mask` is the function's ADT argument, `BIT(cpu-id)` for every CPU node (ADT: `function-enable_core = <&pmgr 'Core' BIT(cpu-id)>`, 18 nodes). |
| `ApplePMGR::enableCPUCores` | `0949606c` | takes the per-complex locks, calls `configMiscCores(mask, enable)` (slot 0xd18), updates the per-complex enabled-core bookkeeping. |
| `ApplePMGR::configMiscCores` | `09495968`, **assembly** (`procedure_assembly`, 449 instructions; pseudocode rejected as in the 2026-10-13 pass) | the only hardware writes, see 2.2. |

The `cpu-impl-reg` window (RVBAR mirror) is read by nothing on the start path. `AppleARMPlatform`'s
strings reference `cpu-id`, `cluster-type`, `no-aic-ipi-required`, `function-cpu_idle`,
`function-enable_core`, `max_cpus`; nothing about reset vectors. **Confirmed (static).**

### 2.2 Register writes (Confirmed, assembly of `configMiscCores`)

All writes go through `writeReg32(RegMap, offset, value, die)` on the register group
"misc-cores" (`this+0x5e10`, RegGroup 8): `map = group.map`, `base = group.offset`.

| Register | Written when | Value |
|---|---|---|
| `base + 0x0` | `enable == false` | per-die bitmap of the cores to stop |
| `base + 0x4` | `enable == true` | per-die bitmap of the cores to start ("start/status") |
| `base + 0x8 + 4*cluster` | `enable == true`, per cluster | mask of cores within the cluster |

Bitmap packing, both code paths agree:

* `this->0x238c != 2` path: fields packed with the `clusters` descriptor at `this->0x6310`
  (`{u16 width, u16 pos}` per cluster; `pos == 0` on a later cluster means `i * default stride`):
  `bitmap |= (mask & ((1 << width) - 1)) << pos; mask >>= width`.
* `this->0x238c == 2` path: bit position = per-core record byte 5 = the ADT `acc-cores` physical
  core number (`acc-cores`: 18 records `{u32 id, u8 0, u8 physCore, u8 coreInCluster, u8 cluster}`,
  physCore = `6*cluster + core`), cluster register index from the complex record.

ADT `/arm-io/pmgr clusters = 06 00 00 00 06 00 06 00 06 00 0c 00` → `(6,0) (6,6) (6,12)` →
start bit = `6*cluster + core`, 18 distinct bits 0..17. m1n1 `smp.c` writes the same three
registers (`CPU_START_OFF_T6031 = 0x88000` from PMGR `reg[0]`, so `0x2_80688000..`) but packs
`1 << (4*cluster + core)`: cores (1,0),(1,1),(2,0),(2,1) alias (0,4),(0,5),(1,4),(1,5).
`m1n1/test_start_bits.py` models both and checks the ADT. **Confirmed** (two independent ADT
tables agree with the descriptor interpretation and with the assembly).

Where `group.offset` for misc-cores comes from on this class is **Unknown**: the generic
`AppleBringUpPMGR::initRegGroups` (`094b4f2c`) reads ADT `cluster-ctl-offset`, `misc-cores-offset`,
`misc-acg-offset`, none of which exist in our ADT, and no `0x88000` immediate occurs in either PMGR
member. m1n1's 0x88000 is kept (its cores do power on, m1n1 PR #610).

### 2.3 Where a started core goes (Confirmed static, Likely for raw mode)

`kernel.release.t6050` (`LC_UNIXTHREAD pc = 0xfffffe0007ca0000`) puts its entry in a separate
segment `__TEXT_BOOT_EXEC.__bootcode`. The first instructions (`evidence/kernel-text.asm`):

| `x0` on arrival | Path |
|---|---|
| 0 | cold boot: set stacks `0x..7e88000/0x..7e80000`, `VBAR_EL1`, jump to `0x..74f6114` with `x1,x2` from arrival |
| 4 | store `w2` to a byte, `x0 = x1`, branch to `__bootcode+0x4000` |
| other | **reset handler**: `x20 = x3`; `MPIDR_EL1 & 0xffff` looked up in a 36-entry table at `0x..7d596e8` (entry+8 → `cpu_data`, compared with `cpu_data+0x1d0`); stacks from `cpu_data+0x28/+0x18`; `cpu_data+0xb8` must be one of two handlers (`0x..74f867c`, `0x..74f8c54`) else spin with `x0 = 0xdeadb001`; unknown MPIDR → `0xdeadb002` |

So on this SoC the hardware reset vector *is* the boot object's entry (locked by mBoot; XNU never
programs it) and the OS entry code distinguishes cold boot from secondary start and idle resume.
In macOS mode SPTM sits in between (GL2) and supplies `x0`; in raw mode (what m1n1 boots) nothing
does, so the values of `x0..x3` on arrival are **Unknown**. m1n1's entry `_start` sits at
`_vectors_start + 0x800` (public `start.S`; confirmed by assembling it) and re-runs the cold path on
the boot CPU's stack if a secondary arrives there. m1n1 only warns when the locked RVBAR differs
from `_vectors_start` and then starts the core anyway. **Hypothesis H1 refined:** the secondaries
of PR #610 arrived at `_start` (or at a firmware trampoline that jumps there) and corrupted or
hung; the spin-table flag was never reached.

### 2.4 Deliverables

* `m1n1/0001-smp-route-late-entries-at-_start-through-cpu_reset.patch`: a gate in the shared
  Device-nGnRnE section (`smp_entry_gate`, set at the end of `smp_init()`); a core that reaches
  `_start` with the gate open stores `MPIDR`, `x0..x3` and a count into `smp_entry_log[cluster*8+core]`,
  prints `L` on the early UART and continues on `cpu_reset` (existing reset path: per-MPIDR stack
  or `_reset_stack`, then `_cpu_reset_c` → `smp_secondary_entry` → spin table). A failed start now
  prints whether and how the core entered `_start`. Original code; no Apple sequence used.
* `m1n1/0002-smp-pack-t6050-start-bitmaps-from-ADT-clusters.patch`: for T6050/T6051 only, parse
  the PMGR `clusters` descriptor (validated: no overlap, inside 32 bits, default stride for a zero
  position) and use `pos(cluster) + core` for the `+0x0` and `+0x4` writes. Other SoCs unchanged.
* `m1n1/apply_and_check.py`: verifies the pinned commit and digests, applies both patches to a
  scratch copy, compiles `smp.c` with m1n1's flags for aarch64 and assembles `start.S` with Xcode's
  clang, checks the new symbols. **PASS** on this host (`build/macos-drivers/m1n1-check*`).
  `m1n1/test_start_bits.py`: **PASS**.
* **Native test (M1 agent, needs the user's approval, one filmed RAM attempt):** boot a m1n1 with
  both patches, let `smp_start_secondaries` run (the launcher currently never requests it), read
  `smp_entry_log` and the spin table over the proxy. Outcomes: (a) flags set → SMP works, keep;
  (b) entries logged, flags not set → entry reached but `cpu_reset` path fails, read `x0..x3`;
  (c) nothing logged → the locked RVBAR points elsewhere, needs the hypervisor census to read
  `cpu-impl-reg`+0 (`0x2_10050000` for cpu0) before anything else.

Not derived from these patches: the CTRR reservation, the secondary watchdog and the
`idle=nop arm64.nowfxt` boot arguments stay exactly as m1n1 `kboot.c` sets them.

## 3. Idle: what WFI means on t6050

| Fact | Evidence | Label |
|---|---|---|
| The whole kernel text contains two `wfi` instructions: `0x..72f8368` inside routine `0x..72f8310` and a plain `wfi; cbz x30, ..; ret` helper at `0x..72f8394`. | `evidence/kernel-text.asm` (2.56 M lines, `grep wfi`) | Confirmed |
| Routine `0x..72f8310(x0)`: `x0==0` → `S3_4_C15_C10_4 = (v & ~3) \| 3` (m1n1 `SYS_IMP_APL_SIQ_CFG_EL1`), `S3_1_C15_C7_4 &= ~1`; `x0!=0` → `S3_5_C15_C6_2 \|= 1 \| BIT(63)`; then `loop: dsb sy; isb; wfi; msr S3_5_C15_C1_1, #1 (IPI_SR ack); b loop`. It never returns. | same, lines 7345–7390 | Confirmed |
| Callers: `0x..74fb41c` (idle path) and `ml_arm_sleep` (`0x..74fbed8`, `0x..74fbf40`). | same | Confirmed |
| No access to `CYC_OVRD` (`S3_5_C15_C5_0`) anywhere in the kernel text: the M1–M3 "deep WFI by CYC_OVRD" sequence (Linux `cpuidle-apple.c`, m1n1 `deep_wfi`) is not used on t6050. | `grep S3_5_C15_C5_0` → 0 hits | Confirmed |
| Resume goes through the `__bootcode` reset handler (§2.3) to `cpu_data+0xb8`. | §2.3 | Confirmed |
| The PMGR idle hooks (`function-cpu_idle` → `ApplePMGRFunctionCPUIdle::callFunction` `094bbd98` → `_cpuIdle(core, complex, enter, arg)` `094ae92c`) do bookkeeping, perf-state accounting and ring a PMP doorbell when the last core of a complex idles; `AppleT6050PMGR::cpuComplexIdleEnter/Exit` (`09882068`/`0988216c`) only wait for the cluster DVFS command register to be not-busy. No register that would make WFI retain state is written there. | pseudocode | Confirmed |

**Linux consequence (Likely):** every WFI on t6050 is a core power-down with a reset-vector
resume, which is why Asahi runs M4+ with `idle=nop arm64.nowfxt`. A cpuidle driver needs
`cpu_suspend()`-style context save plus a way back: the core will re-enter the boot object at its
entry (m1n1 `_start` → `cpu_reset` with patch 0001) and m1n1 must hand it to Linux's resume entry.
That is exactly the PSCI `CPU_SUSPEND` shape of Sven Peter's PSCI-via-EFI RFC (m1n1 branch
`psci-via-efi`, Linux `efi-psci`), so the design recommendation is: implement nothing cpuidle-side
until that conduit is in our tree; then `CPU_SUSPEND` = m1n1 parks the core with the routine above
(IMPDEF writes as listed, no `CYC_OVRD`) and the reset path returns to the saved context. The
IMPDEF registers above are the ones to mirror; their semantics are **Unknown** beyond their names.

## 4. DVFS (cpufreq)

### 4.1 Register interface (Confirmed unless noted)

| Item | Value | Evidence |
|---|---|---|
| Cluster window | `0x2_1X000000` (X = 0 M0, 1 M1, 2 P), 16 MiB; macOS addresses it as "ACC selector" offsets | `AppleT6050PMGR::_macc0Mapping/_macc1Mapping/_paccMapping` data (`07633770..`, 11 entries each `{u32 RegMap, u32 base}`): 0xe50000, 0xe20000, 0xe70000, 0x050000+n·0x100000 (cores), 0xf00000 (acc-impl), 0xe40000 (cpm) |
| DVFS command register | selector `0xe20020` → `0x2_1Xe20020` = ADT pmgr `reg[16/26/36]` (`0x10e20000` +0x20) | `readACCReg` (`09884934`) resolves selector→(RegMap, offset); matches m1n1 `CLUSTER_PSTATE 0x20020` and the draft DT `performance-controller@21Xe20000` |
| `DESIRED1` field | bits [4:0]; `SET` = bit 25; `BUSY` = bit 31 (polled); `APSC_DIS` = bit 23; `APSC_BUSY` = bit 7 | `setPerfState` (`09883554`): `v = (v & ~0x1f) \| (idx & 0x1f) \| 0x2000000`; `_waitAPSCPending` polls bit 31; `enableAPSC` (`09880b30`) toggles bit 23 and waits bit 7 — same bits as m1n1 `cpufreq.c` for M2+ |
| p-state index written | `idx = 2 + PerfState` for the CPU domains (ids 5 PCPU, 0x16 MCPU0, 0x17 MCPU1); domain 1 → 3+state, domain 3 → 6+state | `getPerfStateTableIndex` (`098838b0`, vtable 0xe48) |
| PerfState ↔ frequency | `perfStateToFrequencyMHz(domain, state)` = `freq[state]` of the domain's table; the table has one entry per ADT `voltage-statesN` row (15 for M, 20 for P, F-022) | `0948e494`, `_initPerfDomainInfo` (`0948be34`, IOReport "DVFMStates" StateID = index) — **Likely** that index 0 is the first ADT row (no synthetic entry seen) |
| Cluster selection | ADT `perf-domains` records (28 B: `{u8 id, u8 type, u8 flag, u8 voltage-states idx, u32, u32, name[16]}`): PCPU id 5 → `voltage-states5`, MCPU0 0x16 → 22, MCPU1 0x17 → 23; `acc-clusters` = (0x16,0),(0x17,1),(5,2) | ADT decode, matches F-022 |
| Post-wake register | `restoreACC` writes selector `0xe440f8` = 1 (cpm window +0x40f8) — m1n1 `cpufreq_init_cluster` does the same write for T6030+ at boot | `098804a8` |
| Voltage | handled by hardware/DVFM; macOS checks `PMGR_VOLMAN_STATUS` (map 0 +0x50054 on the CPU die, map 0x82 +0x50054 on the GFX die) for `DVC_DONE_ERR` | `panicOnDvcDoneErr` (`09883fec`) |

### 4.2 Linux delta

* Draft DT (`t6050.dtsi`): `apple,t6050-cluster-cpufreq`, `apple,t8112-cluster-cpufreq` fallback,
  `reg = <0x2 0x1Xe20000 0 0x1000>` — **consistent** with the above (the t8112 info struct uses the
  5-bit `PS1` field, `BUSY` bit 31, `SET` bit 25).
* `dt/0001-t6050-dt-opp-level-is-pstate-index-plus-2.patch` (against the generator
  `kernel/experiments/t6050-dt/gen_t6050_dt.py`): `opp-level = index + 2`, since the driver writes
  `opp-level` into `DESIRED1` and reads the current p-state back to find its OPP. **Likely**; the
  M1–M3 convention is `index + 1`. Verify natively by reading `0x2_1Xe20020` through the proxy
  before Linux changes anything (expected: `DESIRED1` in 2..16 for M, 2..21 for P).
* Not needed for a first cpufreq: the PMC perf-state floors (`AppleT6050PMC::writePerfStateCtlFloor`,
  `(domain << 14)`), the DVFM coprocessor interrupt (`_handleDVFMCopInterrupt`, map 0x85 +0x38004),
  CLPC policy. Unknown whether the firmware/DVFM honours a Linux request without the PMC floor
  (**Unknown**).

## 5. PMGR cluster power, interrupts and the PMP

| Fact | Evidence | Label |
|---|---|---|
| SoC-cluster power state register: `enableCluster(id, on, wait, die, ..)` writes the low nibble (0xf on / 0 off) of `RegMap this->0x5d84` at `this->0xbb1 + 4*physId`, waits for bit 4 clear; `getClusterPowerState` = reg & 0xf. Ids: ADT `soc-clusters` `DISP_INT`(0) `MACC0`(1) `MACC1`(2) `PACC`(3) `DISP_EXT`(4). `configCPUComplexPowerState(c, on)` → `enableCluster(physInDie+1, …)`. | `0949e47c`, `09880a64` | Confirmed (pseudocode; map/offset values not resolved: Unknown) |
| Cluster power-up completion is an interrupt: ADT pmgr `interrupt-config` (live ioreg) `irq[2..5]` = AIC 263/264/265/267 = `MACC0_PWRUP`, `MACC1_PWRUP`, `PACC_PWRUP`, `DISPEXT_PWRUP`; `irq[0]` AIC 471 `DVFM_COP`; `irq[1]` AIC 416 `PMP_STATUS`. Handler marks the cluster 0xf and clears status bit 5 of its register. | `_handleInterruptAll` (`094853fc`), `clearClusterInterruptStatus` (`0949e298`) | Confirmed |
| CPM power-domain gating: SOC PwrGate regs `0x120 + 8*complex`, bit 31 (`enableCPMPowerDomainGating`); `restoreHW` sets bit 31 of PwrGate `0x0` and `0xc0`. | `0988220c`, `0987fd8c` | Confirmed (semantics Unknown) |
| Register map: `initRegMaps` (`0987ea54`) maps 60 RegMap ids onto the 60 ADT pmgr `reg` entries (table in `evidence/notes-pmgr.md`), e.g. RegMap 0 → `reg[0]` 0x2_80600000, 1 → `reg[9]` 0x2_88300000, 0x82 → `reg[46]` die-1 0x21_80600000, 0x2c → `reg[16]` M0 DVFS. | pseudocode, ADT reg count 60 | Confirmed |
| PMP: ADT `pmp = 2` → `_pmpV2()` path. `_sendPMPCommand` 0xe/0xf (device state) → `_pmpWriteDashBoard` → `_pmpWriteDashBoardSetDeviceState`: read PTD entry "SOC-DEV-PS-REQ", set/clear bit `pmpDevHandle`, write it, then poll PTD "PMP-STATUS" and "SOC-DEV-PS-ACK" (bit 54 = new data) every 100 µs, 15 s deadline, panic on timeout. PTD = `ApplePTD` on `/arm-io/aon-ptd` (`ptd,v1`, regs `0x2_8cdc0000/0x2_8cdd0000/0x2_8cdd8000/0x2_8cde0000` +0x4000, 32 IRQs 0x388–0x3a7; pmgr `ptd-ranges = 10 11 12 13 2 4`). | `09491…`, `094a5…`, live ioreg | Confirmed (mechanism); entry indices Hypothesis |
| Which devices: ADT device flag bit 1 (`notify_pmp` in m1n1's `PMGRDeviceFlags`), 27 of the 152 Stage-B unclaimed domains carry it (genpd experiment). `_checkNotifyPMP` also walks parents. | `094a8510`, `094a86e4` | Confirmed |
| PMP doorbells for idle: value regs at PMGR map 0 `0xb8000 + 4*idx`, then a bit in the PMP wrapper block (map 7 = `reg[7]` 0x2_84240000) at `(idx>>3)&~3`, bit `idx & 31`. | `_ringPMPDoorbell` (`094a3…`) | Confirmed |

**Linux consequence:** our `pmgr-pwrstate` writes PS registers without telling the PMP. The
attempt-14/15 resets followed power-offs of PMGR domains; whether a missing PTD request matters
is **Hypothesis** (the stable attempt 16 released 74 domains without it). A PTD-aware driver needs
the entry indices (`aon-ptd ptd_data_table`, 193 records `{tag[4], u16, u8, u8, u8, u8, u16}`,
saved in `evidence/aon-ptd-ptd_data_table.hex`) and the PMP device-handle table, which macOS
obtains from the PMP firmware (`function-pmp_control` selector 2 energy nodes) — both **Unknown**
to us today. Scoped as a follow-up, not needed for the next boots.

## 6. Open questions (Unknown)

1. Value of the locked RVBAR on t6050 and what mBoot/raw mode puts in `x0..x3` on a secondary's
   entry (§2.3). Only a native read answers it.
2. The misc-cores and cluster-ctl register-group offsets as set by `AppleT6050PMGR` (m1n1 uses
   0x88000 for the former).
3. Whether PerfState 0 is the first `voltage-states` row (decides +2 versus +1, §4).
4. Whether the PMC floor/`DVFM_COP` must be programmed for Linux p-state requests to take effect.
5. PTD entry indices and PMP device handles (§5).
6. Semantics of `SIQ_CFG_EL1` bits [1:0], `S3_1_C15_C7_4` bit 0 and `S3_5_C15_C6_2` bits 0/63
   written before the kernel's WFI (§3).

## 7. Reproduce

```sh
# derived members (read-only extraction from the decoded Preboot kernelcache; output is gitignored)
python3 -I build/macos-drivers/scripts/derive.py com.apple.driver.ApplePMGR com.apple.driver.AppleT6050PMGR com.apple.driver.AppleARMPlatform
# REA: open build/macos-drivers/members/<member>.macho (provider ghidra) and decompile the addresses in §8
# vtables
python3 -I build/macos-drivers/scripts/vtab.py AppleT6050PMGR AppleT6050PMGR 600
# offline checks for the deliverables
python3 -I kernel/experiments/cpu-power-smp/m1n1/test_start_bits.py
python3 -I kernel/experiments/cpu-power-smp/m1n1/apply_and_check.py ../apple-silicon-linux-research/third_party/m1n1 build/macos-drivers/m1n1-check-$(date +%s)
```

## 8. Evidence index

| Function | Address | Member |
|---|---|---|
| `AppleARMCPU::startCPU` / `quiesceCPU` / `initCPU` / `_processorIdle` | `08a51100` / `08a51094` / `08a50f9c` / `08a50dc8` | AppleARMPlatform |
| `ApplePMGRFunctionEnableCPUCore::callFunction` / `ApplePMGRFunctionCPUIdle::callFunction` | `094bc62c` / `094bbd98` | ApplePMGR |
| `ApplePMGR::enableCPUCores` / `configMiscCores` / `enableCPUCore` / `enableCPUComplex` / `enableCPUCluster` | `0949606c` / `09495968` / `094964a4` / `09496304` / `09496524` | ApplePMGR |
| `ApplePMGR::enableCluster` / `getClusterPowerState` / `clearClusterInterruptStatus` / `_handleInterruptAll` | `0949e47c` / `0949e3bc` / `0949e298` / `094853fc` | ApplePMGR |
| `ApplePMGR::initRegMap` / `getRegMap` / `readReg32` / `readReg64` / `getRegGroupOffset`; `AppleBringUpPMGR::initRegMaps` / `initRegGroups` | `0947d30c` / `09489678` / `094987ec` / `09497790` / `094985e8`; `094b4e44` / `094b4f2c` | ApplePMGR |
| `ApplePMGR::_cpuIdle` / `_cpuIdleInit` / `getCurrentCoreComplex` | `094ae92c` / `094af5e0` / `0948e7a4` | ApplePMGR |
| `ApplePMGR::initPMP` / `_sendPMPCommand` / `_pmpWriteDashBoard*` / `_ringPMPDoorbell` / `_checkNotifyPMP` / `_notifyPMPInitialDeviceStatusGated` | `0948f0d4` / `09491c..` / `094a41f0`,`094a5..` / `094a3..` / `094a8510` / `094a86e4` | ApplePMGR |
| `ApplePMGR::perfStateToFrequencyMHz` / `_initPerfDomainInfo` | `0948e494` / `0948be34` | ApplePMGR |
| `AppleT6050PMGR::initRegMaps` / `initDriver` / `configCPUComplexPowerState` / `enableAPSC` / `setPerfState` / `perfStateChangePending` / `getPerfStateTableIndex` | `0987ea54` / `0987f168` / `09880a64` / `09880b30` / `09883554` / `09883798` / `098838b0` | AppleT6050PMGR |
| `AppleT6050PMGR::readACCReg` / `writeACCReg` / `_getACCMappingAndLength` / `_getAccMapping`; mapping tables | `09884934` / `09884b74` / `098848bc` / `09884704`; `07633770` | AppleT6050PMGR |
| `AppleT6050PMGR::cpuComplexIdleEnter` / `Exit` / `enableCPMPowerDomainGating` / `quiesceHW` / `restoreHW` / `restoreACC` / `panicOnDvcDoneErr` / `_handleDVFMCopInterrupt` | `09882068` / `0988216c` / `0988220c` / `0987f720` / `0987fd8c` / `098804a8` / `09883fec` / `09880354` | AppleT6050PMGR |
| `AppleT6050PMC::writePerfStateCtlFloor` / `readClusterReg` / `writeClusterReg` / `enableRMBS` | `0988582c` / `098859d0` / `09885a08` / `09885b04` | AppleT6050PMGR |
| kernel `__bootcode` entry / idle WFI routine / `_ml_arm_sleep` | `07ca0000` / `072f8310` / `074fbda8` | kernel.release.t6050 |
