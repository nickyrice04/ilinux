# Hardware Compatibility Matrix: M5 Max (t6050) vs Linux

Snapshot 2026-10-11. Evidence sources:

* `ADT`: sanitized device tree (`hardware/adt/`)
* `IOReg`: macOS driver class bound to the node (`hardware/adt/driver-map.tsv`)
* `ML`: mainline Linux master
* `AS`: AsahiLinux/linux `asahi` branch (pushed 2026-09-27)
* `BENCH`: our measurements
* `AR`: Asahi status report (`research/asahi/asahi-status-m5-2026-10.md`)

Status vocabulary:

* **Supported**: works on this SoC today.
* **Driver exists (other SoCs)**: code exists, but this SoC is untested and
  there's no DT.
* **Partial**: some pieces exist.
* **Missing**: no code.
* **Blocked**: depends on an unavailable interface.

**No subsystem is "Supported" on t6050.** m1n1 has initial T6050 support
(single core). There is no device tree or kernel bring-up in any tree.

## Summary

| # | Subsystem | ADT compatible → macOS driver (IOReg) | Linux driver (ML / AS) | t6050 status | Complexity | Perf impact if missing |
|---|---|---|---|---|---|---|
| 1 | Boot chain (m1n1, DT) | `J716cAP`, `arm-io,t6050`, firmware `mBoot-18000.161.10` | m1n1 **initial T6050/T6051 support** (PR #610, 2026-06-29; mBoot firmware support PR #559; SPTM/SPRR/GXF emulation in the hypervisor PR #643). No t60[45]x/t8142 DT in any tree (AS has a minimal t8132 DT). **Local draft t6050 DT** generated from the ADT (`kernel/experiments/t6050-dt/`, 0 dtc warnings, never booted). Laptop console = dockchannel UART over debugusb (no Linux driver, F-025); m1n1 leaves DCP alone on firmware ≥ 15, so Linux gets mBoot's framebuffer | **Partial**: m1n1 runs; DT is a local draft only; no kernel bring-up | High | Total, since Linux doesn't boot |
| 2 | CPU cores / SMP | `apple,sawtooth` (M) ×12, `apple,everest` (P) ×6; 3 clusters | spin-table SMP via m1n1; `cputype.h` part IDs. m1n1 PR #610: secondaries power on but **never run code** (June 2026). Mainline `idle=` (7.3) for mBoot-locked chicken bits and WFI state loss. MPIDR encoding: M cores 0x4XXYY, P cores 0x1XXYY (m1n1 `5d84c4c3`, F-019). ADT `function-enable_core = <pmgr 'Core' BIT(n)>` (F-020). Still no fix in m1n1 `main` @ `57a9339` | **Blocked** (SMP root cause Unknown, hypotheses in `kernel/native-enablement/plan.md` §1.2; MIDR unknown, and VMs mask it as part 0x000) | High | Single core at best |
| 3 | Interrupts | `aic,3` → `AppleInterruptControllerV3` | `irq-apple-aic` `apple,t8122-aic3` (ML+AS); AS t8132 reuses it, same 0x1cc000 core size. ADT: IRQ_CFG at +0x10000 and per-die stride 0x4a00 match the Linux AIC3 layout; `aic-numdies-per-die = 2` (second die, F-024) | **Driver exists (other SoCs)**, likely compatible. Open: 4-cell specifiers for die-1 IRQs; community claim of a locked VM-timer FIQ sysreg (unverified) | Low–Med | Total |
| 4 | IOMMU | `dart,t8110` → `AppleT8110DART` | `apple-dart` `apple,t8110-dart` (ML+AS) | **Driver exists (other SoCs)**. New props: `exclave-sid`, `avoid-tlbi-in-map` | Low–Med | Devices unusable |
| 5 | Power domains | `pmgr1,t6050` → `AppleT6050PMGR` | `apple-pmgr-pwrstate` (generic `apple,pmgr-pwrstate`) | **Driver exists (other SoCs)**. PS table decoded (661 records, `ps-groups`, 6 blocks incl. die 1). **188 domains generated** into the local draft `t6050-pmgr.dtsi` (F-021). Untested | Medium | Devices stay off |
| 6 | CPU frequency | PMGR / `AppleCLPC` (closed-loop perf controller) | `apple-soc-cpufreq` (t8103/t8112 + generic) | **Driver exists (other SoCs)**. ADT DVFS tables decoded: M 15 states 1.344–4.380 GHz, P 20 states 1.308–4.608 GHz, with core and SRAM voltages (F-022). OPP tables, cluster controllers (0x2_1Xe20000) and a hypothetical EM are in the draft DT. m1n1 has no t6050 cpufreq init; register format unverified | Medium | Large: stuck at boot frequency |
| 7 | CPU idle / power states | `function-cpu_idle` per CPU | AS cpuidle (WFI/deep idle); PSCI-via-EFI RFC (`efi-psci`, m1n1 `psci-via-efi`) | **Blocked**: m1n1 forces `idle=nop arm64.nowfxt` on M4+ because WFI loses state, so idle CPUs spin (F-026) | Medium–High | Idle power or battery life |
| 8 | NVMe storage | `iop,ascwrap-v6` `ans` (`role=ANS2`) → `AppleANS3CGv2Controller`; SART `sart,coastguard` → `IOCoastGuardSARTMapper` | `nvme-apple` (ans2 only); `apple-sart` (t6000/t8103/t8015). m1n1 has **SARTv4** (seen on M5 Pro/Max) and NVMe for M4+ (`nvme_read` works on T6050). macOS-15+ ANS firmware ABI change (`b4/nvme-fwabi` series, **already in the AS `asahi` branch**). Linux gaps (SARTv4, M4+ NVMMU/NVMe register split, I/O-queue base registers) are **drafted locally** as `kernel/patches/t6050/0001–0005` (untested, F-023) | **Partial** (m1n1 works; Linux: local untested drafts) | Medium–High | No internal disk in Linux |
| 9 | Coprocessor mailbox / RTKit | all IOPs `iop,ascwrap-v6` → `AppleASCWrapV6` + `RTBuddy` | `apple-mailbox` (asc-v4, m3-v2) + `apple-rtkit` | **Unknown** (wrapper v6) | Medium | Blocks NVMe, SMC, DCP, GPU, audio |
| 10 | SMC (power, battery, sensors) | `smc` IOP → `AppleSMC*` | `macsmc` (AS; RTKit) | **Partial** (depends on #9) | Medium | No battery or thermals |
| 11 | GPU | `gpu,t6050` + `gfx-asc` + **`gfx1-asc`** → `AGXAcceleratorG17X` | AS `asahi` DRM: agx-t8103/t8112/t600x/t602x only (G13/G14) | **Missing** (G15+ unsupported) | Very high | No acceleration. Matrix units: macOS FP16 GEMM ≈ 64 TFLOP/s (BENCH) |
| 12 | Display | `disp0,t605x`, DCP `iop,ascwrap-v6`, 4× `dispextN,t605x` → `IOMobileFramebufferShim` | AS `apple` DRM (DCP) t8112/t6020 | **Missing** | High | Only a firmware framebuffer, if any |
| 13 | Neural Engine | `ane,t8132exclave` → kext `AppleH16ANEInterface` (H16 IP): `H11ANEIn` + **`ANEExclaveProxy`** | none upstream (see AR) | **Missing / possibly blocked** by exclave design | Very high or unknown | No ANE; AI falls back to GPU/CPU |
| 14 | USB / Type-C | `usb-drd,t6050;usb-drd,t8142` → `AppleT8142USBXHCI`; `atc-phy,t6050;atc-phy,t6040` → `AppleT6050TypeCPhy` | dwc3 + `apple-atcphy` (t8103, t8122) | **Missing** (new PHY) | High | No USB |
| 15 | Thunderbolt / USB4 | `apciec,t6050` ×3, `acio,v2` | AS experimental | **Missing** | Very high | No TB |
| 16 | Internal PCIe (Wi-Fi/BT, SD) | `apcie,t6050` → `AppleT6050PCIe` | `pcie-apple` (t8103/t6000/t602x) | **Unknown** | Medium | No Wi-Fi/BT/SD |
| 17 | Wi-Fi / Bluetooth | `wlan`/`bluetooth` nodes; Apple **N1** wireless chip (Asahi report) | no Linux driver for Apple N1 | **Missing** | Very high | No Wi-Fi or BT |
| 18 | Keyboard / trackpad | `mtp` IOP + `dockchannel,t8002` + `hid-transport,mux` | AS dockchannel + MTP HID (M2 laptops) | **Partial** (depends on #9) | Medium | No input |
| 19 | Audio | `iop-audio,controller`, `admac-evolution,t6050`, mic via `iisaudio,isolated-stream-proxy` | AS macaudio / admac (t8103 et al.) | **Missing** (new ADMAC, exclave mic path) | High | No sound or mic |
| 20 | I2C / GPIO / WDT / UART / SPI | `i2c,t8101`, `gpio,t8101`, `wdt,t8101`, `uart-1,samsung`, `spi-1,spimc` | i2c-pasemi, pinctrl-apple-gpio, apple_wdt, samsung_tty, spi-apple | **Driver exists (other SoCs)**: legacy-compatible IP. Draft DT nodes with power domains from ADT `clock-gates`. UART0 isn't reachable on laptops (F-025). `wdt-version = 3`: m1n1 disarms the secondary watchdog | Low | Boot console and basics |
| 21 | Memory cache controller | `mcc,t6050` | none needed for basic boot | n/a | n/a | n/a |
| 22 | Camera ISP | `isp,isp-generic-ex` + exclave proxies → `AppleH16CamIn` | AS isp (t8103/t6000 era) | **Missing** (exclave-mediated) | Very high | No webcam |
| 23 | Video decode / encode | `avd,t8103;avd,t6020`, `ave2` | none upstream | **Missing** | High | Software codecs (CPU) |
| 24 | SME (CPU matrix unit) | architectural FEAT_SME/SME2/SME2p1, SVL 512 | ML supports "SME-only" CPUs (SME without SVE) | **Supported by kernel design**, not tested on this CPU | Low | CPU AI ≈ 2.2 TFLOP/s per P cluster if exposed (BENCH) |
| 25 | MTE | FEAT_MTE/MTE2/MTE4 present | ML arm64 MTE | **Unknown** (needs firmware tag storage enablement) | Medium | Security feature, not perf |

## Detail per subsystem

The mission's 10-point record per subsystem is maintained in
`reverse-engineering/findings/catalog.md` (F-001 … F-011) and expanded here as
research lands. Key engineering approaches:

* **Boot (1–5, 20):** the minimal-DT bring-up route that Asahi used for t8132
  in 2026-07. That means CPUs, AIC3, timer, PMGR, UART, WDT, pinctrl and I2C
  first, generated from the ADT. Draft: `kernel/experiments/t6050-dt/`.
  Validation requires m1n1 support for t6050 plus native hardware, and the
  user's explicit authorization for any boot experiment.
* **Storage (8):** characterize ANS3 differences. The ADT shows
  `nvme-linear-sq` and `nvme-secure-bar` properties and a new SART type. This
  is a prerequisite for any usable native install. 2026-10-11: the Linux-side
  gaps are drafted (SARTv4; the M4+ register split from m1n1 `53f8ee9b`) in
  `kernel/patches/t6050/`, plan in `kernel/native-enablement/plan.md` §3c.
* **GPU (11):** the largest performance gap. A G17 driver needs firmware
  interface and ISA work by the Asahi GPU team. Not tractable for this
  project alone; track upstream.
* **ANE (13):** feasibility unknown because of exclave mediation.
* **CPU performance (6, 7, 24):** once booting, cpufreq + EAS + the
  `omarchy-qos` tiers (implemented in `omarchy-arm64/configuration/qos-tiers`)
  reproduce macOS's QoS placement.

## What can be validated today without native boot

* SME exposure and throughput inside a Linux VM (Hypervisor.framework).
* CPU, memory and storage overhead of a VM vs macOS (same binaries).
* Omarchy ARM64 userspace and the `omarchy-qos` mechanics in a VM.
* GPU compute via a paravirtual path (Venus/MoltenVK) as a stop-gap. This is
  reported separately from native parity.
