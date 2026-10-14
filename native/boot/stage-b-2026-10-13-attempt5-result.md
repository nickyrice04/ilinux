# Stage B attempt 5 — early Linux observed; AIC initialization panic; return confirmed

2026-10-13 America/New_York (timestamps below UTC on 2026-10-14).

## Scope and provenance

One human-started, phone-recorded RAM attempt after M1 readiness `e362a7f`,
using reviewed M5 handoff `1d1be38`. No automatic retry, reconnect, reinstall
or boot/volume/security/default changes. Prior post-attempt-4 original Full /
lab Permissive policy prerequisite was reviewed by M5 as PASS.

* Package: `native-j716c-boot024`; archive SHA-256
  `f7cb69153adc832cae3a66fd6159e7fd41fccc2a113d3550962a7f959edd9636`.
* Image SHA-256:
  `6b683a2f52e769d1a23474b6807d009da8ad2e19d2168e62caba6cbbae240f7d`.
* SHA256SUMS digest:
  `c9b132f08ea093667c9abb3798315e77cc6347d28897bdfa87654d14e20a2219`.
* Clean client pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
  Installed boot021 m1n1 unchanged; packaged live marker PASS.
* M1 offline archive-before-extraction, 13-file intake, launcher and all 65
  documented test cases PASS. Actual comparison: only Image differs from boot022.
* Source/procedure hashes and full exact invocation retained in ignored
  `build/native-intake/results/boot024-stage-b-attempt5.json`; intake receipt
  `build/native-intake/receipts/boot024.json`. Prior records preserved.

## Controller observations

* Start: `2026-10-14T03:54:01.823993+00:00`. End: `2026-10-14T03:54:12.246249+00:00`.
* Exit **0**, elapsed **10.421 seconds**.
* Handoff checkpoint: `2026-10-14T03:54:12.010468+00:00`; request/reply succeeded.
* Screen deadline: `2026-10-14T03:56:12.010468+00:00` (11:56:12 p.m. Eastern).
* Primary CDC descriptor identity, target t6050/boot021 marker, no started
  secondaries, J716c/boot framebuffer and final prepared-DT gates PASS.
* Both DAPF checkpoints PASS: exact live layout/code/table matched; bounded
  96-byte RAM correction applied and readback verified, other entries retained.
* `Early framebuffer PASS: kernel RAM descriptor checked and populated.`
  Bounded 16-byte kernel RAM data descriptor checked/readback verified.
* Upload, final preflight and kboot reply PASS. Controller success alone does
  not prove kernel execution, scanout writes or userspace success.
* Sanitized wrapper invoked the unchanged reviewed `main(argv)` exactly once.
  Only fixed checkpoints and safe metadata retained; no raw memory/ADT/USB paths.

## Screen evidence — early Linux OBSERVED; userspace NOT OBSERVED

Human confirmed phone video recording before launch and supplied `IMG_2653.jpeg`
after handoff. The still was visually reviewed; it and the full video were not
copied into the workspace or committed. Video contents have not been reviewed.

**Observed:** readable native Linux initialization and a kernel panic on the
built-in display. Screen identifies `7.1.9-g863199d8b4a3-dirty #3 PREEMPT` and
CPU 0 / PID 0 / `swapper/0`. Safe diagnostic text:

```text
Root IRQ handler: aic_handle_irq
Root FIQ handler: aic_handle_fiq
irq_apple_aic: Using Fast IPIs
Internal error: Oops - Undefined instruction
pc : aic_init_cpu+0x9c/0x150
lr : cpuhp_invoke_callback+0x118/0x210
Kernel panic - not syncing: Attempted to kill the idle task!
```

Sanitized symbolic call trace (relative function offsets only):

```text
aic_init_cpu+0x9c/0x150
cpuhp_issue_call+0x50/0x1d4
__cpuhp_setup_state_cpuslocked+0x140/0x2f8
__cpuhp_setup_state+0x34/0x50
aic_of_ic_init+0x4f0/0x5d8
of_irq_init+0x21c/0x3c8
irqchip_init+0x18/0x40
init_IRQ+0xa4/0xbc
start_kernel+0x5a8/0x788
__primary_switched+0x88/0x90
```

This establishes a failure in early interrupt-controller CPU initialization.
The precise instruction/register compatibility issue still requires offline
matching-build analysis; the nearby Fast IPI message alone is not a cause.
Native early text visibility is observed, not full display/GPU enablement.

| Milestone | Result |
|---|---|
| Native Linux early initialization/readable screen | **OBSERVED** |
| Highest white-rectangle count | **NOT OBSERVED / not reported**; still already has kernel text |
| First chronological kernel line | **NOT DETERMINED**; circular text has wrapped |
| Last failure | **Undefined-instruction Oops; idle-task kernel panic** |
| Last `calling`/`returned` initcall pair | **NOT OBSERVED**; symbolic IRQ initialization trace available |
| Diagnostic `PID 1 reached` | **NOT OBSERVED** |
| Diagnostic `online_cpus=1` | **NOT OBSERVED**; early `nr_cpu_ids=1` is visible but is a different milestone |
| 60-second userspace liveness | **NOT OBSERVED** |
| Macintosh HD desktop return | **PASS — human confirmed** |
| Fresh post-return security/default checks | **NOT CHECKED — M5 next** |

Explicit panic prompted stop/return guidance at the screen observation limit.
User confirms successful return to the usual Macintosh HD desktop. No retries,
reconnect, reinstall or settings changes. Raw addresses/register values, code
dump and personal/machine identifiers are omitted; full media stays local.

## M5 next action — offline diagnosis and read-only return checks

Verify original Full / lab Permissive and original macOS return protections
read-only on M5. Analyze `aic_init_cpu+0x9c` against the exact boot024 linked
kernel (`Image` hash above, job-024 symbols) and its AIC feature/register path.
Keep the passing DAPF, version, CPU, storage and framebuffer gates and preserve
the installed boot021 m1n1. This evidence establishes early Linux execution,
not a completed native boot or Omarchy usability. Attempt 5 is consumed;
no additional live test, boot-setting change or automatic retry is authorized.
