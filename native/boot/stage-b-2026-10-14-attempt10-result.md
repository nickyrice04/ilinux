# Stage B attempt 10 — readable P:05 S:09 W:04; return confirmed

2026-10-14 America/New_York. One human-started, phone-recorded boot029 RAM
attempt. Reviewed M5 handoff `73c5e0d`; readiness/execution `8c96579`.
Installed boot021 m1n1 and clean client pin unchanged. No reconnect, retry,
reinstall or boot/security/volume/default changes.

## Provenance and controller

* Archive SHA-256: `ebed9be8b34c3684aaf01ef06b8fc108e0c548960c1f83a25ed411c5ef42ce16`.
* Image SHA-256: `53f5f2c5a7a2d9d0d2ae92961222090c97f0c266bb4066408acd577660e7cc32`.
* SHA256SUMS: `1eeef3e32ef45f6ed1266da2c3888066c49bc3b1a70e61dc6328bee52c0bdccc`.
* Clean client: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Archive digest/16,722,976-byte size verified before extraction; 13-file
  intake, reviewed controller digests, offline launcher and **90 cases PASS**.
* Only Image and package manifest differ from retained boot028. Fixed arguments
  unchanged, including `initcall_blacklist=clk_debug_init ilinux_probe_diag=1`.
* Ignored receipt `build/native-intake/receipts/boot029-attempt10.json`; ignored
  `build/native-intake/results/boot029-stage-b-attempt10.json`/`.md` retain
  exact invocation/args, source/procedure/payload/receipt hashes and checkpoints.
* Post-attempt-9 original Full/lab Permissive prerequisite already PASS per M5;
  those checks are not a fresh post-attempt-10 protection check.

* Start UTC: `2026-10-14T14:48:59.495128+00:00`.
* End UTC: `2026-10-14T14:49:09.991426+00:00`.
* Handoff UTC: `2026-10-14T14:49:09.756446+00:00`.
* Screen deadline UTC: `2026-10-14T14:51:09.756446+00:00`.
* Controller exit **0**, elapsed **10.496 s**. The 120-second deadline was
  communicated as **10:51:10 a.m. Eastern**, with return instructions.
* Primary USB identity, target t6050/packaged boot021 marker, no started
  secondaries, board/framebuffer, upload, prepared-DT/argument gates and kboot
  request/reply PASS. USB closed after this single invocation.
* **Hardware DT PASS:** J716c/t6050 CPU topology, AIC3 and timer routes verified.
* Both DAPF checkpoints PASS; bounded 96-byte RAM correction/readback PASS.
* Framebuffer kernel RAM descriptor/readback PASS (bounded 16-byte data).
* Reviewed launcher `main(argv)` invoked exactly once; fixed checkpoints only.
  No raw target ADT/memory/register output or serial-bearing paths retained.
  Controller completion is separate from Linux/userspace success.

## Reviewed video evidence

Human supplied `IMG_2660.mov`, duration **27.197 s**, oriented 720x1280.
Paused frames/lower-screen crops were reviewed at 6.8, 10, 11, 12, 13.6,
20.4 and 27.05 seconds. At 6.8 seconds the m1n1 screen is visible; at 10 seconds
Linux initcalls are progressing. The later samples show native Linux/Tux,
the clock-debug blacklist message and `deferred_probe_initcall` diagnostics.

The enlarged strip is directly readable as **`P:05 S:09 W:04`** in samples
at **11, 12, 13.6, 20.4 and 27.05 seconds**. No change is seen between those
samples. **H is NOT OBSERVED**: absent, overwritten or unreadable; this is
not `H:00`. The full transition sequence and intermediate S subphases were
not captured in readable samples. Three lanes are now visibly rendered on
native hardware, beyond the earlier mapping-only evidence.

Small timer/target/display text is blurred, and the enlarged strip overlaps
some bottom diagnostics. Exact tick count, timer/mask values, display state,
console_setup and pending/strip fields are **NOT CONFIRMED** from this clip.
No values are copied from attempt 9 or inferred from expected output. Printed
phase 13 is not directly observed; source-based implications of P:05 are
separate below. No readable watchdog heartbeat, scheduler summary, symbolic
stack, retry-compatible identifier or explicit panic/Oops appears in the
reviewed samples.

| Milestone | Result |
|---|---|
| Native Linux / clock blacklist / deferred-probe diagnostics | **OBSERVED** |
| Literal last strip | **P:05 S:09 W:04 OBSERVED** |
| H / full strip transition sequence / context-switch subphases | **NOT OBSERVED** |
| Exact small timer/target/display/console/pending/strip fields | **NOT CONFIRMED** |
| Printed phase 13 / watchdog / symbolic stack / retry compatible | **NOT OBSERVED** |
| Diagnostic PID 1 / userspace online_cpus=1 / 60-second liveness | **NOT OBSERVED** |
| Macintosh HD return | **PASS — human confirmed** |
| Fresh protection/default checks | **NOT CHECKED — M5 next** |

The clip and samples do not cover every frame or the whole 120-second window.
The human confirmed return with “back, update” but supplied no later message
or lane-change report. This does not establish that nothing changed after the
clip. Full media remains outside the workspace/Git; temporary local crops
were used only for review.

## Interpretation and next M5 work

Decode from the reviewed source, separately from the literal observations:

* **P=05** marks entry to the first `flush_work(&deferred_probe_work)` in
  `deferred_probe_initcall` (`kernel/experiments/deferred-probe/apply.py`).
* **S=09** marks `__schedule` exit
  (`kernel/experiments/schedule-boundary/README.md`).
* **W=04** marks the boundary immediately before `bus_probe_device(dev)` in
  `deferred_probe_work_func`; W=05 would mark its return (the same apply.py).

P=05 is later in the source path than phase 13 and the initial preemption
reenable. Progress beyond the earlier phase-12 boundary is therefore
**source-based inference**, not a direct transcription of phase-13 text.
The marks suggest investigating deferred-worker/device-probe progress during
the first flush. They do not identify a particular driver, exact blocked PC,
interrupt fault or deadlock. Rendering can be stale/overwritten and the H
lane is unavailable. No native hang fix or diagnostic userspace success claimed.

**Human confirms usual Macintosh HD desktop return. Attempt 10 is consumed.**
M5 next performs read-only return checks and offline analysis of the observed
worker/probe boundary and diagnostic visibility. Preserve installed boot021,
client pin, passing controller/hardware/DAPF/descriptor gates and the single
existing clock-debug skip. No retry or settings changes are authorized by this
report. Stable diagnostic userspace remains the gate before Linux control/input
and Omarchy configuration.
