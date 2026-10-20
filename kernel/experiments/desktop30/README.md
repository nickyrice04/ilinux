# Attempt30: attribute the application and typing delays

Attempt29's sampled memory attributes are normal, and actual huge-page backing
made little difference to its fixed-order random-load test. It did not identify
the cause of desktop delay. Attempt26 attributed long key-release queues to the
compositor's software drawing; attempt29 still used one M core near 2.65 GHz.
These are distinct observations, not proof that every delay has one cause.

## Executed plan and next native experiment

1. Review M1 report `1b1153d` and preserve its successful boot/images.
2. Use REA on this machine's CPU policy driver to distinguish presentation
   feedback, CPU placement and frequency requests; cross-check original bytes.
3. Test a specific rendering hypothesis offline. Disabling color management
   did not improve full-frame timing in the preliminary VM comparison, so do
   not ship that change or compromise display quality on that evidence.
4. Implement a small original Linux workload and bounded software CPU sampler.
   Validate them against the exact retained Omarchy userspace before shipping.
5. Run one native attempt with two controlled workloads and one 45-second
   human desktop observation. Attribute the delay before selecting the next
   CPU, compositor or presentation change. Native attempt30 remains NOT RUN.

No CPU-frequency request, voltage, controller, idle, core-start, module,
renderer-policy, boot-setting or persistent-storage change is part of this
attempt. There is no verified native speedup yet. The existing two-stage pair,
keyboard fixes, display resolution and current desktop settings are retained.

## Original implementation

* `frameprobe.c`: a normal Wayland SHM client, using standard xdg-shell. It
  opens its own fullscreen gradient window, validates the configured bounds,
  and closes itself. Two shared buffers are reused only after release. Twenty
  callbacks: four warm-ups (including full initial buffer damage), eight tiny
  16x16 updates and eight full-buffer-damage updates. It never injects keys or
  reads other windows. Same pixels, dimensions and CPU policy across cases.
* `samplecpu.c`: samples **only the compositor's main thread**, using Linux's
  software CPU-clock event at a requested 10 ms CPU-time period. No hardware
  PMU event. Kernel/hypervisor execution excluded. Instruction addresses stay
  in its RAM ring and are aggregated into compositor, Mesa, LLVM, anonymous
  executable, other executable file and unmapped categories. No addresses,
  memory contents, file paths or symbols are emitted. Newly generated code
  can be unmapped until the next one-second VMA refresh. Anonymous executable
  samples are not automatically attributed to Mesa.
* `collect.py`: native J716c/t6050, exact core/kernel/compositor, one-session,
  geometry, policy and asset checks precede work. Two frame workloads, then a
  45-second human window. Each phase records process CPU seconds, a bounded
  read-only IPC heartbeat, software samples and workload callbacks. Pre/post
  dependent-ADD clock estimates reuse the already verified CPU28 binary.
  `/run/ilinux-desktop30.started` prevents a repeat. Native client uid1000;
  sampler supervises only the identified compositor. Owned children are
  stopped on success, exceptions, timeout or termination. Partial CPU/IPC/sample
  evidence survives a workload or IPC timeout; completion is never fabricated.
* `receive.py`: exact archive/member/size/hash verification, then extraction
  only into verified `/run` tmpfs. No tar path, permission or owner restoration.
  Root-owned directory is made traversable for the unprivileged client after
  verification; source stays mode600, executables755. No native module ships.

The CPU event can be unavailable (for example ENODEV/EPERM). Preserve its errno
and use the remaining observations; do not enable a kernel feature, relax
security, substitute a hardware event or claim sampling succeeded. Invalid
sample-ring data, compositor restart, failed IPC, resize, incomplete frame
workload or a changed policy stops collection, with no retry.

## Interpret observations narrowly

A Wayland callback permits a client to prepare another frame; it is **not** a
physical presentation timestamp. IPC round-trip measures event-loop service,
not keyboard hardware, application launch or photon latency. Process CPU time
includes all compositor threads; sample categories cover the main thread only.
The controlled fullscreen client does not reproduce the full menu/terminal
composition scene. Its fast/slow contrast needs the separate human phase.

Clock estimates assume one cycle per dependent ADD. They are not hardware
clock telemetry or energy measurements. Power, temperature, efficiency and
OS parity remain unknown. The 100 ms IPC heartbeat and sampler add work; keep
sampling settings fixed, retain lost/unmapped counts, and compare like phases.

| Native observation | Next engineering action |
|---|---|
| Tiny updates fast, full damage slow; real desktop resembles full damage | Trace actual client damage and compositor damage expansion; preserve pixels and fix excess redraw/copy work before changing frequency. |
| High compositor CPU and anonymous/Mesa samples, long IPC queues | Confirm generated-rasterizer attribution, then target the expensive draw path and CPU capacity. More cores do not automatically parallelize the event loop. |
| Long wall/IPC delay with little compositor CPU | Investigate scheduler contention, synchronization and presentation waits; a frequency increase is not an established fix. |
| CPU sampler unavailable | Preserve errno; callback/IPC/CPU-time evidence still counts. Add kernel support offline as a separate change if necessary. |
| Fault, unexpected state, unstable clock or missing completion | Stop and return to Macintosh HD; retain private evidence. |

## CPU parity path informed by REA

See [REA findings](../../../native/boot/attempt30/rea-findings.md). The Linux
counterparts are existing scheduler utilization feedback, capacity-aware
placement and performance hints. The repo already has a QoS-slice prototype;
it must not be represented as a working native frequency controller.

The physical CPU track remains: establish one secondary's entry/park contract,
validate one same-cluster secondary with timer/IPI/coherency checks, then a P
cluster, then all 18 cores. Separately establish bounded frequency transitions
and usable thermal observation; then validate capacity/frequency invariance,
schedutil and per-task hints against measured frame deadlines and energy.
Avoid copying Apple's policy constants or assuming a proprietary call graph is
a complete Linux implementation. GPU acceleration remains an independent
requirement for macOS-class desktop performance and efficiency.

Reproduce offline with job054 and the existing VM runner as documented in
`native/boot/attempt30/validation.md`. M1 procedure:
`tools/m1n1-client/attempt30-instructions.md`.
