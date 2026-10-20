# Resuming the main and side-session work

2026-10-19. Baseline `75411ec`; the remote main branch matches. Existing
uncommitted work was preserved. The user approved commit/push of the reviewed
attempt-27 handoff and separate offline CPU/SMP work on 2026-10-20. Hardware
experiments, boot-policy changes and volume changes are outside that approval.

**Completion:** job045's new image passed its VM desktop/link run; job051's
module, sanitizer and DT/schema checks passed; the recovered SMP findings are
written. Exact results and remaining limitations are in
[the side-session review](subagent-review-2026-10-19.md). The following track
descriptions record the work recovered. Subsequent job049 pairing and the
current handoff status are in [the attempt-27 validation](attempt27-two-stage-validation.md).

## Established state

Attempt 26, on boot042, ran Omarchy natively with the USB journal/SSH link and
working internal keyboard for 63 minutes 34 seconds. The desktop was slow:
about 0.47 seconds per full-screen update on one online CPU. Changing the repeat
delay to 1000 ms delivered 10 characters for 10 injected taps in the reported
test. This is a workaround for delayed release handling, not a rendering fix.
See [the native result](stage-b-2026-10-19-attempt26-result.md).

The actual CPU frequency, thermal margin, and effect of DVFS remain unmeasured.
The small-window comparison also leaves substantial frame cost. Extra cores
cannot be assumed to remove a serialized compositor bottleneck; GPU/display
work and controlled rendering comparisons remain necessary.

## Work recovered, with separate ownership

* **Image/job045:** finish the pending desktop fixes, keyboard startup and
  rerun handling, and SSH configuration; build and test the exact result.
  The first resumed build exposed an incorrect assumption that no user
  `shell.json` existed. Preserve the installer's existing five-section bar
  layout and every other setting when removing the weather widget.
* **CPU-frequency/job051:** review and compile an experimental module and
  candidate DT without modifying boot042 or the committed launcher. Unknown
  status-register reads, writes enabled by default, and false successful
  dry-run transitions are blockers in the interrupted draft. Requested state
  and command acknowledgement must remain distinct from measured frequency.
  No hardware execution or module loading belongs to this offline work.
* **SMP research:** recover existing REA evidence and produce behavior
  specifications with confidence and exact provenance. The macOS SPTM path
  does not establish raw-boot reset-vector ownership. Do not treat a
  macOS-specific sequence as a ready-to-run m1n1 implementation.
* **Main integration/job049:** retain the reviewed two-stage design, rebuild
  stage one only after the new root is pinned, then repeat the rejection,
  switch, desktop and link tests. Prior VM passes name the old root and
  cannot certify a new pair. Keep both images local; the repository is public.

## Attempt ordering and gates

1. Offline work and review are complete; commit/push approved on 2026-10-20.
   M1 verifies the published handoff and both private images, records offline
   readiness, then does the fresh-restart/cable procedure before the attempt.
2. **Attempt 27:** boot042 plus the new Omarchy root and two-stage delivery.
   Test automatic keyboard startup and a rerun, repeat delay and menu-process
   cleanup, transfer integrity, the root switch and USB reconnection. Automatic
   keyboard loading changes initialization timing from attempt 26; prior manual
   success is evidence, not proof of the new ordering. Do not add storage,
   cpufreq, secondary cores or a bootloader change to this experiment.
3. **Attempt 28:** the separately reviewed read-only-storage design remains
   queued. It is not a technical prerequisite for CPU work. If the CPU candidate
   becomes ready earlier, propose a changed order for the user's review; do not
   silently apply either launcher allowance.
4. **DVFS:** first establish the boot-core identity and baseline; use an
   explicitly bounded, reviewed state transition, independent frequency/work
   measurements, and thermal/power observation. Do not infer efficiency from
   higher throughput or requested state alone.
5. **SMP:** first obtain evidence for one additional core entering the intended
   code, then test heartbeat, interrupts/IPIs, timer behavior and shared-memory
   coherency. Expand to another cluster and then all 18 cores. DT/spin-table
   support alone does not establish working SMP; hotplug and deeper idle are
   separate experiments.
6. **Desktop/performance:** keep a software-rendering baseline and isolate
   layer, color-management and damage/presentation costs. Frequency and SMP
   progress can improve this baseline while GPU/DCP work proceeds. Compare
   latency, throughput, energy per task, idle power and sustained thermal
   behavior against macOS with the same workload.

Agents over SSH are already feasible and need not wait for a fast desktop.
Use the helper/build VM for expensive work; use the native machine for bounded
hardware observations. Native driver support is not established by a VM test.

## Still separate decisions

The storage launcher allowance, the third-party m1n1 contributor notice flagged
by the prior agent, and any transfer of extracted macOS artifacts to another
environment remain separate from this work. No proprietary code or raw REA
output goes into public files or releases. Continue local authorized analysis;
publish original implementation and behavior findings, with unresolved facts
clearly marked.
