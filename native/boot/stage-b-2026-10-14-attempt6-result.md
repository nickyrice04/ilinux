# Stage B attempt 6 — late Linux init; last visible clk_debug_init; return confirmed

2026-10-14 America/New_York. Controller timestamps below are UTC.

## Provenance and scope

One human-started attempt after readiness `32f5bcf`, reviewed handoff `f8e98ee`.
Human confirmed Running proxy and phone video recording before launch. No
reconnect, retry, reinstall or boot/volume/security/default changes.

* Archive SHA-256: `908d0a9aa88c83469738f146f464bcb3815e812e56ef1615f0168cb7ce595f86`.
* Image SHA-256: `8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea`.
* SHA256SUMS digest: `aae4c401ef45457cbd03687b4325ffd0bcbe1c15fcac9bf48a1167046c3c4d5d`.
* Clean client pin: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Installed boot021 m1n1 remains unchanged; only packaged Image differs from boot024.
* M1 archive-before-extraction, 13-file intake, five reviewed controller
  hashes, offline launcher and all 65 documented cases PASS.
* Prior post-attempt-5 original Full/lab Permissive policy prerequisite PASS
  per M5-reviewed human JSON. No repeat policy query on M1.
* Fresh ignored receipt `build/native-intake/receipts/boot025.json` and
  `build/native-intake/results/boot025-stage-b-attempt6.json` retain exact
  invocation, command line, source/procedure/payload digests and timestamps.

## Controller observations

* Start `2026-10-14T04:27:29.761928+00:00`; end `2026-10-14T04:27:40.153385+00:00`.
* Exit **0**, elapsed **10.391 s**.
* Handoff checkpoint `2026-10-14T04:27:39.918074+00:00`; kboot request/reply succeeded.
* Screen deadline `2026-10-14T04:29:39.918074+00:00` (12:29:40 a.m. Eastern).
* Primary USB identity, t6050/packaged boot021 marker, no started secondaries,
  board/framebuffer, upload and final prepared-DT gates PASS.
* **DAPF layout PASS** and **DAPF RAM table corrected**: reviewed layout/code
  checked, bounded 96-byte correction applied/read back, other entries retained.
* **Early framebuffer PASS: kernel RAM descriptor checked and populated.**
  Checked 16-byte kernel RAM data descriptor; no instruction patch.
* Reviewed launcher `main(argv)` called once with fixed documented arguments;
  only fixed safe checkpoints retained, no target ADT/memory/register/USB paths.
* Controller success does not independently establish native Linux execution,
  AIC/timer delivery, userspace or screen milestones.

## Screen evidence and return

**Observed:** human-supplied `IMG_2655.jpeg` shows native Linux late initcall
output, advancing printk timestamps and a Tux logo. It was visually reviewed;
no photo/video copied into the workspace or committed. The human subsequently
confirmed the screen stayed at the final `calling clk_debug_init` line until
shutdown and confirmed return to the usual Macintosh HD desktop.

Safe transcription of the first visible line and final completed/called pair:

```text
[1.219475] initcall panic_force_cpu_late_init+0x0/0x4c returned 0 after 0 usecs
...
[1.359287] calling bert_init+0x0/0x30c @ 1
[1.359751] initcall bert_init+0x0/0x30c returned 0 after 0 usecs
[1.360189] calling clk_debug_init+0x0/0x120 @ 1
```

No return from `clk_debug_init` is visible. No panic or Oops is shown. A prior
`mempool_fault_inject_init` returned -19 at 1.311070 s, followed by further
successful initialization; this is not established as the cause of the stop.
Some duplicated/overprinted lines appear mid-screen; retain that observation
without inferring an additional execution or memory fault.

**Inferred from later execution:** the kernel progressed beyond the prior
attempt's early AIC panic point. The supplied still does not directly capture
the restricted-profile or final AIC Initialized line, so those exact checkpoints
remain NOT OBSERVED. Advancing timestamps are progress evidence, not a complete
IRQ/timer validation or a measured period of userspace liveness.

| Milestone | Result |
|---|---|
| Native Linux initialization | **OBSERVED — late initcalls** |
| Highest white-rectangle count | **NOT OBSERVED / not reported** |
| First chronological boot line | **NOT DETERMINED**; supplied still starts at 1.219475 s |
| Last completed visible initcall | `bert_init` returned 0 at 1.359751 s |
| Last visible call | `clk_debug_init+0x0/0x120 @ 1` at 1.360189 s; human reports unchanged until shutdown |
| Explicit panic/Oops | **NOT OBSERVED** |
| Exact t6050 AIC profile / Initialized lines | **NOT OBSERVED** in supplied still |
| Timer/progress | **OBSERVED** advancing printk timestamps; `arch_timer` line **NOT OBSERVED** |
| Diagnostic `PID 1 reached` | **NOT OBSERVED**; initcall `@ 1` is not diagnostic userspace |
| Diagnostic `online_cpus=1` | **NOT OBSERVED** |
| 60-second userspace liveness | **NOT OBSERVED** |
| Macintosh HD desktop return | **PASS — human confirmed** |
| Fresh security/default checks | **NOT CHECKED — M5 next** |

Stop was instructed at the 120-second post-handoff screen limit. No retry,
reconnect, reinstall or settings changes. One successful controller reply
remains distinct from completing native userspace boot.

## Next M5 work

Perform read-only original-macOS return/protection checks, then investigate the
exact boot025 `clk_debug_init` and clock debug registration paths offline.
The last printed initializer is a useful boundary, not proof of the precise
blocking instruction or hardware cause. Preserve the existing passing guards
and unchanged installed boot021 m1n1. The locally retained video may recover
AIC/timer lines; it has not been supplied or reviewed by M1. Attempt 6 is consumed:
no additional physical test or boot-setting change is authorized by this report.
