# G17X GPU on t6050: scope and difficulty from the macOS 26.6.2 drivers (scope only)

2026-10-16, M5 REA session. Offline; nothing ran on the M5; macOS read-only (one `ls` of the Preboot firmware directory).
Inputs: `build/macos-drivers/members/AGXG17X.macho` (`e772f7d8…339b`, 3226 text functions with symbols),
`AGXFirmwareKextG17XRTBuddy.macho` (2 functions), `RTBuddy.macho` (symbols), the sanitized ADT, and the local m1n1 tree's
Rust GPU helper (`rust/src/gpu/`), which mirrors the asahi driver's firmware structures. Labels: Confirmed / Likely /
Hypothesis / Unknown. The asahi DRM driver itself is not in the pinned clone; the m1n1 mirror is the comparison basis.

## 1. Summary (honest assessment: not a near-term target)

1. **Generation and firmware are both outside what Linux knows** (Confirmed): the asahi-mirrored code enumerates
   `GpuGen::G13` and `G14` only (`rust/src/gpu/hw/mod.rs`, hw tables for t8103/t600x/t8112/t602x) and knows initdata
   sizes only for (G13, 12.3/13.5), (G14G, 12.4/13.5) and (G14X, 13.5) (`rust_gpu_initdata_size`). The M5 runs **G17X**
   with the **macOS 26.6.2** firmware (`armfw_g17x.im4p` 3,159,161 B and `armfw1_g17x.im4p` 3,224,761 B on Preboot, one
   per firmware role). Neither the generation-specific hardware tables nor the 26.x structure layouts exist.
2. **Two GPU firmware coprocessors** (Confirmed): `gfx-asc` (role `GFX`, `0x2102600000`) and `gfx1-asc` (role `GFX1`,
   `0x2102e00000`), each `iop,ascwrap-v6` with its own mailbox interrupts and the shared `mapper-gfx-asc` DART mapper; the
   `sgx` node carries both `gfx-data-*` and `gfx1-data-*` regions, the kext has `AGFIFirmwareRole` and `AGXG17CDevice`/
   `AGXG17SDevice`. A Linux driver must boot and feed two firmware instances.
3. **New blocks relative to G13/G14** (Confirmed as present, semantics Unknown): "Fender" (a GPU-side power/perf
   controller with its own register windows: `DFender CS/IVDM/MGPU Regs`, `GFenderCfg`, "Fender Scratch Region",
   `gpu-fender-idle-off-delay-ms`, "Fender Power Transition Regs (G16G only)" → introduced with G16/M4), "KSM" kick/
   completion queues (`AGXKSMKickQueueG17X`, `KSMCompletionQueue0..3`, channel classes `AGX{3D,CL,TA}ChannelSKSMG17X`),
   a UAT with an extra level (`fGPTBATPtr[gptbat_idx]`, `AGXUAT_TTBA_WORD0_{ASID,OUTPUTADDR,VALID}`, ADT `gptbat-ready`,
   `ttbat-phys-addr-base`, `agx-address-space-mgmt-mode`), three GART flavours (`AGXSecureGart`, `AGXGart`, `AGXLegacyGart`)
   and `AGXSecureMonitorG17X` (on macOS the UAT is an SPTM IOMMU class, `IOMMU_ID_UAT`, cf. the NVMe README).
4. **Firmware ABI version string**: not in the kexts (`AGXFirmwareKextG17RTBuddy::getVersion(AGFIFirmwareRole)` reads it
   from the firmware image loaded by iBoot: "GFX firmware was not loaded by iBoot" is a fatal check). The AP side exposes
   `SCMBuildTime`, `AGXTraceCodeVersion` and pool/element sizes (§3) only.
5. **Difficulty**: a new GPU generation (G15, G16 and G17 all unsupported upstream), a new UAT level, dual firmware,
   KSM/Fender, a firmware ABI thirteen macOS versions newer than the last supported one, and a shader ISA generation
   without a Mesa compiler. Expect multiple person-months for an experienced team with hardware tracing, before any
   acceleration. The VM path (VirGL/Venus at 94–99% of native in this project) remains the realistic parity route.

## 2. ADT facts (Confirmed; values of most `gfx-*` properties are sanitized away)

| Node | Facts |
|---|---|
| `/arm-io/sgx` | `gpu,t6050`; `reg[0] 0x2100000000+0x3fdc000` (GPU MMIO), `reg[1] 0x2100d00000+0x177000`; interrupts `0x990 0x991 0x992 0x993 0x1c2 0xaf6 0x99f 0x9a1`; power/clock gates `0x268 0x267`; regions `gfx-data-*`, `gfx1-data-*`, `gfx-data-shared-{ro,rw}-*`, `gfx1-data-shared-{ro,rw}-*`, `gfx-handoff-*`, `gfx-shared-region-*`, `gfx-shared-l2-region-*`, `gpu-region-*`, `rtkit-private-vm-region-*`, `ttbat-phys-addr-base`; `gptbat-ready`, `has-kf`, `active-mcc-bit-vector`, `function-mcc_dataset`; perf tables `perf-states`, `perf-states1..3`, `perf-states-sram`, `perf-states-sram1..3`, `afr-perf-states`, `cs-perf-states`, `gpu-num-perf-states`, `gpu-perf-base-pstate`, `gpu-pwr-perf-scale0/1`, `gpu-supports-higher-mA` |
| `/arm-io/gfx-asc` | `iop,ascwrap-v6`, role `GFX`, `reg 0x2102600000+0x88000`, `0x2102050000+0x8`; interrupts `0xaee 0xaed 0xaf0 0xaef`; `segment-names __TEXT;__DATA`, `segment-ranges` (firmware `__TEXT` at `0x1000000`, `__DATA` at `0x26f0000`); nub `iop-gfx-nub` |
| `/arm-io/gfx1-asc` | role `GFX1`, `reg 0x2102e00000+0x88000`, `0x2102850000+0x60000`; interrupts `0xaf2 0xaf1 0xaf4 0xaf3`; firmware `__TEXT` at `0x104c000`, `__DATA` at `0x2820000` |
| `/arm-io/mapper-gfx-asc` | `iommu-mapper,gfx` (shared by both ASCs) |

m1n1's `kboot_gpu.c` (local tree) handles `/arm-io/sgx` only for T8103/T8112/T6000/T6020 chip ids (perf states, the
`uat-handoff`/`uat-pagetables`/`uat-ttbs` reserved regions, `apple,firmware-abi`) — t6050 is absent there too.

## 3. What the AP kext shows about the firmware interface (Confirmed; pseudocode in `evidence/AGXG17X-firmware-data-batch.txt`)

* Firmware data is allocated as "shared data" regions through a descriptor list (`AGXFirmware::allocateSharedData`
  `0xfffffe00089474f8`): entries of 0x18 bytes `{host ptr*, gpu addr*, type, size, offset}`, each region 64-byte aligned,
  the whole block page-rounded and mapped with `0x23`/`0x22` option bits; `AGXFirmware::allocFirmwareData`
  (`0xfffffe000894a8c8`) creates pools of 64 blocks × 256 entries (`AGXFirmwareResourceStack<…,64,256>`) for
  `AGFITimeStampQueue` (0x18-byte entries), `LateEvalEventSignal` (8), `AGFIChannelState` (0xc0), and cached/uncached
  firmware channel memory of `channels·128 + 0x70` bytes (channel count from the accelerator config, `+0x11160` or
  `+0x718`).
* `AGXFirmware::configurePoolElementSizes` (`0xfffffe0008941d5c`): element sizes `0x9c0, 0xa00, 0x2240, 0x80, 0x1040,
  0x40, 0x80, 0x40, 0x80, 0x40, 0x40, 0x40, 0xc0, 0x40` (the firmware-visible command/record structures of this ABI;
  the asahi 13.5 equivalents are not available offline for a field-level comparison).
* `AGXArmFirmware::initFirmwareSharedData` (`0xfffffe000895fc04`) publishes GPU addresses of nine allocations into two
  firmware-visible tables (`+0x254…+0x274`, `+0x2d0` when the optional region at config `+0x13768` exists; `+0x0/+0x8/
  +0x10/+0x200` of two per-role tables) — the G17 analogue of asahi's `initdata` pointer block, with two copies (one per
  firmware role; Likely).
* The AP-side accelerator config object spans at least `0x1cb34` bytes (`setupMMUConfig` reads `+0x1cb30`;
  `initPowerAndPerformanceData` fills `+0x1b340…+0x1cb20`), i.e. the per-SoC configuration (perf states, power
  coefficients) is larger than the G13/G14 `HwDataA/B` the asahi driver fills.
* The earlier project pass saw GPU kick notification constants `0x83`/`0x87` with `(argument & 7) << 2` payload bits in
  the G17 kick code (`driver-interfaces-2026-10-13/handoff.md`); they are not mapped to asahi's doorbell messages here.

## 4. What would be needed (scope, not a plan)

| # | Item | Label |
|---|---|---|
| 1 | m1n1: t6050 in `kboot_gpu.c` (perf-state tables incl. `perf-states1..3`/`sram1..3`, the UAT regions, `gptbat`/`ttbat` handling), dual-ASC firmware region handoff (`gfx-data-*` and `gfx1-data-*`) | Likely required |
| 2 | asahi driver: `hw/t6050` tables for G17X, a `V26_6` structure version for every firmware struct (initdata, channels, work/commands), dual-firmware boot, KSM kick queues, Fender power control, the GPTBAT UAT level | Confirmed (scope) |
| 3 | Firmware images: `armfw_g17x.im4p`/`armfw1_g17x.im4p` are the inputs for the structure work (im4p-wrapped, not opened here) | Confirmed |
| 4 | Mesa: a G17 ISA backend/compiler; unknown delta from G13/G14 (`has-kf`, `procedural-antialiasing`, `metal-standard` hints only) | Unknown |
| 5 | Without the SPTM, Linux programs the UAT itself (as on M1); whether the G17 UAT requires the GPTBAT indirection even in that mode is Unknown | Unknown |

## 5. Open questions

1. The firmware ABI string inside `armfw_g17x.im4p` (next pass: DER/LZFSE unwrap as done for the SPTM, then strings).
2. Whether `gfx1-asc` is a second compute cluster's firmware or a dedicated role (e.g. compute/secure) — `AGXG17CDevice` vs `AGXG17SDevice`.
3. The meaning of the `sgx` `reg[1]` window (`0x2100d00000+0x177000`): Fender registers or performance counters.
