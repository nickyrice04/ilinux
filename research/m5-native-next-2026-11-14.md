# Native M5 Max direction after 31AJ — November 14, 2026

## What this attempt establishes

31AJ did not reach candidate enrollment, transaction-baseline creation or Linux.
The reported failure is our Recovery workspace pathname meeting our own
descriptor-based no-follow reader: `/private` is a system symlink in the observed
Recovery layout. The original source and result are preserved in
`native/boot/attempt31aj-capability-refusal-2026-11-14.md`. Correcting this path
handling is the immediate engineering task. It does not require an Apple CPU
firmware change, a new kernel, disabled path checks or renewed low-level startup
experiments. Later native admission and entry remain untested.

The report confirms Macintosh HD desktop and default return by the human.
It explicitly marks boot021 restoration **NOT RUN**. Do not turn desktop return
into a claim that the lab object is boot021. Root owns any read-only object
identity reconciliation; this note makes no live query or host change.

## Current primary-source refresh

**Vendor statement, not our physical result:** Apple's current macOS 27.3 beta
notes still list the M5 Pro/Max/Ultra single-core custom-raw-object issue as fixed,
under 182898702 / FB23916610. This supports retaining a raw route as an alternative;
it neither requires a vendor update for the current path correction nor proves
the installed 25G83 loader has the fix. No firmware action is proposed.
[Apple release notes](https://developer.apple.com/documentation/macos-release-notes/macos-27_3-release-notes).

**Attributed same-board evidence:** the November 11 J716c report remains the
newest comment visible in the hardware discussion on this refresh. It names the
same Aura `bd9f3e8273dc` / Linux `dc8f6f77934b` pair, 27.2.1/26B131 firmware,
18 online CPUs, NVMe partition reading and N1 networking/SSH; its display is
simpledrm. This motivates testing our already-built pair, with the firmware
difference retained as an uncertainty. It is not our performance result or a
complete reproducible GPU bundle.
[November 11 board report in the hardware discussion](https://github.com/aurora-silicon/linux/discussions/142).

**Official upstream status is distinct:** Asahi's current M5 table still lists
the relevant T6050 subsystems as TBA and its installer as unavailable. Aurora's
fork work and board reports must not be relabeled an Asahi-supported release.
[Asahi M5 matrix](https://asahilinux.org/docs/platform/feature-support/m5/).

**New source, different execution path:** Aura merged SPTM-virtualization PR70
on November 14, merge `f6aad3a0164240600e9b2028c3b5dc6a4f9b0740`. Its development
history reports a T6050 J714s macOS guest using all 18 cores, with build-specific
and final-head hardware limits. This is macOS running under an experimental
hypervisor, not direct Linux SMP qualification or a full hardware emulator.
It is a possible future source of carefully scoped architectural observations;
do not deploy it or transplant firmware patches as part of this repair.
[Aura PR70](https://github.com/aurora-silicon/aura/pull/70).

The specific CPU fix `6749cbb7e1193d0b6584ee5ec4d2c1221921a2d8` constructs
guest-reset affinity using the boot CPU's Aff2 for its own ADT core class.
The implementation is used by `smp_prepare_guest_resets`, the virtualized-SPTM
reset path. It is **not** a demonstrated fix for our direct Mach-O Linux boot.
Its reported T6050 affinities agree with our existing static DT; blind rebasing
or cherry-picking before the first native diagnostic would mix independent
variables without addressing 31AJ's observed failure.
[Exact public commit](https://github.com/aurora-silicon/aura/commit/6749cbb7e1193d0b6584ee5ec4d2c1221921a2d8).

**GPU path worth preserving:** PR1276 remains merged on November 12 as
`c31d5805ae72283319538a282fc88080706801ff`, with prerequisites 1012/1275.
The owner reports G17C/Vulkan/Hyprland internal-panel operation with a matching
loader/DT/Mesa stack. Its GPU-to-CLPC connection raises DRAM/fabric demand during
GPU work; the owner reports a GPU-memory test improving from 89 to 292 GB/s.
Those numbers are attributed, not measured here. The exact complete tested stack
still has to be pinned before enabling it in this environment.
[GPU/internal-panel PR1276](https://github.com/aurora-silicon/linux/pull/1276).

The newer November 14 G17 synchronization PR1892 and traversal-admission PR1893
are explicitly scoped to the A18 Pro/G17P path and state that M5 is unchanged.
Their performance or correctness numbers are not M5 Max improvements.
[PR1892](https://github.com/aurora-silicon/linux/pull/1892),
[PR1893](https://github.com/aurora-silicon/linux/pull/1893).

## Exact topology to validate

The local sanitized ADT and existing direct31AH DT checker agree on three
six-core clusters. These are architecture/core-class identifiers, not per-unit
hardware identifiers. ADT register values omit Aff2 and must not be substituted
for complete MPIDRs.

| ADT CPU IDs | ADT class / compatible | Cluster | Raw ADT reg | Expected MPIDRs |
|---|---|---:|---|---|
|0–5|M / apple,sawtooth|0|0x0–0x5|0x40000–0x40005|
|6–11|M / apple,sawtooth|1|0x100–0x105|0x40100–0x40105|
|12–17|P / apple,everest|2|0x200–0x205|0x10200–0x10205|

Thus the target is 12 M-class and 6 P-class physical-core identities, historically
called Performance and Super in this project. Do not infer an efficiency-core
class from a familiar M1 naming convention. Linux logical CPU numbers must be
mapped through the live DT identity, not assumed equal to ADT IDs.

The current direct DT's capacities are 794 for M and 1024 for P. They are
**uncalibrated static values**, not measured relative speed or macOS scheduling
parity. The older 31F experiment used 768 for M; that older value is not the current
candidate. References: `hardware/adt/adt-sanitized.json`,
`kernel/experiments/direct31ah/linux/check_dtb.py`,
`kernel/experiments/direct31ah/linux/README.md` and
`kernel/experiments/cpu-topology31f/README.md`.

One focused November 14 read of the actual frozen diagnostic DT using the
existing original `check_dtb.py` returned `OFFLINE_STATIC_DTB / PASS`, with
these 18 MPIDRs, capacities 794/1024 and spin-table release placeholders. This
does not qualify runtime release addresses, cache visibility or online CPUs.

## Shortest sequence toward a usable Omarchy workstation

1. **Fix and qualify Recovery deployment, retaining the existing candidate.**
   Canonicalize and bind only the newly created owned workspace before deriving
   helper/profile/snapshot paths. Preserve no-follow rules. Test both full phase
   blocks with the actual observed system-alias layout. This is a launcher fix,
   not a reason to rebuild the kernel or perform a firmware update.
2. **Get the first native result from the matched direct-boot pair.** The
   existing diagnostic already records online CPUs, DT MPIDR/MIDR/capacity,
   cpufreq telemetry when available, one pinned checksum worker per CPU, actual
   executing CPU, overlapping intervals, timers, 64 MiB RAM integrity and 60-second
   liveness. Require 18 distinct expected core identities and 18 successful
   overlapping workers; absence of USB logging is a separate outcome. A static
   tree or 18 online bits alone is insufficient. Preserve the external 90s cap.
3. **Measure CPU and memory before tuning scheduler values.** In a separately
   reviewed subsequent healthy Linux batch, reuse `benchmarks/src/cpubench.c`
   for fixed-work 1/6/12/18-thread scaling, one-core-class and cross-class loads,
   and within/across-cluster ping-pong. Reuse `membench.c` for working-set sweeps,
   aggregate streaming bandwidth and random-chase latency. Read frequency-policy
   membership and clocks beside results. The current 64 MiB checksum is not proof
   of full RAM speed. Check sustained throughput, thermal behavior and joules
   per completed task against the macOS reference with the same work/compiler
   settings. macOS QoS is not true physical-CPU affinity; report that comparison
   limit instead of pretending both kernels pin identically.
4. **Establish an agent control channel and read-only storage inventory.**
   N1/DHCP/SSH and ANS/NVMe have same-board public evidence, but the diagnostic
   deliberately excludes built-in storage and does not prove these interfaces
   here. Adopt a pinned coherent platform stack and qualify network reliability,
   read-only storage, then disposable-file speed tests on explicitly approved
   Linux storage. FileVault/APFS access to existing macOS personal data is a
   separate feature, not implied by raw NVMe support or equal SSD speed.
5. **Enable the matched G17C/display/Mesa stack and reuse Omarchy's existing
   root.** Pin all loader/DT/kernel/modules/Mesa prerequisites together, then
   measure input-to-frame tails, menu/app startup and frame pacing. This is the
   route to eliminating software-rendering overhead; additional CPU cores alone
   do not guarantee a smooth Retina desktop. Make an authenticated Linux-side
   agent useful once network and a stable desktop/control channel actually work.
6. **Qualify efficiency independently.** Idle power, energy per task, CPU idle,
   thermal limits, suspend-to-idle and deep suspend/resume are distinct results.
   GPU/memory demand voting, frequency invariance and heterogeneous placement
   matter, but no capacity constant or all-core counter establishes parity.

## REA decision and evidence limits

No new decompilation is necessary to explain this own-source pathname failure.
The next useful REA question depends on a native milestone: failure before Aura
entry, during executable-window handoff, at secondary release, or after Linux
entry needs different evidence. Match the actual firmware/build and validate
important conclusions against independent instructions or repeatable experiments.
Do not infer the new SPTM guest's Aff2 workaround applies to another boot path.

This refresh read primary public source metadata, reports and local sanitized
topology only. No new kernel source was executed or built; no Apple artifact was
downloaded, decompiled or published; no camera/server/helper live mode, policy,
firmware, volume, Startup Disk, root or native operation ran in this subtask.
There is no new physical performance result and no evidence from 31AJ that this
project must wait for Apple.
