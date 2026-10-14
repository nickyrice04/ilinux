# boot034: genpd sync_state, the attempt-14 reset hypothesis

2026-10-14, M5 agent. **Boot034 built and tested offline; native attempt 15
NOT RUN.** Original Linux change for the independent project, in
`drivers/pmdomain/core.c`. It is not an upstream submission.

## Question

Attempt 14 reached diagnostic PID 1, then the SoC reset silently at kernel
≈ 8.77 s, ≈ 5.6 s after `of_platform_sync_state_init` (3.15 s). Attempts 11–13
never got past the GPIO controllers and did not reset in 120 s. **Does Linux
powering off PMGR domains at `sync_state` trigger the reset?**

## Evidence (all from the pinned source and the shipped artifacts)

| Fact | Where | Label |
|---|---|---|
| `of_genpd_sync_state()` and `genpd_provider_sync_state()` clear `stay_on` and call `genpd_power_off()`; neither tests `pd_ignore_unused`. | `drivers/pmdomain/core.c` (HEAD d55aa898, same bytes as the boot033 build tree) | Confirmed |
| `pd_ignore_unused` is only tested in `genpd_power_off_unused()`, the late sweep. Attempt 14 printed that sweep's message, `PM: genpd: Not disabling unused power domains`. | `core.c:1409` | Confirmed |
| `of_platform_sync_state_init()` (`late_initcall_sync`) calls `device_links_supplier_sync_state_resume()`. Suppliers whose consumers are all bound, **including suppliers with none**, get `sync_state` there. The step took **5017 µs** in attempt 14, the only measurable late-init work. | `drivers/of/platform.c`, `drivers/base/core.c` | Confirmed (source); duration observed |
| In the Stage-B DT, **152 of 188** PMGR domains are neither always-on nor claimed by an enabled device. Only `gpio` and `uart0` are claimed (plus `ans`, always-on). | `build/native-boot034/domain-audit.json` (generated from the Stage-B DTB) | Confirmed |
| 27 of those 152 carry the ADT `notify_pmp` flag. Linux's `pmgr-pwrstate` driver does not handle it. | sanitized ADT `devices`, flag bit 1 | Observed; effect Unknown |
| The ADT's `on` flag is clear for all 661 records, so it cannot tell which domains iBoot left on. | same | Observed |
| The DT generator's header says "First boots should use pd_ignore_unused", which this path ignores. | `t6050-pmgr.dtsi` | Confirmed |
| M1/M2 Asahi DTs follow the same `critical` → `always-on` rule, so Linux releasing unclaimed domains is normal there. What differs on t6050 is **unknown**. | `pmgr_adt2dt.py` | Confirmed (rule); cause Hypothesis |

## What boot034 changes

Only `Image` (+65,536 bytes); config, DT, initramfs and m1n1 are
byte-identical to boot033. Patch: `apply.py` (digest-gated).

1. **The fix:** both sync_state paths return before touching any domain when
   `pd_ignore_unused` is set, as the late sweep already does. The cmdline
   already carries the flag, so no launcher change is needed.
2. **Trace:** `_genpd_power_off()` logs `PM: ilinux-genpd: power off NAME`
   before the PMGR write, so the last line names the domain being cut.
3. **Release ladder** (armed only with `pd_ignore_unused`): 17 s after
   `late_initcall` (≈ 20 s kernel time), release the remaining boot-on,
   unclaimed domains one every **500 ms**, logging
   `ilinux-genpd: ladder N: release NAME` first. Bounded by the domain list
   (≤ 152 steps, ≈ 76 s), then `ladder complete: N domains released`.
   Domains held by an active device or a powered subdomain stay on, exactly as
   in `genpd_power_off()`.

## How to read the native result

| Observation | Meaning |
|---|---|
| Survives past kernel ≈ 20 s with the `sync_state keeps unused power domains on` line | Linux-initiated domain power-off at sync_state was the trigger. Strong support, since attempt 14 reset at 8.77 s. |
| Resets before ≈ 20 s with no `power off` line | Not a Linux domain power-off. Move to ANS/SART/mailbox side effects, then idle. |
| Resets during the ladder | The culprit is the release ≈ **5.6 s** (attempt 14's delay) before the black frame, ±2 steps. Use `printk.time` stamps and the heartbeat anchor (video − kernel offset). |
| Survives the whole ladder (≈ 96 s kernel) | Domain power-off alone is **not** the trigger, even all at once, one at a time. Hypothesis refuted. |

## Validation (offline)

* `test_genpd.py`: 5 PASS. It extracts the exact ladder from `apply.py` and
  runs it against stubbed genpd types under ASan/UBSan. Five deliberate
  mutations are caught: ignoring always-on, keeping `stay_on`, never
  rescheduling, arming without the fix, and ignoring power state. It also
  applies the patch to the real `core.c` and rejects a modified or
  already-patched file.
* VM job 036 reran those tests with GCC 16.1.1 against the exact boot033 file,
  built the Image in 36 s with identical `.config`, and checked the ELF/Image
  round trip. Disassembly shows both sync_state paths testing
  `pd_ignore_unused` first and returning.
* Exact packaged Image/initramfs in a one-CPU, 4 GiB, diskless, networkless
  VZ guest reaches PID 1 and 60 s liveness. The ladder arms and completes with
  0 domains (no PMGR in that guest), and no `power off` line appears.

## Limits

* The VM has no PMGR, so it validates code paths, not the native effect.
* If domains must be powered off to be useful (idle power), this is a
  diagnostic, not a final configuration.
* The ladder's culprit window is ±2 steps (±1 s) if the firmware's delay is
  not fixed.
* Not a parity or performance claim. No proprietary code was used; the
  analysis used the project's own source and the sanitized ADT.
