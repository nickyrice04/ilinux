# Native Linux enablement plan: Apple M5 Max (t6050), MacBook Pro Mac17,6 / J716c

* **Date:** 2026-10-11
* **Machine:** chip-id 0x6050; mBoot-18000.161.10 (macOS 26.6.2); 3 clusters
  (M0, M1 = 6 M cores each; P = 6 P cores); AIC rev 11; DART t8110; ANS
  `iop,ascwrap-v6` + SART `sart,coastguard`; PMGR `pmgr1,t6050`.
* **Status of this document:** research plan. Nothing here has been booted.
* **Evidence labels:**
  * **Confirmed:** a primary source or this machine's ADT shows it.
  * **Likely:** strong indirect evidence.
  * **Hypothesis:** a reasoned guess that still needs a test.
  * **Unknown:** no evidence either way.
* **Policy:** everything here is local research. It is AI-generated, so it
  must not be contributed to Asahi Linux (D-007). It follows a clean-room
  approach: no Apple binary was disassembled or decompiled. Sources are m1n1
  (MIT ≤ v1.9.9, GPL-2.0+ after that), the Linux and AsahiLinux trees
  (GPL-2.0), and this machine's sanitized ADT.

Source snapshots used. `third_party/m1n1` is a blobless clone.
`third_party/asahi-linux` is a sparse, shallow clone of `asahi` plus the
fetched heads of `apple-soc/dt-7.4`, `apple-soc/drivers-7.4`, `asahi-wip`
and `b4/nvme-fwabi`; it also carries the local draft branch `t6050-local`.
The other branches were read through the GitHub API.

| Repo | Ref | Commit |
|---|---|---|
| AsahiLinux/m1n1 | `main` (v2.0.0-21) | `57a9339ffd1876e78297b17d34dece8cff8fa1ba` (2026-10-11) |
| AsahiLinux/m1n1 | tag `v1.9.9` (last MIT) | `809541515659bf4e504807fd72bc0a539be5eee7` |
| AsahiLinux/linux | `asahi` | `77cb8f24c2381a8abb7272d7bbdec548d6426a8a` (2026-08-20) |
| AsahiLinux/linux | `asahi-wip` | `94fb23346d522edf53722357c426a3e58030beea` |
| AsahiLinux/linux | `apple-soc/dt-7.4` | `a8ac6027e82415f431bbba49ab535c44f2edaf4d` |
| AsahiLinux/linux | `apple-soc/drivers-7.4` | `4edbfa916dbfba44af3ef2378cae2b2653c96058` |
| AsahiLinux/linux | `b4/nvme-fwabi` | `2d2b34f0d85cadebd794cad7a4d18d36829ac3a0` |
| AsahiLinux/linux | `efi-psci` | `ba9f31230c73a4ba3f7c75d8bff8e5e0aacfbb69` |

---

## 0. Summary

1. **m1n1 runs on t6050 single-core** and can read the NVMe.
   * **Confirmed:** PR #610 (`b2d3f5eba7ce`), #652 (`53f8ee9b54ba`) and #661
     (`9bfdf8aeca30`).
   * **SMP does not work.** PR #610 reports that the secondaries power on
     (visible in PMGR) but never run m1n1 code. Its review concluded that
     "the offset is correct but there's some bug in iboot or whatever".
   * **No fix exists** on m1n1 `main` as of 2026-10-11.
   * The root cause is **Unknown**. §1.2 ranks the hypotheses and gives a
     cheap test for each.
2. **The first concrete blocker for Linux was in our own draft DT.**
   * m1n1 matches DT `cpu@` `reg` against each core's real MPIDR. On M5 the
     MPIDR carries a core-type bit in Aff2: M = 0x4xxxx, P = 0x1xxxx (m1n1
     `5d84c4c34d3f`).
   * The previous draft used the ADT `reg` values (0x000 …). With those, m1n1
     would have pruned **every** CPU node, including the boot CPU.
   * **Fixed** in the generator (§4).
3. **NVMe needs two things that no Asahi Linux branch has:**
   * **SARTv4.** Drafted as patches 0001–0003.
   * **The M4+ register split** (NVMMU in ADT reg[3], NVMe in reg[9]) plus
     the I/O-queue base registers. Drafted as 0004–0005.
   * The macOS-15 firmware-ABI series (`b4/nvme-fwabi`) is already in the
     `asahi` branch.
4. **The PMGR table decodes cleanly** with m1n1's documented format.
   * 661 records, u16 ids, `ps-groups` addressing over 6 register blocks.
   * Two of those blocks sit on a second die at +0x21_0000_0000. That
     stride matches the ADT `aic-die-offset-stride`.
   * 188 power domains are now generated with their parents.
5. **The CPU DVFS tables decode cleanly from the ADT.**
   * P cluster: 20 states, 1.308–4.608 GHz.
   * M clusters: 15 states, 1.344–4.380 GHz.
   * Each state has a core voltage and an SRAM voltage.
   * They are self-consistent (the period field × frequency = 65535e6) and
     match a macOS measurement: 4.512 GHz single-thread = P state 19.
   * OPP tables and an energy model are generated for EAS.

Critical path: SMP root cause (m1n1, needs native work) ∥ single-core Linux
boot (a) → NVMe root (c) → input (d) → power (g). Display, audio, Wi-Fi, GPU and
ANE are each long-tail efforts.

---

## 1. What m1n1 knows about t6050 (and M4/M5 generally)

### 1.1 Facts, with file and commit

| Topic | Finding | File / commit | Label |
|---|---|---|---|
| SoC IDs | `T6050 0x6050`, `T6051 0x6051`. `EARLY_UART_BASE 0x505200000` | `src/soc.h`; `b2d3f5eba7ce` (PR #610, 2026-06-29) | Confirmed |
| MIDR parts | T6050 "M5 Pro Sotra": M 0x64, P 0x65. T6051 "M5 Max Sotra C": M 0x68, P 0x69. Both use `features_m4` and have no chicken init function | `src/midr.h`, `src/chickens.c` | Confirmed (code). Our unit reports chip-id 0x6050 but is an M5 Max, so which MIDR it has is Unknown (B-010) |
| MPIDR format | E core `0x80000X0Y`, P core `0x80010X0Y`, **M core `0x80040X0Y`** (X = cluster, Y = core). `is_ecore()` checks bits 16 and 18 | `5d84c4c34d3f`, `c4c4d575e12c` (`MPIDR_CORE_TYPE_P/M`) | Confirmed for M5 Pro |
| CPU start | t6050 uses `CPU_START_OFF_T6031 = 0x88000` from PMGR reg[0]. It writes `+0x4 = 1<<(4*cluster+core)` and `+0x8+4*cluster = 1<<core` | `src/smp.c` `smp_init()` / `smp_start_cpu()` | Confirmed (code) |
| Hypervisor CPU start trap | The hypervisor's CPUSTART hook table lists `0x6031, 0x6032, 0x6034, 0x6040, 0x6041` but **not 0x6050/0x6051**. So m1n1's hypervisor cannot yet trap macOS starting t6050 secondaries | `proxyclient/m1n1/hv/__init__.py` (~line 1560) | Confirmed |
| Locked IMPDEF sysregs (M4+) | `features_m4.apple_sysregs_unlocked = false`. m1n1 does not write RVBAR (`cpu-impl-reg`+0), CYC_OVRD, SPRR/GXF/AMX or L2C_ERR. Writing them SErrors. If the locked RVBAR differs from `_vectors_start`, `smp_start_cpu()` only prints a warning | `7339546899ce`, `53d4271`, `001637f`, `707d564`, `ea95cda`; `48d388bc5151` (hypervisor) | Confirmed |
| Shared SMP state | Since 2026-09-27, state shared by cores that may run with the MMU off lives in a Device-nGnRnE section; reset stacks are found by MPIDR | `d16a2f4e3c4d`, `1b469fcb618f` | Confirmed. These postdate the PR #610 test, see §1.2 H3 |
| WFI loses state (M4+) | mBoot sets and locks per-core chicken bits. For `!apple_sysregs_unlocked`, `kboot.c` appends ` idle=nop arm64.nowfxt` to the bootargs | `3a69c73f5933`, `9095a5ee70bf` (`src/kboot.c` ~line 321) | Confirmed |
| CTRR on secondaries | `kboot_prepare_dt()` reserves `[CTRR_C_LWR, CTRR_C_UPR]` (48 KiB on M4) for all `!apple_sysregs_unlocked` chips, so the DT needs nothing | `a735ea29aed4`; `src/kboot.c` ~line 2830 | Confirmed (M4). Size on M5 Unknown; m1n1 warns if > 48 KiB |
| Secondary watchdog | `wdt-version` 2 or 3 → m1n1 writes 0 to WDT reg[2] (disarms an approx. 120 s reset). **Our ADT: `wdt-version = 3`** | `0e88df7bc989`, `ffe667db24b5`; `src/wdt.c` | Confirmed |
| PMGR on M4 Pro/Max, A18 Pro, M5 | No `ps-regs`. Devices are addressed through `ps-groups[group] = (reg idx, offset, mask)` + a 24-bit device offset. u8 vs u16 ids are auto-detected | `fcaf4765c443` (PR #578), `3cb2ebe`, `400170c`, `f1ab786`; `src/pmgr.c`, `proxyclient/m1n1/adt.py` (`PMGRDevices`), `proxyclient/tools/pmgr_adt2dt.py` | Confirmed (format); validated on our ADT |
| PMGR power-state register (per device, 32-bit) | `PS_TARGET[3:0]`, `PS_ACTUAL[7:4]` (0xf active, 0x4 clock-gated, 0x0 power-gated), `WAS_PWRGATED` b8, `WAS_CLKGATED` b9, `DEV_DISABLE` b10, `PARENT_OFF` b11, `PS_AUTO[27:24]`, `AUTO_ENABLE` b28, `RESET` b31. m1n1 clears `AUTO_ENABLE`/`WAS_*` when setting a mode and powers parents first. Same layout as Linux `apple-pmgr-pwrstate` | `src/pmgr.c`, `src/pmgr.h`; `207c3b6` | Confirmed (code); t6050 unverified at runtime |
| PMGR on M6 | Moved to `/arm-io/pmgr-child` (`pmgr2,arch`); t6050 is not affected | `2307774`, `2e2f9b3` | Confirmed |
| SARTv4 | CONFIG 0x00, PADDR 0x60, SIZE 0xc0; shift 12; size max 2^30-1; flags 0xff. Chosen by ADT `sart-version` (ours = 4) | `9bfdf8aeca30` (PR #661; MIT at v1.9.9) | Confirmed |
| NVMe M4+ | `nvme-secure-bar` → NVMMU = reg[3], NVMe = reg[9]. Writes I/O CQ/SQ base to nvme+0x1208/+0x1200 after CREATE_SQ. Read `cdw12` is 0-based | `53f8ee9b54ba` (PR #652), `34925643ca62` | Confirmed |
| NVMe firmware ABI (macOS 15+) | TCB opcode 0; DMA direction only when PRP1 ≠ 0; no PRP-null-check chicken bit (0x24008 SErrors) | `b0cdce107543`, `0e77db5bf051`, `1aead9e78af0` | Confirmed |
| ASC / mailbox | Every IOP uses `cpu_base = reg[0]`, mailbox at `reg[0]+0x8000`, CPU_CONTROL 0x44; works for the t6050 ANS | `src/asc.c` | Confirmed (m1n1) |
| SPMI gen 4 | ADT `gen >= 4` → STATUS 0x200, CMD 0x210, REPLY 0x220, RX_EMPTY bit 30, TX_EMPTY bit 14. Tested on T6050 | `a09a5e260759`, `5d6df45` (PR #626) | Confirmed (FIFO). IRQ/flush registers Unknown |
| USB-PD | tps6598x over SPMI (`usbc,sn201202x,spmi` here) | `ef33092`, `4d18204`, `aa034e1` | Confirmed (m1n1) |
| Debug console | Dockchannel UART fallback (`/arm-io/dockchannel-uart`, present in our ADT). "debugusb" is enabled when authenticated-root is disabled. **Linux and u-boot have no dockchannel-uart driver yet** | `e3b42cbdd55d`, `1a0e81f9dcd9`, `5130a9a` | Confirmed |
| AIC | kboot uses `apple,t8122-aic3` | `35c76ab` | Confirmed |
| cpufreq | `src/cpufreq.c` supports up to T6034/T8122. **t6050 is "unsupported"**, so no cluster init or default p-state | `src/cpufreq.c` | Confirmed |
| MCC | Supports t8132/t8140/t604x, not `mcc,t6050` | `src/mcc.c`; `e9920b9`, `6e6b8fe` | Confirmed |
| PCIe / ATC | No `apcie,t6050` and no `atc-phy,t6050` handling. `kboot_atc` knows t8122/t8130/t8132 | `src/pcie.c`, `src/kboot_atc.c` | Confirmed |
| Display | `display_configure()` is skipped for OS firmware ≥ 15.0 B1. Linux gets mBoot's framebuffer unchanged | `809541515659` | Confirmed |
| Firmware table | `mBoot-18000.161.10` = macOS 26.6.2 (ours) | `src/firmware.c`; `3e354a2` | Confirmed |
| Hypervisor on M4+ | SPRR/GXF emulation and SPTM IMPDEF-sysreg shadowing (PR #643, `39d759de0f20`); nXS TLBI (`57a9339`). The `sprr-sptm-combined` branch (2026-10-11) stops auto-enabling the emulation on M4 | `src/hv/hv_sptm.[ch]`, `proxyclient/m1n1/hv/impdef.py` | Confirmed |
| PSCI via EFI | Branch `psci-via-efi` (`8e4f1012242a`, not merged): CPU_ON releases cores m1n1 has already started; CPU_SUSPEND 1 = `deep_wfi()` | m1n1 `psci-via-efi`; Linux `efi-psci` (`26045a9edd6f` conduit, `ba9f31230c73` t8103 DT) | Confirmed (RFC) |
| License | MIT ≤ v1.9.9; GPL-2.0-or-later from v2.0.0 | `ce2b8a43cea4`, `2460b604c6f0` | Confirmed |

### 1.2 SMP on t6050: what is known, ranked hypotheses, and tests

**Known**

* The cores turn on (PMGR shows them) but never set their spin-table flag
  within 100 ms (PR #610, tested on macOS 26.2b2 and 27.0b2).
* The start sequence used is the T6031 one.
* On our machine:
  * the ADT gives every CPU `function-enable_core = <&pmgr 'Core' BIT(cpu-id)>`
    and `function-cpu_idle = <&pmgr 'cpuI'>` (**Confirmed**, 2026-10-11
    capture). macOS starts and idles cores through PMGR "platform functions";
    m1n1 does not use them;
  * PMGR has per-core power-state registers `MCPU0_0..MCPU1_5`, `PCPU_0..5`
    at PMGR reg[0] + 0x00..0x88 (stride 8), plus `MCPM0/1` and `PCPM`
    (decoded here);
  * P cores carry `cluster-power-down = 1`; M cores don't.

**Hypotheses (most to least likely), each with a cheap native test through
the m1n1 USB proxy:**

1. **H1 (Likely): the locked RVBAR does not point at m1n1.**
   * On M4+, m1n1 cannot write RVBAR and relies on mBoot having set it to the
     boot object's entry point.
   * On t6050, mBoot (or the SPTM-era boot flow) may lock it to another
     address, so cores would start somewhere else.
   * **Test:** `p.read64(cpu_impl_reg)` for each core before and after
     `smp_start_secondaries()`. m1n1 already prints "RVBAR … is locked and
     differs". Also check the stage-1 vs stage-2 entry (chainloading changes
     `_vectors_start`).
2. **H2 (Likely): t6050 needs more than the T6031 two-register CPU_START
   protocol.** This is what the "Core" platform function suggests.
   * One clue: the `+0x4` write uses 4 bits per cluster, and t6050 clusters
     have 6 cores. Cluster 1 cores 0–1 alias cluster 0 cores 4–5 in that
     register.
   * **Test:** read back CPU_START `+0x0..+0x14` and the per-core PMGR PS
     registers after each start attempt.
   * Then trace macOS's own secondary start with the m1n1 hypervisor. That
     needs `0x6050` added to the hypervisor CPUSTART table, plus PMGR MMIO
     tracing.
   * Hypervisor tracing is the sanctioned clean-room method, but under
     Asahi's policy the interpretation must be done by humans.
3. **H3 (Hypothesis): early-entry cache or attribute problem.**
   * PR #610 predates `d16a2f4` (Device-nGnRnE shared state) and `1b469fc`.
   * **Test:** retest with current `main` first. It's free.
4. **H4 (Hypothesis): the secondary trips over a locked or different sysreg
   in `_cpu_reset_c`** before it sets its flag.
   * **Test:** watch the dockchannel debugusb log for the 'O'/'K' characters
     that `cpu_reset` prints.

**Linux side once m1n1 starts the cores:** only the DT is needed. Use
spin-table with MPIDR `reg` values (done), keep `idle=nop arm64.nowfxt`
(automatic), and keep the CTRR reserve (automatic). PSCI-via-EFI is the path
to CPU hotplug and suspend later.

---

## 2. What already exists in AsahiLinux/linux

| Area | Where | Applies to t6050? |
|---|---|---|
| NVMe macOS-15+ firmware ABI | `b4/nvme-fwabi`: `7d5e1d1d85fb`, `d2bdc9edf220`, `c64e4895d112`, `04fa7c4f1bfa`, `1e8c7bbc5069`, `2d2b34f0d85c` (on v7.2-rc1). In `asahi` as `9c02d723ef80`, `07133e8a2fb8`, `835cbc4205ac`, `055df6031321`, `c3d4bb4f1cab`, `a4f6716c6a69` | **Yes**, required. Already in `asahi` |
| NVMe M4+ register split / IOQ base | none of `asahi`, `asahi-wip`, `apple-soc/drivers-7.4`, `b4/nvme-fwabi`, `bits/050-nvme` | **Missing.** Drafted as patch 0005 |
| SART | `drivers/soc/apple/sart.c`: v0 (t8015), v2 (t8103), v3 (t6000) | **SARTv4 missing.** Drafted as 0001–0003 |
| AIC3 | `irq-apple-aic.c` `apple,t8122-aic3` (mainline 7.3) | Likely works. See §3a for the VM-timer FIQ risk |
| M4 (t8132) minimal DT | `apple-soc/dt-7.4`: `23850378ade7` + bindings `4be8659603b0` … `f8805ac96c9b` | Template for our DT (conventions copied) |
| A18 Pro (t8140) DT | `apple-soc/dt-7.4` | — |
| PMGR misc controls | `apple-soc/drivers-7.3`: `fef9350c314b` (+ binding `a49c2acde67e`) | Unknown relevance |
| PSCI via EFI | `efi-psci`: `654eb24c44be`…`ba9f31230c73` (RFC, 2026-07) | Future SMP and idle path |
| cpufreq | `apple-soc-cpufreq.c` (t8103 / t8112 / generic) | Likely, with `t8112` 5-bit p-states (§3f) |
| DART | `apple-dart.c` `apple,t8110-dart`; `bits/020-dart` (`1143d0263e3a` "Use remap feature") | Likely (ADT `dart,t8110`, has `remap`) |
| Dockchannel / MTP HID | `drivers/soc/apple/dockchannel.c` (asahi) | Likely the base for t6050 input (§3d) |
| ASC mailbox | `drivers/soc/apple/mailbox.c` (`apple,asc-mailbox-v4`) | Likely (m1n1 uses the v4 layout for ascwrap-v6) |
| SPMI | `spmi-apple-controller.c` (gen 1 layout only) | **Gen 4 missing** (§3d) |
| arm64 `idle=` | mainline 7.3-rc1 | **Required** (m1n1 passes `idle=nop`) |

---

## 3. Dependency-ordered plan

```
(a) 1-core shell ──► (c) NVMe root ──► (d) input/USB ──► (g) PM/idle ──► (h) audio
     │                  ▲                   │
     └─► (b) SMP ───────┘ (independent; needs m1n1)  (e) display (long)  (f) cpufreq/EAS ◄─ (b)
                                                       (i) Wi-Fi N1 (very long)  (j) GPU/ANE (very long)
```

Difficulty scale: Low / Medium / High / Very high. "Offline" means it can be
done without booting t6050 (desk work, the VM, or macOS read-only probes).
"Native" means it needs a real boot of m1n1 or Linux on this machine, which
in turn needs the user's explicit authorization and a deployment plan (boot
policy, stub macOS, recovery).

### (a) Single-core shell via initramfs (serial or framebuffer)

**Upstream / Asahi status**

* Every driver needed for a framebuffer shell exists:
  * AIC3, arch timer, `simple-framebuffer` / simpledrm (m1n1 passes mBoot's
    framebuffer), pinctrl-apple-gpio, `apple_wdt`, `i2c-pasemi`,
    `apple-pmgr-pwrstate`;
  * m1n1 boots t6050 single-core.

**Missing for t6050**

1. **DT.** Done as a draft (`kernel/experiments/t6050-dt/out/`; in-tree
   form as patch 0007). The MPIDR-correct CPU `reg` is mandatory (Confirmed,
   see §0.2).
2. **Kernel config.**
   * `CONFIG_ARM64_16K_PAGES=y`, as Asahi does.
   * `ARCH_APPLE`, `APPLE_AIC`, `APPLE_PMGR_PWRSTATE`, `PINCTRL_APPLE_GPIO`,
     `DRM_SIMPLEDRM`, `FRAMEBUFFER_CONSOLE`, `BLK_DEV_INITRD`.
   * A kernel ≥ 7.3 for `idle=`.
   * SME-only support (no SVE) is in mainline. Never build with `-march`
     values that imply SVE (D-009, F-016 context).
3. **Bootargs.** m1n1 adds `idle=nop arm64.nowfxt`. Add
   `pd_ignore_unused clk_ignore_unused` and a debug `loglevel`; the PMGR
   table is unvalidated (Hypothesis-level safety measure).
4. **Console.**
   * The internal UART0 isn't reachable on laptops.
   * A serial console needs a **Linux dockchannel-uart driver** (missing)
     plus debugusb (m1n1 `1a0e81f`, enabled by
     `csrutil authenticated-root disable`, a boot-policy change) and a second
     machine.
   * First target: a framebuffer console with a non-interactive initramfs
     that logs to the screen. m1n1's `phram` MTD for its own log also
     appears.
   * Keyboard input needs (d).
5. **Risk: AIC VM-timer FIQ register.**
   * In VHE mode the AIC driver writes `SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2` on
     every CPU at init.
   * An unreviewed community T6050 patch (`betizzel/omarchy-m5`) claims it is
     locked on T6050 (Hypothesis). If so this SErrors at boot.
   * **Mitigation draft:** guard the access behind a capability check. This
     is not written yet because there is no evidence beyond the claim.
   * **Test:** m1n1 proxy `mrs`/`msr` of that sysreg at EL2.
6. Optional: MIDR part numbers in `arch/arm64/include/asm/cputype.h` (errata
   lists), once this unit's MIDR is known (B-010).

**Sources:** m1n1 `src/kboot.c`, `5d84c4c3`; Asahi t8132 DT
(`apple-soc/dt-7.4`); this machine's ADT.

**Difficulty:** Medium (DT done). Risk sits in the unknowns: AIC VM-timer lock,
the PMGR "unused" power-off, and memory map details m1n1 fills in.

**Offline**

* DT compiles with 0 dtc warnings: done.
* `dtbs_check` and a kernel build in the VM: pending.
* A boot test in the VM is **not** meaningful, because Apple devices aren't
  emulated.

**Native:** all runtime validation.

### (b) SMP

**Upstream / Asahi status:** Linux needs nothing beyond the DT; spin-table via
m1n1. m1n1 fails to start t6050 secondaries (§1.2).

**Missing for t6050:** the m1n1 root cause and fix. Possibly a new PMGR
"Core" start protocol. Later, PSCI-via-EFI for hotplug and suspend.

**Sources:** PR #610 (+ review); `src/smp.c`; `d16a2f4`, `1b469fc`;
`psci-via-efi`; the ADT `function-enable_core`.

**Difficulty:** High (root cause Unknown). The fix itself may be small.

**Offline:** read the m1n1 code (done). Prepare the proxy test script that
reads only RVBAR, CPU_START and the PMGR PS registers (to be written as a
local m1n1 proxyclient experiment; nothing executed on the host).

**Native:** everything else.

**Validation:** m1n1 "Started." for all 17 secondaries; Linux
`smp: Brought up 1 node, 18 CPUs`.

### (c) NVMe root

**Upstream / Asahi status:** `nvme-apple`, RTKit, ASC mailbox v4 and SART
v0–v3 exist. The macOS-15 firmware-ABI series is in `asahi`.

**Missing for t6050 (drafted):**

* SARTv4 (0001–0003);
* the M4+ NVMMU/NVMe split and I/O-queue bases (0004–0005);
* DT nodes for `sart`, `ans_mbox` and `nvme`, generated but disabled:
  * NVMe: reg[9] → 0x4_5dcc0000, mapped 0x40000 (Likely);
  * NVMMU: reg[3] → 0x4_1dcc0000 (+0x60010);
  * ANS: reg[0] → 0x4_19600000;
  * mailbox: ANS + 0x8000;
  * NVMe IRQ 2338 (ADT `nvme-interrupt-idx = 4`, Confirmed);
  * mailbox IRQs 1347–1350 (Likely);
  * power domains `ps_ans`, `ps_apcie_sys_st0`, `ps_apcie_sys_st1`.

**Missing and not drafted:**

* A root filesystem location. This needs an APFS resize or partitioning
  plan, which needs user authorization. The Asahi installer doesn't support
  M5.
* Also check: ANS clock-gates are empty in the ADT on M4+ (Confirmed), so
  domain assignment is by PMGR name.

**Sources:** m1n1 `53f8ee9b`, `9bfdf8ae`, `b0cdce1`, `0e77db5`, `1aead9e`;
Sven Peter's `b4/nvme-fwabi`.

**Difficulty:** Medium.

**Offline:** compile test in the VM, `dt_binding_check`.

**Native:**
1. read-only probe of the namespace list (ADT `namespaces`);
2. read-only mount;
3. writes, only after the user approves a partition plan.

### (d) USB, keyboard, trackpad

**Internal keyboard and trackpad**

* Path: MTP coprocessor (`/arm-io/mtp`, `iop,ascwrap-v6`, RTKit) + DART
  `dart-mtp` + `dockchannel-mtp` (`dockchannel,t8002`, IRQ 660) +
  `hid-transport,mux`.
* **Asahi:** dockchannel and MTP HID work on M2 laptops; the M4 MBP keyboard
  is still an open community PR (#567).
* **Missing for t6050:**
  * DT nodes. Addresses are all in the ADT. DART nodes are drafted,
    disabled.
  * The MTP firmware load path (Unknown on M5). The touchpad firmware blob
    is extracted by Asahi's installer on older machines.
  * MTP-related PMGR devices are all *virtual* (no PS register): power is
    coprocessor-managed (Confirmed from the table).

**USB**

* Needs:
  * the ATC PHY: `atc-phy,t6050;atc-phy,t6040`. Neither the Linux
    `apple-atcphy` nor m1n1 `kboot_atc` knows t6040/t6050 tunables;
  * dwc3: `usb-drd,t6050;usb-drd,t8142`, `dwc3-apple`;
  * the DARTs `dart-usb0..2` (drafted, domains `ps_atc{0,1,2}_usb` from ADT
    clock-gates);
  * **USB-PD over SPMI** (`usbc,sn201202x,spmi` on `nub-spmi-a1`). That in
    turn needs:
    * **SPMI gen 4** support in `spmi-apple-controller.c`. The m1n1 FIFO
      offsets are known; the IRQ and flush registers are Unknown;
    * a tipd/tps6598x SPMI transport (exists only in m1n1).

**Sources:** m1n1 `a09a5e2`, `ef33092`, `aa034e1`; Asahi dockchannel; the ADT.

**Difficulty:** High.

**Offline:** DT, an SPMI gen-4 FIFO patch (feasible; deferred because of the
unknown IRQ registers), compile tests.

**Native:** everything functional. USB-C ports are also the m1n1 proxy
channel, so be careful.

### (e) Display (DCP)

**Status**

* The boot framebuffer works through simpledrm: m1n1 passes mBoot's
  framebuffer and does not touch the DCP on firmware ≥ 15 (`809541515659`)
  (Likely).
* Asahi's DCP driver targets older firmware ABIs (13.5 / 14.x; the V14_7
  work is in progress).

**Missing for t6050:**

* the DCP firmware ABI of macOS 26.x (new tracing required);
* the `disp0,t605x` and `display-crossbar,t6050` details;
* DCP DART mappers that include `-exclave` entries (impact Unknown);
* a backlight controller on I2C7 (`disp-bklt`, addr 0x44). It might be
  usable without the DCP (Hypothesis).

**Sources:** m1n1 `src/dcp*`, the hypervisor `trace_dcp`, Asahi DCP.

**Difficulty:** Very high. Asahi's policy treats LLM-interpreted traces as
forbidden for upstream.

**Offline:** none beyond the DT.

**Native:** a hypervisor-traced macOS (SPTM emulation exists, PR #643).

### (f) cpufreq + energy model (EAS) from the ADT DVFS tables

**Upstream / Asahi status:** `apple-soc-cpufreq` with OPP tables. Asahi DTs
use `opp-level` = p-state and `capacity-dmips-mhz`, but no energy model.

**t6050 data (Confirmed from the ADT)**

* `pmgr` `acc-clusters` = (M0 → `voltage-states22`, M1 → 23, P → 5).
* Each table pairs `(65535e6 / f_kHz, core mV)` with `-sram` =
  `(f_kHz, SRAM mV)`. The generator asserts that product for every state.
* M: 15 states, 1344–4380 MHz, 600–1025 mV.
* P: 20 states, 1308–4608 MHz, 625–1090 mV.
* Cluster DVFS blocks at 0x2_10e20000 / 0x2_11e20000 / 0x2_12e20000, from
  PMGR reg entries of size 0x12e8. That is the M1–M3 address pattern
  (Likely).

**Cross-checks**

* macOS single-thread `cpubench freq` = 4.512 GHz = P state 19 (Confirmed).
* IOReport residency names `V0P14..V14P0` give 15 M states (Confirmed).

**Generated** (in the draft DT):

* three OPP tables (`opp-hz`, `opp-level` = index+1, `opp-microvolt`);
* `performance-domains`;
* `dynamic-power-coefficient` P 1054 / M 550 uW/MHz/V²;
* `capacity-dmips-mhz` P 1024 / M 768.

**Hypotheses to settle natively**

* the p-state index mapping (index+1 as on M1–M3);
* the t8112-style 5-bit DVFS command field;
* whether m1n1 or Linux must do M3-style cluster init (m1n1 `cpufreq.c`
  writes `+0x440f8` on M3; it skips t6050);
* `clock-latency-ns` (placeholder 50 µs; measure with m1n1
  `experiments/cpu_pstate_latencies.py`);
* the EM coefficients. They come from macOS IOReport energy at a single OPP
  (fma kernels) and include leakage. Replace them with per-OPP measurements
  on native Linux.

**Then:**

* `omarchy-qos` tiers (uclamp) on native Linux;
* compare placement against macOS QoS (M cores ≈ 4× better energy per
  FLOP).

**Difficulty:** Medium.

**Offline:** done (decoding and DT). EM sanity math.

**Native:** DVFS writes and frequency verification (cpubench `freq`).
Energy needs a Linux power telemetry source (SMC keys or PMGR energy
counters, B-008 follow-up).

### (g) Power management and idle

**Status**

* m1n1 forces `idle=nop` on M4+ (WFI state loss), so **idle CPUs spin**.
  Expect high idle power and heat (Likely).
* Fix paths:
  1. a downstream Asahi cpuidle driver that saves state;
  2. PSCI-via-EFI CPU_SUSPEND into m1n1 `deep_wfi`. Both need RVBAR to land
     in code that can restore state, which is the same issue as SMP H1.
* Runtime PM: 188 genpd domains generated. Start with `pd_ignore_unused`,
  then enable domains one by one.
* SMC (battery, thermal, fans): `macsmc` (asahi) over RTKit on the `smc` IOP
  (`iop,ascwrap-v6`). Needs the DT plus a check of the key set.
* System suspend doesn't work even on M3 (Asahi); not planned.

**Difficulty:** High.

**Offline:** the DT and the plan; design a WFI-safe idle state for the
draft. **Native:** everything else.

### (h) Audio

**Hardware in the ADT**

* Six speaker amps `audio-control,sn012776` on I2C1/I2C3.
* Codec `cs42l84` on I2C2 (headphone jack).
* ADMAC `admac-evolution,t6050`.
* MCA and audio PMGR domains are virtual (AOP-managed).
* Mics go through `iisaudio,isolated-stream-proxy` (exclave).

**Asahi:** tas2764/tas2770 (sn012776 is likely in that family: Hypothesis),
cs42l84, macaudio, `apple-admac` (t8103 / t6000 / t8112),
`speakersafetyd`.

**Missing for t6050**

* ADMAC "evolution" support (m1n1 proxyclient has t603x ADMAC only);
* the MCA/AOP routing on M5;
* speaker-safety calibration;
* mics, likely blocked by exclaves.

**Difficulty:** High (speakers) / Very high or blocked (mics). **Native**
needed throughout.

### (i) Wi-Fi and Bluetooth (Apple N1)

**Status:** Apple's own N1 chip. No Linux driver and no public documentation.
Asahi lists it as unsupported.

**Missing:** everything (bus protocol, firmware interface).

**Offline next step:** extend the extractor whitelist to the WLAN/BT PCIe
nodes' `vendor-id`/`device-id`/class (non-identifying, *never* the MAC
values; they stay denylisted) to learn the bus identity.

**Difficulty:** Very high or Unknown.

**Stop-gap:** USB networking once (d) works.

### (j) GPU (G17) and ANE

**GPU**

* `gpu,t6050` with two firmware coprocessors `gfx-asc` and `gfx1-asc`
  (F-010).
* Asahi AGX and Mesa support G13/G14; G15 is still being reverse-engineered.
* G17 needs a new firmware interface, ISA support and the matrix units.
* PMGR GPU domains (`GFX_SGX`, `GFX_ASC*`) are virtual. Only `GPX/AFR/CS/GFX`
  have PS registers (block `pmgr_gfx`).
* Very high; multi-year community work. Disassembling Metal or the shader
  compiler is forbidden.

**ANE:** `ane,t8132exclave`, exclave-mediated (F-011). Feasibility from a
non-secure kernel is Unknown.

**Offline:** documentation, and the GPU-in-VM stop-gap (Roadmap 1.7).

---

## 4. Artifacts produced in this pass

| Path | What |
|---|---|
| `hardware/scripts/adt_extract.py` | Whitelist extended (PMGR `devices`/`ps-groups`/`voltage-states*`/`acc-clusters`/`perf-*`, CPU `function-*`, SART/NVMe/DART layout); full-hex binary tables; **content-based leak check** (denylisted values compared in memory against every output representation; `--check-only`). Denylist only extended |
| `hardware/adt/adt-sanitized.json`, `adt-nodes.tsv` | Re-extracted 2026-10-11: 656 nodes, leak check "54 denylisted values compared, 0 problems" |
| `kernel/experiments/t6050-dt/gen_t6050_dt.py` | Stdlib-only generator: PMGR decode, power domains + parents, MPIDR fix, OPP/EM, cpufreq, DARTs (disabled), SART, ANS mailbox, NVMe (disabled) |
| `kernel/experiments/t6050-dt/out/t6050.dtsi`, `t6050-pmgr.dtsi`, `t6050-j716c.dts` | Generated DT. `validate.sh`: **OK, 0 dtc warnings** |
| `kernel/experiments/t6050-dt/validate.sh` | Fixed a glob bug (it recompiled its own `.pre.dts`); now fails on any dtc warning |
| `kernel/patches/t6050/0001…0007*.patch` + `README.md` | SARTv4, NVMe M4+ split, bindings, DT. Untested; compile test pending |

---

## 5. Top next actions

1. **Compile-test the series and the DT in the VM** (`git am` on
   `asahi@77cb8f24`; build `sart.o` and `apple.o`; `dt_binding_check`;
   `dtbs_check`).
   * Needs: the VM to be free (another agent is using it now).
   * Needs: about 250 MB of kernel source (a tarball of one commit) and
     `dtschema` in a VM venv.
   * No native boot.
2. **Native m1n1 diagnostics session (read-only probes).**
   * Covers the RVBAR, CPU_START and PMGR per-core PS registers (SMP H1/H2),
     MIDR (B-010), the DVFS register format, and the AIC VM-timer sysreg
     lock.
   * Needs **user authorization**: Permissive Security plus an m1n1 boot
     object via `kmutil configure-boot` in recoveryOS; optionally
     `csrutil authenticated-root disable` for debugusb.
   * Also needs a second computer for the proxy, and a written
     deployment and rollback plan first (Roadmap Phase 3).
3. **Single-core Linux framebuffer boot** with the draft DT and an
   initramfs.
   * Needs: action 2's setup.
   * Needs a 16K-page Asahi-based kernel built in the VM.
   * Needs **user authorization** per boot experiment.
4. **NVMe read-only bring-up** (patches 0001–0005).
   * Needs: native boot (3).
   * Writes or a Linux root need a separate, user-approved partitioning
     plan.
5. **Offline driver drafting for the next blockers:**
   * SPMI gen 4 (FIFO part from m1n1 `a09a5e2`, MIT);
   * a Linux dockchannel-uart console driver (register layout in m1n1
     `src/dockchannel_uart.c`, GPL-2.0+ code or the MIT-era version in
     v1.9.9);
   * extractor whitelist for WLAN/BT PCIe IDs.
   * Needs: VM compile tests only.

---

## 6. Open questions (tracked)

* Q1. t6050 SMP root cause (H1–H4).
* Q2. This unit's MIDR: 0x64/0x65 (T6050) or 0x68/0x69 (T6051)?
* Q3. Is `SYS_IMP_APL_VM_TMR_FIQ_ENA_EL2` locked on t6050?
* Q4. Does the AIC report 2 dies (ADT `aic-numdies-per-die = 2`)? If so,
  how do second-die IRQs map? The ADT numbers are flat and < 4096.
* Q5. The NVMe window size (0x10000 in the ADT vs. accesses up to +0x24910)
  and `NVMMU_TCB_STAT` (0x28120 vs. 0x29120).
* Q6. SARTv4 has room for 24 entries. Does the hardware implement more than
  16? Does the SART lose its state when ANS is power-gated
  (`sart-power-reg-offset 0x13e8`)?
* Q7. The DVFS p-state index mapping and register format; the cluster init
  needed before Linux cpufreq works.
* Q8. Which PMGR domains are firmware-locked on M5 (the M4 analogues are
  `DISP*_CPU`)? Which domains reboot the machine when gated (ANS on M4)?
* Q9. The size of the secondary-core CTRR region on M5.

---

## 7. Sources

* m1n1: https://github.com/AsahiLinux/m1n1 (PRs #559, #578, #610, #626, #643,
  #652, #661; branches `psci-via-efi`, `sprr-sptm-combined`). Local clone
  `third_party/m1n1` @ `57a9339`.
* AsahiLinux/linux: branches `asahi`, `asahi-wip`, `apple-soc/dt-7.4`,
  `apple-soc/drivers-7.3`, `apple-soc/drivers-7.4`, `b4/nvme-fwabi`,
  `efi-psci`. Local sparse clone `third_party/asahi-linux`, plus a local
  branch `t6050-local` that holds the drafts.
* This machine's sanitized ADT: `hardware/adt/adt-sanitized.json`
  (2026-10-11).
* Measurements: `benchmarks/results/macos-2026-10-11-power/power.jsonl`,
  `benchmarks/results/macos-2026-10-11-*/cpu.jsonl`.
* Asahi status research: `research/asahi/asahi-status-m5-2026-10.md`.
