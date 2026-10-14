# Stage B attempt 11 — pin-controller probe boundary; return confirmation pending

2026-10-14 America/New_York. One human-started, filmed boot030 RAM attempt.
Reviewed M5 handoff `1125c33`; readiness/execution `3c0b051`.
Installed boot021 m1n1 and clean client pin unchanged. No reconnect, retry,
reinstall or boot/security/volume/default changes.

## Provenance and controller

* Archive SHA-256: `260f57106007b654a522480e3c20fb2b3630338a5b90edaa64bd067fa0ec2c16`.
* Image SHA-256: `190cd86d5f823326f5a44277f5efb96cc01c85b3a3f9ffbde16d9cb7abe35067`.
* SHA256SUMS: `8772c4585be4b646eec28873d203928d17ea1855d8177d9ca1d729c315afabad`.
* Clean client: `57a9339ffd1876e78297b17d34dece8cff8fa1ba`.
* Archive size **16,724,043 bytes** and SHA-256 verified before extraction.
  All **13 intake files**, offline launcher, controller/decoder digests and
  **90 offline cases PASS**. Only Image/package manifest changed from boot029.
* Fixed arguments unchanged, including the sole
  `initcall_blacklist=clk_debug_init` and `ilinux_probe_diag=1`.
* Ignored receipt: `build/native-intake/receipts/boot030-attempt11.json`.
  Ignored `build/native-intake/results/boot030-stage-b-attempt11.json`/`.md`
  preserve invocation, hashes, checkpoints and structured screen observations.
* Post-attempt-10 original Full/lab Permissive prerequisite PASS per M5.
  Those results are not fresh post-attempt-11 protection/default checks.

| Controller timing (UTC) | Value |
|---|---|
| Start | 2026-10-14T15:27:11.254767+00:00 |
| End | 2026-10-14T15:27:21.781567+00:00 |
| Handoff | 2026-10-14T15:27:21.541577+00:00 |
| 120-second screen deadline | 2026-10-14T15:29:21.541577+00:00 |
| Exit / elapsed | **0 / 10.526 seconds** |

Primary USB identity, target t6050/packaged boot021 marker, no started secondaries,
board/framebuffer, upload, effective DT/arguments and kboot request/reply PASS.
Final **Hardware DT CPU/AIC3/timer routes PASS**; both DAPF checkpoints and
96-byte RAM correction/readback PASS; 16-byte framebuffer descriptor/readback
PASS. Reviewed launcher `main(argv)` invoked exactly once; USB closed.
Fixed checkpoints only, no raw target dumps or serial-bearing paths retained.

## Direct evidence and coverage

Human confirmed filming before launch and supplied **IMG_2661.mov (43.43 s,
1280x720)** and **IMG_2662.jpeg**. Video frames/crops reviewed at 0, 10, 15, 20,
30 and 43.28 seconds. Detailed photo and original-resolution crops resolve
small text unreadable in the video. Full media remains outside workspace/Git.

The clip is shorter than the full 120-second observation window: no 60/90-second
samples are available. Review uses paused samples, not every frame. The photo
adds detail, not a duration measurement. Panel values can change between
renders; they are not an atomic snapshot. Overlapped lower stack frames and
unreadable prefixes are explicitly omitted rather than reconstructed.

### Native kernel, timer and phases — observed in detailed photo

```text
target=j716c-t6050 mode=EL2 cpus=1
phase=1 device=0
timer counter=PASS ticks=25
timer phys=1 virt=7 irq_masked=0 fiq_masked=0
phase=10 device=0
phase=11 device=0
phase=12 device=0
reschedule pending=1 strip=1 display=6 (P/S/W/H hex)
phase=13 device=0
phase=2 device=0
phase=3 device=0
phase=4 device=0
phase=5 device=0
retry=1 begin compatible=apple,t6050-pinctrl
```

The photo observes `clk_debug_init blacklisted` and
`calling deferred_probe_initcall+0x0/0x4e0 @ 1`.
Phase 13 at kernel timestamp **1.436290** is directly readable this time;
phase 5 appears at **2.581009** and retry 1 begins at **2.817004**.
Kernel header: **7.1.9-gb63199d8b4a3-dirty #8 PREEMPT**, Not tainted.
The early `ilinux-display: ... console_setup=...` line is **NOT OBSERVED**.
The repeated `display=6` and `strip=1` plus visibly rendered lanes are separate
observations. Kernel `cpus=1` is not the diagnostic-userspace `online_cpus=1` marker.

### Literal panel sequence — hexadecimal

| Video time (s) | P | S | W | H | D | B | C |
|---|---|---|---|---|---|---|---|
| 10 | 03 | not confirmed | 00 | 00 | 0000 | 00 | 0000 |
| 15 | 05 | 01 | 04 | 01 | 0057 | 4B | 0057 |
| 20 | 05 | 08 | 04 | 02 | 0059 | 21 | 0059 |
| 30 | 05 | 09 | 04 | 02 | 0059 | 63 | 0059 |
| 43.28 | 05 | 09 | 04 | 02 | 0059 | 63 | 0059 |
| Detailed photo | 05 | 09 | 04 | 02 | 0059 | 63 | 0059 |

All seven lanes/four rows are visible. The sequence demonstrates changing
probe/scheduler/heartbeat observations; it is not a complete list of transitions.
The last panel is unchanged between 30 and 43.28 seconds and matches the photo.
No H=03+ or subsequent phase completion is observed in supplied evidence.

Offline `kernel/experiments/probe-path/decode.py` and pinned public tables decode:

* **D=C=0057:** `/soc/pinctrl@2881e4000`; compatible `apple,t6050-pinctrl`,
  `apple,t8103-pinctrl`. **B=4B:** `really_probe returning`.
* **D=C=0059:** `/soc/pinctrl@29c000000`; same compatible strings.
  **B=21:** driver match returned / matching-deferral decision.
  **B=63:** platform actual driver probe callback boundary, if present.

These are public DT table indexes/paths, not unique hardware IDs. The photo
also directly reads **`2881e4000.pinctrl returned 0 after 164043 usecs`** and
**`retry=1 end compatible=apple,t6050-pinctrl`**. The first pin-controller probe
therefore returned successfully. A subsequent line shows the same compatible
string, but its retry-number prefix is hidden by the panel. Do not infer that
hidden prefix from the later device counter.

### Watchdog and scheduler evidence

First report at kernel time **6.625261**:

```text
heartbeat=1 phase=5 worker=4 device=1 ticks=1304
sched=7 selections=1274 prev=52 next=20 current=20/kdevtmpfs
```

The first dump header names **CPU 0, PID 20, kdevtmpfs**. Readable later text:

```text
[heartbeat prefix obscured] phase=5 worker=4 device=2 ticks=2584
[sched prefix obscured] selections=2550 prev=52 next=38 current=38/kworker/u4:1
```

H=02 and S=09 are separately readable in the panel. Kernel watchdog heartbeats
are **not** the diagnostic userspace 60-second liveness milestone.
The printed `device` is a retry counter; it is separate from public D/C indexes.

Readable first-stack frames, in order, from the detailed photo:

```text
show_stack+0x18/0x24 (C)
dump_stack_lvl+0x60/0x80
dump_stack+0x18/0x24
ilinux_probe_watchdog+0xc8/0xf0
call_timer_fn.isra.0+0x24/0x80
__run_timers+0x218/0x260
run_timer_softirq+0x8c/0x100
handle_softirqs+0xfc/0x240
__do_softirq+0x14/0x20
____do_softirq+0x10/0x20
call_on_irq_stack+0x30/0x48
do_softirq_own_stack+0x1c/0x40
__irq_exit_rcu+0xd4/0x10c
irq_exit_rcu+0x10/0x1c
[remaining lower frames obscured by panel; not reconstructed]
```

This is the requested watchdog diagnostic dump; no explicit panic/Oops is
observed. It was captured with **kdevtmpfs current during the first retry**,
before the final D=0059 boundary. It is **not established as a stack of the
final pin-controller driver callback**. The later scheduler summary identifies
a different current task, `kworker/u4:1`.

## Outcome and next M5 work

| Milestone | Result |
|---|---|
| Controller, hardware DT, DAPF and descriptor gates | **PASS** |
| Native Linux, EL2/one CPU, counter/ticks, phase 13 through 5 | **OBSERVED** |
| Four-row panel, two heartbeat values, first probe return | **OBSERVED** |
| Final public device/operation | **0059 / pinctrl@29c000000 / B=63** |
| Diagnostic PID 1 / userspace online_cpus=1 / 60-second liveness | **NOT OBSERVED** |
| Macintosh HD return | **PENDING HUMAN CONFIRMATION** |
| Fresh protection/default checks | **NOT CHECKED — M5 after return** |

The deadline and shutdown/startup-options/Macintosh HD return instructions were
sent at **11:29:21 a.m. Eastern**. Return confirmation is still pending; do not
claim a successful return or refreshed policies until the human/M5 reports them.
**Attempt 11 is consumed. No retry or settings change.**

Source maps P=05 to the first deferred-work flush, W=04 before bus probing,
and B=63 to the platform driver callback boundary. The decoded final device
and successful earlier probe narrow the next offline investigation to the
**t6050 pin-controller instance at `/soc/pinctrl@29c000000`**, its callback and
its dependencies. This is not an exact blocked PC or proof of a register,
driver, interrupt or lock fault. Preserve all working gates and the sole
clock-debug skip. M5 owns read-only return checks and targeted offline analysis;
native diagnostic userspace remains the gate before Linux control/input/Omarchy.
