# 31S: what the public firmware diagnosis does and does not establish

Checked 2026-10-23, following the independently reviewed 31R checkpoint. This is
a bounded public-source update, not another project catalogue. No downloaded
code ran, no hardware operation occurred, and no upstream message was sent.

## Decision

**No demonstrated T6050 secondary-core workaround or matching G17C startup path
was found. Firmware/handoff initialization remains a well-supported research
direction; “only Apple can fix this” is not established by the available public
evidence.** Gravity states that conclusion, and it deserves attribution as the
project's assessment. It is not an Apple acknowledgement, a published erratum,
or a proof about every possible boot path on this machine's retained 25G83
environment.

The observed result is narrower: cores change power/state without verified
entry under the tested custom-image paths. A faulty or missing pre-handoff
configuration, an inaccessible initialization step, and an accessible step
that software has not yet reproduced remain distinguishable explanations.
Nothing in this search establishes a deliberate prohibition against Linux.
This distinction preserves useful investigation without promising a software
fix. Local CPU1 remains UNVERIFIED; native SMP and G17C acceleration remain
NOT RUN. See [31R CPU findings](native31r-firmware.md),
[31R GPU findings](native31r-gpu-firmware.md) and
[the independent M1 review](../native/boot/attempt31r-m1-offline-2026-10-23.md).

## Evidence for a firmware problem, with its limits

| Evidence | What it supports | What it does not establish |
|---|---|---|
| [Asahi m1n1 PR610](https://github.com/AsahiLinux/m1n1/pull/610), merged July 10, merge `5d84c4c34d3fbb8bbe6230cecd5e8df8428335a2` | Initial T6050/T6051 support reports secondaries powered according to PMGR but not executing, on 26.2 beta 2 and 27.0 beta 2. | Successful all-core bring-up, the exact blocking operation, or coverage of every subsequent firmware. |
| [July 2 inline review](https://github.com/AsahiLinux/m1n1/pull/610#discussion_r3514334184) and [author response](https://github.com/AsahiLinux/m1n1/pull/610#discussion_r3514495744) | The reviewer asks whether the correct offset still leaves an iBoot/firmware bug preventing startup; the author agrees. This is direct upstream discussion supporting that diagnosis. | An Apple response or a demonstrated impossibility theorem. Approval of initial-support code is not approval of a firmware root-cause proof. |
| [Gravity FAQ, pinned website source](https://github.com/GravityLinux/website/blob/cfc74e6b3fcdb2f794fbf725464f27b506ad8d21/content/about.md) | Gravity reports M5 Pro/Max misconfiguration as of 27.0 beta 5, says Apple has been informed, and says it must wait for Apple. | The page supplies no public Feedback identifier, Apple response text/link, mechanism, or fixed build. Treat notification/awareness as Gravity's report. |
| [Independent T6050 raw-path report](https://github.com/rolotrealanis98/m5pro-linux/blob/bb0c75e69d06247faf595641c5a12b0fadc415d2/docs/smp-t6050-raw-path.md) | Negative startup observations also exist on an 18-core J716s/M5 Pro using 27.2 boot objects and `mBoot-20457.41.2`; proposed alternative image packages were rejected before iBoot. | Proof that the inaccessible preparation step has been identified or that all permissible packaging alternatives have been exhausted. |
| [Sowyu direct-install checkpoint](https://github.com/Sowyu/m5-azahi/blob/82c90a5fd0b841d3acec4f558f9424b2cefec8bf/research-archive/probe/CPU-CHECKPOINT.md) | The failure is not confined to one RAM-chainloading setup; that author also records no earliest CPU1 marker after direct installation. | Identical incoming state on this machine, or a reason to repeat an equivalent installation. |

The independent reports remain at their 31R revisions. Their agreement makes a
shared platform/handoff problem more credible. Repetition of the same firmware
diagnosis across projects must not be counted as multiple independent Apple
confirmations. The narrow searches and linked records found no public Apple
response or accepted Apple bug record; that is a limit of this search, not a
claim that a private report does not exist.

## The newly inspected SMP patch is a comparator, not a demonstrated fix

The supplied lead resolves to
[ADevWithAnIdea/m1n1 commit `a611a93c1f8fa26ba2fec14a48e980c3ccbdb724`](https://github.com/ADevWithAnIdea/m1n1/commit/a611a93c1f8fa26ba2fec14a48e980c3ccbdb724),
dated August 15. Its actual changes are relevant to cache transitions:

- Separate the initial uncached reset stack from the later write-back stack.
- Publish stack pointers and shared startup state with cache maintenance.
- Put the spin-table mailbox in a Device-nGnRnE mapping, with independent
  per-CPU slots and explicit publication/acquisition ordering.
- Switch stacks across MMU enablement and reserve both stack allocations for
  the later kernel.

The patch leaves the two PMGR CPU-start writes unchanged. The inspected commit
does not supply a T6050 success log, exact firmware qualification, or evidence
that CPU1 reached the stack/MMU transition it changes. Shared-state publication
can matter before and after a core starts, so it should not be dismissed; it
also cannot be called the missing release operation merely from its title.

Its surrounding [SPTM emulator PR1](https://github.com/ADevWithAnIdea/m1n1/pull/1)
is closed, unmerged, with head `7e43bb1763ff97d661bbddb213596eda9475ae6a`.
The [closing comment](https://github.com/ADevWithAnIdea/m1n1/pull/1#issuecomment-6118622995)
points to [Gravity bootloader PR8](https://github.com/GravityLinux/bootloader/pull/8),
open at `8da6b14ba4672b93ad93917770a7516ec5889238`. PR8 explicitly says the SMP
patch was dropped. Its stated scope is base M4/MacBook Neo on 26.6.2, with Neo
testing; its public version explicitly does not work on M4 Max. The author's
separate private M4 Max branch is not public code or a T6050 result.

PR8's pinned `src/smp.c` is byte-identical to the Gravity and developer-branch
copies already examined in 31R: SHA-256
`7ba57060e8118841b17b1624c8b02a4a8535a977bc6f8275d0066ab75c7f22ce`.
There is no hidden T6050 release correction in that file.

Asahi also has a newer, independently inspectable general cache-coherency change:
[`d16a2f4e3c4d2753c38ef1bb3f756add5822ee15`](https://github.com/AsahiLinux/m1n1/commit/d16a2f4e3c4d2753c38ef1bb3f756add5822ee15),
September 27, moves shared state into a section kept Device-nGnRnE across
mappings. Its message describes general cache-related SMP failures, not a
T6050 workaround. This overlaps an important concern in the older proposed
patch, but is not proof of equivalent implementation or identical symptoms.

## SPTM explanations: useful boundaries, different qualified targets

The public [SPTM documentation](https://github.com/ADevWithAnIdea/apple-silicon-re/tree/35b1c63e5cbfb599d9814dddf68b0f53c236aa1f/docs/sptm)
is pinned at `35b1c63e5cbfb599d9814dddf68b0f53c236aa1f`. Its own
[scope](https://github.com/ADevWithAnIdea/apple-silicon-re/blob/35b1c63e5cbfb599d9814dddf68b0f53c236aa1f/docs/sptm/README.md)
describes primarily T8140/26.6, with some T8142/27 updates. It models enough
XNU-facing behavior for an emulator and explicitly does not describe every
real SPTM check. It is not a verified T6050/25G83 specification.

Two details prevent tempting but unsupported substitutions:

1. The [CPU registration description](https://github.com/ADevWithAnIdea/apple-silicon-re/blob/35b1c63e5cbfb599d9814dddf68b0f53c236aa1f/docs/sptm/xnu_bootstrap.md#238-register_cpu-and-cpu_id-endpoints-14-19)
   says a CPU registers when it spins up, assigning its logical scratch-state
   identity. Registration is therefore described after execution begins, not
   as the operation that makes a nonexecuting secondary fetch its first
   instruction. Endpoint numbers in that table do not identify the unrelated
   range-service owner still unresolved in local 31R.
2. The [UAT description](https://github.com/ADevWithAnIdea/apple-silicon-re/blob/35b1c63e5cbfb599d9814dddf68b0f53c236aa1f/docs/sptm/uat.md)
   explains handoff, map/unmap progress, firmware-owned leaves and completion
   acknowledgement. Its opening note still reports an emulator hang shortly
   after reaching login. These are useful protocol questions for the original
   lifecycle work, not qualified G17C addresses, role assignments or a complete
   native GPU startup sequence.

The source declares reverse-engineering provenance. Fetched source stays as
data under ignored `build/research31s/`; this note publishes only the bounded
scope and behavioral distinctions, not Apple disassembly or pseudocode.

## G17C check after the next public kernel update

Aurora's integration branch advanced from the 31R pin to
[`1aa2857509d50f7f787541280aba7b274721919c`](https://github.com/aurora-silicon/linux/commit/1aa2857509d50f7f787541280aba7b274721919c),
October 23 at 15:42Z, merging T6040 USB work. The current
[`drivers/gpu/drm/asahi/driver.rs`](https://github.com/aurora-silicon/linux/blob/1aa2857509d50f7f787541280aba7b274721919c/drivers/gpu/drm/asahi/driver.rs#L140-L198)
is byte-identical to the 31R file. Its only G17 match remains
`apple,agx-t8140`; it has no T6050/T8142 match. SHA-256:
`7bd5354da2a6c003c25cbb10cd9a80d4e0962b3986cb1052c359d3ca68d5a499`.

[Mesa PR47](https://github.com/aurora-silicon/mesa/pull/47) remains open at
`bd4290aef2b0f68afb3dd508a527fdaf0729b196`. The31R code/ABI comparison therefore
still applies: G17C has ISA identity recognition but is excluded from the M5
experimental admission predicate; the rebased tree reports host-only testing.
See [the exact predicates and typed UAPI comparison](native31r-ecosystem.md).
No matching T6050/G17C/25G83 firmware contract was established by these updates.

## Next useful discriminator and reproducibility

The parallel [31S CPU investigation](native31s-firmware.md) resolves the range
services to handlers in the same retained iBoot/mBoot image and identifies
range-protection behavior. Their historical inputs, effective secondary state
and causal relationship to CPU1 failure remain unknown. The next useful question
is whether the actual handoff leaves a necessary condition unmet, and whether
that condition is accessible to the custom loader. If it is firmware-owned and
immutable after handoff, an Apple change may be necessary. If an accessible
initialization requirement is identified, an original software correction remains
possible. Neither branch has been established. No equivalent PMGR retry or
firmware change follows from this review.

Fresh reads covered PR610 reviews, the supplied SPTM leads, current Asahi and
Gravity SMP history, scoped T6050/G17C issue searches, the previously identified
independent experiment tips, and Aurora PR47/current GPU binding. Public
snapshots and request manifests are retained under ignored
`build/research31s/public/`. They include request URLs, content hashes and fetch
times. One raw GitHub request for the current kernel file returned 429; the
public contents API then supplied the pinned file successfully. No build,
runtime test, firmware update or new native readiness claim is attached to
these source checks.
