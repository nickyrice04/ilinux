# t6050 (M5 Max) minimal device tree: DRAFT

**Status:** generated from data. It is checked by compiling it with `dtc`
(see `validate.sh`). It has **never been booted** and can't be until m1n1
supports t6050. Any boot experiment needs the user's explicit authorization
and a separate deployment plan (`roadmap.md` Phase 3).

## What it is

`gen_t6050_dt.py` turns the sanitized macOS ADT capture
(`hardware/adt/adt-sanitized.json`) into:

* `out/t6050.dtsi`: CPUs (3 clusters, 18 cores, L2 caches), the AIC3
  interrupt controller with PMU affinities, the arch timer, the 24 MHz
  reference clock, the watchdog, three pinctrl/GPIO controllers (AP 221 pins,
  AOP 85, NUB 61), nine I2C controllers and UART0.
* `out/t6050-j716c.dts`: the board file for Mac17,6 (J716c), serial console
  enabled.

The scope mirrors the Asahi "minimal" bring-up DT for t8132 (base M4, added
2026-07-05). It's the smallest set needed for a serial-console kernel boot.
Addresses are translated through the `arm-io` `ranges`. IRQ numbers are the
ADT AIC numbers.

## Evidence and confidence per element

| Element | Source | Confidence |
|---|---|---|
| CPU count, clusters, cache sizes | ADT `/cpus`, `sysctl hw.perflevel*` | Confirmed |
| CPU `reg` (MPIDR) | ADT `reg` 0x000–0x005, 0x100–0x105, 0x200–0x205 | **Hypothesis**: Asahi's M4 DT puts P cores at `0x10100`, which suggests extra Aff2 bits in the real MPIDR |
| CPU `compatible` (`apple,sotra-m/-p`) | named after `CPUFAMILY_ARM_SOTRA`, following Asahi's `apple,donan-e/-p` for M4 | Placeholder; needs a DT binding |
| AIC3 core region 0x2_80400000 + 0x1cc000 | ADT `aic` reg via `arm-io` ranges | Likely |
| AIC3 event region at core + 0x40000 | ADT `aic-iack-offset = 0x40000`, matching the t8122/t8132 layout | Likely |
| AIC compatible fallback `apple,t8122-aic3` | ADT `aic,3`, `aic-rev = 11`, same core size as t8132 | Likely |
| WDT, UART, I2C, GPIO addresses and IRQs | ADT reg and `interrupts` | Likely (direct data) |
| Memory node | placeholder; macOS ADT `/memory` reg is empty, m1n1 fills it | Placeholder |

## Not included (TODO)

* **PMGR power domains** (`t6050-pmgr.dtsi`). These need decoding of the ADT
  `pmgr` `devices`/`ps-regs` tables, whose layout may differ from earlier
  SoCs. Without them, Linux relies on firmware-enabled state.
* cpufreq (`apple,cluster-cpufreq`) and the OPP/energy-model tables, which EAS
  needs (see `omarchy-qos`).
* DARTs, NVMe (ANS3), SART (CoastGuard), SMC, USB/ATC, DCP, GPU, ANE. Each
  needs driver work first (`reports/compatibility-matrix.md`).

## Open questions to resolve on hardware

1. Real MPIDR values and core part numbers (`MIDR_EL1`) for the M and P cores.
2. Whether AIC3 rev 11 needs driver changes, e.g. the `extint-baseaddress`
   0x10000 or stride 0x4a00 values compared with t8122.
3. Whether the samsung UART still runs at 24 MHz with the t8103 divisor scheme.
4. Whether exclave-owned blocks are reachable from a normal-world kernel at all.

## Upstream status: not contributable to Asahi

This draft was produced by an AI agent. Asahi Linux's generative-AI policy
(asahilinux.org/llm-policy, 2026-09-08) broadly forbids generative-AI tooling
for material contributions, so **this file must not be submitted to Asahi
projects** (decision D-007). It serves as a local reference for this project.

Context from the Asahi research report (`research/asahi/`):

* m1n1 gained initial T6050/T6051 support in PR #610 (2026-06-29). It adds
  the M-core type, but secondary cores never start, so SMP is blocked.
* Asahi's naming lists T6051 for "M5 Max". This machine's ADT reports
  `chip-id` 0x6050 and `platform-name` t6050, and we follow the hardware.
* An unofficial, unreviewed ADT-derived T6050 DTS exists in the community
  (`betizzel/omarchy-m5`). Neither it nor this draft is reviewed by Asahi.
