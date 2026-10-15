# Attempt 15 review: the SMC I2C domains, and boot035

2026-10-15, M5 agent. Inputs: the M1 report
`native/boot/stage-b-2026-10-15-attempt15-result.md` (`8b55851`), the shipped
boot034 Stage-B DT, the sanitized ADT export (`hardware/adt/adt-sanitized.json`)
and the pinned Asahi tree. Offline only; **native boot035 / attempt 16 NOT RUN.**

## What attempt 15 established

| Observation | Label |
|---|---|
| With genpd `sync_state` honoring `pd_ignore_unused`, attempt 14's reset at kernel ≈ 8.77 s did not happen; Linux ran to ≥ 27.6 s with PID 1 and heartbeats 000–004 | Confirmed (one changed variable) |
| So Linux powering PMGR domains off is a real reset trigger class | Confirmed |
| The ladder walked genpd's list newest-first: six `smc_i2cm?` releases (19.42–21.98 s), then ten ATC USB domains, then `atc?_common_dp_3` (27.61 s) | Observed |
| Silent reset at ≈ 27.7–27.85 s, no panic or watchdog text | Observed |
| The M1 host kernel-panicked (Apple USB CDC driver) at the handoff; its own reset fell in the same seconds | Observed; a confounder |

## New evidence from this review

**1. Asahi never exposes the SMC's power domains (Confirmed, source).**

| Pinned Asahi PMGR DT | `smc_*` domains | always-on / total |
|---|---|---|
| t8103 (M1) | 0 | 31 / 140 |
| t600x (M1 Pro/Max) | 0 | 91 / 228 |
| t602x (M2 Pro/Max) | 0 | 107 / 245 |
| t8112 (M2) | 0 | 34 / 139 |
| t6030 (M3 Pro/Max) | 0 | 42 / 160 |
| t8122 (M3) | 0 | 33 / 144 |
| **our t6050 draft** | **7 (`smc_i2cm0`–`6`)** | 34 / 188 |

Our draft is generated from the ADT and keeps every device with a power-state
register. Asahi's curated tables drop the SMC's. Other families unique to our
draft (`venc*`, `msr*`, `prores`, `aphy*`, `auss`) are newer media and PHY
blocks, not coprocessor-owned ones.

**2. In the real t6050 table the SMC island is coprocessor-owned (Confirmed,
ADT).** `SMC_FABRIC` (under the NUB fabric) parents `SMC_CPU`, `SMC_AON`,
`SMC_GPIO`, `SMC_UART0/1`, `SMC_FPWM0–3`, `SMC_PTD` and `SMC_I2CM0–6`. All
except the seven I2C masters are virtual (no register the AP can write). The
seven have registers, no critical flag and **no consumer anywhere in the ADT**,
so the generator emitted them and Linux classed them as unclaimed. They are the
SMC's own I2C masters, which on these Macs typically reach the PMU, charger,
battery and Type-C controllers (Likely; not traced on t6050).

**3. The latency matches (Likely).** Attempt 14: bulk power-off at ≈ 3.15 s,
reset at 8.77 s, a lag of 5.55–5.69 s. Attempt 15: the **sixth and last**
`smc_i2cm` release at 21.98 s, reset at 27.7–27.85 s, a lag of 5.70–5.88 s.
The first SMC release at 19.42 s did not reset the machine by 25 s, so if the
mechanism holds, one specific bus matters, not all seven (Hypothesis).

**4. The other candidates fit worse.** Step 17 (`atc?_common_dp_3`) preceded the
black frame by ≤ 0.24 s, but in attempt 14 every ATC domain was off for 5.6 s
without a reset. The M1's own post-panic reset has no known path to reset a Mac
running Linux. Neither can be excluded from this run alone.

**Conclusion (Likely, not hardware-confirmed):** Linux powering off an SMC-owned
I2C master makes the SMC reset the SoC about 5.6 s later. That explains both
attempts with one mechanism and one lag, and it is exactly the class of domain
Asahi keeps out of its device trees.

## boot035: one variable

`ilinux-j716c-boot035` = boot034 with the seven `smc_i2cm` power-controller
nodes **removed** from the Stage-B DT (Asahi's convention; nothing referenced
them). Image, initramfs, m1n1, kernel config, fixed arguments and the reviewed
controller are byte-identical. The boot034 kernel's release ladder therefore
walks the remaining 145 unclaimed, not-always-on domains (those iBoot left on)
from ≈ 19 s, one per ≈ 0.51 s, until ≈ 94 s, then keeps running.

| Attempt 16 shows | Meaning |
|---|---|
| `ladder complete` and heartbeats to 180 s | The SMC domains were the trigger (strong support). Linux can power off every other unclaimed domain: **the first stable, power-managed native baseline**. |
| Reset ≈ 5.6 s after a ladder release | A second domain with the same mechanism. Report that line and ±2 steps; M5 removes or pins it. |
| Reset with no ladder release in the preceding ≈ 6 s | Not a domain release. Report the last lines and the time. |
| Screen freezes or goes black, but no restart to Macintosh HD within about 60 s | A display-domain release (the framebuffer node claims no domain; see below), not a reset. |

## Cheap confirmation without booting Linux (optional, independent)

The PMGR probe (`tools/m1n1-client/pmgr-probe-instructions.md`) can test the
mechanism directly. Stage 1 (read-only) shows which `SMC_I2CMn` iBoot left on.
Stage 2 then runs `cycle SMC_I2CMn --settle 10` on one of them. If the
hypothesis holds, the run ends with `LINK LOST` about 5.6 s after that power-off
for exactly one of them. Each such run costs a restart.

## Noted, deliberately not changed in boot035

* **Display domains.** Asahi's simple-framebuffer nodes claim the display
  coprocessor's domain (`ps_disp0_cpu0` on M1 Pro/Max laptops, `ps_disp_fe` on
  M3 Pro/Max). Our framebuffer claims none. `disp_sys`/`disp_fe` are
  always-on, but `disp_cpu` and `disp_adma` are not and will be released by the
  ladder. In attempt 14 they were powered off with everything else and the
  screen kept updating for 5.6 s, so this is likely harmless. A future DT should
  claim `ps_disp_cpu` from the framebuffer node as Asahi does.
* **M1 host panic.** Apple's CDC driver dereferenced NULL during a tty call at
  the handoff, about six minutes after a sleep/wake. For attempt 16, restart the
  M1 fresh, keep it on power under `caffeinate -i`, and do not let it sleep. A
  launcher change (clear `HUPCL` before the kboot request, then no tty calls
  until the device is gone) is proposed, but it changes a reviewed controller
  digest, so it waits for its own handoff.

## The M4/M5 platform hurdles, against our path

Sources and detail: `research/asahi/asahi-status-m5-2026-10.md` (sections 3 and 4).

| Hurdle (Asahi, M4 and later) | Does it block our native path? | Status on this M5 |
|---|---|---|
| **SPTM in GL2** for Mach-O boot objects; required by XNU, which broke the macOS-tracing hypervisor | No. A **raw** boot object lands in EL2 with GL2 off. That is fine for Linux and costs only macOS tracing, which hv003 does not do (it runs Linux as the guest). | Confirmed by observation: every native attempt since 9 prints `mode=EL2`. |
| **WFI loses core state** (mBoot sets and locks the chicken bits) | Not for bring-up; yes for efficiency. | Worked around: `idle=nop arm64.nowfxt` in the fixed arguments (m1n1 adds the same on M4+, commits 3a69c73f59 and 9095a5ee70, both in our pin). Cost: the CPU never idles, so power and heat stay high. Deep idle later needs a state-saving (non-retentive) idle path. |
| **Locked IMPDEF sysregs, RVBAR locked** | Yes for SMP and deep idle. | Open. We run one CPU (`maxcpus=1`). No public T6050 SMP fix (Asahi PR #610). |
| **No EL3, so no PSCI** | Only for upstream-style SMP/cpuidle. | Asahi RFC "PSCI via EFI" exists; not needed for a one-CPU bring-up. |
| **Secondary watchdog** resets M4 after ≈ 120 s | Could end a long run. | m1n1 disarms it when `wdt-version` is 2 or 3 (commit 0e88df7bc9, in our pin). This M5 reports **`wdt-version = 3`**, so it is disarmed (Likely). Attempt 16's 180 s window tests it. |
| **NVMe firmware ABI** (macOS 15+) | Only for storage. | Our patches 0004–0005 cover the M4 NVMMU split; not in the Stage-B payload. |
| **G17 GPU, new DCP ABI** | For acceleration, not for a first desktop. | No driver: Omarchy starts on `simpledrm` with software rendering. |
| **Apple N1 Wi-Fi/Bluetooth** | For wireless. | No Linux driver: the control channel will be USB networking over the M1 cable. |

So none of these blocks a **first visual Omarchy boot** (one CPU, busy idle,
software rendering, USB networking). They do block **macOS-like performance
and efficiency** (SMP, deep idle, GPU), which stay research tracks with REA
behind the stable baseline. None explains attempt 14's or 15's resets: WFI is
never executed (`idle=nop`), the watchdogs are disarmed, and the resets follow
the SMC domain releases.

## Where this leads (see `roadmap.md`)

A stable native baseline (attempt 16) is the gate for everything toward
Omarchy: a control channel into Linux (USB networking over the same cable), a
RAM root with a real Arch userspace, then Hyprland on `simpledrm` with software
rendering. That is a visual Omarchy boot on one CPU, before SMP, storage, input
and the GPU.
