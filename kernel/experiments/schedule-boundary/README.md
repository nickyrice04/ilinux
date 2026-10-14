# Attempt 9: observe the reschedule boundary without losing the watchdog

**Historical boot028 handoff:** attempt 9 is now consumed; the reviewed result
and successor are in [boot029 context/display](../context-display/README.md).
The original validation below records what was known before attempt 9.

2026-10-14. Original diagnostic improvement in boot028, based on boot027.
**Native cause unresolved; attempt 9 NOT RUN.** This is not a confirmed hang
repair or an Omarchy desktop boot. It preserves the installed boot021 setup.

## Evidence and engineering decision

[M1 attempt 8](../../../native/boot/stage-b-2026-10-14-attempt8-result.md),
commit `7da251d`, observes native J716c/t6050 EL2, one CPU, phase 1 and a
100 ms counter test with **25 ticks**, then architectural timer status. No
phase 2, diagnostic userspace or panic is visible. The last line is not a
blocking PC. The recording was not supplied/reviewed by M1; transient later
output cannot be excluded. Do not call this a timer-delivery failure.

Exact boot027 source and REA 6.4.0/Ghidra 12.1.4 identify a diagnostic defect:
`preempt_enable()` can call `preempt_schedule()` **before** the watchdog is
initialized/armed. A stalled reschedule could therefore leave no heartbeat.
There are also watchdog-setup and console-visibility possibilities.

REA separately verifies `cpu_do_idle`: the NOP branch already exists in this
kernel. There is no justification for reapplying an idle backport or changing
timer routing. The earlier planning version requirement is superseded by the
actual compiled implementation. [audit.py](audit.py) checks both complete
function ranges/high-pcode PCs, **261 ARM64 instruction words** with LLVM,
and **163 nonrelocated words** against the deployed Image. The remaining 98
relocation-bearing words are reviewed in linked GNU disassembly. The ordered
preemption/timer calls are checked there too. [evidence.json](evidence.json)
pins every object and the Image. REA types/signatures have warnings; retained
source and linked instructions govern conclusions. No Apple binary was needed.

## Change

[apply.py](apply.py) rejects unexpected source hashes and ambiguous anchors.
It operates only in a new build-VM copy of the retained boot027 tree.

* Arm the same finite timer-softirq watchdog **before** enabling preemption.
  New main phases 10–13 isolate timer initialization, arming and rescheduling.
  Normal probing, both worker flushes and scheduling semantics are retained.
* Record scheduler checkpoints and selected previous/next kernel PIDs while
  the deferred initializer is active. The hook does not print, acquire locks,
  allocate, enable interrupts, change scheduling policy or touch device registers.
* A small **`P:xx S:xx W:xx H:xx`** strip at the bottom-left writes only to the
  existing validated scanout RAM mapping. Each value is two **hexadecimal**
  digits. It works without printk or timer interrupts, if that scanout is still
  visible. Its renderer is bounded by the existing geometry/font validation.
  Text rendering reserves the bottom font row; the permanent mapping is kept
  for this opt-in RAM diagnostic even if the boot console unregisters.
  A later console/display owner can overwrite it: absence is NOT OBSERVED,
  not proof of zero. No display/GPU firmware command or new MMIO address.
* The first five-second watchdog report adds one interrupted-task stack and
  scheduler summary. At most six reports; normal completion cancels the timer.
  A softirq watchdog still cannot report if interrupts/softirqs/console stop.
  Printed task names are kernel boot threads; do not copy unrelated identifiers.
* Keep all previous hardware checks, arguments, the single clock-debug skip,
  DT, config, initramfs and m1n1 unchanged. **Only Image changes.** No change to
  CPU idle behavior, frequency, storage enablement or hardware routing.

## Read the observations

P is main phase, S the last scheduler checkpoint, W deferred worker subphase,
H heartbeat count. Capture the **sequence/last value**, not the numerically
largest phase: P progresses `01 → 0A → 0B → 0C → 0D → 02 ... 09`.

| P (hex) | Meaning |
|---|---|
| 01 | Counter/tick sample; inspect PASS/ticks/status |
| 0A | Tick sample passed; preparing watchdog |
| 0B | Watchdog initialized; entering mod_timer |
| 0C | Watchdog armed; about to enable preemption |
| 0D | preempt_enable returned |
| 02–09 | Original main phases: ready, debugfs, trigger, first flush, first return, second flush, second return, complete |

| S (hex) | Last scheduler boundary entered |
|---|---|
| 00 | No active scheduler checkpoint yet |
| 01 | __schedule entry, before scheduler debug/IRQ masking |
| 02 | About to acquire runqueue lock |
| 03 | Runqueue lock acquired |
| 04 | Entering task selection |
| 05 | Task selected; previous/next PID snapshot saved |
| 06 | Entering context_switch: preparation/MM/register switch |
| 07 | finish_task_switch entered, including newly created threads |
| 08 | context_switch returned to this scheduling frame |
| 09 | __schedule exit |

These are **last recorded boundaries, not fault diagnoses**. S=07 can be
normal for a newly created thread. Combine changing/frozen strip values with
P, heartbeats and the stack. W retains values 0–7 from the deferred-probe
experiment. H=01–06 is the number of heartbeat reports, not elapsed seconds.

If P=0C persists, S localizes the scheduling path even if no heartbeat arrives.
If heartbeats arrive, the first stack and current task can expose a stuck
worker/function. P=03 or later moves analysis back to normal deferred probing.
P=09 advances investigation to later initialization/userspace. A zero/absent
strip must not be interpreted as a register, task or timer failure.

## Validation and limits

[Job 028](../../../virtualization/jobs/028-schedule-boundary/README.md) builds
Linux 7.1.9 with the retained 16 KiB config, GCC 16.1.1/binutils 2.46.0 and two
build vCPUs. The actual helper tests verify pre-arming before reschedule,
default-inert behavior, scheduler snapshots, one stack maximum, finite timer
reports, shutdown and all inherited invalid timer/CPU/interrupt cases.
The actual renderer tests use ASan/UBSan with three font geometries, all four
lanes, padding/edge guards and rejected inputs. No test pretends to emulate M5.
Full link and ELF-to-Image comparison pass; linked scheduler/renderer call
inspection finds no printk/allocator/lock call (renderer has the compiler's
stack-canary failure path). [validation.json](validation.json) records results.

Exact packaged Image/initramfs in a diskless, networkless one-CPU/4 GiB VZ
reports `pending=1`, returns through phase 13, completes all phases and reaches
PID 1 / online_cpus=1 / 60-second liveness at **60.191892 s**. The VM reports
`strip=0` because it has no J716c framebuffer; physical strip visibility is
untested. Short successful initialization does not exercise the real five-second
watchdog: that callback is sanitizer-tested with controlled timer shims.
Timing/console instrumentation can alter the symptom. No efficiency gain or
native scheduling fix is claimed. An initial export job referenced a nonexistent
scheduler idle.o; it stopped, and the corrected ARM64 idle.o export succeeded.

Fresh post-attempt-8 user JSON: original Full/lab Permissive, both exit 0.
Independent root Macintosh HD/build 25G83/FileVault/SIP/staged m1n1 checksum
pass. No boot/security/volume/default changes; default/installed object and
authenticated-root were not independently queried again.

## Next

M1 follows the [current checklist](../../../tools/m1n1-client/stage-b-instructions.md):
verify private boot028, publish readiness, then one filmed human-started RAM
boot. Photograph/zoom the strip and review the recording **before reporting**.
Return to Macintosh HD within the unchanged bound. No repeated installation.
After stable native PID 1/liveness, prioritize a Linux USB/input control channel
and usable RAM root so the Linux-side agent can configure/test Omarchy. Native
GPU, all cores, power management and macOS-class efficiency remain separate work.
