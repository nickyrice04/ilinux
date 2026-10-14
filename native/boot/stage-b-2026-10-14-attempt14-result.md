# Stage B attempt 14: boot033 reaches native PID 1, then a silent system reset

2026-10-14. **One RAM attempt consumed. Controller PASS.**

* **First native Linux userspace on this M5 Max.** Diagnostic PID 1 ran with
  `online_cpus=1` and printed two heartbeats, 5.003 s apart.
* **Both GPIO controllers probed successfully.** The main controller reported
  the expected `pins=221 readable=216 reserved=5`.
* **The SoC then reset without any message,** about 5.6 s into userspace
  (kernel ≈ 8.77 s), and rebooted into Macintosh HD by itself.
* **60-second liveness: NOT REACHED.** Cause of the reset: unknown.
* Fresh post-attempt policy/default checks: **NOT CHECKED.**

## Reviewed inputs and controller execution

* M5 handoff `b76ab6b`; published readiness/execution commit `994b62f`.
* Release `native-j716c-boot033`: archive 16,723,317 bytes, SHA-256
  `6cbf5d1396ddd2b5f79255e65c6c776f8122921b06327271e1102f7b7f0d55cd`.
* Image SHA-256 `250d9ff58e5f5397e1bb54682f2bd8a7a679f44f2863629ef7b89ec45ad1eb15`;
  Stage-B DT `4b3adee52465b809e9c8a1946b7610c63f1ae3c0b24f7334cd485260da84adce`.
  Only Image changed from boot032.
* Offline intake: 13 files and 102 cases PASS; client pin clean at `57a9339`.
* One invocation through `build/native-intake/run-attempt14.py`, with fixed
  checkpoints only and raw target output discarded:

| Item | Result |
|---|---|
| Invocation count | 1 |
| Handoff UTC | 2026-10-14T19:50:04.394670+00:00 |
| Elapsed / exit | **10.74 s / 0** |
| Target / marker / secondaries | PASS: t6050, boot021 marker, no started secondaries |
| GPIO ADT | PASS: 221 pins / 7 groups, exclusions 5,6,7,112,141 |
| Final hardware DT | PASS: J716c/t6050 CPU topology, AIC3 and timer routes |
| DAPF layout / RAM correction | PASS / PASS (96-byte table, readback) |
| Early framebuffer descriptor | PASS (16-byte descriptor, readback) |
| kboot reply / USB close | PASS |
| Screen deadline | 19:52:04 UTC (3:52:04 PM Eastern), communicated after handoff |

## Media and method

`IMG_2669.mov`: 34.297 s, 30 fps, 720×1280 portrait. It covers the m1n1 proxy
screen, the handoff, Linux, the reset and the macOS login screen. No still photo
was supplied. Frames were extracted locally with AVFoundation, plus
screen-brightness traces and upscaled crops. The media stays in ignored
`build/native-intake/inbox/`; review images were temporary and deleted. The
video is the only source. Video time maps to kernel time by about
**kernel = video − 9.42 s**: heartbeat 001 (8.233382 s) first appears between
video 17.60 and 17.70 s.

## Literal observations

| Video s | Observation |
|---:|---|
| 0–9.2 | m1n1 proxy screen, including `Primary WDT disabled` and `Secondary WDT disabled` |
| 9.27–9.5 | Handoff flash, then the Linux framebuffer |
| 12.0 | Panel `P:05 S:00 / W:04 H:00 / D:0052 I:FFF`; fourth row (B/C) out of frame |
| 12.4 | Panel `P:05 S:00 / W:04 H:00 / D:004C I:FFF` |
| 12.8–18.17 | Diagnostic initramfs output, then heartbeats |
| **18.17 → 18.20** | **Full screen to black within one frame** |
| 21.6 | Apple logo |
| 26.0 | Apple logo with progress bar |
| 34.2 | macOS login screen showing 3:50 |

Kernel lines read from upscaled frames:

* `deferred_probe_initcall` called at 1.317801 s, then:
  * `ilinux-probe: target=j716c-t6050 mode=EL2 cpus=1`;
  * `timer counter=PASS ticks=25`;
  * `phys=1 virt=7 irq_masked=0 fiq_masked=0`;
  * phases 1 → 10 → 11 → 12 → 13 → 2 → 3 → 4;
  * `reschedule pending=1 strip=1 display=6`.
* `…81e4000.pinctrl: GPIO cache: pins=61 readable=61 reserved=0`;
  `t6050 IRQ handoff: pins=61 parents=7 masked=1`; returned 0 after 103600 usecs.
* `…c000000.pinctrl: GPIO cache: pins=221 readable=216 reserved=5`;
  `t6050 IRQ handoff: pins=221 parents=7 masked=0`; returned 0 after 264934 usecs.
* `begin compatible=apple,t6050-asc-mailbox`, then returned 0 after 4570 usecs.
* `clk: Not disabling unused clocks` (3.135819);
  `PM: genpd: Not disabling unused power domains` (3.137949).
* `of_platform_sync_state_init` returned 0 after 5017 usecs (3.150171).
* `Freeing unused kernel memory: 3776K` (3.151293);
  `Run /init as init process` (3.152165).
* `PID 1 reached: the kernel booted and ran userspace.` (3.166444).
* `/proc/version`: `Linux version 7.1.9-…-dirty … #12 SMP PREEMPT Wed Oct 14
  14:42:04 EDT 2026`, consistent with the boot033 build.
* `/proc/cmdline` begins with the fixed diagnostic arguments.
* DT model `Apple MacBook Pro (16-inch, M5 Max)`; compatible
  `apple,j716c apple,t6050 apple,arm-platform`.
* meminfo: MemTotal 132456096 kB, MemFree 132349408 kB, MemAvailable 131906320 kB.
* CPU online mask `0`. cpuinfo: implementer 0x61, BogoMIPS 2000.00, which
  implies a 1 GHz counter; inferred, not separately read.
* `/proc/interrupts`: arch_timer (AIC-FIQ) 803; two ASC mailbox lines at 0;
  IPI5 (IRQ work) 2; other IPIs 0.
* `[diag] heartbeat 000 online_cpus=1` at 3.230083;
  `[diag] heartbeat 001 online_cpus=1` at 8.233382.
* After heartbeat 001 the screen showed only a cursor. There was **no kernel
  message between the heartbeats and none before the reset**: no panic,
  watchdog, deferred-probe, reboot or error text.

Offline decode with the authoritative `device-identities.json`:

* D 0052 = `/soc/mbox@419608000` (`apple,t6050-asc-mailbox`).
* D 004C = `/soc/iommu@41dc50000` (`apple,t6050-sart`).
* Both use PMGR domain `power-controller@140`.
* The 0057/0059 GPIO controllers match the earlier tables.
* B/C were not readable (out of frame). I=FFF means inactive.

## Interpretation (bounded)

* **Confirmed:**
  * native boot033 completes initcalls and reaches diagnostic PID 1 at
    3.152–3.166 s;
  * userspace runs for at least 5.003 s with one online CPU;
  * the boot032 reserved-pin GPIO repair lets both GPIO controllers probe,
    with the expected main-controller counts;
  * the reset is a full SoC reboot to the default volume (Apple logo about
    3.4 s after blackout).
* **Not established:** the reset trigger. Attempts 11-13 ran 120 s without a
  reset but never got past the GPIO controllers. Attempt 14 is the first run
  to execute everything after that: the mailbox and SART probes, late initcalls
  including `of_platform_sync_state_init`, userspace, and second-scale idle.
  The trigger is most likely among these, but which one is unknown.
* **Evidence against a software restart:**
  * nothing printed, and `panic=0` would have frozen a panic on screen;
  * diag init never calls reboot;
  * m1n1 disabled both watchdogs before handoff (on screen);
  * Linux's Apple watchdog driver leaves a disabled watchdog off unless it is
    opened or used for restart.
  Together these point to a hardware or firmware-initiated reset (Likely).
* **Ranked hypotheses for M5** (offline checks first; none tested):
  1. **PMGR domains powered off at sync_state despite `pd_ignore_unused`.**
     Check in the exact 7.1.9 source whether genpd's sync_state path powers
     off boot-on domains regardless of that flag, and which of the 183
     pwrstate domains have no DT consumer. A coprocessor or fabric dependency
     losing power could trigger a supervised reset seconds later. The 5017 µs
     sync_state call is the only late-init step with measurable duration.
  2. **ANS coprocessor side effects.** NVMe is disabled, but Linux bound the
     ANS-area mailbox and SART while the coprocessor firmware may still run.
     Check the mailbox v4/SART probe side effects and m1n1's kboot handling.
  3. **Second idle period.** The first 5 s idle survived; the reset came about
     0.5 s into the second sleep. This needs the same `idle=nop` path review.
  4. **Supervision unrelated to Linux actions.** Unknown.

## Return and next handoff

* The M5 rebooted itself to Macintosh HD. The macOS login screen is visible at
  3:50 PM, and the user reports being in the default OS.
* Fresh policy/default/installed-object checks: **NOT CHECKED** (M5 read-only
  review next).
* Attempt 14 is consumed. No retry or settings changes were made.
* Suggested boot034 observation additions, all offline-buildable:
  * diag init mounts debugfs and prints `pm_genpd/pm_genpd_summary` and
    `devices_deferred` right after PID 1;
  * print a heartbeat every second with kernel time and mailbox interrupt
    counts;
  * keep the earlier proposals (built-in stall detectors, panic output drawn
    without the workqueue).
* Change one variable at a time. The lowest-risk first test of hypothesis 1 is
  keeping PMGR domains powered through sync_state.
* Native userspace now exists only transiently. Control/input, a RAM root and
  the configuration agent still wait on stable userspace.

No media, raw target output, ADT/memory dumps, identifiers or proprietary
binaries are committed. Earlier reports are unchanged.
