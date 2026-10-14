# hv002 session 2: why the chainload went silent, and what to change

2026-10-14, M5 agent, offline. Source: the M1 report
`hv002-session2-2026-10-14-result.md`, the pinned m1n1 (`57a9339`) and our
launcher. **No target action. hv002 behavior: NOT RUN beyond the chainload.**
Private tooling; not for upstream.

## What the test established

| Observation (M1) | Label |
|---|---|
| Package, target, register-preflight and ADT/blob steps passed; boot021 printed `Preparing to run next stage at 0x10010db8240` | Confirmed |
| No m1n1 USB device returned for ≈ 80 s; vUART log empty; no events log | Confirmed |
| Screen: black with the **restored Apple logo**, frozen until power-off; no macOS progress bar, so a hang, not a reset | Confirmed (human report) |
| hv002 never drew its own logo or console | Confirmed |

The restored logo is the first m1n1's last act (`P_VECTOR` sets
`restore_logo = true`). So the new m1n1 hung (or crashed) **before
`fb_init()`**, i.e. in `_start`/`_start_c`/`m1n1_main` up to `display_init()`.
That is a strict *prefix* of m1n1 that none of hv002's changes execute
(`hv_init`, `hv_start`, kboot, proxy ops all run later).

## What the source shows (this pass)

* **`debug_putc` is a no-op** in our build (it compiles to `ret` without
  `EARLY_UART_BASE`), so there is no early-UART poll to hang on.
* **Order of early init** (`startup.c`, `main.c`): `memset(bss)`, copy
  `boot_args`, derive `adt`, `/cpus` walk, `uart_init`, `dockchannel_uart_init`,
  `get_device_info`, `init_cpu` (generic only for `features_m4`),
  `exception_initialize`, then `firmware_init`, `heapblock_init`, `gxf_init`
  (if supported), `mcc_init`, `mmu_init`, `aic_init`, `smp_init`,
  `wdt_disable`, `pmgr_init`, `display_init`, then `fb_init`.
* **Our proxy chainload is not the path Asahi's installer uses.** In-tree
  `chainload_image()` (`src/chainload.c`, stage 1 → stage 2):
  * moves **only SEPFW**;
  * patches that one ADT property **in place** (`adt_setprop`);
  * leaves the other memory-map blobs where iBoot put them;
  * sets `restore_logo = false`.

  The Python flow we reused (`chainload.py`'s logic) instead:
  * stages **six** blobs here: SEPFW, SEPPatches, uStuff, preoslog,
    RTBuddySeg and TrustCache;
  * **rebuilds the whole ADT in Python and writes it back**
    (`Pushing ADT (755924 bytes)`).
* **That Python ADT push was a first on t6050.** Every earlier native
  launcher read the ADT only; kboot prepared the DT on the target. A rebuilt
  ADT that differs from iBoot's (size, alignment or property flags) would make
  the new m1n1's very first `adt_path_offset()` calls loop or fault before any
  console exists.
* **The framebuffer is not mapped by `mmu_init`.** `fb_init()` adds its own
  Normal-NC mapping. Any breadcrumb painted after `mmu_init` must map it first.

## Ranked hypotheses

| # | Hypothesis | Why | Cheap discriminator |
|---|---|---|---|
| 1 | The Python-rebuilt/pushed ADT, or the six-blob relocation, differs from what m1n1 accepts on this iBoot. | Only difference from the field-proven stage-1→2 path; first ADT push on t6050. | Chainload with in-tree semantics (SEPFW only, in-place ADT patch). |
| 2 | The staged region overlaps something m1n1 needs (ADT, boot_args, framebuffer, heap staging). | In-place overwrite at `u.base`; sizes are unknown here. | Read-only layout check of the planned region before the chainload. |
| 3 | Early re-init on t6050 depends on state the first m1n1 changed (MCC, AIC, PMGR, display). | A second m1n1 start after `display_shutdown`/`usb_iodev_shutdown` is untested on this SoC. | On-screen breadcrumbs through `m1n1_main`. |
| 4 | Something specific to the hv002 build. | Nothing it changes runs in the failing window; layout shifts only. | Chainload stock boot021 `m1n1.bin` as a control. |

Hypotheses 1 and 2 are fixable on the host side, so they come first.

## Plan (hv003, not yet implemented; independent of boot034)

1. **Layout gate** (read-only, before any write): from the live target compute
   the planned region and refuse if it overlaps the ADT, `boot_args`, the
   framebuffer or the proxy staging area, and print a sanitized layout table.
2. **In-tree-equivalent chainload:** SEPFW only (the Python six-blob mode
   becomes an explicit option) and an **in-place ADT patch** of the raw bytes,
   with no Python rebuild.
3. **Breadcrumbs:** the host paints stage marks before the handoff, the copy
   stub paints one at the instant before it jumps, and a private m1n1 build
   paints one per early init step (mapping the framebuffer once after
   `mmu_init`). The next silent hang then names its step on the screen.
4. **Control:** a `--chainload-only` mode (chainload, verify the marker, stop;
   no hypervisor) so a session can test stock boot021 vs hv003 without
   touching a guest.

## What this does *not* say

* It does not say hv002's HV changes work: they have still not executed.
* It does not say chainloading works on M4/M5; community M5 reports only show
  m1n1 starts there. Whether our procedure or t6050 is at fault is open.
* Boot034 (attempt 15) does not depend on any of this.
