# t6050 (M5 Max) device tree: DRAFT

**Status:**

* The tree is generated from data and compile-checked with `dtc` 1.8.1:
  `validate.sh` reports **0 warnings** and fails on any.
* Schema-checked inside the kernel tree with the seven patches applied:
  `make CHECK_DTBS=y apple/t6050-j716c.dtb` (dtschema 2026.9, full processed
  schema) reports **0 findings**, and `make dt_binding_check
  DT_SCHEMA_FILES=apple` nothing for the bindings the series touches
  (`virtualization/jobs/044-t6050-dtbs-check/`, 2026-10-16). A clean check
  validates property shapes against the bindings, not the hardware facts in
  the table below.
* It has **never been booted**. It can't be until m1n1 can boot Linux on
  t6050, and every boot experiment needs the user's explicit authorization
  and a deployment plan (`roadmap.md` Phase 3).
* Plan and evidence: `../../native-enablement/plan.md`.

## What it is

`gen_t6050_dt.py` (Python standard library only) turns the sanitized macOS ADT
capture (`hardware/adt/adt-sanitized.json`) into three files.

### `out/t6050.dtsi`

* **18 CPUs.** `reg` is the real MPIDR: M = `0x40000|cluster<<8|core`,
  P = `0x10000|cluster<<8|core`. The tree also has L2 caches and the
  cpu-map.
* **Three OPP tables** (one per cluster).
* **Three cluster cpufreq controllers.**
* **AIC3** and the arch timer.
* **The watchdog.**
* **Pinctrl:** AP, AOP and NUB.
* **9 × I2C and UART0.**
* **6 PMGR blocks.**
* **42 t8110 DART instances**, all `status = "disabled"`.
* **SART (SARTv4), the ANS mailbox and NVMe** (M4+ layout, disabled).
* **The SMC and its mailbox** (2026-10-16; `smc` disabled until verified).

### `out/t6050-pmgr.dtsi`

188 PMGR power domains with their parent dependencies.

### `out/t6050-j716c.dts`

The board file for Mac17,6 (J716c).

The scope goes past the Asahi "minimal" t8132 DT (2026-07) in three ways:

* power domains (needed by every node);
* DVFS / energy-model data;
* disabled draft nodes for the storage path.

The storage nodes need the local kernel patches in `../../patches/t6050/`.
The same three files are in patch 0007 as
`arch/arm64/boot/dts/apple/t6050*`.

```sh
python3 -I gen_t6050_dt.py ../../../hardware/adt/adt-sanitized.json out
./validate.sh      # needs third_party/dtc/dtc and third_party/dt-include
```

## Evidence and confidence per element

| Element | Source | Confidence |
|---|---|---|
| CPU count, clusters, cache sizes | ADT `/cpus`, `sysctl hw.perflevel*` | Confirmed |
| CPU `reg` = MPIDR (M 0x4xxxx, P 0x1xxxx) | m1n1 `5d84c4c34d3f` (MPIDR examples, tested on M5 Pro). m1n1 `dt_set_cpus()` prunes DT CPUs whose `reg` doesn't match | Likely (needs this unit's MPIDR) |
| CPU `compatible` `apple,sotra-m/-p` | named after m1n1's "Sotra" and M-core naming, following Asahi's `apple,donan-e/-p` | Placeholder |
| AIC3 core 0x2_80400000 (+0x1cc000), event at +0x40000 | ADT `aic` reg via `arm-io` ranges; `aic-iack-offset` | Likely |
| AIC3 layout | ADT `extint-baseaddress` 0x10000 = Linux `AIC3_IRQ_CFG`; `extintrcfg-stride` 0x4a00 = Linux die stride for 4096 IRQs | Likely |
| AIC dies | ADT `aic-numdies-per-die = 2`, `aic-die-offset-stride = 0x21_0000_0000`; 3-cell specifiers are used | Unknown (see plan Q4) |
| PMGR record format | m1n1 `proxyclient/m1n1/adt.py` `PMGRDevices` (48 B), `PMGRPSRegs` (12 B); `src/pmgr.c` | Confirmed (format); decodes to 661 unique records |
| PMGR blocks | `ps-groups` → pmgr reg[0], [1], [9], [51], [46], [49]. Groups 4–5 hold `*_GFX` duplicates (AIC_GFX, NUB_GFX_GPIO), media and AMCC, at +0x21_0000_0000, which matches the AIC die stride: a second die | Confirmed (data); "second die" Likely |
| PMGR domain selection | Skipped: 338 virtual (`no_ps`) and 135 CPU/fabric/die-bridge/memory-controller domains, like Asahi t8132. Virtual or skipped parents are replaced by their nearest emitted ancestors | Design choice |
| `apple,always-on` | ADT `critical` flag, plus overrides copied from Asahi t8132 (AIC, ANS, DISP_SYS/FE, UART_P, SPI_P), plus AIC_GFX and CS (conservative). `DISP*_CPU` is disabled ("locked" on M4) | Likely / Hypothesis |
| Node power domains | I2C, UART, DARTs: ADT `clock-gates` ids → PMGR device → real ancestor. AIC, GPIO and NUB_GPIO: by PMGR name. WDT: none (as in Asahi t8132) | Likely |
| OPP tables | ADT `acc-clusters` → `voltage-states22/23/5` (+`-sram`): core mV and frequency. The decoded semantics are asserted per entry (period × f = 65535e6) and match the measured 4.512 GHz single-thread P-state | Confirmed (data); `opp-level` = index+1 is a Hypothesis |
| cpufreq controllers 0x2_1{0,1,2}e20000 | ADT pmgr reg entries (size 0x12e8); same address pattern as M1–M3 | Likely |
| `dynamic-power-coefficient`, `capacity-dmips-mhz` | macOS IOReport energy and QoS runs (plan §3f) | Hypothesis |
| `clock-latency-ns` | not measured | Placeholder |
| DART nodes | ADT `dart,t8110`; `instance` records (FourCC type, index, name) select which `reg` entries are DART register sets, so DAPF/GAPF/SMMU windows are skipped | Likely |
| SART | ADT `sart,coastguard`, `sart-version 4` | Confirmed (data) |
| NVMe regs and IRQ | ADT `ans` reg[9]/reg[3]/reg[0], `nvme-interrupt-idx = 4` → IRQ 2338; m1n1 `53f8ee9b` | Confirmed (data); 0x40000 window Likely |
| ANS mailbox | ANS reg[0] + 0x8000 (m1n1 `asc.c`); IRQs 1347–1350 sorted from the ADT | Likely |
| SMC node | ADT `smc` reg[0] (ASC) at `0x28c600000`; `sram` = ASC + 0x1a00000, 1 MiB, the pattern of the t8103/t8122/t6031 DTs; transport = Linux `macsmc` ABI (REA of AppleSMC, `../smc/README.md`) | Likely (sram window) / Confirmed (ABI) |
| SMC mailbox | ASC + 0x8000; IRQs 899–902 sorted from the ADT | Likely |
| Memory node | placeholder; m1n1 fills it in | Placeholder |

## Open questions to resolve on hardware

See plan §6 (Q1–Q9): SMP, MIDR, the AIC VM-timer lock, AIC dies, the NVMe
window, SARTv4 entry count, the DVFS mapping, locked PMGR domains, and the
CTRR size.

## Upstream status: not contributable to Asahi

An AI agent produced this draft. Asahi Linux's generative-AI policy
(asahilinux.org/llm-policy, 2026-09-08) broadly forbids generative AI for
material contributions, so **this must not be submitted to Asahi projects**
(decision D-007). An unofficial community T6050 DTS (`betizzel/omarchy-m5`)
exists. Neither it nor this draft has been reviewed by Asahi.
