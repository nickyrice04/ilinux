# Attempt31 HOLD — trace the seconds of delay first

2026-10-21. The user rejects the current copy-only boot proposal as insufficient
for menus and typing that take 3–5 seconds. **Do not launch attempt31, send its
root, run its collector, or ask the user to restart for this candidate.**
Preserve its code, images, measurements and pins as an optional later comparison.
No revised native experiment is ready or authorized by this planning update.
This hold supersedes the earlier handoff and its readiness instructions.

Execution follow-up: [diagnosis and measured references](diagnosis/README.md),
[original instrumentation](../../../kernel/experiments/latency31/README.md),
and [M1 hold notice](../../../tools/m1n1-client/attempt31-diagnosis-update.md).

## What the evidence actually says

* Attempt26's independent input reader measured kernel-event-to-reader lag
  from 0 to 5.2 ms over 157 events. Key actions nevertheless triggered 0.8–6.1s of
  CPU activity, mainly userspace; the terminal itself used little CPU. This
  points downstream of Linux input delivery. It does not measure the physical
  switch/firmware-to-kernel interval, establish current input latency or prove
  the keyboard driver fault-free.
* Attempt26's release IPC queued about 0.47s even with corrected repeat delay;
  stopping pollers and disabling animations did not eliminate it. The repeat
  fix improved accuracy without removing the underlying draw/event-loop cost.
* Attempt30's compositor consumed about 97% CPU in controlled workloads, with
  roughly 256 ms tiny-damage and 515 ms full-damage callbacks. Its human-phase IPC
  median was fast, but the maximum was 897 ms. Neither IPC nor callback time is
  a complete physical-key-to-menu measurement. Menu/terminal/file-manager
  action times were not recorded. We have not accounted for the reported 3–5s.
* CPU0 is one M core; 17 of 18 cores remain offline. A dependent-ADD estimate near
  2.65GHz and a mapped requested state do not establish instruction throughput,
  scheduler/idle/thermal behavior or macOS parity. Graphics and desktop clients
  contend with software rasterization on that single core.
* Memory29 observed normal sampled cache attributes and real huge backing.
  Its random-load latency is not sequential bandwidth, memory-controller clock,
  full-cache/coherency validation or GPU-memory performance. Memory is not
  cleared as a contributor. Existing macOS references differ in placement,
  QoS, frequency and compiler; their differences cannot be assigned to the OS.
* Copy31's approximately 25% VM callback improvement concerns one rendering path.
  It neither explains the missing seconds nor establishes the next native boot
  is worth the user's time. Preserve it; remove it from the critical path now.

Sources: `../stage-b-2026-10-19-attempt26-result.md`,
`../stage-b-2026-10-20-attempt29-result.md`,
`../stage-b-2026-10-20-attempt30-result.md`, `validation.md`.

## Revised work, before another restart

1. **Build an event-to-visible-action timeline.** Reuse the existing input-reader
   evidence but add bounded timestamps at the actual Hyprland keyboard callback
   (`CInputManager::onKeyboardKey`), binding dispatch, shell/menu request and
   application startup, first surface commit, rendering start/end and display
   submission. Instrument the pinned original source, with copy31 disabled.
   Use a single verified monotonic clock and action sequence numbers; store no
   arbitrary typed text, window titles or personal data. Measure observer cost.
   Kernel event receipt and a Wayland callback are not physical presentation:
   use filmed keypress/screen timing for that boundary and preserve alignment
   uncertainty. If firmware delay remains plausible, add an MTP/DockChannel
   receive timestamp in a separately built probe; do not guess from evdev alone.
2. **Separate paths in one bounded diagnostic.** Compare a physical shortcut
   with the same menu command invoked directly in the existing user session;
   this bypasses the keyboard and shortcut dispatch, not necessarily the shell
   or compositor. Separately test a minimal client beside the real menu and
   terminal. Record cold and warm launches, CPU running time versus wall time,
   runnable/wait time where available, per-layer rendering costs and pixels
   damaged. Inspect D-Bus/portal/service waits only if the timeline points there.
   Existing warnings and full-screen overlays are hypotheses, not assigned causes.
3. **Establish CPU and memory execution baselines.** Reuse original portable
   fixed-work integer/NEON, dependent-load and explicit streaming-loop tests.
   Compare the same work/size/thread count with and without desktop contention.
   Record compiler flags and generated inner loops, checksums, faults, context
   switches, CPU placement, clock estimates and cache-sized versus larger sets.
   Do not toggle architectural cache/security controls. On macOS, QoS is a
   placement hint, not proof of exact core affinity; label unmatched samples.
   Compare one thread first and normal multicore macOS separately. Sequential
   copy/read/triad bandwidth and random latency answer different questions.
4. **Make a native macOS software-rendering reference.** A CPU-only offscreen
   pixel workload requires no GPU. For rasterizer-specific comparison, use the
   same pinned Mesa/LLVM llvmpipe, workload, dimensions, formats and thread limit
   on each OS, with checked pixels. Mesa documents macOS software-driver builds;
   LIBGL_ALWAYS_SOFTWARE affects compatible Mesa applications, not WindowServer
   or every Metal application. Offscreen results isolate CPU/rasterizer behavior
   but do not reproduce the macOS desktop compositor. Use existing workspace
   tools; any needed host installation/execution permission remains separate.
5. **Select the fix from the measured interval.** Late kernel arrival points to
   firmware/transport/input; prompt kernel input but late compositor receipt to
   dispatch/starvation; late app readiness with low CPU to startup/IPC waits;
   prompt app commits but long rendering to layers/rasterization/copies; slow
   standalone compute/memory to CPU/cache/controller state. Use REA on the
   specific Apple MTP/PMGR/DCS behavior only where that evidence leaves a
   hardware question. Cross-check instruction boundaries and independent bytes.
   Native multi-core startup remains a major implementation track regardless;
   additional cores alone do not guarantee a responsive serial event loop.

## Release criteria for a replacement handoff

A replacement must explain which intervals it measures, pass offline tests,
retain existing working boot/input/USB behavior, and fit the original bounded
return window. Keep physical/native results NOT RUN until observed. No boot,
security, firmware, frequency, memory-controller or storage changes are part
of this hold. Routine policy checks remain waived.

The user-facing target is prompt key echo, menu visibility and application
readiness, compared with matched actions on macOS. Report medians, tails and
cold/warm cases; do not accept a relative shader improvement as the workstation
acceptance criterion. Treat SMP, GPU, thermal/idle, Wi-Fi and storage as explicit
remaining requirements rather than reasons to dismiss the current seconds.

## Primary-source notes for the comparison

Apple's integrated GPU uses unified memory; “integrated graphics” still means
GPU execution, while CPU-only drawing is software rendering. There is no
separate dedicated VRAM clock to validate on this unified-memory design.
[Apple unified-memory API](https://developer.apple.com/documentation/metal/mtldevice/hasunifiedmemory).

[Mesa macOS build notes](https://docs.mesa3d.org/macos.html) describe selecting
software Gallium drivers, including llvmpipe. [Mesa environment variables](https://docs.mesa3d.org/envvars.html#libgl-environment-variables)
document its per-application software-rendering selector. These are not a
systemwide macOS GPU-disable command. No such system modification was made.
