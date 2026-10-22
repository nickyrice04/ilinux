# 31L: platform preparation before a secondary starts

2026-10-22. Offline investigation continuing the consumed 31K result.
**No native 31L controller is released by these findings.** No target access,
macOS modification, installed-image replacement or security change occurred.

The useful distinction is between **requesting core enable** and **restoring an
entire CPU cluster**. The checked macOS code implements both, through different
paths. It does not establish an omitted per-core preparation operation that
should be added to CPU1's two existing start writes.

This is stronger evidence than simply counting those final writes: the review
traced their surrounding locks and state updates, a separate cluster wake
path, its completion dependency, the T6050 ACC restoration override, and that
override's register mapping. It also checked whether the new locations yield
a useful read-only readiness observation. None currently does for CPU1.

## Evidence

The inputs are the same macOS 26.6.2 / 25G83 kernel-collection carrier and
derived members used by the previous CPU research. Carrier SHA-256:
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
Member digests remain ApplePMGR `a74c641b…b0f`, AppleT6050PMGR `45e8d9c2…143e`,
and AppleARMPlatform `f8cba090…6932`.

Three fresh REA 6.4.0 / Ghidra 12.1.4 function queries ran in the existing
isolated diskless VM. All exited 0, in 41.174, 40.862 and 17.381 seconds.
Their 255 instructions / 1,020 bytes are contained in provider-reported bodies;
all 238 high-pcode operations stay inside those bodies, without truncation.
The provider still has indirect-tail-call and removed-block limitations.
Behavioral conclusions below use bounded Apple LLVM disassembly and resolved
static references, rather than treating generated signatures as source.

The broader check matched **1,762 instruction words / 7,048 bytes in 14 bounded
blocks** to both the analysis members and original carrier. It also replayed
18 selected format-8 chained references, including the T6050 virtual dispatch
slots, base-class restore target and three ACC mapping-table pointers. This is
static file analysis, not authentication or modification of runtime pointers.

Raw Apple material and tool outputs remain under ignored build directories.
The public [validation record](../reverse-engineering/findings/cpu-startup31l-platform/validation.json)
contains addresses, digests, counts and limitations only. Fresh-query bodies
overlap the broader check; their instruction totals must not be added together.
The VM stopped, the prior job was restored and all shared locks were released.

## The per-core path does not contain a hidden cluster restore

**Confirmed static, bounded.** `AppleARMCPU::startCPU` at
`0xfffffe0008a51100` dispatches the secondary-core request through the previously
bound `function-enable_core` object. The earlier service-start analysis binds
that object separately from the CPU-idle callback. It is not a direct call to
the cluster-restore routine.

`ApplePMGR::enableCPUCores` at `0xfffffe000949606c` performs these surrounding
operations:

| Location | Behavioral observation | Meaning for this experiment |
|---|---|---|
| `+0x5c..+0xa4` | Disables local interrupts and acquires per-complex software locks; the original carrier resolves the helpers to `ml_set_interrupts_enabled` and `IOSimpleLockLock`. | These are macOS concurrency controls, not additional hardware reset-release transactions. |
| `+0xa8..+0xd4` | Dispatches the requested mask/state through T6050 slot `0xd18`, resolved to `configMiscCores`. | Retains the already reviewed die bitmap and die-local cluster-mask interface. |
| `+0x150..+0x1ec` | Updates software enabled masks, counts and timestamps for affected cores/complexes. | These bookkeeping stores do not identify a pre-start hardware readiness register. |
| Return paths | Releases the locks and restores the saved local interrupt state. | No separate call to cluster power-on or ACC restoration is present in this body. |

The independent `ApplePMGR::_cpuIdleInit` body at `0xfffffe00094af5e0`
initializes fields and callbacks in the supplied processor-info object. In the
checked normal path it does not perform a per-core MMIO release. Its name is
therefore insufficient grounds to import an idle sequence before the first
CPU1 marker. The caller's full OS registration/firmware context remains a
separate question; these bounded findings do not exclude earlier preparation.

## The separate cluster path has real prerequisites

**Confirmed static.** The following order is visible in the fresh queries and
independent byte checks:

| Function | Bounded behavior |
|---|---|
| `ApplePMGR::enableCPUComplex`, `0xfffffe0009496304` | Its on branch requests complex power at `+0x5c`, then conditionally dispatches ACC restoration with its boolean argument clear. The condition is a driver field at `+0x2494`; its active value is not established here. |
| `ApplePMGR::enableCPUCluster`, `0xfffffe0009496524` | Checks a software cluster-state record, requests power at `+0xe0`, then under the same driver condition invokes `_waitForACCClusterPowerUpGated` through a command gate before dispatching ACC restoration with its boolean argument set. |
| `_waitForACCClusterPowerUpGated`, `0xfffffe000949df18` | Its bounded wait examines a software cluster record and waits through a command-gate event when applicable. Completion is not merely a read of the generic CPU power-state nibble. |
| `AppleT6050PMGR::restoreHW`, `0xfffffe000987fd8c` | Its loop at `+0x54..+0x8c` invokes `enableCPUComplex(on)` for configured complexes before later SoC-wide restore work. This is broader platform restoration, not the bounded `startCPU` dispatcher. |

The T6050 complex-power function at `0xfffffe0009880a64` maps a physical
complex to SoC cluster index **physical complex + 1**. The prior verified
group-2 binding consequently gives `0x280620004`, `0x280620008` and
`0x28062000c`. This mapping remains distinct from misc-cores' die-local
cluster ordinal; it does not move CPU1's existing start command to another
offset. The low-nibble power request and bit-4 wait semantics are recorded in
the [October 19 findings](../reverse-engineering/findings/cpu-startup-2026-10-19/README.md).

The base `ApplePMGR::restoreACC` at `0xfffffe0009492b0c` restores performance
counter/feature state, updates accounting and conditionally requests a saved
performance state. Its T6050 override at `0xfffffe00098804a8` first calls this
base routine, then submits a 64-bit write of 1 through the ACC register
interface using selector `0xe440f8`. That order is established; the register's
complete hardware semantics and the need to repeat it for a sibling core are
not established.

## ACC selector provenance: do not reuse an older physical offset

**Confirmed static mapping.** The T6050 selector is resolved through the
three mapping tables selected by `_getACCMappingAndLength`, rather than being
added blindly to an old-generation CPU base. The selected entry has selector
base `0xe40000`; the residual offset is `0x40f8`. `initRegMaps` binds those
map identifiers to the following sanitized PMGR ADT entries:

| Physical complex | Register map | PMGR ADT reg index | Translated CPM base | Restoration address |
|---|---:|---:|---|---|
| 0 / M0 | 45 | 17 | `0x210e40000` | `0x210e440f8` |
| 1 / M1 | 56 | 27 | `0x211e40000` | `0x211e440f8` |
| 2 / P | 22 | 37 | `0x212e40000` | `0x212e440f8` |

The ADT bus-to-physical translation contributes `0x200000000` for these
windows. Each selected 8-byte access fits its ADT aperture. The map binding
calls are at `initRegMaps +0x1f8`, `+0x2e8` and `+0x3d8`. The mapping-table
references and payload hashes are retained in the validation record.

This gives an address with write provenance, **not a qualified read-only
status register or a new write allowance**. No getter or read-side-effect
contract for this location was established by this pass. Replaying it solely
because older m1n1 has a write involving literal `0x440f8` would ignore the
generation-specific mapping and restoration context. The pinned m1n1
`cpufreq.c` does not support T6050, and its generic initialization is not a
verified substitute for the T6050 path.

## What existing CPU0/CPU1 observations can discriminate

CPU1 is local core 1 of the already executing CPU0's M0 cluster. The latest
31K report already contains the useful generic power fields: both CPUs have
`parent_missing=false`, `device_disabled=false` and `auto_enabled=false` in
all three complete samples. CPU0 stays at desired 0 / actual 15; CPU1 changes
from desired 0 / actual 0 to desired 0 / actual 15 after the second start.
Consequently, **desired 0 alone is not evidence that CPU1 needs a manual
power-state request**: the executing CPU0 has the same desired value.

The readiness candidates from this platform investigation have these limits:

| Observation | Useful discrimination | Decision |
|---|---|---|
| Existing per-core generic PS fields | Already distinguish CPU1's reported inactive state from its actual-state transition; already report the parent/disabled fields. | Preserve the measurements. Re-reading the same fields alone is not new evidence of first fetch. |
| Existing CPU implementation byte at `+0x100` | Already distinguishes its observed 0-to-2 transition. | Keep its meaning opaque; it is not an established reset-release or running-PC indication. |
| Group-2 cluster power read | The macOS getter supports a 32-bit access, but it concerns the entire shared cluster and a separate field layout. | Not a per-core readiness discriminator for CPU0 versus CPU1. No new native read is added by this document. |
| Driver software completion byte | Explains the macOS wait ordering. | It is an object in macOS memory, not a hardware register to read from m1n1. |
| T6050 CPM restoration location | A confirmed write during cluster restoration. | Read semantics and current-state significance remain unknown; do not promote it into a status probe. |

This does not require proving every incoming CPU register before a bounded
experiment. A concrete new observation can be useful even when a negative
result is ambiguous. It does require stating which alternative the proposed
read/write distinguishes. None of the newly traced platform locations yet
distinguishes CPU1's missing first fetch/store from its already observed power
transition better than the existing measurements.

## Engineering consequence

For CPU1, continue the first-fetch/incoming-context investigation rather than
adding cluster-wide power or restoration writes to an active cluster. The
[entry investigation](native31l-entry.md) and
[candidate review](../kernel/experiments/smp31l-candidate/README.md) keep the
firmware handoff, secondary entry and publication hypotheses separate.

For the later first CPU in M1 and P clusters, these findings supply a concrete
review checklist: separate topology ordinals from SoC power indices, establish
whether cluster power/ACC restoration is already provided, retain the proper
mapping for each cluster type, and define observable completion before core
release. They do not provide a ready-to-run recipe or establish that macOS's
entire driver restore is necessary in raw boot.

The twelve Performance / six Super topology stays unchanged. All-core Linux,
idle/thermal behavior, scheduler cooperation and macOS performance parity
still require native measurements after secondary entry works.
