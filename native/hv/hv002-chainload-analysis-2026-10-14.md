# hv002 session 2: why the chainload went silent, and what to change

2026-10-14, M5 agent, offline (updated after the hv003 build). Source: the M1 report
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
| 0 | **Misaligned entry literal in our copy stub** (found during the hv003 build, after this note's first version). The stub had 36 bytes of code and then its 64-bit entry literal at +36. The stub address was `0x10010db8240` (8-aligned), so the literal sat at 4 mod 8. The stub runs after `mmu_shutdown`, with data accesses treated as Device-nGnRnE, where an unaligned 8-byte load faults. | **Likely** (arithmetic and an instruction emulator confirm it; not hardware-confirmed). Upstream's assembler pads its literal pool to 8 bytes; our hand-built stub did not. Fits a silent hang right after `Vectoring to next stage`. | Padded literal (hv003 stub), clang-verified; run rung 2 of the ladder. |
| 1 | The Python-rebuilt/pushed ADT, or the six-blob relocation, differs from what m1n1 accepts on this iBoot. | Only difference from the field-proven stage-1→2 path; first ADT push on t6050. | Chainload with in-tree semantics (SEPFW only, in-place ADT patch). |
| 2 | The staged region overlaps something m1n1 needs (ADT, boot_args, framebuffer, heap staging). | In-place overwrite at `u.base`; sizes are unknown here. | Read-only layout check of the planned region before the chainload. |
| 3 | Early re-init on t6050 depends on state the first m1n1 changed (MCC, AIC, PMGR, display). | A second m1n1 start after `display_shutdown`/`usb_iodev_shutdown` is untested on this SoC. | On-screen breadcrumbs through `m1n1_main`. |
| 4 | Something specific to the hv002 build. | Nothing it changes runs in the failing window; layout shifts only. | Chainload stock boot021 `m1n1.bin` as a control. |

Hypotheses 1 and 2 are fixable on the host side, so they come first.

## What hv003 does (implemented, offline-tested; hardware NOT RUN)

1. **Aligned stub:** literal pool padded to 8 bytes; assembled with clang and run
   through an instruction emulator that faults on unaligned literal loads.
2. **Layout gate** (read-only, before any write): from the live target compute the
   planned region and refuse if it overlaps the ADT, the framebuffer or (unsafely)
   the proxy staging block, if a second chainload is detected, or if it leaves
   RAM; print a sanitized layout table. A live `boot_args` inside the destination
   is a NOTE (the new m1n1 uses its staged copy).
3. **In-tree-equivalent chainload:** SEPFW only, in-place patch of that one ADT
   property (16 bytes) as the last write, no Python ADT rebuild, no RVBAR write.
   The `boot_args` copy changes only `top_of_kernel_data`, which is never below
   the live value (the in-tree flow can lower it under live iBoot structures,
   and the new heap starts there). A failed patch is reverted, the whole ADT is
   verified, and the launcher says whether it was restored.
4. **Breadcrumbs:** the host paints stage marks (slot 2 just before the ADT
   patch), the copy stub paints an entry mark in slot 3 before its copy loop and
   then clears the strip and paints a solid bar (slots 0–4) the instant before
   it jumps, and the private m1n1 build paints one block per early init step
   (`c0`…`c15`, mapping the framebuffer once after `mmu_init`; `c15` is also
   stored into the console shadow framebuffer so the first console write does
   not erase it).
5. **Ladder of sessions:** `--layout-only` (no memory writes), `--chainload-only`
   (chainload and verify, no hypervisor), `--chainload-only --control stock`
   (installed boot021 binary as a control, digest-checked), then the full run.
   After the reconnect the launcher also requires the new instance's `boot_args`
   pointer to be the copy it staged, which proves a new instance is running.
6. **Hygiene found in review:** the launcher no longer echoes the target's
   console (it carried the device serial); USB errors carry no device paths; a
   reload that does not reopen the port falls through to the descriptor-checked
   reconnect instead of ending the session.

## What this does *not* say

* It does not say hv002's HV changes work: they have still not executed.
* It does not say chainloading works on M4/M5; community M5 reports only show
  m1n1 starts there. Whether our procedure (the misaligned literal being the
  leading candidate), the unmoved blobs or t6050 itself is at fault is open.
* The in-tree flow overwrites five memory-map blobs that the Python flow moved
  (SEPPatches, uStuff, preoslog, RTBuddySeg, TrustCache). The layout table lists
  them as NOTES; whether any is live on t6050 is Unknown until a session shows
  the effect.
* Boot034 (attempt 15) does not depend on any of this.
