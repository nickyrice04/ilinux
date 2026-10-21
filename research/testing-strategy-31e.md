# More useful evidence per native boot after 31D

2026-10-21. **Planning and source review only.** No native operation, VM run,
installation, boot change or performance measurement was performed for this
document. Proposed later phases are not live allowances. Keep the consumed
31B–31D receipts and procedures unchanged.

The best investment is a reusable offline test system plus a bounded native
campaign with conditional phases. A complete M5 firmware emulator would
require knowing much of the hardware behavior that we are currently trying to
discover. It would not remove the need for physical validation. We can still
eliminate many avoidable reboots by checking real code, transport failures,
artifact pairing and result handling before leaving macOS, then gathering
several compatible observations during each successful native session.

## What 31D changes

**Observed:** [31D](../native/boot/attempt31d-2026-10-21-result.md) completed
both diagnostic UART RAM zeroes and acknowledged both CPU1 start requests.
All 171 sequential samples retained `no_reset_record_seen`. CPU1 arrival was
unverified; the timer and Linux phases did not run. This rules out treating
console isolation alone as a demonstrated fix. It does not locate CPU1's
program counter or prove that no instruction executed.

**Engineering decision:** the next native CPU experiment should distinguish
earlier entry states using independently reviewed instrumentation. Another
unchanged start, a longer timeout, or several guessed power-register writes
would cost another reboot without resolving this ambiguity. Exact entry-code
review must establish which observations are possible before choosing the
instrumentation. A publication/visibility failure is a separate hypothesis
from failure to execute.

The existing [31D validation](../native/boot/attempt31d/review.md) already
tests the real client/parser, high physical addresses and a compiled UART
source harness, including sanitizer runs. Extend that work rather than
replace it with a model that silently assumes successful hardware startup.

## Which kinds of emulation help

| Layer | Useful work before a reboot | What a pass cannot establish |
|---|---|---|
| Original source tests and compiled harnesses | Pointer bounds, topology masks, packing, startup state-machine branches, timeout handling, instruction/source binding and error preservation | CPU reset release, real cache publication, hardware register semantics |
| Narrow instruction emulation | Run a pinned public startup block with modeled RAM and explicit entry state; test branches and which dependencies are reached before a marker | The real reset entry state, Apple-specific system-register effects, coherent visibility or execution time |
| Existing ARM64 Linux VM | Kernel/module builds, DT validation, services, two-stage root delivery, desktop integration, renderer policy, simulated NVMe refusal behavior | Native PMGR/ANS/N1/GPU support, physical SMP startup, native power or performance |
| Trace and protocol replay | Reproduce known controller observations; test dropped, delayed, truncated, duplicate and out-of-order events; exercise all result branches without hardware | New device behavior absent from the trace, a device's actual timing, or the correctness of a guessed protocol |
| Native bounded campaign | Resolve physical entry, interrupts, coherency, device initialization and measured throughput/energy | General correctness from one successful run or behavior of untested cores and states |

QEMU requires a machine model matching a guest's platform. Its ordinary
`virt` board is deliberately generic, not a physical Apple SoC. The official
`vmapple` model represents Apple's Virtualization.framework virtual platform;
its name does not mean t6050 hardware is emulated. These remain useful for
software testing, but selecting an ARM CPU cannot supply missing PMGR, ANS,
N1 or reset-controller models. [QEMU ARM targets](https://www.qemu.org/docs/master/system/target-arm.html),
[virt](https://www.qemu.org/docs/master/system/arm/virt),
[vmapple](https://www.qemu.org/docs/master/system/arm/vmapple.html).

Unicorn supports ARM64 instruction emulation and instrumentation. A later
small harness could execute precisely bounded public m1n1 code and trap memory
accesses. It must stop on an unsupported instruction or unknown Apple register
instead of inventing a successful result. First prefer the existing compiler,
disassembler and source harness: adding an emulator dependency is worthwhile
only when instruction execution answers a specific unresolved question.
[Unicorn capabilities](https://www.unicorn-engine.org/).

The immediate implementation now uses an original dependency-free
[instruction interpreter](../kernel/experiments/smp31e-emulator/README.md),
an [observation prototype](../kernel/experiments/smp31e-observer/README.md)
and a [campaign replay tool](../tools/boot-campaign/README.md). They operate
on pinned public bootloader instructions and explicit synthetic state. No
additional emulator installation is needed. The first-C-frame path and an
original earlier recorder can be checked offline; physical entry and memory
visibility still need separate evidence.

QEMU record/replay reproduces execution inside a modeled QEMU machine and
supports checkpoints. It does not directly replay a native USB journal as an
M5 machine. Use it when a reproducible VM software failure merits reverse
debugging; a small event-replay harness is simpler for current controller
failure paths. [QEMU record/replay](https://www.qemu.org/docs/master/system/replay.html).

For every model, distinguish **observed facts**, **hypotheses** and **test
assumptions** in its inputs. Unknown reads should fail closed. Test a model
against a held-out native observation, not only the trace used to construct
it. A synthetic device that returns the result our driver expects only proves
that those two pieces agree. It cannot validate the missing hardware contract.

## m1n1 tracing and repeated kernels

m1n1 already provides proxy operations, chainloading and hypervisor facilities
for hardware tracing and guest debugging. That is a useful long-term route to
shorter cycles once the particular target and recovery path are validated.
The published short kernel-test-cycle capability is not a timing achieved by
this project. [m1n1 User Guide](https://asahilinux.org/docs/sw/m1n1-user-guide/).

There is a specific limitation for tracing macOS on this M5: the current Asahi
hypervisor guide has no pinned target for M4 or newer machines, citing bugs
and the SPTM requirement for XNU. Therefore running this machine's macOS under
m1n1 is an additional porting project, not an available, proven shortcut.
Static REA plus public source and targeted independent native observations
remain useful now. [m1n1 hypervisor support](https://asahilinux.org/docs/sw/m1n1-hypervisor/).

Similarly, do not presume that chainloading or a guest reboot returns arbitrary
new hardware state to the original baseline. A timed-out secondary may still
be executing or parked somewhere unknown. Retrying CPU startup, unloading a
controller after a partial probe, or launching Linux from that state could
erase attribution. A future reusable native harness needs an explicit,
verified quiescent-state contract before repeated kernels or hardware phases
can safely share a session. It does not require replacing the installed boot
entry merely to develop that contract offline.

## Prepare the campaign before requesting the next reboot

1. **Freeze the tested artifacts and the experiment graph.** Record source
   and output pins, hardware predicates, phase prerequisites, allowed mutation
   counts and one total deadline. Predeclare success, partial progress,
   visibility failure, transport loss and timeout outcomes. A local event
   recorder must preserve progress even if the target stops answering.
2. **Exercise the actual controller offline.** Reuse the pinned client and
   BootArgs/ADT parser. Cover wrong machine, high-address arithmetic,
   unexpected reset records, partial upload/publication, stale observations,
   late replies, lost USB, parser failures, supervisor expiry and a broken
   result writer. Assert that uncertain mutation completion never triggers
   an automatic retry. Replay consumed outcomes as regression inputs; do not
   convert synthetic success into native evidence.
3. **Make CPU entry observable in one attempt.** After the exact entry audit,
   choose a small set of independent checkpoints that distinguish the first
   reachable code, critical setup and the existing arrival path. Checkpoints
   should not depend on the same stack, console, cache assumption or helper
   being diagnosed where avoidable. Preserve the original startup sequence
   unless a separately evidenced defect requires changing it. Report the
   actual visibility guarantees and sequential sampling limits.
4. **Prebuild later tests, but gate their execution.** A verified arrival can
   justify already-reviewed bounded timer/request observations. It does not
   automatically justify Linux SMP, a second cluster, frequency changes or
   storage initialization. These need exact code and a demonstrated handoff
   or quiescent state. If the next package cannot establish that contract,
   returning to macOS after collecting richer entry evidence is still the
   correct outcome.
5. **Have the next Linux batch ready in parallel.** Once a valid two-core
   handoff is implemented, ship the matching kernel/DT, collector and renderer
   comparison together. Review conditional outcomes offline so the M1 agent
   executes the prepared procedure instead of writing new live commands while
   the clock runs. Preserve checkpoints before each new hardware transition.

Measure efficiency of development by resolved hypotheses and complete usable
datasets per reboot, not the number of register writes or individual tests.
A hundred polls of the same ambiguous flag are less useful than two
independent observations that separate plausible causes.

## A useful future Linux batch

This ordering is a proposed campaign after CPU entry and the Linux handoff
work; it is not permission to append these phases to 31D or an unreviewed 31E.

| Order | Work in one healthy Linux session | Gate and reason |
|---|---|---|
| 1 | Capture exact CPU topology/identity, boot arguments, online map, initial faults and available telemetry; verify the control link | Establish a common baseline before changing anything |
| 2 | Short timer, bounded cross-core request/IPI and shared-memory integrity checks, then fixed-work per-core throughput | Two listed CPUs are insufficient evidence of usable SMP; stop on faults or stalled progress |
| 3 | Compare the existing renderer with the reviewed worker policy at unchanged geometry; record frame callbacks, event/IPC latency and CPU time | Attribute the responsiveness benefit to a known CPU/renderer change |
| 4 | Run the existing memory matrix plus streaming bandwidth with explicit CPU placement, page backing and idle desktop conditions | Distinguish locality, placement and bandwidth from a presumed memory-clock problem |
| 5 | Collect approved USB-control-link transfer/reconnect observations and checkpoint results on the helper | Preserve work and quantify the current development path; this does not test N1 Wi-Fi |
| 6 | If separately prepared and authorized, load the guarded storage set, enumerate namespaces and perform bounded repeat reads | ANS/SART/NVMMU initialization is a new DMA/power path; run last, with no automatic retry after a partial failure |

Do not add a first DVFS transition, deep-idle experiment, new cluster start and
first storage probe together. Their interactions would make a failure difficult
to locate. Later successful baselines can support broader combinations.
For sustained performance tests, establish thermal/energy observation and
recovery first; maximum CPU utilization alone is not efficiency.

## Readiness against the workstation goal

**CPU and memory:** [attempt29](../native/boot/stage-b-2026-10-20-attempt29-result.md)
already observed enabled MMU/caches, a sampled Normal write-back,
inner-shareable mapping, and substantial actual huge-page backing in larger
allocations. Its global-random and page-local results differ greatly; existing
macOS comparisons have different placement/QoS/compiler conditions. This is
not evidence that all RAM is uncached, nor proof of full memory performance.
[Attempt30](../native/boot/stage-b-2026-10-20-attempt30-result.md) estimated
about 2.65 GHz on the single CPU and measured compositor CPU time near 97% of
control-phase wall time, with median frame callbacks around 256–257 ms for
small damage and 513–516 ms for full damage. The next measurement should build
on these observations rather than assume the CPU is simply at its lowest speed.

First establish two-core correctness, then expand within and across the
actual cluster topology to all 18 cores. Measure scheduler placement, fixed
work, tail latency and sustained performance; follow with verified DVFS,
idle/resume and energy per task. Software rendering remains relevant even
after SMP: graphics acceleration can be necessary for both smooth interaction
and macOS-class energy use. VM renderer improvements do not prove native GPU
support or a promised percentage speedup.

**Storage:** the [read-only storage set](../kernel/experiments/nvme-ans3/storage-ro/README.md)
has meaningful VM tests, including a writable control disk proving that its
write refusals are enforced by the guard. It still has no native allowance.
Enabling the real controller initializes firmware, mappings and queues even
when host media writes are prohibited. Rebase its launcher against current
two-stage artifacts and review it before a physical probe. Repeatable raw
reads come before throughput tuning and separately authorized scratch writes.
Access to existing macOS files is an additional filesystem/encryption problem;
controller enumeration cannot establish APFS file access. Do not use original
macOS data as a write benchmark.

**Networking:** [N1 research](../kernel/experiments/n1-wireless/README.md) and
[ACIPC software tests](../kernel/experiments/driver-contracts/acipc/README.md)
provide useful foundations, not a working WLAN driver. The unresolved work
includes descriptor ownership/completion, DMA ordering, firmware lifecycle and
WLAN control integration. REA can target the real DriverKit framework code;
the tiny dext stubs are not the transport implementation. Original offline
protocol models are valuable here before hardware writes. Keep built-in Wi-Fi
as a first-class acceptance target: association, IP/DNS/browser access,
throughput, reconnect and power save all need native evidence.

The existing USB/SSH path and previously demonstrated helper relay can support
development in the meantime. A native agent can checkpoint source and reports
through the helper while the root is in RAM. That reduces manual file handling
without pretending persistence, independent networking or acceptable desktop
performance is finished. REA itself already has an offline development path;
moving it into native Linux is not required to continue CPU/network research.

## The helper M1 does not have a demonstrated reboot-per-attempt requirement

The [attempt15 decision](../decisions.md) requested a freshly restarted helper
after an M1 kernel panic/reset confounded the target experiment. That was a
specific diagnostic response. The successful attempt30 report records M1
reader-start uptime of **20,933 seconds**, despite a human-reported restart.
Fresh restart was therefore not independently established in that successful
run. This is evidence against treating restart as a demonstrated universal
prerequisite, not a controlled study of long-running USB reliability.

For a future reviewed handoff, replace the automatic M1 restart with a helper
health gate: awake and powered, one owned USB reader, no unresolved helper
panic or USB fault, and correct device discovery before target mutations.
Record uptime as metadata. If that gate fails, resolve the helper connection
before starting the experiment; a restart can remain a recovery action.
After an uncertain target mutation, stop that target session rather than
restart the helper and reconnect to guess what happened. Historical consumed
instructions stay frozen. No recurring boot-policy check is added.

**Immediate priority:** finish the exact early-entry investigation and its
offline harness, prepare a richer conditional CPU experiment, and keep the
Linux measurement batch, storage preparation and N1 protocol work moving in
parallel. A full physical M5 emulator or a speculative hypervisor port should
not delay these concrete improvements.
