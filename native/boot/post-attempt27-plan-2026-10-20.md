# After attempt 27: make this M5 a usable Linux workstation

**2026-10-20 implementation update:** the user authorized CPU experiment
preparation and publication. Attempt 28 now implements the no-write first
stage of this plan: exact profile/image pairing and bounded collection.
Frequency increases remain deferred until the command/state/thermal evidence
is observed. See [validation](attempt28/validation.md) and
[M1 handoff](../../tools/m1n1-client/attempt28-instructions.md).


2026-10-20. Based on M1 report `cf4e739`, the user's subsequent desktop
observations, and the existing offline CPU, storage and N1 work. This is the
current planning order, superseding the earlier fixed assignment of storage
to attempt 28. **Attempt 28 is proposed CPU work, not a ready boot package or
an authorization to run it.** No launcher, image, hardware or settings change
is made by this review.

## User's acceptance target

Before moving their main development and REA workflow into native Omarchy,
the user wants full CPU capability with macOS-class performance and efficiency,
independent built-in Wi-Fi with a working browser, and fast persistent storage.
Access to existing macOS files is also desired. Treat these as acceptance
targets, not optional polish after an agent can log in. Other peripherals can
follow; graphics remains relevant because it directly affects responsiveness
and energy consumption. Keep the original macOS installation intact.

## What attempt 27 actually established

The [M1 result](stage-b-2026-10-20-attempt27-result.md) confirms one native
two-stage boot, verified root transfer at 28.1 MB/s, a successful root switch,
the second USB/SSH link, automatic keyboard startup and a successful rerun.
The user typed `omarchy` without extra letters and reports substantial delay
opening menus, terminal and the file manager. The repeat-delay workaround is
effective for this observation; it does not establish low input latency.

The machine still runs one CPU, renders in software at 3456×2160, and uses a
RAM filesystem. No native SSD or built-in Wi-Fi was tested. The six-second
idle sample was 1% busy; there is no new clock, frame-time or power measurement.
Attempt 26's approximately 0.47-second screen update remains separate evidence.
The current `idle=nop arm64.nowfxt` configuration means low accounted CPU use
cannot establish low idle power. Reported display refresh is not delivered FPS.

Do not discard earlier native measurements: [attempt 20](stage-b-2026-10-16-attempt20-result.md)
reported a 2.65 GHz dependent-instruction estimate, 29.8 GFLOP/s assembly FMA,
28.2 GB/s STREAM copy and 617 ns at the 128 MiB pointer-chase working set.
Those were on an unidentified single core with competing software rendering,
GCC 16.1.1 and `-O3 -march=armv8.4-a`, on an older image. They are useful
diagnostic evidence, not a current boot042 clock or matched macOS comparison.
Repeat short cache/DRAM tests under controlled conditions as well as CPU work;
the old memory-latency result merits investigation and should not be attributed
to frequency, core type or the PMGR warning without evidence.

Menu-poller cleanup is inconclusive, and the PMGR `cs` initialization failure,
three failed services, stage-one sshd noise and teardown warnings remain open.
Do not classify the PMGR error as harmless merely because the desktop ran.
The user returned to Macintosh HD. Routine policy rechecks remain waived;
original Full/lab Permissive are last reported, not newly verified.

## Priority and implementation sequence

| Track | Current evidence | Next useful implementation | Native evidence needed |
|---|---|---|---|
| CPU frequency | Original guarded driver, DT generator and job051 compile/model/schema tests pass; no native load or rate measurement | Integrate an isolated CPU profile and paired images, with a bounded measurement runner | Boot-core identity/state, independently estimated clock, useful work rate and menu/frame latency before/after a reviewed request |
| All CPU cores | Kernel already has SMP; runtime is restricted to one CPU; REA identifies a start-mask defect but raw secondary entry is unresolved | Finish one-secondary entry diagnostics and descriptor-based masks, then Linux timer/IPI/coherency support as evidence requires | First instruction, stable park, timer, bidirectional IPI, shared-memory correctness, then cross-cluster and all 18 cores |
| CPU efficiency | Deep idle avoided for state-retention reasons; native power/thermal measurement incomplete | Establish telemetry, then bounded idle/resume, scheduler placement and governor integration | Energy per task, idle power, thermal behavior and sustained throughput as well as speed |
| Built-in Wi-Fi | N1 operational metadata and original software queue helpers exist; no native WLAN transport | Resolve PCIe/DART and ACIPC descriptor/ownership/control contracts, then original Linux transport and cfg80211/netdev integration | Scan, associate, DHCP, DNS, HTTPS browser, local-network throughput, reconnect and power-save behavior |
| SSD and persistence | Read-only NVMe module set passed VM refusal/data-integrity tests; Apple controller untested | Rebase the storage profile onto two-stage delivery and test ANS/SART/NVMMU initialization read-only | Controller/namespace enumeration, repeatable reads and no faults; later separately authorized Linux scratch writes and durability |
| Interactive graphics | Software renderer active; previous full-screen work is expensive | Measure input-to-present and rendering/presentation cost alongside CPU tests; use the results to target G17/DCP work | Cold/warm app-open latency, menu latency and frame-time distributions at unchanged display settings |

CPU work leads the next native experiment because it has a compiled candidate
and benefits both the desktop and all later tools. N1 research and storage
preparation need not wait for the CPU to reach parity. Keep each new hardware
initialization path separately attributable; do not combine DVFS, SMP and
storage enablement in one first test. Do not require every CPU research question
to be solved before taking a ready, useful storage or network measurement.

## Proposed attempt 28: CPU baseline and controlled frequency work

The next deliverable is a reviewed CPU experiment package, retaining the
working two-stage delivery, keyboard and USB path. Before asking for a restart:

1. Integrate the existing [cpufreq candidate](../../kernel/experiments/cpufreq-t6050/README.md)
   into a separate launcher profile. Pin Image, module, input DT, root and
   stage-one pair; validate the final m1n1-prepared DT too. Keep storage
   disabled, one CPU online and the existing idle restrictions. Existing
   profiles must continue rejecting the CPU experiment.
2. Package a short collector using the existing measurement helper and CPU
   benchmarks. Record core identity/MPIDR, topology, command line, requested
   state, available temperature/power data, independent work rate, short
   cache/DRAM measurements and render latency. Missing telemetry is missing,
   never zero. Include the incomplete
   menu after-check without turning this into a broad desktop configuration run.
3. Resolve governor behavior before enabling writes: boot042 defaults to
   schedutil, which can request transitions when the driver registers. Establish
   the controlled governor at registration, rather than relying on a later
   userspace change. Preserve default-no-write loading and immutable state caps.
4. Test profile refusals, exact image pairing, module loading/control behavior
   in the VM where meaningful, and baseline collection. Model/VM tests cannot
   confirm this hardware's clock or thermal behavior. Reuse existing results
   where the relevant artifacts have not changed.
5. Publish exact instructions and bounded outcomes. First collect a no-write
   baseline. A transition in the same boot is permissible only if its state,
   monitoring requirements and cap were explicitly covered by the reviewed
   attempt and the observed baseline satisfies them. Otherwise keep the run
   diagnostic and use its evidence for the next package. Do not invent a cap
   live, jump to maximum frequency, or treat command acknowledgement as a clock
   measurement. No sustained load without the required thermal observation.

Use the dependent-ADD clock estimator with its one-cycle-latency assumption
stated, corroborate it with fixed-work throughput, and add a PMU reference when
validated. Compare the same core and build before/after, with short runs and
cooldowns. If frequency is already high or the bottleneck is elsewhere, record
that outcome and prioritize the measured cause instead of forcing a DVFS story.

The report's collector mistake and timing overrun are preparation tasks:
key verification must gate collection in a checked process, and an independent
deadline must end observations even while an agent reviews evidence. Neither
fix requires another policy check or changes to the boot entry.

## SMP and REA: answer the remaining startup question

The inventory describes 18 cores in three groups of six: 12 M and six P cores.
Identify the actual boot core; do not assume it is an efficiency core. Boot042
already has `CONFIG_SMP=y`; changing a core-count setting alone does not start
the hardware.

The [recovered startup findings](../../reverse-engineering/findings/cpu-startup-2026-10-19/README.md)
establish that m1n1's four-bit start-mask stride aliases cores in the six-core
clusters. They also establish that correcting that arithmetic cannot explain
the failure of a secondary in the first cluster, where the bit is unchanged.
The next specific REA question is the raw-boot secondary entry/early-state
contract: which component sets the entry and what must the first Linux-owned
instructions establish? Use PMGR/platform findings, m1n1 source, sanitized ADT
and bounded, independently checked disassembly. A macOS SPTM entry sequence
does not establish the custom-boot ABI and must not be replayed into Linux.

Prepare a reviewed read-only census and one-secondary first-instruction
heartbeat; then prove stable parking, timer delivery, bidirectional IPIs and
coherency before using the scheduler. Expand within one cluster, across cluster
types and finally to all 18 cores. Idle, hotplug, scheduler capacities and SME
context handling have their own correctness/performance checks. All-core
online status alone is not CPU parity.

## Networking: build the N1 path, retain the relay for experiments

Attempt 25 demonstrated web access through the M1 relay. Attempt 27 did not
exercise browser traffic; neither result is built-in Wi-Fi. The N1 track must
deliver an independently working connection on the M5.

The [ACIPC contract work](../../kernel/experiments/driver-contracts/acipc/README.md)
contains tested software bookkeeping, not a hardware transport. Target REA at
the actual DriverKit-cache implementations and AirshipDK/Centauri components;
the previously inspected dext executable files are stubs. Resolve descriptor
layout, buffer ownership, completion/phase/index semantics, DMA visibility,
doorbells, normal firmware initialization and WLAN control/events. Do not
infer descriptor stride from a metadata footer size or assume all rings have
power-of-two sizes. PCIe enumeration and DART mappings precede packet I/O.

Turn each verified contract into an original Linux component with malformed
input and ownership tests. Native success advances from enumeration to control
messages, scan/association, IP service and a browser. Measure against macOS on
the same AP/band/signal using a local endpoint, including reconnect and power
save; an internet speed test alone cannot isolate driver performance.

## Storage: distinguish controller speed, persistence and macOS files

Keep the [read-only ANS experiment](../../kernel/experiments/nvme-ans3/storage-ro/README.md)
ready behind CPU work. Its VM tests prove important software refusal paths,
not that the real Apple controller boots or that experimental drivers cannot
have bugs. The earlier private launcher draft predates two-stage delivery and
must be rebased/reviewed. First prove ANS startup, DMA mappings, queues and
repeatable bounded reads with automount suppressed. No filesystem mounting is
needed for that milestone.

Next, separately plan a dedicated Linux workspace and read/write benchmarks
with matched queue depth, caching and flush/durability semantics. Choosing or
creating persistent storage, enabling writes, and native installation require
their own concrete authorization; this plan does none of them. Keep originals
and backups outside experiment write targets. A fast RAM-root result cannot
be called SSD performance.

Reading existing macOS files adds APFS and the platform's unlock path. Apple
documents hardware-bound internal-volume encryption and Secure Enclave key
handling; an NVMe driver plus a general APFS reader does not establish access
on this machine. This dependency is an inference from that architecture and
our absent native unlock implementation, not a claim to have tested a mount.
See [Apple's volume-encryption documentation](https://support.apple.com/guide/security/volume-encryption-with-filevault-sec4c6dc1b6e/web).
Do not make direct macOS-volume access a prerequisite for Linux development.
Selected, user-approved research inputs can instead be staged privately while
macOS is running; their availability is independent of reading its live volume.

## Measurements and the Linux-side agent

Define parity by comparable results: single-core and all-core work rate,
memory bandwidth/latency, scheduling/wakeup latency, interactive response,
network throughput, durable SSD I/O, idle watts and joules per completed task.
Record hardware/core identity, software/source hashes, compiler flags, power
source/mode, display settings, thermal starting state, repetitions and spread.
The existing headline macOS baseline used Low Power Mode on AC; preserve that
label and establish the intended everyday-use reference before claiming parity.
SME builds must respect the recorded SME-only/non-streaming-SVE distinction.
VM scores remain separate from native results.

REA/Ghidra already works in the project's Linux VM, so analysis of ARM64 macOS
artifacts does not require macOS as the analysis OS. The eventual native setup
needs a private persistent corpus/project, a reproducible toolchain, working
networking and reliable CPU resources. Keep Apple artifacts and raw decompiler
output private; publish behavior findings and original code. The present RAM
root loses unsaved work on reboot, so interim agent sessions require explicit
checkpoints through the existing helper link. Do not move the main workflow
there merely because an agent can connect.

The next restart follows a completed, independently verified CPU handoff, not
this plan. Attempt 27 remains consumed. Later attempt numbers follow actual
readiness and results rather than a promise that one boot will solve each
subsystem. The M1 can read this plan now; there are no new live commands to run.
