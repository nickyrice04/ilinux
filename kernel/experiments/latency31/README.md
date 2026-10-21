# Trace the seconds before revising attempt31

**Offline work only. Native attempt31 remains HOLD.** These tools do not
change CPU registers, clocks, kernel, boot policy, storage or firmware.
The current copy31 images and launcher must not be used for this work.

## What the code measures

* `apply.py` validates seven exact original Hyprland source files, then adds
  CPU-side scopes for input dispatch, bindings, buffer commits, scene/element
  drawing, texture work, final copy, the existing GL completion wait, and
  output submission. Normal tracing adds no GL wait. Copy31 is absent.
  A separate VM diagnostic, `ILINUX_LATENCY_DRAIN=1`, adds explicit finishes
  after the scene and final copy to separate deferred rendering costs. That
  changes batching and is **not** a proposed optimization or native default.
* `ILinuxTimeline.hpp` is disabled unless `ILINUX_LATENCY_TRACE=1`. It opens an
  exclusive, no-follow, mode0600 file in the uid1000 RAM runtime directory,
  only when an instrumented function actually runs. This matters because
  `start-hyprland` invokes a preliminary information query. It records the
  main thread only, at most100,000 entries, and no keycodes, text, titles or
  addresses. Each scope has monotonic start/end and thread CPU time. Arguments
  are dimensions, input timestamp/state or the local client process ID.
* `input_clock.py` independently reads an explicitly selected evdev device for
  at most60s/4096key events. It selects CLOCK_MONOTONIC for that descriptor and
  records event/reader timestamps and press/release/repeat states, never which
  key was typed. It does not grab or inject input. This bounds kernel-to-reader
  delivery, not physical-switch-to-kernel delay.
* `baseline.py` compiles the existing original CPU and STREAM benchmarks and
  `pixels.c` with recorded source hashes/compiler/flags. One thread, bounded
  runtime, at most384MiB of STREAM arrays. macOS default/background are separate
  observations; QoS is not exact-core affinity. The Linux VM is explicitly
  labeled. No DIT/cache/security control is changed.
* `pixels.c` supplies a genuinely CPU-only reference with no graphics API:
  full-size copy and premultiplied-alpha composition into ordinary RAM, with
  checked pixels, per-sample wall/CPU/fault/context-switch counters. It is not
  a substitute for matching Mesa/LLVM shaders or macOS WindowServer.
* `analyze.py` rejects malformed/empty/saturated traces and summarizes each
  stage separately. Nested stages overlap and must **not** be added together.
  First buffer commit is application progress; neither it nor a frame callback
  proves screen presentation.

## VM reproduction

Use the existing development disk and the already pinned attempt28 root.
Job056 builds in guest tmpfs and never modifies the held candidate's source or
images. Its exact dependencies are those of job055. Compiler: GCC16.1.1;
Release/O3, NO_HYPRPM, pinned original Hyprland commit
`efb50993780079460b0cbed1363e2166a2de1d9f`. It uses a thin static archive to avoid
duplicating object files. Check `out/run.log`'s **guest exit**, not just vzrun's
exit code.

Set `virtualization/jobs/056-desktop-timeline/out/mode` to `build`, then run
`tools/vm-job.sh virtualization/jobs/056-desktop-timeline timeline31`.
For the workload set mode to `bench`, acquire the shared quiet lock, and run
the same job with `VZRUN_EXTRA='--gui --size 3456x2160'`. Release the lock after
the VM exits. Outputs are ignored; no raw desktop logs enter Git.

The workload starts the installed Quickshell explicitly in the disposable
chroot session, verifies shell IPC, and invokes real menus and foot. It uses
one guest CPU, software rendering, native pixel dimensions and animations
unchanged. A quarter-pixel control is diagnostic, **not** a proposed native
resolution change. The output is headless and cannot measure panel scanout.
Modes `parallel` and `blur` run separate sensitivity tests. The former allows
the compositor on six guest CPUs with four configured llvmpipe workers while
clients stay on CPU0; it is not native SMP validation. The latter performs a
blur-setting crossover in the guest and restores its original value; it is
not a proposed reduction in visual quality. Normal `bench` also runs a
separate fixed-scene observer control without the Omarchy shell.
Compare trace disabled/enabled; account for background layer changes before
ascribing a difference to observer overhead. A single pair is exploratory.

## Native replacement gate

Do not package this as a performance fix yet. A replacement needs pinned
artifacts, a bounded collection/restore path, confirmed tracing overhead and
an M1 checklist. Native comparison must collect these same compute/memory
workloads both idle and alongside the desktop, then physical shortcuts versus
direct commands, first buffer commits and rendering/submission. Film the
keypress/display boundary if possible; preserve alignment uncertainty. Keep
keyboard accuracy and working USB transport. Native tests remain NOT RUN.

Success is responsive key echo and cold/warm app/menu readiness measured in
absolute time, including tails. A relative improvement in one shader does not
meet that criterion. Native SMP and G17 acceleration remain implementation
priorities; a slow serial drawing loop can remain unresponsive with more cores.
