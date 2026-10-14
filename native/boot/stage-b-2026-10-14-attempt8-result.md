# Stage B attempt 8 — native timer/ticks PASS; phase 1 last visible; return confirmed

2026-10-14 America/New_York. One human-started RAM attempt with phone recording
confirmed before launch. Reviewed M5 handoff `46ad887`; readiness/execution
`174419e`. Used boot027; installed boot021 m1n1 and pinned client unchanged.
No reconnect, retry, reinstall or boot/security/volume/default changes.

## Provenance and controller

* Archive SHA-256: `33c7ff4d1f8e93c929a5024ebb19b7dee825cb14e1c7bf93f7df8c5526bf6a8c`.
* Image SHA-256: `5a5ca64eaf2c3389e9fca226d7244150edbc8975738fe11a9304c0c996e29b64`.
* SHA256SUMS: `3006253a5747677845576c1ba71b67da48c33326d70fa52c7ea8f0c74bf2d6a4`.
* Client: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`, clean.
* Archive digest/16,721,223-byte size verified before extraction; all 13 files,
  reviewed controller hashes, offline launcher and **90 offline cases PASS**.
* Only Image and package manifest differ from retained boot025. Exact fixed
  args retain `initcall_blacklist=clk_debug_init` and add `ilinux_probe_diag=1`.
* Ignored receipt: `build/native-intake/receipts/boot027-attempt8.json`.
  Ignored `build/native-intake/results/boot027-stage-b-attempt8.json` retains
  exact invocation/arguments, source/procedure/payload hashes and checkpoints.
* Post-attempt-7 original Full/lab Permissive protection prerequisite already
  PASS per M5. These are pre-attempt checks, not a fresh post-attempt-8 check.

* Start UTC `2026-10-14T13:38:30.894614+00:00`; end `2026-10-14T13:38:41.387312+00:00`.
* Exit **0**, elapsed **10.492 s**.
* Handoff `2026-10-14T13:38:41.148275+00:00`; kboot request/reply succeeded.
* Screen deadline `2026-10-14T13:40:41.148275+00:00` (9:40:41 a.m. Eastern).
* Primary USB identity, t6050/boot021 marker, no started secondaries,
  board/framebuffer, upload and final prepared-DT/argument gates PASS.
* **Hardware DT PASS:** J716c/t6050 CPU topology, AIC3 and timer routes verified.
* Both DAPF checkpoints PASS: reviewed live layout/code/table and bounded
  96-byte RAM correction/readback. Other entries retained.
* **Early framebuffer PASS:** bounded 16-byte kernel RAM data descriptor
  populated and readback verified.
* Reviewed launcher `main(argv)` called exactly once. Fixed safe checkpoints
  retained; no raw ADT/memory/register output or serial-bearing paths saved.
  Exit 0 establishes controller completion, not diagnostic userspace success.

## Native screen evidence

Fresh human photo `IMG_2658.jpeg` shows late Linux initialization and a Tux
logo. The human describes this as the latest place the boot paused. The
`initcall clk_debug_init blacklisted` message is visible on this attempt.
`sync_state_resume_initcall` returns 0, followed by `deferred_probe_initcall`
and these diagnostic messages (timestamps omitted):

```text
ilinux-probe: target=j716c-t6050 mode=EL2 cpus=1
ilinux-probe: phase=1 device=0
ilinux-probe: timer counter=PASS ticks=25
ilinux-probe: timer phys=1 virt=7 irq_masked=0 fiq_masked=0
```

The final visible line is the timer status. Phase 2 or later, worker/retry
messages and watchdog heartbeats are **NOT OBSERVED** in the supplied photo.
No explicit panic/Oops is visible. The counter/tick check passes its 100 ms
criterion with 25 ticks; that is direct evidence of tick progress during this
sample, not complete validation of interrupts, scheduling or driver probes.
The low timer status bits are retained as observations, not a proposed routing
fix. One CPU is observed in the kernel diagnostic checkpoint; the separate
userspace `online_cpus=1` milestone remains unobserved.

| Milestone | Result |
|---|---|
| Native Linux / exact clock blacklist message | **OBSERVED** |
| Target/mode/CPU checkpoint | **J716c/t6050, EL2, cpus=1 OBSERVED** |
| Counter/tick test | **PASS, 25 ticks OBSERVED** |
| Timer status | **phys=1, virt=7, irq_masked=0, fiq_masked=0 OBSERVED** |
| Highest main phase | **1 OBSERVED**; phase 2 and later **NOT OBSERVED** |
| Worker/retry/heartbeat | **NOT OBSERVED** |
| Diagnostic PID 1 / userspace online_cpus=1 / 60-second liveness | **NOT OBSERVED** |
| Explicit panic/Oops | **NOT OBSERVED** in supplied photo |
| Macintosh HD return | **PASS — human confirmed** |
| Fresh protection/default checks | **NOT CHECKED — M5 next** |

The phone recording was confirmed before launch, but was not supplied or
reviewed. The human was asked to pause/review its ending and reported return
without a video-review result. Do not infer that no transient later text exists
in the video. Full photo/video was not copied into the workspace or committed.
The last visible checkpoint does not prove an exact blocking PC or root cause.

The 120-second deadline and Macintosh HD return steps were communicated. The
human confirms successful return to the usual desktop: "back, update". No
later screen message was reported. Attempt 8 is consumed; no live retry.

## Next M5 work

Perform read-only post-return protection checks and investigate offline the
transition after the timer-status print and before phase 2. In the reviewed
helper, `preempt_enable()` and watchdog setup lie before the phase-2 marker;
this is a source-based investigation boundary, not a confirmed fault in either.
Keep the passing tick result distinct from subsequent scheduling/softirq/console
progress. Incorporate paused video evidence if available. Preserve all gates,
installed boot021 and prior results; do not expand the blacklist or repeat setup.
