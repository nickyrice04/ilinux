# Asahi Linux / upstream Linux status for the Apple M5 Max (t6050), October 2026

- **Date of research:** 2026-10-11
- **Target:** MacBook Pro 16-inch (M5 Max), Mac17,6, board J716c, 128 GB, macOS 26.6.2 (25G83)
- **Method:** I read primary sources: Asahi website and docs sources on GitHub, m1n1, linux-asahi and mainline Linux source trees, Mesa source, Apple developer and newsroom pages, LKML/LWN, and Mastodon. I also ran read-only `ioreg`/`sysctl` queries on the target Mac. Nothing was installed and nothing outside this file was modified.
- **Evidence labels:** **Confirmed / Likely / Hypothesis / Unknown**. For hardware facts: **Observed** (seen on this machine), **Spec** (vendor specification), **Inferred**. Statements marked *Inference* are mine, not the sources'.
- **Privacy:** Machine-unique identifiers (ECID / unique-chip-id, MAC addresses, UUIDs, serials, nonces) were deliberately left out.
- **Quotation policy:** To stay within quotation limits, policy texts are paraphrased closely, with section names and URLs so the verbatim wording can be checked. One short direct quote is used, in section 8.

---

## 0. Executive summary

| Question | Answer (Oct 2026) | Label |
|---|---|---|
| Does Asahi support the M5 Max? | **No.** Asahi's M5 feature page marks every SoC block **TBA** and the installer as **no** for all M5 / M5 Pro / M5 Max / M5 Ultra machines. The installer's chip table stops at M3, so chip-id 0x6050 fails with an unsupported-device error. | Confirmed |
| Newest officially supported generation | **M3** (M3, M3 Pro, M3 Max laptops and iMac). Installer support was announced 2026-09-06, and Expert mode was dropped on 2026-09-15. GPU acceleration and full DCP are still missing, and sleep does not work. M3 Ultra is not supported. | Confirmed |
| SoC ID of this machine | ADT `chip-id` = **0x6050**, `platform-name` = **t6050**, board-id 0x0E (Observed). libirecovery lists Mac17,6 / j716cap as 0x6050. Asahi's codename table says M5 Max = H17C "Sotra_C" = T6050. Asahi's new device-list page and m1n1 `soc.h` both name a **T6051** for the M5 Max, which conflicts with the hardware's chip-id. Base M5 = **T8142** (H17G "Hidra"). M5 Pro = **T6050** (H17S "Sotra_S"). | Confirmed (0x6050). T6051 meaning: Unknown |
| m1n1 on M5 | **Yes, early.** m1n1 has initial T8142, T6050 and T6051 support (June/July 2026). It runs on M5 Pro hardware, and device-mode USB was fixed on an M5 Max MacBook Pro. **On M5 Pro, secondary CPUs power on but never execute m1n1 code** (June 2026, no public fix for T6050 found). | Confirmed (boots). SMP blocked: Likely |
| Linux on M5 | Asahi's Aug 2026 report says NVMe now works on M4 and M5 machines, PCIe enumerates, and a multi-core crash was fixed. Little else works yet. There is **no M5 device tree** in any official Asahi kernel branch. | Confirmed |
| GPU generation | **AGX G17.** The macOS driver class on this machine is `AGXAcceleratorG17X` (Observed). M3 = G15. The Asahi kernel driver and upstream Mesa support only **G13 (M1) and G14 (M2)**. | Confirmed |
| Main blockers | (1) **SPTM/GXF and locked IMPDEF sysregs on M4+.** This breaks the macOS-tracing hypervisor; it is now emulated (Sept 2026) but no tracing macOS target is pinned for M4+. (2) **WFI state loss** because mBoot locks the chicken bits. (3) **T6050 SMP bring-up.** (4) The new **G17 GPU** and a new **DCP firmware ABI**. (5) **Apple N1 Wi-Fi/BT** (no Linux driver exists). (6) Volunteer bandwidth: M3 only shipped in Sept 2026. | Confirmed (sourced) / Inference for ordering |
| Neural Engine on Linux | Only the out-of-tree `eiln/ane` driver exists. It covers **M1-family only** (t8103/t6000), was last pushed 2024-03, and is not in linux-asahi or mainline. On this M5 Max the ANE is described in the ADT as **`ane,t8132exclave`** with exclave services, so macOS reaches it through an Exclave proxy (Observed). | Confirmed |
| Best VM-with-GPU option today | **libkrun/krunkit** (the default Podman machine provider on macOS, also used by RamaLama, and available as a Lima 2.0 vmType). It gives Vulkan in the guest via Venus, then virglrenderer, then MoltenVK, then Metal. It measured about 50–60% of native Metal for llama.cpp on an M2 Max. For llama.cpp specifically, the new **GGML-VirtGPU API-remoting backend** forwards to host `ggml-metal`. That is claimed near-native and is the only VM path that could reach the M5 GPU Neural Accelerators, but it is experimental and untested on macOS 26. Apple `container` and Tart have no GPU acceleration. | Likely |
| Clean-room policy essentials | Hardware probing and **m1n1-hypervisor register/data tracing are the sanctioned methods.** Disassembly is not banned, but code developed alongside binary RE is accepted only from trusted contributors; everyone else must follow a strict clean-room split. Disassembling Apple's **userspace graphics stack** (Metal, shader compiler) is forbidden outright. **Leaked or non-public material is forbidden.** **Apple employees need Board approval.** A **Sept 2026 generative-AI policy broadly forbids LLM use for material contributions**, including using an LLM to interpret hypervisor traces. | Confirmed |

---

## 1. Target machine identity (local, read-only observation)

| Property | Value | Label |
|---|---|---|
| Model / target-type / board-id | Mac17,6 / J716c (`J716cAP`) / 0x0E | Observed |
| ADT `chip-id` / `platform-name` | 0x6050 / `t6050` | Observed |
| System firmware | `mBoot-18000.161.10`. m1n1's firmware table maps this exact string to macOS 26.6.2. From macOS 26.4 on, iBoot reports itself as "mBoot". | Observed + Confirmed (m1n1 `src/firmware.c`) |
| CPU topology | 18 cores. Clusters 0 and 1 have `cluster-type` "M" (6+6 cores, ADT compatible string `apple,sawtooth`). Cluster 2 has `cluster-type` "P" (6 cores, `apple,everest`). The boot CPU (cpu0) is an M core. All cores report `die-id` 0. macOS perflevel0 = "Super" ×6 and perflevel1 = "Performance" ×12. | Observed |
| CPU naming in m1n1 | m1n1 calls the new core type the **M-core**. It is not an E-core: it lacks the E-core-specific Apple sysregs. Apple's "super core" maps to the ADT/MPIDR **P** type. MIDR parts: T6050 Sotra = 0x64 (M) / 0x65 (P); T6051 "M5 Max Sotra C" = 0x68 / 0x69. | Confirmed (m1n1 PR #610, `src/midr.h`). MIDR not readable from macOS userspace: Unknown for this unit |
| `hw.cpufamily` / `hw.cpusubfamily` | 0xf76c5b1a / 5. In XNU's public `machine.h`, subfamily 5 is `CPUSUBFAMILY_ARM_HC_HD` (Max/Ultra class). The family constant is absent from the latest public XNU header I checked, which ends at the M4 DONAN/BRAVA constants. | Observed |
| SME | `FEAT_SME`, `FEAT_SME2`, `FEAT_SME2p1`, F16F16/B16B16/F64F64/I16I64 variants present; `sme_max_svl_b` = 64 (512-bit streaming vector length). No plain `FEAT_SVE`. | Observed |
| Hypervisor support | `kern.hv_support` = 1. IPA size 4 TiB with 16K pages, 1 TiB with 4K pages. | Observed |
| GPU | `gpu,t6050` in the ADT. IORegistry classes `AGXAcceleratorG17X` and `AGXFirmwareKextG17RTBuddy`. `gpu-core-count` = 40. | Observed |
| Interrupt controller | ADT compatible `aic,3` (AICv3) | Observed |
| IOMMUs | 43 DART nodes with compatible `dart,t8110` | Observed |
| NVMe | `ans` and `sart-ans` nodes. The SART compatible is `sart,coastguard`; m1n1 implements it as "SARTv4", first seen on M5 Pro/Max. | Observed + Confirmed (m1n1 PR #661) |
| USB-C / Thunderbolt | `atc-phy,t6050` + `atc-phy,t6040`; `atc-dpxbar,t6050` + `atc-dpxbar,t8142`. Four USB-PD controllers at `usbc,sn201202x,spmi`, attached over SPMI. | Observed |
| Display | `disp0,t605x` plus `dispext0..3,t605x`, five `dcp-expert-v1`, `display-crossbar,t6050` | Observed |
| Keyboard / trackpad | `mtp-transport` (DockChannel, `dockchannel,t8002`) and `mtp@…` nodes | Observed |
| Neural Engine | `ane0`: compatible `ane,t8132exclave`; `exclave-service` = `com.apple.service.ANEExclave`; `exclave-assigned` flag; `pre-loaded` = 1. IORegistry has `H11ANEIn` and `ANEExclaveProxy`. | Observed |
| Camera ISP | Has an `isp-exclave-proxy` node | Observed |
| Wi-Fi / BT | DriverKit dext `com.apple.driver.AppleCentauriAlpha`. Its match criteria name chipset **"proxima"**, vendor "Centauri". Apple's spec page says M5 Pro/Max MacBook Pros use the **Apple N1** chip (Wi-Fi 7, BT 6, Thread). | Observed + Spec |

**Chip-ID mapping (newer generations)**

| Marketing | SoC (ADT chip-id) | Codename (Asahi docs) | Notes |
|---|---|---|---|
| M3 / M3 Pro / M3 Max / M3 Ultra | T8122 / T6030 / T6031, T6034 / T6032 | Ibiza / Lobos / Palma | M3 GPU = G15 (m1n1) |
| M4 / M4 Pro / M4 Max | T8132 / T6040 / T6041 | Donan / Brava Chop / Brava | GPU G16 *Inferred* from Mesa's "M{gen−12}" naming, not directly verified |
| A18 Pro (MacBook Neo, 2026) | T8140 | Tahiti | Asahi groups it with M4 |
| **M5** | **T8142** | Hidra (H17G) | MacBook Pro 14" (Oct 2025), MacBook Air (2026) |
| **M5 Pro** | **T6050** | Sotra_S (H17S) | |
| **M5 Max** | **T6050** (chip-id 0x6050: Observed and libirecovery) | Sotra_C (H17C) | Asahi device list and m1n1 also name "T6051". Possibly an internal die-variant label tied to different MIDR parts, not the ADT chip-id (*Inference*). |
| M5 Ultra | libirecovery: 0x6050. Asahi device list: T6052. | Sotra_D (unnamed in the table) | Conflicting |
| M6 (Mac mini 2026, per Asahi) | T8152 | Komodo (m1n1) | m1n1 basic support added 2026-09-27 |

M5 Pro/Max use Apple's "Fusion Architecture": two third-generation 3 nm dies joined into one SoC. The CPU is 6 super cores plus 12 new performance cores, the GPU has up to 40 cores with a Neural Accelerator in each, and the Neural Engine has 16 cores. The M5 Max supports up to 128 GB at 614 GB/s (Spec, Apple newsroom, 2026-03-03).

---

## 2. Asahi official support status (Q1)

### 2.1 Feature-support pages (asahilinux.org/docs/platform/feature-support/)
The single overview page has been split into per-generation pages: M1, M2, M3, M4 (including A18 Pro), M5, and M6.

- **M5 page** (added 2026-10-03, corrected 2026-10-04). Columns: "M5 (T8142)" and "M5 Pro/Max/Ultra (T6050)". **Every SoC block is TBA**: DCP, USB2/3, Thunderbolt, DP alt mode, GPU, video decode, NVMe, PCIe, cpufreq, cpuidle, suspend, video encode, ProRes, AICv3, DART, PMU, UART, watchdog, I2C, GPIO, USB-PD, MCA, SPI, SPI NOR, SMC, SPMI, RTC, SEP, Neural Engine. Every device, including the "MacBook Pro (14" and 16", 2026)", shows installer **no**, devicetree **TBA**, and all peripherals **TBA**. Under the page's legend, TBA means no active work is happening. **Confirmed.**
- **M4 page.** AICv3, watchdog, I2C and GPIO are "linux-asahi (7.4)" on A18 Pro and M4. Video decoder and NVMe are WIP on M4 and M4 Pro/Max. M4 device trees are "linux-asahi (7.4)", and M4 Pro/Max device trees are WIP. Installer **no** everywhere. **Confirmed.**
- **M3 page.** Installer **yes** for the iMac, MacBook Pro and MacBook Air. Most blocks are linux-asahi, with M3 device trees upstream in 7.2. DCP is WIP: only the boot framebuffer works. **GPU is WIP on M3 (T8122) and TBA on M3 Pro/Max/Ultra.** Neural Engine and SEP are TBA. **Confirmed.**
- **Discrepancy.** The Aug 2026 progress report says NVMe works on M4 and M5, but the M5 table (Oct 2026) still says NVMe TBA. The blog text is newer and more specific; the table seems not to track developer-branch status.

### 2.2 Installer
`asahi-installer/src/main.py` has a `CHIP_MIN_VER` table that covers only M1, M2 and M3 (0x8103 through 0x6034, with M3 needing at least macOS 14.8.3). Any other chip-id gets an unsupported-device error, so **chip-id 0x6050 is rejected**. **Confirmed.**

### 2.3 m1n1 on M4/M5
| Date | Change | Source |
|---|---|---|
| 2025-04 | Initial M4 "Donan" chicken-bit support | m1n1 commit log |
| 2026-01 to 06 | T8132 / T8140 / T6040 / T6041 initial support | m1n1 commits |
| 2026-03-31 | macOS 26.4 / "mBoot" firmware version support, tested on an M5 Pro MacBook Pro | PR #559 |
| 2026-05 | PMGR support for M4 Pro/Max, A18 Pro and M5; fixed m1n1 device-mode USB on an M5 Max MacBook Pro | PR #578 |
| 2026-06-29 | **T6050/T6051 initial support.** Adds the M-core type. M5 Pro boots on an M-core. Secondary cores turn on in PMGR but never run m1n1 code. | PR #610 |
| 2026-07 | T8142 (base M5) initial support, with MIDR and SMP offsets confirmed by a tester | PR #629 |
| 2026-07/08 | SPMI gen 4 (tested on T6050). SARTv4 (seen on M5 Pro/Max). NVMe for M4+, making `nvme_init`/`nvme_read` work on T6050. | PRs #626, #661, #652 |
| 2026-08/09 | WFI/WFIT disabled when WFI loses state. CTRR_M4 reserved region. SPRR/GXF emulation and SPTM IMPDEF-sysreg emulation in the hypervisor. SME instructions no longer trapped to EL2. | commits; PR #643 |

**Bottom line:** m1n1 boots on M5-family machines (**Confirmed**: M5 Pro and base M5 tested, M5 Max USB device mode fixed). SMP on T6050 was not working as of June 2026, and I found no public fix (**Likely still blocked**). A community M5 Pro effort reported on 2026-10-10 that it is still limited to one core (unverified).

### 2.4 Device trees
- No `t8142*`, `t6050*` or `t6051*` DTS exists in the AsahiLinux/linux branches `asahi`, `asahi-wip`, `asahi-wip-7.2` or `apple-soc/dt-7.4`. The `apple-soc/dt-7.4` branch has M4 (t8132) and A18 Pro (t8140) DTS only. Mainline at v7.3-rc6 has M3 (t8122, t603x) DTS but no M4/M5 DTS. **Confirmed.**
- Unofficial: `betizzel/omarchy-m5` has ADT-derived T6050 DTS (j714s, j716s), and `Sunrise-OS/linux` has a t8142-j813 DTS. Neither is reviewed, and see section 11 on policy compatibility.

### 2.5 Timeline of Asahi statements on newer chips (2025–2026)
- **2025-02-13** ("Passing the torch"): until upstreaming and CI progress, the core team cannot prioritise new hardware. Community members are reverse-engineering in preparation.
- **2025-04-04** (Sven Peter, Mastodon): M4 support will be painful because of SPTM (details in section 4).
- **2025-10-24** (6.17 report): m1n1 can bring up M3 to the point of booting a kernel to a blinking cursor.
- **2026-02-15** (6.19 report): three new contributors got M3 to KDE Plasma with software rendering. The M3 GPU is a significant departure. The M3 DCP firmware interface changed in macOS 14.
- **2026-04-26** (7.0 report): M3 reaches roughly first-M1-alpha parity in the Asahi tree.
- **2026-06-30** (7.1 report): M3 audio, cpufreq and sensors work. m1n1 groundwork for M4/A18 Pro covers the non-macOS boot mode and new power-domain metadata.
- **2026-08-26** (7.2 report): M4 WFI issue. SPTM emulation in the hypervisor. M4/M5 NVMe works after a macOS-15 NVMe firmware ABI change. PCIe enumerates. SMP crash fixed. Not ready for the installer.
- **2026-09-06**: official M3 support.
- The project policy throughout is **no ETAs** ("When will Asahi be done" page).

---

## 3. Per-subsystem status (Q2)

Columns: **M3** is the newest supported generation; **M4** and **M5 Pro/Max (T6050)** are the targets of interest.

| Subsystem | M3 | M4 | M5 Pro/Max (T6050) | Evidence / notes |
|---|---|---|---|---|
| **Interrupt controller** | AICv3, linux-asahi. Upstream compatible `apple,t8122-aic3` is in mainline 7.3-rc6. | AICv3 linux-asahi (7.4) on M4; WIP on M4 Pro/Max | TBA. ADT says `aic,3` (Observed). | A community T6050 patch claims the AIC's VM-timer FIQ-enable sysreg is locked on T6050, so guest timer FIQs cannot be masked (unverified). |
| **SMP** | works | Made reliable on M4/M4 Pro by combining WFI/WFIT disable with the CTRR_M4 reservation (m1n1 commit a735ea29) | **Not working on M5 Pro** as of 2026-06 (PR #610). No public fix found for T6050. | RVBAR is locked on M4+ and cannot be pointed at m1n1's entry (m1n1 commits 7339546899, 48d388bc51). *Inference:* this likely relates to the T6050 secondary-start failure. |
| **cpufreq** | linux-asahi. Unchanged since M2, needed DTs only (7.1 report). | TBA | TBA | |
| **cpuidle** | linux-asahi (downstream-only driver) | **WFI loses state on M4**: mBoot sets and locks the chicken bits from M4 onward | TBA | Mainline 7.3-rc1 has arm64 `idle=<wfi\|yield\|nop>` (Yureka Lilian). Sven Peter's RFC "PSCI-via-EFI" (July 2026) adds an EFI runtime-service PSCI conduit, because Apple cores have no EL3. |
| **PMGR power domains** | linux-asahi | m1n1 support (PR #578) | m1n1 support (PR #578). Linux TBA. | The 7.1 report mentions new power-domain metadata in the ADT on M4/A18 Pro. |
| **DART IOMMU** | linux-asahi | TBA | TBA. ADT has 43 `dart,t8110` nodes (Observed). | Mainline `apple-dart` already matches `apple,t8110-dart`. *Hypothesis:* the M5 DARTs may be largely compatible. Unverified. |
| **NVMe (ANS2 + NVMMU + SART + RTKit)** | linux-asahi | WIP | Works in developer trees (7.2 report). The table says TBA. | The NVMe firmware ABI changed with the macOS 15 firmware bundle, which M4 requires. Sven Peter's series "Apple NVMe fixes for macOS 15+ firmware / M4 support" is on branch `b4/nvme-fwabi` (Aug 2026). T6050 needs SARTv4; the linux-asahi `sart.c` on the `asahi` branch has no SARTv4 compatible (Observed). |
| **PCIe** | linux-asahi | enumerates (7.2 report) | enumerates (7.2 report covers M4 and M5) | |
| **USB / Thunderbolt (ATC PHY)** | USB3 works. TB and DP alt mode WIP. M3 needs new N3 tunables, and M3 Pro/Max use **ACE3 over SPMI**. | TBA | TBA. ADT has `atc-phy,t6050`/`t6040` and USB-PD over SPMI (Observed). | ATC PHY driver upstream in 7.0, SPMI controller in 6.16, dwc3-apple in 6.19. m1n1 has SPMI gen 4 and tps6598x-over-SPMI for M5. |
| **Display (DCP)** | Boot framebuffer only. Full DCP is WIP and targets the **macOS 14.8.3 ABI**. | Boot framebuffer only (linux-asahi) | TBA | No hypervisor/firmware target is pinned for M4+ ("m1n1 hypervisor" doc). *Inference:* M5 Pro/Max cannot run pre-macOS-26 firmware, so a new DCP ABI (26.x or 27) will have to be traced. |
| **GPU** | WIP on M3 (T8122) only. Ships software-rendered; Asahi says not to expect performant or efficient 3D yet. | TBA | TBA. **G17** (Observed `AGXAcceleratorG17X`). | Asahi kernel driver `hw/mod.rs` has `GpuGen::{G13,G14}` only. Upstream Mesa's `agx_device.c` has chip classes G13G/G13X/G14G/G14X only. See 3.1. |
| **Video decode (AVD)** | linux-asahi (custom firmware + V4L2 stateless, including AV1 on M3) | WIP | TBA. ADT: `avd,t8103`, `avd,t6020` (Observed). | |
| **Audio** | linux-asahi. I2S, NCO and amps unchanged since M1 (7.1 report). | TBA | TBA | |
| **Keyboard / trackpad** | linux-asahi | TBA (open community PR #567 for M4 MBP keyboard) | TBA. ADT: MTP over DockChannel (Observed). | A community M5 Pro effort reports keyboard and trackpad working with patches (unverified). |
| **Wi-Fi / Bluetooth** | linux-asahi (Broadcom) | TBA | TBA. This machine uses Apple's **N1** chip, chipset "proxima", via an Apple DriverKit driver (Observed / Spec). | *Inference:* N1 is not Broadcom, so brcmfmac/hci_bcm4377 do not apply and a new driver plus firmware RE is needed. The base M5 MacBook Pro is Wi-Fi 6E / BT 5.3 with no N1 (Spec). |
| **SMC** | linux-asahi. Core driver upstream in 6.17; hwmon and RTC in 6.19; power supply in 7.1. | TBA | TBA | macOS 26/27 SMC firmware ABI changes were handled for M1–M3 (6.18 and 7.1 reports). |
| **Suspend / power management** | Sleep **does not work** on M3 (firmware framebuffer) | TBA | TBA | PMP drivers (M1 Pro+) save about 0.5 W idle but are not on by default (7.0 report). |
| **SEP** | TBA | TBA | TBA. ADT: `iop,exclave-sep-manager` (Observed). | |
| **Neural Engine** | TBA | TBA | TBA | See section 5. |

### 3.1 GPU generations and the M3 architectural break
- **Generation map** (Confirmed unless marked): G13 = M1 and G14 = M2 (Asahi driver, Mesa). G15 = M3 (m1n1 added "AGX G15 and G15X" for M3 tracing, 2026-09-16). G17 = M5 (Observed on this machine). G16 = M4 is *Inferred* from Mesa's naming formula, which prints `Apple M{gen−12}` with variant letters G/S/C/D for base/Pro/Max/Ultra. By that convention this M5 Max GPU would be "G17C" (*Inferred*); macOS's driver family name is "G17X".
- **What changed in M3** (Apple "family 9"; Apple newsroom 2023-10-30 and tech talk 111375):
  - **Dynamic Caching** allocates on-chip memory in hardware at run time instead of reserving it per shader. Registers, threadgroup memory, tile memory and the buffer cache come from a unified on-chip cache, sized by the shader's actual live usage, so occupancy rises.
  - A new shader core.
  - Hardware ray tracing and mesh shading.
- **Asahi's account** (6.19 report): the M3 GPU is a significant departure from M1/M2, with ray tracing, mesh shaders, Dynamic Caching and many ISA changes. Volunteers (Alyssa Milburn, Michael Reeves) are reverse-engineering it, building on dougallj and TellowKrinkle's ISA work. An XDC 2026 talk (2026-09-29; Anna Maniscalco of Valve, Alyssa Milburn, Evan Tang of CodeWeavers) covers M3 GPU RE progress, the hardware differences, and the porting status of the userspace and kernel drivers. Its abstract gives no technical details. The GPU firmware ABI also changes with each macOS release, and M3 targets the macOS 14.8.3 ABI (7.2 report).
- *Inference (Hypothesis):* the blockers are three-fold. (a) The compiler's register-allocation and occupancy model and the ISA encodings changed, so Mesa's AGX compiler backend needs a new target. (b) The kernel driver's firmware structures need a new GPU generation and a new macOS-version ABI. (c) The new fixed-function blocks (ray tracing, mesh) need new command-stream and state formats. None of this has an upstream Mesa merge request yet. I found no G15 MR in the Mesa GitLab search.
- **M5 GPU** (Apple "family 10", tech talk 111431): second-generation dynamic caching, a redesigned occupancy management unit, twice the FP16 and complex-ALU rate, third-generation ray tracing, and per-core Neural Accelerators. No Linux driver work for M5 GPUs exists in Asahi.
- **Third-party** (unverified; LLM-written, see section 11): Cody Ho's "I Came, I Prompted, I Left" posts (Sept 2026) report a Rust kernel driver plus Mesa fork for the **M4 Mac mini** with OpenGL ES 3.0 conformance claimed. They say M5 is only partly done (firmware ABI and a drm-shim prototype), and that M5's userspace ISA is mostly a superset of M4's but with different texture descriptors.

---

## 4. Boot-chain obstacles on M4/M5 versus M1/M2 (Q3)

| Obstacle | What sources say | Label |
|---|---|---|
| **SPTM (Secure Page Table Monitor) in GL2** | Sven Peter (Mastodon, 2025-04-04): booting a **Mach-O** boot object on M4 drops you into an environment where SPTM runs in GL2. The OS must then talk to SPTM from EL2 with the MMU already on to set up page tables. That works neither for Linux nor for running XNU under Asahi's hypervisor. | Confirmed |
| **"Raw" boot object mode** | Same post: a **raw** boot object lands in EL2 with GL2 and most (possibly all) Apple-specific extensions disabled. This is fine for Linux but prevents the XNU-tracing hypervisor. It also appeared broken on macOS 15.2 or later at the time. The 7.1 report says m1n1 gained better handling of this non-macOS boot mode. | Confirmed |
| **SPTM mandatory for XNU on M4+; the RE hypervisor was dead** | 7.2 report: SPTM is required for XNU on M4 and later, so the m1n1 hypervisor stopped working there. Sven Peter taught it to **emulate SPRR and GXF**, load Apple's SPTM blob, and patch XNU. Tracing now works again, more slowly. m1n1 also shadows the IMPDEF sysregs SPTM uses on M4+, plus `nXS` TLBI and CTRR/CTXR (commits 39d759de0f, 442c7a28de, 57a9339ffd; PR #643 merged 2026-09-27). | Confirmed |
| **TXM / Exclaves** | Open m1n1 PR #698 (2026-10-07) adds **SPTM and TXM** support to the hypervisor. It was tested on M2 with macOS 26.3, 26.5 and 27 beta 4. It states that Secure Kernel and **Exclaves do not work**, that it needs hardware SPRR/GXF access (M4+ relies on #643's emulation), and that it needs nested virtualization (M2+). On this M5 Max, the ANE, ISP and SEP have exclave-proxy nodes (Observed). | Confirmed / Observed |
| **No pinned tracing target for M4+** | The m1n1-hypervisor doc supports macOS 13.5 for M1/M2 and 14.8.3 for M1–M3. Because of bugs and the SPTM requirement, no target is pinned yet for M4 and newer. | Confirmed |
| **Locked IMPDEF sysregs** | On M4+ (`apple_sysregs_unlocked` false), m1n1 cannot write RVBAR, cannot clear L2C_ERR bits, and does not touch SPRR/GXF/AMX registers. Writing them causes SErrors or exception loops (m1n1 commits by Yureka, 2026-05/06). | Confirmed |
| **Chicken bits locked by mBoot, so WFI loses state** | 7.2 report: from M4 on, Apple sets per-core chicken bits in mBoot and locks them. WFI then loses core state and crashes. Fixes: an m1n1 bootarg (commits 3a69c73f59, 9095a5ee70), mainline arm64 `idle=` (7.3-rc1), and the cpuidle driver saving state. | Confirmed |
| **No EL3, so no PSCI** | The arm64 maintainers require PSCI upstream, but Apple cores have no EL3. Sven Peter's RFC (2026-07-08, six patches) adds a PSCI-via-EFI-runtime conduit with m1n1 staying resident. | Confirmed |
| **CTRR region on secondaries** | A 48 KiB CTRR region enabled on secondary cores (M4, M4 Pro, A18 Pro) must be reserved in the DT (commit a735ea29ae). | Confirmed (M4). M5: Unknown |
| **Secondary watchdog** | M4 and A18 Pro reset after about 120 s with iBoot from macOS 26.x, caused by secondary watchdogs. m1n1 disarms them (commit 0e88df7bc9). | Confirmed |
| **NVMe firmware ABI** | The macOS-15+ ANS firmware removes a control register (accessing it causes an SError) and needs page-aligned admin buffers. M4 requires that firmware (`b4/nvme-fwabi` series). | Confirmed |
| **iBoot renamed mBoot** | From macOS 26.4, firmware reports `mBoot-18000.x` (m1n1 firmware table; observed here). | Confirmed |
| **macOS 27 boot-picker change** | macOS 27 now honours an APFS "bootable" flag, so Asahi stub volumes vanished from the boot picker until the installer set it (7.1 report). There is a fix mode in the installer. | Confirmed |
| **Boot policy / stub macOS** | Custom kernels still need **Permissive Security**, set in recoveryOS, which lets the boot chain accept locally SEP-signed boot objects (Apple Platform Security guide). Asahi still installs a **~2.5 GB stub APFS macOS container** with m1n1 as its "kernel" so Apple's boot picker and Startup Disk work (7.1 report). I found no source saying M5 removed Permissive Security. m1n1 does run on M5 Pro/Max (section 2.3). | Confirmed |
| **Community claim to treat with care** | `antiapplefox/m5-linux` (static analysis of IPSW SPTM/iBoot binaries; no hardware runs) claims Linux must masquerade as XNU. That conflicts with Asahi's evidence that raw-mode Linux boots on M4/M5 (NVMe and PCIe working). | Hypothesis (community); contradicted |

---

## 5. Neural Engine on Linux (Q4)
- **`eiln/ane`** (Eileen Yoon) is a reverse-engineered DRM-accel-style kernel module plus libane and Python bindings. Its match table lists only `apple,t8103-ane` and `apple,t6000-ane` (M1 and M1 Pro/Max/Ultra, T8020-layout DART). It was last pushed **2024-03-12**, and its README still says the module should move into tree soon. **Confirmed.**
- **Asahi tables**: M1 and M2 Neural Engine "out of tree", pointing to eiln/ane (the M2 entry is not backed by an M2 compatible in that repo's `main`, per my observation). M3, M4 and M5: **TBA**. **Confirmed.**
- **Not in linux-asahi**: there is no ANE driver under `drivers/accel` on the `asahi` branch. **Not upstream**: mainline 7.3-rc6 `drivers/accel` has no Apple driver. **Confirmed.**
- A community PR (#584, 2026-08) proposing ANE devicetree bindings for T8103/T600x/T8112/T602x was closed after a reviewer asked what it was for without a driver. **Confirmed.**
- **M5 Max specifics** (Observed): the ADT compatible is `ane,t8132exclave`, there are exclave services `com.apple.service.ANEExclave` and `ANEExclave_EDK`, an `exclave-assigned` flag, `pre-loaded` = 1, and an `ANEExclaveProxy` in the IORegistry. *Inference (Hypothesis):* on M4/M5, macOS drives at least part of the ANE through an Exclave. Whether a raw-boot Linux could drive the ANE directly (MMIO ownership, firmware loading) is **Unknown**, and is a new research question compared with M1.
- The M5's **GPU Neural Accelerators** are a different block from the ANE (section 10).

---

## 6. Mainline upstream status, 2025–2026 (Q5)
First mainline release containing each item. I verified ancestry by comparing release tags against each file's first commit in `torvalds/linux`.

| Component | Mainline since | Notes |
|---|---|---|
| AIC irqchip (`irq-apple-aic`) | 5.13 | AICv3 (`apple,t8122-aic3`) present at 7.3-rc6 |
| DART IOMMU (`apple-dart`) | 5.15 | Matches t8103, t8103-usb4, t8110, t6000. Four-level page tables for T602x landed for 6.18. |
| NVMe (`nvme-apple`), RTKit, SART | 5.19 | Compatibles only for ANS2 t8015/t8103. M4+ firmware-ABI fixes not yet merged. |
| cpufreq (`apple-soc-cpufreq`) | 6.2 | |
| BCM4377 Bluetooth | 6.2 | |
| Apple SPI | 6.13 | |
| ADP (Touch Bar display) | 6.15 | Maintainer: Sasha Finkelstein |
| `asahi_drm.h` GPU **UAPI only** | 6.16 | DRM maintainers allowed the UAPI to land without the driver |
| SPMI controller | 6.16 | |
| SMC core (`macsmc`) plus GPIO and reboot | 6.17 | |
| dwc3-apple, SMC hwmon, SMC RTC | 6.19 | |
| ATC Type-C PHY | 7.0 | |
| SMC power supply | 7.1 | |
| arm64 `idle=` parameter (for M4 WFI) | 7.3-rc1 | |
| **Not upstream** | — | **AGX GPU kernel driver** (Rust, about 21k lines; IGT test patches posted Jan 2026), **DCP**, ISP/webcam (submitted 2025), AOP/mics, AVD, cpuidle driver, PSCI-via-EFI (RFC), **ANE** |
| Mesa `asahi` (GL) and `honeykrisp` (Vulkan) | upstream Mesa (2025) | Conformant GL 4.6 and Vulkan 1.4 on M1/M2. DRM native context in virglrenderer, enabled in Mesa 25.2. G13/G14 only. |

Downstream patch count fell from 1232 patches (about 95k lines, 6.13.8) to 858 (about 83k lines, 6.18.8) (6.19 report). M1–M3 device trees are mainline; M4 device trees are queued for 7.4 (`apple-soc/dt-7.4`).

---

## 7. Project organisation (Q6)
- **2025-02:** Founder **Hector Martin (marcan)** stepped down as a kernel maintainer in early February, then resigned as project lead on 2025-02-13. His reasons included burnout and the upstream disputes over Rust in the kernel (Asahi post; Phoronix; The Register). The project moved to a **seven-member board**: Alyssa Rosenzweig, chaos_princess (Sasha Finkelstein), Davide Cavalca, Neal Gompa, James Calligeros, Janne Grunau, Sven Peter. Funding moved to Open Collective, later also GitHub Sponsors. **Confirmed.**
- **2025-03:** **Asahi Lina** paused Apple GPU driver work indefinitely, citing personal reasons (The Register, Phoronix; secondary sources). **Likely.**
- **2025-08-26:** **Alyssa Rosenzweig** stepped away from the Apple ecosystem after the M1/M2 Mesa drivers were fully upstream (her blog), and joined Intel (Phoronix). The governance and board pages **still list her as a board member and treasurer**. The last published minutes (2025-09-05) show her present. **Confirmed.**
- **Upstream maintainers** (mainline MAINTAINERS, 7.3-rc6): ARM/APPLE MACHINE SUPPORT is maintained by **Sven Peter** and **Janne Grunau**, with **Neal Gompa** as reviewer. The pre-DCP display DRM driver is maintained by Sasha Finkelstein, with Janne Grunau as reviewer. **Confirmed.**
- **Active 2026 contributors** named in progress reports: James Calligeros (author of every 2025–26 report; DCP, audio), Janne Grunau, Sven Peter (SPTM/SPRR emulation, PSCI-via-EFI, NVMe), chaos_princess (AOP, SEP, audio, PMP), Neal Gompa and Davide Cavalca (Fedora). New contributors: **Yureka** (M3, M4 and **M5 bring-up**), Michael Reeves, Alyssa Milburn, Shiz, Oliver Bestmann, sofus (AVD), mildsunrise, dd-dreams. **Confirmed.**
- **Licensing change:** m1n1 was relicensed to **GPLv2** for new code from v2.0.0 (2026-09-30). Previously MIT-licensed code stays MIT (commit 2460b604c6). **Confirmed.**
- **Stance on M3+:**
  - No ETAs, and the project asks people not to request them.
  - New hardware took second place to upstreaming and CI in 2025.
  - M3 shipped in September 2026.
  - M4 and M5 bring-up is driven largely by new volunteer contributors.
  - The "About" page says all Apple Silicon Macs, including future generations, are in scope as development time permits.

  **Confirmed.**

---

## 8. Copyright, reverse-engineering and generative-AI policy (Q7)
Sources: https://asahilinux.org/copyright/ (last changed 2026-07-14) and https://asahilinux.org/llm-policy/ (alias `/slop`, created 2026-09-08). The section titles below are the page's own; the content is paraphrased.

**Allowed**
- *Hardware exploration.* Probing hardware directly (dumping registers, toggling bits, observing behaviour) is described as particularly safe.
- *Register and data tracing.* Running macOS and recording register state, or intercepting traffic between components, is allowed. This is what the m1n1 hypervisor does. Register values and command buffers are treated as generally not copyrightable. Exceptions: large compiler-inserted shader code sequences, and firmware blobs, which may never be copied.
- *Referencing other open source.* APSL code (for example XNU) may be read for understanding, and last-level register names may be reused with Linux-style prefixes. Copying `#define` blocks, headers, code, or identical algorithms or code flows is not allowed. Internal exploration-only tools may use APSL code but cannot become project releases.

**Restricted**
- *Binary disassembly and decompilation* is not banned. However, code developed **concurrently** with binary RE is accepted **only from specific trusted contributors** (contact the Board). Everyone else must follow a textbook clean room: whoever disassembles a component may only write clean documentation for that area, and other people implement it. Binary-RE discussion is allowed only in `#asahi-re` (GPU RE in `#asahi-gpu`), and decompiled code must not be pasted into channels.
- **Graphics userspace:** contributors must not disassemble or decompile Apple's userspace graphics driver binaries, including Metal and the LLVM-based shader compiler, even to write documentation.
- **GPU contributors** must be known to the Board by their real name. Public contributions may still be pseudonymous.
- Open-source code that touches undocumented Apple formats or hardware is treated as if incompatibly licensed. It must not be merged into project code without a case-by-case audit.

**Forbidden**
- *Usage of unreleased materials.* Leaked software (source or binary), unreleased documentation, and non-public or restricted betas, from Apple or anyone else, may not be used.
- Current or former **Apple employees** may not contribute without prior Board approval, and failing to disclose such employment means a permanent ban.

**Generative-AI (LLM) policy (2026-09-08)**
- The policy says LLMs are likely to violate clean-room requirements, and that agentic use makes this worse because the human may not see how the knowledge was obtained. On that basis Asahi says: **"we broadly forbid the use of generative AI tooling for material contributions"**.
- Enforcement examples it gives:
  - An LLM-drafted GitHub issue gets closed. This happened to m1n1 issue #706 on 2026-10-11.
  - **Using an LLM to interpret an m1n1 hypervisor trace earns a first and final warning.**
  - Concealing extensive LLM use earns an immediate ban, especially if unreleased Apple material may have been accessed.
- m1n1 PR templates now require contributors to tick boxes certifying compliance with the copyright policy and **no generative-AI use**, with a DCO sign-off on every commit.

**Other contribution rules:** DCO 1.1 sign-off is required. There is no CLA. Pseudonyms are allowed if established, but collective pseudonyms are not. Asahi-specific modules should be dual-licensed with a permissive licence such as MIT.

**Implications for this project** (*Inference*):
- Any finding produced or interpreted with LLM tooling, including agentic RE workflows, cannot be contributed upstream to Asahi as code or documentation. That would include outputs of an LLM-driven RE tool, if REA works that way.
- If upstream compatibility matters, keep a strict separation: humans do the hypervisor tracing and hardware probing and write the documentation; humans implement.
- Never use leaked material or non-public betas.
- Never disassemble Metal or the shader compiler.

---

## 9. Linux in a VM on Apple Silicon with GPU acceleration (Q8)

| Option | GPU path for a Linux guest | Status in 2026 | Label |
|---|---|---|---|
| **Podman machine, libkrun provider (default on macOS) / krunkit** | virtio-gpu **Venus** in the guest, then virglrenderer (built with `-Dvenus=true`), then **MoltenVK**, then Metal (Homebrew `slp/krun` formula). Vulkan only. | krunkit 1.3.2 (2026-07). RamaLama needs the libkrun provider for GPU on macOS. Podman docs list libkrun as the macOS default. | Confirmed |
| **Lima ≥ 2.0, `vmType: krunkit`** | Same path (Venus) | Lima docs mark it experimental. Example runs llama.cpp with Vulkan in Fedora. | Confirmed |
| **llama.cpp GGML-VirtGPU (API remoting)** | The guest ggml backend forwards graph execution over virtio-gpu and virglrenderer's "APIR" capset to a host library that runs **ggml-metal** | Upstream in llama.cpp (Kevin Pouget, Feb 2026). Its doc lists macOS 14/15 as supported and **macOS 26 as not tested**. Needs patched virglrenderer and podman/libkrun. FOSDEM 2026 talk claims near-native speed but publishes **no numbers**. | Confirmed (exists). Performance: Unknown |
| **UTM 5.0.x (pre-release)** | QEMU + virtio-gpu **Venus** + MoltenVK (KosmicKrisp is WIP and needs macOS 26). Vulkan 1.3 in Linux guests. | Pre-release notes say Linux desktop rendering in Vulkan mode is broken (geometry-shader indirect draws); use VirGL for the desktop. Venus first appears in the 5.0 pre-release notes; the latest stable release is 4.7.5. | Confirmed |
| **Apple `container` (Containerization, VZ)** | none | A maintainer said in June 2025 that GPU is not supported. Request #1511 (2026) is open. Release 1.5.0 is from 2026-09. | Confirmed |
| **Tart (VZ)** | none documented | VZ's `VZVirtioGraphicsDeviceConfiguration` only documents scanouts; there is no documented 3D or compute. | Likely |

**Measured llama.cpp, Vulkan-in-VM versus native Metal** (llama.cpp discussion #12985):
- M2 Max, Podman + libkrun/Venus, Llama-2 7B Q4_0: pp512 **428.5 t/s vs 746.1 native (≈57%)**, tg128 **35.9 vs 71.4 (≈50%)**. Flash-attention hurt Vulkan token generation badly (14.1 t/s).
- M1 Air, Gemma-3 1B: ≈61% (pp512) and ≈41% (tg128) of native.

I found no published M3, M4 or M5 VM numbers, and no API-remoting numbers. **Confirmed** for the numbers listed.

**Nested virtualization:** supported on **M3 and later with macOS 15+**.
- Virtualization.framework: `VZGenericPlatformConfiguration.isNestedVirtualizationSupported`, macOS 15.0+, documented as M3-and-later.
- Hypervisor.framework: `hv_vm_config_get_el2_supported` / `set_el2_enabled`, macOS 15.0+.
- krunkit `--nested` (M3+, macOS 15+).
- QEMU HVF nested virt merged in May 2026.

**Confirmed.**

**SME/SME2 for guests:**
- Hypervisor.framework has had SME state APIs since **macOS 15.2**: `hv_vcpu_get_sme_state` / `hv_vcpu_set_sme_state`, plus Z/P register types. **Confirmed.**
- QEMU commit 55cd59813f (2026-03) exposes FEAT_SME2 to HVF guests, starting with M4 cores and the macOS 15.2 SDK. **Confirmed.**
- **Apple does not support nested virtualization and SME at the same time**: QEMU disables SME when nested virt is on (commit ca34bcb014). **Confirmed.**
- Whether **Virtualization.framework** exposes SME to Linux guests is **Unknown**; I found no documentation. Verify locally by booting a VZ Linux guest and checking `/proc/cpuinfo` for `sme`/`sme2`.

**Recommendation** (*Inference*):
- For general GPU work in a Linux VM on this M5 Max, use **krunkit / podman-machine (libkrun)** with Venus. Expect roughly half of native Metal throughput for llama.cpp, based on M2 data.
- For LLM inference specifically, **GGML-VirtGPU API remoting** is the most promising path. It is the only VM path that can use the M5 **GPU Neural Accelerators**, because host `ggml-metal` turns on its Metal-4 tensor-API path (`has_tensor`) on supporting GPUs and lists the M5 family. It is experimental and untested on macOS 26.
- Benchmark both with `llama-bench` (pp512/tg128) against native Metal before relying on either.

---

## 10. M5 GPU "Neural Accelerators" (Q9)

**What Apple documents** (Spec):
- **Placement:** one per GPU core. That is 10 on M5, up to 20 on M5 Pro, and up to 40 on M5 Max; this unit has 40 (Observed).
- **What they do:** Apple describes dedicated matrix-multiply hardware inside each shader core, intended for dense compute-bound work such as LLM prefill.
- **Claims:**
  - more than 4× peak GPU AI compute versus M4;
  - 4–8× matmul rate depending on precision;
  - up to 4× LLM time-to-first-token;
  - about 19–27% faster decode, mostly from bandwidth (153 GB/s versus 120 GB/s).

  Sources: Apple newsroom 2025-10-15 and 2026-03-03; tech talks 111431/111432; Apple ML Research post of 2025-11-19.
- **Programming model:**
  - Metal 4 **Tensor APIs** (`MTLTensor`, `tensor_inline`).
  - **Metal Performance Primitives "TensorOps"**: matmul2d and convolution primitives, cooperative tensors, and `execution_simdgroups<N>`.
  - TensorOps is portable back to M1 and falls back to shader code.
  - Data types: fp16 and fp32; **bf16 from 26.1**; **int8 and int4 added during the 26.x cycle** (26.4 per tech talk 111432); **fp8 and MX block-scaled formats coming in macOS 27** (WWDC26 session 330).
- **Framework support:** MLX uses TensorOps/MPP on macOS 26.2+. Core ML, MPS and MPSGraph benefit automatically. Apple says llama.cpp and PyTorch already use them, and llama.cpp's ggml-metal source has a Metal-4 tensor path.

**Linux / Mesa knowledge:** **Unknown / none found.**
- No Mesa merge requests, no Asahi statements, and nothing in dougallj's `applegpu` ISA repository covers G15 or newer.
- The third-party LLM-written M4/M5 GPU effort does not describe the accelerators.
- Third-party macOS-side research: "Rigel" (arXiv 2606.12765) characterises the Metal tensor path on an **M4 Max**, which has no accelerators, and reports that fp8 matmul is emulated there. "BaseRT" (arXiv 2607.19438) is a third-party Metal runtime that uses the M5 accelerators. I saw both only through search results and did not verify them.

*Inference:* native Linux use of the Neural Accelerators would need, at minimum, a working G17 kernel driver and compiler, followed by ISA reverse engineering of the tensor instructions. Under Asahi policy that RE must be done by black-box tracing, without disassembling Metal or the compiler. It is years behind M1/M2 parity on the current trajectory.

---

## 11. Unofficial and third-party efforts (treat as unverified)
| Project | Claim | Caveat |
|---|---|---|
| `betizzel/omarchy-m5` (created 2026-09-21) | M5 Pro (T6050, J714s): m1n1 → Linux on a single core, with NVMe (ANS2 + NVMMU + SARTv4), framebuffer, keyboard and trackpad, and USB gadget. ADT-derived T6050 device trees and kernel patches (AIC locked VM-timer FIQ, SARTv4, SPMI gen 4, DockChannel MTP). SMP is the open blocker, which it attributes to SPTM. | 0 stars, not reviewed. Its SPTM-SMP theory conflicts with Asahi's evidence that raw-boot Linux runs. Useful for corroboration only. |
| `antiapplefox/m5-linux` | SPTM / iBoot static RE from IPSWs. Proposes an "XNU shim". | Based on static analysis of Apple binaries, which conflicts with Asahi's clean-room rules unless done by a sanctioned clean-room split. No hardware runs. |
| Cody Ho et al. (codyho.dev, Sept 2026) | Custom SPTM-emulating hypervisor for the MacBook Neo and M5 Air. LLM-written AGX driver for the M4 Mac mini (GLES 3.0), with M5 partial. | Heavy LLM use, including using Claude to disassemble SPTM, so it is incompatible with Asahi's LLM and RE policies for upstreaming. |
| `Sunrise-OS` (describes itself as an AI-powered Asahi fork), `aurora-silicon` (Windows-on-Apple-Silicon effort) | Forks carrying t8142 and other device trees | Not reviewed, not Asahi. |

---

## 12. Open questions and suggested verification (read-only or VM-only)
1. **T6051 versus 0x6050.** Are the M5 Pro and M5 Max distinguished only by MIDR? This needs MIDR_EL1 from m1n1 on this unit, which requires a boot-policy change and therefore user approval.
2. **T6050 SMP.** Watch m1n1 for a secondary-start fix. Check whether RVBAR is pre-locked to an mBoot/SPTM address on T6050.
3. **VZ guest SME exposure.** Boot an existing VZ Linux guest and check `/proc/cpuinfo` flags.
4. **VM GPU performance on M5 Max.** Run `llama-bench` natively (Metal, with and without `GGML_METAL_TENSOR_DISABLE`), under krunkit with Venus, and under API remoting.
5. **ANE exclave assignment.** Is the ANE usable without exclaves in raw-boot mode? This is Unknown and needs hardware RE under the clean-room rules.

**Note on observed content:** one search result, from a `drm-ai-reviews` archive, contained an embedded instruction unrelated to this task. It was ignored and not acted on.

---

## Sources

**Asahi Linux (website and docs)**
- https://asahilinux.org/docs/platform/feature-support/overview/
- https://asahilinux.org/docs/platform/feature-support/m1/
- https://asahilinux.org/docs/platform/feature-support/m3/
- https://asahilinux.org/docs/platform/feature-support/m4/
- https://asahilinux.org/docs/platform/feature-support/m5/
- https://asahilinux.org/docs/platform/feature-support/m6/
- https://asahilinux.org/docs/hw/soc/soc-codenames/
- https://asahilinux.org/docs/hw/devices/device-list/
- https://asahilinux.org/docs/sw/m1n1-hypervisor/
- https://asahilinux.org/docs/hw/soc/agx/
- https://asahilinux.org/docs/project/when-will-asahi-be-done/
- https://asahilinux.org/docs/project/board/asahi-board/
- https://asahilinux.org/docs/project/board/minutes/20250905/
- https://asahilinux.org/blog/
- https://asahilinux.org/2025/02/passing-the-torch/
- https://asahilinux.org/2025/03/progress-report-6-14/
- https://asahilinux.org/2025/05/progress-report-6-15/
- https://asahilinux.org/2025/08/progress-report-6-16/
- https://asahilinux.org/2025/10/progress-report-6-17/
- https://asahilinux.org/2025/12/progress-report-6-18/
- https://asahilinux.org/2026/02/progress-report-6-19/
- https://asahilinux.org/2026/04/progress-report-7-0/
- https://asahilinux.org/2026/06/progress-report-7-1/
- https://asahilinux.org/2026/08/progress-report-7-2/
- https://asahilinux.org/2026/09/m2-episode-1/
- https://asahilinux.org/copyright/
- https://asahilinux.org/llm-policy/ (alias https://asahilinux.org/slop/)
- https://asahilinux.org/governance/
- https://asahilinux.org/about/
- https://indico.freedesktop.org/event/12/contributions/532/ (XDC 2026 M3 GPU talk)

**Asahi and related GitHub repositories**
- https://github.com/AsahiLinux/docs (feature-support/*.md and device-list commit history)
- https://github.com/AsahiLinux/AsahiLinux.github.io (blog and policy sources)
- https://github.com/AsahiLinux/m1n1/blob/main/src/soc.h
- https://github.com/AsahiLinux/m1n1/blob/main/src/midr.h
- https://github.com/AsahiLinux/m1n1/blob/main/src/chickens.c
- https://github.com/AsahiLinux/m1n1/blob/main/src/smp.c
- https://github.com/AsahiLinux/m1n1/blob/main/src/firmware.c
- https://github.com/AsahiLinux/m1n1/pull/559
- https://github.com/AsahiLinux/m1n1/pull/578
- https://github.com/AsahiLinux/m1n1/pull/610
- https://github.com/AsahiLinux/m1n1/pull/626
- https://github.com/AsahiLinux/m1n1/pull/629
- https://github.com/AsahiLinux/m1n1/pull/643
- https://github.com/AsahiLinux/m1n1/pull/652
- https://github.com/AsahiLinux/m1n1/pull/661
- https://github.com/AsahiLinux/m1n1/pull/698
- https://github.com/AsahiLinux/m1n1/issues/706
- https://github.com/AsahiLinux/m1n1/commit/39d759de0f (SPTM IMPDEF sysreg emulation)
- https://github.com/AsahiLinux/m1n1/commit/84715318ae (stop trapping SME on M4+)
- https://github.com/AsahiLinux/m1n1/commit/3a69c73f59 (disable WFI/WFIT when WFI loses state)
- https://github.com/AsahiLinux/m1n1/commit/a735ea29ae (CTRR_M4 reservation)
- https://github.com/AsahiLinux/m1n1/commit/48d388bc51 (RVBAR on locked chips)
- https://github.com/AsahiLinux/m1n1/commit/7339546899 (RVBAR / SError)
- https://github.com/AsahiLinux/m1n1/commit/0e88df7bc9 (secondary watchdog)
- https://github.com/AsahiLinux/m1n1/commit/4184923ffb (AGX G15/G15X)
- https://github.com/AsahiLinux/m1n1/commit/2460b604c6 (GPLv2 relicensing clarification)
- https://github.com/AsahiLinux/m1n1/commit/57a9339ffd (nXS TLBI on M4)
- https://github.com/AsahiLinux/linux (branches `asahi`, `asahi-wip-7.2`, `apple-soc/dt-7.4`, `b4/nvme-fwabi`, `drivers/gpu/drm/asahi/hw/mod.rs`, `drivers/soc/apple/sart.c`)
- https://github.com/AsahiLinux/linux/pull/584
- https://github.com/AsahiLinux/asahi-installer/blob/main/src/main.py
- https://github.com/eiln/ane
- https://github.com/dougallj/applegpu

**Mainline Linux, Mesa and the kernel lists**
- https://github.com/torvalds/linux/blob/master/MAINTAINERS
- https://github.com/torvalds/linux (drivers listed in section 6; tag-ancestry checks via the GitHub compare API)
- https://github.com/torvalds/linux/commit/d97afae6f16a (arm64 `idle=`)
- https://lkml.iu.edu/2607.1/08053.html (arm64 `idle=` v2)
- https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2606.1/13498.html (Apple WFI state-loss erratum patch)
- https://lwn.net/Articles/1081810/ (PSCI-via-EFI RFC cover letter)
- https://lkml.iu.edu/2607.1/00282.html (PSCI EFI conduit patch 5/6)
- https://gitlab.freedesktop.org/mesa/mesa/-/blob/main/src/asahi/lib/agx_device.c

**Sven Peter / M4 SPTM coverage, people and organisation news**
- https://social.treehouse.systems/@sven/114278224116678776
- https://www.linux-magazine.com/Online/News/Asahi-Linux-Runs-into-Issues-with-M4-Support
- https://heise.de/-10346962
- https://media.ccc.de/v/39c3-asahi-linux-porting-linux-to-apple-silicon
- https://alyssarosenzweig.ca/blog/asahi-gpu-part-n.html
- https://www.phoronix.com/news/Rosenzweig-Leaving-Apple-Asahi
- https://www.phoronix.com/news/Alyssa-Rosenzweig-Joins-Intel
- https://www.theregister.com/2025/03/20/asahi_linux_asahi_lina/
- https://www.phoronix.com/news/Asahi-Lina-Steps-Down-Linux-GPU
- https://www.phoronix.com/news/Hector-Martin-Resigns-Asahi
- https://www.theregister.com/2025/02/13/ashai_linux_head_quits/

**Apple**
- https://www.apple.com/newsroom/2026/03/apple-debuts-m5-pro-and-m5-max-to-supercharge-the-most-demanding-pro-workflows/
- https://www.apple.com/newsroom/2025/10/apple-unleashes-m5-the-next-big-leap-in-ai-performance-for-apple-silicon/
- https://www.apple.com/newsroom/2023/10/apple-unveils-m3-m3-pro-and-m3-max-the-most-advanced-chips-for-a-personal-computer/
- https://www.apple.com/macbook-pro/specs/
- https://developer.apple.com/videos/play/tech-talks/111375/ (M3 / A17 Pro GPU)
- https://developer.apple.com/videos/play/tech-talks/111431/ (M5 / A19 GPU graphics)
- https://developer.apple.com/videos/play/tech-talks/111432/ (M5 / A19 GPU ML)
- https://developer.apple.com/videos/play/wwdc2026/330/
- https://machinelearning.apple.com/research/exploring-llms-mlx-m5
- https://developer.apple.com/documentation/hypervisor/hv_vcpu_get_sme_state(_:_:)
- https://developer.apple.com/documentation/hypervisor/hv_vm_config_get_el2_supported(_:)
- https://developer.apple.com/documentation/virtualization/vzgenericplatformconfiguration/isnestedvirtualizationsupported
- https://developer.apple.com/documentation/virtualization/vzvirtiographicsdeviceconfiguration
- https://support.apple.com/guide/security/startup-disk-security-policy-control-sec7d92dc49f/web
- https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/machine.h

**Virtualization and VM GPU**
- https://github.com/libkrun/krunkit (README and https://github.com/libkrun/krunkit/blob/main/docs/usage.md)
- https://github.com/containers/libkrun (README; now libkrun/libkrun)
- https://github.com/slp/homebrew-krun/blob/main/Formula/virglrenderer-krun.rb
- https://lima-vm.io/docs/config/vmtype/krunkit/
- https://github.com/containers/podman/blob/main/docs/source/markdown/podman-machine.1.md
- https://www.mankier.com/7/ramalama-macos
- https://github.com/ggml-org/llama.cpp/discussions/12985
- https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/VirtGPU.md
- https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-metal/ggml-metal-device.m
- https://archive.fosdem.org/2026/schedule/event/C9NF8K-api_remoting_for_llama_cpp_near-native_gpu_speed_in_macos_containers/
- https://github.com/utmapp/UTM/releases (v5.0.x notes)
- https://github.com/apple/container/issues/57
- https://github.com/apple/container/issues/1511
- https://github.com/qemu/qemu/commit/55cd59813f (FEAT_SME2 for HVF guests)
- https://github.com/qemu/qemu/commit/ca34bcb014 (SME disabled with nested virt)
- https://github.com/qemu/qemu/commit/d7a75ea483 (nested virt on HVF)
- https://patchew.org/QEMU/20250224165735.36792-1-j@getutm.app (2025 HVF SME disable)

**Third-party and community** (unverified claims)
- https://codyho.dev/blog/hypervisor-macbook-neo/
- https://codyho.dev/blog/gpu-driver/ (mirror: https://prismix.dev/news/735ab7f0d180)
- https://github.com/betizzel/omarchy-m5
- https://github.com/antiapplefox/m5-linux
- https://github.com/Sunrise-OS/m1n1 and https://github.com/Sunrise-OS/linux
- https://aurorasilicon.org and https://github.com/aurora-silicon
- https://github.com/libimobiledevice/libirecovery/blob/master/src/libirecovery.c (Mac17,x board and chip IDs)
- https://arxiv.org/abs/2606.12765 (Rigel; seen via search only)
- https://arxiv.org/abs/2607.19438 (BaseRT; seen via search only)
- https://developer.apple.com/download/files/Metal-Performance-Primitives-Programming-Guide.pdf (seen via search only)

**Local observations** (read-only, 2026-10-11): `sysctl` (hw.model, perflevels, hw.optional.arm.*, kern.hv*), `sw_vers`, `ioreg -p IODeviceTree` and `ioreg -l` on the target Mac17,6. Unique identifiers were omitted.
