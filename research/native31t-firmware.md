# 31T: protection preparation is not a measurement of CPU1 state

2026-10-23. **Offline investigation; native31T HOLD / NOT RUN.** The merged
M1 review of31S passed441 pins,207 Python methods and74 portable C groups.
CPU1 execution remains unverified. All31S and earlier sources and receipts are
preserved. No native operation or installed-image change was performed.

This pass distinguishes two missing pieces of the CPU1 diagnosis: **what the
firmware can configure, and what state a secondary actually consumes**. The
retained firmware contains a separate control-policy path in addition to31S's
range-bound setters. An existing range-preparation call selects one of those
control policies. This is evidence of firmware preparation, not evidence that
Linux omitted that operation or that an effective restriction caused the failed
first fetch.

The public T6050 investigation adds useful observations, but its boot-CPU system-
register reads do not establish secondary state. The cited hypervisor secondary
setup likewise does not release a host CPU: it operates on shadow state after
host secondary startup. Neither supports a new native workaround here.

## A separate control path, with an established consumer

**Confirmed bounded static:** the same retained generic iBoot/mBoot dispatcher
used in31S has separate services for control policy. The131-entry signed relative
table and its distinct target anchor retain their31S provenance.

| Service | Case target | Handler call site | Returned handler entry |
|---|---|---|---|
| 14 | `0x100c1cb7dd4` | `0x100c1cb7de0` | `0x100c1adad08` |
| 18 | `0x100c1cb7e54` | `0x100c1cb7e64` | `0x100c1adabbc` |

The bounded successful dispatch paths each select one of four banks and contain
eight control-register write sites, pairing a current-context accessor with an
ACC-named accessor. Retained public register definitions identify these as CTRR
and CTXR control accessors. CTRR constructs a fixed control policy; CTXR carries
caller-supplied control data. These paths synchronize their changes but do not
read back effective protection state. Error-reporting tails are separate from
the checked successful paths.

The actual consumer edge is `0x100c1aec740`, inside the previously checked range
preparer. It calls wrapper `0x100c1adacfc`, which fixes bank selector1 and enters
service14. This connects range preparation to a distinct CTRR control operation;
the successful bounds service12 alone was not the complete preparation contract.
The relation is established by the call destination, wrapper argument and
dispatcher target, not by neighboring addresses or a function name.

**Limit:** the historical raw-image branch and descriptor values were not
captured.31Q's current-producer inference does not turn this call into a measured
event during the consumed boot. Nor does a completed setter establish the value
visible after a power transition, successful locking, selected physical CPU,
or the instruction permission at CPU1's reset entry. ACC/EL accessor names alone
do not establish physical ownership or effective privilege;31L's VHE limitation
still applies. No control value or firmware service is proposed for replay.

## The new public state dump has a narrower scope than its conclusion

The public
[T6050 report](https://github.com/betizzel/omarchy-m5/blob/23e40584d97ad94e39d4a96d178ba27730e91ff4/docs/smp-t6050-findings.md)
concerns a15-core J714s M5 Pro with macOS26.5/25F71 and mBoot18000.120.36.
That is a relevant same-SoC comparison, but differs from this J716c M5 Max's
retained25G83/mBoot18000.161.10 environment. Its stronger claim that CPU state is
identical across cores is not supported by the supplied
[range-state probe](https://github.com/betizzel/omarchy-m5/blob/264c683c9416903aa96fdae5cda7bdf5487234ec/scripts/probes/smp-ctrr-dump.py):
the system-register loop executes on the boot CPU; the later loop over CPU
descriptors reads reset-mirror MMIO only. Source was inspected as data, never
imported or executed here.

A boot CPU executing outside a reported interval therefore does not eliminate
secondary-specific enforcement. Equal reset mirrors also do not supply equal
MMU, cache, EL, protection or first-fetch state. This is a concrete observation-
scope correction, not evidence that range protection is the actual cause.
The broader public-source assessment and exact source pins are in
[the31T upstream review](native31t-upstream.md).

## The proposed hypervisor path does not solve first host-CPU fetch

The public SPTM-related secondary initialization in
[m1n1 PR695's implementation](https://github.com/AsahiLinux/m1n1/blob/281b0175e712bd3e0f82fe4c9c0a1f403c78b03a/src/hv/hv_sptm.c)
copies software shadow arrays. It is not a physical CTRR/CTXR programming path.
Current
[hypervisor initialization](https://github.com/AsahiLinux/m1n1/blob/7cde7d1a784d851ebfee5579fa363c38b14150c0/src/hv/hv.c)
starts host secondaries before guest setup; guest work is later dispatched onto
those running host CPUs. Thus that helper cannot supply the missing first
instruction of an unobserved host CPU1. The upstream review separately records
the tested hardware/mode limits of related hypervisor changes.

SPTM support in a SoC, an available firmware object, a static registration
routine and a resident monitor in this exact boot are different facts. The
existing raw-metadata evidence does not establish the latter. A registration
routine reached after a CPU starts is not evidence of a pre-release requirement.
No boot-format substitution, registration call, firmware replay or protection
change is justified by these comparisons.

## What can and cannot distinguish the remaining hypotheses

| Evidence | Supported conclusion | Still missing |
|---|---|---|
| Existing reset mirrors before startup | The observed address-field/readback predicate passed at that time. | Effective reset PC, later state, first fetch and permissions. |
| Consumed31N local startup pair and power/state transitions | The reviewed requests completed and sampled state changed. | Any committed CPU1 instruction/identity evidence. |
| CPU0 recorder and maintenance controls | The observation mechanism works in CPU0's qualified context. | CPU1's incoming translation, visibility and cache state. |
| Retained range bounds and separate control setters | Firmware has concrete preparation mechanisms and the checked consumer edge. | Historical execution, resulting CPU1 bank values and enforcement. |
| Boot-CPU range-register dump on another T6050 machine | That boot CPU's reported values in that run. | Local CPU1 state and same-image/same-phase applicability. |
| Hypervisor shadow-state initialization | Guest bookkeeping for an already running host secondary. | A host first-fetch workaround. |

**Unknown:** whether CPU1 is held before fetch, reaches a different context,
faults before a visible record, encounters an effective execution restriction,
or publishes state the current observations cannot see. The cache/publication
comparators do not select between those cases: the existing early recorders
precede stack/MMU initialization and their instruction ranges already use the
reviewed publication path. Their negative result remains inconclusive.

A useful future record must bind the exact firmware/image, boot phase, CPU that
executes a system-register read, intended physical target of an MMIO read,
EL/VHE context and physical-versus-shadow provenance. Missing CPU1 fields must
stay missing. It must also state whether a proposed prerequisite happens before
first fetch or requires a CPU that is already executing. This is a research
qualification requirement, not a new collection command or native test request.

The retained offline artifacts cannot reconstruct unrecorded historical CPU1
state. No newly qualified read-only observer or actionable startup correction
was established, so this pass adds no CPU mutation code and requests no restart.
It also supplies no proof that the failure is immutable or that only an Apple
change can resolve it. Missing initialization and an inaccessible firmware
restriction remain distinct hypotheses.

## Provenance and bounded validation

The decoded generic image remains4,266,536 bytes, SHA-256
`b4822fc8902c3693ee590c544011603423a75291edd60afd31210d068a4ca120`.
The byte-preserving analysis ELF remains
`f89169923c17be829c6b31c3c04c5695d06d42a42cea7390f61214202400dcee`, with raw
input at file offset4096 and analysis base `0x100c1aa4000`. This is not a measured
runtime mapping. Wrapper/compressed-input provenance is inherited from31S;
no decompression or personalized-object access was repeated.

The initial two REA requests mistakenly used preceding jump-table addresses.
Both returned no-procedure refusals and are preserved as failures, not coverage.
The corrected requests use independently decoded direct-call destinations;
their exact returned bodies and all provider flags are retained in the
[validation record](../reverse-engineering/findings/cpu-startup31t/validation.json).
No artificial procedure, byte change or forced analysis seed was used to turn
table data into a function. Independent LLVM/raw/ELF checks keep code ranges
separate from table data, and whole-function pseudocode is not accepted as source.

Both corrected queries completed with exit0, in67.709 and67.468 seconds. Their
returned bodies contain67 instruction addresses and41 P-code operations, with
no reported truncation, body escape or removed-block warning. Independent checks
cover **82 instruction words /328 bytes in6 disjoint blocks**, with zero
mismatches;81 words are new beyond the prior published range union and1 overlaps.
The two four-entry local tables account for32 separately hashed data bytes.
An original private bounded integer evaluator checks the bank pairing and
caller-data/fixed-policy distinction using synthetic inputs; it does not model
register enforcement, run firmware or establish a hardware result.

The two batches used the existing isolated VM with loopback only and no physical
USB. Root owns the separate VM completion records and lock handling. Apple bytes,
assembly, pseudocode and private evaluator output remain ignored; public records
contain behavioral metadata only. Native Linux SMP, CPU1 first fetch and
performance/energy improvement remain unmeasured.
