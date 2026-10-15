# Stage B attempt 15: boot034 outlives attempt 14's reset, then resets at ~27.7 s, with the M1 host panicking at handoff

2026-10-15. **One RAM attempt consumed. Controller record INCOMPLETE** (the M1
host kernel-panicked at the handoff). The experiment itself ran and is
informative, but its second reset is **confounded** by that host panic.

* **Confirmed:** with genpd `sync_state` honoring `pd_ignore_unused`, attempt
  14's reset at kernel ≈ 8.77 s did **not** happen. Linux ran to at least
  27.6 s, three times longer, with PID 1 and heartbeats 000-004 alive.
* **Observed:** the SoC then reset silently at kernel ≈ 27.7-27.85 s, during
  the release ladder, ≈ 0.07-0.24 s after the 17th release's power-off line.
* **Not established:** what caused that reset. Candidates: a ladder-released
  domain (step 6 or step 17), or the M1's own post-panic hard reset, which fell
  in the same seconds. See "Interpretation".
* **M1 host panic:** Apple's USB CDC driver dereferenced NULL while the
  launcher's Python process was in a tty call, within ~0.5 s of the expected
  handoff. Not our code; a new run hazard.
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and offline verification

* M5 handoff `9499bd0`; published readiness/execution commit `a57837b`.
* Release `native-j716c-boot034`: archive 16,723,189 bytes, SHA-256
  `a856a9b8c6b7fdafeeb68da8dddbc9c82f7e9b5cddf1dc691512f63c0803f5ff`,
  verified against Git before extraction (14 regular members).
* Image 44,599,808 bytes, SHA-256
  `1131a1af5e4d5cfa3206c5eb0afe1a6d72d86a2761a8d906b592e33556882579`. Stage-B
  DT unchanged: `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
  Versus boot033 only the Image and manifest metadata differ.
* 13-file intake and **102 offline cases PASS**; six reviewed controller
  digests match; client pin clean at `57a9339`.
* M1 independent review of the patch: `apply.py` read in full; the ladder block
  ran under ASan/UBSan (2 tests ran, 3 skipped: no Linux tree on M1); the
  152-domain count was reproduced from the Stage-B DT.

## Controller execution (record incomplete)

One invocation through `build/native-intake/run-attempt15.py`, started
**2026-10-15T15:08:37.154Z**. The persisted record reaches only:

* `Package PASS`, `Mode: LIVE RAM LAUNCH`;
* `Primary verified`, `Target PASS: t6050, packaged m1n1 marker, no started
  secondaries`;
* `GPIO ADT PASS: main controller 221 pins/7 groups; exclusions 5,6,7,112,141
  match`;
* `Board/framebuffer PASS`, `DAPF layout PASS`;
* `Uploading DT, initramfs and kernel to RAM` (at +0.84 s).

Nothing after that is recorded: the **RAM-upload-complete, final hardware DT,
DAPF correction, framebuffer descriptor, kboot reply and exit-status
checkpoints are NOT RECORDED**. In attempts 13 and 14 they came at +9.4-9.5 s
and +10.3-10.5 s; the host panicked in that window (next section). Writes after
the panic are plausibly lost, so absence is not evidence of failure. The
M5 booted Linux from the handoff and reproduced attempt 14's GPIO counts, so the
kboot request was delivered with the expected DT.

## M1 host kernel panic (sanitized)

User-supplied panic report; **not committed** (it carries per-boot UUIDs).

| Item | Value |
|---|---|
| Host | MacBookPro18,1 (M1 Pro, T6000), macOS build 25A362 |
| Time | 2026-10-15 15:08:47 UTC (report Calendar field); launcher start +9.85-10.85 s |
| Type | Kernel data abort, NULL dereference (FAR 0x0, ESR 0x96000006), CPU 2 |
| Panicked task | the launcher's single-threaded `Python` process |
| Faulting kext | `com.apple.driver.usb.cdc`, text offset +0x938 (LR +0x1d5c) |
| Call path | IOSerialFamily, usb.serial, usb.cdc.acm, usb.cdc, from a BSD tty syscall |
| Sleep / wake | slept 14:56:00 UTC, woke 15:02:49 UTC (about 6 minutes before) |
| Host reboot | `kern.boottime` 15:09:30 UTC |
| M1 log around panic | nothing persisted for 11:08:36-11:08:50 EDT (unflushed) |

* **Likely:** a race between the launcher's tty close or ioctl and m1n1's USB
  teardown at the handoff (m1n1 replies, then shuts USB down). Same sequence ran
  without incident in about 18 earlier live sessions.
* **Unknown:** the exact syscall. Not tested.
* Plain consequence: the controller wrapper died abruptly, so the record is
  partial. The M5 and its RAM-only state were unaffected by the M1 panic itself.

## Media and method

`Take15.mov`: 49.895 s, 30 fps, 720×1280 portrait, user-supplied into the
ignored inbox. It begins at the m1n1 proxy screen and covers the handoff, Linux,
the reset and the macOS login screen. No still photo.

Reviewed locally with AVFoundation: overview frames, a screen-brightness trace
at 0.5 s and 0.033 s steps, and rotated, upscaled, frame-averaged crops. Review
images were temporary and deleted. **After about 19 s the phone was rotated by
90°**, so the console appears sideways and small; the text is then legible only
in rotated crops, and digits inside domain names are **not** readable. The
macOS login screen at the end is rotated the same way. This is not display
corruption.

Time mapping: `kernel ≈ video − 7.0 s` (bounds 6.94-7.08 s), from the
heartbeat and ladder lines on screen.

## Literal observations

| Video s | Kernel s | Observation |
|---:|---:|---|
| 0-6 | n/a | m1n1 proxy screen (`Running proxy...`) |
| ~7.0 | 0 | flash, Linux boot console with the four-row panel |
| 9.6 | ~2.6 | panel `P:05 S:00 / W:04 H:00 / D:0052 I:FFF / B:2? C:0052` (B glyph unclear) |
| 9.6 | | GPIO `pins=61 readable=61 reserved=0`, handoff `61/7 masked=1`; `pins=221 readable=216 reserved=5`, handoff `221/7 masked=0`; mailbox probe begins |
| 12.0 | | kernel/cmdline/DT model/memory/interrupt dumps, heartbeat 000 |
| 17.8 | 8.33 | heartbeat 001 |
| 26-34.7 | 19.4-27.6 | ladder lines (rotated view) |
| **34.77 → 34.80** | **≈ 27.7-27.85** | **screen goes black within one frame** |
| ~38 | | Apple logo |
| 49.8 | | macOS login, clock 11:09 |

Kernel lines read from upscaled frames:

* `ilinux_genpd_ladder_init` returned 0 after 771 us;
  **`PM: ilinux-genpd: ladder armed: first release in 17000 ms, then one domain
  per 500 ms` at 1.3703 s**.
* `ilinux-probe: target=j716c-t6050 mode=EL2 cpus=1`, timer `counter=PASS
  ticks=25`, phases 1, 10, 11, 12, 13, `reschedule pending=1 strip=1 display=6`.
* **`PM: ilinux-genpd: sync_state keeps unused power domains on
  (pd_ignore_unused)` twice, at 3.2365 and 3.2371 s**, then
  `of_platform_sync_state_init` returned 0 **after 1361 us** (attempt 14: 5017 us,
  which was the actual power-offs).
* `PM: genpd: Not disabling unused power domains` (3.2243 s).
* `PID 1 reached` at 3.2538 s. Version `Linux version 7.1.9-…-dirty … #13 SMP
  PREEMPT Wed Oct 14 19:49:44 EDT 2026` (boot034's build #13).
* Same DT model/compatible, MemTotal 132456032 kB, CPU online mask `0`.
* At about 13.28 s five `apple-pmgr-pwrstate … sync_state() pending due to …`
  lines (driver-core deferral notices; not power-offs).
* `[diag] heartbeat 000-004 online_cpus=1` at 3.32, 8.33, 13.33, 18.33, 23.34 s.
  Heartbeat 005 (28.34 s) was never shown.
* **Ladder, from 19.42 s, one release per ≈ 0.512 s, each a `ladder N: release
  NAME` line followed ≈ 1 ms later by `power off NAME`:**

| Step | Kernel s | Name as read |
|---:|---:|---|
| 1-6 | 19.42, 19.93, 20.45, 20.96, 21.47, **21.98** | six `smc_i2cm?` domains (index digit not readable; descending) |
| 7 | 22.49 | `atc?_usb_aon` |
| 8 | 23.01 | `atc?_phymxwrap` |
| 9-10 | 23.52, 24.03 | `atc?_usb`, `atc?_usb_aon` |
| 11-13 | 24.54, 25.05, 25.57 | `atc?_phymxwrap`, `atc?_usb`, `atc?_usb_aon` |
| 14-16 | 26.08, 26.59, 27.10 | `atc?_phymxwrap`, `atc?_usb`, `atc?_usb_aon` |
| **17** | **27.614 (power off 27.615)** | **`atc?_common_dp_3`** (port digit not readable) |

* No kernel message of any kind between the 17th power-off and the blackout:
  no panic, watchdog, oops or reboot text. `panic=0` would have frozen a panic
  on screen.
* **Last genpd line visible before black:** `PM: ilinux-genpd: power off
  atc?_common_dp_3` at 27.615 s. **Black frame ≈ 27.7-27.85 s kernel.**
* `ladder complete` was **not** reached. The 120 s bound was not needed.

## Interpretation (bounded)

**1. Attempt 14's reset trigger (Confirmed, single changed variable).** The only
difference from boot033 is the genpd change. The bulk sync_state power-off no
longer ran (1.4 ms versus 5 ms), and the 8.77 s reset disappeared. So the
attempt-14 reset came from genpd's sync_state powering domains off, or from
something timing-coupled to it. Domain power-off is therefore a real trigger
class.

**2. The reset at ≈ 27.7 s has three candidate explanations:**

| Candidate | For | Against |
|---|---|---|
| **Step 6** (`smc_i2cm?`, 21.98 s), reset after ≈ 5.7 s | Attempt 14's latency from sync_state to reset was **5.55-5.69 s**; step 6 gives 5.70-5.88 s, the only step within ~0.1 s. Matches the checklist's "≈ 5.6 s before the black frame" rule. | Weak: ~17 candidate steps, so a chance fit is likely. Digit unreadable, so step 6 might be `smc_i2cm1` rather than `0`. |
| **Step 17** (`atc?_common_dp_3`), immediate | Reset ≤ 0.24 s after its power-off line. | Attempt 14 powered the same domain off and survived 5.6 s. Needs an extra assumption. |
| **M1 hard reset** at the end of its panic | The M1's post-panic reset must fall roughly 15:09:00-15:09:22 UTC (panic 15:08:47, kernel up 15:09:30); the M5's reset was ≈ 15:09:15 UTC (handoff ≈ 15:08:47.5 + 27.7 s). | Attempt 14 reset with no M1 event. Cause path (USB-C port reset resets an M5 running Linux) is speculative. |

**These cannot be separated with this run.** Do not claim a culprit domain.

* **Step 17 versus 6** is decidable by a rerun: if the same step precedes the
  reset again, the ladder is implicated.
* **Retraction:** my pre-launch estimate that display domains would be released
  at ~20-34 s was wrong (it assumed device-tree order). The ladder walks genpd's
  list newest-registered first and never reached the display domains before the
  reset.

## Return and next handoff

* Both machines restarted. The M5 reached the macOS login screen on its own
  (clock 11:09); the user reports being back on the default OS. Fresh
  policy/default/installed-object checks: **NOT CHECKED.**
* Attempt 15 is consumed. Because the host panicked at the handoff, the human
  and M5 may judge it **invalid for the second-reset question**.
* **Recommended: rerun the unchanged boot034 package once on a clean M1**
  (restarted fresh, kept on power, `caffeinate -i`, no other activity). The
  readiness record is reusable once the attempt counter is reset by a fresh
  record. If the reset recurs at ≈ 27.7 s after the same step, the ladder is
  implicated. If the ladder runs to `ladder complete`, the M1 reset is the
  likely trigger and sync_state's bulk power-off is the whole story.
* **Film better:** phone fixed, landscape, framed on the bottom-left quarter of
  the M5 screen (the newest ladder lines are at the bottom), and do not move
  it. Mid-run rotation cost the domain-name digits.
* **For M5 (proposals, not authorization):**
  * show the ladder step number and domain index in the large-font panel so a
    camera can read them;
  * a bisect build (skip steps 1-6, or release only 1-6) would separate the
    candidates in one boot;
  * the launcher's final tty close/ioctl may be what hit Apple's driver:
    review clearing `HUPCL` before close and exiting without further tty calls.
    This changes a reviewed controller digest, so it needs a new handoff.

No media, panic text, UUIDs, raw target output or proprietary binaries are
committed. Earlier reports are unchanged.
