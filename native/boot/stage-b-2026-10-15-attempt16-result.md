# Stage B attempt 16: boot035 runs past the whole release ladder — first stable native baseline

2026-10-15. **One RAM attempt consumed. Controller PASS, no host panic.**

* **First stable native Linux on this M5 Max.** Diagnostic PID 1 ran with
  `online_cpus=1`, passed the **60-second liveness milestone** (63.36 s kernel),
  and kept heartbeating to at least **108.4 s** (heartbeat 021). The clip ends
  at kernel ≈ 110.7 s with the system still alive.
* **The release ladder ran to completion:** `ladder complete: 74 domains
  released` at ≈ 57.31 s kernel. No reset, no blackout, no restart.
* **No `smc_i2cm` domain exists in this run.** The seven SMC-owned nodes are
  gone from the DT, and the first ladder lines are `atc*` domains.
* **The release that preceded attempt 15's reset (`atc?_common_dp_3`) passed**
  at ≈ 24.55 s (ladder step 11 here; step 17 there).
* **Not separated by this run:** whether the SMC domains or the M1's
  post-panic reset caused attempt 15's second reset. See "Interpretation".
* Fresh policy/default checks: **NOT CHECKED.** No retry or settings change.

## Reviewed inputs and controller execution

* M5 handoff `4debc28` (published `9815dd7`); readiness/execution `7a37fb6`.
* Release `native-j716c-boot035`: archive 16,723,179 bytes, SHA-256
  `81cbbd1ca09ec53bbfe8f616e578c07d7f878a26a7629c2d1de40d969be966e7`, verified
  against Git before extraction (14 regular members).
* Image `1131a1af…2579` (unchanged from boot034); Stage-B DT
  `b1105bbf2c207c8c816c4b9cc0231ecc1d49543e05fe4b772bcb153019e186db`.
* M1 independent DT diff versus boot034: exactly `smc_i2cm0`-`6` removed (365
  to 358 nodes), nothing else changed, nothing referenced them, GPIO reserved
  ranges kept.
* 13-file intake and 102 offline cases PASS; controller digests match; client
  pin clean at `57a9339`.
* One invocation through `build/native-intake/run-attempt16.py` (durable
  `fsync` per checkpoint; printed deadline set to 180 s):

| Item | Result |
|---|---|
| Invocation count | 1 |
| Start / handoff UTC | 2026-10-15T20:28:15 / 20:28:25.611598 |
| Elapsed / exit | **10.493 s / 0** |
| Target, marker, secondaries | PASS: t6050, boot021 marker, none started |
| GPIO ADT | PASS: 221 pins / 7 groups, exclusions 5,6,7,112,141 |
| Board/framebuffer, DAPF layout and correction | PASS |
| Final hardware DT, framebuffer descriptor | PASS |
| kboot reply / USB close | PASS |
| Screen deadline | 20:31:25 UTC (4:31:25 PM Eastern), communicated after handoff |

* **M1 host:** continuous since its 11:09 EDT boot (uptime 5 h 26 min at review);
  no new panic report. Kept awake with `caffeinate -i`.

## Media and method

`Attempt16.mov`: 120.493 s, 30 fps, **568×320 landscape-encoded, oriented
320×568 portrait** (low resolution), user-supplied into the ignored inbox. The
phone stayed fixed with the console filling the frame vertically, so the text is
legible in upscaled crops, but **digits inside domain names are mostly not
readable**. Reviewed locally with AVFoundation: overview frames, a brightness
trace at 2 s and 0.1 s steps, and upscaled crops. Review images deleted; media
stays local.

Time mapping: the handoff flash is at video 9.77 s, so `kernel ≈ video − 9.8 s`
(bounds 7.1-12.1 s from the last frame). The clip covers ≈ 110 s of Linux.

## Literal observations

| Video s | Kernel s | Observation |
|---:|---:|---|
| 0-8.5 | n/a | m1n1 proxy screen |
| 9.77 | 0 | handoff flash, Linux console |
| 12-14 | | kernel/cmdline/DT model/memory/interrupt dumps, heartbeat 000 |
| ≈ 29 | 19.43 | **ladder step 1** |
| 120.49 (end) | ≈ 110.7 | last frame; no restart |

Brightness trace: steady (25-29 mean) from video 10 s to the end. No blackout,
no Apple logo, no login screen anywhere in the clip.

Kernel lines read from upscaled frames:

* **Ladder first release at ≈ 19.43 s**, one every ≈ 0.51 s. Steps 1-8 read as
  `atc?_usb_aon`, `atc?_phymxwrap`, `atc?_usb` (repeating per port), then
  heartbeat 004 at 23.34 s, step 9 `atc?_usb`, step 10 `atc?_usb_aon`,
  **step 11 `atc?_common_dp_3` at ≈ 24.55 s**, step 12 another `common_dp`
  domain. **No `smc_i2cm` name appears.**
* `PM: ilinux-genpd: ladder complete: 74 domains released` at ≈ 57.31 s. The
  count is cross-checked by timing: 19.43 s + 74 × 0.512 s = 57.3 s. A line
  `power off dispext0_*` precedes it; **display-related domains were released
  and the console kept rendering.**
* `[diag] heartbeat 011 online_cpus=1` at ≈ 58.36 s, then **`[diag] 60s elapsed;
  still alive. Observe the M5 framebuffer; no native USB console is assumed.`
  at ≈ 63.36 s**.
* Heartbeats 012-021 every 5.0 s, each `online_cpus=1`; **heartbeat 021 at
  ≈ 108.39 s** is the last in the clip. Heartbeat 022 (113.39 s) falls after it.
* CPU online mask `0`; DT model `Apple MacBook Pro (16-inch, M5 Max)`; same
  kernel/cmdline/memory dumps as attempt 15.
* **Not re-read at this resolution:** the panel rows, GPIO probe lines and the
  `sync_state keeps unused power domains on` line (same kernel and DT apart from
  the seven nodes; attempt 15 recorded them).

## Interpretation (bounded)

**Confirmed (this run):**

* With the Stage-B DT lacking the seven SMC-owned domains, Linux releases every
  one of the 74 boot-on unclaimed domains it owns, one at a time, and keeps
  running. That includes every `atc*` domain and a `dispext*` domain.
* The step-17-immediate explanation for attempt 15 (`atc?_common_dp_3`) is
  **refuted**: the same domain was released here without incident.
* The ladder finished at 57.3 s, not ≈ 94 s. The M5's estimate of 145 domains
  counted unclaimed nodes in the DT; only 74 were powered on at boot.

**Likely, not separated:** the SMC I2C domains caused attempt 14's and
attempt 15's resets (≈ 5.6-5.7 s after their power-off).

* This run changed **two** things against attempt 15: the SMC nodes were
  removed, **and** the M1 did not panic. The host-reset explanation for attempt
  15's second reset would also have vanished.
* Attempt 14 had no M1 event, so the host-reset story cannot explain it; the SMC
  domains can, as can "74 domains powered off at once". The simultaneity
  alternative is not excluded by anything so far.
* A clean separation needs one of: rerunning boot034 (SMC included) without an
  M1 panic and seeing the ≈ 27.7 s reset recur, or powering a single SMC domain
  off through the proxy (the M5's PMGR probe). Practical value is low: the
  SMC-less DT is the right shape regardless, since no Asahi device tree exposes
  them.

**Not established / not tested:** efficiency, SMP, idle states, storage, USB or
input in Linux, GPU, display control, any parity claim. Boot035 is a diagnostic
RAM image with `pd_ignore_unused` and a one-CPU, no-cpufreq configuration.

## Return and next handoff

* The user reports the M5 stayed up through the filmed 2 minutes and no M5 or M1
  crash afterwards (not filmed, not independently verified here). The M5 needs a
  power-off and Macintosh HD return; fresh policy/default/installed-object
  checks: **NOT CHECKED.**
* Attempt 16 is consumed; no retry or settings change.
* **For M5 (proposals, not authorization):**
  * treat the SMC-less Stage-B DT as the baseline and carry the same removal
    into the t6050 DT draft;
  * the next engineering gate is a Linux-side control channel and a usable RAM
    root, then the configuration agent;
  * an efficiency-relevant next experiment: boot035's DT with stock genpd
    behavior (no `pd_ignore_unused`, no ladder), to see whether the kernel can
    power-gate the 74 domains on its own, which would be the first real power
    saving;
  * film at 1080p or better, and keep the bottom-left corner in frame.

No media, raw target output or proprietary binaries are committed. Earlier
reports are unchanged.
