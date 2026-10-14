# Stage B attempt 9 — phase 12, reschedule pending, strip unavailable; return confirmed

2026-10-14 America/New_York. One human-started, phone-recorded RAM attempt.
Reviewed M5 handoff `3503bf1`; readiness/execution `87a80dd`. Boot028 used;
installed boot021 m1n1 and clean client pin unchanged. No reconnect, retry,
reinstall or boot/security/volume/default changes.

## Provenance and controller

* Archive SHA-256: `689fce13b00c4e59af61e5a23666509579985b89920a0477e4b107c6cf5944e9`.
* Image SHA-256: `514dde0c48c17d77d1979fb98b13f5ecb45096839e8b10a72d24adcf9df0778f`.
* SHA256SUMS: `0120ed68ecf994204a94b2ac2ef3e57a66ea37b9db1e7f61becaf5f4482b87b2`.
* Clean client: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Archive digest/16,722,641-byte size verified before extraction; 13-file
  intake, reviewed controller digests, offline launcher and **90 cases PASS**.
* Only Image and package manifest differ from retained boot027. Fixed arguments
  unchanged, including `initcall_blacklist=clk_debug_init ilinux_probe_diag=1`.
* Ignored receipt `build/native-intake/receipts/boot028-attempt9.json`; ignored
  `build/native-intake/results/boot028-stage-b-attempt9.json`/`.md` retain
  exact invocation/args, source/procedure/payload/receipt hashes and checkpoints.
* Post-attempt-8 original Full/lab Permissive prerequisite already PASS per M5;
  those checks do not constitute a fresh post-attempt-9 protection check.

* Start UTC: `2026-10-14T14:11:02.041163+00:00`.
* End UTC: `2026-10-14T14:11:12.571778+00:00`.
* Handoff UTC: `2026-10-14T14:11:12.342802+00:00`.
* Screen deadline UTC: `2026-10-14T14:13:12.342802+00:00`.
* Controller exit **0**, elapsed **10.530 s**.
* Deadline communicated as **10:13:12 a.m. Eastern**; return steps given.
* Primary USB identity, target t6050/packaged boot021 marker, no started
  secondaries, board/framebuffer, upload, prepared-DT/argument gates and kboot
  request/reply PASS. Controller completion is separate from Linux success.
* **Hardware DT PASS:** J716c/t6050 CPU topology, AIC3 and timer routes verified.
* Both DAPF checkpoints PASS; bounded 96-byte RAM correction/readback PASS.
* Framebuffer kernel RAM descriptor/readback PASS (bounded 16-byte data).
* Reviewed launcher `main(argv)` invoked exactly once. Fixed checkpoints only;
  no raw target ADT/memory/register output or serial-bearing paths retained.

## Reviewed video evidence

Human supplied `IMG_2659.mov`, duration **21.598 s**, at 720x1280. The agent
reviewed paused frames at 0, 5.4, 6, 7, 8, 9, 10.8, 11, 16.2 and 21.45 seconds,
including enlarged crops of the lower display. Original media stayed in place;
temporary review frames stayed outside the workspace. No full media committed.

At the start, m1n1 proxy/heap output is visible. DT preparation is visible at
5.4 seconds; Linux/AIC initialization at 6 seconds; progressing initcalls at
7 seconds. By 8 seconds these ordered diagnostics are visible (timestamps
omitted; kernel messages, not a reconstructed framebuffer-strip sequence):

```text
ilinux-probe: target=j716c-t6050 mode=EL2 cpus=1
ilinux-probe: phase=1 device=0
ilinux-probe: timer counter=PASS ticks=25
ilinux-probe: timer phys=1 virt=7 irq_masked=0 fiq_masked=0
ilinux-probe: phase=10 device=0
ilinux-probe: phase=11 device=0
ilinux-probe: phase=12 device=0
ilinux-probe: reschedule pending=1 strip=0 (P/S/W/H hex)
```

The exact `initcall clk_debug_init blacklisted` message is also visible.
The last line above remains the final visible diagnostic in reviewed frames at
9, 10.8, 11, 16.2 and 21.45 seconds. **Phase 13, phase 2, watchdog heartbeat,
scheduler summary, symbolic stack, worker/retry details and diagnostic
userspace are NOT OBSERVED.** No explicit panic/Oops appears in reviewed frames.

The status-strip availability call reports **strip=0**. Literal P/S/W/H lane
values or changes are **NOT OBSERVED**; do not turn this into `P:00 S:00 W:00
H:00`, or claim P=0C was seen on the strip. Printed decimal phase 12 is observed.
The renderer can reject unavailable mapping/geometry/other prerequisites; this
result alone does not establish which prerequisite failed or prove a display fault.

| Milestone | Result |
|---|---|
| Native Linux and clock blacklist message | **OBSERVED** |
| Kernel target/mode/count | **J716c/t6050, EL2, cpus=1 OBSERVED** |
| Counter/ticks | **PASS, 25 ticks OBSERVED** |
| Timer status | **phys=1 virt=7 irq_masked=0 fiq_masked=0 OBSERVED** |
| Printed phase sequence / last | **1 → 10 → 11 → 12 / last 12 OBSERVED** |
| Rescheduling / strip availability | **pending=1 strip=0 OBSERVED** |
| Literal strip lanes/sequence | **NOT OBSERVED** |
| Phase 13+, heartbeat, scheduler summary, stack, worker/retry | **NOT OBSERVED** |
| Diagnostic PID 1 / userspace online_cpus=1 / 60-second liveness | **NOT OBSERVED** |
| Macintosh HD return | **PASS — human confirmed** |
| Fresh protection/default checks | **NOT CHECKED — M5 next** |

One CPU is observed in the kernel checkpoint; this is separate from the
userspace `online_cpus=1` marker. Counter/tick progress during the sample is
established; subsequent scheduling/interrupt/softirq/console behavior is not.
The clip covers about 21.6 seconds, not the whole 120-second window. Review
used paused samples, not every video frame; fine/fast text can remain unreadable.
No later message was reported in the human's return confirmation. No exact
blocking instruction or root cause is established by this evidence.

## Return and next M5 work

Human confirms usual Macintosh HD desktop return: "back". Attempt 9 is
consumed; no automatic retry or settings changes. M5 performs read-only return
checks and offline analysis next.

In the reviewed source, phase 12 and the pending message follow `mod_timer`
and precede `preempt_enable`; phase 13 would follow its return. This is a
source-based investigation boundary, not proof of a fault in that call.
Investigate the scheduling/visibility boundary and why the strip reports
unavailable. Preserve the passing controller/hardware/DAPF/descriptor gates,
installed boot021 setup and single existing skip. Stable diagnostic userspace
remains the gate before a Linux control channel or Omarchy configuration.
