# H1 register census: BLOCKED for hv001

2026-10-14 · M1. One read-only session on the installed boot021 proxy.
Readiness `8267222`, M5 handoff `4814b6f`. Private tooling: not for upstream.
**hv001 Session 2: NOT RUN.**

## Execution

* Run once at 22:24:14 UTC with
  `census.py --device auto --confirm CENSUS-J716C-READ-ONLY`: exit **2**
  (verdict BLOCKED), under one second.
* The chip, boot021-marker and no-secondaries gates passed; the table prints
  only after they do.
* 15 guarded `mrs` reads; no register writes, no chainload, no hypervisor
  start. m1n1 console text was not echoed. No retry.
* The human powered off and confirms the return to Macintosh HD. Fresh
  policy/default checks: NOT CHECKED.

## Literal table (classes only)

| Register | Access | Class |
|---|---|---|
| ID_AA64MMFR0_EL1 | readable | ECV=1 |
| VM_TMR_FIQ_ENA_EL2 | readable | ENA_V=1 ENA_P=1 |
| HACR_EL2 | readable | zero |
| AMX_CTL_EL2 | readable | zero |
| APVMKEYLO_EL2 | readable | zero |
| APVMKEYHI_EL2 | readable | zero |
| APSTS_EL12 | readable | zero |
| ACTLR_EL2 | readable | nonzero |
| ACTLR_EL12 | readable | nonzero |
| IMP_APL_ACTLR_EL12 | readable | nonzero (informational) |
| SPRR_CONFIG_EL1 | readable | zero |
| GXF_CONFIG_EL1 | readable | zero |
| CNTHCTL_EL2 | readable | zero |
| CNTV_CTL_EL02 | readable | ctl=7 |
| CNTP_CTL_EL02 | readable | ctl=7 |

`VERDICT: BLOCKED: VM_TMR_FIQ_ENA_EL2 not readable as disabled (hv001 refuses)`

## Interpretation

* **Confirmed, this boot state:** all 15 registers read at EL2 without a trap.
  That includes every register `hv_start()` reads without a guard, so those
  reads are not the hazard the README feared. ECV is present, so
  `hv_init()` takes its ECV timer branch.
* **Confirmed:** both guest-timer FIQ enable bits are already set. Attempt 5
  showed that writing this register traps as undefined at EL2, so the
  hypervisor cannot clear them. hv001 correctly refuses to start.
* **Confirmed:** both guest timers read `ctl=7`: ENABLE=1, IMASK=1,
  ISTATUS=1. They are expired but masked at the source. Their FIQ is suppressed
  only by IMASK.
* **Consequence (Likely):** with the enable bits stuck on, a guest timer that
  fires with IMASK clear raises a physical FIQ. With HCR.FMO=1 that FIQ traps
  to EL2 again before the guest can run, unless the source is masked. Polling
  alone cannot work.

## Revision direction for M5 (Hypothesis, untested)

Mask at the architectural source, as the project's Linux t6050 AIC profile
already does at EL2:

* When the hypervisor sees ISTATUS=1 with IMASK=0 on `CNTV_CTL_EL02` or
  `CNTP_CTL_EL02`, set the hardware IMASK and inject HCR_VF.
* Present the guest a shadowed `CTL` through the timer traps. ECV=1, and
  `hv_init()`'s ECV branch traps guest virtual-timer accesses (EL1TVT) and
  leaves EL1PTEN clear. Confirm this in the exact build: `CNTHCTL_EL2` reads
  zero before `hv_init()`.
* Restore the hardware IMASK from the guest's view when the guest rewrites
  CTL, CVAL or TVAL.
* Keep the physical guest timer masked: Linux at EL1 uses the virtual timer.
* Initialize both EL02 timers to masked before guest entry, because they are
  left expired at handoff.

Re-run the census after the revision only if the gate changes. These register
classes are stable facts for this boot state.
