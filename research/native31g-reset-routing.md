# Native31G: CPU release routing and reset evidence

Date: 2026-10-21. Baseline: consumed 31F, M1 report `f2d9035`.
Scope: offline analysis and read-only topology observations. This is an
original behavioral specification, not recovered Apple source. Apple artifacts,
pseudocode and disassembly remain in the ignored analysis workspace.

## Decision supported by the evidence

31F verified CPU0's publication of the recorder and acknowledged both start
stores, but observed no CPU1 marker. It did not prove which instruction CPU1
executed, or that CPU1 executed no instruction. Repeating those stores with
another marker placement would leave the main uncertainty intact.

Before changing the start address, distinguish three different indices:

1. MPIDR/ADT physical cluster identity;
2. the CPU's **die-local cluster ordinal**, exposed as `die-cluster-id`;
3. the PMGR **SoC power-domain cluster index**.

The T6050 power-control mapping to indices 1, 2 and 3 does **not** alone justify
moving CPU1's misc-cores start write from `+8` to `+0xc`. These interfaces use
different mappings. The retained ADT's property-name inventory includes
`die-cluster-id`, but its value was omitted by the collector's allowlist. Its
absence from sanitized values is not an absent firmware property and does not
justify falling back to MPIDR.

The follow-up read-only collection on 2026-10-21 resolved this ambiguity:
all 18 CPUs' nonunique `die-cluster-id` ordinals equal their existing cluster
IDs 0, 1 and 2; CPU1 is die-local cluster 0, local core 1. `acc-cores` assigns
its die-wide bit index 1. **CPU1's two start values remain 2, at misc-cores
offsets `+4` and `+8`. No address or mask correction for CPU1 is supported.**
Consequently the next CPU1 attempt must be explicitly diagnostic, with new
state observations that distinguish release and publication hypotheses.
The collection did not retain the separate unique `die-id` identifier.

The proposed 31G observations bind the ADT's `MCPU0_0` and `MCPU0_1` generic
PS registers at `0x280600000` and `0x280600008`, respectively. These are not
the `0x280620000` cluster-power controls and not the `0x280688000` start
commands. Their device IDs, flags, group, block, offsets and bounds must be
checked from the actual boot ADT before any read. The generic PS field names
match the pinned [m1n1 PMGR definition](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/proxyclient/m1n1/hw/pmgr.py):
desired `[3:0]`, actual `[7:4]`, device-disabled bit 10, parent-missing bit 11,
and auto-enable bit 28. This is a source-supported interpretation, not yet
a measured t6050 CPU-state contract. A value of 15 is the legacy active
state, not CPU instruction-execution evidence.

Two bounded baseline reads before CPU1 starts and at most three subsequent
two-register samples can reveal a state transition without changing those
registers. A baseline fault stops the attempt. Later reads must not introduce
the old shared exception-guard mutation while CPU1 may run. Read success
before release does not guarantee later accessibility; the independent
supervisor remains necessary. Preserve a partial CPU0-only sample if the
CPU1 read fails, stop on the first error, and never infer reset dispatch from
PS state alone. No PS write is justified by this review.

### Focused controller review

Review compared the new `smp31g.py` with frozen 31F and inspected the live
ADT binding, PS tracker, fixed read helper and failure tests. The same two
CPU1 start stores remain; the new helper performs one aligned 32-bit read
between barriers and never changes the shared exception guard. Read intent
is journaled before dispatch; a failed read or pre/post-read exception check
retains partial evidence and stops subsequent target commands.

The review found and reproduced one error in terminal-sample authorization:
an observation that returned after the arrival deadline was classified as
the same timeout as an idle loop expiring naturally. A late invalid arrival
flag could therefore trigger two extra PS reads before its state was checked.
The controller now gives every in-flight deadline crossing the distinct
`cpu1_arrival_observation_deadline` reason. Only natural loop expiry retains
`cpu1_arrival_timeout` and permits a final diagnostic sample. The regression
with a late invalid flag now stops at six PS reads and performs no terminal
sample. Focused original offline controller tests, including that regression,
pass; this is not native runtime evidence.

An entry or recorder change before the second start intentionally stops the
campaign, without final sampling or a second write. The tracker's strict
phase prefix is correct for that contract. A final sample is allowed only
after natural no-arrival expiry following both writes, or after verified
arrival, all eight requests and final park. No final sample is authorized
after transport, recorder, target-state or deadline errors. Individual PS
sample durations are not reported, so these observations must not be used
as performance or wake-latency measurements.

## What 31F actually established

`native/boot/attempt31f-2026-10-21-result.md` reports RAM/UART checks, EL2/VHE
and all 16 translation checks passing. Recorder body, vector hook and whole
text readback passed. There were 63 mutation intents and two acknowledged CPU1
start stores. Across 94 complete recorder samples / 470 reads, the highest
phase stayed zero; reset/spin sampling also saw no reset record. No arrival,
callback, final park or Linux SMP was verified.

CPU0 readback demonstrates CPU0's view. It does not independently demonstrate
CPU1 instruction visibility, a successful first store, or effective hardware
reset dispatch. An exception at the first recorder store, another reset
destination and failure to leave reset remain distinguishable hypotheses.

## PMGR startup mapping: corrected precision

**Confirmed static:** the previously verified T6050 register groups place
misc-cores at physical `0x280688000` (group 8) and cluster power control at
`0x280620000` (group 2). The latter's three CPU power controls map to SoC
cluster indices 1, 2 and 3. See the retained
[CPU startup findings](../reverse-engineering/findings/cpu-startup-2026-10-19/README.md).

**Confirmed static:** `ApplePMGR::configMiscCores`, entry
`0xfffffe0009495968`, has two startup-addressing branches selected by a
driver field at object offset `0x238c`. Its value and property provenance
have not been independently established here.

* In the legacy branch, the cluster start-register offset is `8 + 4 × loop
  index`; core bits come from the retained `clusters` width/position table.
* With selector value 2, the startup register uses a stored **die-local
  cluster ordinal**. The kernel-topology branch takes this from cluster
  descriptor offset `0x1c`, using an 80-byte descriptor stride. The alternate
  internal-object branch takes its saved value at offset `0x8df0`.
* The mode-2 die-wide start bitmap uses the **physical-core bit index from
  `acc-cores`**, not an unconditional `4 × cluster + core` calculation. An
  8-byte entry is matched by its bytes 6 and 7 to MPIDR Aff0 and Aff1;
  byte 5 supplies the bit index. The cluster-local mask uses the topology
  CPU record's `cluster_core_id` field at offset `0x74`.

The `acc-cores` origin is independently supported by the property lookup and
table initialization in `ApplePMGR::initDriver` at
`0xfffffe000947d8d4..0xfffffe000947d9a3`: property name, length divided by
eight, retained entry count and data pointer all lead to the table consumed
by `configMiscCores`. The property name itself was checked against the
original carrier, not inferred from a convenient table shape.

**Observed read-only on this Mac:** `edt-property-ver` is 2; `acc-cores`
contains 18 records of eight bytes. Their record identifiers are 1 through
18; byte 5 is sequential 0 through 17, byte 6 is local core 0 through 5
repeated for each cluster, and byte 7 is cluster 0, 1 or 2. The observed
property version is consistent with the mode-2 table, but this pass has not
proved the specific assignment from that property into object offset
`0x238c`; do not silently upgrade that association to a traced assignment.

The earlier statement “`+8 + 4 × cluster-index`” therefore needs this
qualification. It must not silently mean logical, MPIDR and SoC power indices
are interchangeable. This document adds precision without rewriting the
historical result or changing consumed controllers.

## Independent public-source check

Apple's public [CPU topology declarations](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/arm/cpu_topology.h)
place `die_cluster_id` at cluster-descriptor offset `0x1c`, and at CPU-record
offset `0x70`; `cluster_core_id` follows at `0x74`. These offsets match the
binary's accesses. The public cluster structure is 80 bytes. Its CPU prefix
matches, but the analyzed binary strides 128 bytes versus the public
structure's 120: this is a prefix match, not complete ABI equivalence.

Apple's public [topology parser](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/arm64/machine_routines.c)
reads `die-cluster-id`, falling back to MPIDR Aff1 only when that property is
absent; it similarly reads `cluster-core-id` with an Aff0 fallback. This is
independent support for the field interpretation. Public source from another
revision is not proof of the precise running kernel's entire implementation.

Fresh REA analysis of `ApplePMGR::getCorePhysID` at
`0xfffffe0009487b24` confirms it returns the physical identity from an
existing kernel-topology CPU record. It does not interrogate a stopped CPU's
registers and is not evidence that the core actually ran.

## Reset target and SPTM: what remains unknown

The pinned public [m1n1 SMP implementation](https://github.com/AsahiLinux/m1n1/blob/57a9339ffd1876e78297b17d34dece8cff8fa1ba/src/smp.c)
uses the CPU implementation-window base as an RVBAR mirror, with address and
lock bits. Prior lab observations that CPU0 and CPU1 mirrors match the loaded
image constrain an address mismatch; they do not independently establish the
effective reset-routing policy on this chip.

Previously inspected SPTM early entry and XNU boot dispatch show distinct
firmware and OS entry paths. Their existence in a macOS boot does not prove
that the current custom raw boot routes CPU1 through them. No supported
SPTM call, lock change or protection-register write that fixes this lab boot
has been established. Do not copy a macOS entry protocol into the raw boot,
attempt to defeat locks or change security settings on this evidence.

Likewise, pinned m1n1 reads CPU implementation offset `0x100` while waiting
for a non-deep shutdown, and avoids inaccessible last-core/deep-sleep
registers. That is evidence for a **candidate** bounded CPU1 state read in
the already-active cluster; it is not yet a t6050-specific semantic contract.
This REA pass did not corroborate that offset in the T6050 Apple driver.
Neither its low byte nor a zero value may be labeled “CPU1 executed” or
“CPU1 never executed.” Start-command offsets `+4` and `+8` also must not be
treated as readable status merely because writes are known.

## Analysis provenance and validation

Analysis ran only in the existing isolated, diskless ARM64 VM. REA 6.4.0 and
Ghidra 12.1.4 inspected the retained ApplePMGR member; no target instructions
executed. Both new queries completed within their 90-second per-query caps.
The VM stopped, the prior job was restored and the shared locks were released.

Carrier SHA-256:
`26ddfbe95c7e6ac9a76aedac424576bf00467e7c13da49dd82f8010efdb75093`.
ApplePMGR member SHA-256:
`a74c641b1445c3347d72840a95a08cdff344a14fed8700c2ff9fb75a0a4d0b0f`.

| Bounded analysis | Original bytes / LLVM words | Body SHA-256 |
|---|---:|---|
| `getCorePhysID`, `0xfffffe0009487b24`, 100 bytes | 25 / PASS | `31f6e889b6c00b70824c16297926537cdcc31b7266db2215d4752998ea86f528` |
| `_cpuComplexInit`, `0xfffffe0009489eb0`, 5,236 bytes | 1,309 / PASS | `c3182d72a81b2f3af5998d9cbb5000d1b0c34a8fae7857590303390b75434b64` |
| `acc-cores` lookup, `0xfffffe000947d8d4`, 208 bytes | 52 / PASS | `dc0812b03cb178ea03cb6c98668c10c1c97ebdf3742e0a58599ab07a768bce98` |
| Mode-2 startup mapping, `0xfffffe00094959c0`, 652 bytes | 163 / PASS | `58ec74cc009c556694afeb274e2c5c8a9708cae837f1e1b059436800d371c22b` |

`getCorePhysID`'s whole-function pseudocode was **rejected** because 43 pcode
operations extend beyond the bounded body. Only its 25 original, independently
decoded instructions inform the finding. `_cpuComplexInit` had no out-of-body
pcode, but provider-removed blocks require manual review; no new startup write
was inferred from it. Prior `configMiscCores` whole-function pseudocode was
also rejected; the mapping above comes from bounded original-byte/LLVM
dataflow, checked against public types. Static consistency is not a hardware
success result.

Private reproducibility records are under the sibling lab's ignored
`build/rea-lab/smp31g/`: query plan and run records, `validation.json` and
`routing-validation.json`. No Apple pseudocode, bytes or raw diagnostics are
included here.

## Consequence for all core types

This machine has **12 Performance cores (ADT M, clusters 0/1) and 6 Super
cores (ADT P, cluster 2)**. CPU1 shares CPU0's Performance cluster. The next
release experiment must establish that same-cluster path before extending
to a powered-down cluster or the Super class. Keep topology routing, PMGR
power index, frequency domain and scheduler capacity as separate fields.
Successful CPU1 arrival would be a prerequisite for two-core correctness,
timer/IPI and renderer-threading measurements, not macOS performance parity.

There is a concrete original implementation requirement for later clusters:
derive a per-CPU startup route from the validated topology and `acc-cores`
table, and keep both indices separately. Require exactly one table match for
each MPIDR Aff0/Aff1 pair, unique die-wide bit indices within the 32-bit
register, local core indices below 32, and a consistent die-local cluster
ordinal for every CPU in a cluster. Reject absent, duplicate, truncated or
conflicting entries. Do not silently fall back to a four-bit stride on t6050.

The observed routes are bit 0..5 for the first Performance cluster, bit
6..11 for the second, and bit 12..17 for Super. The existing four-bit
calculation collides across cluster boundaries: cluster 1/core 0 needs bit 6,
and cluster 2/core 0 needs bit 12. CPU1 remains bit 1. Offline tests should
cover all 18 routes and malformed tables before any later multi-cluster
launch. These arithmetic corrections do not solve the currently unobserved
same-cluster CPU1 entry, and must not be advertised as a tested SMP fix.
