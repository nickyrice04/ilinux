# Stage B attempt 7 — later initcalls; deferred_probe_initcall boundary; return pending

2026-10-14 America/New_York. One human-started, phone-recorded RAM attempt.
Readiness `9bda4dd`; reviewed M5 handoff `995efd7`. Reused unchanged boot025.
Installed boot021 m1n1 and clean client pin unchanged. No reconnect, retry,
reinstall or boot/volume/security/default changes.

## Provenance and controller

* Archive SHA-256: `908d0a9aa88c83469738f146f464bcb3815e812e56ef1615f0168cb7ce595f86`.
* Image SHA-256: `8849de7c2b8e529ad5895707ed26f535993cc8ff85447c450b2c13240185a0ea`.
* SHA256SUMS: `aae4c401ef45457cbd03687b4325ffd0bcbe1c15fcac9bf48a1167046c3c4d5d`.
* Client: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Archive/13-file intake, reviewed hashes, offline launcher and 69 cases PASS.
* Only new fixed argument: `initcall_blacklist=clk_debug_init`; exact prepared
  argument check retained. No expanded blacklist.
* Fresh receipt `build/native-intake/receipts/boot025-attempt7.json`; ignored
  `build/native-intake/results/boot025-stage-b-attempt7.json` retains full exact
  invocation/arguments, source/procedure/payload hashes and fixed checkpoints.
* Post-attempt-6 original Full/lab Permissive prerequisite PASS per M5 review.

* Start UTC `2026-10-14T04:53:40.692574+00:00`; end `2026-10-14T04:53:51.122617+00:00`.
* Exit **0**, elapsed **10.433 s**.
* Handoff `2026-10-14T04:53:50.882694+00:00`; kboot request/reply succeeded.
* Screen deadline `2026-10-14T04:55:50.882694+00:00` (12:55:51 a.m. Eastern).
* Primary USB identity, t6050/boot021 marker, no started secondaries,
  board/framebuffer, upload and final prepared-DT gates PASS.
* Both DAPF checks PASS: reviewed live layout/code/table and bounded 96-byte
  correction/readback. Other entries retained.
* `Early framebuffer PASS: kernel RAM descriptor checked and populated.`
  Bounded 16-byte kernel data descriptor/readback PASS.
* Reviewed launcher `main(argv)` called exactly once. Fixed safe checkpoints
  only; no raw memory/ADT/register output or serial-bearing USB paths retained.

## Screen evidence — later native initialization observed

Fresh human photo `IMG_2657.jpeg` shows late Linux initcalls and a Tux logo.
The first visible line is at 1.239536 s; this is not the first chronological
boot line. Final readable lines are:

```text
[1.370317] initcall boot_wait_for_devices+0x0/0x30 returned 0 after 0 usecs
[1.370849] calling sync_state_resume_initcall+0x0/0x20 @ 1
[1.371330] initcall sync_state_resume_initcall+0x0/0x20 returned 0 after 1 usecs
[1.371769] calling deferred_probe_initcall+0x0/0xb8 @ 1
```

No return from `deferred_probe_initcall` or explicit panic/Oops is visible.
Later initialization beyond the previous `clk_debug_init` boundary is observed;
the exact `initcall clk_debug_init blacklisted` text is **NOT OBSERVED** in the
supplied still. The controller verified the fixed blacklist argument in the
prepared DT. Some text is duplicated/overprinted, so missing lines should not
be reconstructed or treated as direct evidence of execution.

| Milestone | Result |
|---|---|
| Native Linux / later initcalls | **OBSERVED** |
| Exact blacklist message | **NOT OBSERVED** in supplied still |
| Last completed visible initializer | `sync_state_resume_initcall` returned 0 |
| Last visible call | `deferred_probe_initcall+0x0/0xb8 @ 1` at 1.371769 s |
| Explicit panic/Oops | **NOT OBSERVED** |
| Highest rectangle count / exact AIC profile/Initialized lines | **NOT OBSERVED** |
| Timer/progress | Advancing printk timestamps **OBSERVED**; `arch_timer` line **NOT OBSERVED** |
| Diagnostic PID 1 / online_cpus=1 / 60-second liveness | **NOT OBSERVED** |
| Macintosh HD return | **PENDING HUMAN CONFIRMATION** |
| Fresh security/default checks | **NOT CHECKED — M5 next** |

The earlier reattached `IMG_2655.jpeg` is from attempt 6 and was excluded from
attempt-7 evidence. Fresh photo reviewed; full photo/video not copied into the
workspace or committed. Video was confirmed before launch but not reviewed.
Initcall `@ 1` does not establish diagnostic userspace, and the last printed
call does not prove the blocking instruction or hardware cause.

At the 120-second screen deadline, stop and Macintosh HD return were instructed.
Return and whether the final line stayed unchanged are awaiting human confirmation.
No reconnect, retry, expanded blacklist, reinstall or boot-setting changes.

## Next M5 work

After return, perform read-only original macOS protection checks. Analyze the
exact boot025 deferred-probe initialization path and shared dependencies offline;
do not chain additional speculative skips. Preserve the passing guards and
installed boot021 m1n1. Native diagnostic userspace/liveness remains unobserved.
Attempt 7 is consumed; no new physical session authorized by this report.
